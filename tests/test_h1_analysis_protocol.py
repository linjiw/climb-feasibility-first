"""Check seed-level H1 inference and all-training-before-outcome ordering."""

from pathlib import Path
import sys

import numpy as np
import pytest

WORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK / "tools"))
import h1_analysis_protocol as protocol


def scores(shifts=(0, 0, 0)):
    values = {arm: np.full((3, 100), .5) for arm in protocol.ARMS}
    values["on"] += np.array(shifts)[:, None]
    return values


def analyze(values):
    return protocol.analyze_scores(values, np.arange(25), training_pass=True, provenance_pass=True)


def test_synthetic_decisions_and_seed_labels():
    result = protocol.synthetic()
    for name, case in result["cases"].items():
        assert case["status"] == name
        assert set(case["primary_on_minus_off"]["paired_seed_deltas"]) == {"61", "62", "63"}
        assert case["primary_on_minus_off"]["independent_units"] == 3
        assert case["primary_on_minus_off"]["df"] == 2


def test_t_interval_uses_three_seed_means():
    result = protocol.seed_interval(np.array([.01, .02, .03]))
    half_width = 4.302652729911275 * .01 / np.sqrt(3)
    assert result["seed_t_95ci"] == pytest.approx([.02 - half_width, .02 + half_width])


def test_preservation_is_not_improvement():
    result = analyze(scores())
    assert result["status"] == "preservation_only"
    assert result["preservation_pass"] and not result["improvement_pass"]


def test_all_panel_harm_blocks_hard_panel_gain():
    values = scores()
    values["on"][:, :25] += .04
    values["on"][:, 25:] -= .08
    result = analyze(values)
    assert result["primary_effect_pass"]
    assert not result["improvement_pass"] and not result["preservation_pass"]


def test_bootstrap_cannot_rescue_seed_uncertainty(monkeypatch):
    monkeypatch.setattr(protocol, "paired_bootstrap", lambda delta: [.05, .1])
    result = analyze(scores([.06, -.02, .04]))
    assert result["primary_on_minus_off"]["mean"] >= .02
    assert not result["improvement_pass"]


@pytest.mark.parametrize("fault", ["wrong_shape", "nan", "out_of_range", "extra_arm", "duplicate_hard"])
def test_invalid_scores_rejected(fault):
    values, hard = scores(), np.arange(25)
    if fault == "wrong_shape":
        values["on"] = np.full((100, 3), .5)
    elif fault == "nan":
        values["on"][0, 0] = np.nan
    elif fault == "out_of_range":
        values["off"][0, 0] = 1.1
    elif fault == "extra_arm":
        values["U"] = values["on"]
    else:
        hard[1] = hard[0]
    with pytest.raises(ValueError):
        protocol.analyze_scores(values, hard, training_pass=True, provenance_pass=True)


def test_failed_gates_do_not_inspect_outcome_arrays():
    assert protocol.analyze_scores(None, None, training_pass=True, provenance_pass=False)["status"] == "invalid"
    assert protocol.analyze_scores(None, None, training_pass=False, provenance_pass=True)["status"] == "not_tested"


def fake_verified_record(record, *, arm, seed):
    return {"status": "gate_training_pass", "admission": arm, "seed": seed, "smoke": False,
            "device": "cuda:0", "transitions": 49152000,
            "checkpoints": [{"iteration": i} for i in [*range(0, 4000, 100), 3999]]}


def test_all_six_training_verifiers_run_before_any_outcome():
    events = []
    records = {(arm, seed): object() for arm in protocol.ARMS for seed in protocol.SEEDS}

    def verifier(record, **identity):
        events.append("training")
        return fake_verified_record(record, **identity)

    def loader(*identity):
        assert events[:6] == ["training"] * 6
        events.append("outcome")
        return "SYNTHETIC"

    result = protocol.load_after_training(records, verifier, loader)
    assert len(result) == 24 and events == ["training"] * 6 + ["outcome"] * 24
    jobs = protocol.schedule()
    assert len(jobs) == 30 and all(j["stage"] == "train" for j in jobs[:6])
    assert [j["arm"] for j in jobs[:6]] == ["on", "off", "off", "on", "on", "off"]


@pytest.mark.parametrize("fault", ["missing_run", "late_failure", "smoke", "missing_checkpoint"])
def test_training_failure_prevents_all_outcome_callbacks(fault):
    records = {(arm, seed): object() for arm in protocol.ARMS for seed in protocol.SEEDS}
    if fault == "missing_run":
        records.pop(("off", 63))
    calls = []

    def verifier(record, **identity):
        result = fake_verified_record(record, **identity)
        if identity == {"arm": "off", "seed": 63}:
            if fault == "late_failure":
                raise ValueError("SYNTHETIC last source check failed")
            if fault == "smoke":
                result["smoke"] = True
            if fault == "missing_checkpoint":
                result["checkpoints"].pop(17)
        return result

    with pytest.raises(ValueError):
        protocol.load_after_training(records, verifier, lambda *args: calls.append(args))
    assert calls == []
