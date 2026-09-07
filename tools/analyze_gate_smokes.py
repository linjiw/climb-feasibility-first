#!/usr/bin/env python3
"""Verify the matched PPO smoke pair and report lifecycle evidence only."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from climb.gate_ablation import file_digest
from train_gate_smoke import verify_smoke


def normalize_configuration(design: dict) -> tuple[dict, dict]:
    cfg, agent = deepcopy(design["config"]), deepcopy(design["agent"])
    for key in ("segment_manifest", "gate_manifest_sha256", "gate_admission"):
        del cfg["fields"]["commands"]["motion"]["fields"][key]
    del agent["fields"]["run_name"]
    return cfg, agent


def analyze(root: Path) -> dict:
    records, normalized = {}, []
    for arm in ("on", "off"):
        directory = root / f"cpu_{arm}"
        design = json.loads((directory / "design.json").read_text())
        for name, digest in design["sources"].items():
            if file_digest(Path(name)) != digest:
                raise ValueError(f"smoke source changed: {name}")
        expected = json.loads((directory / "result.json").read_text())
        manifest = Path(design["manifest"]["path"])
        actual = verify_smoke(directory / "run", manifest, design["manifest"]["sha256"], arm)
        if actual != expected:
            raise ValueError("complete smoke result does not reproduce")
        normalized.append(normalize_configuration(design))
        execution = json.loads((root / f"cpu_{arm}_execution.json").read_text())
        if execution["returncode"] != 0 or execution["device"] != "cpu":
            raise ValueError("CPU smoke did not complete")
        records[arm] = {"result": actual, "execution": execution,
                        "result_file": {"path": str(directory / "result.json"), "sha256": file_digest(directory / "result.json")}}
    if normalized[0] != normalized[1]:
        raise ValueError("non-support configuration differs between gate arms")
    if records["on"]["result"]["initial_actor"] != records["off"]["result"]["initial_actor"]:
        raise ValueError("matched seed did not produce identical initial actor tensors")
    return {"status": "matched_gate_lifecycle_pass", "classification": "measured development PPO lifecycle; no policy benefit",
            "configuration_equal_except_admission_manifest_binding_and_run_name": True,
            "initial_actor_tensors_equal": True, "arms": records,
            "full_training_enabled": False, "heldout_endpoints_opened": False,
            "analyzer_sha256": file_digest(Path(__file__))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.smoke_root.resolve())
    with args.out.open("x") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps({"status": result["status"], "initial_actor_tensors_equal": True,
                      "arms": {arm: {"completed_trials": row["result"]["completed_trials"],
                                     "rejected_completed_trials": row["result"]["final_allocation"]["rejected_completed_trials"],
                                     "post_cap_rejected_mass": row["result"]["final_allocation"]["post_cap_rejected_mass"],
                                     "elapsed_seconds": row["execution"]["elapsed_seconds"]}
                               for arm, row in result["arms"].items()}}, indent=2))
