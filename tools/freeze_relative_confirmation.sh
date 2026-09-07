#!/usr/bin/env bash
# Finalize a new prospective contract only after all fixed prerequisites pass.
# This administrative shell entrypoint is bound explicitly in the new contract
# and seal; it does not alter the Python runtime inventory used by queued smokes.
set -euo pipefail
freeze_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
exec "$freeze_root/mjlab-1.6.0/.venv/bin/python" - "$freeze_root" "$freeze_root/tools/freeze_relative_confirmation.sh" "$@" <<'PY'
from copy import deepcopy
from datetime import datetime
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

root, script = Path(sys.argv[1]), Path(sys.argv[2])
os.chdir(root)
sys.path.insert(0, str(root / "tools"))
from relative_confirmation_setup import build_configs, config_digest, fixed_profiles, verify_contract, verify_prerequisites
from relative_policy_provenance import verified
from run_relative_confirmation import record, schedule
from run_relative_progress_study import write_once
from train_relative_confirmation import verify_entrypoint_smoke


def resolve_pending(entry, label, missing):
    if set(entry) == {"pending_path"}:
        path = Path(entry["pending_path"]).resolve()
        if not path.is_file():
            missing[label] = str(path)
            return entry
        return record(path)
    verified(entry, label)
    return entry


def main():
    parser = argparse.ArgumentParser(description="Verify prerequisites and create a new prospective freeze; never launch jobs.")
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--draft-sha256", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args(sys.argv[3:])
    script_record = record(script)
    draft_path = args.draft.resolve()
    draft_record = {"path": str(draft_path), "sha256": args.draft_sha256}
    draft = verify_contract(draft_path, args.draft_sha256, smoke=True)
    contract = deepcopy(draft)
    missing = {}
    smokes = contract["four_arm_smokes"]
    smokes["design"] = resolve_pending(smokes["design"], "development smoke design", missing)
    for arm in ("U", "A", "R", "D"):
        smokes["decisions"][arm] = resolve_pending(smokes["decisions"][arm], f"development {arm} seed41", missing)
        contract["entrypoint_smokes"][arm] = resolve_pending(contract["entrypoint_smokes"][arm], f"entrypoint {arm} seed51", missing)
    for seed in (31, 32):
        entry = contract["failure_calibration"][str(seed)]
        for key in ("decision", "execution_design"):
            entry[key] = resolve_pending(entry[key], f"D seed{seed} {key}", missing)
    decisions = [(entry, "smoke_pass") for entry in smokes["decisions"].values()]
    decisions += [(entry, "entrypoint_smoke_pass") for entry in contract["entrypoint_smokes"].values()]
    decisions += [(entry["decision"], "calibration_pass") for entry in contract["failure_calibration"].values()]
    for entry, expected in decisions:
        if "pending_path" not in entry and json.loads(verified(entry, "prerequisite decision").read_text()).get("status") != expected:
            raise ValueError("an available prerequisite has not passed")
    if missing:
        print(json.dumps({"status": "prerequisites_pending", "missing": missing,
                          "confirmation_enabled": False, "files_written": 0, "jobs_launched": 0}, indent=2))
        return 2
    verify_prerequisites(contract)
    for arm in ("U", "A", "R", "D"):
        saved = json.loads(verified(contract["entrypoint_smokes"][arm], "entrypoint decision").read_text())
        if saved["draft_contract"] != draft_record:
            raise ValueError("entrypoint smoke binds a different draft")
        if verify_entrypoint_smoke(Path(saved["run_dir"]), draft, draft_record, arm) != saved:
            raise ValueError("entrypoint smoke does not reproduce")
    profiles = fixed_profiles(verified(contract["profiles"], "profiles"))
    for arm in ("U", "A", "R", "D"):
        for seed in (21, 22, 23):
            identity = config_digest(*build_configs(arm, seed, profiles, contract))
            if identity != contract["configuration_sha256"][arm][str(seed)]:
                raise ValueError("configuration changed from the bound draft")
    verified(script_record, "freeze entrypoint")
    if args.check_only:
        print(json.dumps({"status": "ready_to_freeze", "confirmation_enabled": False,
                          "files_written": 0, "jobs_launched": 0}))
        return 0
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    try:
        enabled = deepcopy(profiles)
        enabled["confirmation"]["enabled"] = True
        profile_path = out / "profiles.json"
        write_once(profile_path, enabled)
        contract["profiles"] = record(profile_path)
        contract["status"] = "frozen_before_confirmation"
        contract["classification"] = "prospective simulation confirmation; no policy result"
        if "SYNTHETIC" in draft.get("classification", ""):
            contract["classification"] = "SYNTHETIC TEST FIXTURE ONLY; never launch"
        contract["freeze_provenance"] = {"draft": draft_record, "entrypoint": script_record,
                                          "created_at": datetime.now().astimezone().isoformat()}
        # The administrator is not a simulator dependency. Bind it explicitly so
        # production launch verification also checks the finalized script identity.
        contract["training_sources"]["tools/freeze_relative_confirmation.sh"] = script_record
        contract_path = out / "contract.json"
        write_once(contract_path, contract)
        contract_record = record(contract_path)
        verify_contract(contract_path, contract_record["sha256"])
        jobs = schedule(contract, contract_path, contract_record["sha256"], out / "campaign")
        schedule_path = out / "schedule.json"
        write_once(schedule_path, {"campaign_contract_sha256": contract_record["sha256"], "jobs": jobs})
        launch = {"argv": [str(root / "mjlab-1.6.0/.venv/bin/python"),
                            str(root / "tools/run_relative_confirmation.py"),
                            "--contract", str(contract_path), "--contract-sha256", contract_record["sha256"],
                            "--out-dir", str(out / "campaign")], "jobs_launched": 0}
        write_once(out / "launch_command.json", launch)
        receipt_path = out / "freeze_result.json"
        write_once(receipt_path, {"status": "frozen_before_confirmation", "contract": contract_record,
                   "source_draft": draft_record, "freeze_entrypoint": script_record,
                   "configuration_digests_verified": 12, "training_jobs": 12, "evaluation_jobs": 48,
                   "all_prerequisites_reproduced": True, "policy_endpoints_opened": False, "jobs_launched": 0})
        paths = (profile_path, contract_path, schedule_path, out / "launch_command.json", receipt_path,
                 Path(contract["runtime_inventory"]["path"]), script)
        seal = out / "confirmation.sha256"
        with seal.open("x") as handle:
            for path in paths:
                item = record(path)
                handle.write(f"{item['sha256']}  {item['path']}\n")
        subprocess.run(["sha256sum", "--status", "-c", str(seal)], check=True)
        print(json.dumps({"status": "frozen_before_confirmation", "contract": contract_record,
                          "seal": record(seal), "jobs_launched": 0}, indent=2))
        return 0
    except Exception as exc:
        write_once(out / "freeze_failure.json", {"status": "freeze_failed", "reason": str(exc), "jobs_launched": 0})
        raise


if __name__ == "__main__":
    raise SystemExit(main())
PY
