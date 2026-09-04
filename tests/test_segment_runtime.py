"""Checkpoint and attribution tests for the exact segment sampler runtime."""

from __future__ import annotations

import json
from pathlib import Path

import torch

from climb.segment_runtime import SegmentSampler, SegmentSamples, canonical_hash


def write_manifest(path: Path) -> None:
    """Write a minimal valid two-unit manifest."""
    units = [
        {
            "unit_id": 11,
            "clip_id": 0,
            "clip": "alpha",
            "segment_start": 0,
            "segment_stop": 10,
            "admissible_start_first": 0,
            "admissible_start_stop": 7,
            "legal_start_count": 7,
            "unsupported_ratio_mean": 0.1,
            "unsupported_ratio_p95": 0.2,
            "unsupported_ratio_max": 0.3,
            "table_index": 0,
            "deployment_mass": 7,
        },
        {
            "unit_id": 29,
            "clip_id": 1,
            "clip": "beta",
            "segment_start": 5,
            "segment_stop": 15,
            "admissible_start_first": 5,
            "admissible_start_stop": 12,
            "legal_start_count": 7,
            "unsupported_ratio_mean": 0.1,
            "unsupported_ratio_p95": 0.2,
            "unsupported_ratio_max": 0.3,
            "table_index": 1,
            "deployment_mass": 7,
        },
    ]
    frozen = {
        "horizon_steps": 3,
        "sources": [],
        "source_units": [],
        "admissible_units": units,
    }
    path.write_text(
        json.dumps(
            {
                "schema_version": "segment_unit_table/1",
                **frozen,
                "unit_table_sha256": canonical_hash(frozen),
            }
        )
    )


def test_sampler_draws_only_horizon_safe_exact_starts(tmp_path: Path) -> None:
    manifest = tmp_path / "units.json"
    write_manifest(manifest)
    sampler = SegmentSampler(manifest, mode="uniform", seed=7)
    samples = sampler.sample(10_000)
    assert set(samples.unit_ids.tolist()) == {11, 29}
    assert bool((samples.local_trial_ends < samples.local_segment_stops).all())
    assert bool((samples.local_starts >= sampler.intervals.first[samples.table_indices]).all())


def test_fixed_clock_outcomes_change_only_adaptive_priority(tmp_path: Path) -> None:
    manifest = tmp_path / "units.json"
    write_manifest(manifest)
    adaptive = SegmentSampler(manifest, mode="adaptive", seed=7, decay=1.0)
    adaptive.record_completed_trials(
        torch.tensor([0, 0, 1, 1]), torch.tensor([1, 1, 0, 0])
    )
    before = adaptive.probabilities.clone()
    assert adaptive.adaptation_total_variation() == 0.0
    adaptive.advance_clock()
    assert torch.equal(before, torch.tensor([0.5, 0.5], dtype=before.dtype))
    assert adaptive.probabilities[0] > adaptive.probabilities[1]
    assert adaptive.adaptation_total_variation() > 0.2
    assert adaptive.lifetime_attempts.tolist() == [2, 2]
    assert adaptive.lifetime_failures.tolist() == [2, 0]


def test_uniform_sampler_reports_zero_adaptation(tmp_path: Path) -> None:
    manifest = tmp_path / "units.json"
    write_manifest(manifest)
    uniform = SegmentSampler(manifest, mode="uniform", seed=7, decay=1.0)
    uniform.record_completed_trials(
        torch.tensor([0, 0, 1, 1]), torch.tensor([1, 1, 0, 0])
    )
    uniform.advance_clock()
    assert uniform.adaptation_total_variation() == 0.0


def test_sampler_equivalent_resume_replays_next_draws(tmp_path: Path) -> None:
    manifest = tmp_path / "units.json"
    write_manifest(manifest)
    original = SegmentSampler(manifest, mode="adaptive", seed=123)
    original.sample(17)
    original.record_completed_trials(torch.tensor([0, 1]), torch.tensor([1, 0]))
    original.advance_clock()
    state = original.state_dict()
    expected = original.sample(100)

    resumed = SegmentSampler(manifest, mode="adaptive", seed=999)
    resumed.load_state_dict(state)
    actual = resumed.sample(100)
    for field in SegmentSamples.__dataclass_fields__:
        assert torch.equal(getattr(expected, field), getattr(actual, field))


def _drive(sampler: SegmentSampler, failed: list[int], ticks: int) -> None:
    for _ in range(ticks):
        sampler.record_completed_trials(
            torch.tensor([0, 1]), torch.tensor(failed, dtype=torch.bool)
        )
        sampler.advance_clock()


def test_learning_progress_rank_is_uniform_until_the_window_fills(tmp_path: Path) -> None:
    manifest = tmp_path / "units.json"
    write_manifest(manifest)
    sampler = SegmentSampler(
        manifest, mode="adaptive", seed=7, difficulty_power=0.0,
        rank="learning_progress", progress_window=3, decay=1.0,
    )
    assert sampler.learning_progress() is None
    _drive(sampler, [1, 0], ticks=2)
    assert sampler.learning_progress() is None
    assert sampler.adaptation_total_variation() == 0.0
    _drive(sampler, [1, 0], ticks=1)
    assert sampler.learning_progress() is not None
    assert sampler.rate_history.shape == (4, 2)


