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
