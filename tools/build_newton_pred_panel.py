#!/usr/bin/env python3
"""Freeze the reference-only inputs for the Newton predictive gate.

This tool reads the already-selected 42 exact units, their feasibility
sidecars, and reference-motion arrays. It does not load a policy, instantiate a
simulator, or read a Newton outcome. The resulting CSV is therefore safe to
construct before the predictive-gate preregistration is sealed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

KINEMATIC_COLUMNS = (
    "root_linear_speed_rms_mps",
    "root_angular_speed_rms_rps",
    "joint_speed_rms_rps",
    "joint_acceleration_rms_rps2",
    "body_linear_speed_rms_mps",
    "root_height_range_m",
)


def sha256_file(path: Path) -> str:
    """Return a file's SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rms(value: np.ndarray) -> float:
    """Return the root mean square in float64 accumulation."""
    return float(np.sqrt(np.mean(np.square(value, dtype=np.float64))))


def reference_features(motion_path: Path, start: int, steps: int) -> dict[str, float]:
    """Compute the sealed kinematic control battery on one fixed window."""
    with np.load(motion_path, allow_pickle=False) as motion:
        stop = start + steps
        fps = float(np.asarray(motion["fps"]).reshape(-1)[0])
        joint_vel = np.asarray(motion["joint_vel"][start:stop], dtype=np.float64)
        body_pos = np.asarray(motion["body_pos_w"][start:stop], dtype=np.float64)
        body_lin_vel = np.asarray(
            motion["body_lin_vel_w"][start:stop], dtype=np.float64
        )
        body_ang_vel = np.asarray(
            motion["body_ang_vel_w"][start:stop], dtype=np.float64
        )
    if len(joint_vel) != steps:
        raise ValueError(
            f"{motion_path.name}: requested [{start}, {stop}) but read "
            f"{len(joint_vel)} frames"
        )
    joint_accel = np.diff(joint_vel, axis=0) * fps
    return {
        "root_linear_speed_rms_mps": rms(body_lin_vel[:, 0]),
        "root_angular_speed_rms_rps": rms(body_ang_vel[:, 0]),
        "joint_speed_rms_rps": rms(joint_vel),
        "joint_acceleration_rms_rps2": rms(joint_accel),
        "body_linear_speed_rms_mps": rms(body_lin_vel),
        "root_height_range_m": float(np.ptp(body_pos[:, 0, 2])),
    }


def build_rows(
    table: dict[str, Any],
    bank: Path,
    sidecars: Path,
    probe_steps: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build one row per admissible unit and verify every bound input."""
    sources = {int(row["clip_id"]): row for row in table["sources"]}
    rows: list[dict[str, Any]] = []
    input_files: list[dict[str, Any]] = []
    seen_files: set[Path] = set()
    for unit in table["admissible_units"]:
        source = sources[int(unit["clip_id"])]
        motion_path = bank / f"{unit['clip']}.npz"
        sidecar_path = sidecars / f"{unit['clip']}.json"
        motion_hash = sha256_file(motion_path)
        sidecar_hash = sha256_file(sidecar_path)
        if motion_hash != source["motion_sha256"]:
            raise ValueError(f"motion hash mismatch: {motion_path}")
        if sidecar_hash != source["sidecar_sha256"]:
            raise ValueError(f"sidecar hash mismatch: {sidecar_path}")
        sidecar = json.loads(sidecar_path.read_text())
        first = int(unit["admissible_start_first"])
        count = int(unit["legal_start_count"])
        canonical_start = first + (count - 1) // 2
        if canonical_start + int(table["horizon_steps"]) > int(unit["segment_stop"]):
            raise ValueError(f"unit {unit['unit_id']} violates the frozen 50-step support")
        features = reference_features(motion_path, canonical_start, probe_steps)
        rows.append(
            {
                "table_index": int(unit["table_index"]),
                "unit_id": int(unit["unit_id"]),
                "clip_id": int(unit["clip_id"]),
                "clip": unit["clip"],
                "canonical_start_frame": canonical_start,
                "probe_stop_frame": canonical_start + probe_steps,
                "clip_infeasible_frac": float(sidecar["infeasible_frac"]),
                "unit_unsupported_ratio_mean": float(unit["unsupported_ratio_mean"]),
                **features,
            }
        )
        for path, digest in ((motion_path, motion_hash), (sidecar_path, sidecar_hash)):
            if path not in seen_files:
                input_files.append(
                    {"path": str(path.resolve()), "sha256": digest}
                )
                seen_files.add(path)
    if len(rows) != 42 or {row["table_index"] for row in rows} != set(range(42)):
        raise ValueError("the predictive panel must contain table_index 0..41 exactly once")
    return rows, input_files


def main() -> int:
    """Build the frozen panel CSV and its provenance manifest."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unit-table", type=Path, required=True)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--sidecars", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--probe-steps", type=int, default=25)
    args = parser.parse_args()
    if args.probe_steps != 25:
        parser.error("the N-c preregistration fixes --probe-steps=25")

    table = json.loads(args.unit_table.read_text())
    rows, inputs = build_rows(table, args.bank, args.sidecars, args.probe_steps)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0])
    with args.out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "schema_version": "newton15_pred_panel/1",
        "classification": (
            "unsealed reference-only preregistration input; no policy or solver outcomes"
        ),
        "selection_rule": (
            "all 42 admissible units in the segment-v2 mechanism table; canonical "
            "start is first + floor((legal_start_count - 1) / 2)"
        ),
        "probe_steps": args.probe_steps,
        "units": len(rows),
        "clips": len({row["clip_id"] for row in rows}),
        "unit_table_file_sha256": sha256_file(args.unit_table),
        "unit_table_payload_sha256": table["unit_table_sha256"],
        "panel_csv": str(args.out.resolve()),
        "panel_csv_sha256": sha256_file(args.out),
        "kinematic_columns": list(KINEMATIC_COLUMNS),
        "input_files": sorted(inputs, key=lambda row: row["path"]),
    }
    args.manifest.write_text(json.dumps(manifest, indent=1) + "\n")
    print(
        f"wrote {len(rows)} units across {manifest['clips']} clips -> {args.out} "
        f"({manifest['panel_csv_sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
