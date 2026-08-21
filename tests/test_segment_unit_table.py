"""Fail-closed exact segment unit-table tests."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tools.build_segment_unit_table import build_manifest


def write_motion(path: Path, frames: int) -> None:
    """Write the minimal timeline fields inspected by the builder."""
    np.savez(path, joint_pos=np.zeros((frames, 1)), fps=np.array([50.0]))


def write_sidecar(
    path: Path,
    name: str,
    frames: int,
    feasible: list[list[int]],
    severe: list[list[int]],
) -> None:
    """Write an exact-v2 reducer sidecar."""
    records = [
        {
            "start_frame": start,
            "stop_frame": stop,
            "unsupported_ratio_mean": 0.1,
            "unsupported_ratio_p95": 0.2,
            "unsupported_ratio_max": 0.3,
        }
        for start, stop in feasible
    ]
    path.write_text(
        json.dumps(
            {
                "clip": name,
                "frames": frames,
                "fps": 50.0,
                "guard_s": 0.0,
                "guard_mode": "symmetric",
                "severity": "severe",
                "source_screen_sha256": "a" * 64,
                "reducer_sha256": "b" * 64,
                "feasible_segments_frames": feasible,
                "feasible_segment_records": records,
                "guarded_severe_windows_frames": severe,
            }
        )
    )


def test_builder_preserves_source_unit_ids_across_short_filtering(
    tmp_path: Path,
) -> None:
    clips = tmp_path / "clips.txt"
    bank = tmp_path / "bank"
    sidecars = tmp_path / "sidecars"
    bank.mkdir()
    sidecars.mkdir()
    clips.write_text("alpha\nbeta\n")
    write_motion(bank / "alpha.npz", 10)
    write_motion(bank / "beta.npz", 8)
    write_sidecar(
        sidecars / "alpha.json", "alpha", 10, [[0, 3], [5, 10]], [[3, 5]]
    )
    write_sidecar(sidecars / "beta.json", "beta", 8, [[0, 8]], [])

    manifest = build_manifest(clips, bank, sidecars, horizon_steps=3)
    assert manifest["counts"] == {
        "clips": 2,
        "source_units": 3,
        "admissible_units": 2,
        "discarded_short_units": 1,
        "legal_starts": 7,
    }
    assert [unit["unit_id"] for unit in manifest["admissible_units"]] == [1, 2]
    assert [unit["table_index"] for unit in manifest["admissible_units"]] == [0, 1]


def test_builder_fails_closed_when_any_sidecar_is_missing(tmp_path: Path) -> None:
    clips = tmp_path / "clips.txt"
    bank = tmp_path / "bank"
    sidecars = tmp_path / "sidecars"
    bank.mkdir()
    sidecars.mkdir()
    clips.write_text("alpha\n")
    write_motion(bank / "alpha.npz", 10)
    with pytest.raises(FileNotFoundError, match="fail closed"):
        build_manifest(clips, bank, sidecars, horizon_steps=3)
