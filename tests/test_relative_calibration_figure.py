"""Figure ingestion must reproduce complete calibration evidence before plotting."""

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "paper/figures"))
import relative_calibration_comparison as figure

CALIBRATION = ROOT / "reports/relative_progress_2026-09-05/failure_calibration_gate_retry"


@pytest.fixture(scope="module")
def decision():
    path = CALIBRATION / "seed31_result.json"
    if not path.exists():
        pytest.skip("complete D development calibration not available")
    return path


def test_actual_full_D_decision_reproduces(decision):
    result = figure.read_result(decision, CALIBRATION / "design.json")
    assert result["status"] == "calibration_pass"
    assert result["post_warmup_snapshots"] == 37
    assert len(result["snapshots"]) == 41
    assert result["execution_cost"]["actual_launches"] == 1


def test_rehashed_summary_change_rejected(decision, tmp_path):
    result = json.loads(decision.read_text())
    result["gate"]["mean_tv"] += 0.01
    path = tmp_path / "SYNTHETIC_CORRUPTED_result.json"
    path.write_text(json.dumps(result))
    with pytest.raises(ValueError, match="does not reproduce"):
        figure.read_result(path, CALIBRATION / "design.json")


def test_missing_D_execution_design_rejected(decision):
    with pytest.raises(ValueError, match="fixed execution design"):
        figure.read_result(decision)


def test_duplicate_history_cannot_inflate_replication(tmp_path):
    row = {"arm": "D", "seed": 31}
    with pytest.raises(ValueError, match="empty or duplicate"):
        figure.generate([row, row], tmp_path / "absent")
    assert not (tmp_path / "absent").exists()
