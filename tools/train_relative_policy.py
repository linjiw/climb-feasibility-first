#!/usr/bin/env python3
"""Build fixed U/A/R/D profiles; allow development runs, refuse confirmation."""

from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path

import torch

import climb_segment_train as base
from climb.relative_progress import RelativeProgressCommandCfg
from climb.segment_env_cfg import segment_native_g1_tracking_env_cfg

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "plan/R3_BASELINE_CONTRACT_2026-09-05.json"


def profile(arm: str, stage: str, seed: int) -> tuple[dict, dict]:
    contract = json.loads(CONTRACT.read_text())
    if contract["schema_version"] != "relative_policy_profiles/1":
        raise ValueError("unsupported policy profile contract")
    if stage == "confirmation":
        raise ValueError("confirmation requires the future verified run manifest and frozen launcher")
    if stage not in ("smoke", "calibration") or arm not in contract["arms"]:
        raise ValueError("unknown development stage or arm")
    stage_contract = contract[stage]
    if seed not in stage_contract["seeds"] or arm not in stage_contract.get("arms", contract["arms"]):
        raise ValueError("arm/seed not allowed for this development stage")
    return contract, contract["arms"][arm]


def config(arm: str, stage: str, seed: int):
    """Use a shared environment factory with only the declared sampler changes."""
    contract, selected = profile(arm, stage, seed)
    common = contract["common"]
    manifest_path = Path(os.environ["CLIMB_SEGMENT_MANIFEST"])
    manifest = json.loads(manifest_path.read_text())
    if manifest["unit_table_sha256"] != contract["unit_table_sha256"]:
        raise ValueError("wrong exact-support manifest")
    cfg = segment_native_g1_tracking_env_cfg(
        motion_files=base.read_clip_list(os.environ["CLIMB_CLIPS"], os.environ["CLIMB_BANK"]),
        segment_manifest=str(manifest_path), segment_sampling_mode=selected["mode"],
        sampler_seed=seed, env_seed=seed, segment_rank=selected["rank"],
        segment_exploration_ratio=selected["exploration_ratio"],
        segment_difficulty_power=selected["difficulty_power"],
        segment_progress_window=common["progress_window"],
        segment_progress_floor=selected["progress_floor"],
        max_unit_probability=common["max_unit_probability"],
        max_clip_probability=common["max_clip_probability"],
        verify_motion_hashes=common["verify_motion_hashes"], failure_penalty=common["failure_penalty"],
    )
    if arm == "R":
        command = cfg.commands["motion"]
        cfg.commands["motion"] = RelativeProgressCommandCfg(
            **{field.name: getattr(command, field.name) for field in dataclasses.fields(command)},
            relative_progress_factor=selected["relative_factor"],
        )
    return cfg


def install_ledger(arm: str, stage: str, seed: int) -> None:
    original = base.MotionTrackingOnPolicyRunner.save
    contract, selected = profile(arm, stage, seed)
    expected_envs = contract[stage]["num_envs"]
    names = ("tools/train_relative_policy.py", "climb/relative_progress.py",
             "climb/segment_runtime.py", "climb/segment_curriculum.py",
             "climb/segment_command.py", "climb/segment_env_cfg.py")
    source_hashes = {name: base._sha256_file(ROOT / name) for name in names}
    contract_hash = base._sha256_file(CONTRACT)

    def save(self, path: str, infos=None):
        original(self, path, infos)
        command = self.env.unwrapped.command_manager.get_term("motion")
        stats = command.per_clip_stats()
        segment = stats["segment"]
        if (segment["training_seed"] != seed or segment["sampler_seed"] != seed
                or self.env.unwrapped.num_envs != expected_envs):
            raise ValueError("actual seed or environment count differs from development contract")
        checkpoint = Path(path).resolve()
        stats.update({"iteration": int(self.current_learning_iteration),
                      "classification": "prospective R3 development telemetry; no policy-benefit test",
                      "relative_policy_arm": arm, "relative_policy_stage": stage,
                      "profile": selected, "profile_contract_sha256": contract_hash,
                      "source_hashes_at_launch": source_hashes,
                      "training_entrypoint_sha256": source_hashes["tools/train_relative_policy.py"],
                      "num_envs": int(self.env.unwrapped.num_envs),
                      "checkpoint": {"path": str(checkpoint), "sha256": base._sha256_file(checkpoint)}})
        checkpoint.with_name(f"{checkpoint.stem}_segment.json").write_text(json.dumps(stats, indent=1) + "\n")
        torch.save({"iteration": int(self.current_learning_iteration), "sampler": command.sampler.state_dict()},
                   checkpoint.with_name(f"{checkpoint.stem}_segment_sampler.pt"))

    base.MotionTrackingOnPolicyRunner.save = save


if __name__ == "__main__":
    arm = os.environ["CLIMB_POLICY_ARM"]
    stage = os.environ["CLIMB_POLICY_STAGE"]
    seed = int(os.environ["CLIMB_POLICY_SEED"])
    contract, _ = profile(arm, stage, seed)
    task = f"Climb-Tracking-Flat-Unitree-G1-Policy-{arm}-Development"
    cfg = config(arm, stage, seed)
    cfg.scene.num_envs = contract[stage]["num_envs"]
    runner = base.unitree_g1_tracking_ppo_runner_cfg()
    runner.seed = seed
    runner.max_iterations = contract[stage]["iterations"]
    runner.save_interval = contract["common"]["save_interval"]
    base.register_mjlab_task(task_id=task, env_cfg=cfg, play_env_cfg=config(arm, stage, seed),
                            rl_cfg=runner, runner_cls=base.MotionTrackingOnPolicyRunner)
    install_ledger(arm, stage, seed)
    base.main()
