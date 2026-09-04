"""Environment configuration for the unsealed segment-native experiment."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from mjlab.envs import mdp
from mjlab.managers.reward_manager import RewardTermCfg
from mjlab.managers.termination_manager import TerminationTermCfg

from .env_cfg import climb_g1_tracking_env_cfg
from .segment_command import (
    SegmentNativeMotionCommandCfg,
    segment_trial_timeout,
)
from .segment_runtime import RankMode, SamplingMode


def segment_native_g1_tracking_env_cfg(
    *,
    motion_files: list[str],
    segment_manifest: str,
    segment_sampling_mode: SamplingMode = "adaptive",
    sampler_seed: int = 0,
    env_seed: int | None = None,
    segment_rank: RankMode = "failure",
    segment_exploration_ratio: float = 0.1,
    segment_difficulty_power: float = 1.0,
    segment_progress_window: int = 10,
    segment_progress_floor: float = 0.01,
    max_unit_probability: float | None = 0.05,
    max_clip_probability: float | None = 0.25,
    play: bool = False,
    verify_motion_hashes: bool = True,
    failure_penalty: float = -10.0,
):
    """Build the ordinary G1 tracker with an exact segment trial command."""
    if failure_penalty > 0.0:
        raise ValueError("failure_penalty must be non-positive")
    cfg = climb_g1_tracking_env_cfg(
        motion_files=motion_files,
        sampling_mode="uniform",
        eligibility_path=None,
        eligibility_mode="off",
        play=play,
    )
    base = cfg.commands["motion"]
    shared = {field.name: getattr(base, field.name) for field in dataclasses.fields(base)}
    cfg.commands["motion"] = SegmentNativeMotionCommandCfg(
        **shared,
        segment_manifest=segment_manifest,
        segment_sampling_mode=segment_sampling_mode,
        sampler_seed=sampler_seed,
        segment_rank=segment_rank,
        segment_exploration_ratio=segment_exploration_ratio,
        segment_difficulty_power=segment_difficulty_power,
        segment_progress_window=segment_progress_window,
        segment_progress_floor=segment_progress_floor,
        max_unit_probability=max_unit_probability,
        max_clip_probability=max_clip_probability,
        verify_motion_hashes=verify_motion_hashes,
    )
    # The fixed segment horizon is the only time limit.  Keeping the upstream
    # 10 s episode timeout would let RSL-RL's random initial episode lengths
    # censor a subset of first trials before their declared segment boundary.
    cfg.terminations.pop("time_out", None)
    cfg.terminations["segment_trial"] = TerminationTermCfg(
        func=segment_trial_timeout,
        time_out=True,
        params={"command_name": "motion"},
    )
    step_dt = cfg.sim.mujoco.timestep * cfg.decimation
    manifest = json.loads(Path(segment_manifest).read_text())
    horizon_steps = int(manifest["horizon_steps"])
    cfg.episode_length_s = horizon_steps * step_dt
    if failure_penalty:
        # RewardManager scales every term by dt.  Divide here so the configured
        # value is the actual one-off cost of a failure, not a rate whose
        # meaning changes with control frequency.  Segment time-outs are not
        # included by mdp.is_terminated.
        cfg.rewards["failure_terminal"] = RewardTermCfg(
            func=mdp.is_terminated,
            weight=failure_penalty / step_dt,
        )
    cfg.seed = env_seed
    cfg.is_finite_horizon = False
    return cfg
