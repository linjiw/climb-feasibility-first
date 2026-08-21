#!/usr/bin/env python3
"""Analyze paired segment-v2 policies with unit-clustered uncertainty."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

QUALITY_METRICS = (
    "error_body_pos_m",
    "error_anchor_pos_m",
    "error_anchor_rot_rad",
    "error_joint_pos_l2",
    "mechanical_work_per_actuator_j",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def clustered_interval(
    values_by_unit: dict[int, list[float]], rng: np.random.Generator
) -> dict[str, float | int]:
    unit_means = np.asarray(
        [np.mean(values_by_unit[key]) for key in sorted(values_by_unit)],
        dtype=np.float64,
    )
    if unit_means.size < 2:
        raise ValueError("at least two units are required for clustered uncertainty")
    draws = rng.choice(unit_means, size=(10_000, unit_means.size), replace=True).mean(
        axis=1
    )
    return {
        "estimate": float(unit_means.mean()),
        "ci95_low": float(np.quantile(draws, 0.025)),
        "ci95_high": float(np.quantile(draws, 0.975)),
        "units": int(unit_means.size),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uniform", required=True, type=Path)
    parser.add_argument("--adaptive", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=20260820)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)

    uniform = {row["world_id"]: row for row in read_csv(args.uniform)}
    adaptive = {row["world_id"]: row for row in read_csv(args.adaptive)}
    if uniform.keys() != adaptive.keys():
        raise ValueError("policy summaries do not contain the same worlds")
    condition_fields = (
        "table_index",
        "unit_id",
        "clip_id",
        "phase",
        "rep",
        "start_frame",
    )
    for world_id in uniform:
        if any(
            uniform[world_id][field] != adaptive[world_id][field]
            for field in condition_fields
        ):
            raise ValueError(f"condition mismatch for {world_id}")

    uniform_meta = json.loads(Path(f"{args.uniform}.meta.json").read_text())
    adaptive_meta = json.loads(Path(f"{args.adaptive}.meta.json").read_text())
    paired_fields = (
        "unit_table_sha256",
        "conditions_sha256",
        "environment_seed",
        "initial_state_sha256",
        "startup_randomization_sha256",
        "worlds",
    )
    for field in paired_fields:
        if uniform_meta[field] != adaptive_meta[field]:
            raise ValueError(f"evaluation pairing mismatch: {field}")

    endpoints: dict[str, dict[str, float | int]] = {}
    for name in ("success", "survival_s"):
        differences: dict[int, list[float]] = defaultdict(list)
        for world_id, uniform_row in uniform.items():
            unit_id = int(uniform_row["unit_id"])
            differences[unit_id].append(
                float(adaptive[world_id][name]) - float(uniform_row[name])
            )
        endpoints[f"adaptive_minus_uniform_{name}"] = clustered_interval(
            differences, rng
        )

    uniform_trajectory_path = args.uniform.with_name(
        f"{args.uniform.stem}_trajectory.csv"
    )
    adaptive_trajectory_path = args.adaptive.with_name(
        f"{args.adaptive.stem}_trajectory.csv"
    )
    uniform_trajectory = {
        (row["world_id"], int(row["step"])): row
        for row in read_csv(uniform_trajectory_path)
    }
    adaptive_trajectory = {
        (row["world_id"], int(row["step"])): row
        for row in read_csv(adaptive_trajectory_path)
    }
    common_keys = uniform_trajectory.keys() & adaptive_trajectory.keys()
    quality: dict[str, dict[str, float | int]] = {}
    for metric in QUALITY_METRICS:
        differences = defaultdict(list)
        for world_id, step in common_keys:
            unit_id = int(uniform[world_id]["unit_id"])
            differences[unit_id].append(
                float(adaptive_trajectory[(world_id, step)][metric])
                - float(uniform_trajectory[(world_id, step)][metric])
            )
        quality[f"adaptive_minus_uniform_{metric}"] = clustered_interval(
            differences, rng
        )

    per_unit: list[dict[str, Any]] = []
    grouped_worlds: dict[int, list[str]] = defaultdict(list)
    for world_id, row in uniform.items():
        grouped_worlds[int(row["unit_id"])].append(world_id)
    for unit_id in sorted(grouped_worlds):
        worlds = grouped_worlds[unit_id]
        per_unit.append(
            {
                "unit_id": unit_id,
                "clip_id": int(uniform[worlds[0]]["clip_id"]),
                "worlds": len(worlds),
                "uniform_success": float(
                    np.mean([float(uniform[world]["success"]) for world in worlds])
                ),
                "adaptive_success": float(
                    np.mean([float(adaptive[world]["success"]) for world in worlds])
                ),
                "uniform_survival_s": float(
                    np.mean(
                        [float(uniform[world]["survival_s"]) for world in worlds]
                    )
                ),
                "adaptive_survival_s": float(
                    np.mean(
                        [float(adaptive[world]["survival_s"]) for world in worlds]
                    )
                ),
            }
        )

    result = {
        "schema_version": "segment_pilot_analysis/1",
        "classification": "unsealed exploratory paired pilot",
        "pairing": {field: uniform_meta[field] for field in paired_fields},
        "uniform": {
            "checkpoint": uniform_meta["checkpoint"],
            "success_rate": uniform_meta["success_rate"],
            "mean_survival_s": uniform_meta["mean_survival_s"],
        },
        "adaptive": {
            "checkpoint": adaptive_meta["checkpoint"],
            "success_rate": adaptive_meta["success_rate"],
            "mean_survival_s": adaptive_meta["mean_survival_s"],
        },
        "cluster_bootstrap": {
            "resamples": 10_000,
            "cluster": "canonical segment unit_id",
            "seed": args.seed,
            "endpoints": endpoints,
            "common_survivor_frame_quality": quality,
        },
        "common_survivor_frames": len(common_keys),
        "uniform_survivor_frames": len(uniform_trajectory),
        "adaptive_survivor_frames": len(adaptive_trajectory),
        "per_unit": per_unit,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result["cluster_bootstrap"], indent=1))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
