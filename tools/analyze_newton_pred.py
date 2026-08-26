#!/usr/bin/env python3
"""Analyze the sealed Newton 1.5 no-training predictive gate.

The real-data contract is defined in ``plan/PREREGISTRATION_NEWTON_PRED.md``.
``--synthetic`` exercises passing, null, and replication-discordant branches
without opening policy or solver outcomes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

AXES = ("delay_20ms", "motor_clamp_85pct", "newton_contact")
HELDOUT_POLICIES = ("adaptive", "grounded")
CONTROL_COLUMNS = (
    "clip_infeasible_frac",
    "root_linear_speed_rms_mps",
    "root_angular_speed_rms_rps",
    "joint_speed_rms_rps",
    "joint_acceleration_rms_rps2",
    "body_linear_speed_rms_mps",
    "root_height_range_m",
)
PARTIAL_RHO_THRESHOLD = 0.25
LOCO_RHO_LIFT_THRESHOLD = 0.05
PERMUTATION_P_THRESHOLD = 0.05
RIDGE_ALPHA = 1.0
REAL_PERMUTATIONS = 10_000
PERMUTATION_SEED = 20260826


def sha256_file(path: Path) -> str:
    """Return a file's SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rankdata_average(value: np.ndarray) -> np.ndarray:
    """Return one-based average ranks, including deterministic tie handling."""
    value = np.asarray(value, dtype=np.float64)
    order = np.argsort(value, kind="mergesort")
    sorted_value = value[order]
    ranks = np.empty(len(value), dtype=np.float64)
    first = 0
    while first < len(value):
        stop = first + 1
        while stop < len(value) and sorted_value[stop] == sorted_value[first]:
            stop += 1
        ranks[order[first:stop]] = 0.5 * (first + 1 + stop)
        first = stop
    return ranks


def correlation(left: np.ndarray, right: np.ndarray) -> float:
    """Return a Pearson correlation, or zero for a constant vector."""
    left = np.asarray(left, dtype=np.float64)
    right = np.asarray(right, dtype=np.float64)
    if np.std(left) < 1.0e-12 or np.std(right) < 1.0e-12:
        return 0.0
    return float(np.corrcoef(left, right)[0, 1])


def spearman(left: np.ndarray, right: np.ndarray) -> float:
    """Return Spearman rho with average ranks."""
    return correlation(rankdata_average(left), rankdata_average(right))


def residualize(value: np.ndarray, controls: np.ndarray) -> np.ndarray:
    """OLS-residualize a rank vector against the frozen control matrix."""
    design = np.column_stack([np.ones(len(value)), controls])
    coefficient = np.linalg.lstsq(design, value, rcond=None)[0]
    return value - design @ coefficient


def partial_spearman(
    development: np.ndarray, target: np.ndarray, controls: np.ndarray
) -> float:
    """Spearman correlation after residualizing both ranked variables."""
    left = residualize(rankdata_average(development), controls)
    right = residualize(rankdata_average(target), controls)
    return correlation(left, right)


def ridge_predict(
    train_x: np.ndarray,
    train_y: np.ndarray,
    test_x: np.ndarray,
    alpha: float = RIDGE_ALPHA,
) -> np.ndarray:
    """Fit a standardized ridge with an unpenalized intercept."""
    mean = train_x.mean(axis=0)
    scale = train_x.std(axis=0)
    scale[scale < 1.0e-9] = 1.0
    train_z = np.column_stack([(train_x - mean) / scale, np.ones(len(train_x))])
    test_z = np.column_stack([(test_x - mean) / scale, np.ones(len(test_x))])
    penalty = alpha * np.eye(train_z.shape[1])
    penalty[-1, -1] = 0.0
    coefficient = np.linalg.solve(
        train_z.T @ train_z + penalty, train_z.T @ train_y
    )
    return test_z @ coefficient


