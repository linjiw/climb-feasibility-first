#!/usr/bin/env python3
"""Verify device receipts and saved development lifecycle before any full study."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import torch

from analyze_natural_entity_lifecycle import verify_lifecycle
from analyze_physics_development import equal_tensors, sha256
from analyze_physics_reset_fixture import verify_physical
from eval_device_lifecycle import verify_graphs
from eval_natural_lifecycle import verify_policy


def analyze(run: Path) -> dict:
    design_path = run / "design.json"
    design = json.loads(design_path.read_text())
    if design["stage"] != "device_lifecycle_development" or design["full_evaluation_enabled"] is not False:
        raise ValueError("not a device development design")
    for path, digest in design["bindings"].items():
        if sha256(Path(path)) != digest:
            raise ValueError(f"source/input changed: {path}")
    device = design["evaluator_arguments"]["device"]
    conditions = json.loads(Path(design["evaluator_arguments"]["conditions"]).read_text())["conditions"]
    if (run / "original/evaluation.csv").read_bytes() != (run / "unchanged/evaluation.csv").read_bytes():
        raise ValueError("same-device original/unchanged CSV parity failed")
    baseline = torch.load(run / "unchanged/physical.pt", map_location="cpu", weights_only=True)
    cells = []
    for name in design["conditions"]:
        cell = run / name
        receipt = json.loads((cell / "receipt.json").read_text())
        if (receipt["condition"] != name or receipt["design_sha256"] != sha256(design_path)
                or receipt["device"] != device or receipt["status"] != "device_lifecycle_completed"):
            raise ValueError("wrong device receipt")
        for filename, digest in receipt["artifacts"].items():
            if sha256(cell / filename) != digest:
                raise ValueError("device artifact changed")
        data = torch.load(cell / "lifecycle.pt", map_location="cpu", weights_only=True)
        if data["condition"] != name or data["design_sha256"] != sha256(design_path):
            raise ValueError("lifecycle identity mismatch")
        result = verify_lifecycle(data, list(csv.DictReader((cell / "evaluation.csv").open())), conditions, name)
        policy = torch.load(cell / "policy.pt", map_location="cpu", weights_only=True)
        if verify_policy(policy, len(data["steps"])) != receipt["policy"]:
            raise ValueError("policy receipt does not replay")
        graphs = json.loads((cell / "graphs.json").read_text())
        verify_graphs(graphs, device, len(data["physics"]))
        result["graphs"] = graphs
        if name != "original":
            physical = torch.load(cell / "physical.pt", map_location="cpu", weights_only=True)
            verify_physical(physical, baseline, name)
            if len(physical["physics"]) != len(data["physics"]) or any(
                    not equal_tensors(a, b) for a, b in zip(physical["physics"], data["physics"])):
                raise ValueError("device physical/lifecycle traces differ")
        if device == "cpu":
            previous = Path(design["cpu_reference_run"]) / name / "evaluation.csv"
            if previous.read_bytes() != (cell / "evaluation.csv").read_bytes():
                raise ValueError("new device entrypoint changed CPU reference output")
        cells.append(result)
    coverage = all(c["natural_failures"] and c["early_successes"] and c["partial_reset_events"] for c in cells)
    return {"status": "device_lifecycle_pass" if coverage else "device_lifecycle_coverage_incomplete",
            "device": device, "cells": cells, "episode_rows": sum(c["episode_rows"] for c in cells),
            "same_device_original_unchanged_parity": True, "policy_immutability_pass": True,
            "full_evaluation_enabled": False, "confirmation_endpoints_opened_by_this_job": False,
            "design_sha256": sha256(design_path), "analyzer_sha256": sha256(Path(__file__)),
            "classification": "development conformance only; no policy benefit or physical transfer claim"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.run)
    with args.out.open("x") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "cells"}))
