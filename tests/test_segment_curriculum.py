"""CPU invariants for the post-FGAS segment curriculum."""

from __future__ import annotations

import pytest
import torch

from climb.segment_curriculum import (
    aggregate_trial_outcomes,
    build_admissible_starts,
    conditional_failure_rate,
    sample_admissible_starts,
    sampling_concentration,
    segment_sampling_probabilities,
    update_conditional_failure_statistics,
    validate_sampling_concentration,
)


def test_priority_uses_conditional_rate_not_failure_flux() -> None:
    rates = conditional_failure_rate(
        failures=torch.tensor([81.0, 9.0]),
        attempts=torch.tensor([90.0, 10.0]),
        prior_strength=0.0,
    )
    probabilities = segment_sampling_probabilities(
        difficulty_rates=rates,
        eligibility=torch.ones(2),
        deployment_mass=torch.ones(2),
        exploration_ratio=0.1,
    )
    torch.testing.assert_close(probabilities, torch.tensor([0.5, 0.5]))


def test_success_evidence_reduces_priority() -> None:
    batch_failures, batch_attempts = aggregate_trial_outcomes(
        num_units=2,
        unit_ids=torch.zeros(4, dtype=torch.long),
        failed=torch.zeros(4),
    )
    failures, attempts = update_conditional_failure_statistics(
        failure_mass=torch.ones(2),
        attempt_mass=torch.full((2,), 2.0),
        batch_failures=batch_failures,
        batch_attempts=batch_attempts,
        decay=1.0,
    )
    rates = conditional_failure_rate(
        failures,
        attempts,
        prior_strength=0.0,
    )
    probabilities = segment_sampling_probabilities(
        difficulty_rates=rates,
        eligibility=torch.ones(2),
        deployment_mass=torch.ones(2),
    )
    assert probabilities[0] < probabilities[1]


def test_invalid_support_fails_closed() -> None:
    with pytest.raises(ValueError, match="no admissible segment"):
        segment_sampling_probabilities(
            difficulty_rates=torch.full((2,), 0.5),
            eligibility=torch.zeros(2),
            deployment_mass=torch.ones(2),
        )


def test_soft_score_cannot_replace_hard_support() -> None:
    with pytest.raises(ValueError, match="binary hard-support"):
        segment_sampling_probabilities(
            difficulty_rates=torch.full((2,), 0.5),
            eligibility=torch.tensor([1.0, 0.5]),
            deployment_mass=torch.ones(2),
        )


def test_continuous_ranking_cannot_leak_invalid_units() -> None:
    probabilities = segment_sampling_probabilities(
        difficulty_rates=torch.full((3,), 0.5),
        eligibility=torch.tensor([1.0, 1.0, 0.0]),
        deployment_mass=torch.ones(3),
        ranking_weight=torch.tensor([100.0, 1.0, 1000.0]),
        exploration_ratio=0.2,
    )
    assert probabilities[2] == 0.0
    assert probabilities[0] >= 0.1
    assert probabilities[1] >= 0.1


def test_concentration_gate_catches_a_persistent_hard_unit() -> None:
    rates = torch.zeros(100)
    rates[0] = 1.0
    probabilities = segment_sampling_probabilities(
        difficulty_rates=rates,
        eligibility=torch.ones(100),
        deployment_mass=torch.ones(100),
        exploration_ratio=0.1,
    )
    diagnostics = sampling_concentration(probabilities)
    assert diagnostics.top1_probability > 0.9
    assert diagnostics.entropy_effective_units < 3.0
    with pytest.raises(ValueError, match="top-1"):
        validate_sampling_concentration(
            probabilities,
            max_top1_probability=0.2,
            min_entropy_effective_units=20.0,
        )


def test_concentration_gate_accepts_balanced_sampling() -> None:
    probabilities = torch.full((100,), 0.01)
    diagnostics = validate_sampling_concentration(
        probabilities,
        max_top1_probability=0.02,
        min_entropy_effective_units=90.0,
    )
    assert diagnostics.top1_probability == pytest.approx(0.01)
    assert diagnostics.entropy_effective_units == pytest.approx(100.0, rel=1.0e-5)


