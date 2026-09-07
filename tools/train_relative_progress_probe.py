#!/usr/bin/env python3
"""Run the separately named exploratory relative-ALP manipulation probe."""

from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path

import torch

import climb_segment_train as base
from climb.relative_progress import PROTOCOL, RelativeProgressCommand, RelativeProgressCommandCfg
from climb.segment_env_cfg import segment_native_g1_tracking_env_cfg

TASK = "Climb-Tracking-Flat-Unitree-G1-RelativeALP-Probe"
ROOT = Path(__file__).resolve().parents[1]
SEED = int(os.environ.get("CLIMB_RELATIVE_SEED", "11"))


def config():
    cfg = segment_native_g1_tracking_env_cfg(
        motion_files=base.read_clip_list(os.environ["CLIMB_CLIPS"], os.environ["CLIMB_BANK"]),
        segment_manifest=os.environ["CLIMB_SEGMENT_MANIFEST"],
        segment_sampling_mode="adaptive", sampler_seed=SEED, env_seed=SEED,
        segment_rank="learning_progress", segment_exploration_ratio=0.4,
        segment_difficulty_power=0.0, segment_progress_window=10, segment_progress_floor=0.0,
        max_unit_probability=0.05, max_clip_probability=0.25,
        verify_motion_hashes=True, failure_penalty=-10,
    )
    command = cfg.commands["motion"]
    cfg.commands["motion"] = RelativeProgressCommandCfg(
        **{field.name: getattr(command, field.name) for field in dataclasses.fields(command)},
        relative_progress_factor=2.0,
    )
    return cfg


def install_ledger() -> None:
    original = base.MotionTrackingOnPolicyRunner.save
    source_hashes = {
        name: base._sha256_file(ROOT / name) for name in (
            "tools/train_relative_progress_probe.py", "climb/relative_progress.py",
            "climb/segment_runtime.py", "climb/segment_curriculum.py",
            "climb/segment_command.py", "climb/segment_env_cfg.py",
        )
    }

    def save(self, path: str, infos=None):
        original(self, path, infos)
        command = self.env.unwrapped.command_manager.get_term("motion")
        if not isinstance(command, RelativeProgressCommand):
            raise TypeError("wrong command in relative-progress probe")
        checkpoint = Path(path).resolve()
        stats = command.per_clip_stats()
        stats.update({
            "iteration": int(self.current_learning_iteration),
            "classification": "exploratory relative-progress manipulation telemetry",
            "checkpoint": {"path": str(checkpoint), "sha256": base._sha256_file(checkpoint)},
            "training_entrypoint_sha256": base._sha256_file(Path(__file__)),
            "relative_module_sha256": base._sha256_file(ROOT / "climb/relative_progress.py"),
            "allocation_protocol": PROTOCOL,
            "source_hashes_at_launch": source_hashes,
            "num_envs": int(self.env.unwrapped.num_envs),
        })
        Path(f"{checkpoint.with_suffix('')}_segment.json").write_text(json.dumps(stats, indent=1) + "\n")
        torch.save({"iteration": int(self.current_learning_iteration),
                    "sampler": command.sampler.state_dict()},
                   Path(f"{checkpoint.with_suffix('')}_segment_sampler.pt"))

    base.MotionTrackingOnPolicyRunner.save = save


if __name__ == "__main__":
    runner = base.unitree_g1_tracking_ppo_runner_cfg()
    runner.seed = SEED
    runner.save_interval = 100
    base.register_mjlab_task(task_id=TASK, env_cfg=config(), play_env_cfg=config(),
                            rl_cfg=runner, runner_cls=base.MotionTrackingOnPolicyRunner)
    install_ledger()
    base.main()
