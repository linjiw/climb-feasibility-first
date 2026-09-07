"""Real preflight through aggregation on a complete, explicitly synthetic campaign."""

import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import analyze_relative_campaign as campaign
from relative_campaign_fixture import build_campaign, record


@pytest.fixture(scope="module")
def full_campaign(tmp_path_factory):
    return build_campaign(tmp_path_factory.mktemp("SYNTHETIC_campaign"))


def test_complete_preflight_and_aggregation_without_gate_stubs(full_campaign):
    result = campaign.analyze(full_campaign)
    assert result["status"] == "positive", result
    assert result["primary_R_minus_U"]["mean"] == pytest.approx(0.04)
    assert len(result["manipulation"]) == 12
    assert all(len(row["snapshots"]) == 41 for row in result["manipulation"].values())
    assert result["quality_and_work_descriptive"]["R_minus_U"]["21"]["common_successes"] == 2800
    assert result["training_cost_descriptive"]["total_elapsed_gpu_hours"] == pytest.approx(0.12)


def test_last_cell_mismatch_stops_before_any_endpoint_aggregation(full_campaign, monkeypatch):
    manifest = json.loads(full_campaign.read_text())
    cell = manifest["arms"]["U"]["23"]["evaluations"]["3999"]
    original_path = Path(cell["metadata"]["path"])
    changed = json.loads(original_path.read_text())
    changed["initial_state_sha256"] = "c" * 64
    path = full_campaign.parent / "corrupted_last_cell.meta.json"
    path.write_text(json.dumps(changed))
    cell["metadata"] = record(path)
    bad_manifest = full_campaign.parent / "corrupted_manifest.json"
    bad_manifest.write_text(json.dumps(manifest))
    def unexpected(*args, **kwargs):
        pytest.fail("opened endpoint aggregation before complete pairing gate")
    monkeypatch.setattr(campaign, "aggregate_rows", unexpected)
    result = campaign.analyze(bad_manifest)
    assert result["status"] == "invalid"
    assert result["policy_endpoints_opened"] is False
    assert "pairing mismatch" in result["reason"]
