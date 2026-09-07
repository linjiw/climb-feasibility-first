"""Exploratory scale-relative ALP; separate from the frozen E4 sampler."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import torch

from climb.segment_runtime import SegmentSampler

PROTOCOL = "relative_progress_alp/1"


def relative_weights(progress: torch.Tensor, mass: torch.Tensor, factor: float) -> torch.Tensor:
    """Normalize ALP by its deployment-prior mean before adding a relative floor."""
    if (progress.shape != mass.shape or factor < 0 or not torch.isfinite(torch.tensor(factor))
            or not torch.isfinite(progress).all() or not torch.isfinite(mass).all()
            or (progress < 0).any() or (mass < 0).any() or mass.sum() <= 0):
        raise ValueError("invalid relative-progress inputs")
    mean = (progress * (mass / mass.sum())).sum()
    if mean == 0:
        return torch.ones_like(progress)
    return progress / mean + factor


class RelativeProgressSampler(SegmentSampler):
    """Keep exact support, event statistics, and caps; replace only rank scaling."""

    def __init__(self, *args: Any, relative_factor: float = 2.0, **kwargs: Any) -> None:
        if kwargs.get("rank") != "learning_progress" or kwargs.get("progress_floor") != 0.0:
            raise ValueError("relative ALP requires learning_progress and zero absolute floor")
        if relative_factor < 0 or not torch.isfinite(torch.tensor(relative_factor)):
            raise ValueError("invalid relative factor")
        self.relative_factor = relative_factor
        super().__init__(*args, **kwargs)

    def _ranking_weight(self) -> torch.Tensor | None:
        progress = self.learning_progress()
        if progress is None:
            return None
        return relative_weights(progress, self.deployment_mass.double(), self.relative_factor)

    def state_dict(self) -> dict[str, Any]:
        return {**super().state_dict(), "relative_progress": {
            "protocol": PROTOCOL, "factor": self.relative_factor}}

    def load_state_dict(self, state: dict[str, Any]) -> None:
        if state.get("relative_progress") != {"protocol": PROTOCOL, "factor": self.relative_factor}:
            raise ValueError("relative-progress resume contract mismatch")
        super().load_state_dict(state)


# Simulator imports remain below the pure ranking helper and sampler.
from climb.segment_command import SegmentNativeMotionCommand, SegmentNativeMotionCommandCfg


class RelativeProgressCommand(SegmentNativeMotionCommand):
    def __init__(self, cfg: RelativeProgressCommandCfg, env: Any) -> None:
        super().__init__(cfg, env)
        if self.completed_trials or (self.active_unit_ids >= 0).any():
            raise ValueError("relative sampler must be installed before the first trial")
        self.sampler = RelativeProgressSampler(
            cfg.segment_manifest, mode=cfg.segment_sampling_mode, seed=cfg.sampler_seed,
            exploration_ratio=cfg.segment_exploration_ratio, difficulty_power=0.0,
            decay=cfg.segment_decay, prior_rate=cfg.segment_prior_rate,
            prior_strength=cfg.segment_prior_strength, max_unit_probability=cfg.max_unit_probability,
            max_clip_probability=cfg.max_clip_probability, rank="learning_progress",
            progress_window=cfg.segment_progress_window, progress_floor=0.0,
            relative_factor=cfg.relative_progress_factor,
        )
        self._update_sampling_metrics()

    def segment_telemetry(self) -> dict[str, object]:
        result = super().segment_telemetry()
        result.update({"allocation_protocol": PROTOCOL,
                       "relative_progress_factor": self.sampler.relative_factor})
        return result


@dataclass
class RelativeProgressCommandCfg(SegmentNativeMotionCommandCfg):
    relative_progress_factor: float = 2.0

    def build(self, env: Any) -> RelativeProgressCommand:
        return RelativeProgressCommand(self, env)
