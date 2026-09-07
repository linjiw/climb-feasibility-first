"""Rebuilding conditions detects changed starts, identities and motion timelines."""

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from check_relative_inputs import verify_conditions


@pytest.fixture
def conditions():
    return json.loads((ROOT / "reports/g_segment/eval_conditions.json").read_text())


def test_fixed_condition_manifest_reconstructs(conditions):
    verify_conditions(conditions, conditions["motions"])


@pytest.mark.parametrize("field,value", [("world_id", 99), ("start_frame", 1),
                                         ("replicate", 1), ("full_window", False),
                                         ("condition_id", "forged")])
def test_rehashed_condition_edits_do_not_reconstruct(conditions, field, value):
    conditions["conditions"][0][field] = value
    with pytest.raises(ValueError, match="reconstruct"):
        verify_conditions(conditions, conditions["motions"])


def test_current_motion_header_must_match_saved_timeline(conditions):
    metadata = deepcopy(conditions["motions"])
    metadata[0]["frames"] += 1
    with pytest.raises(ValueError, match="reconstruct"):
        verify_conditions(conditions, metadata)
