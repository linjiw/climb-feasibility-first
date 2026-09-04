#!/usr/bin/env python3
"""Select a Phase-G ALP configuration using sampler telemetry only.

The finite candidate grid, seeds, ledger times, TV target, and safety gates live
in ``plan/G2_CALIBRATION_GRID.json``.  This tool refuses evaluator/checkpoint
inputs so policy endpoints cannot influence treatment-strength selection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import tempfile
from pathlib import Path
from typing import Any

import numpy as np


def sha256_file(path: Path) -> str:
    """Hash a calibration input without trusting its filename."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _exact_keys(value: dict[str, Any], allowed: set[str], label: str) -> None:
    extra = set(value) - allowed
    if extra:
        raise ValueError(f"{label}: undeclared keys are not allowed: {sorted(extra)}")


def load_runs(path: Path, design_sha256: str, stage: str) -> dict[str, list[str]]:
    """Load a ledger-only run map and reject endpoint-bearing schemas."""
    payload = json.loads(path.read_text())
    _exact_keys(payload, {"schema_version", "design_sha256", "stage", "runs"}, str(path))
    if payload.get("schema_version") != "g2_calibration_runs/1":
        raise ValueError(f"{path}: unsupported run-map schema")
    if payload.get("design_sha256") != design_sha256:
        raise ValueError(f"{path}: design hash mismatch")
    if payload.get("stage") != stage:
        raise ValueError(f"{path}: expected stage {stage!r}")
    if not isinstance(payload.get("runs"), dict):
        raise ValueError(f"{path}: runs must map candidate IDs to ledger lists")
    for candidate_id, entry in payload["runs"].items():
        _exact_keys(entry, {"ledgers"}, f"{path}:{candidate_id}")
        if not isinstance(entry.get("ledgers"), list):
            raise ValueError(f"{path}:{candidate_id}: ledgers must be a list")
    return {key: value["ledgers"] for key, value in payload["runs"].items()}


def assess(
    design: dict[str, Any],
    candidate: dict[str, Any],
    ledger_paths: list[str],
    *,
    expected_seed: int,
) -> dict[str, Any]:
    """Apply the frozen manipulation checks to one telemetry series."""
    required = {int(value) for value in design["required_ledger_iterations"]}
    by_iteration: dict[int, dict[str, Any]] = {}
    hashes: dict[str, str] = {}
    for raw_path in ledger_paths:
        path = Path(raw_path)
        payload = json.loads(path.read_text())
        iteration = int(payload["iteration"])
        segment = payload["segment"]
        if iteration in by_iteration:
            raise ValueError(f"{candidate['id']}: duplicate ledger iteration {iteration}")
        by_iteration[iteration] = segment
        hashes[str(path.resolve())] = sha256_file(path)
    missing = required - set(by_iteration)
    if missing:
        raise ValueError(f"{candidate['id']}: missing ledgers {sorted(missing)}")

    rows = [by_iteration[index] for index in sorted(required)]
    expected = {
        "unit_table_sha256": design["unit_table_sha256"],
        "sampler_seed": expected_seed,
        "training_seed": expected_seed,
        "rank": design["rank"],
        "progress_window": int(design["progress_window"]),
        "difficulty_power": float(design["difficulty_power"]),
        "exploration_ratio": float(candidate["exploration_ratio"]),
        "progress_floor": float(candidate["progress_floor"]),
        "max_unit_probability": float(design["max_unit_probability"]),
        "max_clip_probability": float(design["max_clip_probability"]),
    }
    for row in rows:
        for key, value in expected.items():
            actual = row.get(key)
            if isinstance(value, float):
                matches = actual is not None and math.isclose(
                    float(actual), value, rel_tol=0.0, abs_tol=1.0e-12
                )
            else:
                matches = actual == value
            if not matches:
                raise ValueError(
                    f"{candidate['id']}: telemetry {key}={actual!r}, expected {value!r}"
                )

    tv = np.array([float(row["adaptation_total_variation"]) for row in rows])
    entropy = np.array([float(row["entropy_effective_units"]) for row in rows])
    top1 = np.array([float(row["top1_probability"]) for row in rows])
    invalid = sum(
        int(row["invalid_start_count"])
        + int(row["invalid_reference_frame_count"])
        + int(row.get("censored_resets", 0))
        for row in rows
    )
    saturation = float(rows[-1]["rank_saturation_fraction"])
    band = design["tv_band"]
    outer = design["checkpoint_tv_outer_band"]
    passed = bool(
        band[0] <= tv.mean() <= band[1]
        and np.all((tv >= outer[0]) & (tv <= outer[1]))
        and entropy.min() >= float(design["min_entropy_effective_units"])
        and top1.max() <= float(design["max_top1_probability"]) + 1.0e-8
        and invalid == 0
        and math.isfinite(saturation)
        and saturation < float(design["max_saturation_fraction"])
    )
    return {
        "candidate": candidate,
        "iterations": sorted(required),
        "tv": tv.tolist(),
        "mean_tv": float(tv.mean()),
        "sd_tv": float(tv.std()),
        "min_entropy_effective_units": float(entropy.min()),
        "max_top1_probability": float(top1.max()),
        "invalid_or_censored": invalid,
        "final_saturation_fraction": saturation,
        "pass": passed,
        "ledger_sha256": hashes,
    }


