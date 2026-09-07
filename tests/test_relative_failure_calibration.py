"""D calibration needs complete source-bound evidence and fixed pass/fail gates."""

import json
from pathlib import Path
import sys

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from run_relative_failure_calibration import CONTRACT, MANIFEST, TRAINING_SOURCES, profile, sha256, verify_calibration
from climb.segment_runtime import SegmentSampler


@pytest.fixture
def calibration(tmp_path):
    contract, selected = profile("D", "calibration", 31)
    sources = {name: sha256(ROOT / name) for name in TRAINING_SOURCES}
    sampler = SegmentSampler(MANIFEST, mode="adaptive", seed=31, rank="failure", exploration_ratio=0.8,
                             difficulty_power=1.0, progress_window=10, progress_floor=0.0,
                             max_unit_probability=0.05, max_clip_probability=0.25)
    ids = torch.arange(sampler.num_units).repeat(10)
    sampler.record_completed_trials(ids, ids < sampler.num_units // 2)
    sampler.advance_clock()
    for iteration in [*range(0, 4000, 100), 3999]:
        checkpoint = tmp_path / f"model_{iteration}.pt"
        checkpoint.write_bytes(b"synthetic, not policy evidence")
        state_path = tmp_path / f"model_{iteration}_segment_sampler.pt"
        torch.save({"iteration": iteration, "sampler": sampler.state_dict()}, state_path)
        segment = {"training_seed": 31, "sampler_seed": 31, "horizon_steps": 50,
                   "unit_table_sha256": contract["unit_table_sha256"],
                   **{key: selected[key] for key in ("mode", "rank", "exploration_ratio", "difficulty_power", "progress_floor")},
                   **{key: contract["common"][key] for key in ("progress_window", "max_unit_probability", "max_clip_probability")},
                   "probabilities": sampler.probabilities.tolist(), "invalid_start_count": 0,
                   "invalid_reference_frame_count": 0, "censored_resets": 0,
                   "completed_trials": int(sampler.lifetime_attempts.sum()),
                   "failed_trials": int(sampler.lifetime_failures.sum())}
        row = {"iteration": iteration, "relative_policy_arm": "D", "relative_policy_stage": "calibration",
               "num_envs": 512, "profile": selected, "profile_contract_sha256": sha256(CONTRACT),
               "training_entrypoint_sha256": sources["tools/train_relative_policy.py"],
               "source_hashes_at_launch": sources, "segment": segment,
               "checkpoint": {"path": str(checkpoint), "sha256": sha256(checkpoint)}}
        (tmp_path / f"model_{iteration}_segment.json").write_text(json.dumps(row))
    return tmp_path, sources


def test_full_fixed_calibration_replays(calibration):
    path, sources = calibration
    result = verify_calibration(path, 31, sources)
    assert result["status"] == "calibration_pass"
    assert len(result["snapshots"]) == 41
    assert result["policy_endpoints_opened"] is False


def test_missing_final_snapshot_cannot_pass(calibration):
    path, sources = calibration
    (path / "model_3999_segment.json").unlink()
    with pytest.raises(ValueError, match="41"):
        verify_calibration(path, 31, sources)


@pytest.mark.parametrize("key,value", [("sampler_seed", 32), ("completed_trials", -1),
                                       ("censored_resets", 1), ("exploration_ratio", 0.4)])
def test_wrong_evidence_rejected(calibration, key, value):
    path, sources = calibration
    ledger_path = path / "model_3999_segment.json"
    row = json.loads(ledger_path.read_text())
    row["segment"][key] = value
    ledger_path.write_text(json.dumps(row))
    with pytest.raises(ValueError):
        verify_calibration(path, 31, sources)


def test_changed_sampler_probabilities_rejected(calibration):
    path, sources = calibration
    ledger_path = path / "model_3999_segment.json"
    row = json.loads(ledger_path.read_text())
    row["segment"]["probabilities"][0] += 0.001
    ledger_path.write_text(json.dumps(row))
    with pytest.raises(ValueError, match="replay"):
        verify_calibration(path, 31, sources)
