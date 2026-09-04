#!/usr/bin/env python3
"""Build an outcome-blind feasible-hard stratum for the Phase-G panel.

Hardness here means high reference-side dynamic demand, not low policy survival.
The score is a rank average over the seven features already declared by
``tools/screen_bank.py`` and is computed against the full eligible population.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

FEATURES = (
    ("required_mu_p95", 1.0),
    ("vert_force_bw_max", 1.0),
    ("contact_switch_rate", 1.0),
    ("flight_phase_frac", 1.0),
    ("nonfoot_ground_frac", 1.0),
    ("angmom_peak", 1.0),
    ("support_margin_mean", -1.0),
)
MIN_FRAMES = 250
MAX_INFEASIBLE_FRAC = 0.10
MAX_AIRBORNE_FRAC = 0.10


def sha256_file(path: Path) -> str:
    """Return the SHA-256 identity of one input or output."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile_ranks(values: np.ndarray) -> np.ndarray:
    """Return deterministic average-tie percentile ranks in [0, 1]."""
    order = np.argsort(values, kind="stable")
    sorted_values = values[order]
    ranks = np.empty(values.size, dtype=np.float64)
    start = 0
    while start < values.size:
        stop = start + 1
        while stop < values.size and sorted_values[stop] == sorted_values[start]:
            stop += 1
        ranks[order[start:stop]] = 0.5 * (start + stop - 1)
        start = stop
    return ranks / max(values.size - 1, 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, default=Path("reports/g_segment/panel/panel.txt"))
    parser.add_argument("--features", type=Path, default=Path("reports/features_amass.csv"))
    parser.add_argument(
        "--feasibility",
        type=Path,
        default=Path("reports/feasibility_all/feasibility.csv"),
    )
    parser.add_argument("--hard-count", type=int, default=25)
    parser.add_argument(
        "--out", type=Path, default=Path("reports/g_segment/panel/strata.csv")
    )
    args = parser.parse_args()

    panel = [line.strip() for line in args.panel.read_text().splitlines() if line.strip()]
    feature_rows = {row["name"]: row for row in csv.DictReader(args.features.open())}
    feasibility_rows = {
        row["clip"]: row for row in csv.DictReader(args.feasibility.open())
    }
    if set(feature_rows) != set(feasibility_rows):
        raise ValueError("feature and feasibility tables contain different clip identities")
    if not 0 < args.hard_count < len(panel):
        raise ValueError("hard-count must be between zero and panel size")

    eligible = [
        name
        for name, row in feasibility_rows.items()
        if int(row["frames"]) >= MIN_FRAMES
        and float(row["infeasible_frac"]) <= MAX_INFEASIBLE_FRAC
        and float(row["airborne_frac"]) <= MAX_AIRBORNE_FRAC
    ]
    missing = set(panel) - set(eligible)
    if missing:
        raise ValueError(f"panel contains ineligible clips: {sorted(missing)[:3]}")

    component: dict[str, dict[str, float]] = {name: {} for name in eligible}
    for feature, sign in FEATURES:
        values = np.array(
            [sign * float(feature_rows[name][feature]) for name in eligible],
            dtype=np.float64,
        )
        ranks = percentile_ranks(values)
        for name, rank in zip(eligible, ranks, strict=True):
            component[name][feature] = float(rank)
    score = {
        name: float(np.mean(list(component[name].values()))) for name in eligible
    }
    ordered_panel = sorted(panel, key=lambda name: (-score[name], name))
    hard = set(ordered_panel[: args.hard_count])

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["clip", "stratum", "reference_difficulty_score", *[key for key, _ in FEATURES]]
    with args.out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for name in sorted(panel):
            writer.writerow({
                "clip": name,
                "stratum": "feasible_hard_reference" if name in hard else "feasible_remainder",
                "reference_difficulty_score": f"{score[name]:.12g}",
                **{key: f"{component[name][key]:.12g}" for key, _ in FEATURES},
            })
    manifest = {
        "schema_version": "g_segment_eval_strata/1",
        "classification": "pending; outcome-blind reference-only stratification",
        "definition": (
            f"top {args.hard_count}/{len(panel)} panel clips by mean global percentile rank "
            "over seven pre-existing dynamic-demand features; this is reference-hardness, "
            "not observed policy hardness"
        ),
        "eligibility": {
            "frames_min": MIN_FRAMES,
            "infeasible_frac_max": MAX_INFEASIBLE_FRAC,
            "airborne_frac_max": MAX_AIRBORNE_FRAC,
            "population": len(eligible),
        },
        "features": [{"name": key, "direction": sign} for key, sign in FEATURES],
        "counts": {
            "feasible_hard_reference": len(hard),
            "feasible_remainder": len(panel) - len(hard),
        },
        "inputs": {
            "panel_sha256": sha256_file(args.panel),
            "features_sha256": sha256_file(args.features),
            "feasibility_sha256": sha256_file(args.feasibility),
        },
        "output_sha256": sha256_file(args.out),
        "builder_sha256": sha256_file(Path(__file__).resolve()),
    }
    manifest_path = args.out.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"counts": manifest["counts"], "output_sha256": manifest["output_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
