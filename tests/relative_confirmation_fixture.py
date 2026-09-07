"""Construct a strict-contract campaign from synthetic histories, never policies."""

from copy import deepcopy
import json
from pathlib import Path

from relative_campaign_fixture import ROOT, PROFILE, build_campaign, record, write_json, write_run
from relative_confirmation_setup import config_digest, fixed_profiles, runtime_inventory
from run_relative_policy_smokes import verify_smoke
from train_relative_confirmation import smoke_configs, verify_entrypoint_smoke


def build_strict_campaign(base: Path) -> Path:
    """Exercise current production verifiers with real inputs and dummy checkpoints."""
    manifest_path = build_campaign(base)
    manifest = json.loads(manifest_path.read_text())
    legacy = json.loads(Path(manifest['contract']['path']).read_text())
    prepared = ROOT / 'reports/relative_progress_2026-09-05/confirmation_preparation/draft_contract.json'
    draft = json.loads(prepared.read_text())
    draft['classification'] = 'SYNTHETIC TEST FIXTURE ONLY; NEVER LAUNCH'
    # Capture current sources rather than relying on a historical prepared inventory.
    draft['runtime_inventory'] = write_json(base / 'SYNTHETIC_runtime.json', runtime_inventory())
    for group in ('training_sources', 'analysis_sources', 'evaluator_sources'):
        draft[group] = {name: record(Path(value['path'])) for name, value in draft[group].items()}
    for key in ('training_entrypoint', 'evaluator'):
        draft[key] = record(Path(draft[key]['path']))
    draft['evaluator_adapter'] = record(ROOT / 'tools/eval_relative_confirmation.py')
    draft['relative_replication'] = legacy['relative_replication']
    draft['failure_calibration'] = legacy['failure_calibration']
    sources = json.loads((ROOT / 'reports/relative_progress_2026-09-05/policy_smokes_gate_retry/design.json').read_text())['sources']
    sources = {name: record(ROOT / name)['sha256'] for name in sources}
    draft['four_arm_smokes'] = {'design': write_json(base / 'SYNTHETIC_smoke_design.json', {'sources': sources}),
                                'decisions': {}}
    launch_sources = {name: sources[name] for name in ('tools/train_relative_policy.py', 'climb/relative_progress.py',
                      'climb/segment_runtime.py', 'climb/segment_curriculum.py', 'climb/segment_command.py', 'climb/segment_env_cfg.py')}
    for arm in ('U', 'A', 'R', 'D'):
        run = base / f'SYNTHETIC_development_smoke_{arm}'
        write_run(run, arm, 41, 'smoke', PROFILE)
        for path in run.glob('model_*_segment.json'):
            row = json.loads(path.read_text())
            row.update(training_entrypoint_sha256=sources['tools/train_relative_policy.py'],
                       source_hashes_at_launch=launch_sources)
            write_json(path, row)
        result = verify_smoke(run, arm, sources)
        draft['four_arm_smokes']['decisions'][arm] = write_json(base / f'SYNTHETIC_smoke_{arm}.json', result)
    draft['entrypoint_smokes'] = {arm: {'pending_path': str(base / f'SYNTHETIC_entrypoint_{arm}.json')}
                                  for arm in ('U', 'A', 'R', 'D')}
    draft_path = base / 'SYNTHETIC_draft.json'
    draft_record = write_json(draft_path, draft)
    entrypoints = {}
    for arm in ('U', 'A', 'R', 'D'):
        run = base / f'SYNTHETIC_entrypoint_smoke_{arm}'
        write_run(run, arm, 51, 'smoke', PROFILE)
        identity = config_digest(*smoke_configs(arm, fixed_profiles(PROFILE), draft))
        for path in run.glob('model_*_segment.json'):
            row = json.loads(path.read_text())
            row.update(relative_policy_stage='entrypoint_smoke', configuration_sha256=identity,
                       campaign_contract_sha256=draft_record['sha256'],
                       training_entrypoint_sha256=draft['training_entrypoint']['sha256'],
                       source_hashes_at_launch={name: value['sha256'] for name, value in draft['training_sources'].items()})
            write_json(path, row)
        result = verify_entrypoint_smoke(run, draft, draft_record, arm)
        entrypoints[arm] = write_json(base / f'SYNTHETIC_entrypoint_{arm}.json', result)
    contract = deepcopy(draft)
    contract.update(status='frozen_before_confirmation', profiles=legacy['profiles'], entrypoint_smokes=entrypoints)
    contract_record = write_json(base / 'SYNTHETIC_strict_contract.json', contract)
    manifest['contract'] = contract_record
    for arm, seeds in manifest['arms'].items():
        for seed, run in seeds.items():
            ledgers = {}
            for snapshot in run['snapshots']:
                path = Path(snapshot['ledger']['path'])
                row = json.loads(path.read_text())
                row.update(campaign_contract_sha256=contract_record['sha256'],
                           configuration_sha256=contract['configuration_sha256'][arm][seed],
                           training_entrypoint_sha256=contract['training_entrypoint']['sha256'],
                           source_hashes_at_launch={name: value['sha256'] for name, value in contract['training_sources'].items()})
                snapshot['ledger'] = write_json(path, row)
                ledgers[str(row['iteration'])] = snapshot['ledger']
            for iteration, cell in run['evaluations'].items():
                cell['ledger'] = ledgers[iteration]
                path = Path(cell['metadata']['path'])
                metadata = json.loads(path.read_text())
                from eval_relative_confirmation import adapter_record
                metadata.update(execution_adapter=adapter_record(), software_versions=contract['software_versions'],
                                source_sha256={name: value['sha256'] for name, value in contract['evaluator_sources'].items()})
                cell['metadata'] = write_json(path, metadata)
    path = base / 'SYNTHETIC_strict_manifest.json'
    write_json(path, manifest)
    return path
