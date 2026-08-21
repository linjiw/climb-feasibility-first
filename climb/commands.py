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

from .eligibility import (
    EligibilityMode,
    EligibilityState,
    clip_sampling_probabilities,
    eligibility_set_hash,
    eligible_entropy,
    load_bank_eligibility,
    sample_eligible_local_frames,
    sampling_ineligible_mass,
    validate_fgas_config,
)
from .motion_bank import MotionBank

if TYPE_CHECKING:
    from mjlab.envs import ManagerBasedRlEnv


class MultiClipMotionCommand(MotionCommand):
    """A ``MotionCommand`` whose reference is a bank of clips."""

    cfg: MultiClipMotionCommandCfg
    motion: MotionBank

    def __init__(self, cfg: MultiClipMotionCommandCfg, env: ManagerBasedRlEnv):
        if not cfg.motion_files:
            raise ValueError("MultiClipMotionCommandCfg.motion_files is empty")
        validate_fgas_config(
            cfg.eligibility_path, cfg.eligibility_mode, cfg.sampling_mode
        )
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
        self._grounding: Literal["additive", "mixture"] = (
            "mixture" if cfg.sampling_mode == "grounded" else "additive"
        )

        self.motion = MotionBank(
            cfg.motion_files, self.body_indexes, device=self.device
        )
        self.clip_ids = torch.zeros(self.num_envs, dtype=torch.long, device=self.device)
        self._force_start = False
        self._eligibility_state: EligibilityState | None = None

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
        if cfg.eligibility_path is not None:
            for key in (
                "sampling_ineligible_mass",
                "sampling_eligible_entropy",
                "sampling_clips_without_sidecar_frac",
            ):
                self.metrics[key] = torch.zeros(self.num_envs, device=self.device)
        print(f"[climb] motion bank: {self.motion.summary()}")

    # -- clip choice ------------------------------------------------------

    def _ensure_eligibility(self) -> EligibilityState | None:
        """Load eligibility lazily, after the base loader has become a bank."""
        if self.cfg.eligibility_path is None:
            return None
        if self._eligibility_state is None:
            self._eligibility_state = load_bank_eligibility(
                path=self.cfg.eligibility_path,
                clip_names=self.motion.clip_names,
                clip_start=self.motion.clip_start,
                clip_len=self.motion.clip_len,
                fps=self.motion.fps,
                mode=self.cfg.eligibility_mode,
                hard_threshold=self.cfg.eligibility_hard_threshold,
                device=self.device,
            )
        return self._eligibility_state

    def _clip_probabilities(self) -> torch.Tensor:
        n = self.motion.num_clips
        uniform = torch.full((n,), 1.0 / n, device=self.device)
        if not self._weight_by_failure:
            return uniform

        state = self._ensure_eligibility()
        applied = None if state is None else state.clip_applied
        return clip_sampling_probabilities(
            self.clip_failed_ema,
            self.cfg.clip_uniform_ratio,
            self._grounding,
            applied,
        )

    def _sample_clips(self, count: int) -> torch.Tensor:
        p = self._clip_probabilities()
        clips = torch.multinomial(p, count, replacement=True)
        H = -(p * (p + 1e-12).log()).sum()
        self.metrics["sampling_clip_entropy"][:] = (
            H / math.log(self.motion.num_clips) if self.motion.num_clips > 1 else 1.0
        )
        self.metrics["sampling_clip_top1_prob"][:] = p.max()
        state = self._ensure_eligibility()
        if state is not None:
            self.metrics["sampling_ineligible_mass"][:] = sampling_ineligible_mass(
                p, state, self.motion.clip_start, self.motion.clip_len
            )
            self.metrics["sampling_eligible_entropy"][:] = eligible_entropy(
                p, state.clip_screen
            )
            self.metrics["sampling_clips_without_sidecar_frac"][:] = (
                state.clips_without_sidecar_frac
            )
        return clips

    def _count_exposure(self, env_ids: torch.Tensor) -> None:
        """Tally the episodes ending on ``env_ids``, keyed by the clip they ran.

        ``clip_ids[env_ids]`` still names the *outgoing* clip at this point, so
        this has to run before ``_place`` overwrites it.

        Envs whose episode length is still zero are the startup reset, not a
        finished episode; counting them would credit ``num_envs`` phantom
        episodes to whichever clip ``clip_ids`` was initialised to (clip 0).
        ``ManagerBasedRlEnv._reset_idx`` zeroes ``episode_length_buf`` *after*
        it resets the command manager, so the buffer read here still holds the
        outgoing episode's length.
        """
        ran = self._env.episode_length_buf[env_ids] > 0
        clips = self.clip_ids[env_ids]
        terminated = self._env.termination_manager.terminated[env_ids] & ran
        if torch.any(terminated):
            self._clip_failed_now[:] = torch.bincount(
                clips[terminated], minlength=self.motion.num_clips
            ).float()
            self.clip_failures += self._clip_failed_now
        self.clip_episodes += torch.bincount(
            clips[ran], minlength=self.motion.num_clips
        ).float()

    def _place(
        self, env_ids: torch.Tensor, clips: torch.Tensor, count_exposure: bool = True
    ) -> None:
        """Seat each env on its clip, at frame 0 or a uniform position within.

        Exposure is tallied here rather than inside one sampler because every
        sampler routes through this method. Counting it in ``_adaptive_sampling``
        instead left ``clip_episodes`` and ``clip_failures`` identically zero on
        the uniform arm -- which is every E-HYG and N3 arm -- so
        ``per_clip_stats`` returned a row of zeros that reads like a measured
        "this clip was never sampled" rather than like an absent instrument.

        ``assign_clips`` opts out: evaluation pins clips deterministically, and
        folding that into the training-exposure ledger would mix the two.
        """
        if count_exposure:
            self._count_exposure(env_ids)
        lens = self.motion.clip_len[clips]
        if self._force_start:
            local = torch.zeros_like(lens)
        else:
            # Uniform over clips then uniform within, so every clip is equally
            # likely regardless of length. Uniform over *frames* would weight by
            # duration, and this bank spans 3.7 s to 264 s -- a 70x spread that
            # would quietly turn the control arm into a length-weighted
            # curriculum and confound the comparison it is meant to anchor.
            local = sample_eligible_local_frames(
                self._ensure_eligibility(),
                self.motion.clip_start,
                self.motion.clip_len,
                clips,
            )
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
        # The failure/episode tally that used to live here now runs in _place,
        # which this call reaches -- and which the uniform arm reaches too.
        self._place(env_ids, self._sample_clips(len(env_ids)))
        p = self._clip_probabilities()
        self.metrics["sampling_entropy"][:] = self.metrics["sampling_clip_entropy"][0]
        self.metrics["sampling_top1_prob"][:] = p.max()
        self.metrics["sampling_top1_bin"][:] = (
            p.argmax().float() / self.motion.num_clips
        )

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

        wrap_ids = torch.where(self.time_steps >= self.motion.clip_end(self.clip_ids))[
            0
        ]
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
            self._place(env_ids, clip_ids, count_exposure=False)
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

    def per_clip_stats(self) -> dict[str, object]:
        """Episode and failure counts per clip, for the difficulty atlas."""
        ep = self.clip_episodes.cpu().tolist()
        fa = self.clip_failures.cpu().tolist()
        stats = {
            "clip": list(self.motion.clip_names),
            "episodes": ep,
            "failures": fa,
            "failure_rate": [f / e if e > 0 else float("nan") for e, f in zip(ep, fa)],
            "sampling_weight": self._clip_probabilities().cpu().tolist(),
        }
        state = self._ensure_eligibility()
        if state is not None:
            stats.update(
                {
                    "eligibility_mode": self.cfg.eligibility_mode,
                    "eligibility_set_hash": eligibility_set_hash(
                        self.cfg.eligibility_path or ""
                    ),
                    "clip_eligibility_screen": state.clip_screen.cpu().tolist(),
                    "clip_eligibility_applied": None
                    if state.clip_applied is None
                    else state.clip_applied.cpu().tolist(),
                }
            )
        return stats


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
    eligibility_path: str | None = None
    """Directory or JSON bundle containing per-clip eligibility sidecars."""
    eligibility_mode: EligibilityMode = "off"
    """Measure only (off), exclude hard bins, or weight by continuous score."""
    eligibility_hard_threshold: float = 0.5
    """Eligible-frame fraction required for a clip to pass the hard screen."""
    sampling_mode: Literal["adaptive", "grounded", "uniform", "start"] = "uniform"

    def build(self, env: ManagerBasedRlEnv) -> MultiClipMotionCommand:
        return MultiClipMotionCommand(self, env)