def analyze(
    design_path: Path,
    screen_path: Path,
    validation_path: Path | None,
) -> dict[str, Any]:
    """Select once on the screen seed and optionally verify once on validation."""
    design = json.loads(design_path.read_text())
    design_hash = sha256_file(design_path)
    if design.get("schema_version") != "g2_calibration_design/1":
        raise ValueError("unsupported calibration design")
    candidates = design["candidates"]
    if len({row["id"] for row in candidates}) != len(candidates):
        raise ValueError("candidate IDs must be unique")
    screen_runs = load_runs(screen_path, design_hash, "screen")
    if set(screen_runs) != {row["id"] for row in candidates}:
        raise ValueError("screen run map must contain every candidate exactly once")
    screen = [
        assess(
            design,
            row,
            screen_runs[row["id"]],
            expected_seed=int(design["screen_seed"]),
        )
        for row in candidates
    ]
    eligible = [row for row in screen if row["pass"]]
    result: dict[str, Any] = {
        "schema_version": "g2_calibration_result/1",
        "classification": "pending; manipulation only; no policy endpoint read",
        "design_sha256": design_hash,
        "screen_runs_sha256": sha256_file(screen_path),
        "screen": screen,
    }
    if not eligible:
        result.update(status="no_candidate_passed", selected=None)
        return result
    order = {row["id"]: index for index, row in enumerate(candidates)}
    selected = min(
        eligible,
        key=lambda row: (
            abs(row["mean_tv"] - float(design["tv_target"])),
            row["sd_tv"],
            order[row["candidate"]["id"]],
        ),
    )
    result["selected"] = selected["candidate"]
    if validation_path is None:
        result["status"] = "selected_pending_independent_validation"
        return result
    validation_runs = load_runs(validation_path, design_hash, "validation")
    if set(validation_runs) != {selected["candidate"]["id"]}:
        raise ValueError("validation map must contain only the selected candidate")
    validation = assess(
        design,
        selected["candidate"],
        validation_runs[selected["candidate"]["id"]],
        expected_seed=int(design["validation_seed"]),
    )
    result["validation_runs_sha256"] = sha256_file(validation_path)
    result["validation"] = validation
    result["status"] = "ready_to_freeze" if validation["pass"] else "validation_failed"
    return result


