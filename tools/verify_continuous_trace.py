"""Independently replay one-attempt continuous evaluation and retirement."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from continuous_execution_support import permit_reset, verify_transition
from eval_gate_development import verify_loaded_actor
from eval_natural_lifecycle import verify_policy


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay_trace(conditions: list[dict], trace: dict, rows: list[dict]) -> dict:
    """Rebuild active masks from failures and horizons, never from saved masks."""
    count = len(conditions)
    if not count or len(rows) != count:
        raise ValueError('incomplete condition grid')
    identifiers = [c['condition_id'] for c in conditions]
    if len(set(identifiers)) != count:
        raise ValueError('duplicate condition')
    starts = [c['start_frame'] for c in conditions]
    stops = [c['support_stop'] for c in conditions]
    horizons = [c['horizon_steps'] for c in conditions]
    if any(type(h) is not int or h < 1 or b - a - 1 != h
           for a, b, h in zip(starts, stops, horizons, strict=True)):
        raise ValueError('condition is not one complete interval')
    steps = trace['steps']
    if not steps or len(steps) > max(horizons):
        raise ValueError('invalid vector execution length')
    active = [True] * count
    durations = [0] * count
    failure_frames = [None] * count
    remaining_by_step = {}
    partial_steps = 0
    for index, record in enumerate(steps, 1):
        if record['step'] != index or not any(active):
            raise ValueError('skipped step or execution after all attempts retired')
        for key in ('active', 'failed', 'remaining'):
            if len(record[key]) != count or any(type(v) is not bool for v in record[key]):
                raise ValueError('malformed boolean world mask')
        if record['active'] != active:
            raise ValueError('active mask resumed or omitted an attempt')
        verify_transition(record['before'], record['after'], active, starts, stops, index)
        partial_steps += int(any(active) and not all(active))
        for world, live in enumerate(active):
            if live:
                durations[world] += 1
                if record['failed'][world]:
                    failure_frames[world] = record['after'][world]
        active = [live and not record['failed'][i] and index < horizons[i]
                  for i, live in enumerate(active)]
        if record['remaining'] != active:
            raise ValueError('retirement mask differs from failure/horizon rule')
        remaining_by_step[index] = active.copy()
    if any(active):
        raise ValueError('trace ended with an unfinished attempt')
    for key in ('resets', 'reference_writes'):
        for event in trace[key]:
            step = event['step']
            if step not in remaining_by_step or any(
                    type(i) is not int or i < 0 or i >= count for i in event['ids']):
                raise ValueError('invalid reset event')
            permit_reset(event['ids'], remaining_by_step[step])
    summaries = []
    for i, (condition, row) in enumerate(zip(conditions, rows, strict=True)):
        if row['condition_id'] != condition['condition_id']:
            raise ValueError('CSV condition order changed')
        success = failure_frames[i] is None and durations[i] == horizons[i]
        if (abs(float(row['survival_s']) - durations[i] / 50) > 1e-9
                or abs(float(row['actual_window_s']) - horizons[i] / 50) > 1e-9
                or row['success'] != str(int(success))):
            raise ValueError('CSV survival, horizon or success disagrees with retirement')
        if bool(row['termination_causes']) == success:
            raise ValueError('failure cause is absent or attached to successful attempt')
        position = float(row['common_root_relative_mpkpe_m_mean'])
        orientation = float(row['common_anchor_orientation_error_rad_mean'])
        if not np.isfinite([position, orientation]).all() or min(position, orientation) < 0:
            raise ValueError('invalid tracking error')
        # Match the original arithmetic exactly; no changed score or tolerance.
        score = min((durations[i] / 50) / (horizons[i] / 50), 1) * float(
            np.exp(-position / .30 - orientation / .40))
        summaries.append({'condition_id': row['condition_id'], 'horizon_steps': horizons[i],
                          'scored_steps': durations[i], 'success': success,
                          'tracking_score': score, 'failure_frame': failure_frames[i]})
    return {'rows': summaries, 'vector_steps': len(steps),
            'failed_attempts': sum(v is not None for v in failure_frames),
            'completed_attempts': sum(v is None for v in failure_frames),
            'partial_active_steps': partial_steps,
            'retired_reset_events': len(trace['resets']),
            'retired_reference_write_events': len(trace['reference_writes']),
            'active_resets_or_reference_writes': 0}


def verify_run(design_path: Path, design_hash: str, run: Path) -> dict:
    """Authenticate sources, physical-input links, policy and native CSV first."""
    if sha256(design_path) != design_hash:
        raise ValueError('design hash mismatch')
    design = json.loads(design_path.read_text())
    if (design['stage'] != 'continuous_execution_cpu_development'
            or design['full_evaluation_enabled'] is not False
            or design['lookahead_offsets'] != [0]):
        raise ValueError('only current-frame CPU development is supported')
    for path, digest in design['bindings'].items():
        if sha256(Path(path)) != digest:
            raise ValueError(f'bound source/input changed: {path}')
    receipt = json.loads((run / 'receipt.json').read_text())
    if (receipt['design_sha256'] != design_hash
            or receipt['status'] != 'continuous_execution_development_pass'
            or receipt['full_evaluation_enabled'] is not False):
        raise ValueError('wrong development receipt')
    expected_files = {'lifecycle.json', 'policy.pt', 'evaluation.csv', 'evaluation.csv.meta.json'}
    if set(receipt['artifacts']) != expected_files:
        raise ValueError('incomplete development artifact inventory')
    for name, digest in receipt['artifacts'].items():
        if sha256(run / name) != digest:
            raise ValueError(f'artifact changed: {name}')
    args = design['evaluator_arguments']
    metadata = json.loads((run / 'evaluation.csv.meta.json').read_text())
    for name in ('checkpoint', 'clips', 'conditions'):
        if (Path(metadata[name]).resolve() != Path(args[name]).resolve()
                or metadata[name + '_sha256'] != sha256(Path(args[name]))):
            raise ValueError('metadata input link changed')
    if (metadata['device'] != 'cpu' or metadata['task'] != 'Climb-Tracking-Flat-Unitree-G1'
            or Path(metadata['output']).resolve() != (run / 'evaluation.csv').resolve()):
        raise ValueError('metadata execution identity changed')
    if json.loads(Path(args['conditions']).read_text()) != design['conditions']:
        raise ValueError('conditions disagree with design')
    for name, digest in metadata['selected_reference_sha256'].items():
        if sha256(Path(args['bank']) / (name + '.npz')) != digest:
            raise ValueError('reference payload changed')
    if metadata['selected_reference_sha256'] != metadata['common_reference_sha256']:
        raise ValueError('active and common reference differ')
    trace = json.loads((run / 'lifecycle.json').read_text())
    with (run / 'evaluation.csv').open() as handle:
        result = replay_trace(design['conditions']['conditions'], trace, list(csv.DictReader(handle)))
    if result['rows'] != receipt['rows']:
        raise ValueError('receipt score/failure frames do not reproduce exactly')
    policy = torch.load(run / 'policy.pt', map_location='cpu', weights_only=True)
    if verify_policy(policy, result['vector_steps']) != receipt['policy']:
        raise ValueError('policy receipt does not reproduce')
    verify_loaded_actor(policy, Path(args['checkpoint']))
    return dict(result, status='continuous_trace_replay_pass', design_sha256=design_hash,
                receipt_sha256=sha256(run / 'receipt.json'), source_run=str(run),
                verifier_sha256=sha256(Path(__file__)),
                initial_state_sha256=metadata['initial_state_sha256'],
                startup_randomization_sha256=metadata['startup_randomization_sha256'],
                full_evaluation_enabled=False,
                classification='independent CPU development trace replay; no method comparison',
                checked_at=datetime.now().astimezone().isoformat())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--design', type=Path, required=True)
    parser.add_argument('--design-sha256', required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = verify_run(args.design, args.design_sha256, args.run)
    with args.out.open('x') as handle:
        handle.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}))
