#!/usr/bin/env python3
"""Validate the new confirmation entrypoint after fixed D calibration passes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

from check_relative_progress_probe import sha256
from continue_relative_progress import wait_for_terminal
from relative_confirmation_setup import ROOT, verify_contract
from run_relative_confirmation import PYTHON, record, run_once
from run_relative_failure_calibration import verify_calibration
from run_relative_progress_study import write_once
from train_relative_confirmation import verify_entrypoint_smoke


def verify_baseline(directory: Path) -> None:
    terminal = json.loads((directory / "terminal_status.json").read_text())
    if terminal["status"] != "baseline_calibration_pass":
        raise ValueError("fixed D calibration prerequisite did not pass")
    design = json.loads((directory / "design.json").read_text())
    for seed in (31, 32):
        saved = json.loads((directory / f"seed{seed}_result.json").read_text())
        parents = {Path(name).parent for name in saved["bindings"]}
        if (len(parents) != 1 or verify_calibration(parents.pop(), seed, design["sources"]) != saved
                or saved["status"] != "calibration_pass"):
            raise ValueError("fixed D calibration does not reproduce")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--draft-sha256", required=True)
    parser.add_argument("--calibration-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--wait-seconds", type=int, default=21600)
    args = parser.parse_args()
    if args.wait_seconds <= 0:
        parser.error("wait budget must be positive")
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    write_once(out / "design.json", {"classification": "entrypoint lifecycle only; no policy benefit",
               "draft_contract": {"path": str(args.draft.resolve()), "sha256": args.draft_sha256},
               "calibration_dir": str(args.calibration_dir.resolve()), "arms": ["U", "A", "R", "D"],
               "seed": 51, "num_envs": 8, "iterations": 20,
               "supervisor_sha256": sha256(Path(__file__)), "policy_endpoints_opened": False})
    try:
        print("Waiting for both fixed D calibration passes", flush=True)
        wait_for_terminal(args.calibration_dir, time.monotonic() + args.wait_seconds, None)
        verify_baseline(args.calibration_dir)
        for arm in ("U", "A", "R", "D"):
            contract = verify_contract(args.draft, args.draft_sha256, smoke=True)
            cell = out / arm
            job = {"log": str(out / f"{arm}.log"), "argv": [str(PYTHON), str(ROOT / "tools/train_relative_confirmation.py"),
                   "--contract", str(args.draft.resolve()), "--contract-sha256", args.draft_sha256,
                   "--arm", arm, "--seed", "51", "--smoke", "--out-dir", str(cell)]}
            write_once(out / f"{arm}_launch.json", job)
            run_once(job, wait_seconds=args.wait_seconds,
                     validate=lambda: verify_contract(args.draft, args.draft_sha256, smoke=True))
            saved = json.loads((cell / "smoke_result.json").read_text())
            if verify_entrypoint_smoke(Path(saved["run_dir"]), contract, record(args.draft), arm) != saved:
                raise ValueError("new entrypoint smoke does not reproduce")
            write_once(out / f"{arm}_result.json", saved)
            print(f"{arm}: entrypoint_smoke_pass", flush=True)
        result = {"status": "four_arm_entrypoint_smoke_pass", "next": "final contract audit and prospective freeze"}
    except Exception as exc:
        result = {"status": "execution_stopped", "reason": str(exc)}
    result["policy_endpoints_opened"] = False
    write_once(out / "terminal_status.json", result)
    print(json.dumps(result), flush=True)
    if result["status"] != "four_arm_entrypoint_smoke_pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