def leave_one_clip_out(
    baseline: np.ndarray,
    augmented: np.ndarray,
    target: np.ndarray,
    clip_ids: np.ndarray,
) -> dict[str, float]:
    """Compute frozen-alpha grouped out-of-fold prediction correlations."""
    prediction_baseline = np.empty(len(target), dtype=np.float64)
    prediction_augmented = np.empty(len(target), dtype=np.float64)
    for clip_id in np.unique(clip_ids):
        test = clip_ids == clip_id
        train = ~test
        prediction_baseline[test] = ridge_predict(
            baseline[train], target[train], baseline[test]
        )
        prediction_augmented[test] = ridge_predict(
            augmented[train], target[train], augmented[test]
        )
    baseline_rho = spearman(prediction_baseline, target)
    augmented_rho = spearman(prediction_augmented, target)
    return {
        "baseline_rho": baseline_rho,
        "augmented_rho": augmented_rho,
        "rho_lift": augmented_rho - baseline_rho,
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV into dictionaries."""
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def validate_and_join(
    reference_rows: list[dict[str, Any]], effect_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Validate the 42x3 table and join frozen reference controls."""
    reference = {int(row["table_index"]): row for row in reference_rows}
    if len(reference) != 42 or set(reference) != set(range(42)):
        raise ValueError("reference table must contain table_index 0..41 exactly once")
    joined: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
    for effect in effect_rows:
        table_index = int(effect["table_index"])
        axis = str(effect["axis"])
        key = (table_index, axis)
        if table_index not in reference or axis not in AXES or key in seen:
            raise ValueError(f"invalid or duplicate effect row {key}")
        row = {**reference[table_index], **effect}
        for policy in ("development", *HELDOUT_POLICIES):
            if int(effect[f"{policy}_replicates"]) != 8:
                raise ValueError(f"{key}: {policy} does not have exactly 8 replicates")
            if float(effect[f"{policy}_paired_alive_fraction"]) < 0.80:
                raise ValueError(f"{key}: {policy} paired-alive fraction is below 0.80")
        joined.append(row)
        seen.add(key)
    expected = {(unit, axis) for unit in range(42) for axis in AXES}
    if seen != expected:
        missing = sorted(expected - seen)
        raise ValueError(f"effect table is not the frozen 42x3 panel; missing={missing[:5]}")
    return sorted(joined, key=lambda row: (int(row["table_index"]), AXES.index(row["axis"])))


def matrices(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Construct rank controls, axis indicators, and fixed row metadata."""
    numeric = np.column_stack(
        [
            rankdata_average(np.asarray([float(row[name]) for row in rows]))
            for name in CONTROL_COLUMNS
        ]
    )
    axis = np.asarray([AXES.index(str(row["axis"])) for row in rows], dtype=int)
    axis_dummies = np.column_stack([axis == 1, axis == 2]).astype(np.float64)
    controls = np.column_stack([numeric, axis_dummies])
    development = np.asarray(
        [float(row["development_s_mm"]) for row in rows], dtype=np.float64
    )
    development_rank = rankdata_average(development)
    development_by_axis = np.column_stack(
        [development_rank * (axis == index) for index in range(len(AXES))]
    )
    return {
        "controls": controls,
        "baseline": controls,
        "augmented": np.column_stack([controls, development_by_axis]),
        "development": development,
        "axis": axis,
        "clip_ids": np.asarray([int(row["clip_id"]) for row in rows], dtype=int),
        "unit_ids": np.asarray([int(row["table_index"]) for row in rows], dtype=int),
    }


def within_clip_permutation_indices(
    clip_ids: np.ndarray,
    unit_ids: np.ndarray,
    axis: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Reassign intact three-axis unit vectors within each source clip."""
    lookup = {
        (int(unit), int(axis_id)): index
        for index, (unit, axis_id) in enumerate(zip(unit_ids, axis, strict=True))
    }
    permutation = np.arange(len(unit_ids))
    for clip_id in np.unique(clip_ids):
        units = np.unique(unit_ids[clip_ids == clip_id])
        reassigned = rng.permutation(units)
        for destination, source in zip(units, reassigned, strict=True):
            for axis_id in range(len(AXES)):
                permutation[lookup[(int(destination), axis_id)]] = lookup[
                    (int(source), axis_id)
                ]
    return permutation


def analyze_target(
    data: dict[str, Any],
    target: np.ndarray,
    permutations: int,
    seed: int,
) -> dict[str, Any]:
    """Analyze one held-out policy against the frozen development vector."""
    observed_partial = partial_spearman(
        data["development"], target, data["controls"]
    )
    predictive = leave_one_clip_out(
        data["baseline"], data["augmented"], target, data["clip_ids"]
    )
    null_partial = np.empty(permutations, dtype=np.float64)
    null_lift = np.empty(permutations, dtype=np.float64)
    rng = np.random.default_rng(seed)
    for draw in range(permutations):
        index = within_clip_permutation_indices(
            data["clip_ids"], data["unit_ids"], data["axis"], rng
        )
        permuted_development = data["development"][index]
        null_partial[draw] = partial_spearman(
            permuted_development, target, data["controls"]
        )
        permuted_rank = rankdata_average(permuted_development)
        permuted_by_axis = np.column_stack(
            [
                permuted_rank * (data["axis"] == axis_id)
                for axis_id in range(len(AXES))
            ]
        )
        permuted_augmented = np.column_stack(
            [data["baseline"], permuted_by_axis]
        )
        null_lift[draw] = leave_one_clip_out(
            data["baseline"],
            permuted_augmented,
            target,
            data["clip_ids"],
        )["rho_lift"]
    partial_p = float((1 + np.sum(null_partial >= observed_partial)) / (permutations + 1))
    lift_p = float((1 + np.sum(null_lift >= predictive["rho_lift"])) / (permutations + 1))
    per_axis = {}
    for axis_id, axis_name in enumerate(AXES):
        selected = data["axis"] == axis_id
        per_axis[axis_name] = {
            "n_units": int(np.sum(selected)),
            "rho": spearman(data["development"][selected], target[selected]),
        }
    return {
        "partial_spearman": observed_partial,
        "partial_permutation_p_one_sided": partial_p,
        "loco_ridge": predictive,
        "loco_lift_permutation_p_one_sided": lift_p,
        "per_axis_raw_spearman": per_axis,
        "permutation_null": {
            "draws": permutations,
            "scheme": "intact three-axis unit vectors permuted within source clip",
            "partial_rho_p95": float(np.percentile(null_partial, 95)),
            "loco_rho_lift_p95": float(np.percentile(null_lift, 95)),
        },
    }


def decision(results: dict[str, dict[str, Any]], measurement_valid: bool) -> dict[str, Any]:
    """Apply the sealed quantitative and replication rules."""
    primary = results["adaptive"]
    replication = results["grounded"]
    primary_pass = bool(
        primary["partial_spearman"] >= PARTIAL_RHO_THRESHOLD
        and primary["partial_permutation_p_one_sided"] <= PERMUTATION_P_THRESHOLD
        and primary["loco_ridge"]["rho_lift"] >= LOCO_RHO_LIFT_THRESHOLD
    )
    replication_pass = bool(
        replication["partial_spearman"] > 0.0
        and replication["loco_ridge"]["rho_lift"] > 0.0
    )
    passed = bool(measurement_valid and primary_pass and replication_pass)
    return {
        "measurement_valid": measurement_valid,
        "primary_adaptive_pass": primary_pass,
        "grounded_directional_replication_pass": replication_pass,
        "gate_pass": passed,
        "next_action": (
            "G3 remains eligible for a later sealed wiring screen"
            if passed
            else "Newton remains an analysis instrument; G3 must never run"
        ),
    }


def analyze_rows(
    rows: list[dict[str, Any]],
    measurement_valid: bool,
    permutations: int,
    seed: int,
) -> dict[str, Any]:
    """Run both held-out-policy tests and the sealed decision function."""
    data = matrices(rows)
    results = {}
    for offset, policy in enumerate(HELDOUT_POLICIES):
        target = np.asarray(
            [float(row[f"{policy}_s_mm"]) for row in rows], dtype=np.float64
        )
        results[policy] = analyze_target(
            data, target, permutations=permutations, seed=seed + offset
        )
    return {
        "results": results,
        "decision": decision(results, measurement_valid),
    }


def synthetic_tables(mode: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Construct outcome-free data for one decision branch."""
    counts = (2, 2, 3, 4, 10, 3, 6, 7, 3, 2)
    rng = np.random.default_rng(9182)
    reference: list[dict[str, Any]] = []
    effects: list[dict[str, Any]] = []
    table_index = 0
    latent = rng.normal(size=sum(counts))
    controls = rng.normal(size=(sum(counts), len(CONTROL_COLUMNS)))
    for clip_id, count in enumerate(counts):
        for _ in range(count):
            row = {
                "table_index": table_index,
                "unit_id": table_index,
                "clip_id": clip_id,
                "clip": f"synthetic_clip_{clip_id}",
            }
            row.update(
                {
                    name: float(controls[table_index, column])
                    for column, name in enumerate(CONTROL_COLUMNS)
                }
            )
            reference.append(row)
            for axis_id, axis_name in enumerate(AXES):
                dev = 3.0 * latent[table_index] + 0.8 * axis_id + rng.normal(scale=0.25)
                if mode == "pass":
                    adaptive = 0.9 * dev + 0.6 * controls[table_index, 0] + rng.normal(scale=0.3)
                    grounded = 0.6 * dev + 0.6 * controls[table_index, 1] + rng.normal(scale=0.5)
                elif mode == "discordant":
                    adaptive = 0.9 * dev + rng.normal(scale=0.3)
                    grounded = -0.8 * dev + rng.normal(scale=0.3)
                else:
                    source = (table_index + 1) % sum(counts)
                    adaptive = 1.2 * controls[table_index, 0] + latent[source]
                    grounded = 1.2 * controls[table_index, 1] - latent[source]
                effects.append(
                    {
                        "table_index": table_index,
                        "unit_id": table_index,
                        "clip_id": clip_id,
                        "clip": row["clip"],
                        "axis": axis_name,
                        "development_s_mm": dev,
                        "adaptive_s_mm": adaptive,
                        "grounded_s_mm": grounded,
                        "development_replicates": 8,
                        "adaptive_replicates": 8,
                        "grounded_replicates": 8,
                        "development_paired_alive_fraction": 1.0,
                        "adaptive_paired_alive_fraction": 1.0,
                        "grounded_paired_alive_fraction": 1.0,
                    }
                )
            table_index += 1
    return reference, effects


def synthetic() -> dict[str, Any]:
    """Exercise the pass, null, and discordant-replication decisions."""
    branches = {}
    expected = {"pass": True, "null": False, "discordant": False}
    for mode, want in expected.items():
        reference, effects = synthetic_tables(mode)
        rows = validate_and_join(reference, effects)
        result = analyze_rows(
            rows,
            measurement_valid=True,
            permutations=499,
            seed=PERMUTATION_SEED,
        )
        got = bool(result["decision"]["gate_pass"])
        if got != want:
            raise AssertionError(f"synthetic {mode}: expected {want}, got {got}")
        branches[mode] = result
    return {
        "schema_version": "newton15_pred_synthetic/1",
        "synthetic": True,
        "pass": True,
        "branches": branches,
    }


def validate_probe_manifest(manifest: dict[str, Any], effects_path: Path) -> bool:
    """Fail closed on the sealed probe manipulation/integrity checks."""
    if manifest.get("effects_csv_sha256") != sha256_file(effects_path):
        raise ValueError("probe manifest does not bind the effects CSV")
    required_zero = (
        "deterministic_repeat_max_abs_delta",
        "invalid_starts",
        "escaped_reference_frames",
        "cross_condition_initial_state_max_abs_delta",
    )
    return bool(
        manifest.get("pass_preflight") is True
        and all(float(manifest.get(name, float("inf"))) == 0.0 for name in required_zero)
    )


def main() -> int:
    """Run the synthetic dry-run or analyze a frozen real probe table."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--effects", type=Path)
    parser.add_argument("--probe-manifest", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--permutations", type=int, default=REAL_PERMUTATIONS)
    parser.add_argument("--seed", type=int, default=PERMUTATION_SEED)
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    if args.synthetic:
        output = synthetic()
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(output, indent=1) + "\n")
        print("Newton predictive-gate synthetic pass/null/discordant branches: PASS")
        return 0
    if args.permutations != REAL_PERMUTATIONS:
        parser.error(f"real analysis requires exactly {REAL_PERMUTATIONS} permutations")
    for name in ("reference", "effects", "probe_manifest"):
        if getattr(args, name) is None:
            parser.error(f"--{name.replace('_', '-')} is required without --synthetic")

    probe_manifest = json.loads(args.probe_manifest.read_text())
    measurement_valid = validate_probe_manifest(probe_manifest, args.effects)
    reference_rows = read_csv(args.reference)
    effect_rows = read_csv(args.effects)
    rows = validate_and_join(reference_rows, effect_rows)
    analyzed = analyze_rows(
        rows,
        measurement_valid=measurement_valid,
        permutations=args.permutations,
        seed=args.seed,
    )
    output = {
        "schema_version": "newton15_pred_result/1",
        "classification": "sealed-protocol measured no-training predictive gate",
        "reference_sha256": sha256_file(args.reference),
        "effects_sha256": sha256_file(args.effects),
        "probe_manifest_sha256": sha256_file(args.probe_manifest),
        "axes": list(AXES),
        "controls": list(CONTROL_COLUMNS),
        "thresholds": {
            "partial_rho": PARTIAL_RHO_THRESHOLD,
            "loco_rho_lift": LOCO_RHO_LIFT_THRESHOLD,
            "permutation_p_one_sided": PERMUTATION_P_THRESHOLD,
        },
        "permutations": args.permutations,
        "seed": args.seed,
        **analyzed,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=1) + "\n")
    verdict = "PASS" if output["decision"]["gate_pass"] else "FAIL"
    print(f"Newton predictive gate: {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
