#!/usr/bin/env python3
"""Analyze an exploratory four-cell paired-v2 K/R repair pilot.

Quality is compared only on paired jointly successful conditions. Survival and
RMST use every full-window condition. This tool never replaces sealed N7 output.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

CELLS = ("K_raw", "K_repaired", "R_raw", "R_repaired")
SURVIVAL_METRICS = ("success", "survival_s")
QUALITY_METRICS = (
    "common_anchor_position_error_m_mean",
    "common_anchor_orientation_error_rad_mean",
    "common_root_relative_mpkpe_m_mean",
    "common_body_orientation_error_rad_mean",
    "common_root_relative_velocity_error_mps_mean",
    "common_joint_position_error_rad_mean",
    "common_joint_velocity_error_rps_mean",
    "common_body_acceleration_error_mps2_mean",
    "common_body_jerk_error_mps3_mean",
    "effort_sat_mean",
    "effort_sat_peak",
    "absolute_mechanical_work_per_actuator_j",
    "action_delta_mean_per_step",
    "joint_limit_exposure",
    "foot_contact_fraction",
    "contacting_ankle_link_speed_mean_mps",
    "foot_penetration_mean_m",
    "foot_contact_switch_rate_hz",
)
REFERENCE_DISTORTION_METRICS = (
    "active_to_common_root_relative_mpkpe_m_mean",
    "active_to_common_body_orientation_error_rad_mean",
    "active_to_common_root_relative_velocity_error_mps_mean",
)
CONDITION_FIELDS = (
    "condition_id",
    "clip",
    "start_frame",
    "phase",
    "replicate",
    "horizon_steps",
    "full_window",
)
PAIRING_META_FIELDS = (
    "conditions_sha256",
    "evaluator_sha256",
    "startup_randomization_sha256",
    "software_versions",
    "nconmax_per_world",
    "nominal",
    "joint_noise",
    "source_sha256",
    "common_reference_sha256",
)


def sha256_file(path: Path) -> str:
    """Hash a pilot input."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_cell(path: Path) -> tuple[dict[str, dict[str, str]], dict[str, Any]]:
    """Read unique condition rows and adjacent metadata."""
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_id = {row["condition_id"]: row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError(f"{path}: duplicate condition_id")
    meta_path = Path(f"{path}.meta.json")
    return by_id, json.loads(meta_path.read_text())


def validate_pairing(
    cells: dict[str, dict[str, dict[str, str]]],
    metadata: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Reject any condition or mechanics mismatch before arithmetic."""
    reference_ids = set(cells[CELLS[0]])
    for name in CELLS[1:]:
        if set(cells[name]) != reference_ids:
            raise ValueError(f"{name}: condition-ID set differs")
    for condition_id in reference_ids:
        baseline = cells[CELLS[0]][condition_id]
        for name in CELLS[1:]:
            row = cells[name][condition_id]
            if any(row[field] != baseline[field] for field in CONDITION_FIELDS):
                raise ValueError(f"{name}/{condition_id}: condition fields differ")

    baseline_meta = metadata[CELLS[0]]
    for name in CELLS[1:]:
        for field in PAIRING_META_FIELDS:
            if metadata[name].get(field) != baseline_meta.get(field):
                raise ValueError(f"{name}: pairing metadata differs at {field}")
    for left, right in (("K_raw", "R_raw"), ("K_repaired", "R_repaired")):
        if (
            metadata[left]["initial_state_sha256"]
            != metadata[right]["initial_state_sha256"]
        ):
            raise ValueError(f"{left}/{right}: initial-state hashes differ")
    if (
        metadata["K_raw"]["checkpoint_sha256"]
        != metadata["K_repaired"]["checkpoint_sha256"]
    ):
        raise ValueError("K checkpoint differs across references")
    if (
        metadata["R_raw"]["checkpoint_sha256"]
        != metadata["R_repaired"]["checkpoint_sha256"]
    ):
        raise ValueError("R checkpoint differs across references")
    return {
        "conditions": len(reference_ids),
        "conditions_sha256": baseline_meta["conditions_sha256"],
        "evaluator_sha256": baseline_meta["evaluator_sha256"],
        "startup_randomization_sha256": baseline_meta["startup_randomization_sha256"],
        "raw_initial_state_sha256": metadata["K_raw"]["initial_state_sha256"],
        "repaired_initial_state_sha256": metadata["K_repaired"]["initial_state_sha256"],
    }


def motion_means(
    rows: dict[str, dict[str, str]], condition_ids: set[str], metric: str
) -> dict[str, float]:
    """Average replicates/starts within each scientific motion unit."""
    values: dict[str, list[float]] = defaultdict(list)
    for condition_id in condition_ids:
        row = rows[condition_id]
        values[row["clip"]].append(float(row[metric]))
    return {clip: float(np.mean(items)) for clip, items in values.items()}


def cell_means(
    cells: dict[str, dict[str, dict[str, str]]],
    condition_ids: set[str],
    metric: str,
) -> dict[str, dict[str, float]]:
    """Return motion tables for all four cells."""
    return {
        name: motion_means(rows, condition_ids, metric) for name, rows in cells.items()
    }


def decompose(tables: dict[str, dict[str, float]]) -> dict[str, float]:
    """Motion-equal 2x2 policy/reference decomposition."""
    motions = sorted(set.intersection(*(set(table) for table in tables.values())))
    if not motions:
        raise ValueError("no motions remain for decomposition")
    mean = {
        name: float(np.mean([table[motion] for motion in motions]))
        for name, table in tables.items()
    }
    training = mean["R_raw"] - mean["K_raw"]
    reference_k = mean["K_repaired"] - mean["K_raw"]
    reference_r = mean["R_repaired"] - mean["R_raw"]
    deployment = mean["R_repaired"] - mean["K_raw"]
    interaction = (
        mean["R_repaired"] - mean["R_raw"] - mean["K_repaired"] + mean["K_raw"]
    )
    return {
        "motions": len(motions),
        "K_raw": mean["K_raw"],
        "K_repaired": mean["K_repaired"],
        "R_raw": mean["R_raw"],
        "R_repaired": mean["R_repaired"],
        "training_transfer_Rraw_minus_Kraw": training,
        "reference_effect_Krepaired_minus_Kraw": reference_k,
        "reference_effect_Rrepaired_minus_Rraw": reference_r,
        "deployment_Rrepaired_minus_Kraw": deployment,
        "interaction": interaction,
        "identity_residual": deployment - training - reference_k - interaction,
    }


def paired_delta(
    treatment: dict[str, float], control: dict[str, float]
) -> dict[str, float]:
    """Motion-equal paired delta on a shared motion table."""
    motions = sorted(set(treatment) & set(control))
    return {
        "motions": len(motions),
        "paired_delta": float(
            np.mean([treatment[motion] - control[motion] for motion in motions])
        ),
    }


def bootstrap_contrasts(
    tables: dict[str, dict[str, float]], *, seed: int, draws: int
) -> dict[str, list[float]]:
    """Exploratory motion bootstrap for the four named survival contrasts."""
    motions = sorted(set.intersection(*(set(table) for table in tables.values())))
    if len(motions) < 2:
        return {}
    matrix = np.array(
        [[tables[name][motion] for name in CELLS] for motion in motions], dtype=float
    )
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(motions), size=(draws, len(motions)))
    sampled = matrix[indices].mean(axis=1)
    contrasts = {
        "training_transfer_Rraw_minus_Kraw": sampled[:, 2] - sampled[:, 0],
        "reference_effect_Krepaired_minus_Kraw": sampled[:, 1] - sampled[:, 0],
        "deployment_Rrepaired_minus_Kraw": sampled[:, 3] - sampled[:, 0],
        "interaction": sampled[:, 3] - sampled[:, 2] - sampled[:, 1] + sampled[:, 0],
    }
    return {
        name: [float(value) for value in np.quantile(values, [0.025, 0.975])]
        for name, values in contrasts.items()
    }


def summarize_pair(
    treatment: dict[str, float],
    control: dict[str, float],
    *,
    seed: int,
    draws: int,
) -> dict[str, Any]:
    """Motion-equal paired means, delta, and motion-bootstrap interval."""
    motions = sorted(set(treatment) & set(control))
    if not motions:
        raise ValueError("no motions remain for paired comparison")
    treatment_values = np.array([treatment[motion] for motion in motions])
    control_values = np.array([control[motion] for motion in motions])
    deltas = treatment_values - control_values
    result: dict[str, Any] = {
        "motions": len(motions),
        "K_raw": float(control_values.mean()),
        "R_raw": float(treatment_values.mean()),
        "Rraw_minus_Kraw": float(deltas.mean()),
    }
    if len(motions) >= 2:
        rng = np.random.default_rng(seed)
        indices = rng.integers(0, len(motions), size=(draws, len(motions)))
        result["motion_bootstrap_95ci"] = [
            float(value)
            for value in np.quantile(deltas[indices].mean(axis=1), [0.025, 0.975])
        ]
    return result


def analyze_clean_control(
    k_path: Path,
    r_path: Path,
    *,
    bootstrap_seed: int,
    bootstrap_draws: int,
) -> dict[str, Any]:
    """Analyze a disjoint raw-reference K/R panel under strict pairing."""
    k_rows, k_meta = read_cell(k_path)
    r_rows, r_meta = read_cell(r_path)
    if set(k_rows) != set(r_rows):
        raise ValueError("clean control: condition-ID sets differ")
    for condition_id, k_row in k_rows.items():
        r_row = r_rows[condition_id]
        if any(r_row[field] != k_row[field] for field in CONDITION_FIELDS):
            raise ValueError(f"clean control/{condition_id}: condition fields differ")
    for field in PAIRING_META_FIELDS:
        if r_meta.get(field) != k_meta.get(field):
            raise ValueError(f"clean control: pairing metadata differs at {field}")
    if r_meta["initial_state_sha256"] != k_meta["initial_state_sha256"]:
        raise ValueError("clean control: initial-state hashes differ")

    full_ids = {
        condition_id
        for condition_id, row in k_rows.items()
        if row["full_window"] == "True"
    }
    shared_success = {
        condition_id
        for condition_id in full_ids
        if int(k_rows[condition_id]["success"]) == 1
        and int(r_rows[condition_id]["success"]) == 1
    }

    def comparison(condition_ids: set[str], metric: str) -> dict[str, Any]:
        return summarize_pair(
            motion_means(r_rows, condition_ids, metric),
            motion_means(k_rows, condition_ids, metric),
            seed=bootstrap_seed,
            draws=bootstrap_draws,
        )

    return {
        "classification": "exploratory feasible-disjoint clean/raw control",
        "populations": {
            "all_conditions": len(k_rows),
            "full_window_conditions": len(full_ids),
            "joint_success_conditions": len(shared_success),
        },
        "pairing": {
            "conditions_sha256": k_meta["conditions_sha256"],
            "startup_randomization_sha256": k_meta[
                "startup_randomization_sha256"
            ],
            "initial_state_sha256": k_meta["initial_state_sha256"],
        },
        "survival": {
            metric: comparison(full_ids, metric) for metric in SURVIVAL_METRICS
        },
        "quality_joint_success": {
            metric: comparison(shared_success, metric) for metric in QUALITY_METRICS
        },
        "reference_distortion_joint_success": {
            metric: comparison(shared_success, metric)
            for metric in REFERENCE_DISTORTION_METRICS
        },
        "inputs": {
            "K_raw": {"path": str(k_path), "sha256": sha256_file(k_path)},
            "R_raw": {"path": str(r_path), "sha256": sha256_file(r_path)},
        },
    }


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    """Validate and analyze real pilot cells."""
    paths = {
        "K_raw": args.k_raw.resolve(),
        "K_repaired": args.k_repaired.resolve(),
        "R_raw": args.r_raw.resolve(),
        "R_repaired": args.r_repaired.resolve(),
    }
    loaded = {name: read_cell(path) for name, path in paths.items()}
    cells = {name: value[0] for name, value in loaded.items()}
    metadata = {name: value[1] for name, value in loaded.items()}
    pairing = validate_pairing(cells, metadata)

    manifest = json.loads(args.repair_manifest.read_text())
    strata = {row["name"]: row["stratum"] for row in manifest["clips"]}
    baseline = cells["K_raw"]
    full_ids = {
        condition_id
        for condition_id, row in baseline.items()
        if row["full_window"] == "True"
    }
    four_way_success = {
        condition_id
        for condition_id in full_ids
        if all(int(cells[name][condition_id]["success"]) == 1 for name in CELLS)
    }

    result: dict[str, Any] = {
        "classification": (
            "exploratory one-training-seed evaluator/checkpoint pilot; "
            "does not replace sealed N7"
        ),
        "pairing": pairing,
        "populations": {
            "all_conditions": len(baseline),
            "full_window_conditions": len(full_ids),
            "four_way_joint_success_conditions": len(four_way_success),
            "short_window_conditions": len(baseline) - len(full_ids),
        },
        "survival": {},
        "quality_four_way_joint_success": {},
        "reference_distortion_four_way_joint_success": {},
        "quality_pairwise_joint_success": {},
        "by_repair_stratum": {},
        "inputs": {
            name: {"path": str(path), "sha256": sha256_file(path)}
            for name, path in paths.items()
        },
    }
    for metric in SURVIVAL_METRICS:
        tables = cell_means(cells, full_ids, metric)
        result["survival"][metric] = {
            "decomposition": decompose(tables),
            "motion_bootstrap_95ci": bootstrap_contrasts(
                tables, seed=args.bootstrap_seed, draws=args.bootstrap_draws
            ),
        }
    for metric in QUALITY_METRICS:
        result["quality_four_way_joint_success"][metric] = decompose(
            cell_means(cells, four_way_success, metric)
        )
    for metric in REFERENCE_DISTORTION_METRICS:
        result["reference_distortion_four_way_joint_success"][metric] = decompose(
            cell_means(cells, four_way_success, metric)
        )

    comparisons = {
        "training_raw_R_minus_K": ("R_raw", "K_raw"),
        "reference_K_repaired_minus_raw": ("K_repaired", "K_raw"),
        "reference_R_repaired_minus_raw": ("R_repaired", "R_raw"),
        "deployment_Rrepaired_minus_Kraw": ("R_repaired", "K_raw"),
    }
    for label, (treatment, control) in comparisons.items():
        shared_success = {
            condition_id
            for condition_id in full_ids
            if int(cells[treatment][condition_id]["success"]) == 1
            and int(cells[control][condition_id]["success"]) == 1
        }
        result["quality_pairwise_joint_success"][label] = {
            "conditions": len(shared_success),
            "metrics": {
                metric: paired_delta(
                    motion_means(cells[treatment], shared_success, metric),
                    motion_means(cells[control], shared_success, metric),
                )
                for metric in QUALITY_METRICS
            },
        }

    for stratum in (
        "repaired_certified",
        "repaired_over_budget",
        "repaired_residual",
    ):
        ids = {
            condition_id
            for condition_id in full_ids
            if strata[baseline[condition_id]["clip"]] == stratum
        }
        result["by_repair_stratum"][stratum] = {
            metric: decompose(cell_means(cells, ids, metric))
            for metric in SURVIVAL_METRICS
        }
    return result


def synthetic() -> None:
    """Check the 2x2 arithmetic identity."""
    tables = {
        "K_raw": {"a": 0.2, "b": 0.4},
        "K_repaired": {"a": 0.3, "b": 0.5},
        "R_raw": {"a": 0.25, "b": 0.45},
        "R_repaired": {"a": 0.4, "b": 0.6},
    }
    result = decompose(tables)
    assert abs(result["identity_residual"]) < 1.0e-12
    assert result["motions"] == 2
    print("paired-v2 pilot analyzer synthetic identity passes")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k-raw", type=Path)
    parser.add_argument("--k-repaired", type=Path)
    parser.add_argument("--r-raw", type=Path)
    parser.add_argument("--r-repaired", type=Path)
    parser.add_argument(
        "--repair-manifest",
        type=Path,
        default=Path("reports/repaired800/manifest.json"),
    )
    parser.add_argument("--out", type=Path)
    parser.add_argument("--bootstrap-seed", type=int, default=20260824)
    parser.add_argument("--bootstrap-draws", type=int, default=20_000)
    parser.add_argument("--control-k-raw", type=Path)
    parser.add_argument("--control-r-raw", type=Path)
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    if args.synthetic:
        synthetic()
        return 0
    required = (args.k_raw, args.k_repaired, args.r_raw, args.r_repaired, args.out)
    if any(value is None for value in required):
        parser.error("four cell paths and --out are required")
    result = analyze(args)
    if (args.control_k_raw is None) != (args.control_r_raw is None):
        parser.error("both clean-control paths are required together")
    if args.control_k_raw is not None and args.control_r_raw is not None:
        result["clean_control"] = analyze_clean_control(
            args.control_k_raw.resolve(),
            args.control_r_raw.resolve(),
            bootstrap_seed=args.bootstrap_seed,
            bootstrap_draws=args.bootstrap_draws,
        )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(
        json.dumps(
            {
                "wrote": str(args.out),
                "populations": result["populations"],
                "survival": result["survival"],
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
