"""CLIMB environment config: the G1 tracking task over a bank of clips.

Built by taking mjlab's own G1 tracking config and replacing only the motion
command, so every reward, termination, observation and randomisation term stays
byte-identical to upstream. Sampling strategy is then the single manipulated
variable across experimental arms, which is what the compute-matched comparison
in the plan requires.
"""

from __future__ import annotations

import dataclasses
import os

from mjlab.tasks.tracking.config.g1.env_cfgs import unitree_g1_flat_tracking_env_cfg
from mjlab.tasks.tracking.mdp import MotionCommandCfg

from .commands import MultiClipMotionCommandCfg


def read_clip_list(path: str, bank_dir: str) -> list[str]:
    """Resolve a newline-delimited list of clip names to .npz paths."""
    with open(path) as fh:
        names = [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]
    files, missing = [], []
    for n in names:
        p = n if n.endswith(".npz") else os.path.join(bank_dir, n + ".npz")
        (files if os.path.exists(p) else missing).append(p)
    if missing:
        raise FileNotFoundError(
            f"{len(missing)} clip(s) from {path} not in {bank_dir}, e.g. {missing[:3]}"
        )
    return files


def climb_g1_tracking_env_cfg(
    motion_files: list[str] | None = None,
    sampling_mode: str = "uniform",
    clip_uniform_ratio: float = 0.1,
    play: bool = False,
):
    """G1 flat tracking over a multi-clip bank."""
    cfg = unitree_g1_flat_tracking_env_cfg(play=play)

    base = cfg.commands["motion"]
    assert isinstance(base, MotionCommandCfg)
    # Carry every field across rather than restating them, so upstream changes
    # to pose/velocity randomisation ranges are inherited automatically.
    shared = {
        f.name: getattr(base, f.name)
        for f in dataclasses.fields(base)
        if f.name not in ("motion_files", "clip_uniform_ratio",
                          "clip_adaptive_alpha", "sampling_mode")
    }
    files = list(motion_files or [])
    # train.py refuses to start a tracking task whose motion_file is empty.
    # Point it at the first clip: the bank supersedes it, but it keeps that
    # guard meaningful and gives the logged config a concrete reference.
    shared["motion_file"] = files[0] if files else ""
    cfg.commands["motion"] = MultiClipMotionCommandCfg(
        **shared,
        motion_files=files,
        sampling_mode=sampling_mode,  # type: ignore[arg-type]
        clip_uniform_ratio=clip_uniform_ratio,
    )
    return cfg
