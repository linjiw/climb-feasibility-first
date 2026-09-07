"""Freeze prospective arm/seed identity and prevent accidental confirmation."""

import os
from pathlib import Path
import sys

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from train_relative_policy import config, profile
from climb.relative_progress import RelativeProgressCommandCfg, relative_weights


@pytest.mark.parametrize("arm", ("U", "A", "R", "D"))
def test_profile_builds_expected_command(arm, monkeypatch):
    for key, value in {"CLIMB_BANK": ROOT / "bank/amass", "CLIMB_CLIPS": ROOT / "bank/tiers/tier_800.txt",
                       "CLIMB_SEGMENT_MANIFEST": ROOT / "reports/g_segment/unit_table.json"}.items():
        monkeypatch.setenv(key, str(value))
    _, selected = profile(arm, "smoke", 41)
    cfg = config(arm, "smoke", 41)
    command = cfg.commands["motion"]
    assert command.sampler_seed == 41
    assert cfg.seed == 41
    assert command.segment_sampling_mode == selected["mode"]
    assert command.segment_exploration_ratio == selected["exploration_ratio"]
    assert command.segment_rank == selected["rank"]
    assert isinstance(command, RelativeProgressCommandCfg) == (arm == "R")


@pytest.mark.parametrize("arm,stage,seed", [("R", "confirmation", 21), ("D", "smoke", 11),
                                           ("R", "calibration", 31), ("D", "calibration", 21)])
def test_unapproved_profile_combination_is_rejected(arm, stage, seed):
    with pytest.raises(ValueError):
        profile(arm, stage, seed)


def test_effective_mixture_identity_before_caps():
    b = torch.tensor([0.2, 0.3, 0.5], dtype=torch.float64)
    signal = torch.tensor([0.01, 0.4, 0.1], dtype=torch.float64)
    weight = relative_weights(signal, b, 2.0)
    relative = 0.4 * b + 0.6 * b * weight / (b * weight).sum()
    effective = 0.8 * b + 0.2 * b * signal / (b * signal).sum()
    torch.testing.assert_close(relative, effective)
