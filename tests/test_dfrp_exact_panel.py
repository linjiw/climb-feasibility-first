from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tools.run_dfrp_exact_panel import validate_selection
from tools.select_dfrp_exact_panel import select_panel

ROOT = Path(__file__).resolve().parents[1]
CENSUS = ROOT / "reports" / "dfrp_v0" / "census" / "manifest.json"


def test_frozen_exact_panel_is_deterministic_and_stratified() -> None:
    manifest = json.loads(CENSUS.read_text())
    first = select_panel(manifest, manifest_path=CENSUS)
    second = select_panel(manifest, manifest_path=CENSUS)

    assert first == second
    assert first["counts"] == {"flagged": 26, "controls": 4, "total": 30}
    assert len({row["name"] for row in first["clips"]}) == 30
    assert sum(row["stratum"] == "rare_le_2cm" for row in first["clips"]) == 2
    regular = [
        row
        for row in first["clips"]
        if row["role"] == "flagged_primary_candidate"
        and row["stratum"] != "rare_le_2cm"
    ]
    assert len({row["stratum"] for row in regular}) == 6
    assert all(
        sum(candidate["stratum"] == row["stratum"] for candidate in regular) == 4
        for row in regular
    )
    validate_selection(first)


def test_selection_payload_tamper_fails_closed() -> None:
    manifest = json.loads(CENSUS.read_text())
    selection = select_panel(manifest, manifest_path=CENSUS)
    tampered = copy.deepcopy(selection)
    tampered["clips"][0]["name"] = "different"
    with pytest.raises(ValueError, match="selection payload mismatch"):
        validate_selection(tampered)
