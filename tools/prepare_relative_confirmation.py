#!/usr/bin/env python3
"""Write a non-executable confirmation draft with exact configs and job commands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from check_relative_progress_probe import sha256
from relative_confirmation_setup import ROOT, PROFILE_PATH, build_configs, config_digest, fixed_profiles, runtime_inventory
from run_relative_confirmation import record, schedule
from run_relative_progress_study import write_once


def pending_or_record(path: Path) -> dict:
    return record(path) if path.is_file() else {"pending_path": str(path.resolve())}


def prepare(out: Path, report_root: Path, entrypoint_smokes: Path | None = None) -> dict:
    """Prepare reviewable artifacts; never enable profiles, seal files, or launch jobs."""
    out.mkdir(parents=True, exist_ok=False)
    entrypoint_smokes = entrypoint_smokes or report_root / "confirmation_entrypoint_smokes"
    audit_path = report_root / "replication_reference_audit.json"
    inputs = json.loads(audit_path.read_text())
    if inputs["status"] != "input_audit_pass":
        raise ValueError("reference audit must pass before draft preparation")
    runtime = runtime_inventory()
    write_once(out / "runtime_inventory.json", runtime)
    training_names = ("tools/train_relative_confirmation.py", "tools/relative_confirmation_setup.py",
                      "tools/climb_segment_train.py", "climb/relative_progress.py", "climb/segment_runtime.py",
                      "climb/segment_curriculum.py", "climb/segment_command.py", "climb/segment_env_cfg.py")
    evaluator_names = ("climb/commands.py", "climb/env_cfg.py", "climb/motion_bank.py", "climb/contact_timing.py",
                       "mjlab-1.6.0/src/mjlab/envs/manager_based_rl_env.py",
                       "mjlab-1.6.0/src/mjlab/tasks/tracking/mdp/commands.py")
    analysis_names = ("analyze_relative_campaign.py", "analyze_relative_policy.py", "relative_policy_provenance.py",
                      "relative_policy_secondaries.py", "analyze_relative_cost.py")
    contract = {"schema_version": "relative_confirmation_contract/1", "status": "draft",
                "classification": "prospective preparation only; not a freeze or launch authorization",
                "profiles": record(PROFILE_PATH), "bank": inputs["bank"],
                **{key: inputs["inputs"][key] for key in ("unit_table", "training_clips", "panel", "conditions", "strata")},
                "panel": inputs["inputs"]["panel"], "panel_manifest": inputs["inputs"]["panel_manifest"],
                "reference_audit": record(audit_path), "runtime_inventory": record(out / "runtime_inventory.json"),
                "software_versions": runtime["software_versions"],
                "training_entrypoint": record(ROOT / "tools/train_relative_confirmation.py"),
                "evaluator": record(ROOT / "tools/eval_paired_v2.py"),
                "evaluator_adapter": record(ROOT / "tools/eval_relative_confirmation.py"),
                "training_sources": {name: record(ROOT / name) for name in training_names},
                "analysis_sources": {name: record(ROOT / "tools" / name) for name in analysis_names},
                "evaluator_sources": {name: record(ROOT / name) for name in evaluator_names},
                "configuration_sha256": {}, "relative_replication": {}, "failure_calibration": {}}
    contract["entrypoint_smokes"] = {arm: pending_or_record(entrypoint_smokes / f"{arm}_result.json")
                                    for arm in ("U", "A", "R", "D")}
    # The campaign analyzer's panel field binds JSON reference identities. The
    # executable panel list is separate to avoid confusing the two representations.
    contract["panel_clips"] = inputs["inputs"]["panel"]
    contract["panel"] = inputs["inputs"]["panel_manifest"]
    profiles = fixed_profiles(PROFILE_PATH)
    for arm in ("U", "A", "R", "D"):
        contract["configuration_sha256"][arm] = {}
        for seed in (21, 22, 23):
            env, agent = build_configs(arm, seed, profiles, contract)
            contract["configuration_sha256"][arm][str(seed)] = config_digest(env, agent)
    for seed, path in ((11, report_root / "study_s11"), (12, report_root / "continuation_gate_retry/study_s12")):
        contract["relative_replication"][str(seed)] = {"study_dir": str(path), "decision": record(path / "long_result.json")}
    smokes = report_root / "policy_smokes_gate_retry"
    contract["four_arm_smokes"] = {"design": pending_or_record(smokes / "design.json"),
                                  "decisions": {arm: pending_or_record(smokes / f"{arm}_result.json") for arm in ("U", "A", "R", "D")}}
    calibration = report_root / "failure_calibration_gate_retry"
    for seed in (31, 32):
        contract["failure_calibration"][str(seed)] = {"decision": pending_or_record(calibration / f"seed{seed}_result.json"),
                                                     "execution_design": pending_or_record(calibration / "design.json")}
    path = out / "draft_contract.json"
    write_once(path, contract)
    jobs = schedule(contract, path, sha256(path), out / "NOT_LAUNCHED_campaign")
    write_once(out / "schedule_preview.json", {"status": "draft_non_executable", "jobs": jobs,
                "note": "These commands intentionally fail the draft-contract gate; freeze only after validation."})
    write_once(out / "entrypoint_smoke_preview.json", {"seed": 51, "num_envs": 8, "iterations": 20,
                "after": "fixed D calibration", "jobs": [
                    {"arm": arm, "argv": [str(ROOT / "mjlab-1.6.0/.venv/bin/python"),
                      str(ROOT / "tools/train_relative_confirmation.py"), "--contract", str(path),
                      "--contract-sha256", sha256(path), "--arm", arm, "--seed", "51", "--smoke",
                      "--out-dir", str(entrypoint_smokes / arm)]}
                    for arm in ("U", "A", "R", "D")]})
    summary = {"status": "prepared_not_frozen", "confirmation_enabled": False, "jobs_launched": 0,
               "configuration_count": 12, "training_jobs": 12, "evaluation_jobs": 48,
               "runtime_file_count": len(runtime["files"]), "g1_asset_count": runtime["g1_asset_count"],
               "draft_contract": record(path), "policy_endpoints_opened": False,
               "remaining": ["four-arm development smokes and fixed D calibration",
                             "simulator smoke of the new confirmation entrypoint and checkpoint ledger",
                             "complete frozen-contract/evaluator integration audit and prospective freeze"]}
    write_once(out / "preparation_result.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--report-root", type=Path, default=ROOT / "reports/relative_progress_2026-09-05")
    parser.add_argument("--entrypoint-smokes-dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.out_dir.resolve(), args.report_root.resolve(),
                             args.entrypoint_smokes_dir.resolve() if args.entrypoint_smokes_dir else None), indent=2))
