#!/usr/bin/env python3
"""Launch the isolated segment-v2 uniform or adaptive training task.

Required environment variables:

``CLIMB_CLIPS``
    Newline-delimited motion list in the same order as the unit manifest.
``CLIMB_BANK``
    Directory containing the listed motion NPZs.
``CLIMB_SEGMENT_MANIFEST``
    Exact ``segment_unit_table/1`` JSON produced by the v2 builder.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import torch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from mjlab.scripts.train import main
from mjlab.tasks.registry import register_mjlab_task
from mjlab.tasks.tracking.config.g1.rl_cfg import (
    unitree_g1_tracking_ppo_runner_cfg,
)
from mjlab.tasks.tracking.rl import MotionTrackingOnPolicyRunner

import climb  # noqa: F401
from climb.env_cfg import read_clip_list
from climb.segment_command import SegmentNativeMotionCommand
from climb.segment_env_cfg import segment_native_g1_tracking_env_cfg
from climb.segment_runtime import SamplingMode

TASKS: dict[str, SamplingMode] = {
    "Climb-Tracking-Flat-Unitree-G1-SegmentV2-Uniform": "uniform",
    "Climb-Tracking-Flat-Unitree-G1-SegmentV2-Adaptive": "adaptive",
}


def _register_tasks() -> None:
    clips_path = os.environ.get("CLIMB_CLIPS")
    manifest = os.environ.get("CLIMB_SEGMENT_MANIFEST")
    if not clips_path or not manifest:
        raise SystemExit("set CLIMB_CLIPS and CLIMB_SEGMENT_MANIFEST")
    bank = os.environ.get("CLIMB_BANK", os.path.dirname(clips_path))
    files = read_clip_list(clips_path, bank)
    sampler_seed = int(os.environ.get("CLIMB_SEGMENT_SEED", "0"))
    failure_penalty = float(os.environ.get("CLIMB_SEGMENT_FAILURE_PENALTY", "-10"))
    verify_hashes = os.environ.get("CLIMB_VERIFY_MOTION_HASHES", "1") != "0"
    for task_id, mode in TASKS.items():
        register_mjlab_task(
            task_id=task_id,
            env_cfg=segment_native_g1_tracking_env_cfg(
                motion_files=files,
                segment_manifest=manifest,
                segment_sampling_mode=mode,
                sampler_seed=sampler_seed,
                verify_motion_hashes=verify_hashes,
                failure_penalty=failure_penalty,
            ),
            play_env_cfg=segment_native_g1_tracking_env_cfg(
                motion_files=files,
                segment_manifest=manifest,
                segment_sampling_mode=mode,
                sampler_seed=sampler_seed,
                play=True,
                verify_motion_hashes=verify_hashes,
                failure_penalty=failure_penalty,
            ),
            rl_cfg=unitree_g1_tracking_ppo_runner_cfg(),
            runner_cls=MotionTrackingOnPolicyRunner,
        )


def _install_segment_checkpoint_ledger() -> None:
    original_save = MotionTrackingOnPolicyRunner.save

    def save(
        self: MotionTrackingOnPolicyRunner,
        path: str,
        infos: Any | None = None,
    ) -> None:
        original_save(self, path, infos)
        try:
            command = self.env.unwrapped.command_manager.get_term("motion")
            if not isinstance(command, SegmentNativeMotionCommand):
                raise TypeError("checkpoint command is not segment-native")
            stats = command.per_clip_stats()
            stats["iteration"] = int(self.current_learning_iteration)
            stats["classification"] = "unsealed segment-v2 training telemetry"
            stem = Path(path).with_suffix("")
            stats_path = Path(f"{stem}_segment.json")
            state_path = Path(f"{stem}_segment_sampler.pt")
            stats_path.write_text(json.dumps(stats, indent=1) + "\n")
            torch.save(
                {
                    "classification": "sampler-only state; not a full simulator resume",
                    "iteration": int(self.current_learning_iteration),
                    "sampler": command.sampler.state_dict(),
                },
                state_path,
            )
            print(f"[climb] segment ledger -> {stats_path}")
            print(f"[climb] segment sampler state -> {state_path}")
        except Exception as exc:  # noqa: BLE001 -- telemetry must not kill PPO
            print(f"[climb] segment checkpoint ledger skipped: {exc}")

    MotionTrackingOnPolicyRunner.save = save  # type: ignore[invalid-assignment]


if __name__ == "__main__":
    _register_tasks()
    _install_segment_checkpoint_ledger()
    main()
