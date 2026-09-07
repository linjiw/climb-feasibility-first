"""Exercise new checkpoint bookkeeping with real samplers and a dummy runner."""

import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import train_relative_confirmation as trainer
from relative_confirmation_setup import PROFILE_PATH, fixed_profiles, config_digest
from run_relative_confirmation import record


@pytest.fixture(params=["U", "A", "R", "D"])
def smoke(tmp_path, monkeypatch, request):
    arm = request.param
    profiles = fixed_profiles(PROFILE_PATH)
    selected = profiles["arms"][arm]
    contract = {"profiles": record(PROFILE_PATH), "bank": str(ROOT / "bank/amass"),
                "unit_table": record(ROOT / "reports/g_segment/unit_table.json"),
                "training_clips": record(ROOT / "bank/tiers/tier_800.txt"),
                "training_sources": {"tools/train_relative_confirmation.py": record(Path(trainer.__file__))}}
    draft = tmp_path / "draft.json"
    draft.write_text(json.dumps(contract))
    draft_record = record(draft)
    cls = trainer.RelativeProgressSampler if arm == "R" else trainer.SegmentSampler
    kwargs = {"relative_factor": 2.0} if arm == "R" else {}
    sampler = cls(Path(contract["unit_table"]["path"]), mode=selected["mode"], seed=51, rank=selected["rank"],
                  exploration_ratio=selected["exploration_ratio"], difficulty_power=selected["difficulty_power"],
                  progress_window=10, progress_floor=selected["progress_floor"],
                  max_unit_probability=0.05, max_clip_probability=0.25, **kwargs)
    def stats():
        segment = {"training_seed": 51, "sampler_seed": 51, "horizon_steps": 50,
                   "unit_table_sha256": profiles["unit_table_sha256"],
                   **{key: selected[key] for key in ("mode", "rank", "exploration_ratio", "difficulty_power", "progress_floor")},
                   "progress_window": 10, "max_unit_probability": 0.05, "max_clip_probability": 0.25,
                   "invalid_start_count": 0, "invalid_reference_frame_count": 0, "censored_resets": 0,
                   "probabilities": sampler.probabilities.tolist(), "completed_trials": int(sampler.lifetime_attempts.sum()),
                   "failed_trials": int(sampler.lifetime_failures.sum())}
        if arm == "R":
            segment.update(allocation_protocol="relative_progress_alp/1", relative_progress_factor=2.0)
        return {"segment": segment}
    command = SimpleNamespace(sampler=sampler, per_clip_stats=stats)
    env = SimpleNamespace(num_envs=8, command_manager=SimpleNamespace(get_term=lambda name: command))
    runner = SimpleNamespace(env=SimpleNamespace(unwrapped=env), current_learning_iteration=0)
    def original_save(self, path, infos=None):
        Path(path).write_bytes(b"SYNTHETIC CHECKPOINT; NOT A POLICY")
    monkeypatch.setattr(trainer.base.MotionTrackingOnPolicyRunner, "save", original_save)
    identity = config_digest(*trainer.smoke_configs(arm, profiles, contract))
    trainer.install_ledger(contract, draft_record["sha256"], arm, 51, identity, stage="entrypoint_smoke", num_envs=8)
    run = tmp_path / "run"
    run.mkdir()
    for iteration in (0, 19):
        sampler.record_completed_trials(torch.tensor([0, 1]), torch.tensor([True, False]))
        sampler.advance_clock()
        runner.current_learning_iteration = iteration
        trainer.base.MotionTrackingOnPolicyRunner.save(runner, str(run / f"model_{iteration}.pt"))
    return run, contract, draft_record, arm


def test_new_ledger_and_sampler_states_reproduce(smoke):
    result = trainer.verify_entrypoint_smoke(*smoke)
    assert result["status"] == "entrypoint_smoke_pass"
    assert result["seed"] == 51 and result["completed_trials"] == 4


def test_rehashed_wrong_configuration_cannot_pass(smoke):
    run, contract, draft, arm = smoke
    path = run / "model_19_segment.json"
    row = json.loads(path.read_text())
    row["configuration_sha256"] = "wrong"
    path.write_text(json.dumps(row))
    with pytest.raises(ValueError, match="configuration/source"):
        trainer.verify_entrypoint_smoke(run, contract, draft, arm)


def test_invalid_actual_trial_cannot_pass(smoke):
    run, contract, draft, arm = smoke
    path = run / "model_19_segment.json"
    row = json.loads(path.read_text())
    row["segment"]["censored_resets"] = 1
    path.write_text(json.dumps(row))
    with pytest.raises(ValueError, match="accounting/replay"):
        trainer.verify_entrypoint_smoke(run, contract, draft, arm)
