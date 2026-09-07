"""Check measured reset regression and reject corrupted retirement telemetry."""

from copy import deepcopy
import csv
import json
from pathlib import Path
import sys

import pytest
import torch

WORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK / "tools"))
from analyze_physics_reset_fixture import analyze, verify_lifecycle

OLD = WORK / "reports/injected_reset_fixture_2026-09-06"
FIXED = WORK / "reports/injected_reset_fixed_2026-09-06"


@pytest.fixture(scope="module")
def measured():
    return (torch.load(FIXED / "delay_20ms/lifecycle.pt", weights_only=True),
            list(csv.DictReader((FIXED / "delay_20ms/evaluation.csv").open())),
            json.loads((FIXED / "design.json").read_text()))


def test_complete_fixed_fixture():
    result = analyze(FIXED)
    assert result["status"] == "injected_reset_fixture_pass"
    assert result["episode_rows"] == 36
    assert result["confirmation_endpoints_opened"] is False


@pytest.mark.parametrize("name", ["delay_5ms", "delay_10ms", "delay_20ms"])
def test_pre_fix_measured_clock_regression_rejected(name):
    data = torch.load(OLD / name / "lifecycle.pt", weights_only=True)
    rows = list(csv.DictReader((OLD / name / "evaluation.csv").open()))
    design = json.loads((OLD / "design.json").read_text())
    reset = data["resets"][0]
    assert torch.equal(reset["after"]["delay_0_count"][1:],
                       reset["before"]["delay_0_count"][1:] + 1)
    with pytest.raises(ValueError, match="partial reset changed another world: delay_0_(count|peek)"):
        verify_lifecycle(data, rows, design, name)


@pytest.mark.parametrize("fault", ["score_after_retirement", "horizon_success", "missing_reset",
                                  "wrong_reset_world", "unselected_state", "unselected_clock",
                                  "uncleared_buffer", "cross_reset_delay", "injection"])
def test_corrupted_reset_or_scoring_rejected(measured, fault):
    data, rows, design = deepcopy(measured)
    if fault == "score_after_retirement":
        rows[0]["error_body_pos_mean"] = str(float(rows[0]["error_body_pos_mean"]) + 0.1)
    elif fault == "horizon_success":
        rows[3]["success"] = "1"
    elif fault == "missing_reset":
        data["resets"].pop(1)
    elif fault == "wrong_reset_world":
        data["resets"][0]["ids"][0] = 2
    elif fault == "unselected_state":
        data["resets"][0]["after"]["qpos"][2, 0] += 0.1
    elif fault == "unselected_clock":
        data["resets"][0]["after"]["delay_0_count"][2] += 1
    elif fault == "uncleared_buffer":
        data["resets"][0]["after"]["delay_0_peek"][0, 0] = 0.1
    elif fault == "cross_reset_delay":
        data["physics"][40]["ctrl"][0, 0] += 0.1
    elif fault == "injection":
        data["steps"][9]["terms"]["fixture_injected_failure"][0] = False
    with pytest.raises(ValueError):
        verify_lifecycle(data, rows, design, "delay_20ms")
