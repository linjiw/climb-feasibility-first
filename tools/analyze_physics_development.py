#!/usr/bin/env python3
"""Verify original-evaluator parity and actual development policy interventions."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

import torch

from physics_sensitivity import CONDITIONS, FOOT_PATTERN, KNEES


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def equal_tensors(left: dict, right: dict) -> bool:
    return set(left) == set(right) and all(torch.equal(left[k], right[k]) for k in left)


def verify_trace(name: str, data: dict, baseline: dict) -> dict:
    selected = CONDITIONS[name]
    if data["condition"] != name:
        raise ValueError("instrumentation belongs to another condition")
    for key in ("startup_before_intervention", "initial_state", "first_observation"):
        if not equal_tensors(data[key], baseline[key]):
            raise ValueError(f"unpaired {key}")
    if not torch.equal(data["first_action"], baseline["first_action"]):
        raise ValueError("initial policy action differs")
    if data["actuator_names"] != baseline["actuator_names"] or data["geom_names"] != baseline["geom_names"]:
        raise ValueError("physical target identities differ")
    expected_limits = baseline["force_ranges"].clone()
    knees = [i for i, n in enumerate(data["actuator_names"]) if n.split("/")[-1] in KNEES]
    feet = [i for i, n in enumerate(data["geom_names"]) if FOOT_PATTERN.fullmatch(n.split("/")[-1])]
    if len(knees) != 2 or len(feet) != 14:
        raise ValueError("unexpected named intervention targets")
    if selected["knee_cap_nm"] is not None:
        expected_limits[knees] = torch.tensor([-selected["knee_cap_nm"], selected["knee_cap_nm"]], dtype=expected_limits.dtype)
    if not torch.equal(data["force_ranges"], expected_limits):
        raise ValueError("knee intervention changes wrong force limits")
    expected_friction = baseline["startup_before_intervention"]["geom_friction"].clone()
    if selected["foot_friction"] is not None:
        expected_friction[:, feet, 0] = selected["foot_friction"]
    if not torch.equal(data["friction_after_intervention"], expected_friction):
        raise ValueError("friction intervention changes wrong coefficients")
    rows = data["physics"]
    if len(rows) != 200:
        raise ValueError("missing physics substeps in one-second development run")
    lag = selected["delay_steps"]
    max_force_excess = 0.0
    for i, row in enumerate(rows):
        if not torch.equal(row["ctrl"], rows[max(0, i - lag)]["desired"]):
            raise ValueError("actual delayed controls do not match requested targets")
        force = row["force"]
        if force.shape != (4, 29) or not torch.isfinite(force).all():
            raise ValueError("invalid force telemetry")
        excess = max(float((force - expected_limits[:, 1]).max()),
                     float((expected_limits[:, 0] - force).max()))
        max_force_excess = max(max_force_excess, excess)
        if excess > 1e-4:
            raise ValueError("force exceeds realized actuator clamp")
    knee_forces = torch.stack([r["force"][:, knees] for r in rows]).abs()
    knee_saturation = knee_forces >= 0.98 * expected_limits[knees, 1]
    return {"condition": name, "startup_state_observation_action_paired": True,
            "recorded_physics_substeps": len(rows), "delay_ms": lag * 5,
            "maximum_force_bound_excess_nm": max_force_excess,
            "maximum_absolute_knee_force_nm": float(knee_forces.max()),
            "knee_samples_at_98pct_limit": int(knee_saturation.sum()),
            "knee_force_sample_count": knee_forces.numel(),
            "friction_and_knee_target_specificity": True}


def analyze(run: Path) -> dict:
    design_path = run / "design.json"
    design = json.loads(design_path.read_text())
    for name, digest in design["bindings"].items():
        if sha256(Path(name)) != digest:
            raise ValueError(f"bound input/source changed: {name}")
    root = Path(design["root"])
    sys.path[:0] = [str(root / "tools"), str(root)]
    from analyze_relative_policy import aggregate_rows
    from eval_paired_v2 import sha256_tensors
    args = design["evaluator_arguments"]
    conditions = json.loads(Path(args["conditions"]).read_text())["conditions"]
    clips = Path(args["clips"]).read_text().splitlines()
    if len(clips) != 2 or len(conditions) != 4:
        raise ValueError("wrong development panel size")
    if set(clips) & set((root / "reports/g_segment/panel/panel.txt").read_text().splitlines()):
        raise ValueError("development inputs overlap the held-out panel")
    if (run / "original/evaluation.csv").read_bytes() != (run / "unchanged/evaluation.csv").read_bytes():
        raise ValueError("zero-intervention CSV differs from original evaluator")
    baseline = torch.load(run / "unchanged/instrumentation.pt", map_location="cpu", weights_only=True)
    original_meta = json.loads((run / "original/evaluation.csv.meta.json").read_text())
    results = []
    for name in ("original", *CONDITIONS):
        cell = run / name
        receipt = json.loads((cell / "receipt.json").read_text())
        if (receipt["condition"] != name or receipt["design_sha256"] != sha256(design_path)
                or receipt["csv_sha256"] != sha256(cell / "evaluation.csv")
                or receipt["metadata_sha256"] != sha256(cell / "evaluation.csv.meta.json")):
            raise ValueError("cell receipt does not authenticate this run")
        meta = json.loads((cell / "evaluation.csv.meta.json").read_text())
        for key in ("checkpoint_sha256", "clips_sha256", "conditions_sha256", "initial_state_sha256",
                    "selected_reference_sha256", "common_reference_sha256", "software_versions", "evaluator_sha256"):
            if meta[key] != original_meta[key]:
                raise ValueError(f"cell changes common evaluator provenance: {key}")
        with (cell / "evaluation.csv").open() as handle:
            rows = list(csv.DictReader(handle))
        scores = aggregate_rows(rows, conditions, clips, window_s=args["window"])
        if not (scores > 0).all():
            raise ValueError("development tracking is zero on a selected clip")
        record = {"condition": name, "episode_rows": len(rows),
                  "full_horizon_success_rows": sum(int(r["success"]) for r in rows),
                  "nonzero_clip_tracking_verified": True}
        if name != "original":
            trace_path = cell / "instrumentation.pt"
            if receipt["instrumentation_sha256"] != sha256(trace_path):
                raise ValueError("instrumentation hash differs")
            data = torch.load(trace_path, map_location="cpu", weights_only=True)
            if data["design_sha256"] != sha256(design_path):
                raise ValueError("instrumentation binds another design")
            record.update(verify_trace(name, data, baseline))
            if sha256_tensors(data["initial_state"]) != meta["initial_state_sha256"]:
                raise ValueError("initial state trace disagrees with original evaluator metadata")
            startup = data["startup_before_intervention"]
            expected = {"body_ipos": startup["body_ipos"], "encoder_bias": startup["encoder_bias"],
                        "geom_friction": data["friction_after_intervention"]}
            if sha256_tensors(expected) != meta["startup_randomization_sha256"]:
                raise ValueError("startup intervention differs from evaluator metadata")
        results.append(record)
    return {"status": "development_evaluator_lifecycle_pass", "conditions": results,
            "classification": "measured CPU development integration; no robustness-benefit inference",
            "original_vs_unchanged_csv_exact": True, "design_sha256": sha256(design_path),
            "development_checkpoint": design["development_checkpoint"],
            "environment_seed": args["seed"], "joint_noise_seed": args["joint_noise_seed"],
            "episode_rows": sum(r["episode_rows"] for r in results),
            "confirmation_endpoints_opened": False, "full_evaluation_enabled": False,
            "limitations": ["Two training clips and one development policy; not held-out efficacy.",
                            "Short episodes do not establish long-horizon robustness or hardware transfer.",
                            "CPU-only; GPU graph lifecycle remains pending.",
                            "No explicit actor/normalizer tensor immutability hashes collected in this adapter.",
                            "Uninterrupted delay checks do not cover policy-triggered reset cases; fixture partial-reset checks are separate."]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.run_dir.resolve())
    with args.out.open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": result["status"], "episode_rows": result["episode_rows"]}))
