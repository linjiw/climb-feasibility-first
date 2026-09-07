"""Reject incomplete/tampered H1 training records; fixtures are not policy evidence."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
from climb.gate_ablation import file_digest
from gate_study_setup import canonical, configs, verify_contract
from gate_training_provenance import scheduled_iterations, verify_training

ARTIFACTS = ROOT / 'reports/gate_entrypoint_2026-09-06'
CONTRACT_PATH = ARTIFACTS / 'preparation/draft_contract.json'
CONTRACT = json.loads(CONTRACT_PATH.read_text())
DIGEST = file_digest(CONTRACT_PATH)


def write(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


def replay(run):
    return verify_training(run, CONTRACT, DIGEST, 'on', 81, smoke=True)


@pytest.fixture
def run(tmp_path):
    target = tmp_path / 'cpu_on'
    shutil.copytree(ARTIFACTS / 'cpu_on', target)
    return target / 'run'


def test_actual_cpu_smoke_replays():
    run = ARTIFACTS / 'cpu_on/run'
    assert replay(run) == json.loads((run.parent / 'result.json').read_text())


def test_draft_rejects_full_training():
    with pytest.raises(ValueError, match='frozen contract'):
        verify_contract(CONTRACT_PATH, DIGEST, smoke=False)


def test_full_configuration_parity():
    values = []
    for arm in ('on', 'off'):
        cfg, agent = configs(CONTRACT, arm, 61, smoke=False, digest=DIGEST)
        assert cfg.scene.num_envs == 512 and agent.max_iterations == 4000
        cfg, agent = canonical(cfg), canonical(agent)
        for name in ('segment_manifest', 'gate_manifest_sha256', 'gate_admission'):
            del cfg['fields']['commands']['motion']['fields'][name]
        del agent['fields']['run_name']
        values.append((cfg, agent))
    assert values[0] == values[1]


def test_missing_initial_checkpoint_rejected(run):
    (run / 'model_0_gate.json').unlink()
    with pytest.raises(ValueError, match='scheduled checkpoint'):
        replay(run)


def test_tampered_checkpoint_rejected(run):
    with (run / 'model_0.pt').open('ab') as f:
        f.write(b'tampered')
    with pytest.raises(ValueError, match='file changed'):
        replay(run)


@pytest.mark.parametrize('field', ['invalid_start_count', 'invalid_reference_frame_count', 'censored_resets'])
def test_nonfinal_invalid_events_rejected(run, field):
    path = run / 'model_0_gate.json'
    row = json.loads(path.read_text()); row['segment'][field] = 1; write(path, row)
    with pytest.raises(ValueError, match='invalid or censored'):
        replay(run)


def test_wrong_sampler_clock_rejected(run):
    path = run / 'model_0_gate.json'
    row = json.loads(path.read_text()); row['segment']['sampler_clock'] += 1; write(path, row)
    with pytest.raises(ValueError, match='sampler clock'):
        replay(run)


def test_changed_support_rejected(tmp_path):
    contract = deepcopy(CONTRACT)
    path = tmp_path / 'support.json'
    path.write_text('{}')
    contract['support']['on']['path'] = str(path)
    with pytest.raises(ValueError, match='changed bound artifact'):
        configs(contract, 'on', 81, smoke=True, digest=DIGEST)


def test_synthetic_full_checkpoint_schedule(tmp_path, monkeypatch):
    # Expand measured snapshot tensors into a fabricated 41-save history. This
    # exercises verification coverage only and cannot authorize an actual launch.
    import gate_training_provenance as provenance
    target = tmp_path / 'SYNTHETIC'
    shutil.copytree(ARTIFACTS / 'cpu_on', target)
    run = target / 'run'
    base = json.loads((run / 'model_19_gate.json').read_text())
    model = torch.load(run / 'model_19.pt', map_location='cpu', weights_only=False)
    state = torch.load(run / 'model_19_sampler.pt', map_location='cpu', weights_only=True)
    for path in run.glob('model_*'):
        path.unlink()
    cfg, agent = configs(CONTRACT, 'on', 81, smoke=True, digest=DIGEST)
    agent.max_iterations = 4000
    monkeypatch.setattr(provenance, 'configs', lambda *args, **kwargs: (cfg, agent))
    identity = {'smoke': False, 'configuration_sha256': provenance.configuration_digest(cfg, agent)}
    for name in ('design.json', 'execution.json'):
        path = target / name; row = json.loads(path.read_text())
        row.update(identity, device='cuda:0'); write(path, row)
    for iteration in scheduled_iterations(False):
        steps = 24*(iteration+1)
        model['iter'] = iteration
        model['infos']['env_state']['common_step_counter'] = steps
        state['clock'] = steps//50
        checkpoint = run / f'model_{iteration}.pt'; sampler = run / f'model_{iteration}_sampler.pt'
        torch.save(model, checkpoint); torch.save(state, sampler)
        row = deepcopy(base)
        row.update(identity, iteration=iteration, common_step_counter=steps,
                   checkpoint_sha256=file_digest(checkpoint), sampler_sha256=file_digest(sampler))
        row['segment']['sampler_clock'] = steps//50
        row['segment']['gate_ablation'].update(full_training_enabled=True, stage='confirmation')
        write(run / f'model_{iteration}_gate.json', row)
    result = provenance.verify_training(run, CONTRACT, DIGEST, 'on', 81, smoke=False)
    assert len(result['checkpoints']) == 41
    (run / 'model_1700_gate.json').unlink()
    with pytest.raises(ValueError, match='scheduled checkpoint'):
        provenance.verify_training(run, CONTRACT, DIGEST, 'on', 81, smoke=False)
