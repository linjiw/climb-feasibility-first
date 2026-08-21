#!/usr/bin/env python3
"""Select the frozen, deterministic DFRP v1 exact-repair panel."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "dfrp_exact_panel_selection/1"
DEFAULT_SEED = "dfrp-v1-exact-panel-2026-08-21"


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _rank(seed: str, name: str) -> str:
    return hashlib.sha256(f"{seed}\0{name}".encode()).hexdigest()


def _source(name: str) -> str:
    return name.split("_", 1)[0]


def _diverse_pick(rows: list[dict[str, Any]], count: int, seed: str) -> list[dict]:
    """Prefer distinct source families, then fill by stable hash order."""
    ordered = sorted(rows, key=lambda row: (_rank(seed, row["name"]), row["name"]))
    selected: list[dict] = []
    seen_sources: set[str] = set()
    for row in ordered:
        source = _source(row["name"])
        if source in seen_sources:
            continue
        selected.append(row)
        seen_sources.add(source)
        if len(selected) == count:
            return selected
    selected_names = {row["name"] for row in selected}
    selected.extend(
        row for row in ordered if row["name"] not in selected_names
    )
    return selected[:count]


def _offset_stratum(offset: float) -> str | None:
    if offset <= 0.02:
        return "rare_le_2cm"
    if offset <= 0.04:
        return "2to4cm"
    if offset <= 0.06:
        return "4to6cm"
    if offset <= 0.08:
        return "6to8cm"
    return None


def select_panel(
    manifest: dict[str, Any],
    *,
    manifest_path: Path,
    flagged_per_cell: int = 4,
    controls: int = 4,
    seed: str = DEFAULT_SEED,
) -> dict[str, Any]:
    """Select flagged strata and source-matched feasible controls."""
    primary = [row for row in manifest["clips"] if row["route"] == "repair_primary"]
    rare = [
        row
        for row in primary
        if _offset_stratum(float(row["repair"]["offset_max_m"])) == "rare_le_2cm"
    ]
    if len(rare) != 2:
        raise ValueError(f"frozen panel expects two <=2 cm candidates, got {len(rare)}")

    selected_rows: list[tuple[dict[str, Any], str]] = [
        (row, "rare_le_2cm")
        for row in sorted(rare, key=lambda row: row["name"])
    ]
    for offset_label in ("2to4cm", "4to6cm", "6to8cm"):
        for severity_label in ("10to20pct", "over20pct"):
            cell = [
                row
                for row in primary
                if _offset_stratum(float(row["repair"]["offset_max_m"]))
                == offset_label
                and (
                    (float(row["screen"]["infeasible_frac"]) <= 0.20)
                    == (severity_label == "10to20pct")
                )
            ]
            if len(cell) < flagged_per_cell:
                raise ValueError(
                    f"stratum {offset_label}/{severity_label} has {len(cell)} rows; "
                    f"need {flagged_per_cell}"
                )
            cell_seed = f"{seed}:{offset_label}:{severity_label}"
            selected_rows.extend(
                (row, f"{offset_label}_{severity_label}")
                for row in _diverse_pick(cell, flagged_per_cell, cell_seed)
            )

    selected_names = [row["name"] for row, _ in selected_rows]
    if len(selected_names) != len(set(selected_names)):
        raise ValueError("flagged selection contains duplicates")

    source_counts = Counter(_source(name) for name in selected_names)
    control_sources = [
        source
        for source, _ in sorted(
            source_counts.items(), key=lambda item: (-item[1], item[0])
        )[:controls]
    ]
    raw_feasible = [
        row
        for row in manifest["clips"]
        if row["route"] == "raw_feasible" and int(row["original"]["frames"]) >= 50
    ]
    control_rows: list[dict[str, Any]] = []
    for source in control_sources:
        candidates = [
            row for row in raw_feasible if _source(row["name"]) == source
        ]
        if not candidates:
            raise ValueError(f"no raw-feasible control for source {source}")
        control_rows.append(
            min(
                candidates,
                key=lambda row: (_rank(f"{seed}:control", row["name"]), row["name"]),
            )
        )

    clips = []
    for row, stratum in selected_rows:
        clips.append(
            {
                "name": row["name"],
                "role": "flagged_primary_candidate",
                "stratum": stratum,
                "source": _source(row["name"]),
                "frames": int(row["original"]["frames"]),
                "infeasible_frac_before": float(row["screen"]["infeasible_frac"]),
                "legacy_offset_max_m": float(row["repair"]["offset_max_m"]),
            }
        )
    for row in control_rows:
        clips.append(
            {
                "name": row["name"],
                "role": "raw_feasible_control",
                "stratum": f"control_{_source(row['name'])}",
                "source": _source(row["name"]),
                "frames": int(row["original"]["frames"]),
                "infeasible_frac_before": float(row["screen"]["infeasible_frac"]),
                "legacy_offset_max_m": None,
            }
        )

    payload = {
        "schema_version": SCHEMA_VERSION,
        "classification": "unsealed deterministic CPU repair panel",
        "seed": seed,
        "source_manifest": str(manifest_path),
        "source_manifest_sha256": sha256_file(manifest_path),
        "source_manifest_payload_sha256": manifest["payload_sha256"],
        "rules": {
            "rare_offset_max_m": 0.02,
            "regular_offset_edges_m": [0.02, 0.04, 0.06, 0.08],
            "severity_split": 0.20,
            "flagged_per_regular_cell": flagged_per_cell,
            "controls": controls,
            "selection": "source-diverse then seeded SHA-256",
        },
        "counts": {
            "flagged": len(selected_rows),
            "controls": len(control_rows),
            "total": len(clips),
        },
        "clips": clips,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["payload_sha256"] = hashlib.sha256(encoded).hexdigest()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-clips", type=Path, required=True)
    parser.add_argument("--flagged-per-cell", type=int, default=4)
    parser.add_argument("--controls", type=int, default=4)
    parser.add_argument("--seed", default=DEFAULT_SEED)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    panel = select_panel(
        manifest,
        manifest_path=args.manifest,
        flagged_per_cell=args.flagged_per_cell,
        controls=args.controls,
        seed=args.seed,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_clips.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(panel, indent=1) + "\n")
    args.out_clips.write_text(
        "\n".join(row["name"] for row in panel["clips"]) + "\n"
    )
    print(json.dumps(panel["counts"], indent=1))
    print(f"payload sha256 {panel['payload_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
