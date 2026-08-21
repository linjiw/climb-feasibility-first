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
        self.deployment_probabilities = self._compute_probabilities(
            force_uniform=True
        )
        self.probabilities = self._compute_probabilities()

    @property
    def num_units(self) -> int:
        """Number of admissible runtime rows."""
        return self.intervals.first.numel()

    def _compute_probabilities(
        self, *, force_uniform: bool = False
    ) -> torch.Tensor:
        if self.mode == "uniform" or force_uniform:
            difficulty = torch.ones(self.num_units, dtype=torch.float64)
        else:
            difficulty = conditional_failure_rate(
                self.failure_mass,
                self.attempt_mass,
                prior_strength=0.0,
            )
        return segment_sampling_probabilities(
            difficulty,
            torch.ones(self.num_units, dtype=torch.float64),
            self.deployment_mass.to(torch.float64),
            exploration_ratio=self.exploration_ratio,
            difficulty_power=self.difficulty_power,
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
        self.probabilities = self._compute_probabilities()

    def state_dict(self) -> dict[str, Any]:
        """Return all sampler state needed at an all-env reset boundary."""
        return {
            "schema_version": "segment_sampler_state/1",
            "unit_table_sha256": self.manifest["unit_table_sha256"],
            "mode": self.mode,
            "clock": self.clock,
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
        if not torch.equal(self.probabilities, self._compute_probabilities()):
            raise ValueError("sampler-state probabilities do not match its statistics")
        generator_state = state.get("generator_state")
        if not isinstance(generator_state, torch.Tensor):
            raise TypeError("sampler state has no generator state")
        self.generator.set_state(generator_state.cpu())
        self.clock = int(state["clock"])
