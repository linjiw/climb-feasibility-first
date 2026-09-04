#!/usr/bin/env python3
"""Select the outcome-blind manual contact-label validation panel."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

SCHEMA_VERSION = "contact_validation_panel/1"
DEFAULT_SEED = 20260903


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _selection_key(seed: int, clip: str) -> str:
    return hashlib.sha256(f"{seed}:{clip}".encode()).hexdigest()


def select_rows(strata_path: Path, seed: int) -> list[dict[str, str | int]]:
    """Select five clips per stratum and split by deterministic hash order."""
    with strata_path.open(newline="") as handle:
        source = list(csv.DictReader(handle))
    by_stratum: dict[str, list[str]] = {}
    for row in source:
        by_stratum.setdefault(row["stratum"], []).append(row["clip"])
    expected = {"feasible_hard_reference", "feasible_remainder"}
    if set(by_stratum) != expected:
        raise ValueError(f"expected strata {sorted(expected)}")

    rows: list[dict[str, str | int]] = []
    for stratum in sorted(expected):
        ordered = sorted(
            by_stratum[stratum], key=lambda clip: (_selection_key(seed, clip), clip)
        )
        if len(ordered) < 10:
            raise ValueError(f"too few clips in {stratum}")
        for rank, clip in enumerate(ordered[:10], start=1):
            rows.append(
                {
                    "clip": clip,
                    "stratum": stratum,
                    "split": "development" if rank <= 5 else "validation",
                    "stratum_selection_rank": rank,
                }
            )
    return sorted(rows, key=lambda row: (str(row["split"]), str(row["clip"])))


def _csv_bytes(rows: list[dict[str, str | int]]) -> bytes:
    output = io.StringIO(newline="")
    fields = ["clip", "stratum", "split", "stratum_selection_rank"]
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode()


def _write_immutable(path: Path, payload: bytes) -> None:
    if path.exists():
        if path.read_bytes() != payload:
            raise FileExistsError(f"refusing to replace differing artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strata",
        type=Path,
        default=Path("reports/g_segment/panel/strata.csv"),
    )
    parser.add_argument(
        "--strata-manifest",
        type=Path,
        default=Path("reports/g_segment/panel/strata.manifest.json"),
    )
    parser.add_argument(
        "--panel-manifest",
        type=Path,
        default=Path("reports/g_segment/panel/panel_manifest.json"),
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("reports/g_segment/contact_validation/panel.csv"),
    )
    args = parser.parse_args()

    strata_manifest = json.loads(args.strata_manifest.read_text())
    if strata_manifest.get("schema_version") != "g_segment_eval_strata/1":
        raise ValueError("unsupported strata manifest")
    if strata_manifest.get("output_sha256") != sha256_file(args.strata):
        raise ValueError("strata hash does not match its manifest")
    panel_manifest = json.loads(args.panel_manifest.read_text())
    if panel_manifest.get("schema_version") != "g_segment_eval_panel/1":
        raise ValueError("unsupported panel manifest")

    rows = select_rows(args.strata, args.seed)
    selected = {str(row["clip"]) for row in rows}
    panel_hashes = panel_manifest.get("motion_sha256", {})
    if not selected.issubset(panel_hashes):
        raise ValueError("selected contact-validation clips are not in frozen panel")
    _write_immutable(args.out, _csv_bytes(rows))
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "classification": "outcome-blind reference-only instrument-validation panel",
        "selection_rule": (
            "within each frozen feasible-hard/remainder stratum, order by "
            "SHA256(seed:clip), take first 10, assign ranks 1-5 to rater "
            "development and 6-10 to held-out validation"
        ),
        "seed": args.seed,
        "counts": {
            "development": sum(row["split"] == "development" for row in rows),
            "validation": sum(row["split"] == "validation" for row in rows),
            "feasible_hard_reference": sum(
                row["stratum"] == "feasible_hard_reference" for row in rows
            ),
            "feasible_remainder": sum(
                row["stratum"] == "feasible_remainder" for row in rows
            ),
        },
        "inputs": {
            "strata": {"path": str(args.strata), "sha256": sha256_file(args.strata)},
            "strata_manifest": {
                "path": str(args.strata_manifest),
                "sha256": sha256_file(args.strata_manifest),
            },
            "panel_manifest": {
                "path": str(args.panel_manifest),
                "sha256": sha256_file(args.panel_manifest),
            },
        },
        "output": {"path": str(args.out), "sha256": sha256_file(args.out)},
        "motion_sha256": {clip: panel_hashes[clip] for clip in sorted(selected)},
        "builder_sha256": sha256_file(Path(__file__).resolve()),
    }
    manifest_path = args.out.with_suffix(".manifest.json")
    encoded = (json.dumps(manifest, indent=1, sort_keys=True) + "\n").encode()
    _write_immutable(manifest_path, encoded)
    print(json.dumps({"counts": manifest["counts"], "output": str(args.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
