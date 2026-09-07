#!/usr/bin/env python3
"""Replay injected retirement, scoring and partial-reset isolation from CPU traces."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import torch

from analyze_physics_development import equal_tensors, sha256
from audit_policy_immutability import verify_payload
from physics_sensitivity import CONDITIONS, FOOT_PATTERN, KNEES


def verify_lifecycle(data: dict, rows: list[dict], design: dict, name: str) -> dict:
    steps, physics, resets = data["steps"], data["physics"], data["resets"]
    if len(steps) != 50 or len(physics) != 200 or len(rows) != 4:
        raise ValueError("incomplete fixture trace")
    alive = torch.ones(4, dtype=torch.bool)
    survival = torch.zeros(4)
    success = torch.zeros(4, dtype=torch.bool)
    sums, last, causes = {}, {}, [set() for _ in range(4)]
    expected_resets = []
    for index, step in enumerate(steps, 1):
        if step["step"] != index:
            raise ValueError("step order changed")
        injected = torch.zeros(4, dtype=torch.bool)
        injected[design["injected_failures"].get(str(index), [])] = True
        if not torch.equal(step["terms"]["fixture_injected_failure"], injected):
            raise ValueError("injected failure schedule changed")
        if bool((injected & ~step["terminated"]).any()):
            raise ValueError("injected failures did not terminate")
        survival += alive.float()
        for key, value in step["metrics"].items():
            if key not in sums:
                sums[key], last[key] = torch.zeros(4), torch.zeros(4)
            sums[key] += torch.where(alive, value, torch.zeros_like(value))
            last[key] = torch.where(alive, value, last[key])
        for term, values in step["terms"].items():
            for world in torch.where(alive & step["terminated"] & values)[0].tolist():
                causes[world].add(term)
        success |= alive & (index == 50) & ~step["terminated"]
        alive &= ~(step["terminated"] | (index == 50))
        if index < 50 and step["dones"].any():
            expected_resets.append((index, torch.where(step["dones"])[0].tolist()))
    if survival.tolist() != design["expected_survival_steps"] or success.int().tolist() != design["expected_success"]:
        raise ValueError("fixture did not exercise planned scoring cases")
    metric_checks = 0
    for world, row in enumerate(rows):
        if (int(row["world_id"]) != world or int(row["success"]) != int(success[world])
                or not np.isclose(float(row["survival_s"]), float(survival[world]) * 0.02)
                or set(filter(None, row["termination_causes"].split(";"))) != causes[world]):
            raise ValueError("CSV retirement accounting differs from trace")
        for key in sums:
            if f"{key}_mean" not in row:
                continue
            for suffix, expected in (("mean", sums[key][world] / survival[world]),
                                     ("terminal", last[key][world])):
                if not np.isclose(float(row[f"{key}_{suffix}"]), float(expected), rtol=1e-6, atol=1e-7):
                    raise ValueError("retired world contributed to CSV metrics")
                metric_checks += 1
    if metric_checks == 0:
        raise ValueError("no score-accounting coverage")
    actual_resets = [(r["after_step"], r["ids"].tolist()) for r in resets]
    if actual_resets != expected_resets:
        raise ValueError("reset does not match evaluator done mask")
    if not all(event in actual_resets for event in [(10, [0]), (20, [0]), (25, [1])]):
        raise ValueError("missing planned active/retired reset")
    isolation_checks = 0
    for reset in resets:
        if reset["physics_index"] != reset["after_step"] * 4:
            raise ValueError("reset physics boundary differs")
        ids = reset["ids"]
        keep = torch.ones(4, dtype=torch.bool)
        keep[ids] = False
        before, after = reset["before"], reset["after"]
        if before.keys() != after.keys():
            raise ValueError("reset telemetry missing")
        for key in before:
            if not torch.equal(before[key][keep], after[key][keep]):
                raise ValueError(f"partial reset changed another world: {key}")
            isolation_checks += 1
            if key.startswith("delay_") and bool(after[key][ids].any()):
                raise ValueError("selected command buffer not cleared")
        if name.startswith("delay_") and not any(k.startswith("delay_") for k in before):
            raise ValueError("delay buffer reset coverage missing")
    lag = CONDITIONS.get(name, CONDITIONS["unchanged"])["delay_steps"]
    last_reset = [0] * 4
    by_boundary = {r["physics_index"]: r["ids"].tolist() for r in resets}
    for index, row in enumerate(physics):
        for world in by_boundary.get(index, []):
            last_reset[world] = index
        for world in range(4):
            target = physics[max(last_reset[world], index - lag)]["desired"][world]
            if not torch.equal(row["ctrl"][world], target):
                raise ValueError("delayed command crosses reset or wrong lag")
    return {"condition": name, "reset_events": len(resets), "reset_sequence": actual_resets,
            "survival_steps": survival.tolist(), "success": success.int().tolist(),
            "metric_values_replayed": metric_checks, "reset_isolation_checks": isolation_checks,
            "physics_control_worlds_replayed": len(physics) * 4,
            "retired_world_reset_verified": True, "failure_at_horizon_verified": True}


def verify_physical(data: dict, baseline: dict, name: str) -> None:
    for key in ("startup_before_intervention", "initial_state", "first_observation"):
        if not equal_tensors(data[key], baseline[key]):
            raise ValueError("initial physical pairing differs")
    if not torch.equal(data["first_action"], baseline["first_action"]):
        raise ValueError("initial action differs")
    if data["actuator_names"] != baseline["actuator_names"] or data["geom_names"] != baseline["geom_names"]:
        raise ValueError("named physical targets differ")
    selected = CONDITIONS[name]
    knees = [i for i, n in enumerate(data["actuator_names"]) if n.split("/")[-1] in KNEES]
    feet = [i for i, n in enumerate(data["geom_names"]) if FOOT_PATTERN.fullmatch(n.split("/")[-1])]
    if len(knees) != 2 or len(feet) != 14:
        raise ValueError("physical target count differs")
    limits = baseline["force_ranges"].clone()
    if selected["knee_cap_nm"] is not None:
        limits[knees] = torch.tensor([-selected["knee_cap_nm"], selected["knee_cap_nm"]], dtype=limits.dtype)
    if not torch.equal(data["force_ranges"], limits):
        raise ValueError("wrong force ranges")
    friction = baseline["startup_before_intervention"]["geom_friction"].clone()
    if selected["foot_friction"] is not None:
        friction[:, feet, 0] = selected["foot_friction"]
    if not torch.equal(data["friction_after_intervention"], friction):
        raise ValueError("wrong friction")
    for step in data["physics"]:
        force = step["force"]
        if not torch.isfinite(force).all() or (force > limits[:, 1] + 1e-4).any() or (force < limits[:, 0] - 1e-4).any():
            raise ValueError("invalid force bounds")


def analyze(run: Path) -> dict:
    design_path = run / "design.json"
    design = json.loads(design_path.read_text())
    for path, digest in design["bindings"].items():
        if sha256(Path(path)) != digest:
            raise ValueError(f"source/input changed: {path}")
    if (run / "original/evaluation.csv").read_bytes() != (run / "unchanged/evaluation.csv").read_bytes():
        raise ValueError("original and unchanged injected fixtures differ")
    baseline = torch.load(run / "unchanged/physical.pt", weights_only=True)
    cells = []
    for name in design["conditions"]:
        cell = run / name
        receipt = json.loads((cell / "receipt.json").read_text())
        if receipt["condition"] != name or receipt["design_sha256"] != sha256(design_path):
            raise ValueError("wrong cell receipt")
        for filename, digest in receipt["artifacts"].items():
            if sha256(cell / filename) != digest:
                raise ValueError("fixture artifact changed")
        data = torch.load(cell / "lifecycle.pt", weights_only=True)
        rows = list(csv.DictReader((cell / "evaluation.csv").open()))
        checked = verify_lifecycle(data, rows, design, name)
        verify_payload(torch.load(cell / "policy.pt", weights_only=True))
        if name != "original":
            physical = torch.load(cell / "physical.pt", weights_only=True)
            verify_physical(physical, baseline, name)
            if len(physical["physics"]) != len(data["physics"]):
                raise ValueError("physical/lifecycle telemetry length differs")
            for left, right in zip(physical["physics"], data["physics"]):
                if not equal_tensors(left, right):
                    raise ValueError("physical/lifecycle traces differ")
        cells.append(checked)
    return {"status": "injected_reset_fixture_pass", "classification": "measured CPU software conformance with injected failures",
            "cells": cells, "episode_rows": len(cells) * 4,
            "original_unchanged_csv_exact_match": True, "policy_immutability_pass": True,
            "confirmation_endpoints_opened": False, "full_evaluation_enabled": False,
            "design_sha256": sha256(design_path), "analyzer_sha256": sha256(Path(__file__)),
            "limitations": ["deliberate termination signals, not naturally failing policy trajectories",
                            "CPU only; GPU and successful early retirement coverage pending",
                            "no robustness, recovery or hardware-transfer conclusion"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.run)
    with args.out.open("x") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "cells"}))
