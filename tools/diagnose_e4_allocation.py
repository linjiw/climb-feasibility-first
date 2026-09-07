#!/usr/bin/env python3
"""Replay sealed sampler snapshots; never load policy evaluation endpoints."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from climb.segment_curriculum import segment_sampling_probabilities
from check_g_seed1_manipulation import evaluate, sha256_file


def probabilities(progress: np.ndarray, mass: np.ndarray, clips: np.ndarray,
                  floor: float) -> np.ndarray:
    return segment_sampling_probabilities(
        torch.ones(len(mass), dtype=torch.float64),
        torch.ones(len(mass), dtype=torch.float64),
        torch.tensor(mass, dtype=torch.float64), exploration_ratio=0.4,
        difficulty_power=0.0,
        ranking_weight=torch.tensor(progress + floor, dtype=torch.float64),
        clip_ids=torch.tensor(clips, dtype=torch.long),
        max_unit_probability=0.05, max_clip_probability=0.25,
    ).numpy()


def summary(p: np.ndarray, base: np.ndarray) -> dict:
    return {"tv": float(np.abs(p - base).sum() / 2),
            "entropy_effective_units": float(np.exp(-(p[p > 0] * np.log(p[p > 0])).sum())),
            "top1_unit_mass": float(p.max())}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source = ROOT / "reports/g_segment/confirmation/seed1/manipulation_result.json"
    result = json.loads(source.read_text())
    reproduced = evaluate(Path(result["inputs"]["G1"]["run_dir"]),
                          Path(result["inputs"]["G2"]["run_dir"]),
                          ROOT / "plan/G2_CALIBRATION_GRID.json",
                          ROOT / "reports/g_segment/calibration/result.json")
    if result != reproduced:
        raise ValueError("seed-1 decision changed")
    table = json.loads((ROOT / "reports/g_segment/unit_table.json").read_text())
    units = table["admissible_units"]
    mass = np.array([r["deployment_mass"] for r in units], dtype=float)
    clips = np.array([r["clip_id"] for r in units])
    base = mass / mass.sum()
    snapshots = []
    for path in sorted(Path(result["inputs"]["G2"]["run_dir"]).glob("model_*_segment.json")):
        ledger = json.loads(path.read_text())
        if ledger["iteration"] < 400:
            continue
        seg = ledger["segment"]
        progress = np.array(seg["learning_progress"], dtype=float)
        observed = np.array(seg["probabilities"], dtype=float)
        replay = probabilities(progress, mass, clips, 0.05)
        error = float(np.abs(observed - replay).max())
        if error > 1e-10:
            raise ValueError(f"snapshot does not replay: {path}, error={error}")
        mean = float(base @ progress)
        mad = float(base @ np.abs(progress - mean))
        uncapped_tv = 0.6 * mad / (2 * (mean + 0.05))
        candidates = {}
        for floor in (0.0, 0.001, 0.005, 0.01, 0.02, 0.05):
            candidates[f"absolute_{floor:g}"] = summary(probabilities(progress, mass, clips, floor), base)
        for multiplier in (0.5, 1.0, 2.0):
            p = probabilities(progress, mass, clips, multiplier * mean)
            scaled = probabilities(progress * 1e-4, mass, clips, multiplier * mean * 1e-4)
            candidates[f"relative_{multiplier:g}"] = {
                **summary(p, base), "scale_invariance_max_error": float(np.abs(p - scaled).max())}
        snapshots.append({
            "iteration": ledger["iteration"], "ledger_sha256": sha256_file(path),
            "progress_prior_weighted_mean": mean, "progress_weighted_mad": mad,
            "floor_share_of_focus_normalizer": 0.05 / (mean + 0.05),
            "observed": summary(observed, base), "replay_max_probability_error": error,
            "uncapped_closed_form_tv": uncapped_tv,
            "cap_effect_on_tv": uncapped_tv - summary(replay, base)["tv"],
            "counterfactual_fixed_snapshot": candidates,
        })
    snapshots.sort(key=lambda r: r["iteration"])
    aggregate = {}
    for name in snapshots[0]["counterfactual_fixed_snapshot"]:
        cells = [r["counterfactual_fixed_snapshot"][name] for r in snapshots]
        aggregate[name] = {
            "mean_tv": float(np.mean([r["tv"] for r in cells])),
            "min_tv": min(r["tv"] for r in cells), "max_tv": max(r["tv"] for r in cells),
            "min_entropy_effective_units": min(r["entropy_effective_units"] for r in cells),
            "max_top1_unit_mass": max(r["top1_unit_mass"] for r in cells),
        }
    payload = {
        "schema_version": "e4_allocation_diagnosis/1",
        "classification": "measured sampler replay + exploratory fixed-snapshot counterfactuals",
        "frozen_status": result["status"], "policy_endpoints_opened": False,
        "seed1_result_sha256": sha256_file(source), "tool_sha256": sha256_file(Path(__file__)),
        "mechanism": "Before caps, TV=(1-rho)*E_base|g-E_base(g)|/[2*(E_base(g)+floor)].",
        "limitation": "Counterfactual weights hold recorded learning history fixed; they are not alternative training outcomes.",
        "snapshots": snapshots, "counterfactual_summary": aggregate,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as handle:
        json.dump(payload, handle, indent=1, allow_nan=False)
        handle.write("\n")
    print(json.dumps(aggregate, indent=1))


if __name__ == "__main__":
    main()
