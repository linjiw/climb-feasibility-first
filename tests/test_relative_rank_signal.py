"""Signed change accounting must not confuse absolute progress with improvement."""

from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from analyze_relative_rank_signal import describe_history


def test_extra_mass_partitions_improvement_decline_and_zero():
    history = np.full((11, 3), 0.5)
    history[-1] = [0.6, 0.3, 0.5]
    row = describe_history(history, np.array([0.4, 0.5, 0.1]), np.full(3, 1 / 3))
    assert row["excess_fraction_declining"] == pytest.approx(5 / 7)
    assert row["excess_fraction_improving"] == pytest.approx(2 / 7)
    assert row["excess_fraction_unchanged"] == 0


def test_no_extra_mass_has_no_directional_fraction():
    row = describe_history(np.full((11, 3), 0.5), np.full(3, 1 / 3), np.full(3, 1 / 3))
    assert row["positive_excess_mass"] == 0
    assert row["excess_fraction_declining"] is None


def test_bad_rate_history_rejected():
    with pytest.raises(ValueError):
        describe_history(np.full((11, 3), np.nan), np.full(3, 1 / 3), np.full(3, 1 / 3))