def test_learning_progress_rank_focuses_on_the_changing_unit(tmp_path: Path) -> None:
    manifest = tmp_path / "units.json"
    write_manifest(manifest)
    sampler = SegmentSampler(
        manifest, mode="adaptive", seed=7, difficulty_power=0.0,
        rank="learning_progress", progress_window=2, decay=1.0,
        max_unit_probability=None, max_clip_probability=None,
    )
    # unit 0 keeps failing (rate saturates, no progress); unit 1 flips from
    # failing to succeeding, so its success estimate moves across the window.
    _drive(sampler, [1, 1], ticks=3)
    _drive(sampler, [1, 0], ticks=2)
    progress = sampler.learning_progress()
    assert progress is not None
    assert progress[1] > progress[0]
    assert sampler.probabilities[1] > sampler.probabilities[0]
    assert sampler.adaptation_total_variation() > 0.0


def test_uncertainty_rank_prefers_unsaturated_units(tmp_path: Path) -> None:
    manifest = tmp_path / "units.json"
    write_manifest(manifest)
    sampler = SegmentSampler(
        manifest, mode="adaptive", seed=7, difficulty_power=0.0,
        rank="uncertainty", decay=1.0,
        max_unit_probability=None, max_clip_probability=None,
    )
    # unit 0 always fails (s -> 0); unit 1 alternates (s ~ 0.5).
    for tick in range(20):
        sampler.record_completed_trials(
            torch.tensor([0, 1]), torch.tensor([True, bool(tick % 2)])
        )
        sampler.advance_clock()
    assert sampler.probabilities[1] > sampler.probabilities[0]
    assert 0.0 < sampler.saturation_fraction() < 1.0


def test_non_failure_ranks_require_zero_difficulty_power(tmp_path: Path) -> None:
    manifest = tmp_path / "units.json"
    write_manifest(manifest)
    try:
        SegmentSampler(manifest, mode="adaptive", seed=7, rank="learning_progress")
    except ValueError as error:
        assert "difficulty_power" in str(error)
    else:
        raise AssertionError("expected difficulty_power == 0 to be enforced")


def test_learning_progress_resume_round_trips_the_history(tmp_path: Path) -> None:
    manifest = tmp_path / "units.json"
    write_manifest(manifest)
    original = SegmentSampler(
        manifest, mode="adaptive", seed=123, difficulty_power=0.0,
        rank="learning_progress", progress_window=3,
    )
    _drive(original, [1, 0], ticks=5)
    state = original.state_dict()
    expected_draws = original.sample(100)
    _drive(original, [0, 1], ticks=2)
    expected_after = original.probabilities.clone()

    resumed = SegmentSampler(
        manifest, mode="adaptive", seed=999, difficulty_power=0.0,
        rank="learning_progress", progress_window=3,
    )
    resumed.load_state_dict(state)
    actual_draws = resumed.sample(100)
    for field in SegmentSamples.__dataclass_fields__:
        assert torch.equal(getattr(expected_draws, field), getattr(actual_draws, field))
    _drive(resumed, [0, 1], ticks=2)
    assert torch.equal(resumed.probabilities, expected_after)

    wrong = SegmentSampler(
        manifest, mode="adaptive", seed=999, difficulty_power=0.0,
        rank="learning_progress", progress_window=4,
    )
    try:
        wrong.load_state_dict(state)
    except ValueError:
        pass
    else:
        raise AssertionError("mismatched progress_window must be rejected")


def test_failure_rank_state_without_history_still_loads(tmp_path: Path) -> None:
    manifest = tmp_path / "units.json"
    write_manifest(manifest)
    original = SegmentSampler(manifest, mode="adaptive", seed=1)
    _drive(original, [1, 0], ticks=2)
    state = original.state_dict()
    state.pop("rate_history")
    state.pop("rank")
    resumed = SegmentSampler(manifest, mode="adaptive", seed=2)
    resumed.load_state_dict(state)
    assert torch.equal(resumed.probabilities, original.probabilities)


def test_learning_progress_exposes_checkpoint_diagnostic_vectors(tmp_path: Path) -> None:
    manifest = tmp_path / "units.json"
    write_manifest(manifest)
    sampler = SegmentSampler(
        manifest,
        mode="adaptive",
        seed=7,
        difficulty_power=0.0,
        rank="learning_progress",
        progress_window=2,
    )
    assert sampler.learning_progress() is None
    _drive(sampler, [1, 0], ticks=2)
    progress = sampler.learning_progress()
    rates = sampler.conditional_success_rates()
    assert progress is not None
    assert progress.shape == rates.shape == (2,)
    assert bool((progress >= 0.0).all())
    assert bool(((rates >= 0.0) & (rates <= 1.0)).all())
