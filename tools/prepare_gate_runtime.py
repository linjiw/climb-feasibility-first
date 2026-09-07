#!/usr/bin/env python3
"""Create matched development runtime views from the audited full start universe."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from audit_gate_candidate_support import partition_starts
from build_segment_unit_table import canonical_hash
from climb.gate_ablation import PROTOCOL, file_digest, rejection_telemetry, sampler_for, verified_manifest


def build_views(original: dict, partition: list[dict], partition_digest: str) -> dict[str, dict]:
    """Preserve original feasible unit identities; append stable rejected IDs."""
    originals = {row["unit_id"]: row for row in original["admissible_units"]}
    next_id = max(row["unit_id"] for row in original["source_units"]) + 1
    candidates = []
    for i, part in enumerate(partition):
        first, stop = part["start_first"], part["start_stop"]
        source = original["sources"][part["clip_id"]]
        if not 0 <= first < stop <= source["frames"]-original["horizon_steps"]:
            raise ValueError("candidate start interval crosses a clip boundary")
        if part["legal_start_count"] != stop-first:
            raise ValueError("candidate mass must count legal starts")
        if part["gate_admitted"]:
            row = deepcopy(originals[part["existing_feasible_unit_id"]])
            if (row["clip_id"], row["admissible_start_first"], row["admissible_start_stop"]) != (part["clip_id"], first, stop):
                raise ValueError("existing feasible unit identity or support changed")
            row.pop("table_index")
            row.pop("deployment_mass")
        else:
            row = {"unit_id": next_id, "clip_id": part["clip_id"], "clip": part["clip"],
                   "segment_start": first, "segment_stop": stop+original["horizon_steps"],
                   "admissible_start_first": first, "admissible_start_stop": stop,
                   "legal_start_count": stop-first}
            next_id += 1
        row.update(candidate_start_interval_id=i, gate_admitted=part["gate_admitted"])
        candidates.append(row)
    admitted_ids = [row["unit_id"] for row in candidates if row["gate_admitted"]]
    if admitted_ids != list(originals):
        raise ValueError("candidate partition changed the ordered feasible unit set")
    for source in original["sources"]:
        rows = [r for r in candidates if r["clip_id"] == source["clip_id"]]
        cursor = 0
        for row in rows:
            if row["admissible_start_first"] != cursor:
                raise ValueError("candidate starts have a gap or overlap")
            cursor = row["admissible_start_stop"]
        if cursor != max(0, source["frames"]-original["horizon_steps"]):
            raise ValueError("candidate partition does not exhaust legal starts")
    views = {}
    for arm in ("on", "off"):
        selected = [r for r in candidates if arm == "off" or r["gate_admitted"]]
        payload = {"horizon_steps": original["horizon_steps"], "sources": deepcopy(original["sources"]),
                   "source_units": deepcopy(candidates),
                   "admissible_units": [{**deepcopy(r), "table_index": i, "deployment_mass": r["legal_start_count"]}
                                        for i, r in enumerate(selected)]}
        views[arm] = {"schema_version": "segment_unit_table/1", **payload,
                      "classification": f"development exact-start support with dynamic admission {arm}; gate-off runtime eligibility does not imply physical admissibility",
                      "unit_table_sha256": canonical_hash(payload),
                      "gate_ablation": {"protocol": PROTOCOL, "admission": arm,
                                        "candidate_partition_sha256": partition_digest,
                                        "original_unit_table_sha256": original["unit_table_sha256"],
                                        "full_training_enabled": False}}
    return views


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-manifest", type=Path, required=True)
    parser.add_argument("--candidate-audit", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    original = json.loads(args.original_manifest.read_text())
    audit = json.loads((args.candidate_audit / "result.json").read_text())
    if file_digest(args.original_manifest) != audit["manifest"]["sha256"] or audit["training_enabled"]:
        raise ValueError("candidate audit requires unchanged original support and disabled training")
    rebuilt = []
    for source in original["sources"]:
        paths = [Path(p) for p in audit["sidecar_bindings"] if Path(p).name == f"{source['clip']}.json"]
        if len(paths) != 1 or file_digest(paths[0]) != source["sidecar_sha256"]:
            raise ValueError("candidate sidecar changed")
        sidecar = json.loads(paths[0].read_text())
        identities = {(r["admissible_start_first"], r["admissible_start_stop"]): r["unit_id"]
                      for r in original["admissible_units"] if r["clip_id"] == source["clip_id"]}
        for row in partition_starts(source["frames"], original["horizon_steps"], sidecar["feasible_segments_frames"]):
            rebuilt.append({"clip_id": source["clip_id"], "clip": source["clip"], **row,
                            "legal_start_count": row["start_stop"]-row["start_first"],
                            "existing_feasible_unit_id": identities.get((row["start_first"], row["start_stop"]))})
    partition_path = args.candidate_audit / "candidate_start_intervals.json"
    if rebuilt != json.loads(partition_path.read_text()):
        raise ValueError("candidate partition does not reproduce from bound sidecars")
    views = build_views(original, rebuilt, file_digest(partition_path))
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    records = {}
    for arm, view in views.items():
        path = out / f"gate_{arm}.json"
        path.write_text(json.dumps(view, indent=2)+"\n")
        verified_manifest(path, file_digest(path), arm)
        sampler = sampler_for(path, 71)
        records[arm] = {"path": str(path), "sha256": file_digest(path),
                        "startup": rejection_telemetry(sampler)}
    result = {"status": "matched_development_views_prepared", "full_training_enabled": False,
              "shared_candidate_partition": {"path": str(partition_path.resolve()), "sha256": file_digest(partition_path)},
              "original_manifest": {"path": str(args.original_manifest.resolve()), "sha256": file_digest(args.original_manifest)},
              "arms": records, "builder_sha256": file_digest(Path(__file__))}
    (out / "result.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
