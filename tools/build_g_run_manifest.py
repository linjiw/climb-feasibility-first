#!/usr/bin/env python3
"""Build the hash-complete Phase-G confirmation run manifest.

The input run map contains paths only. This tool verifies evaluator sidecars and
training ledgers, hashes every artifact, and emits the manifest accepted by
``tools/analyze_g_segment.py``. It never parses evaluator CSV rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUN_MAP_SCHEMA = "g_segment_run_map/1"
RUN_MANIFEST_SCHEMA = "g_segment_run_manifest/1"
EVAL_OUTPUT_SCHEMA = "paired_eval_output/1"
ARMS = ("G1", "G2")
EVALUATION_ITERATIONS = (1000, 2000, 3000, 3999)
EVALUATOR_PATH = ROOT / "tools" / "eval_paired_v2.py"
TRAINING_ENTRYPOINT_PATH = ROOT / "tools" / "climb_segment_train.py"


def sha256_file(path: Path) -> str:
    """Hash one artifact without loading it all into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact(path_value: str, label: str) -> dict[str, str]:
    """Resolve one required path and return its immutable manifest record."""
    path = Path(path_value).resolve()
    if not path.is_file():
        raise ValueError(f"{label}: missing file {path}")
    return {"path": str(path), "sha256": sha256_file(path)}


def _metadata_path_matches(value: Any, expected: str) -> bool:
    """Compare one sidecar path while treating malformed types as mismatch."""
    return isinstance(value, str) and Path(value).resolve() == Path(expected)


def _validated_evaluation(
    source: Any,
    *,
    label: str,
    conditions_sha256: str,
    evaluator_sha256: str,
    reference_sha256: dict[str, str],
) -> dict[str, dict[str, str]]:
    if not isinstance(source, dict) or set(source) != {"csv", "checkpoint"}:
        raise ValueError(f"{label}: expected exact csv/checkpoint path record")
    csv_record = artifact(source["csv"], f"{label} CSV")
    checkpoint_record = artifact(source["checkpoint"], f"{label} checkpoint")
    metadata_record = artifact(
        f"{csv_record['path']}.meta.json", f"{label} metadata"
    )
    metadata = json.loads(Path(metadata_record["path"]).read_text())
    expected = {
        "schema_version": EVAL_OUTPUT_SCHEMA,
        "task": "Climb-Tracking-Flat-Unitree-G1",
        "conditions_sha256": conditions_sha256,
        "evaluator_sha256": evaluator_sha256,
        "checkpoint_sha256": checkpoint_record["sha256"],
    }
    for key, value in expected.items():
        if metadata.get(key) != value:
            raise ValueError(
                f"{label}: metadata {key}={metadata.get(key)!r}, expected {value!r}"
            )
    if not _metadata_path_matches(
        metadata.get("checkpoint"), checkpoint_record["path"]
    ):
        raise ValueError(f"{label}: metadata checkpoint path mismatch")
    if not _metadata_path_matches(metadata.get("output"), csv_record["path"]):
        raise ValueError(f"{label}: metadata output path mismatch")
    if metadata.get("selected_reference_sha256") != reference_sha256:
        raise ValueError(f"{label}: active references differ from panel manifest")
    if metadata.get("common_reference_sha256") != reference_sha256:
        raise ValueError(f"{label}: common references differ from panel manifest")
    return {
        "csv": csv_record,
        "metadata": metadata_record,
        "checkpoint": checkpoint_record,
    }


