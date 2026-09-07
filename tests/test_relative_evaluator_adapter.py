"""Keep sealed condition payloads exact while accepting their bound provenance."""

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import eval_relative_confirmation as adapter
import eval_paired_v2 as sealed


def arguments():
    saved = json.loads(adapter.CONDITIONS.read_text())
    return (saved['motions'], saved['requested_phases'], saved['episodes_per_start'], saved['window_s'],
            saved['environment_seed'], saved['joint_noise_seed'], saved['joint_noise'], saved['nominal'],
            saved['nconmax_per_world'])


def test_sealed_loader_reproduces_original_blocker():
    with pytest.raises(ValueError, match='existing condition manifest differs'):
        sealed.load_or_create_manifest(adapter.CONDITIONS, *arguments())


def test_adapter_validates_exact_payload_without_rewriting():
    before = adapter.CONDITIONS.read_bytes()
    result = adapter.load_sealed_conditions(adapter.CONDITIONS, *arguments())
    assert len(result['conditions']) == 2800
    assert result['panel_txt_sha256'] == adapter.sha256(adapter.PANEL)
    assert adapter.CONDITIONS.read_bytes() == before


@pytest.mark.parametrize('index,value', [(2, 8), (3, 2.0), (4, 20260912), (6, 0.1), (7, True), (8, 71)])
def test_changed_requested_condition_cannot_pass(index, value):
    args = list(arguments())
    args[index] = value
    with pytest.raises(ValueError, match='payload or provenance differs'):
        adapter.load_sealed_conditions(adapter.CONDITIONS, *args)


def test_other_condition_file_cannot_substitute(tmp_path):
    path = tmp_path / 'copy.json'
    path.write_bytes(adapter.CONDITIONS.read_bytes())
    with pytest.raises(ValueError, match='unchanged sealed'):
        adapter.load_sealed_conditions(path, *arguments())


def test_adapter_records_identity_after_stub_rollout_and_restores_loader(tmp_path, monkeypatch):
    output = tmp_path / 'synthetic.csv'
    metadata = output.with_suffix('.csv.meta.json')
    original = sealed.load_or_create_manifest
    def fake_rollout():
        assert sealed.load_or_create_manifest is adapter.load_sealed_conditions
        output.write_text('SYNTHETIC ONLY\n')
        metadata.write_text(json.dumps({'evaluator_sha256': adapter.sha256(Path(sealed.__file__))}))
        return 0
    monkeypatch.setattr(sealed, 'main', fake_rollout)
    monkeypatch.setattr(sys, 'argv', ['adapter', '--out', str(output)])
    assert adapter.main() == 0
    assert sealed.load_or_create_manifest is original
    result = json.loads(metadata.read_text())
    assert result['execution_adapter'] == adapter.adapter_record()
    assert result['evaluator_sha256'] == adapter.sha256(Path(sealed.__file__))


def test_failed_rollout_restores_loader_and_does_not_write_metadata(tmp_path, monkeypatch):
    original = sealed.load_or_create_manifest
    def fail():
        raise RuntimeError('synthetic rollout failure')
    monkeypatch.setattr(sealed, 'main', fail)
    monkeypatch.setattr(sys, 'argv', ['adapter', '--out', str(tmp_path / 'absent.csv')])
    with pytest.raises(RuntimeError, match='synthetic rollout failure'):
        adapter.main()
    assert sealed.load_or_create_manifest is original
    assert list(tmp_path.iterdir()) == []
