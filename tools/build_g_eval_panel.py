#!/usr/bin/env python3
"""Build the Phase-G disjoint evaluation panel before any Phase-G outcome exists.

The panel is selected from reference-only inputs (the bank-invariant clean tier
and the frozen feasibility screen). It never reads a policy, a simulator
outcome, or a training log. Every exclusion list is bound by name *and* by the
SHA-256 of the motion file so that renamed-but-identical clips cannot leak in
(the N7 audit found eight `heldout100` motions inside `tier_800`).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

SEED = 20260827
PANEL_SIZE = 100
MIN_FRAMES = 250  # 5.0 s at 50 Hz: seven 3.0 s windows need room to phase
MAX_INFEASIBLE_FRAC = 0.10
MAX_AIRBORNE_FRAC = 0.10

EXCLUSION_LISTS = {
    "tier_800": "bank/tiers/tier_800.txt",
    "tier_800_pruned": "bank/tiers/tier_800_pruned.txt",
    "tier_800_flagged99": "bank/tiers/tier_800_flagged99.txt",
    "tier_mixed100": "bank/tiers/tier_mixed100.txt",
    "heldout100": "bank/tiers/heldout100.txt",
    "dfrp_v1_exact_panel": "reports/dfrp_v1_exact_panel/clips.txt",
    "segment_v2_mechanism_panel": "reports/segment_v2_smoke/clips.txt",
}
EXCLUSION_BANKS = (
    "bank/amass",
    "bank/amass_repaired800",
    "bank/amass_repaired800_certified",
    "bank/dfrp_v1_exact_panel",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_list(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--bank", type=Path, default=Path("bank/amass"))
    parser.add_argument("--clean", type=Path, default=Path("bank/tiers/clean.txt"))
    parser.add_argument(
        "--screen", type=Path, default=Path("reports/feasibility_all/feasibility.csv")
    )
    parser.add_argument("--out-dir", type=Path, default=Path("reports/g_segment/panel"))
    parser.add_argument("--size", type=int, default=PANEL_SIZE)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    root = args.root.resolve()

    clean = read_list(root / args.clean)
    screen = {}
    with (root / args.screen).open() as handle:
        for row in csv.DictReader(handle):
            screen[row["clip"]] = row

    excluded_names: dict[str, set[str]] = {}
    for label, rel in EXCLUSION_LISTS.items():
        excluded_names[label] = set(read_list(root / rel))
    excluded_union = set().union(*excluded_names.values())

    # Hash every motion file in every exclusion list, in every bank variant
    # where it exists, so repaired/certified byte-variants are excluded too.
    excluded_hashes: dict[str, str] = {}
    for name in sorted(excluded_union):
        for bank in EXCLUSION_BANKS:
            file = root / bank / f"{name}.npz"
            if file.exists():
                excluded_hashes[sha256_file(file)] = f"{bank}/{name}.npz"

    candidates = []
    rejected = {"not_screened": 0, "excluded_by_name": 0, "short": 0, "infeasible": 0,
                "airborne": 0, "missing_file": 0, "excluded_by_hash": 0}
    for name in clean:
        row = screen.get(name)
        if row is None:
            rejected["not_screened"] += 1
            continue
        if name in excluded_union:
            rejected["excluded_by_name"] += 1
            continue
        if int(row["frames"]) < MIN_FRAMES:
            rejected["short"] += 1
            continue
        if float(row["infeasible_frac"]) > MAX_INFEASIBLE_FRAC:
            rejected["infeasible"] += 1
            continue
        if float(row["airborne_frac"]) > MAX_AIRBORNE_FRAC:
            rejected["airborne"] += 1
            continue
        file = root / args.bank / f"{name}.npz"
        if not file.exists():
            rejected["missing_file"] += 1
            continue
        candidates.append(name)

    rng = np.random.default_rng(args.seed)
    order = rng.permutation(len(candidates))
    panel = []
    panel_hashes = {}
    for index in order:
        name = candidates[index]
        digest = sha256_file(root / args.bank / f"{name}.npz")
        if digest in excluded_hashes:
            rejected["excluded_by_hash"] += 1
            continue
        panel.append(name)
        panel_hashes[name] = digest
        if len(panel) == args.size:
            break
    if len(panel) != args.size:
        raise SystemExit(f"only {len(panel)} admissible clips for a {args.size}-clip panel")
    panel.sort()

    # Fail closed on disjointness, by name and by content hash.
    name_overlap = {label: sorted(set(panel) & names) for label, names in excluded_names.items()}
    hash_overlap = sorted(h for h in panel_hashes.values() if h in excluded_hashes)
    if any(name_overlap.values()) or hash_overlap:
        raise SystemExit(f"panel is not disjoint: {name_overlap} {hash_overlap}")

    out = root / args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    panel_txt = out / "panel.txt"
    panel_txt.write_text("\n".join(panel) + "\n")
    frames = [int(screen[n]["frames"]) for n in panel]
    manifest = {
        "schema_version": "g_segment_eval_panel/1",
        "classification": "outcome-blind Phase-G evaluation panel; reference-only inputs",
        "selection_rule": (
            f"uniform draw (NumPy seed {args.seed}) from bank/tiers/clean.txt clips with "
            f"frames >= {MIN_FRAMES}, infeasible_frac <= {MAX_INFEASIBLE_FRAC}, "
            f"airborne_frac <= {MAX_AIRBORNE_FRAC}, not in any exclusion list by name, "
            "and not matching any excluded motion file by SHA-256"
        ),
        "size": len(panel),
        "candidates": len(candidates),
        "rejected": rejected,
        "inputs": {
            "clean_list": {"path": str(args.clean), "sha256": sha256_file(root / args.clean)},
            "screen": {"path": str(args.screen), "sha256": sha256_file(root / args.screen)},
            "bank": str(args.bank),
        },
        "exclusions": {
            label: {"path": rel, "count": len(excluded_names[label]),
                    "sha256": sha256_file(root / rel)}
            for label, rel in EXCLUSION_LISTS.items()
        },
        "excluded_motion_hashes": len(excluded_hashes),
        "disjoint_by_name": {k: len(v) for k, v in name_overlap.items()},
        "disjoint_by_hash_overlaps": len(hash_overlap),
        "panel_duration_s": {"total": sum(frames) / 50.0, "min": min(frames) / 50.0,
                             "max": max(frames) / 50.0},
        "panel_txt_sha256": sha256_file(panel_txt),
        "motion_sha256": panel_hashes,
        "builder_sha256": sha256_file(Path(__file__).resolve()),
    }
    (out / "panel_manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: manifest[k] for k in ("size", "candidates", "rejected",
                      "disjoint_by_name", "disjoint_by_hash_overlaps", "panel_duration_s",
                      "panel_txt_sha256")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
