"""Audit existing evidence and freeze all H1 code/configuration before any GPU use."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess

import protocol as p


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    out.mkdir(exist_ok=False)
    draft_path = p.ROOT / 'reports/gate_entrypoint_2026-09-06/preparation/draft_contract.json'
    draft = json.loads(draft_path.read_text())
    if p.legacy.sources() != draft['sources']:
        raise ValueError('archived H1 source inventory changed')
    cpu = []
    for arm in p.ARMS:
        run = p.ROOT / f'reports/gate_entrypoint_2026-09-06/cpu_{arm}/run'
        replay = p.original_verify_training(run, draft, p.file_digest(draft_path), arm, 81, smoke=True)
        if replay != json.loads((run.parent / 'result.json').read_text()):
            raise ValueError('archived CPU smoke does not replay')
        cpu.append(p.record(run.parent / 'result.json'))
    roots = [r / d for r in (p.MAIN, p.ROOT, p.EVIDENCE,
                            Path('/home/linjiw/climb-signal-quality-2026-09-06'))
             for d in ('reports', 'runs', 'logs') if (r / d).exists()]
    regex = r'(?i)(?:["\x27]?(?:seed|sampler_seed|training_seed|env_seed)["\x27]?\s*[:=]\s*|(?:_s|--seed\s+))(?:1041|1042|1043|1044|1045)\b'
    command = ['rg', '--no-ignore', '--hidden', '--line-number', '-g', '*.json', '-g', '*.yaml', '-g', '*.yml', '-g', '*.log', regex, *map(str, roots)]
    scan = subprocess.run(command, capture_output=True, text=True)
    if scan.returncode != 1 or scan.stderr or scan.stdout:
        raise ValueError(f'fresh-seed scan found matches or failed: {scan.stdout[:3000]} {scan.stderr[:1000]}')
    p.dump(out / 'fresh_seed_audit.json', {'status': 'fresh_seed_audit_pass', 'seeds': list(p.SEEDS),
           'scope': 'seed fields, --seed and _s run identities in existing local JSON/YAML/log records; four research worktrees, reports/runs/logs',
           'limitation': 'Does not assert absence from unrecorded or external experiments.',
           'command': command, 'returncode': scan.returncode, 'stdout': scan.stdout, 'stderr': scan.stderr,
           'audited_at': datetime.now(timezone.utc).isoformat()})
    parent_path = p.MAIN / 'reports/relative_progress_2026-09-05/confirmation_freeze/contract.json'
    parent = json.loads(parent_path.read_text())
    bank = parent['bank']
    if isinstance(bank, dict):
        bank = bank['path']
    panel = p.verified(parent['panel_clips'])
    clips = panel.read_text().splitlines()
    conditions = p.verified(parent['conditions'])
    strata_path = p.verified(parent['strata'])
    with strata_path.open() as handle:
        strata = {r['clip']: r['stratum'] for r in csv.DictReader(handle)}
    hard = [i for i, clip in enumerate(clips) if strata[clip] == 'feasible_hard_reference']
    if len(clips) != 100 or len(hard) != 25:
        raise ValueError('original fixed panel changed')
    training = p.verified(draft['training_clips']).read_text().splitlines()
    if set(training) & set(clips):
        raise ValueError('training and evaluation clip names overlap')
    training_hashes = {p.file_digest(Path(bank) / f'{c}.npz') for c in training}
    refs = {c: p.record(Path(bank) / f'{c}.npz') for c in clips}
    if training_hashes & {r['sha256'] for r in refs.values()}:
        raise ValueError('training and evaluation motion hashes overlap')
    eval_args = {'clips': str(panel), 'bank': bank, 'common_reference_bank': bank, 'conditions': str(conditions),
                 'reference_contact_manifest': None, 'contact_validation_report': None,
                 'phases': '0.0,0.16666666666666666,0.3333333333333333,0.5,0.6666666666666666,0.8333333333333334,1.0',
                 'episodes': 4, 'window': 3., 'seed': 20260910, 'joint_noise_seed': 20260911,
                 'joint_noise': .05, 'nconmax': 70, 'nominal': False, 'device': 'cuda:0'}
    contract = {k: draft[k] for k in ('bank', 'support', 'development_support', 'training_clips')}
    contract.update(schema_version='h1_fable_contract/2', status='frozen_before_any_gpu_job',
                    classification='prospective fixed five-paired-seed admission test under D; no H1 policy outcomes yet',
                    frozen_at=datetime.now(timezone.utc).isoformat(), specification=p.SPEC, schedule=p.schedule(),
                    campaign=str(out / 'campaign'), sources=p.sources(), software_versions=p.legacy.software_versions(),
                    fresh_seed_audit=p.record(out / 'fresh_seed_audit.json'),
                    previous_confirmation_terminal=p.record(p.MAIN / 'reports/relative_progress_2026-09-05/confirmation_freeze/campaign_gpu_reentry_2026-09-06/terminal_status.json'),
                    evaluator_arguments=eval_args, hard_indices=hard,
                    mechanism='Equal-weight saved checkpoints 1000..3900 by 100 and 3999: sum positive excess on rejected / sum all positive excess; retain zero-excess as undefined, and record top1 identity and rejection.',
                    inputs={'original_confirmation': p.record(parent_path), 'archived_h1_draft': p.record(draft_path),
                            'panel': p.record(panel), 'conditions': p.record(conditions), 'strata': p.record(strata_path),
                            'cpu_on': cpu[0], 'cpu_off': cpu[1], 'synthetic_tests': p.record(p.ROOT / 'reports/h1_fable_preparation_2026-09-07/tests.json'),
                            **{f'reference:{c}': r for c, r in refs.items()}})
    contract['configuration_sha256'] = {}
    for arm in p.ARMS:
        contract['configuration_sha256'][arm] = {}
        for seed in (81, *p.SEEDS):
            cfg, agent = p.legacy.configs(contract, arm, seed, smoke=seed == 81, digest='prospective')
            contract['configuration_sha256'][arm][str(seed)] = p.legacy.configuration_digest(cfg, agent)
    path = out / 'contract.json'
    p.dump(path, contract)
    p.verify_contract(path, p.file_digest(path), smoke=True)
    entries = {**contract['sources'], str(path): p.file_digest(path),
               str(out / 'fresh_seed_audit.json'): p.file_digest(out / 'fresh_seed_audit.json')}
    entries.update({r['path']: r['sha256'] for r in contract['inputs'].values()})
    with (out / 'H1_FREEZE.sha256').open('x') as handle:
        handle.write(''.join(f'{digest}  {name}\n' for name, digest in sorted(entries.items())))
    print(json.dumps({'status': 'h1_frozen_before_any_gpu_job', 'contract': p.record(path), 'jobs': len(p.schedule()),
                      'source_files': len(contract['sources']), 'hard_clips': len(hard)}))


if __name__ == '__main__':
    main()
