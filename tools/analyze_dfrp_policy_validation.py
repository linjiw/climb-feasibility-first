#!/usr/bin/env python3
"""Analyze the exploratory, fixed-policy raw/repaired DFRP comparison.

All conditions remain in survival/TrackingScore accounting. Fidelity is also
reported on paired complete-window survivors, with its selection denominator.
Intervals resample clips, not trials; one policy seed cannot establish seed-level
uncertainty or a training benefit.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np

from analyze_g_segment import tracking_score
from eval_paired_v2 import sha256_file

METRICS = (
    "success", "survival_fraction", "tracking_score",
    "common_root_relative_mpkpe_m_mean",
    "common_anchor_orientation_error_rad_mean",
    "absolute_mechanical_work_per_actuator_j",
)


def truth(value: object) -> bool:
    if str(value) not in ("True", "False", "true", "false", "1", "0"):
        raise ValueError(f"invalid boolean: {value}")
    return str(value) in ("True", "true", "1")


def metric(row: dict, name: str) -> float:
    if name == "survival_fraction":
        return float(row["survival_s"]) / float(row["actual_window_s"])
    if name == "tracking_score":
        return float(tracking_score(row))
    return float(row[name])


def read_cell(path: Path, design: dict, arm: str) -> tuple[dict, dict]:
    with path.open(newline="") as handle:
        records = list(csv.DictReader(handle))
    rows = {r["condition_id"]: r for r in records}
    conditions = json.loads(Path(design["conditions"]["path"]).read_text())
    expected = {r["condition_id"]: r for r in conditions["conditions"]}
    if len(rows) != len(records) or set(rows) != set(expected):
        raise ValueError(f"{arm}: missing, duplicate, or extra conditions")
    for key, row in rows.items():
        condition = expected[key]
        for field in ("world_id", "start_frame", "replicate", "horizon_steps"):
            if int(row[field]) != condition[field]:
                raise ValueError(f"{arm}: condition field mismatch: {field}")
        if (row["clip"] != condition["clip"]
                or float(row["phase"]) != condition["phase"]
                or truth(row["full_window"]) != condition["full_window"]):
            raise ValueError(f"{arm}: condition identity mismatch")
        window = float(row["actual_window_s"])
        survival = float(row["survival_s"])
        if (not np.isfinite(window) or not np.isfinite(survival)
                or abs(window - condition["horizon_steps"] / 50) > 1e-6
                or not 0 <= survival <= window + 1e-6):
            raise ValueError(f"{arm}: invalid survival horizon")
        if truth(row["success"]) and abs(survival - window) > 1e-5:
            raise ValueError(f"{arm}: success without completed window")
        if any(not np.isfinite(metric(row, name)) for name in METRICS):
            raise ValueError(f"{arm}: nonfinite endpoint")
        if any(metric(row, name) < 0 for name in METRICS):
            raise ValueError(f"{arm}: negative endpoint")
    meta = json.loads(Path(f"{path}.meta.json").read_text())
    source_key = "raw_sha256" if arm == "raw" else "repaired_sha256"
    selected = {r["clip"]: r[source_key] for r in design["clips"]}
    common = {r["clip"]: r["raw_sha256"] for r in design["clips"]}
    required = {
        "schema_version": "paired_eval_output/1",
        "task": "Climb-Tracking-Flat-Unitree-G1",
        "conditions_sha256": design["conditions"]["sha256"],
        "evaluator_sha256": design["evaluator_sha256"],
        "clips_sha256": design["clip_list"]["sha256"],
        "selected_reference_sha256": selected,
        "common_reference_sha256": common,
        "worlds": len(expected), "nominal": False,
        "joint_noise": 0.05, "nconmax_per_world": 70,
    }
    for key, value in required.items():
        if meta.get(key) != value:
            raise ValueError(f"{arm}: metadata mismatch: {key}")
    checkpoint = Path(meta["checkpoint"])
    if checkpoint.name != "model_3999.pt" or not checkpoint.parent.name.endswith(
        "_phase_g_g1_s1"
    ):
        raise ValueError(f"{arm}: checkpoint violates pre-outcome selection")
    if meta["checkpoint_sha256"] != sha256_file(checkpoint):
        raise ValueError(f"{arm}: checkpoint hash mismatch")
    for key in ("startup_randomization_sha256", "initial_state_sha256"):
        if not isinstance(meta.get(key), str) or len(meta[key]) != 64:
            raise ValueError(f"{arm}: missing state provenance")
    if not meta.get("software_versions") or not meta.get("source_sha256"):
        raise ValueError(f"{arm}: missing software provenance")
    for source, digest in meta["source_sha256"].items():
        if sha256_file(Path(source)) != digest:
            raise ValueError(f"{arm}: changed evaluator dependency: {source}")
    return rows, meta


def summarize(raw: dict, repaired: dict, keys: list[str]) -> dict:
    clips = sorted({raw[key]["clip"] for key in keys})
    result = {"conditions": len(keys), "clips": len(clips), "metrics": {}}
    if not keys:
        return result
    rng = np.random.default_rng(20260905)
    indices = rng.integers(0, len(clips), size=(10000, len(clips)))
    for name in METRICS:
        # Clips receive equal weight even if timeline shortening deduplicates starts.
        means = np.array([
            [np.mean([metric(rows[key], name) for key in keys if rows[key]["clip"] == clip])
             for clip in clips]
            for rows in (raw, repaired)
        ], dtype=float)
        delta = means[1] - means[0]
        ci = np.quantile(delta[indices].mean(axis=1), [0.025, 0.975])
        result["metrics"][name] = {
            "raw": float(means[0].mean()), "repaired": float(means[1].mean()),
            "repaired_minus_raw": float(delta.mean()),
            "clip_bootstrap_95ci": ci.tolist(),
        }
    result["trial_accounting"] = {}
    for arm, rows in (("raw", raw), ("repaired", repaired)):
        failures = [rows[k] for k in keys if not truth(rows[k]["success"])]
        result["trial_accounting"][arm] = {
            "successes": len(keys) - len(failures), "failures": len(failures),
            "termination_causes": dict(Counter(r["termination_causes"] for r in failures)),
        }
    return result


def analyze(design_path: Path, raw_path: Path, repaired_path: Path) -> dict:
    design = json.loads(design_path.read_text())
    if design.get("schema_version") != "dfrp_policy_validation_design/1":
        raise ValueError("unsupported design")
    for key in ("conditions", "clip_list", "curated_manifest", "training_clips"):
        artifact = design[key]
        if sha256_file(Path(artifact["path"])) != artifact["sha256"]:
            raise ValueError(f"changed design input: {key}")
    if sha256_file(Path(__file__)) != design["analyzer_sha256"]:
        raise ValueError("analysis implementation changed after design construction")
    raw, raw_meta = read_cell(raw_path, design, "raw")
    repaired, repaired_meta = read_cell(repaired_path, design, "repaired")
    for field in ("checkpoint_sha256", "startup_randomization_sha256", "task",
                  "software_versions", "source_sha256", "device"):
        if raw_meta.get(field) != repaired_meta.get(field):
            raise ValueError(f"unpaired evaluation provenance: {field}")
    # Initial robot state follows the assigned reference; equality is not required.
    groups = {
        "all": {r["clip"] for r in design["clips"]},
        "qualified_repairs": {r["clip"] for r in design["clips"] if r["qualified_repair"]},
        "unchanged_controls": {r["clip"] for r in design["clips"] if not r["qualified_repair"]},
        "training_overlap": {r["clip"] for r in design["clips"] if r["training_overlap"]},
        "outside_training": {r["clip"] for r in design["clips"] if not r["training_overlap"]},
    }
    strata = {}
    for name, clips in groups.items():
        keys = [k for k, r in raw.items() if r["clip"] in clips]
        frame_zero = [k for k in keys if int(raw[k]["start_frame"]) == 0]
        full = [k for k in keys if truth(raw[k]["full_window"])]
        survivors = [k for k in full if truth(raw[k]["success"]) and truth(repaired[k]["success"])]
        strata[name] = {
            "all_conditions": summarize(raw, repaired, keys),
            "frame_zero": summarize(raw, repaired, frame_zero),
            "full_windows": summarize(raw, repaired, full),
            "short_windows": summarize(raw, repaired, [k for k in keys if k not in full]),
            "paired_complete_window_survivors": summarize(raw, repaired, survivors),
            "survivor_eligible_conditions": len(full),
        }
    return {
        "schema_version": "dfrp_policy_validation_result/1",
        "classification": "exploratory fixed-policy reference comparison",
        "status": "measured", "design_sha256": sha256_file(design_path),
        "checkpoint_sha256": raw_meta["checkpoint_sha256"],
        "inputs": {arm: {"csv_sha256": sha256_file(path),
                          "metadata_sha256": sha256_file(Path(f"{path}.meta.json"))}
                   for arm, path in (("raw", raw_path), ("repaired", repaired_path))},
        "limitations": ["One checkpoint/seed; intervals reflect clip sampling only.",
                        "Window survival is not uninterrupted full-clip execution.",
                        "Complete-window survivor fidelity is selection-conditioned.",
                        "Reference assignment changes initialization and termination targets.",
                        "Outside-training clips are not an independently sampled benchmark."],
        "strata": strata,
        "per_clip": {clip: summarize(raw, repaired, [k for k, r in raw.items() if r["clip"] == clip])
                     for clip in sorted(groups["all"])},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--repaired", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.design, args.raw, args.repaired)
    with args.out.open("x") as handle:
        json.dump(result, handle, indent=1, allow_nan=False)
        handle.write("\n")


if __name__ == "__main__":
    main()
