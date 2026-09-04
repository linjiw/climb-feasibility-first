#!/usr/bin/env python3
"""Build the typed, clip-level AMASS-to-G1 feasibility release candidate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

NUMERIC_COLUMNS = {
    "frames": int,
    "fps": float,
    "gap": float,
    "airborne_frac": float,
    "infeasible_frac": float,
    "unsupported_impulse_Ns": float,
    "unsupported_impulse_per_weight_s": float,
    "torque_infeasible_frac": float,
    "max_tau_ratio_p95": float,
    "sim_infeasible_frac": float,
}
EXPECTED_ROWS = 10_705
CLIP_THRESHOLD = 0.10


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("reports/feasibility_all/feasibility.csv"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("datasets/amass_g1_feasibility_v1.parquet"),
    )
    args = parser.parse_args()

    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SystemExit(
            "pyarrow is required; install it in the pinned mjlab environment"
        ) from exc

    raw_rows = list(csv.DictReader(args.input.open()))
    if len(raw_rows) != EXPECTED_ROWS:
        raise ValueError(f"expected {EXPECTED_ROWS} rows, found {len(raw_rows)}")
    names = [row["clip"] for row in raw_rows]
    if len(set(names)) != len(names):
        raise ValueError("clip identities are not unique")

    columns: dict[str, list[object]] = {
        "clip": [],
        "robot": [],
        "corpus": [],
        "retarget_pipeline": [],
        "scene": [],
        **{key: [] for key in NUMERIC_COLUMNS},
        "duration_s": [],
        "clip_infeasible_gt_0p10": [],
        "clip_airborne_gt_0p10": [],
    }
    for row in raw_rows:
        columns["clip"].append(row["clip"])
        columns["robot"].append("Unitree G1")
        columns["corpus"].append("AMASS")
        columns["retarget_pipeline"].append("whole_body_tracking")
        columns["scene"].append("flat_ground")
        parsed: dict[str, int | float] = {}
        for key, constructor in NUMERIC_COLUMNS.items():
            parsed[key] = constructor(row[key])
            if not math.isfinite(float(parsed[key])):
                raise ValueError(f"{row['clip']}: non-finite {key}")
            columns[key].append(parsed[key])
        columns["duration_s"].append(float(parsed["frames"]) / float(parsed["fps"]))
        columns["clip_infeasible_gt_0p10"].append(
            float(parsed["infeasible_frac"]) > CLIP_THRESHOLD
        )
        columns["clip_airborne_gt_0p10"].append(
            float(parsed["airborne_frac"]) > CLIP_THRESHOLD
        )

    table = pa.table(columns)
    metadata = {
        b"schema_version": b"amass_g1_feasibility/1",
        b"classification": (
            b"measured; internal clip-level candidate; do not publish without permission"
        ),
        b"scope": b"one AMASS corpus / whole_body_tracking retarget / Unitree G1 / flat ground",
        b"source_csv_sha256": sha256_file(args.input).encode(),
        b"clip_threshold": b"infeasible_frac > 0.10",
        b"not_included": b"motion trajectories and per-frame feasibility masks",
    }
    table = table.replace_schema_metadata(metadata)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        table,
        args.out,
        compression="zstd",
        use_dictionary=("robot", "corpus", "retarget_pipeline", "scene"),
        row_group_size=2048,
    )
    reread = pq.read_table(args.out)
    if reread.num_rows != EXPECTED_ROWS or reread.column_names != table.column_names:
        raise RuntimeError("Parquet round-trip validation failed")

    flagged = sum(bool(value) for value in columns["clip_infeasible_gt_0p10"])
    manifest = {
        "schema_version": "amass_g1_feasibility_release/1",
        "classification": "internal release candidate; do not publish without written permission",
        "scope": "one corpus-and-pipeline pairing; not an AMASS-wide or retargeter-wide rate",
        "rows": EXPECTED_ROWS,
        "flagged_infeasible_gt_0p10": flagged,
        "flagged_fraction": flagged / EXPECTED_ROWS,
        "source": {
            "path": str(args.input),
            "sha256": sha256_file(args.input),
        },
        "artifact": {
            "path": str(args.out),
            "sha256": sha256_file(args.out),
            "bytes": args.out.stat().st_size,
        },
        "writer": {"pyarrow": pa.__version__, "compression": "zstd"},
        "limitations": [
            "No AMASS motion trajectories are redistributed.",
            "This v1 candidate contains clip aggregates, not per-frame masks.",
            "Public distribution requires written permission or a documented legal determination.",
        ],
        "builder_sha256": sha256_file(Path(__file__).resolve()),
    }
    manifest_path = args.out.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(json.dumps({
        "rows": EXPECTED_ROWS,
        "flagged": flagged,
        "parquet_sha256": manifest["artifact"]["sha256"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
