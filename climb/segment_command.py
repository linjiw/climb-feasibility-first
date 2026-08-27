"""Exact fixed-horizon motion command for the unsealed segment-v2 experiment.

This module is intentionally separate from the frozen FGAS command.  It turns
the pure :mod:`climb.segment_runtime` sampler into an mjlab command while
preserving one critical MDP invariant: a sampled segment ends as an explicit
time-out before its reference can wrap or teleport inside a continuing
transition.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import torch

from .commands import MultiClipMotionCommand, MultiClipMotionCommandCfg
from .segment_curriculum import validate_sampling_concentration
from .segment_runtime import RankMode, SamplingMode, SegmentSampler

if TYPE_CHECKING:
    from mjlab.envs import ManagerBasedRlEnv


def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class SegmentNativeMotionCommand(MultiClipMotionCommand):
    """Track exact feasible segments as independent fixed-horizon trials."""

    cfg: SegmentNativeMotionCommandCfg

    def __init__(
        self, cfg: SegmentNativeMotionCommandCfg, env: ManagerBasedRlEnv
    ) -> None:
        if cfg.sampling_mode != "uniform":
            raise ValueError(
                "segment-v2 reserves base sampling_mode='uniform'; use "
                "segment_sampling_mode for the segment curriculum"
            )
        if min(cfg.resampling_time_range) <= env.max_episode_length_s:
            raise ValueError(
                "the command timer must outlive an episode; segment boundaries "
                "are handled by an explicit termination"
            )
        if cfg.curriculum_update_interval_steps <= 0:
            raise ValueError("curriculum_update_interval_steps must be positive")

        super().__init__(cfg, env)
        self.sampler = SegmentSampler(
            cfg.segment_manifest,
            mode=cfg.segment_sampling_mode,
            seed=cfg.sampler_seed,
            exploration_ratio=cfg.segment_exploration_ratio,
            difficulty_power=cfg.segment_difficulty_power,
            decay=cfg.segment_decay,
            prior_rate=cfg.segment_prior_rate,
            prior_strength=cfg.segment_prior_strength,
            max_unit_probability=cfg.max_unit_probability,
            max_clip_probability=cfg.max_clip_probability,
            rank=cfg.segment_rank,
            progress_window=cfg.segment_progress_window,
            progress_floor=cfg.segment_progress_floor,
        )
        self._validate_manifest_sources(cfg.motion_files)
        frames_per_step = self.motion.fps * env.step_dt
        if not math.isclose(frames_per_step, 1.0, abs_tol=1.0e-6):
            raise ValueError(
                "segment-v2 requires one reference frame per environment step; "
                f"got fps*step_dt={frames_per_step}"
            )
        validate_sampling_concentration(
            self.sampler.probabilities,
            max_top1_probability=cfg.max_top1_probability,
            min_entropy_effective_units=cfg.min_entropy_effective_units,
        )

        self.active_table_indices = torch.full(
            (self.num_envs,), -1, dtype=torch.long, device=self.device
        )
        self.active_unit_ids = torch.full_like(self.active_table_indices, -1)
        self.local_start_steps = torch.full_like(self.active_table_indices, -1)
        self.local_trial_end_steps = torch.full_like(
            self.active_table_indices, -1
        )
        self.local_segment_stop_steps = torch.full_like(
            self.active_table_indices, -1
        )
        self.trial_end_steps = torch.full_like(self.active_table_indices, -1)
        self.segment_start_steps = torch.full_like(self.active_table_indices, -1)
        self.segment_stop_steps = torch.full_like(self.active_table_indices, -1)

        self.completed_trials = 0
        self.failed_trials = 0
        self.censored_resets = 0
        self.invalid_start_count = 0
        self.invalid_reference_frame_count = 0
        self._last_sampler_update_step = -1

        for key in (
            "sampling_unit_effective_count",
            "sampling_adaptation_total_variation",
            "sampling_rank_saturation_fraction",
            "segment_failure_rate",
            "segment_censored_resets",
            "segment_invalid_start_count",
            "segment_invalid_reference_frame_count",
        ):
            self.metrics[key] = torch.zeros(self.num_envs, device=self.device)
        self._update_sampling_metrics()

    def _validate_manifest_sources(self, motion_files: list[str]) -> None:
        sources = self.sampler.manifest.get("sources", [])
        if len(sources) != self.motion.num_clips or len(motion_files) != len(sources):
            raise ValueError("segment manifest and runtime motion bank differ in size")
        for clip_id, (source, motion_file) in enumerate(
            zip(sources, motion_files, strict=True)
        ):
            expected_name = Path(motion_file).stem
            if (
                source.get("clip_id") != clip_id
                or source.get("clip") != expected_name
                or self.motion.clip_names[clip_id] != expected_name
                or int(source.get("frames", -1))
                != int(self.motion.clip_len[clip_id].item())
                or not math.isclose(
                    float(source.get("fps", -1.0)), self.motion.fps, abs_tol=1.0e-9
                )
            ):
                raise ValueError(
                    f"segment source row {clip_id} does not match {motion_file}"
                )
            cfg_hash = source.get("motion_sha256")
            if not isinstance(cfg_hash, str) or len(cfg_hash) != 64:
                raise ValueError(f"segment source row {clip_id} has no motion hash")
            if self.cfg.verify_motion_hashes and _sha256_file(motion_file) != cfg_hash:
                raise ValueError(f"motion hash mismatch for {motion_file}")

        clip_ids = self.sampler.intervals.clip_ids
        first = self.sampler.intervals.first
        stop = self.sampler.segment_stops
        lengths = self.motion.clip_len.cpu()[clip_ids]
        if bool((clip_ids < 0).any()) or bool((clip_ids >= self.motion.num_clips).any()):
            raise ValueError("segment unit table references an unknown clip")
        if bool((first < 0).any()) or bool((stop > lengths).any()):
            raise ValueError("segment unit table escapes its source clip timeline")

    def _record_outgoing_trials(self, env_ids: torch.Tensor) -> None:
        ran = self._env.episode_length_buf[env_ids] > 0
        if not bool(ran.any()):
            return
        terminated = self._env.termination_manager.terminated[env_ids]
        try:
            segment_timed_out = self._env.termination_manager.get_term(
                self.cfg.segment_timeout_term
            )[env_ids]
        except ValueError as exc:
            raise RuntimeError(
                f"missing segment timeout term {self.cfg.segment_timeout_term!r}"
            ) from exc
        completed = ran & (terminated | segment_timed_out)
        censored = ran & ~completed
        if bool(completed.any()):
            outgoing = self.active_table_indices[env_ids][completed]
            if bool((outgoing < 0).any()):
                raise RuntimeError("completed trial has no active segment unit")
            failed = terminated[completed]
            self.sampler.record_completed_trials(outgoing, failed)
            self.completed_trials += int(completed.sum().item())
            self.failed_trials += int(failed.sum().item())
        self.censored_resets += int(censored.sum().item())

    def _uniform_sampling(self, env_ids: torch.Tensor) -> None:
        """Seat reset environments on exact horizon-safe starts."""
        self._record_outgoing_trials(env_ids)
        samples = self.sampler.sample(len(env_ids))
        table_indices = samples.table_indices.to(self.device)
        unit_ids = samples.unit_ids.to(self.device)
        clip_ids = samples.clip_ids.to(self.device)
        local_starts = samples.local_starts.to(self.device)
        local_trial_ends = samples.local_trial_ends.to(self.device)
        local_segment_stops = samples.local_segment_stops.to(self.device)
        invalid = (local_starts < 0) | (local_trial_ends >= local_segment_stops)
        self.invalid_start_count += int(invalid.sum().item())
        if bool(invalid.any()):
            raise RuntimeError("segment sampler produced an invalid fixed-horizon start")

        clip_starts = self.motion.clip_start[clip_ids]
        self.active_table_indices[env_ids] = table_indices
        self.active_unit_ids[env_ids] = unit_ids
        self.clip_ids[env_ids] = clip_ids
        self.local_start_steps[env_ids] = local_starts
        self.local_trial_end_steps[env_ids] = local_trial_ends
        self.local_segment_stop_steps[env_ids] = local_segment_stops
        self.time_steps[env_ids] = clip_starts + local_starts
        self.trial_end_steps[env_ids] = clip_starts + local_trial_ends
        self.segment_start_steps[env_ids] = clip_starts + local_starts
        self.segment_stop_steps[env_ids] = clip_starts + local_segment_stops
        self._update_sampling_metrics()

    def _update_sampling_metrics(self) -> None:
        diagnostics = self.sampler.concentration()
        probabilities = self.sampler.probabilities
        entropy_norm = (
            math.log(diagnostics.entropy_effective_units) / math.log(self.sampler.num_units)
            if self.sampler.num_units > 1
            else 1.0
        )
        self.metrics["sampling_entropy"][:] = entropy_norm
        self.metrics["sampling_top1_prob"][:] = diagnostics.top1_probability
        self.metrics["sampling_top1_bin"][:] = float(probabilities.argmax()) / max(
            self.sampler.num_units - 1, 1
        )
        self.metrics["sampling_unit_effective_count"][:] = (
            diagnostics.entropy_effective_units
        )
        self.metrics["sampling_adaptation_total_variation"][:] = (
            self.sampler.adaptation_total_variation()
        )
        self.metrics["sampling_rank_saturation_fraction"][:] = (
            self.sampler.saturation_fraction()
        )
        self.metrics["bank_clip_count"][:] = float(self.motion.num_clips)

        clip_mass = torch.zeros(
            self.motion.num_clips, dtype=probabilities.dtype, device="cpu"
        )
        clip_mass.scatter_add_(0, self.sampler.intervals.clip_ids, probabilities)
        positive = clip_mass[clip_mass > 0]
        clip_entropy = -(positive * positive.log()).sum()
        self.metrics["sampling_clip_entropy"][:] = (
            float(clip_entropy / math.log(self.motion.num_clips))
            if self.motion.num_clips > 1
            else 1.0
        )
        self.metrics["sampling_clip_top1_prob"][:] = float(clip_mass.max())

        failure_rate = self.failed_trials / max(self.completed_trials, 1)
        self.metrics["segment_failure_rate"][:] = failure_rate
        self.metrics["segment_censored_resets"][:] = self.censored_resets
        self.metrics["segment_invalid_start_count"][:] = self.invalid_start_count
        self.metrics["segment_invalid_reference_frame_count"][:] = (
            self.invalid_reference_frame_count
        )

    def assert_active_references_valid(self) -> None:
        active = self.active_table_indices >= 0
        invalid = active & (
            (self.time_steps < self.segment_start_steps)
            | (self.time_steps >= self.segment_stop_steps)
            | (self.time_steps > self.trial_end_steps)
        )
        count = int(invalid.sum().item())
        self.invalid_reference_frame_count += count
        if count:
            ids = invalid.nonzero(as_tuple=False).flatten()[:8].cpu().tolist()
            raise RuntimeError(f"segment reference escaped its trial window: envs={ids}")

    def _update_command(self, env_ids: torch.Tensor | None = None) -> None:
        if env_ids is None:
            if self._env.cfg.auto_reset:
                self.time_steps += 1
            else:
                # Manual-reset evaluation keeps terminal environments on the
                # exact reference frame that produced their done signal.
                self.time_steps[~self._env.reset_buf] += 1
        else:
            self.time_steps[env_ids] += 1
        self.assert_active_references_valid()

        if self._pending_forward:
            self._pending_forward = False
            self._env.sim.forward()
        self.update_relative_body_poses()

        if env_ids is None:
            step = int(self._env.common_step_counter)
            if (
                step > 0
                and step % self.cfg.curriculum_update_interval_steps == 0
                and step != self._last_sampler_update_step
            ):
                self.sampler.advance_clock()
                validate_sampling_concentration(
                    self.sampler.probabilities,
                    max_top1_probability=self.cfg.max_top1_probability,
                    min_entropy_effective_units=self.cfg.min_entropy_effective_units,
                )
                self._last_sampler_update_step = step
            self._update_sampling_metrics()

    def segment_telemetry(self) -> dict[str, object]:
        """Return runtime state needed to audit a smoke or checkpoint."""
        concentration = self.sampler.concentration()
        return {
            "schema_version": "segment_command_telemetry/1",
            "mode": self.sampler.mode,
            "unit_table_sha256": self.sampler.manifest["unit_table_sha256"],
            "horizon_steps": self.sampler.horizon_steps,
            "sampler_clock": self.sampler.clock,
            "completed_trials": self.completed_trials,
            "failed_trials": self.failed_trials,
            "censored_resets": self.censored_resets,
            "invalid_start_count": self.invalid_start_count,
            "invalid_reference_frame_count": self.invalid_reference_frame_count,
            "top1_probability": concentration.top1_probability,
            "entropy_effective_units": concentration.entropy_effective_units,
            "adaptation_total_variation": (
                self.sampler.adaptation_total_variation()
            ),
            "rank": self.sampler.rank,
            "rank_saturation_fraction": self.sampler.saturation_fraction(),
            "lifetime_attempts": self.sampler.lifetime_attempts.tolist(),
            "lifetime_failures": self.sampler.lifetime_failures.tolist(),
            "probabilities": self.sampler.probabilities.tolist(),
        }

    def assign_segments(
        self, table_indices: torch.Tensor, local_starts: torch.Tensor
    ) -> None:
        """Assign exact units/starts for paired evaluation, then expose s+1."""
        if table_indices.shape != (self.num_envs,) or local_starts.shape != (
            self.num_envs,
        ):
            raise ValueError("one segment table index and start are required per env")
        table_cpu = table_indices.to(device="cpu", dtype=torch.long)
        starts_cpu = local_starts.to(device="cpu", dtype=torch.long)
        if bool((table_cpu < 0).any()) or bool(
            (table_cpu >= self.sampler.num_units).any()
        ):
            raise ValueError("segment table index is out of range")
        first = self.sampler.intervals.first[table_cpu]
        stop = self.sampler.intervals.stop[table_cpu]
        if bool(((starts_cpu < first) | (starts_cpu >= stop)).any()):
            raise ValueError("paired-evaluation start is not horizon safe")

        env_ids = torch.arange(self.num_envs, device=self.device)
        unit_ids = self.sampler.intervals.unit_ids[table_cpu].to(self.device)
        clip_ids = self.sampler.intervals.clip_ids[table_cpu].to(self.device)
        trial_ends = starts_cpu + self.sampler.horizon_steps
        segment_stops = self.sampler.segment_stops[table_cpu]
        clip_starts = self.motion.clip_start[clip_ids]
        starts = starts_cpu.to(self.device)
        self.active_table_indices[:] = table_cpu.to(self.device)
        self.active_unit_ids[:] = unit_ids
        self.clip_ids[:] = clip_ids
        self.local_start_steps[:] = starts
        self.local_trial_end_steps[:] = trial_ends.to(self.device)
        self.local_segment_stop_steps[:] = segment_stops.to(self.device)
        self.time_steps[:] = clip_starts + starts
        self.trial_end_steps[:] = clip_starts + trial_ends.to(self.device)
        self.segment_start_steps[:] = clip_starts + starts
        self.segment_stop_steps[:] = clip_starts + segment_stops.to(self.device)
        self._finalize_reference(env_ids)
        self._update_command(env_ids)
        self.assert_active_references_valid()

    def per_clip_stats(self) -> dict[str, object]:
        """Aggregate completed segment trials by source clip for checkpoints."""
        clip_ids = self.sampler.intervals.clip_ids
        attempts = torch.zeros(self.motion.num_clips, dtype=torch.int64)
        failures = torch.zeros_like(attempts)
        attempts.scatter_add_(0, clip_ids, self.sampler.lifetime_attempts)
        failures.scatter_add_(0, clip_ids, self.sampler.lifetime_failures)
        clip_mass = torch.zeros(
            self.motion.num_clips, dtype=self.sampler.probabilities.dtype
        )
        clip_mass.scatter_add_(0, clip_ids, self.sampler.probabilities)
        attempt_values = attempts.tolist()
        failure_values = failures.tolist()
        return {
            "schema_version": "segment_clip_stats/1",
            "clip": list(self.motion.clip_names),
            "episodes": attempt_values,
            "failures": failure_values,
            "failure_rate": [
                f / a if a else float("nan")
                for a, f in zip(attempt_values, failure_values, strict=True)
            ],
            "sampling_weight": clip_mass.tolist(),
            "segment": self.segment_telemetry(),
        }


def segment_trial_timeout(
    env: ManagerBasedRlEnv, command_name: str = "motion"
) -> torch.Tensor:
    """Truncate exactly after H safe reference transitions."""
    command = env.command_manager.get_term(command_name)
    if not isinstance(command, SegmentNativeMotionCommand):
        raise TypeError(f"{command_name!r} is not a segment-native motion command")
    command.assert_active_references_valid()
    return command.time_steps >= command.trial_end_steps


@dataclass
class SegmentNativeMotionCommandCfg(MultiClipMotionCommandCfg):
    """Configuration for exact segment-native training."""

    segment_manifest: str = ""
    segment_sampling_mode: SamplingMode = "adaptive"
    sampler_seed: int = 0
    segment_exploration_ratio: float = 0.1
    segment_difficulty_power: float = 1.0
    segment_rank: RankMode = "failure"
    segment_progress_window: int = 10
    segment_progress_floor: float = 0.01
    segment_decay: float = 0.99
    segment_prior_rate: float = 0.5
    segment_prior_strength: float = 2.0
    max_unit_probability: float | None = 0.05
    max_clip_probability: float | None = 0.25
    max_top1_probability: float = 0.05
    min_entropy_effective_units: float = 12.0
    curriculum_update_interval_steps: int = 50
    segment_timeout_term: str = "segment_trial"
    verify_motion_hashes: bool = True

    def build(self, env: ManagerBasedRlEnv) -> SegmentNativeMotionCommand:
        return SegmentNativeMotionCommand(self, env)
