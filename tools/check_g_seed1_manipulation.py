#!/usr/bin/env python3
"""Apply the frozen Phase-G seed-1 manipulation gate without evaluator inputs.

The command accepts only the two training run directories, verifies every
scheduled sampler ledger and its checkpoint, binds the endpoint-blind
calibration files, and calls the Phase-G manipulation gate.  It cannot accept
an evaluator CSV, reward, survival, or tracking endpoint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from analyze_g_segment import (
    UNIT_TABLE_SHA256,
    exploratory_rank_agreement,
    manipulation_gate,
)

ROOT = Path(__file__).resolve().parents[1]
TRAINING_ENTRYPOINT = ROOT / "tools/climb_segment_train.py"
EXPECTED_ITERATIONS = (0, 500, 1000, 1500, 2000, 2500, 3000, 3500, 3999)


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of one artifact."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact(path: Path) -> dict[str, str]:
    """Create the hash record consumed by the frozen analyzer."""
    path = path.resolve()
    return {"path": str(path), "sha256": sha256_file(path)}


def collect_run(run_dir: Path, arm: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Verify one seed-1 training directory and collect ledger-only provenance."""
    run_dir = run_dir.resolve()
    if not run_dir.is_dir():
        raise ValueError(f"{arm}: missing run directory {run_dir}")
    expected_training_hash = sha256_file(TRAINING_ENTRYPOINT)
    ledger_records: list[dict[str, str]] = []
    checkpoints: dict[str, str] = {}
    for iteration in EXPECTED_ITERATIONS:
        ledger_path = run_dir / f"model_{iteration}_segment.json"
        checkpoint_path = run_dir / f"model_{iteration}.pt"
        if not ledger_path.is_file() or not checkpoint_path.is_file():
            raise ValueError(
                f"{arm}: iteration {iteration} lacks its ledger/checkpoint pair"
            )
        payload = json.loads(ledger_path.read_text())
        if int(payload.get("iteration", -1)) != iteration:
            raise ValueError(f"{arm}: ledger filename/iteration mismatch at {iteration}")
        if payload.get("classification") != "unsealed segment-v2 training telemetry":
            raise ValueError(f"{arm}: unexpected ledger classification at {iteration}")
        if payload.get("training_entrypoint_sha256") != expected_training_hash:
            raise ValueError(f"{arm}: training-entrypoint mismatch at {iteration}")
        checkpoint = payload.get("checkpoint")
        expected_checkpoint = artifact(checkpoint_path)
        if not isinstance(checkpoint, dict) or set(checkpoint) != {"path", "sha256"}:
            raise ValueError(f"{arm}: malformed checkpoint binding at {iteration}")
        if Path(checkpoint["path"]).resolve() != checkpoint_path.resolve():
            raise ValueError(f"{arm}: checkpoint path mismatch at {iteration}")
        if checkpoint["sha256"] != expected_checkpoint["sha256"]:
            raise ValueError(f"{arm}: checkpoint hash mismatch at {iteration}")
        ledger_records.append(artifact(ledger_path))
        checkpoints[str(iteration)] = expected_checkpoint["sha256"]

    discovered = {
        int(path.name.removeprefix("model_").removesuffix("_segment.json"))
        for path in run_dir.glob("model_*_segment.json")
        if path.name.removeprefix("model_").removesuffix("_segment.json").isdigit()
    }
    if discovered != set(EXPECTED_ITERATIONS):
        raise ValueError(
            f"{arm}: ledger iteration set {sorted(discovered)} differs from "
            f"{list(EXPECTED_ITERATIONS)}"
        )
    run = {"ledgers": ledger_records}
    provenance = {
        "run_dir": str(run_dir),
        "ledger_sha256": {
            str(record["path"]): record["sha256"] for record in ledger_records
        },
        "checkpoint_sha256": checkpoints,
    }
    return run, provenance


def evaluate(
    g1_run_dir: Path,
    g2_run_dir: Path,
    design_path: Path,
    calibration_result_path: Path,
) -> dict[str, Any]:
    """Return the seed-1 manipulation decision using sampler telemetry only."""
    design_path = design_path.resolve()
    calibration_result_path = calibration_result_path.resolve()
    g1, g1_provenance = collect_run(g1_run_dir, "G1")
    g2, g2_provenance = collect_run(g2_run_dir, "G2")
    manifest = {
        "calibration": {
            "design_path": str(design_path),
            "design_sha256": sha256_file(design_path),
            "result_path": str(calibration_result_path),
            "result_sha256": sha256_file(calibration_result_path),
        },
        "arms": {
            "G1": {"seeds": {"1": g1}},
            "G2": {"seeds": {"1": g2}},
        },
    }
    gate = manipulation_gate(manifest)
    return {
        "schema_version": "g_segment_seed1_manipulation/1",
        "classification": "measured sampler-only manipulation; no policy endpoint read",
        "status": "pass_for_evaluation" if gate["pass"] else "not_tested",
        "policy_endpoints_opened": False,
        "gate": gate,
        "exploratory_rank_agreement": exploratory_rank_agreement(manifest),
        "inputs": {
            "G1": g1_provenance,
            "G2": g2_provenance,
            "calibration_design_sha256": sha256_file(design_path),
            "calibration_result_sha256": sha256_file(calibration_result_path),
            "training_entrypoint_sha256": sha256_file(TRAINING_ENTRYPOINT),
            "gate_tool_sha256": sha256_file(Path(__file__).resolve()),
        },
    }


