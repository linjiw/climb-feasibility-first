"""Configuration tests for explicit Phase-G sampler settings."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from climb.segment_env_cfg import segment_native_g1_tracking_env_cfg
from tools.climb_segment_train import _runner_cfg_from_env


def test_learning_progress_settings_reach_motion_command(tmp_path: Path) -> None:
    """The launcher-facing configuration must not fall back to failure rank."""
    manifest = tmp_path / "unit_table.json"
    manifest.write_text(json.dumps({"horizon_steps": 50}))

    cfg = segment_native_g1_tracking_env_cfg(
        motion_files=["dummy.npz"],
        segment_manifest=str(manifest),
        segment_sampling_mode="adaptive",
        sampler_seed=7,
        env_seed=7,
        segment_rank="learning_progress",
        segment_exploration_ratio=0.1,
        segment_difficulty_power=0.0,
        segment_progress_window=10,
        segment_progress_floor=0.01,
        max_unit_probability=0.05,
        max_clip_probability=0.25,
    )

    command = cfg.commands["motion"]
    assert command.segment_rank == "learning_progress"
    assert command.segment_difficulty_power == 0.0
    assert command.segment_progress_window == 10
    assert command.segment_progress_floor == 0.01
    assert command.max_unit_probability == 0.05
    assert command.max_clip_probability == 0.25
    assert cfg.seed == 7


def test_calibration_save_interval_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLIMB_SEGMENT_SEED", "20260903")
    monkeypatch.setenv("CLIMB_SEGMENT_SAVE_INTERVAL", "10")
    runner_cfg = _runner_cfg_from_env()
    assert runner_cfg.seed == 20260903
    assert runner_cfg.save_interval == 10


def test_nonpositive_save_interval_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLIMB_SEGMENT_SEED", "20260903")
    monkeypatch.setenv("CLIMB_SEGMENT_SAVE_INTERVAL", "0")
    with pytest.raises(SystemExit, match="must be positive"):
        _runner_cfg_from_env()


def test_missing_or_invalid_training_seed_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLIMB_SEGMENT_SEED", raising=False)
    with pytest.raises(SystemExit, match="explicitly"):
        _runner_cfg_from_env()
    monkeypatch.setenv("CLIMB_SEGMENT_SEED", "not-an-integer")
    with pytest.raises(SystemExit, match="must be an integer"):
        _runner_cfg_from_env()