def synthetic(out: Path) -> int:
    """Exercise selection, validation, and endpoint-schema refusal."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        design = {
            "schema_version": "g2_calibration_design/1",
            "unit_table_sha256": "unit-hash",
            "screen_seed": 1,
            "validation_seed": 2,
            "rank": "learning_progress",
            "progress_window": 10,
            "difficulty_power": 0.0,
            "required_ledger_iterations": [30, 40, 49],
            "tv_band": [0.05, 0.15],
            "tv_target": 0.10,
            "checkpoint_tv_outer_band": [0.025, 0.20],
            "min_entropy_effective_units": 12.0,
            "max_top1_probability": 0.05,
            "max_saturation_fraction": 0.90,
            "max_unit_probability": 0.05,
            "max_clip_probability": 0.25,
            "candidates": [
                {"id": "weak", "exploration_ratio": 0.4, "progress_floor": 0.05},
                {"id": "target", "exploration_ratio": 0.1, "progress_floor": 0.01},
            ],
        }
        design_path = root / "design.json"
        design_path.write_text(json.dumps(design))
        design_hash = sha256_file(design_path)

        def ledgers(candidate: dict[str, Any], values: list[float], prefix: str) -> list[str]:
            paths = []
            seed = design["screen_seed"] if prefix == "s" else design["validation_seed"]
            for iteration, tv in zip((30, 40, 49), values, strict=True):
                path = root / f"{prefix}_{candidate['id']}_{iteration}.json"
                path.write_text(json.dumps({
                    "iteration": iteration,
                    "segment": {
                        "unit_table_sha256": "unit-hash",
                        "sampler_seed": seed,
                        "training_seed": seed,
                        "rank": "learning_progress",
                        "progress_window": 10,
                        "difficulty_power": 0.0,
                        "exploration_ratio": candidate["exploration_ratio"],
                        "progress_floor": candidate["progress_floor"],
                        "max_unit_probability": 0.05,
                        "max_clip_probability": 0.25,
                        "adaptation_total_variation": tv,
                        "entropy_effective_units": 30.0,
                        "top1_probability": 0.04,
                        "invalid_start_count": 0,
                        "invalid_reference_frame_count": 0,
                        "censored_resets": 0,
                        "rank_saturation_fraction": 0.4,
                    },
                }))
                paths.append(str(path))
            return paths

        screen = root / "screen.json"
        screen.write_text(json.dumps({
            "schema_version": "g2_calibration_runs/1",
            "design_sha256": design_hash,
            "stage": "screen",
            "runs": {
                "weak": {"ledgers": ledgers(design["candidates"][0], [0.02] * 3, "s")},
                "target": {"ledgers": ledgers(design["candidates"][1], [0.09, 0.10, 0.11], "s")},
            },
        }))
        validation = root / "validation.json"
        validation.write_text(json.dumps({
            "schema_version": "g2_calibration_runs/1",
            "design_sha256": design_hash,
            "stage": "validation",
            "runs": {
                "target": {
                    "ledgers": ledgers(
                        design["candidates"][1], [0.08, 0.10, 0.12], "v"
                    )
                },
            },
        }))
        result = analyze(design_path, screen, validation)
        endpoint_map = root / "screen_with_endpoint.json"
        endpoint_payload = json.loads(screen.read_text())
        endpoint_payload["checkpoint"] = "forbidden.pt"
        endpoint_map.write_text(json.dumps(endpoint_payload))
        try:
            load_runs(endpoint_map, design_hash, "screen")
        except ValueError:
            endpoint_refused = True
        else:
            endpoint_refused = False

        validation_payload = json.loads(validation.read_text())
        validation_ledger = Path(
            validation_payload["runs"]["target"]["ledgers"][0]
        )
        wrong_seed_payload = json.loads(validation_ledger.read_text())
        wrong_seed_payload["segment"]["training_seed"] = 42
        wrong_seed_ledger = root / "wrong_seed.json"
        wrong_seed_ledger.write_text(json.dumps(wrong_seed_payload))
        wrong_seed_paths = list(
            validation_payload["runs"]["target"]["ledgers"]
        )
        wrong_seed_paths[0] = str(wrong_seed_ledger)
        try:
            assess(
                design,
                design["candidates"][1],
                wrong_seed_paths,
                expected_seed=design["validation_seed"],
            )
        except ValueError:
            wrong_seed_refused = True
        else:
            wrong_seed_refused = False
    passed = (
        result["status"] == "ready_to_freeze"
        and result["selected"]["id"] == "target"
        and endpoint_refused
        and wrong_seed_refused
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "status": result["status"],
        "selected": result["selected"],
        "screen_pass": {
            row["candidate"]["id"]: row["pass"] for row in result["screen"]
        },
        "validation_pass": result["validation"]["pass"],
        "endpoint_schema_refused": endpoint_refused,
        "wrong_seed_refused": wrong_seed_refused,
    }
    out.write_text(
        json.dumps(
            {
                "synthetic": True,
                "pass": passed,
                "summary": summary,
                "analyzer_sha256": sha256_file(Path(__file__).resolve()),
            },
            indent=1,
        )
        + "\n"
    )
    print(f"G2 treatment calibration synthetic: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", type=Path, default=Path("plan/G2_CALIBRATION_GRID.json"))
    parser.add_argument("--screen-runs", type=Path)
    parser.add_argument("--validation-runs", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    if args.synthetic:
        return synthetic(args.out)
    if args.screen_runs is None:
        parser.error("--screen-runs is required without --synthetic")
    result = analyze(args.design, args.screen_runs, args.validation_runs)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({"status": result["status"], "selected": result["selected"]}))
    return 0 if result["status"] == "ready_to_freeze" else 2


if __name__ == "__main__":
    raise SystemExit(main())
