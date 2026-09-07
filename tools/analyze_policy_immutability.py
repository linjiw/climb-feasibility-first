#!/usr/bin/env python3
"""Replay the complete development inference audit from saved tensor receipts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

from analyze_physics_development import analyze, equal_tensors, sha256
from audit_policy_immutability import verify_payload


def verify(run: Path) -> dict:
    design_path = run / "design.json"
    design = json.loads(design_path.read_text())
    if design.get("policy_immutability_audit") is not True:
        raise ValueError("not an immutability audit")
    lifecycle = analyze(run)
    baseline = None
    cells = []
    for name, previous in design["previous_csv"].items():
        cell = run / name
        trace_path = cell / "policy_immutability.pt"
        data = torch.load(trace_path, map_location="cpu", weights_only=True)
        if data["condition"] != name or data["design_sha256"] != sha256(design_path):
            raise ValueError("wrong trace identity")
        checked = verify_payload(data)
        saved = json.loads((cell / "immutability_verification.json").read_text())
        expected = dict(checked, condition=name, design_sha256=sha256(design_path),
                        trace_sha256=sha256(trace_path), previous_csv_exact_match=True,
                        confirmation_endpoints_opened=False, full_evaluation_enabled=False)
        if saved != expected:
            raise ValueError("immutability receipt does not replay")
        if (sha256(Path(previous["path"])) != previous["sha256"]
                or sha256(cell / "evaluation.csv") != previous["sha256"]):
            raise ValueError("prior development CSV does not match")
        if baseline is None:
            baseline = data["before"]
        for group in ("parameters", "buffers"):
            if not equal_tensors(baseline[group], data["before"][group]):
                raise ValueError("different policy tensors across conditions")
        cells.append(expected)
    if len(cells) != 9:
        raise ValueError("incomplete development audit")
    return {"status": "development_immutability_audit_pass", "cells": cells,
            "inference_calls": sum(cell["forward_calls"] for cell in cells),
            "episode_rows_replayed": lifecycle["episode_rows"],
            "all_previous_csvs_identical": True, "lifecycle_replay": lifecycle,
            "confirmation_endpoints_opened": False, "full_evaluation_enabled": False,
            "limitations": ["same two training clips and development checkpoint replayed",
                            "CPU only; failure/reset and GPU graph coverage pending",
                            "no new independent policy-benefit or transfer evidence"],
            "analyzer_sha256": sha256(Path(__file__))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.run)
    with args.out.open("x") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("cells", "lifecycle_replay")}))
