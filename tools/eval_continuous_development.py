#!/usr/bin/env python3
"""Run a bound CPU full-interval continuity smoke without confirmation policies."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import csv
import json
import os
from pathlib import Path
import sys

import numpy as np
import torch

from audit_policy_immutability import observe_policy
from continuous_execution_support import legal_starts, permit_reset, verify_transition
from eval_gate_development import verify_loaded_actor
from eval_natural_lifecycle import verify_policy
from eval_physics_development import sha256


@contextmanager
def continuity_guard(design: dict, payload: dict):
    import mjlab.envs
    original = mjlab.envs.ManagerBasedRlEnv
    conditions = design['conditions']['conditions']
    payload.update(steps=[], resets=[], reference_writes=[])

    class Environment(original):
        def __init__(self, *, cfg, device):
            self._continuous_step = 0
            cfg.episode_length_s = max(cfg.episode_length_s, design['max_horizon_steps'] / 50 + 1)
            super().__init__(cfg=cfg, device=device)
            if cfg.auto_reset or abs(self.step_dt - .02) > 1e-9:
                raise ValueError('continuous evaluation requires explicit retirement at 50 Hz')
            self._continuous_active = [True] * self.num_envs
            self._continuous_starts = [r['start_frame'] for r in conditions]
            self._continuous_stops = [r['support_stop'] for r in conditions]
            self._continuous_horizons = [r['horizon_steps'] for r in conditions]
            cmd = self.command_manager.get_term('motion')
            write_reference = cmd._write_reference_state_to_sim

            def write(env_ids, *args, **kwargs):
                ids = env_ids.cpu().tolist()
                if self._continuous_step:
                    permit_reset(ids, self._continuous_active)
                    payload['reference_writes'].append({'step': self._continuous_step, 'ids': ids})
                return write_reference(env_ids, *args, **kwargs)

            cmd._write_reference_state_to_sim = write

        def reset(self, *, seed=None, env_ids=None, options=None):
            if self._continuous_step:
                ids = list(range(self.num_envs)) if env_ids is None else env_ids.cpu().tolist()
                permit_reset(ids, self._continuous_active)
                payload['resets'].append({'step': self._continuous_step, 'ids': ids})
            return super().reset(seed=seed, env_ids=env_ids, options=options)

        def step(self, action):
            self._continuous_step += 1
            cmd = self.command_manager.get_term('motion')
            clip_ids = cmd.clip_ids.clone()
            before = (cmd.time_steps - cmd.motion.clip_start[clip_ids]).cpu().tolist()
            active = self._continuous_active.copy()
            result = super().step(action)
            after = (cmd.time_steps - cmd.motion.clip_start[clip_ids]).cpu().tolist()
            if any(live and int(cmd.clip_ids[i]) != int(clip_ids[i]) for i, live in enumerate(active)):
                raise ValueError('active motion identity changed')
            verify_transition(before, after, active, self._continuous_starts,
                              self._continuous_stops, self._continuous_step)
            failed = self.termination_manager.terminated.cpu().tolist()
            timed_out = self.termination_manager.time_outs.cpu().tolist()
            for i, live in enumerate(active):
                if live and timed_out[i] and self._continuous_step < self._continuous_horizons[i]:
                    raise ValueError('unexpected timeout before continuous sequence end')
            self._continuous_active = [live and not failed[i] and self._continuous_step < self._continuous_horizons[i]
                                       for i, live in enumerate(active)]
            payload['steps'].append({'step': self._continuous_step, 'active': active, 'before': before,
                                     'after': after, 'failed': failed, 'remaining': self._continuous_active.copy()})
            return result

    mjlab.envs.ManagerBasedRlEnv = Environment
    try:
        yield
    finally:
        mjlab.envs.ManagerBasedRlEnv = original


def run(design_path: Path, digest: str, out: Path) -> dict:
    if sha256(design_path) != digest:
        raise ValueError('development design changed')
    design = json.loads(design_path.read_text())
    if (design['stage'] != 'continuous_execution_cpu_development'
            or design['full_evaluation_enabled'] is not False or design['lookahead_offsets'] != [0]):
        raise ValueError('only the bound current-frame CPU development adapter is enabled')
    for name, expected in design['bindings'].items():
        if sha256(Path(name)) != expected:
            raise ValueError(f'bound input/source changed: {name}')
    root = Path(design['root'])
    sys.path[:0] = [str(root / 'tools'), str(root)]
    import eval_paired_v2 as original
    args = argparse.Namespace(**design['evaluator_arguments'])
    for name in ('checkpoint', 'clips', 'bank', 'common_reference_bank', 'conditions'):
        setattr(args, name, Path(getattr(args, name)))
    if set(args.clips.read_text().splitlines()) & set(Path(design['heldout_clip_list']).read_text().splitlines()):
        raise ValueError('development references overlap held-out clips')
    table = json.loads(Path(design['unit_table']).read_text())
    admitted = {u['unit_id']: u for u in table['admissible_units']}
    for row in design['conditions']['conditions']:
        unit = admitted[row['unit_id']]
        if (unit['clip'] != row['clip'] or row['support_stop'] != unit['segment_stop']
                or row['start_frame'] != unit['segment_start']
                or row['horizon_steps'] != unit['segment_stop'] - unit['segment_start'] - 1
                or row['start_frame'] not in legal_starts(unit['segment_start'], unit['segment_stop'], row['horizon_steps'])):
            raise ValueError('continuous condition is not one complete admitted interval')
    # The unchanged evaluator's standard manifest is fixed-window. This separate
    # adapter supplies authenticated per-interval horizons without splicing files.
    previous_loader = original.load_or_create_manifest
    def load_conditions(path, metadata, phases, episodes, window, seed, noise_seed, noise, nominal, nconmax):
        manifest = json.loads(path.read_text())
        if manifest != design['conditions'] or metadata != manifest['motions']:
            raise ValueError('continuous condition identity or reference timeline changed')
        expected = [manifest[k] for k in ('requested_phases', 'episodes_per_start', 'window_s', 'environment_seed', 'joint_noise_seed', 'joint_noise', 'nominal', 'nconmax_per_world')]
        if [phases, episodes, window, seed, noise_seed, noise, nominal, nconmax] != expected:
            raise ValueError('continuous evaluator arguments differ from conditions')
        return manifest
    out.mkdir(parents=True, exist_ok=False)
    args.out = out / 'evaluation.csv'
    policy, lifecycle = {}, {}
    original.load_or_create_manifest = load_conditions
    try:
        with observe_policy(policy), continuity_guard(design, lifecycle):
            if original.evaluate(args):
                raise ValueError('continuous evaluator failed')
    finally:
        original.load_or_create_manifest = previous_loader
    verified_policy = verify_policy(policy, len(lifecycle['steps']))
    verify_loaded_actor(policy, args.checkpoint)
    rows = list(csv.DictReader(args.out.open()))
    conditions = design['conditions']['conditions']
    if len(rows) != len(conditions):
        raise ValueError('incomplete continuous evaluation')
    summaries = []
    for index, (row, condition) in enumerate(zip(rows, conditions, strict=True)):
        if row['condition_id'] != condition['condition_id']:
            raise ValueError('condition order changed')
        scored = [r for r in lifecycle['steps'] if r['active'][index]]
        survival = len(scored) / 50
        horizon = condition['horizon_steps'] / 50
        success = len(scored) == condition['horizon_steps'] and not scored[-1]['failed'][index]
        if (abs(float(row['survival_s']) - survival) > 1e-6 or int(row['success']) != success
                or abs(float(row['actual_window_s']) - horizon) > 1e-6):
            raise ValueError('native score accounting differs from continuity trace')
        position = float(row['common_root_relative_mpkpe_m_mean'])
        orientation = float(row['common_anchor_orientation_error_rad_mean'])
        if not np.isfinite([position, orientation]).all() or min(position, orientation) < 0:
            raise ValueError('invalid tracking metric')
        score = min(survival / horizon, 1) * float(np.exp(-position/.30-orientation/.40))
        summaries.append({'condition_id': row['condition_id'], 'horizon_steps': condition['horizon_steps'],
                          'scored_steps': len(scored), 'success': success, 'tracking_score': score,
                          'failure_frame': None if success else scored[-1]['after'][index]})
    (out / 'lifecycle.json').write_text(json.dumps(lifecycle, indent=2)+'\n')
    torch.save(policy, out / 'policy.pt')
    receipt = {'status': 'continuous_execution_development_pass', 'classification': 'measured CPU continuity on two training references; no method comparison',
               'design_sha256': digest, 'policy': verified_policy, 'rows': summaries,
               'active_resets_or_reference_writes': 0, 'full_evaluation_enabled': False,
               'confirmation_policy_outcomes_read': False,
               'artifacts': {p.name: sha256(p) for p in out.iterdir() if p.is_file()}}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    return receipt


if __name__ == '__main__':
    os.environ.update(CUDA_VISIBLE_DEVICES='', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', WANDB_MODE='offline', MUJOCO_GL='egl')
    torch.set_num_threads(1)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--design', type=Path, required=True)
    parser.add_argument('--design-sha256', required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.design, args.design_sha256, args.out_dir)))
