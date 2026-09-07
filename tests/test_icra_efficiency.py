"""Guard sparse-grid interpretation and unopened campaign endpoints."""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

PATH = Path(__file__).resolve().parents[1] / "tools/analyze_icra_efficiency.py"
SPEC = importlib.util.spec_from_file_location("efficiency", PATH)
eff = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(eff)


def test_exact_half_budget_and_primary_status():
    result = eff.synthetic()
    record = result["panels"]["feasible_hard"]["paired_U_final_target"]["21"]["arms"]["R"]
    assert record["budget_fraction"] == 2001 / 4000
    assert result["original_primary_status"] == "inconclusive"
    assert result["training_transitions"][-1] == 49_152_000


def test_transient_crossing_is_not_sustained():
    result = eff.attainment(np.array([0.8, 0.3, 0.6, 0.7]), 0.6)
    assert result["iteration"] == 3000


def test_missing_attainment_has_no_finite_ratio():
    result = eff.attainment(np.array([0.3, 0.4, 0.5, 0.59]), 0.6)
    assert result["transitions"] is None
    assert result["budget_fraction"] is None


def test_first_observation_is_labelled():
    assert eff.attainment(np.ones(4), 0.6)["status"] == "attained_at_first_observation"


@pytest.mark.parametrize("status", ["pending", "invalid", "not_tested", "execution_stopped"])
def test_invalid_campaign_cannot_be_promoted(status):
    with pytest.raises(ValueError):
        eff.summarize({"status": status, "policy_endpoints_opened": True})


def test_pending_and_stopped_campaign_do_not_read_endpoints(tmp_path):
    freeze = tmp_path / "reports/relative_progress_2026-09-05/confirmation_freeze"
    campaign = freeze / "campaign"
    campaign.mkdir(parents=True)
    contract = freeze / "contract.json"
    contract.write_text(json.dumps({"status": "frozen_before_confirmation"}))
    # Deliberately unreadable as JSON: neither branch may access this endpoint.
    (campaign / "analysis.json").write_text("unopened")
    assert eff.analyze_campaign(tmp_path, eff.sha256(contract))["status"] == "pending"
    (campaign / "terminal_status.json").write_text('{"status":"execution_stopped"}')
    result = eff.analyze_campaign(tmp_path, eff.sha256(contract))
    assert result["status"] == "unavailable"
    assert result["policy_endpoints_opened"] is False


def test_trapezoidal_area_has_analytic_value():
    curves = {str(i): {a: {f"{p}_per_seed": [0.2 + 0.4 * (i - 1000) / 2999] * 3
                          for p in ("feasible_hard", "all_panel")}
                      for a in eff.ARMS} for i in eff.ITERATIONS}
    result = eff.summarize({"status": "inconclusive", "policy_endpoints_opened": True,
                            "learning_curves_descriptive": curves})
    np.testing.assert_allclose(result["panels"]["all_panel"]["normalized_AULC_per_seed"]["U"], 0.4)


def test_original_aulc_disagreement_rejected():
    curves = {str(i): {a: {f"{p}_per_seed": [0.5] * 3 for p in ("feasible_hard", "all_panel")}
                      for a in eff.ARMS} for i in eff.ITERATIONS}
    with pytest.raises(ValueError, match="AULC disagree"):
        eff.summarize({"status": "inconclusive", "policy_endpoints_opened": True,
                      "learning_curves_descriptive": curves,
                      "AULC_R_minus_U_descriptive": {"paired_seed_deltas": {str(s): 0.1 for s in eff.SEEDS}}})


@pytest.mark.parametrize("value", [float("nan"), -0.1, 1.1])
def test_bad_scores_rejected(value):
    curves = {str(i): {a: {f"{p}_per_seed": [value] * 3 for p in ("feasible_hard", "all_panel")}
                      for a in eff.ARMS} for i in eff.ITERATIONS}
    with pytest.raises(ValueError):
        eff.summarize({"status": "inconclusive", "policy_endpoints_opened": True,
                      "learning_curves_descriptive": curves})
