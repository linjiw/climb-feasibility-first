"""Check four-arm smoke evidence independently of a running GPU simulator."""

import json
from pathlib import Path
import sys

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from run_relative_policy_smokes import MANIFEST, verify_smoke
from train_relative_policy import CONTRACT, profile
from check_relative_progress_probe import sha256
from climb.relative_progress import RelativeProgressSampler
from climb.segment_runtime import SegmentSampler


def make_smoke(tmp_path, arm):
    contract, selected = profile(arm, "smoke", 41)
    cls = RelativeProgressSampler if arm == "R" else SegmentSampler
    extra = {"relative_factor": 2.0} if arm == "R" else {}
    sampler = cls(MANIFEST, mode=selected["mode"], seed=41, rank=selected["rank"],
                  exploration_ratio=selected["exploration_ratio"], difficulty_power=selected["difficulty_power"],
                  progress_window=10, progress_floor=selected["progress_floor"],
                  max_unit_probability=0.05, max_clip_probability=0.25, **extra)
    sources = {name: sha256(ROOT / name) for name in (
        "tools/train_relative_policy.py", "climb/relative_progress.py", "climb/segment_runtime.py",
        "climb/segment_curriculum.py", "climb/segment_command.py", "climb/segment_env_cfg.py")}
    for iteration in (0, 19):
        sampler.record_completed_trials(torch.tensor([0, 1]), torch.tensor([False, True]))
        sampler.advance_clock()
        checkpoint = tmp_path / f"model_{iteration}.pt"
        checkpoint.write_bytes(f"fixture {arm} {iteration}".encode())
        state_path = tmp_path / f"model_{iteration}_segment_sampler.pt"
        torch.save({"iteration": iteration, "sampler": sampler.state_dict()}, state_path)
        segment = {"sampler_seed": 41, "training_seed": 41, "horizon_steps": 50,
                   "unit_table_sha256": contract["unit_table_sha256"], "mode": selected["mode"],
                   "rank": selected["rank"], "exploration_ratio": selected["exploration_ratio"],
                   "difficulty_power": selected["difficulty_power"], "progress_floor": selected["progress_floor"],
                   "progress_window": 10, "max_unit_probability": 0.05, "max_clip_probability": 0.25,
                   "probabilities": sampler.probabilities.tolist(), "invalid_start_count": 0,
                   "invalid_reference_frame_count": 0, "censored_resets": 0,
                   "completed_trials": int(sampler.lifetime_attempts.sum()),
                   "failed_trials": int(sampler.lifetime_failures.sum())}
        row = {"iteration": iteration, "relative_policy_arm": arm, "relative_policy_stage": "smoke",
               "num_envs": 8, "profile": selected, "profile_contract_sha256": sha256(CONTRACT),
               "training_entrypoint_sha256": sources["tools/train_relative_policy.py"],
               "source_hashes_at_launch": sources, "segment": segment,
               "checkpoint": {"path": str(checkpoint), "sha256": sha256(checkpoint)}}
        (tmp_path / f"model_{iteration}_segment.json").write_text(json.dumps(row))
    return sources


@pytest.mark.parametrize("arm", ["U", "A", "R", "D"])
def test_all_four_sampler_states_replay(tmp_path, arm):
    sources = make_smoke(tmp_path, arm)
    assert verify_smoke(tmp_path, arm, sources)["status"] == "smoke_pass"


@pytest.mark.parametrize("field", ["completed_trials", "failed_trials", "censored_resets"])
def test_event_accounting_corruption_fails(tmp_path, field):
    sources = make_smoke(tmp_path, "D")
    path = tmp_path / "model_19_segment.json"
    row = json.loads(path.read_text())
    row["segment"][field] += 1
    path.write_text(json.dumps(row))
    with pytest.raises(ValueError):
        verify_smoke(tmp_path, "D", sources)
