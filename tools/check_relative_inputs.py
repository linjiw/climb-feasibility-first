#!/usr/bin/env python3
"""Audit R3 reference inputs on CPU without constructing a simulator or policy."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import subprocess

from check_relative_progress_probe import sha256
from eval_paired_v2 import build_conditions, motion_metadata, read_names, software_versions
from research_preflight import check_clip_list, check_eval_inputs, check_motion_bank, load_unit_table
from restore_phase_g_bank import load_requirements

ROOT = Path(__file__).resolve().parents[1]


def verify_conditions(saved: dict, metadata: list[dict]) -> None:
    """Reconstruct every start, replicate, world identity and horizon from inputs."""
    rebuilt = build_conditions(metadata, saved["requested_phases"], saved["episodes_per_start"],
                               saved["window_s"], saved["environment_seed"], saved["joint_noise_seed"],
                               saved["joint_noise"], saved["nominal"], saved["nconmax_per_world"])
    if any(saved.get(key) != value for key, value in rebuilt.items()):
        raise ValueError("evaluation conditions do not reconstruct from current motion headers")
    if (len(metadata) != 100 or saved["window_s"] != 3.0 or len(saved["conditions"]) != 2800
            or any(row["horizon_steps"] != 150 or row["full_window"] is not True for row in saved["conditions"])):
        raise ValueError("not the fixed 100-clip, 2800-condition, 150-step panel")


def audit(bank: Path) -> dict:
    """Verify only reference inputs; this cannot authorize confirmation training."""
    subprocess.run(["sha256sum", "--status", "-c", "plan/G_SEGMENT_FREEZE.sha256"], cwd=ROOT, check=True)
    files = {"unit_table": ROOT / "reports/g_segment/unit_table.json",
             "training_clips": ROOT / "bank/tiers/tier_800.txt",
             "panel": ROOT / "reports/g_segment/panel/panel.txt",
             "panel_manifest": ROOT / "reports/g_segment/panel/panel_manifest.json",
             "conditions": ROOT / "reports/g_segment/eval_conditions.json",
             "strata": ROOT / "reports/g_segment/panel/strata.csv",
             "strata_manifest": ROOT / "reports/g_segment/panel/strata.manifest.json",
             "phase_g_seal": ROOT / "plan/G_SEGMENT_FREEZE.sha256"}
    table, first = load_unit_table(files["unit_table"])
    if table is None:
        raise ValueError(first.detail)
    checks = [first, check_clip_list(table, files["training_clips"]),
              *check_eval_inputs(files["panel"], files["panel_manifest"], files["conditions"], files["strata"])]
    requirements, counts, _ = load_requirements(files["unit_table"], files["panel_manifest"], scope="full")
    if counts != {"training": 800, "evaluation": 100, "unique": 900}:
        raise ValueError("unexpected input population or name overlap")
    panel = json.loads(files["panel_manifest"].read_text())
    training_hashes = {row["motion_sha256"] for row in table["sources"]}
    if training_hashes.intersection(panel["motion_sha256"].values()):
        raise ValueError("training/evaluation motion content overlaps")
    checks.append(check_motion_bank(requirements, counts, bank, scope="full", verify_hashes=True))
    if any(check.status != "ok" for check in checks):
        raise ValueError("; ".join(check.detail for check in checks if check.status != "ok"))
    saved = json.loads(files["conditions"].read_text())
    verify_conditions(saved, motion_metadata(read_names(files["panel"]), bank))
    if saved["panel_txt_sha256"] != sha256(files["panel"]):
        raise ValueError("condition panel identity mismatch")
    sources = ("tools/check_relative_inputs.py", "tools/research_preflight.py", "tools/restore_phase_g_bank.py",
               "tools/eval_paired_v2.py", "tools/check_relative_progress_probe.py")
    return {"schema_version": "relative_reference_audit/1", "status": "input_audit_pass",
            "classification": "reference-input verification only; no policy evidence",
            "confirmation_ready": False, "policy_endpoints_opened": False, "simulator_constructed": False,
            "checks": [asdict(check) for check in checks], "conditions_reconstructed": 2800,
            "training_evaluation_content_overlap": 0,
            "inputs": {key: {"path": str(path), "sha256": sha256(path)} for key, path in files.items()},
            "bank": str(bank.resolve()), "verified_motion_sha256": requirements,
            "software_versions": software_versions(),
            "source_sha256": {name: sha256(ROOT / name) for name in sources},
            "remaining": ["four-arm lifecycle and D calibration results", "confirmation execution and prospective freeze",
                          "complete runtime/source and robot-asset audit"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, default=ROOT / "bank/amass")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.bank)
    except Exception as exc:
        result = {"status": "invalid", "reason": str(exc), "confirmation_ready": False,
                  "policy_endpoints_opened": False, "simulator_constructed": False}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({key: result[key] for key in ("status", "confirmation_ready")}))
    if result["status"] != "input_audit_pass":
        raise SystemExit(1)