def build_manifest(
    run_map_path: Path,
    conditions_path: Path,
    strata_path: Path,
    panel_manifest_path: Path,
    design_path: Path,
    result_path: Path,
) -> dict[str, Any]:
    """Verify the path-only map and build a hash-complete analysis manifest."""
    run_map_path = run_map_path.resolve()
    conditions_path = conditions_path.resolve()
    strata_path = strata_path.resolve()
    panel_manifest_path = panel_manifest_path.resolve()
    design_path = design_path.resolve()
    result_path = result_path.resolve()
    run_map = json.loads(run_map_path.read_text())
    if run_map.get("schema_version") != RUN_MAP_SCHEMA:
        raise ValueError(f"run map must use {RUN_MAP_SCHEMA}")
    if set(run_map.get("arms", {})) != set(ARMS):
        raise ValueError("run map must contain exactly G1 and G2")

    conditions_sha256 = sha256_file(conditions_path)
    conditions = json.loads(conditions_path.read_text())
    panel_record = artifact(str(panel_manifest_path), "evaluation panel manifest")
    panel = json.loads(panel_manifest_path.read_text())
    if panel.get("schema_version") != "g_segment_eval_panel/1":
        raise ValueError("unsupported evaluation panel manifest")
    reference_sha256 = panel.get("motion_sha256")
    condition_clips = {row["clip"] for row in conditions["conditions"]}
    if (
        not isinstance(reference_sha256, dict)
        or set(reference_sha256) != condition_clips
    ):
        raise ValueError("panel motion hashes do not match condition clips")
    evaluator_sha256 = sha256_file(EVALUATOR_PATH)
    training_sha256 = sha256_file(TRAINING_ENTRYPOINT_PATH)
    design_sha256 = sha256_file(design_path)
    result_sha256 = sha256_file(result_path)
    calibration = json.loads(result_path.read_text())
    if (
        calibration.get("schema_version") != "g2_calibration_result/1"
        or calibration.get("status") != "ready_to_freeze"
        or calibration.get("design_sha256") != design_sha256
    ):
        raise ValueError("calibration result is not ready or design-bound")

    seeds = sorted(run_map["arms"]["G1"].get("seeds", {}))
    if seeds not in (["1", "2"], ["1", "2", "3"]):
        raise ValueError("run map must contain confirmation seeds 1-2 or 1-3")
    if sorted(run_map["arms"]["G2"].get("seeds", {})) != seeds:
        raise ValueError("G1 and G2 seed sets differ")

    arms: dict[str, Any] = {}
    for arm in ARMS:
        arms[arm] = {"seeds": {}}
        for seed in seeds:
            label = f"{arm} seed {seed}"
            source_run = run_map["arms"][arm]["seeds"][seed]
            if not isinstance(source_run, dict) or set(source_run) != {
                "ledgers", "evaluations"
            }:
                raise ValueError(
                    f"{label}: expected exact ledgers/evaluations record"
                )
            if not isinstance(source_run["ledgers"], list):
                raise TypeError(f"{label}: ledgers must be a path list")
            ledger_records = [
                artifact(path, f"{label} ledger {index}")
                for index, path in enumerate(source_run["ledgers"])
            ]
            ledgers = [
                json.loads(Path(record["path"]).read_text())
                for record in ledger_records
            ]
            by_iteration: dict[int, list[dict[str, Any]]] = {}
            for ledger in ledgers:
                by_iteration.setdefault(int(ledger["iteration"]), []).append(ledger)

            source_evaluations = source_run["evaluations"]
            if not isinstance(source_evaluations, dict) or set(
                source_evaluations
            ) != {str(value) for value in EVALUATION_ITERATIONS}:
                raise ValueError(
                    f"{label}: evaluations must be exactly "
                    f"{list(EVALUATION_ITERATIONS)}"
                )
            evaluations = {}
            for iteration in EVALUATION_ITERATIONS:
                cell_label = f"{label} iteration {iteration}"
                record = _validated_evaluation(
                    source_evaluations[str(iteration)],
                    label=cell_label,
                    conditions_sha256=conditions_sha256,
                    evaluator_sha256=evaluator_sha256,
                    reference_sha256=reference_sha256,
                )
                linked = by_iteration.get(iteration, [])
                if len(linked) != 1:
                    raise ValueError(
                        f"{cell_label}: expected one matching ledger, got {len(linked)}"
                    )
                if linked[0].get("checkpoint") != record["checkpoint"]:
                    raise ValueError(
                        f"{cell_label}: ledger does not bind evaluated checkpoint"
                    )
                if linked[0].get("training_entrypoint_sha256") != training_sha256:
                    raise ValueError(
                        f"{cell_label}: training-entrypoint hash mismatch"
                    )
                evaluations[str(iteration)] = record
            arms[arm]["seeds"][seed] = {
                "ledgers": ledger_records,
                "evaluations": evaluations,
            }

    return {
        "schema_version": RUN_MANIFEST_SCHEMA,
        "classification": "unsealed Phase-G confirmation artifact manifest",
        "source_run_map": artifact(str(run_map_path), "run map"),
        "conditions_sha256": conditions_sha256,
        "strata_sha256": sha256_file(strata_path),
        "panel_manifest": panel_record,
        "evaluator_sha256": evaluator_sha256,
        "training_entrypoint_sha256": training_sha256,
        "calibration": {
            "design_path": str(design_path),
            "design_sha256": design_sha256,
            "result_path": str(result_path),
            "result_sha256": result_sha256,
        },
        "arms": arms,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-map", type=Path, required=True)
    parser.add_argument(
        "--conditions",
        type=Path,
        default=Path("reports/g_segment/eval_conditions.json"),
    )
    parser.add_argument(
        "--strata",
        type=Path,
        default=Path("reports/g_segment/panel/strata.csv"),
    )
    parser.add_argument(
        "--panel-manifest",
        type=Path,
        default=Path("reports/g_segment/panel/panel_manifest.json"),
    )
    parser.add_argument(
        "--calibration-design",
        type=Path,
        default=Path("plan/G2_CALIBRATION_GRID.json"),
    )
    parser.add_argument("--calibration-result", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = build_manifest(
        args.run_map,
        args.conditions,
        args.strata,
        args.panel_manifest,
        args.calibration_design,
        args.calibration_result,
    )
    serialized = json.dumps(payload, indent=1) + "\n"
    if args.out.exists() and args.out.read_text() != serialized:
        raise ValueError(f"refusing to replace differing manifest {args.out}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(serialized)
    print(
        f"Phase-G run manifest: {len(payload['arms']['G1']['seeds'])} seeds, "
        f"{len(ARMS) * len(payload['arms']['G1']['seeds']) * len(EVALUATION_ITERATIONS)} "
        f"evaluation cells -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
