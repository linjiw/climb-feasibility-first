from __future__ import annotations

import numpy as np

from climb.contact_timing import (
    contact_event_metrics,
    contact_mask_from_signals,
    event_frames,
)


def test_contact_proxy_uses_hysteresis_and_merges_chatter() -> None:
    clearance = np.array([0.04, 0.009, 0.008, 0.03, 0.008, 0.008, 0.04])
    speed = np.full(clearance.shape, 0.1)

    mask = contact_mask_from_signals(
        clearance,
        speed,
        enter_clearance_m=0.01,
        exit_clearance_m=0.02,
        enter_speed_mps=0.2,
        exit_speed_mps=0.4,
        minimum_run_frames=2,
    )

    assert mask.tolist() == [False, True, True, True, True, True, False]
    assert event_frames(mask)["touchdown"].tolist() == [1]
    assert event_frames(mask)["liftoff"].tolist() == [6]


def test_event_f1_matches_each_foot_and_event_once() -> None:
    reference = np.zeros((12, 2), dtype=bool)
    observed = np.zeros_like(reference)
    reference[2:7, 0] = True
    reference[5:10, 1] = True
    observed[3:8, 0] = True
    observed[4:9, 1] = True

    metrics = contact_event_metrics(reference, observed, tolerance_frames=1)

    assert metrics["tp"] == 4
    assert metrics["fp"] == 0
    assert metrics["fn"] == 0
    assert metrics["f1"] == 1.0
    assert metrics["matched_timing_mae_frames"] == 1.0


def test_event_f1_penalizes_missed_and_spurious_transitions() -> None:
    reference = np.zeros((12, 2), dtype=bool)
    observed = np.zeros_like(reference)
    reference[2:8, 0] = True
    observed[2:5, 0] = True
    observed[10:11, 0] = True

    metrics = contact_event_metrics(reference, observed, tolerance_frames=1)

    assert metrics["tp"] == 1
    assert metrics["fp"] == 3
    assert metrics["fn"] == 1
    assert np.isclose(metrics["f1"], 1 / 3)


def test_no_events_are_not_counted_as_perfect_timing() -> None:
    empty = np.zeros((12, 2), dtype=bool)

    metrics = contact_event_metrics(empty, empty, tolerance_frames=2)

    assert np.isnan(metrics["f1"])
    assert metrics["reference_event_count"] == 0
