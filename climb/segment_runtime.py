"""Stateful, checkpointable sampler for exact segment-native trials."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import torch

from .dfrp import sha256_file, validate_dfrp_manifest
from .segment_curriculum import (
    AdmissibleStarts,
    SamplingConcentration,
    aggregate_trial_outcomes,
    conditional_failure_rate,
    sample_admissible_starts,
    sampling_concentration,
    segment_sampling_probabilities,
    update_conditional_failure_statistics,
)

SamplingMode = Literal["uniform", "adaptive"]
RankMode = Literal["failure", "learning_progress", "uncertainty"]
"""Adaptive focus rank.

``failure``: conditional failure rate raised to ``difficulty_power`` (the
segment-v2 pilot rank; retired as a sole rank because it saturates on an exact
support).  ``learning_progress``: absolute change of the conditional success
estimate over ``progress_window`` sampler ticks, plus ``progress_floor``.
``uncertainty``: Bernoulli variance ``s (1 - s)`` of the conditional success
estimate (the pre-declared fallback).  Both non-failure ranks require
``difficulty_power == 0`` so the failure rate never enters multiplicatively.
"""


def canonical_hash(value: Any) -> str:
    """Hash a JSON-compatible value independent of formatting."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class SegmentSamples:
    """A batch of exact fixed-horizon trial assignments."""

    table_indices: torch.Tensor
    unit_ids: torch.Tensor
    clip_ids: torch.Tensor
    local_starts: torch.Tensor
    local_trial_ends: torch.Tensor
    local_segment_stops: torch.Tensor


