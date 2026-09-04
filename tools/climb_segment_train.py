#!/usr/bin/env python3
"""Launch the isolated segment-v2 uniform or adaptive training task.

Required environment variables:

``CLIMB_CLIPS``
    Newline-delimited motion list in the same order as the unit manifest.
``CLIMB_BANK``
    Directory containing the listed motion NPZs.
``CLIMB_SEGMENT_MANIFEST``
    Exact ``segment_unit_table/1`` JSON produced by the v2 builder.
``CLIMB_SEGMENT_SEED``
    One explicit seed shared by PPO, the environment, and the segment sampler.

Phase-G adaptive runs must also set ``CLIMB_SEGMENT_RANK=learning_progress``.
The launcher then defaults ``CLIMB_SEGMENT_DIFFICULTY_POWER`` to zero, as the
rank contract requires.  The remaining ``CLIMB_SEGMENT_*`` variables expose
the sealed exploration, progress-window, and probability-cap settings without
hiding them in task code. ``CLIMB_SEGMENT_SAVE_INTERVAL`` can shorten the
checkpoint/ledger cadence for endpoint-blind treatment calibration; it does not
alter PPO or sampler updates.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, cast

import torch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from mjlab.rl import RslRlOnPolicyRunnerCfg
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
from climb.segment_runtime import RankMode, SamplingMode

TASKS: dict[str, SamplingMode] = {
    "Climb-Tracking-Flat-Unitree-G1-SegmentV2-Uniform": "uniform",
    "Climb-Tracking-Flat-Unitree-G1-SegmentV2-Adaptive": "adaptive",
}


def _sha256_file(path: Path) -> str:
    """Hash a checkpoint or source artifact without loading it into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rank_from_env() -> RankMode:
    rank = os.environ.get("CLIMB_SEGMENT_RANK", "failure")
    if rank not in ("failure", "learning_progress", "uncertainty"):
        raise SystemExit(
            "CLIMB_SEGMENT_RANK must be failure, learning_progress, or uncertainty"
        )
    return cast(RankMode, rank)


def _seed_from_env() -> int:
    """Return the required seed shared by every stochastic training component."""
    raw_seed = os.environ.get("CLIMB_SEGMENT_SEED")
    if raw_seed is None:
        raise SystemExit("set CLIMB_SEGMENT_SEED explicitly")
    try:
        return int(raw_seed)
    except ValueError as exc:
        raise SystemExit("CLIMB_SEGMENT_SEED must be an integer") from exc


def _runner_cfg_from_env() -> RslRlOnPolicyRunnerCfg:
    """Build a fresh runner config with explicit seed and ledger cadence."""
    runner_cfg = unitree_g1_tracking_ppo_runner_cfg()
    runner_cfg.seed = _seed_from_env()
    runner_cfg.save_interval = int(
        os.environ.get("CLIMB_SEGMENT_SAVE_INTERVAL", runner_cfg.save_interval)
    )
    if runner_cfg.save_interval <= 0:
        raise SystemExit("CLIMB_SEGMENT_SAVE_INTERVAL must be positive")
    return runner_cfg


def _register_tasks() -> None:
    clips_path = os.environ.get("CLIMB_CLIPS")
    manifest = os.environ.get("CLIMB_SEGMENT_MANIFEST")
    if not clips_path or not manifest:
        raise SystemExit("set CLIMB_CLIPS and CLIMB_SEGMENT_MANIFEST")
    bank = os.environ.get("CLIMB_BANK", os.path.dirname(clips_path))
    files = read_clip_list(clips_path, bank)
    sampler_seed = _seed_from_env()
    failure_penalty = float(os.environ.get("CLIMB_SEGMENT_FAILURE_PENALTY", "-10"))
    verify_hashes = os.environ.get("CLIMB_VERIFY_MOTION_HASHES", "1") != "0"
    rank = _rank_from_env()
    difficulty_default = "1" if rank == "failure" else "0"
    exploration_ratio = float(
        os.environ.get("CLIMB_SEGMENT_EXPLORATION_RATIO", "0.1")
    )
    difficulty_power = float(
        os.environ.get("CLIMB_SEGMENT_DIFFICULTY_POWER", difficulty_default)
    )
    progress_window = int(os.environ.get("CLIMB_SEGMENT_PROGRESS_WINDOW", "10"))
    progress_floor = float(os.environ.get("CLIMB_SEGMENT_PROGRESS_FLOOR", "0.01"))
    max_unit_probability = float(
        os.environ.get("CLIMB_SEGMENT_MAX_UNIT_PROBABILITY", "0.05")
    )
    max_clip_probability = float(
        os.environ.get("CLIMB_SEGMENT_MAX_CLIP_PROBABILITY", "0.25")
    )
    for task_id, mode in TASKS.items():
        runner_cfg = _runner_cfg_from_env()
        register_mjlab_task(
            task_id=task_id,
            env_cfg=segment_native_g1_tracking_env_cfg(
                motion_files=files,
                segment_manifest=manifest,
                segment_sampling_mode=mode,
                sampler_seed=sampler_seed,
                env_seed=sampler_seed,
                segment_rank=rank,
                segment_exploration_ratio=exploration_ratio,
                segment_difficulty_power=difficulty_power,
                segment_progress_window=progress_window,
                segment_progress_floor=progress_floor,
                max_unit_probability=max_unit_probability,
                max_clip_probability=max_clip_probability,
                verify_motion_hashes=verify_hashes,
                failure_penalty=failure_penalty,
            ),
            play_env_cfg=segment_native_g1_tracking_env_cfg(
                motion_files=files,
                segment_manifest=manifest,
                segment_sampling_mode=mode,
                sampler_seed=sampler_seed,
                env_seed=sampler_seed,
                segment_rank=rank,
                segment_exploration_ratio=exploration_ratio,
                segment_difficulty_power=difficulty_power,
                segment_progress_window=progress_window,
                segment_progress_floor=progress_floor,
                max_unit_probability=max_unit_probability,
                max_clip_probability=max_clip_probability,
                play=True,
                verify_motion_hashes=verify_hashes,
                failure_penalty=failure_penalty,
            ),
            rl_cfg=runner_cfg,
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
            checkpoint = Path(path).resolve()
            stats["checkpoint"] = {
                "path": str(checkpoint),
                "sha256": _sha256_file(checkpoint),
            }
            stats["training_entrypoint_sha256"] = _sha256_file(
                Path(__file__).resolve()
            )
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
