"""Pure segment-level primitives for the post-FGAS curriculum.

This module intentionally does not modify the frozen FGAS command.  It defines
the probability and start-window invariants that a separately sealed follow-up
must use: adapt on conditional failure rates, and sample only starts whose full
trial remains inside an admissible segment.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class AdmissibleStarts:
    """Half-open start-frame intervals for fixed-horizon segment trials."""

    unit_ids: torch.Tensor
    clip_ids: torch.Tensor
    first: torch.Tensor
    stop: torch.Tensor

    @property
    def counts(self) -> torch.Tensor:
        """Number of legal integer starts in every interval."""
        return self.stop - self.first


@dataclass(frozen=True)
class SamplingConcentration:
    """Concentration diagnostics used as pre-training launch gates."""

    top1_probability: float
    entropy_effective_units: float


def sampling_concentration(probabilities: torch.Tensor) -> SamplingConcentration:
    """Return top-1 mass and exp(entropy) after validating a probability table."""
    if probabilities.ndim != 1 or probabilities.numel() == 0:
        raise ValueError("probabilities must be a non-empty one-dimensional table")
    if not bool(torch.isfinite(probabilities).all()) or bool((probabilities < 0).any()):
        raise ValueError("probabilities must be finite and non-negative")
    if not torch.isclose(
        probabilities.sum(),
        torch.ones((), dtype=probabilities.dtype, device=probabilities.device),
        atol=1.0e-6,
        rtol=1.0e-6,
    ):
        raise ValueError("probabilities must sum to one")
    positive = probabilities[probabilities > 0]
    entropy = -(positive * positive.log()).sum()
    return SamplingConcentration(
        top1_probability=float(probabilities.max()),
        entropy_effective_units=float(entropy.exp()),
    )


def validate_sampling_concentration(
    probabilities: torch.Tensor,
    *,
    max_top1_probability: float,
    min_entropy_effective_units: float,
) -> SamplingConcentration:
    """Fail a wiring launch when a sampler has already collapsed."""
    if not 0.0 < max_top1_probability <= 1.0:
        raise ValueError("max_top1_probability must be in (0, 1]")
    if min_entropy_effective_units < 1.0:
        raise ValueError("min_entropy_effective_units must be at least one")
    diagnostics = sampling_concentration(probabilities)
    if diagnostics.top1_probability > max_top1_probability:
        raise ValueError("top-1 sampling mass exceeds the declared concentration gate")
    if diagnostics.entropy_effective_units < min_entropy_effective_units:
        raise ValueError("entropy-effective unit count is below the declared gate")
    return diagnostics


def conditional_failure_rate(
    failures: torch.Tensor,
    attempts: torch.Tensor,
    *,
    prior_rate: float = 0.5,
    prior_strength: float = 2.0,
) -> torch.Tensor:
    """Estimate failure probability without folding in sampling frequency.

    ``prior_rate`` and ``prior_strength`` define a Beta prior.  Unlike a raw
    failure-count score, the estimate converges to the same value for units
    with the same conditional outcome rate even when their exposure differs.
    """
    if failures.shape != attempts.shape:
        raise ValueError("failure and attempt tables must have the same shape")
    if not 0.0 <= prior_rate <= 1.0:
        raise ValueError("prior_rate must be in [0, 1]")
    if prior_strength < 0.0:
        raise ValueError("prior_strength must be non-negative")
    if not bool(torch.isfinite(failures).all()) or not bool(
        torch.isfinite(attempts).all()
    ):
        raise ValueError("failure and attempt tables must be finite")
    if bool((failures < 0).any()) or bool((attempts < failures).any()):
        raise ValueError("counts must satisfy 0 <= failures <= attempts")

    numerator = failures + prior_rate * prior_strength
    denominator = attempts + prior_strength
    if prior_strength == 0.0 and bool((attempts == 0).any()):
        raise ValueError("zero-attempt units require a positive prior_strength")
    return numerator / denominator


def _capped_weight_allocation(
    weights: torch.Tensor,
    fallback_weights: torch.Tensor,
    capacities: torch.Tensor,
    total: float,
) -> torch.Tensor:
    """Allocate mass proportionally with deterministic water-filling."""
    if total < 0.0:
        raise ValueError("allocation total must be non-negative")
    output = torch.zeros_like(weights)
    remaining_capacity = capacities.clone()
    remaining = torch.as_tensor(total, dtype=weights.dtype, device=weights.device)
    tolerance = max(1.0e-12, torch.finfo(weights.dtype).eps * 64)
    if float(remaining) <= tolerance:
        return output
    if float(remaining_capacity.sum()) + tolerance < float(remaining):
        raise ValueError("probability caps cannot contain unit mass")

    for _ in range(weights.numel() + 1):
        active = remaining_capacity > tolerance
        if not bool(active.any()):
            break
        active_weights = torch.where(active, weights, torch.zeros_like(weights))
        if float(active_weights.sum()) <= tolerance:
            active_weights = torch.where(
                active, fallback_weights, torch.zeros_like(fallback_weights)
            )
        if float(active_weights.sum()) <= tolerance:
            active_weights = torch.where(
                active, remaining_capacity, torch.zeros_like(remaining_capacity)
            )
        proposed = remaining * active_weights / active_weights.sum()
        addition = torch.minimum(proposed, remaining_capacity)
        allocated = addition.sum()
        if float(allocated) <= tolerance:
            break
        output += addition
        remaining_capacity -= addition
        remaining -= allocated
        if float(remaining) <= tolerance:
            return output
    raise ValueError("probability caps could not allocate unit mass")


def _apply_probability_caps(
    base: torch.Tensor,
    focus: torch.Tensor,
    clip_ids: torch.Tensor | None,
    *,
    exploration_ratio: float,
    max_unit_probability: float | None,
    max_clip_probability: float | None,
) -> torch.Tensor:
    """Cap focus allocation while preserving the exact exploration floor."""
    if max_unit_probability is None and max_clip_probability is None:
        return exploration_ratio * base + (1.0 - exploration_ratio) * focus
    if max_unit_probability is not None and not 0.0 < max_unit_probability <= 1.0:
        raise ValueError("max_unit_probability must be in (0, 1]")
    if max_clip_probability is not None and not 0.0 < max_clip_probability <= 1.0:
        raise ValueError("max_clip_probability must be in (0, 1]")

    original_device = base.device
    output_dtype = base.dtype
    original_base = base.detach().to(device="cpu", dtype=output_dtype)
    base = base.detach().to(device="cpu", dtype=torch.float64)
    focus = focus.detach().to(device="cpu", dtype=torch.float64)
    base = base / base.sum()
    focus = focus / focus.sum()
    lower = exploration_ratio * base
    unit_ceiling = torch.full_like(
        lower, 1.0 if max_unit_probability is None else max_unit_probability
    )
    unit_capacity = torch.where(base > 0, unit_ceiling - lower, 0.0)
    tolerance = 1.0e-12
    if bool((unit_capacity < -tolerance).any()):
        raise ValueError("unit cap is below the declared exploration floor")
    unit_capacity.clamp_min_(0.0)
    focus_total = 1.0 - exploration_ratio

    if max_clip_probability is None:
        allocation = _capped_weight_allocation(
            focus, base, unit_capacity, focus_total
        )
        probabilities = (lower + allocation).to(output_dtype)
        output_tolerance = max(1.0e-8, torch.finfo(output_dtype).eps * 4)
        if max_unit_probability is not None and bool(
            (probabilities > max_unit_probability + output_tolerance).any()
        ):
            raise ValueError("unit cap was violated after probability allocation")
        if bool(
            (
                probabilities + output_tolerance
                < exploration_ratio * original_base
            ).any()
        ):
            raise ValueError("probability allocation violated the exploration floor")
        if bool((probabilities[original_base == 0] != 0).any()):
            raise ValueError("probability allocation leaked outside hard support")
        return probabilities.to(original_device)

    if clip_ids is None:
        raise ValueError("clip_ids are required when max_clip_probability is set")
    if clip_ids.shape != base.shape or clip_ids.ndim != 1:
        raise ValueError("clip_ids must align with the probability tables")
    if clip_ids.dtype not in (torch.int32, torch.int64) or bool(
        (clip_ids < 0).any()
    ):
        raise ValueError("clip_ids must be non-negative integer IDs")
    clip_ids = clip_ids.to(device="cpu")

    unique_clips, inverse = torch.unique(clip_ids, sorted=True, return_inverse=True)
    num_clips = unique_clips.numel()
    clip_lower = torch.zeros(num_clips, dtype=base.dtype, device=base.device)
    clip_focus = torch.zeros_like(clip_lower)
    clip_base = torch.zeros_like(clip_lower)
    clip_unit_capacity = torch.zeros_like(clip_lower)
    clip_lower.scatter_add_(0, inverse, lower)
    clip_focus.scatter_add_(0, inverse, focus)
    clip_base.scatter_add_(0, inverse, base)
    clip_unit_capacity.scatter_add_(0, inverse, unit_capacity)
    clip_capacity = torch.minimum(
        torch.full_like(clip_lower, max_clip_probability) - clip_lower,
        clip_unit_capacity,
    )
    if bool((clip_capacity < -tolerance).any()):
        raise ValueError("clip cap is below the declared exploration floor")
    clip_capacity.clamp_min_(0.0)
    clip_allocation = _capped_weight_allocation(
        clip_focus, clip_base, clip_capacity, focus_total
    )

    allocation = torch.zeros_like(base)
    for clip_index in range(num_clips):
        members = inverse == clip_index
        allocation[members] = _capped_weight_allocation(
            focus[members],
            base[members],
            unit_capacity[members],
            float(clip_allocation[clip_index]),
        )
    probabilities = (lower + allocation).to(output_dtype)
    output_tolerance = max(1.0e-8, torch.finfo(output_dtype).eps * 4)
    if max_unit_probability is not None and bool(
        (probabilities > max_unit_probability + output_tolerance).any()
    ):
        raise ValueError("unit cap was violated after probability allocation")
    output_clip_mass = torch.zeros(
        num_clips, dtype=torch.float64, device=base.device
    ).scatter_add_(0, inverse, probabilities.to(torch.float64))
    if bool((output_clip_mass > max_clip_probability + output_tolerance).any()):
        raise ValueError("clip cap was violated after probability allocation")
    if bool(
        (probabilities + output_tolerance < exploration_ratio * original_base).any()
    ):
        raise ValueError("probability allocation violated the exploration floor")
    if bool((probabilities[original_base == 0] != 0).any()):
        raise ValueError("probability allocation leaked outside hard support")
    return probabilities.to(original_device)


def segment_sampling_probabilities(
    difficulty_rates: torch.Tensor,
    eligibility: torch.Tensor,
    deployment_mass: torch.Tensor,
    *,
    exploration_ratio: float = 0.1,
    difficulty_power: float = 1.0,
    ranking_weight: torch.Tensor | None = None,
    clip_ids: torch.Tensor | None = None,
    max_unit_probability: float | None = None,
    max_clip_probability: float | None = None,
) -> torch.Tensor:
    """Mix a feasible deployment prior with conditional-difficulty focus.

    ``difficulty_rates`` is explicit event-updated conditional-rate state, not
    raw failure arrivals or lifetime failure counts. ``eligibility`` is a binary
    hard-support mask. Both mixture terms therefore have the same support
    ``deployment_mass * eligibility``; an optional continuous ``ranking_weight``
    can alter only the focus term. No all-zero fallback is allowed: an invalid
    support table is a launch error, not permission to train on rejected material.
    """
    shape = difficulty_rates.shape
    if difficulty_rates.dtype not in (torch.float32, torch.float64):
        raise ValueError("difficulty_rates must use float32 or float64")
    if any(x.shape != shape for x in (eligibility, deployment_mass)):
        raise ValueError("all segment tables must have the same shape")
    if ranking_weight is not None and ranking_weight.shape != shape:
        raise ValueError("ranking_weight must have the same shape as segment tables")
    if not 0.0 <= exploration_ratio <= 1.0:
        raise ValueError("exploration_ratio must be in [0, 1]")
    if difficulty_power < 0.0:
        raise ValueError("difficulty_power must be non-negative")
    if any(
        not bool(torch.isfinite(value).all())
        for value in (difficulty_rates, eligibility, deployment_mass)
    ):
        raise ValueError("difficulty, eligibility, and deployment mass must be finite")
    if bool((difficulty_rates < 0).any()) or bool((difficulty_rates > 1).any()):
        raise ValueError("difficulty_rates must be conditional probabilities in [0, 1]")
    if bool((eligibility < 0).any()) or bool((deployment_mass < 0).any()):
        raise ValueError("eligibility and deployment mass must be non-negative")
    if bool(((eligibility != 0) & (eligibility != 1)).any()):
        raise ValueError("eligibility must be a binary hard-support mask")
    if ranking_weight is not None and (
        not bool(torch.isfinite(ranking_weight).all())
        or bool((ranking_weight < 0).any())
    ):
        raise ValueError("ranking_weight must be finite and non-negative")

    base_mass = eligibility.to(difficulty_rates) * deployment_mass.to(difficulty_rates)
    total = base_mass.sum()
    if float(total) <= 0.0:
        raise ValueError("no admissible segment has positive deployment mass")
    base = base_mass / total

    ranking = (
        torch.ones_like(base_mass)
        if ranking_weight is None
        else ranking_weight.to(base_mass)
    )
    focus_mass = base_mass * ranking * difficulty_rates.pow(difficulty_power)
    focus_total = focus_mass.sum()
    focus = focus_mass / focus_total if float(focus_total) > 0.0 else base
    probabilities = _apply_probability_caps(
        base,
        focus,
        clip_ids,
        exploration_ratio=exploration_ratio,
        max_unit_probability=max_unit_probability,
        max_clip_probability=max_clip_probability,
    )
    if not torch.isclose(
        probabilities.sum(),
        torch.ones((), dtype=probabilities.dtype, device=probabilities.device),
        atol=1.0e-5,
        rtol=1.0e-6,
    ):
        raise ValueError("capped probabilities do not sum to one")
    return probabilities


def build_admissible_starts(
    clip_ids: torch.Tensor,
    segment_start: torch.Tensor,
    segment_stop: torch.Tensor,
    horizon_steps: int,
    *,
    unit_ids: torch.Tensor | None = None,
) -> AdmissibleStarts:
    """Convert feasible ``[start, stop)`` segments into transition-safe starts.

    A trial of H simulator transitions consumes its initial reference and then
    advances through H more reference frames.  A start is retained only when
    all H advances remain strictly below ``stop``.  Short segments are dropped
    rather than silently falling back to an unsafe uniform draw.
    """
    if horizon_steps <= 0:
        raise ValueError("horizon_steps must be positive")
    if unit_ids is None:
        unit_ids = torch.arange(
            clip_ids.numel(), dtype=torch.long, device=clip_ids.device
        )
    if not (
        clip_ids.shape == segment_start.shape == segment_stop.shape == unit_ids.shape
        and clip_ids.ndim == 1
    ):
        raise ValueError("segment tables must be one-dimensional and aligned")
    for name, value in (
        ("clip_ids", clip_ids),
        ("segment_start", segment_start),
        ("segment_stop", segment_stop),
        ("unit_ids", unit_ids),
    ):
        if value.dtype not in (
            torch.int8,
            torch.int16,
            torch.int32,
            torch.int64,
            torch.uint8,
        ):
            raise ValueError(f"{name} must use an integer dtype")
    if bool((clip_ids < 0).any()) or bool((unit_ids < 0).any()):
        raise ValueError("clip_ids and unit_ids must be non-negative")
    if unit_ids.unique().numel() != unit_ids.numel():
        raise ValueError("unit_ids must be unique and canonical")
    if bool((segment_start < 0).any()) or bool((segment_stop <= segment_start).any()):
        raise ValueError("segments must satisfy 0 <= start < stop")

    # Legal starts satisfy start + H < stop. The half-open upper bound is stop-H.
    safe_stop = segment_stop - horizon_steps
    keep = safe_stop > segment_start
    if not bool(keep.any()):
        raise ValueError("no feasible segment can contain the requested horizon")
    return AdmissibleStarts(
        unit_ids=unit_ids[keep],
        clip_ids=clip_ids[keep],
        first=segment_start[keep],
        stop=safe_stop[keep],
    )


def sample_admissible_starts(
    intervals: AdmissibleStarts,
    interval_ids: torch.Tensor,
    *,
    generator: torch.Generator | None = None,
) -> torch.Tensor:
    """Sample starts from filtered interval rows using a dedicated RNG."""
    if interval_ids.ndim != 1:
        raise ValueError("interval_ids must be one-dimensional")
    if interval_ids.dtype not in (torch.int32, torch.int64):
        raise ValueError("interval_ids must use an integer index dtype")
    if interval_ids.numel() == 0:
        return torch.empty(0, dtype=torch.long, device=interval_ids.device)
    if bool((interval_ids < 0).any()) or bool(
        (interval_ids >= intervals.first.numel()).any()
    ):
        raise ValueError("interval_ids contains an out-of-range interval index")
    first = intervals.first.to(interval_ids.device)[interval_ids]
    counts = intervals.counts.to(interval_ids.device)[interval_ids]
    draw = (
        torch.rand(
            interval_ids.numel(),
            device=interval_ids.device,
            generator=generator,
        )
        * counts
    ).long()
    return first + draw


def aggregate_trial_outcomes(
    num_units: int,
    unit_ids: torch.Tensor,
    failed: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Aggregate one fixed-clock batch into sufficient statistics."""
    if num_units <= 0:
        raise ValueError("num_units must be positive")
    if unit_ids.shape != failed.shape or unit_ids.ndim != 1:
        raise ValueError("unit_ids and failed must be aligned one-dimensional tables")
    if unit_ids.dtype not in (torch.int32, torch.int64):
        raise ValueError("unit_ids must use an integer index dtype")
    if bool((unit_ids < 0).any()) or bool((unit_ids >= num_units).any()):
        raise ValueError("unit_ids contains an out-of-range segment index")
    failed_float = failed.float()
    if not bool(torch.isfinite(failed_float).all()) or bool(
        ((failed_float != 0) & (failed_float != 1)).any()
    ):
        raise ValueError("failed outcomes must be finite and binary")
    attempts = torch.bincount(unit_ids, minlength=num_units).to(failed_float)
    failures = torch.bincount(unit_ids, weights=failed_float, minlength=num_units).to(
        failed_float
    )
    return failures, attempts


