"""Failures and missing common survivors must remain visible in secondaries."""

from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from relative_policy_secondaries import POSE_METRICS, WORK, paired_secondary


@pytest.fixture
def rows():
    conditions = [{"condition_id": str(i), "clip": "a" if i < 2 else "b", "start_frame": i,
                   "replicate": 0, "horizon_steps": 150, "full_window": True} for i in range(4)]
    left = [{**row, "survival_s": 3.0, "actual_window_s": 3.0, "success": 1,
             WORK: 6.0, POSE_METRICS[0]: 0.1, POSE_METRICS[1]: 0.2} for row in conditions]
    right = deepcopy(left)
    for row in right:
        row[POSE_METRICS[0]] = 0.3
    return left, right, conditions, ["a", "b"]


def test_paired_pose_and_work_keep_counts(rows):
    result = paired_secondary(*rows)
    assert result["common_successes"] == 4
    assert result["covered_pose_clips"] == 2
    assert result["pose_left_minus_right_covered_clip_mean"][POSE_METRICS[0]] == pytest.approx(-0.2)
    assert result["per_clip"]["a"]["work_all_conditions"]["left"]["exposure_weighted_power_per_actuator_w"] == 2


def test_early_failure_is_less_work_but_not_more_efficient(rows):
    left, right, conditions, clips = rows
    left[0].update(success=0, survival_s=0.3, **{WORK: 0.6})
    result = paired_secondary(left, right, conditions, clips)
    clip = result["per_clip"]["a"]
    assert clip["counts"] == {"conditions": 2, "common_successes": 1, "left_successes": 1, "right_successes": 2}
    assert clip["work_left_minus_right_j"] == pytest.approx(-2.7)
    assert clip["work_all_conditions"]["left"]["exposure_weighted_power_per_actuator_w"] == pytest.approx(2)


def test_no_common_survivors_keep_nulls_and_panel_denominator(rows):
    left, right, conditions, clips = rows
    for row in left:
        row.update(success=0, survival_s=0.0, **{WORK: 0.0})
    result = paired_secondary(left, right, conditions, clips)
    assert result["panel_clips"] == 2 and result["covered_pose_clips"] == 0
    assert result["conditions"] == 4 and result["common_successes"] == 0
    assert result["pose_left_minus_right_covered_clip_mean"][POSE_METRICS[0]] is None
    assert result["per_clip"]["b"]["work_all_conditions"]["left"]["exposure_weighted_power_per_actuator_w"] is None


def test_failure_at_final_step_is_not_common_success(rows):
    left, right, conditions, clips = rows
    left[0]["success"] = 0
    result = paired_secondary(left, right, conditions, clips)
    assert result["common_successes"] == 3


@pytest.mark.parametrize("change", [{"success": 2}, {"survival_s": 1.0}, {WORK: float("nan")}, {WORK: -1.0}])
def test_invalid_secondary_values_stop_analysis(rows, change):
    left, right, conditions, clips = rows
    left[0].update(change)
    with pytest.raises(ValueError):
        paired_secondary(left, right, conditions, clips)


def test_missing_condition_cannot_change_denominator(rows):
    left, right, conditions, clips = rows
    with pytest.raises(ValueError, match="condition"):
        paired_secondary(left[:-1], right, conditions, clips)
