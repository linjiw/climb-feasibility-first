"""Reject incomplete and corrupted manipulation evidence before promotion."""

import json
from pathlib import Path
import sys

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_relative_progress_probe import check_run, sha256
from climb.relative_progress import PROTOCOL, RelativeProgressSampler

MANIFEST = ROOT / "reports/g_segment/unit_table.json"


@pytest.fixture
def smoke(tmp_path):
    sampler = RelativeProgressSampler(
        MANIFEST, mode="adaptive", seed=11, rank="learning_progress",
        difficulty_power=0.0, exploration_ratio=0.4, progress_window=10,
        progress_floor=0.0, relative_factor=2.0,
        max_unit_probability=0.05, max_clip_probability=0.25,
    )
    for iteration in (0, 19):
        checkpoint = tmp_path / f"model_{iteration}.pt"
        checkpoint.write_bytes(b"fixture checkpoint")
        torch.save({"iteration": iteration, "sampler": sampler.state_dict()},
                   tmp_path / f"model_{iteration}_segment_sampler.pt")
        segment = {
            "allocation_protocol": PROTOCOL, "relative_progress_factor": 2.0,
            "sampler_seed": 11, "training_seed": 11, "horizon_steps": 50,
            "mode": "adaptive", "rank": "learning_progress", "exploration_ratio": 0.4,
            "difficulty_power": 0.0, "progress_window": 10, "progress_floor": 0.0,
            "max_unit_probability": 0.05, "max_clip_probability": 0.25,
            "unit_table_sha256": sampler.manifest["unit_table_sha256"],
            "probabilities": sampler.probabilities.tolist(), "completed_trials": 1,
            "rank_saturation_fraction": 0.0, "censored_resets": 0,
            "invalid_start_count": 0, "invalid_reference_frame_count": 0,
        }
        sources = {name: sha256(ROOT / name) for name in (
            "tools/train_relative_progress_probe.py", "climb/relative_progress.py",
            "climb/segment_runtime.py", "climb/segment_curriculum.py",
            "climb/segment_command.py", "climb/segment_env_cfg.py",
        )}
        ledger = {"iteration": iteration, "num_envs": 8, "segment": segment,
                  "source_hashes_at_launch": sources,
                  "checkpoint": {"path": str(checkpoint), "sha256": sha256(checkpoint)}}
        (tmp_path / f"model_{iteration}_segment.json").write_text(json.dumps(ledger))
    return tmp_path


def test_complete_smoke_passes_and_is_reproducible(smoke):
    first = check_run(smoke, MANIFEST, seed=11, stage="smoke")
    assert first["status"] == "smoke_pass"
    assert first == check_run(smoke, MANIFEST, seed=11, stage="smoke")


def test_missing_final_cannot_pass(smoke):
    (smoke / "model_19_segment.json").unlink()
    with pytest.raises(ValueError, match="missing"):
        check_run(smoke, MANIFEST, seed=11, stage="smoke")


@pytest.mark.parametrize("corruption", ["seed", "source", "probabilities", "invalid", "nan"])
def test_corrupt_ledger_cannot_pass(smoke, corruption):
    path = smoke / "model_19_segment.json"
    ledger = json.loads(path.read_text())
    if corruption == "seed":
        ledger["segment"]["training_seed"] = 12
    elif corruption == "source":
        ledger["source_hashes_at_launch"] = {}
    elif corruption == "probabilities":
        ledger["segment"]["probabilities"][0] += 0.01
    elif corruption == "invalid":
        ledger["segment"]["invalid_start_count"] = 1
    else:
        ledger["segment"]["rank_saturation_fraction"] = float("nan")
    path.write_text(json.dumps(ledger))
    with pytest.raises(ValueError):
        check_run(smoke, MANIFEST, seed=11, stage="smoke")


def test_corrupt_checkpoint_cannot_pass(smoke):
    (smoke / "model_19.pt").write_bytes(b"replaced")
    with pytest.raises(ValueError, match="checkpoint"):
        check_run(smoke, MANIFEST, seed=11, stage="smoke")


def test_sampler_contract_cannot_be_substituted(smoke):
    path = smoke / "model_19_segment_sampler.pt"
    state = torch.load(path, weights_only=True)
    state["sampler"]["relative_progress"]["factor"] = 1
    torch.save(state, path)
    with pytest.raises(ValueError, match="resume contract"):
        check_run(smoke, MANIFEST, seed=11, stage="smoke")


def test_short_run_cannot_be_used_as_long_evidence(smoke):
    with pytest.raises(ValueError, match="missing"):
        check_run(smoke, MANIFEST, seed=11, stage="long")
