#!/usr/bin/env python3
"""Verify H1 development checkpoint loading and paired evaluation provenance."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import torch

from eval_gate_development import verify_inputs, verify_loaded_actor
from eval_natural_lifecycle import verify_policy
from eval_physics_development import sha256


def analyze(run: Path) -> dict:
    design_path = run / "design.json"
    design, training = verify_inputs(design_path, sha256(design_path))
    from analyze_relative_policy import aggregate_rows
    from eval_paired_v2 import selected_file_hashes, software_versions

    args = design["evaluator_arguments"]
    gate = Path(design["gate_worktree"])
    clips = Path(args["clips"]).read_text().splitlines()
    conditions = json.loads(Path(args["conditions"]).read_text())["conditions"]
    references = selected_file_hashes(clips, Path(args["bank"]))
    paired_metadata = None
    results = {}
    for arm in ("on", "off"):
        cell = run / arm
        receipt = json.loads((cell / "receipt.json").read_text())
        if (receipt["admission"] != arm or receipt["design_sha256"] != sha256(design_path)
                or receipt["training_gate"] != training[arm]):
            raise ValueError("gate development receipt identity mismatch")
        for name, digest in receipt["artifacts"].items():
            if sha256(cell / name) != digest:
                raise ValueError("gate development output changed")
        checkpoint = Path(design["training_runs"][arm]) / "model_19.pt"
        policy = torch.load(cell / "policy.pt", map_location="cpu", weights_only=True)
        verify_loaded_actor(policy, checkpoint)
        if verify_policy(policy, receipt["steps"]) != receipt["policy"]:
            raise ValueError("policy immutability receipt changed")
        meta = json.loads((cell / "evaluation.csv.meta.json").read_text())
        expected = {"checkpoint": str(checkpoint), "checkpoint_sha256": sha256(checkpoint),
                    "task": "Climb-Tracking-Flat-Unitree-G1", "device": "cpu",
                    "clips_sha256": sha256(Path(args["clips"])),
                    "conditions_sha256": sha256(Path(args["conditions"])),
                    "evaluator_sha256": sha256(gate / "tools/eval_paired_v2.py"),
                    "selected_reference_sha256": references, "common_reference_sha256": references,
                    "worlds": len(conditions), "full_window_worlds": len(conditions),
                    "nominal": args["nominal"], "joint_noise": args["joint_noise"],
                    "nconmax_per_world": args["nconmax"], "software_versions": software_versions(),
                    "output": str(cell / "evaluation.csv")}
        if any(meta[k] != v for k, v in expected.items()):
            raise ValueError("evaluation metadata does not match bound checkpoint/inputs")
        for name, digest in meta["source_sha256"].items():
            if sha256(gate / name) != digest:
                raise ValueError("evaluation runtime source changed")
        paired = {k: meta[k] for k in ("startup_randomization_sha256", "initial_state_sha256",
                                       "conditions_sha256", "selected_reference_sha256", "common_reference_sha256")}
        if paired_metadata is None:
            paired_metadata = paired
        elif paired_metadata != paired:
            raise ValueError("on/off evaluation initial conditions are not paired")
        rows = list(csv.DictReader((cell / "evaluation.csv").open()))
        scores = aggregate_rows(rows, conditions, clips, window_s=args["window"])
        if not np.isfinite(scores).all() or not ((scores > 0) & (scores <= 1)).all():
            raise ValueError("development tracking score is invalid or zero")
        results[arm] = {"episode_rows": len(rows), "inference_steps": receipt["steps"],
                        "successful_rows": sum(int(row["success"]) for row in rows),
                        "clip_scores": dict(zip(clips, scores.tolist())),
                        "checkpoint_sha256": sha256(checkpoint), "policy_loaded_and_unchanged": True,
                        "training_completed_trials": training[arm]["completed_trials"],
                        "training_rejected_trials": training[arm]["final_allocation"]["rejected_completed_trials"]}
    return {"status": "gate_development_evaluator_pass", "arms": results,
            "episode_rows": sum(row["episode_rows"] for row in results.values()),
            "paired_initial_state": True, "paired_training_initial_actor": True,
            "confirmation_endpoints_opened": False, "full_evaluation_enabled": False,
            "classification": "measured H1 CPU train-to-evaluation conformance; no gate benefit estimate",
            "design_sha256": sha256(design_path), "analyzer_sha256": sha256(Path(__file__))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.run)
    with args.out.open("x") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "arms"}))
