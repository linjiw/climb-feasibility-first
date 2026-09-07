"""Load actual development checkpoints through the evaluator's runner on CPU.

The environment supplies fixed zero tensors only; no simulator or rollout is
constructed. This tests serialization, normalization and actor-only loading,
not policy performance or runtime observation correctness.
"""

from contextlib import redirect_stdout
from dataclasses import asdict
import io
import json
from pathlib import Path
import sys

import pytest
import torch
from tensordict import TensorDict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import climb  # noqa: F401
from check_relative_progress_probe import sha256
from mjlab.tasks.registry import load_rl_cfg, load_runner_cls

TASK = "Climb-Tracking-Flat-Unitree-G1"
SMOKES = ROOT / "reports/relative_progress_2026-09-05/policy_smokes_gate_retry"


class ObservationStub:
    """Supply the actual development checkpoint dimensions, never physics."""

    num_envs = 2
    num_actions = 29
    device = "cpu"
    cfg = {}
    common_step_counter = 0

    @property
    def unwrapped(self):
        return self

    def get_observations(self):
        return TensorDict({"actor": torch.zeros(2, 160), "critic": torch.zeros(2, 286)}, batch_size=[2])

    def step(self, actions):
        raise AssertionError("checkpoint audit must never step an environment")


def checkpoint_for(arm: str) -> Path:
    decision = SMOKES / f"{arm}_result.json"
    if not decision.is_file():
        pytest.skip("actual seed-41 development checkpoint is not available")
    saved = json.loads(decision.read_text())
    assert saved["status"] == "smoke_pass"
    paths = [Path(name) for name in saved["bindings"] if Path(name).name == "model_19_segment.json"]
    assert len(paths) == 1
    checkpoint = paths[0].with_name("model_19.pt")
    assert sha256(checkpoint) == saved["bindings"][str(paths[0])]["checkpoint"]
    return checkpoint


def make_runner():
    with redirect_stdout(io.StringIO()), torch.random.fork_rng(devices=[]):
        return load_runner_cls(TASK)(ObservationStub(), asdict(load_rl_cfg(TASK)), device="cpu")


def audit_checkpoint(arm: str) -> dict:
    """Use the same strict actor-only runner call as the sealed evaluator."""
    checkpoint = checkpoint_for(arm)
    saved = torch.load(checkpoint, map_location="cpu", weights_only=True)
    runner = make_runner()
    critic_before = {name: value.clone() for name, value in runner.alg._raw_critic.state_dict().items()}
    runner.load(str(checkpoint), load_cfg={"actor": True}, strict=True, map_location="cpu")
    policy = runner.get_inference_policy(device="cpu")
    restored = policy.state_dict()
    assert set(restored) == set(saved["actor_state_dict"])
    assert all(torch.equal(value, saved["actor_state_dict"][name]) for name, value in restored.items())
    assert all(torch.equal(value, critic_before[name]) for name, value in runner.alg._raw_critic.state_dict().items())
    assert runner.current_learning_iteration == 0
    assert runner.env.common_step_counter == saved["infos"]["env_state"]["common_step_counter"]
    assert policy.training is False
    assert all(torch.isfinite(value).all() for value in restored.values())
    return {"arm": arm, "seed": 41, "iteration": 19, "status": "strict_actor_load_pass",
            "checkpoint": {"path": str(checkpoint), "sha256": sha256(checkpoint)},
            "actor_observation_dim": 160, "critic_observation_dim": 286, "action_dim": 29,
            "actor_tensors_restored": len(restored),
            "normalization_tensors_restored": sum(name.startswith("obs_normalizer.") for name in restored),
            "critic_unchanged": True, "training_iteration_not_restored": True,
            "common_step_counter_restored": True, "simulator_constructed": False,
            "policy_forward_calls": 0, "policy_endpoints_opened": False}


@pytest.mark.parametrize("arm", ("U", "A", "R", "D"))
def test_actual_development_actor_load_and_normalization(arm):
    assert audit_checkpoint(arm)["status"] == "strict_actor_load_pass"


@pytest.mark.parametrize("arm", ("U", "A", "R", "D"))
def test_missing_normalization_cannot_load_strictly(arm, tmp_path):
    saved = torch.load(checkpoint_for(arm), map_location="cpu", weights_only=True)
    del saved["actor_state_dict"]["obs_normalizer._mean"]
    path = tmp_path / "SYNTHETIC_CORRUPTED_checkpoint.pt"
    torch.save(saved, path)
    with pytest.raises(RuntimeError, match="Missing key"):
        make_runner().load(str(path), load_cfg={"actor": True}, strict=True, map_location="cpu")


@pytest.mark.parametrize("arm", ("U", "A", "R", "D"))
def test_incompatible_actor_input_cannot_load_strictly(arm, tmp_path):
    saved = torch.load(checkpoint_for(arm), map_location="cpu", weights_only=True)
    saved["actor_state_dict"]["mlp.0.weight"] = saved["actor_state_dict"]["mlp.0.weight"][:, :-1]
    path = tmp_path / "SYNTHETIC_WRONG_DIM_checkpoint.pt"
    torch.save(saved, path)
    with pytest.raises(RuntimeError, match="size mismatch"):
        make_runner().load(str(path), load_cfg={"actor": True}, strict=True, map_location="cpu")