def update_conditional_failure_statistics(
    failure_mass: torch.Tensor,
    attempt_mass: torch.Tensor,
    batch_failures: torch.Tensor,
    batch_attempts: torch.Tensor,
    *,
    decay: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Update discounted sufficient statistics once per fixed rollout clock.

    The caller must first combine every outcome at a clock tick with
    :func:`aggregate_trial_outcomes`, then call this function exactly once.
    Decaying numerator and denominator together leaves an unvisited unit's
    conditional rate unchanged while allowing later mastery evidence to replace
    older evidence. The two masses, clock, and RNG are checkpoint state.
    """
    shape = failure_mass.shape
    if (
        any(
            value.shape != shape
            for value in (attempt_mass, batch_failures, batch_attempts)
        )
        or failure_mass.ndim != 1
    ):
        raise ValueError("all statistic tables must be aligned and one-dimensional")
    if not 0.0 < decay <= 1.0:
        raise ValueError("decay must be in (0, 1]")
    if any(
        not bool(torch.isfinite(value).all())
        for value in (failure_mass, attempt_mass, batch_failures, batch_attempts)
    ):
        raise ValueError("statistic tables must be finite")
    if bool((failure_mass < 0).any()) or bool((attempt_mass < failure_mass).any()):
        raise ValueError("state must satisfy 0 <= failure_mass <= attempt_mass")
    if bool((batch_failures < 0).any()) or bool(
        (batch_attempts < batch_failures).any()
    ):
        raise ValueError("batch must satisfy 0 <= failures <= attempts")
    return (
        decay * failure_mass + batch_failures.to(failure_mass),
        decay * attempt_mass + batch_attempts.to(attempt_mass),
    )