class SegmentSampler:
    """Sample exact units and update conditional outcomes on a fixed clock."""

    def __init__(
        self,
        manifest_path: str | Path,
        *,
        mode: SamplingMode,
        seed: int,
        exploration_ratio: float = 0.1,
        difficulty_power: float = 1.0,
        decay: float = 0.99,
        prior_rate: float = 0.5,
        prior_strength: float = 2.0,
        max_unit_probability: float | None = None,
        max_clip_probability: float | None = None,
        rank: RankMode = "failure",
        progress_window: int = 10,
        progress_floor: float = 0.01,
    ) -> None:
        self.manifest_path = Path(manifest_path).resolve()
        self.manifest = json.loads(self.manifest_path.read_text())
        if self.manifest.get("schema_version") != "segment_unit_table/1":
            raise ValueError("unsupported segment unit-table schema")
        dfrp_link = self.manifest.get("dfrp")
        if dfrp_link is not None:
            dfrp_path = Path(dfrp_link["manifest_path"])
            if not dfrp_path.is_file():
                raise FileNotFoundError(f"missing DFRP manifest {dfrp_path}")
            if sha256_file(dfrp_path) != dfrp_link["manifest_file_sha256"]:
                raise ValueError("DFRP manifest file hash mismatch")
            dfrp_manifest = json.loads(dfrp_path.read_text())
            validate_dfrp_manifest(dfrp_manifest)
            if (
                dfrp_manifest["payload_sha256"]
                != dfrp_link["manifest_payload_sha256"]
            ):
                raise ValueError("DFRP manifest payload identity mismatch")
            if any(
                source.get("dfrp_manifest_payload_sha256")
                != dfrp_manifest["payload_sha256"]
                for source in self.manifest["sources"]
            ):
                raise ValueError("segment sources disagree on DFRP provenance")
        frozen_table = {
            "horizon_steps": self.manifest["horizon_steps"],
            "sources": self.manifest["sources"],
            "source_units": self.manifest["source_units"],
            "admissible_units": self.manifest["admissible_units"],
        }
        if canonical_hash(frozen_table) != self.manifest.get("unit_table_sha256"):
            raise ValueError("segment unit-table hash mismatch")
        if mode not in ("uniform", "adaptive"):
            raise ValueError("mode must be 'uniform' or 'adaptive'")
        if not 0.0 < decay <= 1.0:
            raise ValueError("decay must be in (0, 1]")
        if not 0.0 <= prior_rate <= 1.0 or prior_strength <= 0.0:
            raise ValueError("a positive Beta prior in [0, 1] is required")
        if rank not in ("failure", "learning_progress", "uncertainty"):
            raise ValueError("rank must be 'failure', 'learning_progress', or 'uncertainty'")
        if rank != "failure" and difficulty_power != 0.0:
            raise ValueError("non-failure ranks require difficulty_power == 0")
        if progress_window < 1:
            raise ValueError("progress_window must be at least one sampler tick")
        if progress_floor < 0.0:
            raise ValueError("progress_floor must be non-negative")

        units = self.manifest["admissible_units"]
        if not units:
            raise ValueError("unit table has no admissible units")
        if [unit["table_index"] for unit in units] != list(range(len(units))):
            raise ValueError("unit table indices must be contiguous and ordered")
        unit_ids = torch.tensor([unit["unit_id"] for unit in units], dtype=torch.long)
        if unit_ids.unique().numel() != unit_ids.numel():
            raise ValueError("canonical unit IDs must be unique")
        self.horizon_steps = int(self.manifest["horizon_steps"])
        self.intervals = AdmissibleStarts(
            unit_ids=unit_ids,
            clip_ids=torch.tensor(
                [unit["clip_id"] for unit in units], dtype=torch.long
            ),
            first=torch.tensor(
                [unit["admissible_start_first"] for unit in units], dtype=torch.long
            ),
            stop=torch.tensor(
                [unit["admissible_start_stop"] for unit in units], dtype=torch.long
            ),
        )
        self.segment_stops = torch.tensor(
            [unit["segment_stop"] for unit in units], dtype=torch.long
        )
        if bool((self.intervals.counts <= 0).any()) or bool(
            (
                self.intervals.stop + self.horizon_steps
                != self.segment_stops
            ).any()
        ):
            raise ValueError("unit table violates the fixed-horizon interval contract")
        self.deployment_mass = torch.tensor(
            [unit["deployment_mass"] for unit in units], dtype=torch.float32
        )
        if not torch.equal(
            self.deployment_mass,
            self.intervals.counts.to(self.deployment_mass),
        ):
            raise ValueError("deployment mass must equal the legal-start count")

        self.mode = mode
        self.rank = rank
        self.progress_window = int(progress_window)
        self.progress_floor = float(progress_floor)
        self.exploration_ratio = exploration_ratio
        self.difficulty_power = difficulty_power
        self.decay = decay
        self.max_unit_probability = max_unit_probability
        self.max_clip_probability = max_clip_probability
        self.generator = torch.Generator(device="cpu").manual_seed(seed)
        num_units = len(units)
        self.failure_mass = torch.full(
            (num_units,), prior_rate * prior_strength, dtype=torch.float64
        )
        self.attempt_mass = torch.full(
            (num_units,), prior_strength, dtype=torch.float64
        )
        self.pending_failures = torch.zeros(num_units, dtype=torch.float64)
        self.pending_attempts = torch.zeros(num_units, dtype=torch.float64)
        self.lifetime_failures = torch.zeros(num_units, dtype=torch.int64)
        self.lifetime_attempts = torch.zeros(num_units, dtype=torch.int64)
        self.clock = 0
        self.rate_history = self.conditional_success_rates().unsqueeze(0)
        self.deployment_probabilities = self._compute_probabilities(
            force_uniform=True
        )
        self.probabilities = self._compute_probabilities()

    @property
    def num_units(self) -> int:
        """Number of admissible runtime rows."""
        return self.intervals.first.numel()

    def conditional_success_rates(self) -> torch.Tensor:
        """Current Beta-smoothed conditional success estimate per unit."""
        return 1.0 - conditional_failure_rate(
            self.failure_mass, self.attempt_mass, prior_strength=0.0
        )

    def saturation_fraction(self, low: float = 0.05, high: float = 0.95) -> float:
        """Fraction of units whose success estimate lies outside ``(low, high)``.

        A rank has nothing to order when almost every estimate is saturated;
        the Phase-G manipulation gate reads this value.
        """
        rates = self.conditional_success_rates()
        return float(((rates <= low) | (rates >= high)).double().mean())

    def learning_progress(self) -> torch.Tensor | None:
        """Absolute success-rate change over ``progress_window`` ticks.

        Returns ``None`` until the history spans the full window, during which
        an adaptive learning-progress sampler is uniform over its support.
        """
        if self.rate_history.shape[0] < self.progress_window + 1:
            return None
        return (self.rate_history[-1] - self.rate_history[-(self.progress_window + 1)]).abs()

    def _ranking_weight(self) -> torch.Tensor | None:
        if self.rank == "learning_progress":
            progress = self.learning_progress()
            if progress is None:
                return None
            return progress + self.progress_floor
        if self.rank == "uncertainty":
            rates = self.rate_history[-1]
            return rates * (1.0 - rates)
        return None

    def _compute_probabilities(
        self, *, force_uniform: bool = False
    ) -> torch.Tensor:
        ranking_weight = None
        if self.mode == "uniform" or force_uniform:
            difficulty = torch.ones(self.num_units, dtype=torch.float64)
        elif self.rank == "failure":
            difficulty = conditional_failure_rate(
                self.failure_mass,
                self.attempt_mass,
                prior_strength=0.0,
            )
        else:
            difficulty = torch.ones(self.num_units, dtype=torch.float64)
            ranking_weight = self._ranking_weight()
        return segment_sampling_probabilities(
            difficulty,
            torch.ones(self.num_units, dtype=torch.float64),
            self.deployment_mass.to(torch.float64),
            exploration_ratio=self.exploration_ratio,
            difficulty_power=self.difficulty_power,
            ranking_weight=ranking_weight,
            clip_ids=self.intervals.clip_ids,
            max_unit_probability=self.max_unit_probability,
            max_clip_probability=self.max_clip_probability,
        ).cpu()

    def concentration(self) -> SamplingConcentration:
        """Return current concentration telemetry."""
        return sampling_concentration(self.probabilities)

    def adaptation_total_variation(self) -> float:
        """Distance from the capped deployment control distribution.

        Entropy can stay high even when an adaptive curriculum is nearly
        identical to its control.  This manipulation check is zero for the
        uniform arm and lies in ``[0, 1]`` for an adaptive arm.
        """
        return float(
            0.5
            * (self.probabilities - self.deployment_probabilities).abs().sum()
        )

    def sample(self, count: int) -> SegmentSamples:
        """Draw exact units and legal starts using only the dedicated CPU RNG."""
        if count <= 0:
            raise ValueError("sample count must be positive")
        table_indices = torch.multinomial(
            self.probabilities,
            count,
            replacement=True,
            generator=self.generator,
        )
        starts = sample_admissible_starts(
            self.intervals,
            table_indices,
            generator=self.generator,
        )
        return SegmentSamples(
            table_indices=table_indices,
            unit_ids=self.intervals.unit_ids[table_indices],
            clip_ids=self.intervals.clip_ids[table_indices],
            local_starts=starts,
            local_trial_ends=starts + self.horizon_steps,
            local_segment_stops=self.segment_stops[table_indices],
        )

    def record_completed_trials(
        self, table_indices: torch.Tensor, failed: torch.Tensor
    ) -> None:
        """Accumulate completed, uncensored trials without updating the clock."""
        failures, attempts = aggregate_trial_outcomes(
            self.num_units,
            table_indices.to(device="cpu", dtype=torch.long),
            failed.to(device="cpu"),
        )
        self.pending_failures += failures
        self.pending_attempts += attempts
        self.lifetime_failures += failures.to(torch.int64)
        self.lifetime_attempts += attempts.to(torch.int64)

    def advance_clock(self) -> None:
        """Apply all pending outcomes once, then refresh the cached distribution."""
        self.failure_mass, self.attempt_mass = update_conditional_failure_statistics(
            self.failure_mass,
            self.attempt_mass,
            self.pending_failures,
            self.pending_attempts,
            decay=self.decay,
        )
        self.pending_failures.zero_()
        self.pending_attempts.zero_()
        self.clock += 1
        self.rate_history = torch.cat(
            [self.rate_history, self.conditional_success_rates().unsqueeze(0)]
        )[-(self.progress_window + 1) :]
        self.probabilities = self._compute_probabilities()

    def state_dict(self) -> dict[str, Any]:
        """Return all sampler state needed at an all-env reset boundary."""
        return {
            "schema_version": "segment_sampler_state/1",
            "unit_table_sha256": self.manifest["unit_table_sha256"],
            "mode": self.mode,
            "rank": self.rank,
            "progress_window": self.progress_window,
            "progress_floor": self.progress_floor,
            "clock": self.clock,
            "rate_history": self.rate_history.clone(),
            "generator_state": self.generator.get_state().clone(),
            "failure_mass": self.failure_mass.clone(),
            "attempt_mass": self.attempt_mass.clone(),
            "pending_failures": self.pending_failures.clone(),
            "pending_attempts": self.pending_attempts.clone(),
            "lifetime_failures": self.lifetime_failures.clone(),
            "lifetime_attempts": self.lifetime_attempts.clone(),
            "probabilities": self.probabilities.clone(),
        }

    def load_state_dict(self, state: dict[str, Any]) -> None:
        """Restore sampler state only when its frozen unit table and mode match."""
        if state.get("schema_version") != "segment_sampler_state/1":
            raise ValueError("unsupported sampler-state schema")
        if state.get("unit_table_sha256") != self.manifest["unit_table_sha256"]:
            raise ValueError("sampler state belongs to a different unit table")
        if state.get("mode") != self.mode:
            raise ValueError("sampler state belongs to a different sampling mode")
        if state.get("rank", "failure") != self.rank:
            raise ValueError("sampler state belongs to a different focus rank")
        if self.rank != "failure" and (
            int(state.get("progress_window", -1)) != self.progress_window
            or float(state.get("progress_floor", -1.0)) != self.progress_floor
        ):
            raise ValueError("sampler state uses different rank parameters")
        tensor_names = (
            "failure_mass",
            "attempt_mass",
            "pending_failures",
            "pending_attempts",
            "lifetime_failures",
            "lifetime_attempts",
            "probabilities",
        )
        for name in tensor_names:
            value = state.get(name)
            current = getattr(self, name)
            if not isinstance(value, torch.Tensor) or value.shape != current.shape:
                raise ValueError(f"sampler state has invalid {name}")
            setattr(self, name, value.to(dtype=current.dtype, device="cpu").clone())
        history = state.get("rate_history")
        if history is None:
            if self.rank != "failure":
                raise ValueError("sampler state has no success-rate history")
            history = self.conditional_success_rates().unsqueeze(0)
        if (
            not isinstance(history, torch.Tensor)
            or history.ndim != 2
            or history.shape[1] != self.num_units
            or not 1 <= history.shape[0] <= self.progress_window + 1
        ):
            raise ValueError("sampler state has invalid rate_history")
        self.rate_history = history.to(dtype=torch.float64, device="cpu").clone()
        if not torch.equal(self.probabilities, self._compute_probabilities()):
            raise ValueError("sampler-state probabilities do not match its statistics")
        generator_state = state.get("generator_state")
        if not isinstance(generator_state, torch.Tensor):
            raise TypeError("sampler state has no generator state")
        self.generator.set_state(generator_state.cpu())
        self.clock = int(state["clock"])