def _write_synthetic_run(
    run_dir: Path,
    *,
    arm: str,
    selected: dict[str, Any],
    design: dict[str, Any],
) -> None:
    run_dir.mkdir(parents=True)
    training_hash = sha256_file(TRAINING_ENTRYPOINT)
    for iteration in EXPECTED_ITERATIONS:
        checkpoint = run_dir / f"model_{iteration}.pt"
        checkpoint.write_bytes(f"{arm}:{iteration}".encode())
        segment = {
            "mode": "adaptive" if arm == "G2" else "uniform",
            "unit_table_sha256": UNIT_TABLE_SHA256,
            "sampler_seed": 1,
            "training_seed": 1,
            "rank": design["rank"],
            "progress_window": design["progress_window"],
            "difficulty_power": design["difficulty_power"],
            "exploration_ratio": selected["exploration_ratio"],
            "progress_floor": selected["progress_floor"],
            "max_unit_probability": design["max_unit_probability"],
            "max_clip_probability": design["max_clip_probability"],
            "adaptation_total_variation": 0.10 if arm == "G2" else 0.0,
            "entropy_effective_units": 100.0,
            "top1_probability": 0.01,
            "invalid_start_count": 0,
            "invalid_reference_frame_count": 0,
            "censored_resets": 0,
            "rank_saturation_fraction": 0.20,
            "conditional_success_rates": [0.2, 0.5, 0.8],
            "learning_progress": [0.1, 0.2, 0.05],
        }
        ledger = run_dir / f"model_{iteration}_segment.json"
        ledger.write_text(json.dumps({
            "iteration": iteration,
            "classification": "unsealed segment-v2 training telemetry",
            "checkpoint": artifact(checkpoint),
            "training_entrypoint_sha256": training_hash,
            "segment": segment,
        }, indent=1) + "\n")


def synthetic(out: Path) -> int:
    """Exercise the passing and seed-mismatch not-tested branches."""
    design_path = ROOT / "plan/G2_CALIBRATION_GRID.json"
    result_path = ROOT / "reports/g_segment/calibration/result.json"
    design = json.loads(design_path.read_text())
    result = json.loads(result_path.read_text())
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        g1_dir = temp / "G1"
        g2_dir = temp / "G2"
        _write_synthetic_run(
            g1_dir, arm="G1", selected=result["selected"], design=design
        )
        _write_synthetic_run(
            g2_dir, arm="G2", selected=result["selected"], design=design
        )
        passing = evaluate(g1_dir, g2_dir, design_path, result_path)
        bad_path = g2_dir / "model_1000_segment.json"
        bad = json.loads(bad_path.read_text())
        bad["segment"]["training_seed"] = 42
        bad_path.write_text(json.dumps(bad, indent=1) + "\n")
        rejected = evaluate(g1_dir, g2_dir, design_path, result_path)
    passed = (
        passing["status"] == "pass_for_evaluation"
        and passing["policy_endpoints_opened"] is False
        and rejected["status"] == "not_tested"
        and rejected["gate"]["G2"]["1"]["contract_mismatches"].get(
            "training_seed"
        )
        is not None
    )
    payload = {
        "synthetic": True,
        "pass": passed,
        "statuses": {
            "valid": passing["status"],
            "wrong_seed": rejected["status"],
        },
        "policy_endpoints_opened": False,
        "tool_sha256": sha256_file(Path(__file__).resolve()),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(f"Phase-G seed-1 manipulation synthetic: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--g1-run-dir", type=Path)
    parser.add_argument("--g2-run-dir", type=Path)
    parser.add_argument(
        "--calibration-design",
        type=Path,
        default=Path("plan/G2_CALIBRATION_GRID.json"),
    )
    parser.add_argument(
        "--calibration-result",
        type=Path,
        default=Path("reports/g_segment/calibration/result.json"),
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    if args.synthetic:
        return synthetic(args.out)
    if args.g1_run_dir is None or args.g2_run_dir is None:
        parser.error("--g1-run-dir and --g2-run-dir are required")
    result = evaluate(
        args.g1_run_dir,
        args.g2_run_dir,
        args.calibration_design,
        args.calibration_result,
    )
    serialized = json.dumps(result, indent=1) + "\n"
    if args.out.exists() and args.out.read_text() != serialized:
        raise ValueError(f"refusing to replace differing result {args.out}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(serialized)
    print(json.dumps({"status": result["status"], "policy_endpoints_opened": False}))
    return 0 if result["status"] == "pass_for_evaluation" else 2


if __name__ == "__main__":
    raise SystemExit(main())
