#!/usr/bin/env python3
"""Queue a fixed GPU development batch after confirmation and its noise pilot."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_once(path: Path, value: dict) -> None:
    with path.open("x") as handle:
        handle.write(json.dumps(value, indent=2) + "\n")


def verify_design(path: Path, digest: str) -> dict:
    if sha256(path) != digest:
        raise ValueError("GPU queue design changed")
    design = json.loads(path.read_text())
    if (design["stage"] != "device_lifecycle_development" or design["full_evaluation_enabled"] is not False
            or design["evaluator_arguments"]["device"] != "cuda:0" or design["queue"]["automatic_retries"] != 0):
        raise ValueError("requires a fixed single-attempt GPU development design")
    for name, expected in design["bindings"].items():
        if sha256(Path(name)) != expected:
            raise ValueError(f"GPU queue dependency changed: {name}")
    cpu = json.loads(Path(design["queue"]["cpu_verification"]).read_text())
    if cpu["status"] != "device_lifecycle_pass" or cpu["device"] != "cpu":
        raise ValueError("CPU entrypoint smoke did not pass")
    return design


def prerequisites_ready(queue: dict) -> bool:
    ready = True
    for prerequisite in queue["prerequisites"]:
        path = Path(prerequisite["path"])
        if not path.exists():
            ready = False
            continue
        value = json.loads(path.read_text())
        if value.get("status") != prerequisite["status"]:
            raise ValueError(f"prerequisite stopped: {path}: {value.get('status')}")
        if "completed_jobs" in prerequisite:
            if value.get("completed_jobs") != prerequisite["completed_jobs"] or value.get("policy_endpoints_opened") is not True:
                raise ValueError("confirmation completion does not match bound schedule")
        if prerequisite.get("stationarity_established") is False and value.get("stationarity_established") is not False:
            raise ValueError("pilot completion metadata changed")
    return ready


def gpu_available() -> bool:
    text = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.free,utilization.gpu",
                                    "--format=csv,noheader,nounits"], text=True)
    free, utilization = map(int, text.splitlines()[0].split(","))
    return free >= 14000 and utilization <= 60


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--design-sha256", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    design = verify_design(args.design, args.design_sha256)
    queue = design["queue"]
    args.out_dir.mkdir(parents=True, exist_ok=False)
    write_once(args.out_dir / "launch.json", {"design": str(args.design), "sha256": args.design_sha256,
                                             "started": datetime.now().astimezone().isoformat(),
                                             "priority": "after confirmation and frozen-policy pilot"})
    stage = "waiting_for_confirmation_and_pilot"
    completed = []
    try:
        print(stage, flush=True)
        deadline = time.monotonic() + queue["prerequisite_wait_seconds"]
        while not prerequisites_ready(queue):
            if time.monotonic() >= deadline:
                raise TimeoutError("prerequisite wait deadline; no GPU job launched")
            time.sleep(30)
        for job in queue["jobs"]:
            stage = f"waiting_for_gpu:{job['condition']}"
            deadline = time.monotonic() + queue["gpu_wait_seconds"]
            while True:
                verify_design(args.design, args.design_sha256)
                if not prerequisites_ready(queue):
                    raise ValueError("prerequisite completion disappeared")
                if gpu_available():
                    verify_design(args.design, args.design_sha256)
                    if gpu_available():
                        break
                if time.monotonic() >= deadline:
                    raise TimeoutError("GPU wait deadline; no automatic retry")
                time.sleep(30)
            stage = f"running:{job['condition']}"
            print(stage, flush=True)
            argv = [queue["python"], queue["entrypoint"], "--design", str(args.design),
                    "--design-sha256", args.design_sha256, "--condition", job["condition"],
                    "--out-dir", job["out_dir"]]
            write_once(args.out_dir / f"{job['condition']}_launch.json", {
                "argv": argv, "cwd": design["root"], "attempt": 1,
                "started": datetime.now().astimezone().isoformat()})
            with (args.out_dir / f"{job['condition']}.log").open("x") as handle:
                subprocess.run(argv, cwd=design["root"], env=dict(os.environ, CUDA_VISIBLE_DEVICES="0"),
                               stdout=handle, stderr=subprocess.STDOUT, check=True)
            completed.append(job["condition"])
        stage = "analyzing_saved_traces"
        verify_design(args.design, args.design_sha256)
        with (args.out_dir / "analysis.log").open("x") as handle:
            subprocess.run(queue["analysis_argv"], cwd=design["root"],
                           stdout=handle, stderr=subprocess.STDOUT, check=True)
        result = json.loads(Path(queue["analysis_output"]).read_text())
        if result["status"] != "device_lifecycle_pass" or result["device"] != "cuda:0":
            raise ValueError("GPU lifecycle coverage did not pass")
        terminal = {"status": "gpu_development_lifecycle_completed", "analysis_sha256": sha256(Path(queue["analysis_output"]))}
    except Exception as exc:
        terminal = {"status": "execution_stopped", "reason": str(exc)}
    terminal.update(stage=stage, completed_cells=completed, automatic_retries=0,
                    full_evaluation_enabled=False, design_sha256=args.design_sha256)
    write_once(args.out_dir / "terminal_status.json", terminal)
    print(json.dumps(terminal), flush=True)
    if terminal["status"] != "gpu_development_lifecycle_completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
