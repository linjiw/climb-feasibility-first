"""The continuation must not launch through failed or altered seed-1 evidence."""

import importlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
runner = importlib.import_module("run_e4_confirmation")


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "OUT", tmp_path)
    monkeypatch.setattr(runner, "verify_seal", lambda: None)
    monkeypatch.setattr(sys, "argv", ["run_e4_confirmation.py"])
    monkeypatch.setattr(runner, "run_dir", lambda seed, arm: tmp_path / arm)
    launched = []
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: launched.append(a))
    return tmp_path, launched


def test_missing_seed1_result_launches_nothing(isolated):
    _, launched = isolated
    with pytest.raises(ValueError, match="absent"):
        runner.main()
    assert not launched


def test_failed_seed1_stops_without_training_or_evaluation(isolated, monkeypatch):
    out, launched = isolated
    result = {"status": "not_tested", "policy_endpoints_opened": False}
    runner.write_once(out / "seed1/manipulation_result.json", result)
    monkeypatch.setattr(runner, "evaluate", lambda *args: result)
    assert runner.main() == 2
    assert not launched


def test_changed_seed1_evidence_rejected(isolated, monkeypatch):
    out, launched = isolated
    runner.write_once(out / "seed1/manipulation_result.json", {"status": "pass_for_evaluation"})
    monkeypatch.setattr(runner, "evaluate", lambda *args: {"status": "not_tested"})
    with pytest.raises(ValueError, match="differs"):
        runner.main()
    assert not launched


def test_failed_all_seed_gate_keeps_endpoints_closed(isolated, monkeypatch):
    out, launched = isolated
    passing = {"status": "pass_for_evaluation", "policy_endpoints_opened": False}
    runner.write_once(out / "seed1/manipulation_result.json", passing)
    monkeypatch.setattr(runner, "evaluate", lambda *args: passing)
    training = []
    monkeypatch.setattr(runner, "gated", lambda command, log, seed: training.append(command))
    monkeypatch.setattr(runner, "collect_run", lambda *args: ({"ledgers": []}, {}))
    monkeypatch.setattr(runner, "manipulation_gate", lambda manifest: {"pass": False})
    assert runner.main() == 2
    assert len(training) == 4
    assert all("tools/climb_segment_train.py" in command for command in training)
    result = json.loads((out / "manipulation_all_seeds.json").read_text())
    assert result["status"] == "not_tested"
    assert result["policy_endpoints_opened"] is False


def test_result_rewrite_rejected(tmp_path):
    path = tmp_path / "result.json"
    runner.write_once(path, {"status": "not_tested"})
    with pytest.raises(ValueError, match="overwrite"):
        runner.write_once(path, {"status": "pass_for_evaluation"})


def test_passed_gate_builds_all_cells_with_common_reference(isolated, monkeypatch):
    out, _ = isolated
    passing = {"status": "pass_for_evaluation", "policy_endpoints_opened": False}
    runner.write_once(out / "seed1/manipulation_result.json", passing)
    monkeypatch.setattr(runner, "evaluate", lambda *args: passing)
    commands = []
    monkeypatch.setattr(runner, "gated", lambda command, log, seed: commands.append(command))
    monkeypatch.setattr(runner, "collect_run", lambda *args: ({"ledgers": []}, {}))
    monkeypatch.setattr(runner, "manipulation_gate", lambda manifest: {"pass": True})
    monkeypatch.setattr(runner, "build_manifest", lambda *args: {})
    assert runner.main() == 0
    evaluations = [c for c in commands if "tools/eval_paired_v2.py" in c]
    assert len(evaluations) == 24
    for command in evaluations:
        bank = command[command.index("--bank") + 1]
        common = command[command.index("--common-reference-bank") + 1]
        assert bank == common
        assert command[command.index("--episodes") + 1] == "4"
        assert command[command.index("--seed") + 1] == "20260910"