def test_unit_and_clip_caps_prevent_persistent_hard_unit_collapse() -> None:
    rates = torch.zeros(100)
    rates[0] = 1.0
    probabilities = segment_sampling_probabilities(
        difficulty_rates=rates,
        eligibility=torch.ones(100),
        deployment_mass=torch.ones(100),
        exploration_ratio=0.1,
        clip_ids=torch.arange(100) // 10,
        max_unit_probability=0.05,
        max_clip_probability=0.2,
    )
    torch.testing.assert_close(probabilities.sum(), torch.tensor(1.0))
    assert float(probabilities.max()) <= 0.05 + 1.0e-6
    clip_mass = torch.zeros(10).scatter_add_(
        0, torch.arange(100) // 10, probabilities
    )
    assert bool((clip_mass <= 0.2 + 1.0e-6).all())
    assert bool((probabilities >= 0.001 - 1.0e-7).all())
    assert sampling_concentration(probabilities).entropy_effective_units > 20.0


def test_probability_caps_preserve_hard_support() -> None:
    probabilities = segment_sampling_probabilities(
        difficulty_rates=torch.tensor([1.0, 0.0, 1.0]),
        eligibility=torch.tensor([1.0, 1.0, 0.0]),
        deployment_mass=torch.ones(3),
        exploration_ratio=0.1,
        clip_ids=torch.tensor([0, 1, 2]),
        max_unit_probability=0.6,
        max_clip_probability=0.6,
    )
    assert probabilities[2] == 0.0
    assert bool((probabilities[:2] >= 0.05 - 1.0e-7).all())


def test_infeasible_probability_caps_fail_before_training() -> None:
    with pytest.raises(ValueError, match="cannot contain unit mass"):
        segment_sampling_probabilities(
            difficulty_rates=torch.ones(2),
            eligibility=torch.ones(2),
            deployment_mass=torch.ones(2),
            max_unit_probability=0.4,
        )
    with pytest.raises(ValueError, match="exploration floor"):
        segment_sampling_probabilities(
            difficulty_rates=torch.ones(2),
            eligibility=torch.ones(2),
            deployment_mass=torch.tensor([0.99, 0.01]),
            exploration_ratio=0.5,
            max_unit_probability=0.4,
        )


def test_large_table_cannot_hide_floor_cap_conflict_in_tolerance() -> None:
    deployment = torch.ones(1_000)
    deployment[0] = 2.2
    with pytest.raises(ValueError, match="below the declared exploration floor"):
        segment_sampling_probabilities(
            difficulty_rates=torch.ones(1_000),
            eligibility=torch.ones(1_000),
            deployment_mass=deployment,
            exploration_ratio=0.5,
            max_unit_probability=1.0 / 1_000,
        )


def test_noop_clip_cap_tolerates_float32_normalization_roundoff() -> None:
    probabilities = segment_sampling_probabilities(
        difficulty_rates=torch.tensor([0.1, 0.2, 0.3]),
        eligibility=torch.ones(3),
        deployment_mass=torch.ones(3),
        clip_ids=torch.zeros(3, dtype=torch.long),
        max_unit_probability=0.5,
        max_clip_probability=1.0,
    )
    torch.testing.assert_close(probabilities.sum(), torch.tensor(1.0))
    assert bool((probabilities <= 0.5).all())


def test_capped_projection_is_bitwise_replayable() -> None:
    rates = torch.linspace(0.0, 1.0, 1_000)
    eligibility = torch.ones(1_000)
    deployment = torch.linspace(1.0, 2.0, 1_000)
    clip_ids = torch.arange(1_000) // 10
    first = segment_sampling_probabilities(
        rates,
        eligibility,
        deployment,
        exploration_ratio=0.1,
        clip_ids=clip_ids,
        max_unit_probability=0.003,
        max_clip_probability=0.02,
    )
    second = segment_sampling_probabilities(
        rates,
        eligibility,
        deployment,
        exploration_ratio=0.1,
        clip_ids=clip_ids,
        max_unit_probability=0.003,
        max_clip_probability=0.02,
    )
    assert torch.equal(first, second)


def test_float32_group_sum_cannot_reject_a_feasible_noop_clip_cap() -> None:
    generator = torch.Generator().manual_seed(220)
    eligibility = torch.zeros(141)
    eligibility[:120] = 1.0
    probabilities = segment_sampling_probabilities(
        difficulty_rates=torch.rand(141, generator=generator),
        eligibility=eligibility,
        deployment_mass=torch.ones(141),
        exploration_ratio=0.6748759746551514,
        clip_ids=torch.zeros(141, dtype=torch.long),
        max_unit_probability=0.00875,
        max_clip_probability=1.0,
    )
    assert float(probabilities.double().sum()) == pytest.approx(1.0, abs=1.0e-6)
    assert float(probabilities.max()) <= 0.00875 + 1.0e-7
    assert bool((probabilities[eligibility == 0] == 0).all())


