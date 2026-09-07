#!/usr/bin/env python3
"""Prepare disabled H1 launch bindings; this tool cannot freeze or launch H1."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from gate_study_setup import ARMS, SEEDS, SPEC, configuration_digest, configs, record, sources
from climb.gate_study import PROTOCOL
from eval_paired_v2 import software_versions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--development-root', type=Path, required=True)
    parser.add_argument('--clips', type=Path, required=True)
    parser.add_argument('--bank', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    contract = {'schema_version': 'gate_study_contract/1', 'status': 'draft', 'full_training_enabled': False,
        'classification': 'prospective development entrypoint; full H1 pending', 'specification': SPEC,
        'training_clips': record(args.clips), 'bank': str(args.bank.resolve()), 'support': {},
        'development_support': {}, 'sources': sources(), 'software_versions': software_versions(),
        'configuration_sha256': {}, 'development_smoke_pair': record(args.development_root / 'paired_smoke_result.json'),
        'pending': ['previous confirmation completed and declared decision recorded', 'fresh seed audit',
                    'GPU entrypoint smokes', 'paired evaluation and analysis adapters',
                    'prospective full-study freeze and training-before-evaluation scheduler']}
    for arm in ARMS:
        old = args.development_root / 'manifests' / f'gate_{arm}.json'
        contract['development_support'][arm] = record(old)
        value = json.loads(old.read_text())
        value['gate_ablation'].pop('full_training_enabled')
        value['gate_ablation'].update(protocol=PROTOCOL, requires_frozen_launch_contract=True)
        path = out / f'gate_{arm}.json'
        path.write_text(json.dumps(value, indent=2)+'\n')
        contract['support'][arm] = record(path)
        contract['configuration_sha256'][arm] = {}
        for seed in SEEDS:
            cfg, agent = configs(contract, arm, seed, smoke=False, digest='0'*64)
            contract['configuration_sha256'][arm][str(seed)] = configuration_digest(cfg, agent)
    path = out / 'draft_contract.json'
    path.write_text(json.dumps(contract, indent=2)+'\n')
    print(json.dumps(record(path)))


if __name__ == '__main__':
    main()
