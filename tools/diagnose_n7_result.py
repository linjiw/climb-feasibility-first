#!/usr/bin/env python3
"""Post-outcome N7 decomposition and evaluation-integrity audit.

This analysis is exploratory.  It never replaces the frozen N7 analyzer or its
decision; it exposes where the deployment delta comes from and recomputes the
generalization guard on genuinely disjoint motions.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OFFSETS_S = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0])
WINDOW_S = 3.0
BOOTSTRAP_DRAWS = 20_000
BOOTSTRAP_SEED = 20260820


def read_list(path: Path) -> list[str]:
    """Read a comment-tolerant motion-name list."""
    return [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]


def read_strat(path: Path, field: str = "survival") -> dict[str, float]:
    """Average a stratified CSV over its non-summary offset rows."""
    grouped: dict[str, list[float]] = {}
    with path.open() as handle:
        for row in csv.DictReader(handle):
            if row["offset_s"] == "mean":
                continue
            grouped.setdefault(row["clip"], []).append(float(row[field]))
    return {name: float(np.mean(values)) for name, values in grouped.items()}


def summarize_delta(
    treatment: dict[str, float], control: dict[str, float], motions: list[str]
) -> dict[str, Any]:
    """Return a motion-paired mean and fixed-bootstrap interval."""
    delta = np.array([treatment[name] - control[name] for name in motions])
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    sample = rng.integers(0, len(motions), (BOOTSTRAP_DRAWS, len(motions)))
    interval = np.quantile(delta[sample].mean(axis=1), (0.025, 0.975))
    return {
        "motions": len(motions),
        "control_mean": float(np.mean([control[name] for name in motions])),
        "treatment_mean": float(np.mean([treatment[name] for name in motions])),
        "paired_delta": float(delta.mean()),
        "motion_bootstrap_95ci": [float(interval[0]), float(interval[1])],
    }


def offset_coverage(root: Path, motions: list[str]) -> dict[str, Any]:
    """Quantify clipping/duplication and temporal coverage in the frozen grid."""
    clipped_rows = 0
    duplicate_rows = 0
    motions_with_duplicates = 0
    covered_frames = 0
    total_frames = 0
    per_motion_coverage = []
    for motion in motions:
        with np.load(root / "bank/amass" / f"{motion}.npz") as archive:
            frames = len(archive["joint_pos"])
            fps = float(np.asarray(archive["fps"]).reshape(-1)[0])
        requested = (OFFSETS_S * fps).astype(int)
        starts = np.minimum(requested, frames - 2)
        clipped_rows += int((starts != requested).sum())
        unique = np.unique(starts)
        duplicates = len(starts) - len(unique)
        duplicate_rows += duplicates
        motions_with_duplicates += int(duplicates > 0)
        covered = np.zeros(frames, dtype=bool)
        window_frames = round(WINDOW_S * fps)
        for start in unique:
            covered[start : min(frames, start + window_frames)] = True
        covered_frames += int(covered.sum())
        total_frames += frames
        per_motion_coverage.append(float(covered.mean()))
    rows = len(motions) * len(OFFSETS_S)
    return {
        "motions": len(motions),
        "scheduled_offset_rows": rows,
        "clipped_rows": clipped_rows,
        "clipped_row_fraction": clipped_rows / rows,
        "duplicate_clipped_rows": duplicate_rows,
        "duplicate_clipped_row_fraction": duplicate_rows / rows,
        "motions_with_duplicate_starts": motions_with_duplicates,
        "duration_weighted_window_coverage": covered_frames / total_frames,
        "mean_motion_window_coverage": float(np.mean(per_motion_coverage)),
        "minimum_motion_window_coverage": float(np.min(per_motion_coverage)),
    }


def analyze(root: Path) -> dict[str, Any]:
    """Build the complete exploratory N7 audit."""
    n7 = root / "reports/N7"
    cells = {
        "keep_raw": read_strat(n7 / "keep_policy_raw_reference_flagged99.csv"),
        "keep_repaired": read_strat(
            n7 / "keep_policy_repaired_reference_flagged99.csv"
        ),
        "repair_raw": read_strat(n7 / "repair_policy_raw_reference_flagged99.csv"),
        "repair_repaired": read_strat(
            n7 / "repair_policy_repaired_reference_flagged99.csv"
        ),
    }
    manifest = json.loads((root / "reports/repaired800/manifest.json").read_text())
    by_stratum: dict[str, list[dict[str, float]]] = {}
    motion_rows = []
    for record in manifest["clips"]:
        if record["stratum"] == "original":
            continue
        name = record["name"]
        census = record["census"]
        row = {
            "deployment_delta": cells["repair_repaired"][name]
            - cells["keep_raw"][name],
            "training_transfer_delta": cells["repair_raw"][name]
            - cells["keep_raw"][name],
            "reference_only_delta": cells["keep_repaired"][name]
            - cells["keep_raw"][name],
        }
        row["interaction"] = (
            cells["repair_repaired"][name]
            - cells["repair_raw"][name]
            - row["reference_only_delta"]
        )
        row.update(
            {
                "infeasible_before": float(census["infeasible_frac_before"]),
                "infeasible_after": float(census["infeasible_frac_after"]),
                "offset_max_m": float(census["offset_max_m"]),
            }
        )
        by_stratum.setdefault(record["stratum"], []).append(row)
        motion_rows.append(row)

    stratum_summary = {}
    fields = (
        "deployment_delta",
        "training_transfer_delta",
        "reference_only_delta",
        "interaction",
        "infeasible_before",
        "infeasible_after",
        "offset_max_m",
    )
    for stratum, rows in sorted(by_stratum.items()):
        stratum_summary[stratum] = {
            "motions": len(rows),
            **{
                f"mean_{field}": float(np.mean([row[field] for row in rows]))
                for field in fields
            },
        }

    flagged = read_list(root / "bank/tiers/tier_800_flagged99.txt")
    deployment = summarize_delta(
        cells["repair_repaired"], cells["keep_raw"], flagged
    )
    training = summarize_delta(cells["repair_raw"], cells["keep_raw"], flagged)
    reference = summarize_delta(
        cells["keep_repaired"], cells["keep_raw"], flagged
    )
    interaction = deployment["paired_delta"] - training["paired_delta"] - reference[
        "paired_delta"
    ]

    heldout = read_list(root / "bank/tiers/heldout100.txt")
    train = set(read_list(root / "bank/tiers/tier_800.txt"))
    feasibility = {}
    with (root / "reports/feasibility_e3/feasibility.csv").open() as handle:
        for row in csv.DictReader(handle):
            feasibility[row["clip"]] = float(row["infeasible_frac"])
    keep_heldout = read_strat(
        root / "reports/E_HYG_uniform-amass800-s1_heldout100_strat.csv"
    )
    repair_heldout = read_strat(n7 / "repair_policy_heldout100.csv")
    populations = {
        "all100": heldout,
        "disjoint92": [name for name in heldout if name not in train],
        "feasible71": [name for name in heldout if feasibility[name] <= 0.10],
        "feasible_disjoint68": [
            name
            for name in heldout
            if feasibility[name] <= 0.10 and name not in train
        ],
    }
    overlap = sorted(set(heldout) & train)

    deployment_delta = np.array(
        [cells["repair_repaired"][name] - cells["keep_raw"][name] for name in flagged]
    )
    return {
        "analysis": "exploratory N7 post-outcome audit; frozen decision unchanged",
        "decomposition": {
            "deployment_repair_repaired_minus_keep_raw": deployment,
            "training_transfer_repair_raw_minus_keep_raw": training,
            "reference_only_keep_repaired_minus_keep_raw": reference,
            "policy_by_reference_interaction": interaction,
            "identity_check": float(
                deployment["paired_delta"]
                - training["paired_delta"]
                - reference["paired_delta"]
                - interaction
            ),
        },
        "repair_heterogeneity": {
            "by_manifest_stratum": stratum_summary,
            "motions_improved_tied_worse": {
                "improved": int((deployment_delta > 0).sum()),
                "tied": int((deployment_delta == 0).sum()),
                "worse": int((deployment_delta < 0).sum()),
            },
        },
        "heldout_integrity": {
            "training_overlap_count": len(overlap),
            "training_overlap": overlap,
            "populations": {
                name: summarize_delta(repair_heldout, keep_heldout, motions)
                for name, motions in populations.items()
            },
        },
        "offset_protocol": {
            "flagged99": offset_coverage(root, flagged),
            "heldout100": offset_coverage(root, heldout),
            "feasible_hard20": offset_coverage(
                root, read_list(root / "bank/tiers/fgas_feasible_hard20.txt")
            ),
            "zs_ground60": offset_coverage(
                root, read_list(root / "bank/tiers/zs_ground_feasible.txt")
            ),
        },
        "scope": {
            "classification": "post-hoc exploratory",
            "sealed_n7_result_replaced": False,
            "motion_bootstrap_is_not_training_seed_uncertainty": True,
        },
    }


def synthetic() -> None:
    """Exercise the paired summary on benefit and null branches."""
    names = [f"m{i}" for i in range(20)]
    control = {name: 0.4 for name in names}
    treatment = {name: 0.5 for name in names}
    result = summarize_delta(treatment, control, names)
    assert np.isclose(result["paired_delta"], 0.1)
    assert result["motion_bootstrap_95ci"][0] > 0.0
    assert summarize_delta(control, control, names)["paired_delta"] == 0.0
    print("N7 post-outcome diagnostic synthetic branches pass")


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
