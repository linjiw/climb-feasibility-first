"""Exact segment-reducer invariants used by the v2 runtime."""

from __future__ import annotations

import numpy as np
import pytest

from tools.screen_segments import dilate


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