@pytest.mark.parametrize("exploration_ratio", [0.0, 1.0])
def test_probability_cap_exploration_endpoints(exploration_ratio: float) -> None:
    probabilities = segment_sampling_probabilities(
        difficulty_rates=torch.tensor([1.0, 0.5, 0.25, 0.0]),
        eligibility=torch.ones(4),
        deployment_mass=torch.ones(4),
        exploration_ratio=exploration_ratio,
        clip_ids=torch.tensor([2, 2, 9, 9]),
        max_unit_probability=0.4,
        max_clip_probability=0.6,
    )
    assert float(probabilities.max()) <= 0.4 + 1.0e-7
    torch.testing.assert_close(probabilities.sum(), torch.tensor(1.0))


def test_half_precision_probability_state_is_rejected() -> None:
    with pytest.raises(ValueError, match="float32 or float64"):
        segment_sampling_probabilities(
            difficulty_rates=torch.ones(4, dtype=torch.float16),
            eligibility=torch.ones(4),
            deployment_mass=torch.ones(4),
        )


def test_fixed_horizon_starts_never_cross_a_segment_boundary() -> None:
    intervals = build_admissible_starts(
        clip_ids=torch.tensor([0, 1, 2]),
        segment_start=torch.tensor([10, 30, 50]),
        segment_stop=torch.tensor([20, 33, 60]),
        horizon_steps=4,
        unit_ids=torch.tensor([101, 205, 309]),
    )
    # The three-frame segment is removed. Legal starts in the others are
    # [10, 16) and [50, 56), so four advances remain strictly before the stop.
    torch.testing.assert_close(intervals.clip_ids, torch.tensor([0, 2]))
    torch.testing.assert_close(intervals.unit_ids, torch.tensor([101, 309]))
    torch.manual_seed(7)
    interval_ids = torch.randint(0, 2, (20_000,))
    starts = sample_admissible_starts(intervals, interval_ids)
    stops = torch.tensor([20, 60])[interval_ids]
    assert bool((starts >= intervals.first[interval_ids]).all())
    assert bool((starts + 4 < stops).all())


def test_horizon_requires_an_initial_frame_plus_all_advances() -> None:
    intervals = build_admissible_starts(
        clip_ids=torch.tensor([0, 1]),
        segment_start=torch.tensor([10, 20]),
        segment_stop=torch.tensor([14, 25]),
        horizon_steps=4,
    )
    # Four frames cannot support four transitions; five frames admit one start.
    torch.testing.assert_close(intervals.clip_ids, torch.tensor([1]))
    torch.testing.assert_close(intervals.first, torch.tensor([20]))
    torch.testing.assert_close(intervals.stop, torch.tensor([21]))


def test_fixed_clock_outcome_aggregation_is_order_independent() -> None:
    unit_ids = torch.tensor([0, 0, 2, 1, 0])
    failed = torch.tensor([1, 0, 0, 1, 1])
    forward = aggregate_trial_outcomes(3, unit_ids, failed)
    reverse = aggregate_trial_outcomes(3, unit_ids.flip(0), failed.flip(0))
    torch.testing.assert_close(forward[0], reverse[0])
    torch.testing.assert_close(forward[1], reverse[1])


def test_unvisited_unit_rate_is_unchanged_by_fixed_clock_decay() -> None:
    old_failures = torch.tensor([1.0, 4.0, 2.0])
    old_attempts = torch.tensor([5.0, 5.0, 5.0])
    batch_failures, batch_attempts = aggregate_trial_outcomes(
        num_units=3,
        unit_ids=torch.tensor([0, 0, 2]),
        failed=torch.tensor([1, 1, 0]),
    )
    failures, attempts = update_conditional_failure_statistics(
        old_failures,
        old_attempts,
        batch_failures,
        batch_attempts,
        decay=0.9,
    )
    old_rates = conditional_failure_rate(old_failures, old_attempts, prior_strength=0.0)
    rates = conditional_failure_rate(failures, attempts, prior_strength=0.0)
    assert rates[0] > old_rates[0]
    assert rates[2] < old_rates[2]
    torch.testing.assert_close(rates[1], old_rates[1])


def test_sampler_uses_a_dedicated_replayable_generator() -> None:
    intervals = build_admissible_starts(
        clip_ids=torch.tensor([0]),
        segment_start=torch.tensor([10]),
        segment_stop=torch.tensor([30]),
        horizon_steps=4,
    )
    interval_ids = torch.zeros(100, dtype=torch.long)
    first_generator = torch.Generator().manual_seed(123)
    second_generator = torch.Generator().manual_seed(123)
    first = sample_admissible_starts(intervals, interval_ids, generator=first_generator)
    second = sample_admissible_starts(
        intervals, interval_ids, generator=second_generator
    )
    torch.testing.assert_close(first, second)
