from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tools import analyze_g_segment
from tools.build_g_run_manifest import RUN_MAP_SCHEMA, build_manifest, sha256_file


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path, Path]:
    conditions_payload = {
        "schema_version": "paired_eval_conditions/2",
        "joint_noise": 0.05,
        "nominal": False,
        "nconmax_per_world": 70,
        "conditions": [
            {
                "condition_id": "clip_a@0:r0",
                "clip": "clip_a",
                "full_window": True,
            },
            {
                "condition_id": "clip_b@0:r0",
                "clip": "clip_b",
                "full_window": True,
            },
        ],
    }
    conditions_path = tmp_path / "conditions.json"
    conditions_path.write_text(json.dumps(conditions_payload))
    strata_path = tmp_path / "strata.csv"
    strata_path.write_text(
        "clip,stratum\nclip_a,feasible_hard_reference\n"
        "clip_b,feasible_remainder\n"
    )
    conditions = {
        **conditions_payload,
        "_sha256": sha256_file(conditions_path),
        "_strata_sha256": sha256_file(strata_path),
    }
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    manifest = analyze_g_segment._synthetic_case(
        artifact_root,
        conditions,
        delta=0.1,
        noise=0.01,
        tv=0.08,
        rng=np.random.default_rng(1),
    )
    run_map = {"schema_version": RUN_MAP_SCHEMA, "arms": {}}
    for arm, arm_record in manifest["arms"].items():
        run_map["arms"][arm] = {"seeds": {}}
        for seed, run in arm_record["seeds"].items():
            run_map["arms"][arm]["seeds"][seed] = {
                "ledgers": [record["path"] for record in run["ledgers"]],
                "evaluations": {
                    iteration: {
                        "csv": record["csv"]["path"],
                        "checkpoint": record["checkpoint"]["path"],
                    }
                    for iteration, record in run["evaluations"].items()
                },
            }
    run_map_path = tmp_path / "run_map.json"
    run_map_path.write_text(json.dumps(run_map))
    calibration = manifest["calibration"]
    return (
        run_map_path,
        conditions_path,
        strata_path,
        Path(manifest["panel_manifest"]["path"]),
        Path(calibration["design_path"]),
        Path(calibration["result_path"]),
    )


def test_build_manifest_binds_every_evaluation_artifact(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    manifest = build_manifest(*paths)

    assert manifest["schema_version"] == "g_segment_run_manifest/1"
    assert set(manifest["arms"]) == {"G1", "G2"}
    assert set(manifest["arms"]["G2"]["seeds"]["1"]["evaluations"]) == {
        "1000",
        "2000",
        "3000",
        "3999",
    }
    record = manifest["arms"]["G2"]["seeds"]["1"]["evaluations"]["3999"]
    assert set(record) == {"csv", "metadata", "checkpoint"}


def test_build_manifest_rejects_metadata_checkpoint_swap(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    run_map = json.loads(paths[0].read_text())
    swapped = run_map["arms"]["G1"]["seeds"]["1"]["evaluations"]["3999"]
    swapped["checkpoint"] = run_map["arms"]["G2"]["seeds"]["1"][
        "evaluations"
    ]["3999"]["checkpoint"]
    paths[0].write_text(json.dumps(run_map))

    with pytest.raises(ValueError, match="metadata checkpoint"):
        build_manifest(*paths)
