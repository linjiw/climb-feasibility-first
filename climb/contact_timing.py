"""Reference-contact proxy construction and event-timing metrics.

These functions distinguish a kinematic contact proxy from physical contact
ground truth. A caller may promote the proxy only after a separate validation
protocol establishes its agreement with an independent reference.
"""

from __future__ import annotations

from typing import Any

import numpy as np

FOOT_NAMES = ("left", "right")
EVENT_NAMES = ("touchdown", "liftoff")


def _merge_short_runs(mask: np.ndarray, minimum_frames: int) -> np.ndarray:
    """Merge interior binary runs shorter than ``minimum_frames``."""
    result = np.asarray(mask, dtype=bool).copy()
    if result.ndim != 1:
        raise ValueError("contact mask must be one-dimensional")
    if minimum_frames <= 0:
        raise ValueError("minimum_frames must be positive")
    if result.size < 3 or minimum_frames == 1:
        return result

    changed = True
    while changed:
        changed = False
        boundaries = np.flatnonzero(result[1:] != result[:-1]) + 1
        starts = np.concatenate(([0], boundaries))
        stops = np.concatenate((boundaries, [result.size]))
        for index in range(1, len(starts) - 1):
            if (
                stops[index] - starts[index] < minimum_frames
                and result[starts[index - 1]] == result[starts[index + 1]]
            ):
                result[starts[index] : stops[index]] = result[starts[index - 1]]
                changed = True
                break
    return result


def contact_mask_from_signals(
    clearance_m: np.ndarray,
    speed_mps: np.ndarray,
    *,
    enter_clearance_m: float,
    exit_clearance_m: float,
    enter_speed_mps: float,
    exit_speed_mps: float,
    minimum_run_frames: int,
) -> np.ndarray:
    """Construct a hysteretic, debounced kinematic contact proxy."""
    clearance = np.asarray(clearance_m, dtype=float)
    speed = np.asarray(speed_mps, dtype=float)
    if clearance.ndim != 1 or speed.shape != clearance.shape:
        raise ValueError("clearance and speed must be equal one-dimensional arrays")
    if not np.isfinite(clearance).all() or not np.isfinite(speed).all():
        raise ValueError("clearance and speed must be finite")
    if not 0 <= enter_clearance_m <= exit_clearance_m:
        raise ValueError("clearance thresholds must satisfy 0 <= enter <= exit")
    if not 0 <= enter_speed_mps <= exit_speed_mps:
        raise ValueError("speed thresholds must satisfy 0 <= enter <= exit")

    result = np.zeros(clearance.size, dtype=bool)
    active = False
    for index, (gap, velocity) in enumerate(zip(clearance, speed, strict=True)):
        if active:
            active = gap <= exit_clearance_m and velocity <= exit_speed_mps
        else:
            active = gap <= enter_clearance_m and velocity <= enter_speed_mps
        result[index] = active
    return _merge_short_runs(result, minimum_run_frames)


def event_frames(mask: np.ndarray) -> dict[str, np.ndarray]:
    """Return internal touchdown and liftoff transitions for one foot."""
    state = np.asarray(mask, dtype=bool)
    if state.ndim != 1:
        raise ValueError("contact mask must be one-dimensional")
    changes = np.flatnonzero(state[1:] != state[:-1]) + 1
    return {
        "touchdown": changes[state[changes]],
        "liftoff": changes[~state[changes]],
    }


def match_event_frames(
    reference: np.ndarray,
    observed: np.ndarray,
    tolerance_frames: int,
) -> dict[str, Any]:
    """Chronologically match events one-to-one within a fixed tolerance."""
    expected = np.asarray(reference, dtype=np.int64)
    actual = np.asarray(observed, dtype=np.int64)
    if expected.ndim != 1 or actual.ndim != 1:
        raise ValueError("event frames must be one-dimensional")
    if tolerance_frames < 0:
        raise ValueError("tolerance_frames must be nonnegative")
    if np.any(expected[1:] < expected[:-1]) or np.any(actual[1:] < actual[:-1]):
        raise ValueError("event frames must be sorted")

    ref_index = 0
    obs_index = 0
    errors = []
    while ref_index < expected.size and obs_index < actual.size:
        delta = int(actual[obs_index] - expected[ref_index])
        if abs(delta) <= tolerance_frames:
            errors.append(delta)
            ref_index += 1
            obs_index += 1
        elif actual[obs_index] < expected[ref_index] - tolerance_frames:
            obs_index += 1
        else:
            ref_index += 1
    true_positive = len(errors)
    false_positive = int(actual.size - true_positive)
    false_negative = int(expected.size - true_positive)
    return {
        "tp": true_positive,
        "fp": false_positive,
        "fn": false_negative,
        "signed_errors_frames": errors,
    }


def _ratio(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else float("nan")


def contact_event_metrics(
    reference_contact: np.ndarray,
    observed_contact: np.ndarray,
    *,
    tolerance_frames: int,
) -> dict[str, Any]:
    """Score per-foot touchdown/liftoff events and aggregate micro-F1."""
    reference = np.asarray(reference_contact, dtype=bool)
    observed = np.asarray(observed_contact, dtype=bool)
    if reference.shape != observed.shape or reference.ndim != 2:
        raise ValueError("contact arrays must have equal shape [frames, feet]")
    if reference.shape[1] != len(FOOT_NAMES):
        raise ValueError(f"expected {len(FOOT_NAMES)} feet")

    detail: dict[str, Any] = {}
    total = {"tp": 0, "fp": 0, "fn": 0}
    timing_errors = []
    for foot_index, foot in enumerate(FOOT_NAMES):
        detail[foot] = {}
        expected_events = event_frames(reference[:, foot_index])
        actual_events = event_frames(observed[:, foot_index])
        for event in EVENT_NAMES:
            matched = match_event_frames(
                expected_events[event],
                actual_events[event],
                tolerance_frames,
            )
            denominator = 2 * matched["tp"] + matched["fp"] + matched["fn"]
            detail[foot][event] = {
                **matched,
                "f1": _ratio(2 * matched["tp"], denominator),
                "matched_timing_mae_frames": (
                    float(
                        np.mean(
                            [abs(value) for value in matched["signed_errors_frames"]]
                        )
                    )
                    if matched["signed_errors_frames"]
                    else float("nan")
                ),
            }
            for key in total:
                total[key] += matched[key]
            timing_errors.extend(abs(value) for value in matched["signed_errors_frames"])

    precision = _ratio(total["tp"], total["tp"] + total["fp"])
    recall = _ratio(total["tp"], total["tp"] + total["fn"])
    f1 = _ratio(2 * total["tp"], 2 * total["tp"] + total["fp"] + total["fn"])
    intersection = int(np.logical_and(reference, observed).sum())
    union = int(np.logical_or(reference, observed).sum())
    return {
        **total,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "matched_timing_mae_frames": (
            float(np.mean(timing_errors)) if timing_errors else float("nan")
        ),
        "contact_state_iou": _ratio(intersection, union),
        "reference_event_count": int(total["tp"] + total["fn"]),
        "observed_event_count": int(total["tp"] + total["fp"]),
        "tolerance_frames": tolerance_frames,
        "detail": detail,
    }
