"""Prospective five-pair H1, independent of the archived three-seed draft."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
MAIN = Path('/home/linjiw/climb-feasibility-first')
EVIDENCE = Path('/home/linjiw/climb-icra-evidence-2026-09-06')
PYTHON = MAIN / 'mjlab-1.6.0/.venv/bin/python'
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT), str(EVIDENCE / 'tools')]
import gate_study_setup as legacy
from climb.gate_ablation import file_digest, sampler_for
from climb.gate_study import verify_support
from gate_training_provenance import verify_training as original_verify_training

SEEDS = (1041, 1042, 1043, 1044, 1045)
ARMS = ('on', 'off')
CHECKPOINTS = (1000, 2000, 3000, 3999)
legacy.SEEDS = SEEDS  # Process-local adapter; archived source bytes remain unchanged.
record, verified = legacy.record, legacy.verified
SPEC = {**legacy.SPEC, 'seeds': list(SEEDS), 'benefit_target': None,
        'nonregression_margin': None, 'reference_effect': .02,
        'decision': 'final hard on-minus-off paired seed two-sided t95: lower>0 positive; upper<0 negative; otherwise inconclusive',
        'all_panel': 'descriptive interval, no pass/fail guard',
        'bootstrap_seed': 20260907, 'bootstrap_draws': 10000,
        'postwarmup_first_checkpoint': 1000, 'minimum_off_rejected_mass': .0923,
        'resource_gate': {'free_mib': 14000, 'max_utilization_percent': 60, 'wait_seconds': 7200},
        'launch_cutoff': '2026-09-08T22:00:00-04:00',
        'training_cutoff': '2026-09-11T12:00:00-04:00',
        'evidence_cutoff': '2026-09-12T23:59:59-04:00',
        'attempts_per_job': 1, 'all_training_before_evaluation': True}


def dump(path: Path, value: dict) -> None:
    with path.open('x') as handle:
        handle.write(json.dumps(value, indent=2, allow_nan=False) + '\n')


def sources() -> dict:
    inventory = legacy.sources()
    extra = list((ROOT / 'paper/h1').glob('*.py'))
    extra += list((EVIDENCE / 'tools').glob('*.py')) + list((EVIDENCE / 'climb').rglob('*.py'))
    inventory.update({str(p.resolve()): file_digest(p) for p in extra})
    return dict(sorted(inventory.items()))


def schedule() -> list[dict]:
    jobs = [{'stage': 'smoke', 'arm': a, 'seed': 81} for a in ARMS]
    for index, seed in enumerate(SEEDS):
        jobs.extend({'stage': 'train', 'arm': a, 'seed': seed}
                    for a in (ARMS if index % 2 == 0 else ARMS[::-1]))
    jobs.extend({'stage': 'evaluate', 'arm': a, 'seed': s, 'iteration': i}
                for s in SEEDS for a in ARMS for i in CHECKPOINTS)
    for job in jobs:
        job['id'] = f"{job['stage']}_{job['arm']}_s{job['seed']}" + (
            f"_i{job['iteration']}" if 'iteration' in job else '')
    return jobs


def verify_contract(path: Path, digest: str, *, smoke: bool) -> dict:
    value = json.loads(verified({'path': str(path), 'sha256': digest}).read_text())
    if (value['schema_version'] != 'h1_fable_contract/2' or value['status'] != 'frozen_before_any_gpu_job'
            or value['specification'] != SPEC or value['schedule'] != schedule()
            or value['sources'] != sources() or value['software_versions'] != legacy.software_versions()):
        raise ValueError('H1 contract, source inventory, software or schedule changed')
    for artifact in value['inputs'].values():
        verified(artifact)
    terminal = json.loads(verified(value['previous_confirmation_terminal']).read_text())
    audit = json.loads(verified(value['fresh_seed_audit']).read_text())
    if terminal['status'] != 'completed' or audit['status'] != 'fresh_seed_audit_pass' or audit['seeds'] != list(SEEDS):
        raise ValueError('confirmation unresolved or fresh seeds not audited')
    for arm in ARMS:
        support = verify_support(verified(value['support'][arm]), value['support'][arm]['sha256'], arm)
        development = json.loads(verified(value['development_support'][arm]).read_text())
        if any(support[k] != development[k] for k in ('sources', 'source_units', 'admissible_units', 'unit_table_sha256', 'horizon_steps')):
            raise ValueError('support changed from validated candidate partition')
        for seed in (81, *SEEDS):
            cfg, agent = legacy.configs(value, arm, seed, smoke=seed == 81, digest=digest)
            if legacy.configuration_digest(cfg, agent) != value['configuration_sha256'][arm][str(seed)]:
                raise ValueError('configuration differs from prospective binding')
    if not smoke:
        checked = []
        for arm in ARMS:
            out = Path(value['campaign']) / f'smoke_{arm}_s81'
            replay = verify_training(out / 'run', value, digest, arm, 81, smoke=True)
            if replay != json.loads((out / 'result.json').read_text()) or replay['device'] != 'cuda:0':
                raise ValueError('both GPU entrypoint smokes must replay before full training')
            checked.append(replay)
        if checked[0]['initial_actor'] != checked[1]['initial_actor']:
            raise ValueError('GPU smoke initial actors differ')
    return value


def verify_training(run: Path, contract: dict, digest: str, arm: str, seed: int, *, smoke: bool) -> dict:
    import torch
    value = original_verify_training(run, contract, digest, arm, seed, smoke=smoke)
    sampler = sampler_for(Path(contract['support'][arm]['path']), seed)
    units = sampler.manifest['admissible_units']
    rejected = torch.tensor([not u['gate_admitted'] for u in units])
    base = sampler.deployment_mass.double() / sampler.deployment_mass.sum()
    mechanism = []

    def finite(item):
        if isinstance(item, torch.Tensor) and not torch.isfinite(item).all():
            raise ValueError('nonfinite checkpoint tensor')
        if isinstance(item, dict):
            for child in item.values():
                finite(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                finite(child)

    for row in value['checkpoints']:
        finite(torch.load(row['checkpoint']['path'], map_location='cpu', weights_only=False))
        sampler.load_state_dict(torch.load(row['sampler']['path'], map_location='cpu', weights_only=True))
        if arm == 'off' and float(sampler.probabilities[rejected].sum()) < .0923 - 1e-12:
            raise ValueError('off rejected mass below frozen minimum')
        if row['iteration'] >= SPEC['postwarmup_first_checkpoint']:
            extra = (sampler.probabilities - base).clamp_min(0)
            total = float(extra.sum())
            top = int(sampler.probabilities.argmax())
            mechanism.append({'iteration': row['iteration'], 'positive_excess_total': total,
                              'positive_excess_rejected': float(extra[rejected].sum()),
                              'rejected_share_of_positive_excess': float(extra[rejected].sum()) / total if total else None,
                              'top1_table_index': top, 'top1_unit': units[top],
                              'top1_rejected': bool(rejected[top]), 'top1_probability': float(sampler.probabilities[top])})
    value['mechanism'] = mechanism
    value['all_saved_checkpoint_tensors_finite'] = True
    return value


def all_training(contract: dict, digest: str) -> dict:
    checked = {}
    for job in schedule()[2:12]:
        arm, seed = job['arm'], job['seed']
        out = Path(contract['campaign']) / job['id']
        value = verify_training(out / 'run', contract, digest, arm, seed, smoke=False)
        if value != json.loads((out / 'result.json').read_text()) or value['transitions'] != 49152000:
            raise ValueError('training result does not replay at the full budget')
        checked[(arm, seed)] = value
    for seed in SEEDS:
        if checked[('on', seed)]['initial_actor'] != checked[('off', seed)]['initial_actor']:
            raise ValueError('training initial actors are not paired')
    return checked


def analyze(scores: dict, hard) -> dict:
    import numpy as np
    from scipy.stats import t
    if set(scores) != set(ARMS) or any(v.shape != (5, 100) or not np.isfinite(v).all()
                                       or ((v < 0) | (v > 1)).any() for v in scores.values()):
        raise ValueError('requires complete finite five-seed, 100-clip scores')
    hard = np.asarray(hard)
    if hard.shape != (25,) or hard.dtype.kind not in 'iu' or len(set(hard.tolist())) != 25 or ((hard < 0) | (hard >= 100)).any():
        raise ValueError('requires exactly 25 fixed hard clips')
    delta = scores['on'] - scores['off']

    def summary(panel):
        paired = panel.mean(axis=1)
        mean, sd = float(paired.mean()), float(paired.std(ddof=1))
        half = float(t.ppf(.975, 4) * sd / np.sqrt(5))
        rng = np.random.default_rng(SPEC['bootstrap_seed'])
        seeds = rng.integers(0, 5, (10000, 5))
        clips = rng.integers(0, panel.shape[1], (10000, panel.shape[1]))
        boot = panel[seeds[:, :, None], clips[:, None, :]].mean(axis=(1, 2))
        return {'paired_seed_deltas': dict(zip(map(str, SEEDS), paired.tolist())), 'mean': mean,
                'seed_t_95ci': [mean-half, mean+half], 'sd_across_seeds': sd, 'independent_units': 5,
                'df': 4, 'supplementary_paired_seed_clip_bootstrap_95ci': np.quantile(boot, [.025, .975]).tolist()}
    primary = summary(delta[:, hard])
    lo, hi = primary['seed_t_95ci']
    return {'status': 'positive' if lo > 0 else 'negative' if hi < 0 else 'inconclusive',
            'primary_on_minus_off': primary, 'all_panel_on_minus_off': summary(delta),
            'reference_effect': .02, 'all_panel_pass_fail_guard': None}
