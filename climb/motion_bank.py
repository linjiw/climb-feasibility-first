"""A multi-clip motion bank for mjlab's tracking task.

mjlab's ``MotionLoader`` holds exactly one clip and ``MotionCommand`` indexes it
with a single ``time_steps`` tensor. Rather than restructure that indexing, this
bank concatenates every clip along the time axis and keeps a per-clip offset
table, so ``time_steps`` becomes a *global* index into the concatenation and all
of the command's ~20 accessors keep working untouched.

    clip 0            clip 1        clip 2
    [==========][===============][=======]
     ^clip_start[1]=10            ^clip_start[2]=25

    global index = clip_start[clip_id] + local_frame
"""

from __future__ import annotations

import os

import numpy as np
import torch


class MotionBank:
    """Concatenated multi-clip reference motion.

    Exposes the same field names as mjlab's ``MotionLoader`` (``joint_pos``,
    ``body_pos_w``, ...) so it is a drop-in replacement, plus ``clip_start`` /
    ``clip_len`` for resolving a global frame index.
    """

    _FIELDS = ("joint_pos", "joint_vel", "body_pos_w", "body_quat_w",
               "body_lin_vel_w", "body_ang_vel_w")

    def __init__(
        self,
        motion_files: list[str],
        body_indexes: torch.Tensor,
        device: str = "cpu",
        expected_fps: float | None = None,
    ) -> None:
        if not motion_files:
            raise ValueError("motion bank is empty")

        parts: dict[str, list[torch.Tensor]] = {k: [] for k in self._FIELDS}
        starts, lens, names, fps_seen = [], [], [], set()
        cursor = 0

        for path in motion_files:
            data = np.load(path)
            missing = [k for k in self._FIELDS if k not in data]
            if missing:
                raise KeyError(f"{path}: missing keys {missing}")
            n = int(data["joint_pos"].shape[0])
            if n < 2:
                raise ValueError(f"{path}: only {n} frame(s)")
            for k in self._FIELDS:
                parts[k].append(torch.tensor(data[k], dtype=torch.float32, device=device))
            fps_seen.add(float(np.asarray(data["fps"]).reshape(-1)[0]))
            starts.append(cursor)
            lens.append(n)
            names.append(os.path.splitext(os.path.basename(path))[0])
            cursor += n

        # A bank whose clips disagree on playback rate would advance different
        # envs at different real-time speeds against one shared control dt.
        if len(fps_seen) != 1:
            raise ValueError(f"clips disagree on fps: {sorted(fps_seen)}")
        self.fps = fps_seen.pop()
        if expected_fps is not None and abs(self.fps - expected_fps) > 1e-6:
            raise ValueError(f"bank is {self.fps} fps, env expects {expected_fps}")

        self.joint_pos = torch.cat(parts["joint_pos"])
        self.joint_vel = torch.cat(parts["joint_vel"])
        self._body_pos_w = torch.cat(parts["body_pos_w"])
        self._body_quat_w = torch.cat(parts["body_quat_w"])
        self._body_lin_vel_w = torch.cat(parts["body_lin_vel_w"])
        self._body_ang_vel_w = torch.cat(parts["body_ang_vel_w"])

        self._body_indexes = body_indexes
        self.body_pos_w = self._body_pos_w[:, body_indexes]
        self.body_quat_w = self._body_quat_w[:, body_indexes]
        self.body_lin_vel_w = self._body_lin_vel_w[:, body_indexes]
        self.body_ang_vel_w = self._body_ang_vel_w[:, body_indexes]

        self.clip_start = torch.tensor(starts, dtype=torch.long, device=device)
        self.clip_len = torch.tensor(lens, dtype=torch.long, device=device)
        self.clip_names = names
        self.num_clips = len(names)
        self.time_step_total = cursor

    @property
    def duration_s(self) -> float:
        return self.time_step_total / self.fps

    def global_index(self, clip_ids: torch.Tensor, local: torch.Tensor) -> torch.Tensor:
        """Resolve (clip, local frame) to an index into the concatenated tensors."""
        return self.clip_start[clip_ids] + torch.minimum(
            local, self.clip_len[clip_ids] - 1
        )

    def clip_end(self, clip_ids: torch.Tensor) -> torch.Tensor:
        """First global index past the end of each env's current clip."""
        return self.clip_start[clip_ids] + self.clip_len[clip_ids]

    def summary(self) -> str:
        secs = (self.clip_len.float() / self.fps)
        return (f"{self.num_clips} clips, {self.duration_s / 3600:.2f} h @ {self.fps:g} fps, "
                f"clip length min/median/max = {secs.min():.1f}/"
                f"{secs.median():.1f}/{secs.max():.1f} s")
