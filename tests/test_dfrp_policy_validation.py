"""Reference pairing, failure accounting, and fail-closed DFRP orchestration."""

import csv
import importlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
analysis = importlib.import_module("analyze_dfrp_policy_validation")
runner = importlib.import_module("run_dfrp_policy_validation")


@pytest.fixture
def cells(tmp_path):
    checkpoint = tmp_path / "test_phase_g_g1_s1/model_3999.pt"
    checkpoint.parent.mkdir()
    checkpoint.write_bytes(b"fixed policy")
    conditions = analysis.json.loads(json.dumps({"conditions": [
        {"world_id": i, "condition_id": f"clip@{start}:r0", "clip": "clip",
         "start_frame": start, "phase": i, "replicate": 0,
         "horizon_steps": 150, "full_window": True}
        for i, start in enumerate((0, 150))
    ]}))
    conditions_path = tmp_path / "conditions.json"
    conditions_path.write_text(json.dumps(conditions))
    clip_list = tmp_path / "clips.txt"
    clip_list.write_text("clip\n")
    def bound(path):
        return {"path": str(path), "sha256": analysis.sha256_file(path)}
    design = {
        "schema_version": "dfrp_policy_validation_design/1",
        "conditions": bound(conditions_path), "clip_list": bound(clip_list),
        "curated_manifest": bound(clip_list), "training_clips": bound(clip_list),
        "evaluator_sha256": "e" * 64,
        "analyzer_sha256": analysis.sha256_file(Path(analysis.__file__)),
        "clips": [{"clip": "clip", "raw_sha256": "a" * 64,
                   "repaired_sha256": "b" * 64, "qualified_repair": True,
                   "training_overlap": False}],
    }
    design_path = tmp_path / "design.json"
    design_path.write_text(json.dumps(design))
    for arm in ("raw", "repaired"):
        records = []
        for condition in conditions["conditions"]:
            success = arm == "repaired" or condition["start_frame"] == 150
            row = {**condition, "actual_window_s": 3, "survival_s": 3 if success else 1,
                   "success": int(success), "termination_causes": "" if success else "fall",
                   "common_root_relative_mpkpe_m_mean": 0.1,
                   "common_anchor_orientation_error_rad_mean": 0.1,
                   "absolute_mechanical_work_per_actuator_j": 1}
            records.append(row)
        path = tmp_path / f"{arm}.csv"
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=records[0])
            writer.writeheader()
            writer.writerows(records)
        meta = {
            "schema_version": "paired_eval_output/1", "task": "Climb-Tracking-Flat-Unitree-G1",
            "checkpoint": str(checkpoint), "checkpoint_sha256": analysis.sha256_file(checkpoint),
            "conditions_sha256": design["conditions"]["sha256"],
            "clips_sha256": design["clip_list"]["sha256"],
            "evaluator_sha256": design["evaluator_sha256"],
            "selected_reference_sha256": {"clip": ("a" if arm == "raw" else "b") * 64},
            "common_reference_sha256": {"clip": "a" * 64},
            "worlds": 2, "nominal": False, "joint_noise": 0.05, "nconmax_per_world": 70,
            "startup_randomization_sha256": "1" * 64,
            "initial_state_sha256": ("2" if arm == "raw" else "3") * 64,
            "software_versions": {"test": "synthetic"},
            "source_sha256": {str(clip_list): analysis.sha256_file(clip_list)},
            "device": "synthetic",
        }
        Path(f"{path}.meta.json").write_text(json.dumps(meta))
    return design_path, tmp_path / "raw.csv", tmp_path / "repaired.csv"


def test_all_failures_retained_and_survivor_denominator_explicit(cells):
    result = analysis.analyze(*cells)
    all_rows = result["strata"]["all"]
    assert all_rows["all_conditions"]["conditions"] == 2
    assert all_rows["all_conditions"]["trial_accounting"]["raw"]["failures"] == 1
    assert all_rows["all_conditions"]["metrics"]["success"]["repaired_minus_raw"] == 0.5
    assert all_rows["survivor_eligible_conditions"] == 2
    assert all_rows["paired_complete_window_survivors"]["conditions"] == 1
    assert all_rows["frame_zero"]["metrics"]["success"]["repaired_minus_raw"] == 1
    assert result["strata"]["training_overlap"]["all_conditions"]["conditions"] == 0


