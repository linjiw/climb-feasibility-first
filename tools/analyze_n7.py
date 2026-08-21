#!/usr/bin/env python3
"""Frozen N7 repair-versus-keep/prune analysis."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_DRAWS = 20_000
BOOTSTRAP_SEED = 20260820


def read_strat(path: Path) -> dict[str, float]:
    values: dict[str, list[float]] = {}
    with path.open() as handle:
        for row in csv.DictReader(handle):
            if row["offset_s"] == "mean":
                continue
            values.setdefault(row["clip"], []).append(float(row["survival"]))
    return {clip: float(np.mean(rows)) for clip, rows in values.items()}


def read_list(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def paired_delta(
    treatment: dict[str, float], control: dict[str, float], clips: list[str]
) -> dict[str, Any]:
    missing = [clip for clip in clips if clip not in treatment or clip not in control]
    if missing:
        raise ValueError(f"missing {len(missing)} motions, e.g. {missing[:3]}")
    differences = np.array([treatment[clip] - control[clip] for clip in clips])
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = np.empty(BOOTSTRAP_DRAWS)
    for index in range(BOOTSTRAP_DRAWS):
        sample = rng.integers(0, len(clips), len(clips))
        draws[index] = differences[sample].mean()
    interval = np.quantile(draws, (0.025, 0.975))
    return {
        "motions": len(clips),
        "control_mean": float(np.mean([control[clip] for clip in clips])),
        "treatment_mean": float(np.mean([treatment[clip] for clip in clips])),
        "paired_delta": float(differences.mean()),
        "motion_bootstrap_95ci": [float(interval[0]), float(interval[1])],
    }


def analyze(root: Path) -> dict[str, Any]:
    n7 = root / "reports/N7"
    flagged = read_list(root / "bank/tiers/tier_800_flagged99.txt")
    heldout = read_list(root / "bank/tiers/heldout100.txt")
    ground = read_list(root / "bank/tiers/zs_ground_feasible.txt")

    keep_raw = read_strat(n7 / "keep_policy_raw_reference_flagged99.csv")
    keep_repaired = read_strat(n7 / "keep_policy_repaired_reference_flagged99.csv")
    repair_raw = read_strat(n7 / "repair_policy_raw_reference_flagged99.csv")
    repair_repaired = read_strat(n7 / "repair_policy_repaired_reference_flagged99.csv")
    deployment = paired_delta(repair_repaired, keep_raw, flagged)
    training_transfer = paired_delta(repair_raw, keep_raw, flagged)
    reference_only = paired_delta(keep_repaired, keep_raw, flagged)

    keep_ref_effect = np.array(
        [keep_repaired[clip] - keep_raw[clip] for clip in flagged]
    )
    repair_ref_effect = np.array(
        [repair_repaired[clip] - repair_raw[clip] for clip in flagged]
    )
    interaction = float((repair_ref_effect - keep_ref_effect).mean())

    keep_heldout = read_strat(
        root / "reports/E_HYG_uniform-amass800-s1_heldout100_strat.csv"
    )
    repair_heldout = read_strat(n7 / "repair_policy_heldout100.csv")
    heldout_delta = paired_delta(repair_heldout, keep_heldout, heldout)

    keep_ground = read_strat(root / "reports/E_HYG_uniform-amass800-s1_zsg_strat.csv")
    prune_ground = read_strat(root / "reports/E_HYG_uniform-amass800p-s1_zsg_strat.csv")
    repair_ground = read_strat(n7 / "repair_policy_zs_ground.csv")
    ground_keep = paired_delta(repair_ground, keep_ground, ground)
    ground_prune = paired_delta(repair_ground, prune_ground, ground)

    primary_pass = (
        float(deployment["paired_delta"]) >= 0.05
        and float(deployment["motion_bootstrap_95ci"][0]) > 0.0
    )
    no_regression = float(heldout_delta["paired_delta"]) >= -0.03
    coverage = (
        float(ground_keep["paired_delta"]) >= -0.03
        and float(ground_prune["paired_delta"]) >= 0.03
    )
    return {
        "analysis": "N7 repair-all versus keep/prune, seed 1",
        "flagged99": {
            "deployment_repair_vs_keep": deployment,
            "training_transfer_on_raw_references": training_transfer,
            "reference_only_under_keep_policy": reference_only,
            "policy_by_reference_interaction": interaction,
        },
        "heldout100": heldout_delta,
        "zs_ground_feasible": {
            "repair_vs_keep": ground_keep,
            "repair_vs_prune": ground_prune,
        },
        "decision": {
            "repair_benefit": primary_pass,
            "no_heldout_regression": no_regression,
            "coverage_preserved_vs_prune": coverage,
            "overall_pass": primary_pass and no_regression and coverage,
            "rules": {
                "primary": "flagged99 deployment delta >= 0.05 and motion CI low > 0",
                "no_regression": "heldout100 delta >= -0.03",
                "coverage": "repair-keep >= -0.03 and repair-prune >= 0.03 on zs_ground",
            },
            "scope": "one seed; motion bootstrap is not seed uncertainty",
        },
    }


def synthetic() -> None:
    clips = [f"c{i}" for i in range(20)]
    keep = {clip: 0.4 for clip in clips}
    repair = {clip: 0.6 for clip in clips}
    result = paired_delta(repair, keep, clips)
    assert result["paired_delta"] == np.float64(0.2)
    assert result["motion_bootstrap_95ci"][0] > 0.0
    null = paired_delta(keep, keep, clips)
    assert null["paired_delta"] == 0.0
    print("N7 synthetic analysis: benefit and null branches pass")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    if args.synthetic:
        synthetic()
        return
    result = analyze(args.root)
    rendered = json.dumps(result, indent=1)
    print(rendered)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n")


if __name__ == "__main__":
    main()
