"""Exact segment-reducer invariants used by the v2 runtime."""

from __future__ import annotations

import numpy as np
import pytest

from tools.screen_segments import dilate, reduce_clip


def test_backward_guard_excludes_only_preceding_lookahead_frames() -> None:
    severe = np.zeros(7, dtype=bool)
    severe[3] = True
    np.testing.assert_array_equal(
        dilate(severe, 1, mode="backward"),
        np.array([False, False, True, True, False, False, False]),
    )
    np.testing.assert_array_equal(
        dilate(severe, 1, mode="symmetric"),
        np.array([False, False, True, True, True, False, False]),
    )


def test_unknown_guard_mode_fails_closed() -> None:
    with pytest.raises(ValueError, match="guard mode"):
        dilate(np.array([False, True]), 1, mode="future")


def test_excluded_windows_include_dropped_short_feasible_islands() -> None:
    frames = []
    for index in range(10):
        unsupported = 100.0 if index < 3 or index >= 6 else 0.0
        frames.append(
            {
                "t": index / 10.0,
                "n_contacts": 1,
                "real": {
                    "unsupported_force_N": unsupported,
                    "tl_unsupported_force_N": unsupported,
                },
            }
        )
    result = reduce_clip(
        {
            "clip": "short_island",
            "fps": 10.0,
            "gap": 0.06,
            "total_mass_kg": 10.0,
            "frames": frames,
        },
        guard_s=0.0,
        min_seg_s=1.0,
        bin_frames=5,
        min_bin_frac=1.0,
        severity="severe",
    )
    assert result["guarded_severe_windows_frames"] == [[0, 3], [6, 10]]
    assert result["feasible_segments_frames"] == []
    assert result["excluded_windows_frames"] == [[0, 10]]