@pytest.mark.parametrize("field,value", [
    ("common_reference_sha256", {"clip": "b" * 64}),
    ("startup_randomization_sha256", "9" * 64),
    ("selected_reference_sha256", {"clip": "a" * 64}),
    ("checkpoint_sha256", "9" * 64),
    ("evaluator_sha256", "9" * 64),
    ("source_sha256", {}),
])
def test_unpaired_provenance_rejected(cells, field, value):
    path = Path(f"{cells[2]}.meta.json")
    meta = json.loads(path.read_text())
    meta[field] = value
    path.write_text(json.dumps(meta))
    with pytest.raises(ValueError):
        analysis.analyze(*cells)


def test_missing_trial_rejected(cells):
    path = cells[2]
    lines = path.read_text().splitlines()
    path.write_text("\n".join(lines[:-1]) + "\n")
    with pytest.raises(ValueError, match="conditions"):
        analysis.analyze(*cells)


def test_clip_weighting_not_trial_weighting():
    rows = {
        str(i): {"clip": "a" if i < 3 else "b", "success": 1 if i < 3 else 0,
                 "actual_window_s": 3, "survival_s": 3, "termination_causes": "test",
                 "common_root_relative_mpkpe_m_mean": 0.1,
                 "common_anchor_orientation_error_rad_mean": 0.1,
                 "absolute_mechanical_work_per_actuator_j": 1}
        for i in range(4)
    }
    result = analysis.summarize(rows, rows, list(rows))
    assert result["metrics"]["success"]["raw"] == 0.5


def test_e4_active_cannot_launch_gpu(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "OUT", tmp_path)
    monkeypatch.setattr(runner, "prepare", lambda: tmp_path / "design.json")
    monkeypatch.setattr(runner, "terminal_e4", lambda: None)
    monkeypatch.setattr(sys, "argv", ["run_dfrp_policy_validation.py", "--source-repo", "/tmp"])
    launched = []
    monkeypatch.setattr(runner, "gated", lambda *a: launched.append(a))
    with pytest.raises(ValueError, match="still active"):
        runner.main()
    assert not launched


def test_recovery_receipt_cannot_mask_missing_payload(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "RECOVERY", tmp_path)
    (tmp_path / "recovery_result.json").write_text(json.dumps({
        "pass": True, "raw_verified": 26, "repaired_verified": 26,
        "manifest_sha256": "h", "raw_bank": str(tmp_path), "repaired_bank": str(tmp_path),
    }))
    with pytest.raises(ValueError, match="artifact"):
        runner.verify_payload({"curated_manifest": {"sha256": "h"},
                               "clips": [{"clip": "missing", "raw_sha256": "x"}]})


def test_same_checkpoint_and_raw_common_reference_in_both_cells(monkeypatch, cells, tmp_path):
    monkeypatch.setattr(runner, "OUT", tmp_path / "new")
    monkeypatch.setattr(runner, "analyze", lambda *a: {"status": "synthetic"})
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: None)
    calls = []
    monkeypatch.setattr(runner, "gated", lambda command, *a: calls.append(command))
    checkpoint = tmp_path / "test_phase_g_g1_s1/model_3999.pt"
    raw, repaired = tmp_path / "raw_bank", tmp_path / "repaired_bank"
    runner.evaluate_cells(cells[0], checkpoint, raw, repaired)
    assert len(calls) == 2
    for command in calls:
        assert command[command.index("--checkpoint") + 1] == str(checkpoint)
        assert command[command.index("--common-reference-bank") + 1] == str(raw)
    assert calls[1][calls[1].index("--bank") + 1] == str(repaired)
