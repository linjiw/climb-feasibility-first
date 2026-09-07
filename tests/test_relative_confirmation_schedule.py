"""Prospective orchestration never evaluates a partially validated training panel."""

import json
from itertools import chain, repeat
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import run_relative_confirmation as runner
from analyze_relative_cost import execution_cost


@pytest.fixture
def contract():
    return {"conditions": {"path": str(ROOT / "reports/g_segment/eval_conditions.json")},
            "panel_clips": {"path": str(ROOT / "reports/g_segment/panel/panel.txt")}, "bank": str(ROOT / "bank/amass")}


def test_fixed_schedule_has_full_training_before_all_evaluations(contract, tmp_path):
    jobs = runner.schedule(contract, tmp_path / "contract.json", "synthetic", tmp_path)
    assert len(jobs) == 60
    assert [job["stage"] for job in jobs] == ["train"] * 12 + ["evaluate"] * 48
    assert len({(job["arm"], job["seed"]) for job in jobs[:12]}) == 12
    assert len({(job["arm"], job["seed"], job["iteration"]) for job in jobs[12:]}) == 48
    conditions = json.loads(Path(contract["conditions"]["path"]).read_text())
    for job in jobs[12:]:
        args = job["argv"]
        for flag, value in (("--seed", conditions["environment_seed"]),
                            ("--joint-noise-seed", conditions["joint_noise_seed"]),
                            ("--episodes", conditions["episodes_per_start"]), ("--window", 3.0)):
            assert args[args.index(flag) + 1] == str(value)


@pytest.fixture
def orchestrator(contract, tmp_path, monkeypatch):
    """Stub child execution only; actual evidence verifiers have separate tests."""
    path = tmp_path / "contract.json"
    path.write_text("{}")
    calls = []
    monkeypatch.setattr(runner, "verify_contract", lambda *args: contract)
    monkeypatch.setattr(runner, "record", lambda path: {"path": str(path), "sha256": "synthetic"})
    monkeypatch.setattr(runner, "training_record", lambda job: {"snapshots": [], "evaluations": {}})
    monkeypatch.setattr(runner, "verify_training", lambda *args, **kwargs: {"passed": True})
    monkeypatch.setattr(runner, "analyze", lambda path: {"status": "inconclusive"})
    def run(job, *, wait_seconds, validate, before_launch):
        validate()
        if before_launch is not None:
            before_launch()
        calls.append(job["stage"])
    monkeypatch.setattr(runner, "run_once", run)
    return contract, path, tmp_path / "execution", calls


def test_successful_orchestration_keeps_primary_decision(orchestrator):
    contract, path, out, calls = orchestrator
    result = runner.execute(contract, path, "synthetic", out, 1)
    assert result["status"] == "completed" and result["analysis_status"] == "inconclusive"
    assert calls == ["train"] * 12 + ["evaluate"] * 48
    assert result["policy_endpoints_opened"] is True


def test_training_gate_failure_never_opens_endpoints(orchestrator, monkeypatch):
    contract, path, out, calls = orchestrator
    def fail(*args, **kwargs):
        raise ValueError("synthetic manipulation failure")
    monkeypatch.setattr(runner, "verify_training", fail)
    result = runner.execute(contract, path, "synthetic", out, 1)
    assert calls == ["train"]
    assert result["status"] == "execution_stopped" and result["policy_endpoints_opened"] is False
    assert not (out / "endpoint_access.json").exists()


def test_failed_evaluator_still_records_endpoint_access(orchestrator, monkeypatch):
    contract, path, out, calls = orchestrator
    def run(job, *, wait_seconds, validate, before_launch):
        validate()
        if before_launch is not None:
            before_launch()
        calls.append(job["stage"])
        if job["stage"] == "evaluate":
            raise subprocess.CalledProcessError(1, ["synthetic evaluator"])
    monkeypatch.setattr(runner, "run_once", run)
    result = runner.execute(contract, path, "synthetic", out, 1)
    assert result["status"] == "execution_stopped" and result["policy_endpoints_opened"] is True
    assert calls == ["train"] * 12 + ["evaluate"]


def test_busy_gpu_timeout_never_launches(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "gpu_state", lambda: (16000, 10000, 99))
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *a, **k: pytest.fail("launched on busy GPU"))
    with pytest.raises(TimeoutError):
        runner.run_once({"argv": [], "log": str(tmp_path / "absent.log")}, wait_seconds=0)
    assert not (tmp_path / "absent.log").exists()


def test_failed_child_runs_once_and_retains_cost(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "gpu_state", lambda: (16384, 1000, 0))
    log = tmp_path / "cpu_child.log"
    with pytest.raises(subprocess.CalledProcessError):
        runner.run_once({"argv": [sys.executable, "-c", "raise SystemExit(7)"], "log": str(log)}, wait_seconds=1)
    result = execution_cost(log.read_text())
    assert result["actual_launches"] == 1 and result["returncode"] == 7
    assert result["status"] == "failed"


def test_gpu_gap_closing_during_validation_waits_without_launch_retry(monkeypatch, tmp_path):
    states = chain([(16384, 1000, 0), (16384, 10000, 99)], repeat((16384, 1000, 0)))
    monkeypatch.setattr(runner, "gpu_state", lambda: next(states))
    monkeypatch.setattr(runner.time, "sleep", lambda seconds: None)
    validations, launches = [], []
    log = tmp_path / "cpu_gap.log"
    runner.run_once({"argv": [sys.executable, "-c", "pass"], "log": str(log)}, wait_seconds=10,
                    validate=lambda: validations.append(True), before_launch=lambda: launches.append(True))
    assert len(validations) == 2 and len(launches) == 1
    assert execution_cost(log.read_text())["actual_launches"] == 1
