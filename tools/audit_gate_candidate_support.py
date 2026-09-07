#!/usr/bin/env python3
"""Audit H1's full legal-start universe; never create a training-ready manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def partition_starts(frames: int, horizon: int, feasible: list[list[int]]) -> list[dict]:
    """Partition legal starts, retaining feasible units and boundary-crossing rejects."""
    if frames < 0 or horizon < 1:
        raise ValueError("invalid timeline or horizon")
    legal_stop = max(0, frames - horizon)
    previous_stop = 0
    accepted = []
    for first, stop in feasible:
        if not 0 <= first < stop <= frames or first < previous_stop:
            raise ValueError("feasible runs must be ordered, disjoint and within the clip")
        previous_stop = stop
        if stop - first > horizon:
            accepted.append((first, stop - horizon))
    rows, cursor = [], 0
    for first, stop in accepted:
        if cursor < first:
            rows.append({"start_first": cursor, "start_stop": first, "gate_admitted": False})
        rows.append({"start_first": first, "start_stop": stop, "gate_admitted": True})
        cursor = stop
    if cursor < legal_stop:
        rows.append({"start_first": cursor, "start_stop": legal_stop, "gate_admitted": False})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--sidecar-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    horizon = manifest["horizon_steps"]
    intervals, clips, bindings = [], [], {}
    for source in manifest["sources"]:
        path = args.sidecar_dir / f"{source['clip']}.json"
        if digest(path) != source["sidecar_sha256"]:
            raise ValueError("sidecar changed from source-bound feasible manifest")
        sidecar = json.loads(path.read_text())
        if sidecar["frames"] != source["frames"] or sidecar["clip"] != source["clip"]:
            raise ValueError("sidecar timeline mismatch")
        runs = sidecar["feasible_segments_frames"]
        excluded = sidecar.get("excluded_windows_frames", sidecar["guarded_severe_windows_frames"])
        cursor = 0
        for start, stop in sorted(runs + excluded):
            if start != cursor or stop <= start:
                raise ValueError("feasible/excluded frames fail exhaustive disjoint partition")
            cursor = stop
        if cursor != source["frames"]:
            raise ValueError("frame partition does not cover the clip")
        parts = partition_starts(source["frames"], horizon, runs)
        existing = [u for u in manifest["admissible_units"] if u["clip_id"] == source["clip_id"]]
        accepted = [p for p in parts if p["gate_admitted"]]
        if [(p["start_first"], p["start_stop"]) for p in accepted] != [
                (u["admissible_start_first"], u["admissible_start_stop"]) for u in existing]:
            raise ValueError("candidate construction changed existing feasible support")
        identities = {(u["admissible_start_first"], u["admissible_start_stop"]): u["unit_id"] for u in existing}
        for part in parts:
            intervals.append({"clip_id": source["clip_id"], "clip": source["clip"], **part,
                              "legal_start_count": part["start_stop"]-part["start_first"],
                              "existing_feasible_unit_id": identities.get((part["start_first"], part["start_stop"]))})
        full = max(0, source["frames"]-horizon)
        admitted = sum(p["start_stop"]-p["start_first"] for p in accepted)
        assert sum(p["start_stop"]-p["start_first"] for p in parts) == full
        clips.append({"clip": source["clip"], "full_legal_starts": full,
                      "admitted_starts": admitted, "rejected_starts": full-admitted})
        bindings[str(path.resolve())] = source["sidecar_sha256"]
    full = sum(c["full_legal_starts"] for c in clips)
    admitted = sum(c["admitted_starts"] for c in clips)
    result = {
        "classification": "reference-only candidate support audit; no policy or training evidence",
        "schema_version": "gate_candidate_start_partition/1", "training_enabled": False,
        "horizon_steps": horizon, "clips": len(clips),
        "full_legal_starts": full, "admitted_legal_starts": admitted,
        "rejected_legal_starts": full-admitted,
        "rejected_mass_under_uncapped_legal_start_uniform_prior": (full-admitted)/full,
        "candidate_intervals": len(intervals),
        "preserved_feasible_units": sum(r["gate_admitted"] for r in intervals),
        "rejected_start_intervals": sum(not r["gate_admitted"] for r in intervals),
        "clips_with_rejected_starts": sum(c["rejected_starts"] > 0 for c in clips),
        "clips_with_no_admitted_starts": sum(c["admitted_starts"] == 0 for c in clips),
        "existing_source_units_are_feasible_frame_runs": True,
        "limitation": "This prior-mass count is not post-cap allocation, wasted PPO budget, or practical gate benefit.",
        "manifest": {"path": str(args.manifest.resolve()), "sha256": digest(args.manifest)},
        "sidecar_bindings": bindings, "builder_sha256": digest(Path(__file__))}
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    for name, value in (("result.json", result), ("candidate_start_intervals.json", intervals), ("clips.json", clips)):
        with (out / name).open("x") as handle:
            json.dump(value, handle, indent=2)
            handle.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k != "sidecar_bindings"}, indent=2))


if __name__ == "__main__":
    main()
