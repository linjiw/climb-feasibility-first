#!/usr/bin/env python3
"""Run fixed confirmation training, then evaluate only after all training gates pass."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import time

from analyze_relative_campaign import analyze, verify_training
from check_relative_progress_probe import sha256
from relative_confirmation_setup import ROOT, verify_contract
from run_relative_progress_study import write_once

PYTHON = ROOT / "mjlab-1.6.0/.venv/bin/python"
ARMS = ("U", "A", "R", "D")
SEEDS = (21, 22, 23)
ITERATIONS = (1000, 2000, 3000, 3999)


def record(path: Path) -> dict:
    return {"path": str(path.resolve()), "sha256": sha256(path)}


def schedule(contract: dict, path: Path, digest: str, out: Path) -> list[dict]:
    """Predeclare twelve training jobs followed by forty-eight fixed evaluations."""
    jobs = []
    for index, seed in enumerate(SEEDS):
        order = ARMS[index:] + ARMS[:index]
        for arm in order:
            cell = out / f"{arm}_s{seed}"
            run = cell / "g1_tracking" / f"relative_confirmation_{arm}_s{seed}"
            jobs.append({"stage": "train", "arm": arm, "seed": seed, "run_dir": str(run),
                         "log": str(out / f"{arm}_s{seed}.log"),
                         "argv": [str(PYTHON), str(ROOT / "tools/train_relative_confirmation.py"),
                                  "--contract", str(path.resolve()), "--contract-sha256", digest,
                                  "--arm", arm, "--seed", str(seed), "--out-dir", str(cell)]})
    conditions = json.loads(Path(contract["conditions"]["path"]).read_text())
    for seed in SEEDS:
        for arm in ARMS:
            run = out / f"{arm}_s{seed}" / "g1_tracking" / f"relative_confirmation_{arm}_s{seed}"
            for iteration in ITERATIONS:
                csv_path = out / "evaluation" / f"{arm}_s{seed}_{iteration}.csv"
                argv = [str(PYTHON), str(ROOT / "tools/eval_paired_v2.py"),
                        "--checkpoint", str(run / f"model_{iteration}.pt"),
                        "--clips", contract["panel_clips"]["path"], "--bank", contract["bank"],
                        "--common-reference-bank", contract["bank"], "--conditions", contract["conditions"]["path"],
                        "--out", str(csv_path), "--phases", ",".join(map(str, conditions["requested_phases"])),
                        "--episodes", str(conditions["episodes_per_start"]), "--window", str(conditions["window_s"]),
                        "--seed", str(conditions["environment_seed"]), "--joint-noise-seed", str(conditions["joint_noise_seed"]),
                        "--joint-noise", str(conditions["joint_noise"]), "--nconmax", str(conditions["nconmax_per_world"]),
                        "--device", "cuda:0"]
                if conditions["nominal"]:
                    argv.append("--nominal")
                jobs.append({"stage": "evaluate", "arm": arm, "seed": seed, "iteration": iteration,
                             "run_dir": str(run), "csv": str(csv_path), "log": str(csv_path.with_suffix(".log")), "argv": argv})
    return jobs


def gpu_state() -> tuple[int, int, int]:
    output = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.total,memory.used,utilization.gpu",
                                      "--format=csv,noheader,nounits"], text=True)
    return tuple(int(value.strip()) for value in output.splitlines()[0].split(","))


def run_once(job: dict, *, wait_seconds: int, validate=None, before_launch=None) -> None:
    """Wait for availability and launch once; never restart a scientific run."""
    deadline = time.monotonic() + wait_seconds
    while True:
        total, used, util = gpu_state()
        if total - used >= 14000 and util <= 60:
            if validate is not None:
                validate()
            total, used, util = gpu_state()
            if total - used >= 14000 and util <= 60:
                break
        if time.monotonic() >= deadline:
            raise TimeoutError("GPU availability deadline; job not launched")
        time.sleep(min(30, max(0, deadline - time.monotonic())))
    log = Path(job["log"])
    log.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="0", MUJOCO_GL="egl", WANDB_MODE="offline")
    if before_launch is not None:
        before_launch()
    with log.open("x") as handle:
        start = int(time.time())
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        handle.write(f"LAUNCH attempt=1 free_mib={total-used} util_pct={util} baseline_vram_mib={used} {stamp}\n")
        handle.flush()
        process = subprocess.Popen(job["argv"], cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                   stdout=handle, stderr=subprocess.STDOUT)
        peak = used
        try:
            while process.poll() is None:
                peak = max(peak, gpu_state()[1])
                time.sleep(1)
            rc = process.wait()
        except BaseException:
            process.terminate()
            process.wait()
            raise
        elapsed = int(time.time()) - start
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        handle.write(f"DONE rc={rc} attempt=1 elapsed_s={elapsed} gpu_hours={elapsed/3600:.6f} "
                     f"baseline_vram_mib={used} peak_total_vram_mib={peak} peak_delta_mib={peak-used} {stamp}\n")
    if rc:
        raise subprocess.CalledProcessError(rc, job["argv"])


def training_record(job: dict) -> dict:
    run = Path(job["run_dir"])
    return {"execution_log": record(Path(job["log"])), "evaluations": {}, "snapshots": [
        {"checkpoint": record(run / f"model_{iteration}.pt"),
         "ledger": record(run / f"model_{iteration}_segment.json"),
         "sampler": record(run / f"model_{iteration}_segment_sampler.pt")}
        for iteration in (*range(0, 4000, 100), 3999)]}


def execute(contract: dict, path: Path, digest: str, out: Path, wait_seconds: int) -> dict:
    """Require every training manipulation pass before opening any policy endpoint."""
    out.mkdir(parents=True, exist_ok=False)
    jobs = schedule(contract, path, digest, out)
    write_once(out / "schedule.json", {"campaign_contract_sha256": digest, "jobs": jobs})
    manifest = {"schema_version": "relative_campaign_manifest/1", "contract": record(path),
                "arms": {arm: {} for arm in ARMS}}
    opened = False
    completed = []

    def open_endpoints():
        nonlocal opened
        if not opened:
            write_once(out / "endpoint_access.json", {"all_twelve_training_gates_passed": True,
                                                       "campaign_contract_sha256": digest})
            opened = True

    try:
        for job in jobs:
            # Recheck bindings immediately before each queued job; train entrypoint
            # independently repeats the full launch checks as well.
            verify_contract(path, digest)
            run_once(job, wait_seconds=wait_seconds, validate=lambda: verify_contract(path, digest),
                     before_launch=open_endpoints if job["stage"] == "evaluate" else None)
            arm, seed = job["arm"], str(job["seed"])
            if job["stage"] == "train":
                run = training_record(job)
                checked = verify_training(run, contract, digest, arm=arm, seed=job["seed"])
                write_once(out / f"{arm}_s{seed}_training_gate.json", {k: v for k, v in checked.items() if k != "checkpoint_links"})
                manifest["arms"][arm][seed] = run
            else:
                run, iteration = Path(job["run_dir"]), job["iteration"]
                manifest["arms"][arm][seed]["evaluations"][str(iteration)] = {
                    "csv": record(Path(job["csv"])), "metadata": record(Path(job["csv"] + ".meta.json")),
                    "checkpoint": record(run / f"model_{iteration}.pt"),
                    "ledger": record(run / f"model_{iteration}_segment.json")}
            completed.append({k: job[k] for k in ("stage", "arm", "seed")})
        manifest_path = out / "campaign_manifest.json"
        write_once(manifest_path, manifest)
        result = analyze(manifest_path)
        write_once(out / "analysis.json", result)
        status = "completed" if result["status"] not in ("invalid", "not_tested") else result["status"]
        terminal = {"status": status, "analysis_status": result["status"]}
    except Exception as exc:
        write_once(out / "partial_manifest.json", manifest)
        terminal = {"status": "execution_stopped", "reason": str(exc)}
    terminal.update(policy_endpoints_opened=opened, completed_jobs=completed)
    write_once(out / "terminal_status.json", terminal)
    return terminal


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--gpu-wait-seconds", type=int, default=7200)
    args = parser.parse_args()
    if args.gpu_wait_seconds <= 0:
        parser.error("GPU wait must be positive")
    checked = verify_contract(args.contract, args.contract_sha256)
    terminal = execute(checked, args.contract.resolve(), args.contract_sha256, args.out_dir.resolve(), args.gpu_wait_seconds)
    print(json.dumps(terminal))
    if terminal["status"] != "completed":
        raise SystemExit(1)
