"""Independent seed inference and failure-preserving R3 statistical decisions."""

from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from analyze_relative_policy import ARMS, aggregate_rows, analyze_scores, seed_summary, synthetic


def test_all_six_predeclared_branches():
    result = synthetic()
    assert len(result["branches"]) == 6
    assert not result["branches"]["nonregression_failure"]["nonregression_pass"]


def test_interval_uses_three_seeds_not_300_clip_observations():
    result = seed_summary(np.array([0.01, 0.02, 0.03]))
    assert result["independent_units"] == 3
    assert result["df"] == 2
    assert result["sd_across_seeds"] == pytest.approx(0.01)
    # t_(0.975,2) = 4.3026527297, not a normal 1.96 multiplier.
    assert result["seed_t_95ci"][0] == pytest.approx(0.02 - 4.3026527297 * 0.01 / np.sqrt(3))


@pytest.mark.parametrize("case", ["nan", "missing_arm", "out_of_range", "missing_seed", "duplicate_hard"])
def test_bad_panel_cannot_enter_inference(case):
    scores = {arm: np.full((3, 100), 0.5) for arm in ARMS}
    hard = np.arange(25)
    if case == "nan":
        scores["U"][0, 0] = np.nan
    elif case == "missing_arm":
        del scores["D"]
    elif case == "out_of_range":
        scores["R"][0, 0] = 1.1
    elif case == "missing_seed":
        scores["R"] = scores["R"][:2]
    else:
        hard[-1] = 0
    with pytest.raises(ValueError):
        analyze_scores(scores, hard, manipulation_pass=True, provenance_pass=True)


def test_failed_gate_never_touches_outcome_arrays():
    assert analyze_scores({}, None, manipulation_pass=False, provenance_pass=True)["status"] == "not_tested"
    assert analyze_scores({}, None, manipulation_pass=True, provenance_pass=False)["status"] == "invalid"


@pytest.fixture
def trial_rows():
    conditions = [{"condition_id": f"alpha@0:r{replicate}", "clip": "alpha", "start_frame": 0,
                   "replicate": replicate, "horizon_steps": 150, "full_window": True}
                  for replicate in range(2)]
    rows = [{**condition, "survival_s": survival, "actual_window_s": 3.0,
             "common_root_relative_mpkpe_m_mean": 0.0,
             "common_anchor_orientation_error_rad_mean": 0.0}
            for condition, survival in zip(conditions, (0.0, 3.0))]
    return conditions, rows


def test_failed_trial_stays_in_denominator(trial_rows):
    conditions, rows = trial_rows
    assert aggregate_rows(rows, conditions, ["alpha"]).tolist() == [0.5]


@pytest.mark.parametrize("case", ["duplicate", "missing", "identity", "window", "nan", "negative"])
def test_invalid_or_unpaired_trial_is_rejected(trial_rows, case):
    conditions, rows = trial_rows
    if case == "duplicate":
        rows.append(rows[0])
    elif case == "missing":
        rows.pop()
    elif case == "identity":
        rows[0]["start_frame"] = 1
    elif case == "window":
        rows[0]["actual_window_s"] = 1
    elif case == "nan":
        rows[0]["survival_s"] = float("nan")
    else:
        rows[0]["common_root_relative_mpkpe_m_mean"] = -0.01
    with pytest.raises(ValueError):
        aggregate_rows(rows, conditions, ["alpha"])
