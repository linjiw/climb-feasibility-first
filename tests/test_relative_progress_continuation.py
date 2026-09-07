"""Continuation cannot promote absent, failed, or mismatched predecessor evidence."""

import json
import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import continue_relative_progress as continuation


@pytest.fixture
def study(tmp_path, monkeypatch):
    design = {"seed": 11, "policy_endpoints_opened": False, "sources": {}}
    (tmp_path / "design.json").write_text(json.dumps(design))
    terminal = {"seed": 11, "policy_endpoints_opened": False, "status": "completed"}
    (tmp_path / "terminal_status.json").write_text(json.dumps(terminal))
    saved = {}
    for stage, status in (("smoke", "smoke_pass"), ("long", "manipulation_pass")):
        saved[stage] = {"seed": 11, "stage": stage, "status": status, "gate": None,
                        "bindings": {str(tmp_path / "model_0_segment.json"): {}}}
        (tmp_path / f"{stage}_result.json").write_text(json.dumps(saved[stage]))
    (tmp_path / "long.log").write_text("DONE rc=0 elapsed_s=10\n")
    monkeypatch.setattr(continuation, "check_run", lambda *args, stage, **kwargs: saved[stage])
    return tmp_path, saved


def test_complete_pass_is_promotable(study):
    path, _ = study
    assert continuation.verify_study(path, 11)["status"] == "pass"


def test_relative_smoke_paths_reproduce_without_rewriting(study, monkeypatch):
    path, saved = study
    relative_parent = Path(os.path.relpath(path))
    saved["smoke"]["bindings"] = {str(relative_parent / "model_0_segment.json"): {}}
    (path / "smoke_result.json").write_text(json.dumps(saved["smoke"]))

    def reproduce(run_dir, *args, stage, **kwargs):
        if stage == "smoke":
            assert run_dir == relative_parent
            assert not run_dir.is_absolute()
        return saved[stage]

    monkeypatch.setattr(continuation, "check_run", reproduce)
    assert continuation.verify_study(path, 11)["status"] == "pass"


def test_scientific_failure_is_preserved(study):
    path, saved = study
    saved["long"]["status"] = "manipulation_fail"
    (path / "long_result.json").write_text(json.dumps(saved["long"]))
    terminal = json.loads((path / "terminal_status.json").read_text())
    terminal["status"] = "stopped"
    (path / "terminal_status.json").write_text(json.dumps(terminal))
    assert continuation.verify_study(path, 11)["status"] == "fail"


def test_forged_summary_is_rejected(study):
    path, _ = study
    row = json.loads((path / "long_result.json").read_text())
    row["gate"] = {"mean_tv": 0.1}
    (path / "long_result.json").write_text(json.dumps(row))
    with pytest.raises(ValueError, match="does not reproduce"):
        continuation.verify_study(path, 11)


@pytest.mark.parametrize("case", ["seed", "endpoint", "terminal", "log", "source"])
def test_invalid_study_is_not_promoted(study, case):
    path, _ = study
    terminal_path = path / "terminal_status.json"
    terminal = json.loads(terminal_path.read_text())
    if case == "seed":
        terminal["seed"] = 12
    elif case == "endpoint":
        terminal["policy_endpoints_opened"] = True
    elif case == "terminal":
        terminal["status"] = "stopped"
    elif case == "log":
        (path / "long.log").write_text("DONE rc=1\n")
    else:
        design_path = path / "design.json"
        design = json.loads(design_path.read_text())
        design["sources"] = {"tools/continue_relative_progress.py": "wrong"}
        design_path.write_text(json.dumps(design))
    terminal_path.write_text(json.dumps(terminal))
    with pytest.raises(ValueError):
        continuation.verify_study(path, 11)
