"""Protect training-to-evaluation identity and on/off pairing in H1 development."""

import json
from pathlib import Path
import shutil
import sys

import pytest
import torch

WORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK / "tools"))
from analyze_gate_development import analyze
from eval_gate_development import verify_inputs
from eval_physics_development import sha256

RUN = WORK / "reports/gate_evaluator_environment_fixed_2026-09-06"


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


@pytest.fixture
def copied(tmp_path):
    run = tmp_path / "run"
    shutil.copytree(RUN, run)
    for arm in ("on", "off"):
        meta_path = run / arm / "evaluation.csv.meta.json"
        meta = json.loads(meta_path.read_text())
        meta["output"] = str(run / arm / "evaluation.csv")
        write(meta_path, meta)
        receipt_path = run / arm / "receipt.json"
        receipt = json.loads(receipt_path.read_text())
        receipt["artifacts"][meta_path.name] = sha256(meta_path)
        write(receipt_path, receipt)
    return run


def test_complete_measured_round_trip():
    result = analyze(RUN)
    assert result["status"] == "gate_development_evaluator_pass"
    assert result["episode_rows"] == 8
    assert result["arms"]["on"]["training_rejected_trials"] == 0
    assert result["arms"]["off"]["training_rejected_trials"] == 25
    assert result["confirmation_endpoints_opened"] is False


@pytest.mark.parametrize("fault", ["pairing", "checkpoint_metadata", "conditions", "actor_swap",
                                  "normalizer_mutation", "csv_hash", "receipt_arm"])
def test_corrupt_evaluation_rejected(copied, fault):
    cell = copied / "off"
    receipt_path = cell / "receipt.json"
    receipt = json.loads(receipt_path.read_text())
    if fault in ("pairing", "checkpoint_metadata", "conditions"):
        path = cell / "evaluation.csv.meta.json"
        data = json.loads(path.read_text())
        field = {"pairing": "initial_state_sha256", "checkpoint_metadata": "checkpoint_sha256",
                 "conditions": "conditions_sha256"}[fault]
        data[field] = "0" * 64
        write(path, data)
        receipt["artifacts"][path.name] = sha256(path)
    elif fault in ("actor_swap", "normalizer_mutation"):
        path = cell / "policy.pt"
        if fault == "actor_swap":
            shutil.copyfile(copied / "on/policy.pt", path)
        else:
            data = torch.load(path, weights_only=True)
            data["after"]["buffers"]["obs_normalizer.count"] += 1
            torch.save(data, path)
        receipt["artifacts"][path.name] = sha256(path)
    elif fault == "csv_hash":
        with (cell / "evaluation.csv").open("a") as handle:
            handle.write("corrupt\n")
    elif fault == "receipt_arm":
        receipt["admission"] = "on"
    write(receipt_path, receipt)
    with pytest.raises(ValueError):
        analyze(copied)


def test_full_evaluation_cannot_use_development_adapter(tmp_path):
    design = json.loads((RUN / "design.json").read_text())
    design["full_evaluation_enabled"] = True
    path = tmp_path / "design.json"
    write(path, design)
    with pytest.raises(ValueError, match="only the bound H1 CPU"):
        verify_inputs(path, sha256(path))
