"""Audit actual policy rollout traces and reject broken pairing/interventions."""

from copy import deepcopy
from pathlib import Path
import sys

import pytest
import torch

WORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK / "tools"))
from analyze_physics_development import analyze, verify_trace

RUN = WORK / "reports/physics_evaluator_development_2026-09-06"


@pytest.fixture(scope="module")
def baseline():
    return torch.load(RUN / "unchanged/instrumentation.pt", map_location="cpu", weights_only=True)


def test_complete_measured_lifecycle():
    result = analyze(RUN)
    assert result["status"] == "development_evaluator_lifecycle_pass"
    assert result["episode_rows"] == 36
    assert result["confirmation_endpoints_opened"] is False
    assert result["full_evaluation_enabled"] is False


@pytest.mark.parametrize("fault", ["startup", "initial", "observation", "action", "delay", "force", "friction", "missing"])
def test_corrupted_policy_telemetry_rejected(baseline, fault):
    data = deepcopy(baseline)
    if fault == "startup":
        data["startup_before_intervention"]["encoder_bias"][0, 0] += 0.01
    elif fault == "initial":
        data["initial_state"]["qpos"][0, 0] += 0.01
    elif fault == "observation":
        key = next(iter(data["first_observation"]))
        data["first_observation"][key][0, 0] += 0.01
    elif fault == "action":
        data["first_action"][0, 0] += 0.01
    elif fault == "delay":
        data["physics"][3]["ctrl"][0, 0] += 0.01
    elif fault == "force":
        data["physics"][3]["force"][0, 0] = 999
    elif fault == "friction":
        data["friction_after_intervention"][0, 0, 1] += 0.01
    elif fault == "missing":
        data["physics"].pop()
    with pytest.raises(ValueError):
        verify_trace("unchanged", data, baseline)
