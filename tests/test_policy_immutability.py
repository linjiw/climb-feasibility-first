"""Reject changed weights/statistics and incomplete inference coverage."""

from copy import deepcopy
from pathlib import Path
import sys

import pytest
import torch

WORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK / "tools"))
from audit_policy_immutability import verify_payload


@pytest.fixture(scope="module")
def trace():
    return torch.load(WORK / "reports/policy_immutability_2026-09-06/original/policy_immutability.pt",
                      map_location="cpu", weights_only=True)


def test_measured_policy_immutability(trace):
    result = verify_payload(trace)
    assert result["tensor_counts"] == {"parameters": 9, "buffers": 4}
    assert "obs_normalizer.count" in result["normalizer_buffers"]


@pytest.mark.parametrize("fault", ["weight", "statistic", "count", "mode", "interim_mode",
                                  "missing_forward", "missing_buffer", "nonfinite"])
def test_corrupted_immutability_rejected(trace, fault):
    data = deepcopy(trace)
    if fault == "weight":
        next(iter(data["after"]["parameters"].values())).view(-1)[0] += 1
    elif fault == "statistic":
        data["after"]["buffers"]["obs_normalizer._mean"].view(-1)[0] += 1
    elif fault == "count":
        data["after"]["buffers"]["obs_normalizer.count"] += 1
    elif fault == "mode":
        data["after"]["training"][""] = True
    elif fault == "interim_mode":
        data["training_mode_observed"] = True
    elif fault == "missing_forward":
        data["forward_calls"] -= 1
    elif fault == "missing_buffer":
        data["after"]["buffers"].pop("obs_normalizer.count")
    elif fault == "nonfinite":
        next(iter(data["after"]["parameters"].values())).view(-1)[0] = float("nan")
    with pytest.raises(ValueError):
        verify_payload(data)
