"""Reject broken H1 training links and incomplete paired evaluation grids."""

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

WORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK / "tools"))
from h1_evaluation_provenance import (
    PAIR_FIELDS, development, expectations, record, verify_cell, verify_pairing,
)
from eval_gate_development import verify_inputs
from eval_physics_development import sha256

RUN = WORK / "reports/gate_evaluator_environment_fixed_2026-09-06"


@pytest.fixture(scope="module")
def authentic():
    path = RUN / "design.json"
    design, training = verify_inputs(path, sha256(path))
    expected = expectations(design, training["on"], "on", 81, 19)
    cell = {"csv": record(RUN / "on/evaluation.csv"),
            "metadata": record(RUN / "on/evaluation.csv.meta.json"),
            "checkpoint": expected["checkpoint"], "ledger": expected["ledger"]}
    return cell, expected


def test_measured_development_round_trip():
    result = development(RUN)
    assert result["status"] == "h1_development_cell_provenance_pass"
    assert len(result["cells"]) == 2
    assert result["production_manifest_ingestion_enabled"] is False
    assert result["confirmation_endpoints_opened"] is False


@pytest.mark.parametrize("fault", ["missing_sources", "empty_sources", "extra_sources",
                                  "checkpoint_path", "conditions_path", "malformed_pair",
                                  "wrong_checkpoint_hash", "wrong_device"])
def test_metadata_corruption_rejected(authentic, tmp_path, fault):
    cell, expected = deepcopy(authentic)
    meta = json.loads(Path(cell["metadata"]["path"]).read_text())
    if fault == "missing_sources":
        meta["source_sha256"].pop(next(iter(meta["source_sha256"])))
    elif fault == "empty_sources":
        meta["source_sha256"] = {}
    elif fault == "extra_sources":
        meta["source_sha256"]["unknown.py"] = "0" * 64
    elif fault == "checkpoint_path":
        meta["checkpoint"] = str(tmp_path / "wrong.pt")
    elif fault == "conditions_path":
        meta["conditions"] = str(tmp_path / "wrong.json")
    elif fault == "malformed_pair":
        meta[PAIR_FIELDS[0]] = "not-a-hash"
    elif fault == "wrong_checkpoint_hash":
        meta["checkpoint_sha256"] = "0" * 64
    else:
        meta["device"] = "cuda:0"
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps(meta))
    cell["metadata"] = record(path)
    with pytest.raises(ValueError):
        verify_cell(cell, expected)


@pytest.mark.parametrize("link", ["checkpoint", "ledger"])
def test_bad_training_link_rejected_before_outcome_read(authentic, tmp_path, link):
    cell, expected = deepcopy(authentic)
    cell[link]["sha256"] = "0" * 64
    # Break shared references deliberately retained by deepcopy of the tuple.
    expected = deepcopy(authentic[1])
    cell["csv"]["path"] = str(tmp_path / "outcome-must-not-be-opened.csv")
    with pytest.raises(ValueError, match="not linked"):
        verify_cell(cell, expected)


def test_ledger_identity_rejected(authentic):
    cell, expected = deepcopy(authentic)
    expected["identity"]["seed"] = 82
    with pytest.raises(ValueError, match="ledger identity"):
        verify_cell(cell, expected)


def synthetic_grid():
    grid = {(a, s, i) for a in ("on", "off") for s in (61, 62, 63)
            for i in (1000, 2000, 3000, 3999)}
    cells = [{"arm": a, "seed": s, "iteration": i,
              "csv": f"/{a}_{s}_{i}.csv", "metadata": f"/{a}_{s}_{i}.json",
              **{field: "a" * 64 for field in PAIR_FIELDS}}
             for a, s, i in sorted(grid)]
    return cells, grid


def test_synthetic_complete_24_cell_grid():
    verify_pairing(*synthetic_grid())


@pytest.mark.parametrize("fault", ["missing", "duplicate", "reused_csv", "reused_metadata",
                                  "startup", "initial"])
def test_synthetic_incomplete_or_unpaired_grid_rejected(fault):
    cells, grid = synthetic_grid()
    if fault == "missing":
        cells.pop()
    elif fault == "duplicate":
        cells[-1] = deepcopy(cells[0])
    elif fault.startswith("reused_"):
        key = fault.removeprefix("reused_")
        cells[-1][key] = cells[0][key]
    else:
        cells[-1][PAIR_FIELDS[fault == "initial"]] = "b" * 64
    with pytest.raises(ValueError):
        verify_pairing(cells, grid)
