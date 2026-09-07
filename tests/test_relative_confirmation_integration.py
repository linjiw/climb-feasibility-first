"""Strict production contracts through analysis on explicitly synthetic outcomes."""

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import analyze_relative_campaign as campaign
from relative_confirmation_fixture import build_strict_campaign
from relative_campaign_fixture import write_json
from relative_confirmation_setup import build_configs, config_digest, fixed_profiles, verify_contract


@pytest.fixture(scope='module')
def strict_campaign(tmp_path_factory):
    return build_strict_campaign(tmp_path_factory.mktemp('SYNTHETIC_strict_campaign'))


def test_full_new_contract_preflight_and_analysis_without_gate_stubs(strict_campaign):
    manifest = json.loads(strict_campaign.read_text())
    bound = manifest['contract']
    contract = verify_contract(Path(bound['path']), bound['sha256'])
    profiles = fixed_profiles(Path(contract['profiles']['path']))
    for arm in ('U', 'A', 'R', 'D'):
        for seed in (21, 22, 23):
            assert config_digest(*build_configs(arm, seed, profiles, contract)) == contract['configuration_sha256'][arm][str(seed)]
    result = campaign.analyze(strict_campaign)
    assert result['status'] == 'positive', result
    assert result['primary_R_minus_U']['mean'] == pytest.approx(0.04)
    assert len(result['manipulation']) == 12
    assert all(len(row['snapshots']) == 41 for row in result['manipulation'].values())
    assert result['quality_and_work_descriptive']['R_minus_U']['21']['common_successes'] == 2800


@pytest.mark.parametrize('damage,expected', [
    ('entrypoint_decision', 'entrypoint smoke: missing or changed artifact'),
    ('entrypoint_sampler', 'entrypoint smoke does not reproduce'),
    ('runtime', 'runtime sources, assets or package versions changed'),
    ('reference_crosslink', 'campaign reference cross-link mismatch'),
    ('configuration', 'training snapshot identity/source/frozen-contract mismatch'),
    ('pairing', 'evaluation pairing mismatch'),
    ('adapter', 'evaluation adapter identity mismatch'),
])
def test_corruption_blocks_outcomes(strict_campaign, tmp_path, monkeypatch, damage, expected):
    manifest = json.loads(strict_campaign.read_text())
    contract = json.loads(Path(manifest['contract']['path']).read_text())
    if damage == 'entrypoint_decision':
        contract['entrypoint_smokes']['D']['sha256'] = '0' * 64
    elif damage == 'entrypoint_sampler':
        entry = contract['entrypoint_smokes']['D']
        result = json.loads(Path(entry['path']).read_text())
        result['completed_trials'] += 1
        contract['entrypoint_smokes']['D'] = write_json(tmp_path / 'corrupt_smoke.json', result)
    elif damage == 'runtime':
        inventory = json.loads(Path(contract['runtime_inventory']['path']).read_text())
        inventory['gpu_identity'] = 'synthetic incorrect identity'
        contract['runtime_inventory'] = write_json(tmp_path / 'corrupt_inventory.json', inventory)
    elif damage == 'reference_crosslink':
        contract['panel_clips'] = deepcopy(contract['training_clips'])
    elif damage == 'configuration':
        run = manifest['arms']['U']['23']
        snapshot = run['snapshots'][-1]
        row = json.loads(Path(snapshot['ledger']['path']).read_text())
        row['configuration_sha256'] = '0' * 64
        snapshot['ledger'] = write_json(tmp_path / 'corrupt_ledger.json', row)
        run['evaluations']['3999']['ledger'] = snapshot['ledger']
    else:
        cell = manifest['arms']['U']['23']['evaluations']['3999']
        metadata = json.loads(Path(cell['metadata']['path']).read_text())
        if damage == 'adapter':
            metadata['execution_adapter']['sha256'] = '0' * 64
        else:
            metadata['initial_state_sha256'] = 'c' * 64
        cell['metadata'] = write_json(tmp_path / 'corrupt_metadata.json', metadata)
    # Contract corruption fails before training-ledger bindings are considered.
    if damage not in ('configuration', 'pairing', 'adapter'):
        manifest['contract'] = write_json(tmp_path / 'corrupt_contract.json', contract)
    path = tmp_path / 'corrupt_manifest.json'
    write_json(path, manifest)
    def unexpected(*args, **kwargs):
        pytest.fail('opened endpoint aggregation before strict preflight completed')
    monkeypatch.setattr(campaign, 'aggregate_rows', unexpected)
    result = campaign.analyze(path)
    assert result['status'] == 'invalid', result
    assert result['policy_endpoints_opened'] is False
    assert expected in result['reason']
