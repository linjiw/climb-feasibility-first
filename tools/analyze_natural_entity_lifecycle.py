#!/usr/bin/env python3
"""Verify natural lifecycle with environment and command-driven entity resets."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import torch

from analyze_physics_development import equal_tensors, sha256
from analyze_physics_reset_fixture import verify_physical
from eval_natural_lifecycle import verify_policy
from physics_sensitivity import CONDITIONS


def verify_lifecycle(data: dict, rows: list[dict], conditions: list[dict], name: str) -> dict:
    count = len(conditions)
    horizons = torch.tensor([r["horizon_steps"] for r in conditions])
    steps, resets, physics = data["steps"], data["resets"], data["physics"]
    if not steps or len(steps) > int(horizons.max()) or len(physics) != len(steps) * 4 or len(rows) != count:
        raise ValueError("incomplete natural lifecycle trace")
    alive = torch.ones(count, dtype=torch.bool)
    success = torch.zeros(count, dtype=torch.bool)
    survival = torch.zeros(count)
    sums, last, causes = {}, {}, [set() for _ in range(count)]
    expected_resets, early_success, failure_events = [], [], []
    retired_before = {}
    for index, step in enumerate(steps, 1):
        if step["step"] != index or step["terms"]["fixture_injected_failure"].any():
            raise ValueError("step mismatch or injected failure in natural fixture")
        retired_before[index] = ~alive.clone()
        survival += alive.float()
        for key, value in step["metrics"].items():
            if key not in sums:
                sums[key], last[key] = torch.zeros(count), torch.zeros(count)
            sums[key] += torch.where(alive, value, torch.zeros_like(value))
            last[key] = torch.where(alive, value, last[key])
        failed = alive & step["terminated"]
        for world in torch.where(failed)[0].tolist():
            failure_events.append({"step": index, "world": world})
        for term, values in step["terms"].items():
            for world in torch.where(failed & values)[0].tolist():
                causes[world].add(term)
        reached = index >= horizons
        completed = alive & reached & ~step["terminated"]
        for world in torch.where(completed & (horizons < horizons.max()))[0].tolist():
            early_success.append({"step": index, "world": world})
        success |= completed
        alive &= ~(step["terminated"] | reached)
        if not alive.any() and index != len(steps):
            raise ValueError("evaluator continued after all worlds retired")
        if alive.any() and step["dones"].any():
            expected_resets.append((index, torch.where(step["dones"])[0].tolist()))
    if alive.any():
        raise ValueError("evaluator stopped with active worlds")
    metric_values = 0
    for world, row in enumerate(rows):
        if (int(row["world_id"]) != world or row["condition_id"] != conditions[world]["condition_id"]
                or int(row["success"]) != int(success[world])
                or not np.isclose(float(row["survival_s"]), float(survival[world]) * .02)
                or set(filter(None, row["termination_causes"].split(";"))) != causes[world]):
            raise ValueError("natural retirement CSV disagrees with trace")
        for key in sums:
            if f"{key}_mean" not in row:
                continue
            for suffix, value in (("mean", sums[key][world] / survival[world]), ("terminal", last[key][world])):
                if not np.isclose(float(row[f"{key}_{suffix}"]), float(value), rtol=1e-6, atol=1e-7):
                    raise ValueError("retired world changed score accounting")
                metric_values += 1
    if not metric_values:
        raise ValueError("missing native metrics")
    if [(r["after_step"], r["ids"].tolist()) for r in resets] != expected_resets:
        raise ValueError("reset events do not match done masks")
    retired_resets = 0
    for reset in resets:
        ids = reset["ids"]
        retired_resets += int(retired_before[reset["after_step"]][ids].sum())
        if reset["physics_index"] != 4 * reset["after_step"]:
            raise ValueError("wrong reset physics boundary")
        keep = torch.ones(count, dtype=torch.bool)
        keep[ids] = False
        before, after = reset["before"], reset["after"]
        if before.keys() != after.keys():
            raise ValueError("incomplete reset state")
        for key in before:
            if not torch.equal(before[key][keep], after[key][keep]):
                raise ValueError("partial reset changed another world")
            if key.startswith("delay_") and after[key][ids].any():
                raise ValueError("selected delay history not cleared")
        if name.startswith("delay_") and not any(k.startswith("delay_") for k in before):
            raise ValueError("missing delay reset evidence")
    lag = CONDITIONS.get(name, CONDITIONS["unchanged"])["delay_steps"]
    last_reset = [0] * count
    entity_resets = data["entity_resets"]
    boundaries = {}
    previous_boundary = 0
    for event in entity_resets:
        boundary = event["physics_index"]
        if boundary != event["step"] * 4 or boundary < previous_boundary:
            raise ValueError("entity reset boundary/order mismatch")
        previous_boundary = boundary
        if event["source"] not in ("environment_reset", "motion_resample"):
            raise ValueError("unknown entity reset source")
        ids = event["ids"]
        keep = torch.ones(count, dtype=torch.bool)
        keep[ids] = False
        before, after = event["before"], event["after"]
        if before.keys() != after.keys():
            raise ValueError("entity reset state missing")
        for key in before:
            if not torch.equal(before[key][keep], after[key][keep]):
                raise ValueError("entity reset changed another world")
            if key.startswith("delay_") and after[key][ids].any():
                raise ValueError("entity reset did not clear command history")
        boundaries.setdefault(boundary, []).extend(ids.tolist())
    for event in resets:
        matching = set()
        for entity in entity_resets:
            if entity["source"] == "environment_reset" and entity["physics_index"] == event["physics_index"]:
                matching.update(entity["ids"].tolist())
        if not set(event["ids"].tolist()).issubset(matching):
            raise ValueError("environment reset has no entity reset evidence")
    for index, record in enumerate(physics):
        for world in boundaries.get(index, []):
            last_reset[world] = index
        for world in range(count):
            if not torch.equal(record["ctrl"][world], physics[max(last_reset[world], index - lag)]["desired"][world]):
                raise ValueError("command delay violates world reset boundary")
    return {"condition": name, "episode_rows": count, "control_steps": len(steps),
            "successes": int(success.sum()), "natural_failures": failure_events,
            "early_successes": early_success, "partial_reset_events": len(resets),
            "already_retired_world_resets": retired_resets, "native_metric_values_replayed": metric_values,
            "survival_steps": survival.tolist(), "success_flags": success.int().tolist(),
            "entity_reset_events": len(entity_resets),
            "motion_resample_events": sum(e["source"] == "motion_resample" for e in entity_resets)}


def analyze(run: Path) -> dict:
    design_path = run / "design.json"
    design = json.loads(design_path.read_text())
    if design["stage"] != "natural_lifecycle_cpu" or design["injected_failures"] != {}:
        raise ValueError("wrong natural development design")
    for path, digest in design["bindings"].items():
        if sha256(Path(path)) != digest:
            raise ValueError(f"source/input changed: {path}")
    root = Path(design["root"])
    clips = Path(design["evaluator_arguments"]["clips"]).read_text().splitlines()
    if set(clips) & set((root / "reports/g_segment/panel/panel.txt").read_text().splitlines()):
        raise ValueError("held-out clip in natural development batch")
    conditions = json.loads(Path(design["evaluator_arguments"]["conditions"]).read_text())["conditions"]
    if (run / "original/evaluation.csv").read_bytes() != (run / "unchanged/evaluation.csv").read_bytes():
        raise ValueError("original/unchanged CSV mismatch")
    baseline = torch.load(run / "unchanged/physical.pt", weights_only=True)
    cells = []
    previous_csv_hashes = {}
    for name in design["conditions"]:
        cell = run / name
        receipt = json.loads((cell / "receipt.json").read_text())
        if receipt["condition"] != name or receipt["design_sha256"] != sha256(design_path):
            raise ValueError("cell receipt identity mismatch")
        for filename, digest in receipt["artifacts"].items():
            if sha256(cell / filename) != digest:
                raise ValueError("cell artifact changed")
        data = torch.load(cell / "lifecycle.pt", weights_only=True)
        if data["condition"] != name or data["design_sha256"] != sha256(design_path):
            raise ValueError("lifecycle identity mismatch")
        checked = verify_lifecycle(data, list(csv.DictReader((cell / "evaluation.csv").open())), conditions, name)
        policy = verify_policy(torch.load(cell / "policy.pt", weights_only=True), len(data["steps"]))
        if policy != receipt["policy"]:
            raise ValueError("policy immutability receipt mismatch")
        if name != "original":
            physical = torch.load(cell / "physical.pt", weights_only=True)
            verify_physical(physical, baseline, name)
            if len(physical["physics"]) != len(data["physics"]) or any(
                    not equal_tensors(a, b) for a, b in zip(physical["physics"], data["physics"])):
                raise ValueError("physical/lifecycle trace mismatch")
        previous = Path(design["previous_run"]) / name / "evaluation.csv"
        if previous.read_bytes() != (cell / "evaluation.csv").read_bytes():
            raise ValueError("entity instrumentation changed prior CSV")
        previous_csv_hashes[str(previous)] = sha256(previous)
        cells.append(checked)
    covered = all(c["natural_failures"] and c["early_successes"] and c["partial_reset_events"] for c in cells)
    return {"status": "natural_entity_lifecycle_pass" if covered else "natural_entity_lifecycle_valid_but_coverage_incomplete",
            "classification": "measured development lifecycle; selected training clips, single development policy",
            "cells": cells, "episode_rows": sum(c["episode_rows"] for c in cells),
            "partial_reset_events": sum(c["partial_reset_events"] for c in cells),
            "entity_reset_events": sum(c["entity_reset_events"] for c in cells),
            "motion_resample_events": sum(c["motion_resample_events"] for c in cells),
            "previous_csv_hashes": previous_csv_hashes, "previous_csvs_exact_match": True,
            "natural_failure_rows": sum(len(c["natural_failures"]) for c in cells),
            "early_success_rows": sum(len(c["early_successes"]) for c in cells),
            "original_unchanged_csv_exact_match": True, "policy_immutability_pass": True,
            "confirmation_endpoints_opened": False, "full_evaluation_enabled": False,
            "design_sha256": sha256(design_path), "analyzer_sha256": sha256(Path(__file__)),
            "limitations": ["CPU only; GPU validation pending", "no independent robustness or policy-benefit estimate",
                            "lifecycle uses isolated reset correction; full S1 adapter/freeze pending"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.run)
    with args.out.open("x") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "cells"}))
