"""Protect temporal support and one-attempt continuity semantics."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from continuous_execution_support import access_offsets, legal_starts, permit_reset, verify_transition


def test_terminal_observation_is_included():
    assert access_offsets(2) == (0, 1, 2)
    assert list(legal_starts(0, 51, 50)) == [0]
    assert list(legal_starts(0, 50, 50)) == []


def test_lookahead_and_history_erode_both_boundaries():
    assert list(legal_starts(10, 20, 3, (-2, 4))) == [12]
    assert access_offsets(2, (3,)) == (0, 1, 2, 3, 4, 5)


def test_disconnected_intervals_cannot_be_spliced():
    assert not list(legal_starts(0, 80, 100))
    assert not list(legal_starts(90, 170, 100))


@pytest.mark.parametrize('horizon,offsets', [(0,(0,)), (1,()), (True,(0,)), (2,(0.5,))])
def test_invalid_footprint_rejected(horizon, offsets):
    with pytest.raises(ValueError):
        access_offsets(horizon, offsets)


def test_exact_active_step_and_unused_retired_world():
    verify_transition([10, 999], [11, 0], [True, False], [10, 0], [12, 4], 1)


@pytest.mark.parametrize('before,after,step', [(10,12,1), (10,0,1), (11,12,1), (11,12,2)])
def test_skip_wrap_drift_and_terminal_escape_rejected(before, after, step):
    with pytest.raises(ValueError, match='escaped support'):
        verify_transition([before], [after], [True], [10], [12], step)


def test_active_reset_rejected_and_retired_housekeeping_allowed():
    with pytest.raises(ValueError, match='scored attempt'):
        permit_reset([0], [True,False])
    permit_reset([1], [True,False])
