"""Reject lost entity resets, changed retired scores and incomplete inference."""

from copy import deepcopy
import csv
import json
from pathlib import Path
import sys

import pytest
import torch

WORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK / "tools"))
from analyze_natural_entity_lifecycle import analyze, verify_lifecycle
from eval_natural_lifecycle import verify_policy

RUN = WORK / "reports/natural_entity_lifecycle_2026-09-06"


@pytest.fixture(scope="module")
def measured():
    design = json.loads((RUN / "design.json").read_text())
    return (torch.load(RUN / "delay_20ms/lifecycle.pt", weights_only=True),
            list(csv.DictReader((RUN / "delay_20ms/evaluation.csv").open())),
            json.loads(Path(design["evaluator_arguments"]["conditions"]).read_text())["conditions"])


def test_complete_natural_coverage():
    result = analyze(RUN)
    assert result["status"] == "natural_entity_lifecycle_pass"
    assert result["episode_rows"] == 63
    assert result["natural_failure_rows"] == 21
    assert result["early_success_rows"] == 10
    assert result["previous_csvs_exact_match"] is True
    assert result["confirmation_endpoints_opened"] is False


def test_early_stop_inference_coverage():
    policy = torch.load(RUN / "delay_20ms/policy.pt", weights_only=True)
    assert verify_policy(policy, 131)["unchanged"] is True
    with pytest.raises(ValueError, match="inference coverage"):
        verify_policy(policy, 150)


@pytest.mark.parametrize("fault", ["missing_motion_reset", "entity_reset_time", "unselected_history",
                                  "uncleared_history", "early_success_score", "failed_world_success",
                                  "injected_failure", "missing_final_step", "cross_reset_control"])
def test_corrupt_natural_lifecycle_rejected(measured, fault):
    data, rows, conditions = deepcopy(measured)
    if fault == "missing_motion_reset":
        data["entity_resets"] = [e for e in data["entity_resets"]
                                 if not (e["source"] == "motion_resample" and e["step"] == 57)]
    elif fault == "entity_reset_time":
        data["entity_resets"][0]["physics_index"] += 1
    elif fault == "unselected_history":
        data["entity_resets"][0]["after"]["delay_0_count"][6] += 1
    elif fault == "uncleared_history":
        data["entity_resets"][0]["after"]["delay_0_peek"][2, 0] = 1
    elif fault == "early_success_score":
        rows[0]["error_body_pos_mean"] = str(float(rows[0]["error_body_pos_mean"]) + .1)
    elif fault == "failed_world_success":
        rows[2]["success"] = "1"
    elif fault == "injected_failure":
        data["steps"][0]["terms"]["fixture_injected_failure"][0] = True
    elif fault == "missing_final_step":
        data["steps"].pop()
    elif fault == "cross_reset_control":
        data["physics"][228]["ctrl"][0, 0] += .1
    with pytest.raises(ValueError):
        verify_lifecycle(data, rows, conditions, "delay_20ms")
