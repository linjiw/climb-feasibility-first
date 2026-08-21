#!/usr/bin/env python3
"""Build a frozen, fail-closed exact segment unit table for v2 training."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

SCHEMA = "segment_unit_table/1"


def sha256_file(path: Path) -> str:
    """Hash an input artifact."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: Any) -> str:
    """Hash a JSON-compatible value independent of formatting."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def read_names(path: Path) -> list[str]:
    """Read a comment-tolerant motion list and reject duplicates."""
    names = [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    if not names or len(names) != len(set(names)):
        raise ValueError("clip list must be non-empty and contain unique names")
    return names


def validate_runs(value: Any, *, frames: int, label: str) -> list[tuple[int, int]]:
    """Validate ordered, non-overlapping integer half-open frame runs."""
    if not isinstance(value, list):
        raise TypeError(f"{label} must be a list")
    runs: list[tuple[int, int]] = []
    previous_stop = 0
    for index, item in enumerate(value):
        if (
            not isinstance(item, list)
            or len(item) != 2
            or not all(isinstance(frame, int) for frame in item)
        ):
            raise ValueError(f"{label}[{index}] must be two integer frames")
        start, stop = item
        if start < previous_stop or start < 0 or stop <= start or stop > frames:
            raise ValueError(f"{label} must be ordered, disjoint, and inside the clip")
        runs.append((start, stop))
        previous_stop = stop
    return runs


def build_manifest(
    clips_path: Path,
    bank: Path,
    sidecar_dir: Path,
    *,
    horizon_steps: int,
) -> dict[str, Any]:
    """Validate exact sidecars and return a canonical training-unit manifest."""
    if horizon_steps <= 0:
        raise ValueError("horizon_steps must be positive")
    names = read_names(clips_path)
    sources: list[dict[str, Any]] = []
    source_units: list[dict[str, Any]] = []
    admissible_units: list[dict[str, Any]] = []
    canonical_unit_id = 0

    for clip_id, name in enumerate(names):
        motion_path = bank / f"{name}.npz"
        sidecar_path = sidecar_dir / f"{name}.json"
        if not motion_path.is_file() or not sidecar_path.is_file():
            raise FileNotFoundError(
                f"{name}: exact motion and sidecar are both required (fail closed)"
            )
        with np.load(motion_path) as archive:
            frames = len(archive["joint_pos"])
            fps = float(np.asarray(archive["fps"]).reshape(-1)[0])
        sidecar = json.loads(sidecar_path.read_text())
        required = (
            "source_screen_sha256",
            "reducer_sha256",
            "feasible_segments_frames",
            "feasible_segment_records",
            "guarded_severe_windows_frames",
        )
        if any(field not in sidecar for field in required):
            raise ValueError(f"{name}: sidecar lacks exact-v2 provenance fields")
        if (
            sidecar.get("clip") != name
            or int(sidecar.get("frames", -1)) != frames
            or abs(float(sidecar.get("fps", -1.0)) - fps) > 1.0e-9
        ):
            raise ValueError(f"{name}: sidecar timeline does not match motion NPZ")

        feasible = validate_runs(
            sidecar["feasible_segments_frames"],
            frames=frames,
            label=f"{name}.feasible_segments_frames",
        )
        severe = validate_runs(
            sidecar["guarded_severe_windows_frames"],
            frames=frames,
            label=f"{name}.guarded_severe_windows_frames",
        )
        feasible_mask = np.zeros(frames, dtype=bool)
        severe_mask = np.zeros(frames, dtype=bool)
        for start, stop in feasible:
            feasible_mask[start:stop] = True
        for start, stop in severe:
            severe_mask[start:stop] = True
        if bool((feasible_mask & severe_mask).any()) or not bool(
            (feasible_mask | severe_mask).all()
        ):
            raise ValueError(f"{name}: exact feasible/severe support is not a partition")
        records = sidecar["feasible_segment_records"]
        if not isinstance(records, list) or len(records) != len(feasible):
            raise ValueError(f"{name}: segment record table is misaligned")

        sources.append(
            {
                "clip_id": clip_id,
                "clip": name,
                "frames": frames,
                "fps": fps,
                "motion_sha256": sha256_file(motion_path),
                "sidecar_sha256": sha256_file(sidecar_path),
                "source_screen_sha256": sidecar["source_screen_sha256"],
                "reducer_sha256": sidecar["reducer_sha256"],
                "guard_s": sidecar["guard_s"],
                "guard_mode": sidecar["guard_mode"],
                "severity": sidecar["severity"],
            }
        )
        for (start, stop), record in zip(feasible, records, strict=True):
            if (
                int(record.get("start_frame", -1)) != start
                or int(record.get("stop_frame", -1)) != stop
            ):
                raise ValueError(f"{name}: segment record frame IDs are misaligned")
            safe_stop = stop - horizon_steps
            source_unit = {
                "unit_id": canonical_unit_id,
                "clip_id": clip_id,
                "clip": name,
                "segment_start": start,
                "segment_stop": stop,
                "admissible_start_first": start,
                "admissible_start_stop": safe_stop,
                "legal_start_count": max(safe_stop - start, 0),
                "unsupported_ratio_mean": float(record["unsupported_ratio_mean"]),
                "unsupported_ratio_p95": float(record["unsupported_ratio_p95"]),
                "unsupported_ratio_max": float(record["unsupported_ratio_max"]),
            }
            source_units.append(source_unit)
            if safe_stop > start:
                admissible_units.append(
                    {
                        **source_unit,
                        "table_index": len(admissible_units),
                        "deployment_mass": safe_stop - start,
                    }
                )
            canonical_unit_id += 1

    if not admissible_units:
        raise ValueError("no exact segment can contain the requested horizon")
    frozen_table = {
        "horizon_steps": horizon_steps,
        "sources": sources,
        "source_units": source_units,
        "admissible_units": admissible_units,
    }
    return {
        "schema_version": SCHEMA,
        "classification": "unsealed v2 runtime input; exact support fails closed",
        "clips_sha256": sha256_file(clips_path),
        "builder_sha256": sha256_file(Path(__file__).resolve()),
        **frozen_table,
        "unit_table_sha256": canonical_hash(frozen_table),
        "counts": {
            "clips": len(names),
            "source_units": len(source_units),
            "admissible_units": len(admissible_units),
            "discarded_short_units": len(source_units) - len(admissible_units),
            "legal_starts": sum(
                unit["legal_start_count"] for unit in admissible_units
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clips", type=Path, required=True)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--sidecars", type=Path, required=True)
    parser.add_argument("--horizon-steps", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    manifest = build_manifest(
        args.clips.resolve(),
        args.bank.resolve(),
        args.sidecars.resolve(),
        horizon_steps=args.horizon_steps,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=1) + "\n")
    print(
        f"wrote {args.out}: {manifest['counts']['admissible_units']} units, "
        f"{manifest['counts']['legal_starts']} exact starts"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
