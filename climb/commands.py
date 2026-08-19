"""Multi-clip motion command with clip-level samplers.

Extends mjlab's single-clip ``MotionCommand`` along the axis CLIMB needs: which
*clip* an environment tracks, not just where within one clip it starts. mjlab
already samples the start frame inside a clip -- its ``adaptive`` mode is
BeyondMimic-style failure-weighted bin sampling with an epsilon-uniform floor --
but the clip axis does not exist upstream.

Sampling modes reuse the base class's names so its dispatch calls the overrides
here, giving the two comparator arms the experiment matrix needs:

    uniform    uniform clip, uniform frame within        (control arm)
    adaptive   p ~ failureEMA + eps/N, then normalise    (error-adaptive arm)
    grounded   p = (1-eps)*failureEMA_hat + eps*uniform  (grounded arm)
    start      frame 0 of a uniformly chosen clip        (playback / eval)

adaptive and grounded differ only in how the uniform prior is combined, which
turns out to matter a great deal. The additive form is mjlab's, and its uniform
term contributes eps/(sum(q)+eps) of the mass -- progressively swamped as
failure mass concentrates. Measured here on 100 clips with eps=0.1, one clip
reached 78% of all sampling mass and normalised entropy fell to 0.22 despite the
nominal "10% uniform floor". The convex mixture holds exactly eps of the mass
regardless, which is the minimal form of the plan's grounding term.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

import torch

from mjlab.tasks.tracking.mdp.commands import MotionCommand, MotionCommandCfg

from .motion_bank import MotionBank

if TYPE_CHECKING:
    from mjlab.envs import ManagerBasedRlEnv


class MultiClipMotionCommand(MotionCommand):
    """A ``MotionCommand`` whose reference is a bank of clips."""

    cfg: MultiClipMotionCommandCfg

    def __init__(self, cfg: MultiClipMotionCommandCfg, env: ManagerBasedRlEnv):
        if not cfg.motion_files:
            raise ValueError("MultiClipMotionCommandCfg.motion_files is empty")
        # The base class builds a single-clip loader from cfg.motion_file and
        # derives body indices and metric buffers from it. Let it do that with
        # the first clip, then swap in the bank: every accessor it defines
        # indexes self.motion by a flat frame index, which the bank preserves.
        cfg.motion_file = cfg.motion_files[0]
        super().__init__(cfg, env)

        # Resolved once, because _resample_command temporarily rewrites
        # cfg.sampling_mode to borrow the base class's dispatch. Reading the
        # mode inside _clip_probabilities would then silently take the wrong
        # branch and turn the grounded arm back into the additive one.
        self._weight_by_failure = cfg.sampling_mode in ("adaptive", "grounded")
        self._grounding = "mixture" if cfg.sampling_mode == "grounded" else "additive"

        self.motion = MotionBank(cfg.motion_files, self.body_indexes, device=self.device)
        self.clip_ids = torch.zeros(self.num_envs, dtype=torch.long, device=self.device)
        self._force_start = False

        n = self.motion.num_clips
        # Per-clip failure statistics: the clip-axis analogue of the base
        # class's per-bin counters.
        self.clip_failed_ema = torch.zeros(n, device=self.device)
        self._clip_failed_now = torch.zeros(n, device=self.device)
        self.clip_episodes = torch.zeros(n, device=self.device)
        self.clip_failures = torch.zeros(n, device=self.device)

        for key in ("sampling_clip_entropy", "sampling_clip_top1_prob"):
            self.metrics[key] = torch.zeros(self.num_envs, device=self.device)
        self.metrics["bank_clip_count"] = torch.full(
            (self.num_envs,), float(n), device=self.device
        )
        print(f"[climb] motion bank: {self.motion.summary()}")

    # -- clip choice ------------------------------------------------------

    def _clip_probabilities(self) -> torch.Tensor:
        n = self.motion.num_clips
        uniform = torch.full((n,), 1.0 / n, device=self.device)
        if not self._weight_by_failure:
            return uniform

        q = self.clip_failed_ema
        eps = self.cfg.clip_uniform_ratio

        if self._grounding == "mixture":
            # Convex mixture: the uniform component keeps exactly eps of the
            # mass whatever the failure signal does.
            q = q / q.sum() if float(q.sum()) > 0 else uniform
            return (1.0 - eps) * q + eps * uniform

        # Additive offset -- mjlab's formulation, ported to the clip axis. The
        # uniform term contributes eps / (sum(q) + eps) of the mass, so it is
        # progressively swamped as failure mass accumulates. Measured on a
        # 100-clip bank with eps=0.1, this let a single clip reach 78% of all
        # sampling mass and normalised entropy fall to 0.22, despite the
        # nominal "10% uniform floor". Kept as-is because it is the honest
        # reproduction of the error-adaptive baseline.
        p = q + eps / n
        return p / p.sum()

    def _sample_clips(self, count: int) -> torch.Tensor:
        p = self._clip_probabilities()
        clips = torch.multinomial(p, count, replacement=True)
        H = -(p * (p + 1e-12).log()).sum()
        self.metrics["sampling_clip_entropy"][:] = (
            H / math.log(self.motion.num_clips) if self.motion.num_clips > 1 else 1.0
        )
        self.metrics["sampling_clip_top1_prob"][:] = p.max()
        return clips

    def _place(self, env_ids: torch.Tensor, clips: torch.Tensor) -> None:
        """Seat each env on its clip, at frame 0 or a uniform position within."""
        lens = self.motion.clip_len[clips]
        if self._force_start:
            local = torch.zeros_like(lens)
        else:
            # Uniform over clips then uniform within, so every clip is equally
            # likely regardless of length. Uniform over *frames* would weight by
            # duration, and this bank spans 3.7 s to 264 s -- a 70x spread that
            # would quietly turn the control arm into a length-weighted
            # curriculum and confound the comparison it is meant to anchor.
            local = (torch.rand(len(clips), device=self.device) * lens.float()).long()
        self.clip_ids[env_ids] = clips
        self.time_steps[env_ids] = self.motion.global_index(clips, local)

    # -- samplers (names match the base dispatch) -------------------------

    def _uniform_sampling(self, env_ids: torch.Tensor):
        self._place(env_ids, self._sample_clips(len(env_ids)))
        self.metrics["sampling_entropy"][:] = 1.0
        self.metrics["sampling_top1_prob"][:] = 1.0 / self.motion.num_clips
        self.metrics["sampling_top1_bin"][:] = 0.5

    def _adaptive_sampling(self, env_ids: torch.Tensor):
        """Clip-level failure-weighted sampling: the error-adaptive comparator."""
        terminated = self._env.termination_manager.terminated[env_ids]
        if torch.any(terminated):
            failed = self.clip_ids[env_ids][terminated]
            self._clip_failed_now[:] = torch.bincount(
                failed, minlength=self.motion.num_clips
            ).float()
            self.clip_failures += self._clip_failed_now
        self.clip_episodes += torch.bincount(
            self.clip_ids[env_ids], minlength=self.motion.num_clips
        ).float()

        self._place(env_ids, self._sample_clips(len(env_ids)))
        p = self._clip_probabilities()
        self.metrics["sampling_entropy"][:] = self.metrics["sampling_clip_entropy"][0]
        self.metrics["sampling_top1_prob"][:] = p.max()
        self.metrics["sampling_top1_bin"][:] = p.argmax().float() / self.motion.num_clips

    def _resample_command(self, env_ids: torch.Tensor):
        # "start" is not a base-class code path for a bank (it would seat every
        # env at frame 0 of clip 0), so route it through the uniform branch with
        # the in-clip position pinned, reusing the base's pose-writing tail.
        if self.cfg.sampling_mode == "start":
            self._force_start = True
            self.cfg.sampling_mode = "uniform"
            try:
                super()._resample_command(env_ids)
            finally:
                self.cfg.sampling_mode = "start"
                self._force_start = False
        elif self.cfg.sampling_mode == "grounded":
            # The base dispatch asserts the mode is one of its own three, so
            # borrow the "adaptive" branch: it calls _adaptive_sampling, whose
            # clip weights already come from _clip_probabilities and are
            # therefore grounded.
            self.cfg.sampling_mode = "adaptive"
            try:
                super()._resample_command(env_ids)
            finally:
                self.cfg.sampling_mode = "grounded"
        else:
            super()._resample_command(env_ids)

    # -- time advance -----------------------------------------------------

    def _update_command(self, env_ids: torch.Tensor | None = None):
        # As the base class, except a clip ends at its own boundary rather than
        # at the end of one global timeline.
        if env_ids is None:
            self.time_steps += 1
        else:
            self.time_steps[env_ids] += 1

        wrap_ids = torch.where(self.time_steps >= self.motion.clip_end(self.clip_ids))[0]
        if wrap_ids.numel() > 0:
            self._resample_command(wrap_ids)

        if self._pending_forward:
            self._pending_forward = False
            self._env.sim.forward()
        self.update_relative_body_poses()

        if env_ids is None and self._weight_by_failure:
            a = self.cfg.clip_adaptive_alpha
            self.clip_failed_ema = (
                a * self._clip_failed_now + (1 - a) * self.clip_failed_ema
            )
            self._clip_failed_now.zero_()

    # -- deterministic control, for evaluation ----------------------------

    def assign_clips(self, clip_ids: torch.Tensor, at_start: bool = True) -> None:
        """Pin each environment to a specific clip.

        Training samples clips stochastically, which is the wrong instrument for
        measuring per-clip difficulty: coverage would be uneven and confounded
        with whatever the sampler is currently favouring. Evaluation assigns
        every clip a fixed set of environments instead.
        """
        env_ids = torch.arange(self.num_envs, device=self.device)
        clip_ids = clip_ids.to(self.device, torch.long)
        self._force_start = at_start
        try:
            self._place(env_ids, clip_ids)
        finally:
            self._force_start = False
        self._finalize_reference(env_ids)

    def _finalize_reference(self, env_ids: torch.Tensor) -> None:
        """Teleport the robot onto the newly assigned reference frame."""
        root_pos = self.body_pos_w[env_ids, 0].clone()
        root_ori = self.body_quat_w[env_ids, 0].clone()
        self._write_reference_state_to_sim(
            env_ids,
            root_pos,
            root_ori,
            self.body_lin_vel_w[env_ids, 0].clone(),
            self.body_ang_vel_w[env_ids, 0].clone(),
            self.joint_pos[env_ids].clone(),
            self.joint_vel[env_ids].clone(),
        )
        self._env.sim.forward()
        self.update_relative_body_poses()

    # -- telemetry --------------------------------------------------------

    def per_clip_stats(self) -> dict[str, list]:
        """Episode and failure counts per clip, for the difficulty atlas."""
        ep = self.clip_episodes.cpu().tolist()
        fa = self.clip_failures.cpu().tolist()
        return {
            "clip": list(self.motion.clip_names),
            "episodes": ep,
            "failures": fa,
            "failure_rate": [f / e if e > 0 else float("nan") for e, f in zip(ep, fa)],
            "sampling_weight": self._clip_probabilities().cpu().tolist(),
        }


@dataclass
class MultiClipMotionCommandCfg(MotionCommandCfg):
    motion_files: list[str] = field(default_factory=list)
    clip_uniform_ratio: float = 0.1
    """Epsilon-uniform floor mixed into the clip distribution.

    The clip-axis counterpart of mjlab's ``adaptive_uniform_ratio``, and the
    crude form of a grounding term: a fixed mixture with the uniform prior
    rather than a divergence from the deployment distribution.
    """
    clip_adaptive_alpha: float = 0.01
    sampling_mode: Literal["adaptive", "grounded", "uniform", "start"] = "uniform"

    def build(self, env: ManagerBasedRlEnv) -> MultiClipMotionCommand:
        return MultiClipMotionCommand(self, env)
