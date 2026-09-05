#!/usr/bin/env python3
"""Continue approved E4 seeds 2–3 after the sealed seed-1 gate, then evaluate.

This orchestration layer preserves all sealed training and analysis entrypoints.
It opens no evaluator output until the complete manipulation gate passes.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from analyze_g_segment import manipulation_gate
from build_g_run_manifest import build_manifest
from check_g_seed1_manipulation import collect_run, evaluate, sha256_file

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/g_segment/confirmation"
PYTHON = ROOT / "mjlab-1.6.0/.venv/bin/python"
DESIGN = ROOT / "plan/G2_CALIBRATION_GRID.json"
CALIBRATION = ROOT / "reports/g_segment/calibration/result.json"
CONDITIONS = ROOT / "reports/g_segment/eval_conditions.json"
STRATA = ROOT / "reports/g_segment/panel/strata.csv"
PANEL = ROOT / "reports/g_segment/panel/panel_manifest.json"
ITERATIONS = (1000, 2000, 3000, 3999)


def write_once(path: Path, value: dict) -> None:
    serialized = json.dumps(value, indent=1) + "\n"
    if path.exists() and path.read_text() != serialized:
        raise ValueError(f"refusing differing overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized)


def verify_seal() -> None:
    subprocess.run(
        ["sha256sum", "--check", "--status", "plan/G_SEGMENT_FREEZE.sha256"],
        cwd=ROOT, check=True,
    )


def run_dir(seed: int, arm: str) -> Path:
    parent = OUT / f"seed{seed}/training/g1_tracking"
    candidates = [
        path for path in parent.glob(f"*_phase_g_{arm.lower()}_s{seed}")
        if (path / "model_3999_segment.json").is_file()
    ]
    if len(candidates) != 1:
        raise ValueError(f"{arm} seed {seed}: expected one completed run")
    return candidates[0]


def environment(seed: int) -> dict[str, str]:
    env = dict(os.environ)
    env.update({
        "CLIMB_BANK": str(ROOT / "bank/amass"),
        "CLIMB_CLIPS": str(ROOT / "bank/tiers/tier_800.txt"),
        "CLIMB_SEGMENT_MANIFEST": str(ROOT / "reports/g_segment/unit_table.json"),
        "CLIMB_SEGMENT_SEED": str(seed),
        "CLIMB_SEGMENT_RANK": "learning_progress",
        "CLIMB_SEGMENT_DIFFICULTY_POWER": "0",
        "CLIMB_SEGMENT_EXPLORATION_RATIO": "0.40",
        "CLIMB_SEGMENT_PROGRESS_WINDOW": "10",
        "CLIMB_SEGMENT_PROGRESS_FLOOR": "0.05",
        "CLIMB_SEGMENT_MAX_UNIT_PROBABILITY": "0.05",
        "CLIMB_SEGMENT_MAX_CLIP_PROBABILITY": "0.25",
        "CLIMB_SEGMENT_FAILURE_PENALTY": "-10",
        "CLIMB_SEGMENT_SAVE_INTERVAL": "500",
        "CLIMB_VERIFY_MOTION_HASHES": "1",
        "WANDB_MODE": "offline",
    })
    return env


def gated(command: list[str], log: Path, seed: int) -> None:
    verify_seal()
    if log.exists():
        raise ValueError(f"existing launch log; inspect before retry: {log}")
    subprocess.run(
        [str(ROOT / "tools/run_when_free.sh"), "14000", str(log), "--", *command],
        cwd=ROOT, env=environment(seed), check=True,
    )
    if not any(line.startswith("DONE rc=0 ") for line in log.read_text().splitlines()):
        raise ValueError(f"missing successful sentinel: {log}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wait-seed1", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    os.chdir(ROOT)
    verify_seal()
    if args.dry_run:
        print(json.dumps({
            "training": [{"seed": s, "arm": a, "environments": 512,
                          "iterations": 4000} for s in (2, 3) for a in ("G1", "G2")],
            "evaluation_cells": 24,
            "evaluation_iterations": ITERATIONS,
            "seed1_gate_required": "pass_for_evaluation",
            "policy_endpoints_opened": False,
        }, indent=1))
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    lock = (OUT / ".continuation.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    seed1_result = OUT / "seed1/manipulation_result.json"
    while not seed1_result.exists():
        if not args.wait_seed1:
            raise ValueError("seed-1 manipulation result is absent")
        print("WAIT seed-1 manipulation result", flush=True)
        time.sleep(30)
    recorded = json.loads(seed1_result.read_text())
    current = evaluate(run_dir(1, "G1"), run_dir(1, "G2"), DESIGN, CALIBRATION)
    if current != recorded:
        raise ValueError("seed-1 result differs from recomputed ledger-only result")
    if current["status"] != "pass_for_evaluation":
        print("STOP seed-1 manipulation failed; E4 not_tested", flush=True)
        return 2

    for seed in (2, 3):
        subprocess.run(
            [str(PYTHON), "tools/research_preflight.py", "--g2-stage", "confirmation",
             "--verify-motion-hashes", "--strict"],
            env=environment(seed), check=True,
        )
        for arm, mode in (("G1", "Uniform"), ("G2", "Adaptive")):
            name = f"phase_g_{arm.lower()}_s{seed}"
            parent = OUT / f"seed{seed}/training/g1_tracking"
            if list(parent.glob(f"*_{name}")):
                raise ValueError(f"existing {name}; refusing ambiguous rerun")
            print(f"TRAIN {arm} seed {seed}", flush=True)
            gated([
                str(PYTHON), "tools/climb_segment_train.py",
                f"Climb-Tracking-Flat-Unitree-G1-SegmentV2-{mode}",
                "--env.scene.num-envs", "512", "--agent.max-iterations", "4000",
                "--agent.logger", "tensorboard", "--agent.run-name", name,
                "--log-root", str(OUT / f"seed{seed}/training"),
            ], OUT / f"seed{seed}/logs/{name}.log", seed)

    calibration = {
        "design_path": str(DESIGN), "design_sha256": sha256_file(DESIGN),
        "result_path": str(CALIBRATION), "result_sha256": sha256_file(CALIBRATION),
    }
    manifest = {"calibration": calibration, "arms": {}}
    for arm in ("G1", "G2"):
        manifest["arms"][arm] = {"seeds": {}}
        for seed in (1, 2, 3):
            run, _ = collect_run(run_dir(seed, arm), arm)
            manifest["arms"][arm]["seeds"][str(seed)] = run
    gate = manipulation_gate(manifest)
    write_once(OUT / "manipulation_all_seeds.json", {
        "gate": gate, "policy_endpoints_opened": False,
        "status": "pass_for_evaluation" if gate["pass"] else "not_tested",
    })
    if not gate["pass"]:
        print("STOP all-seed manipulation failed; E4 not_tested", flush=True)
        return 2

    run_map = {"schema_version": "g_segment_run_map/1", "arms": {}}
    for arm in ("G1", "G2"):
        run_map["arms"][arm] = {"seeds": {}}
        for seed in (1, 2, 3):
            run = manifest["arms"][arm]["seeds"][str(seed)]
            cell = {"ledgers": [r["path"] for r in run["ledgers"]], "evaluations": {}}
            for iteration in ITERATIONS:
                checkpoint = run_dir(seed, arm) / f"model_{iteration}.pt"
                output = OUT / f"evaluation/{arm}_s{seed}_it{iteration}.csv"
                if output.exists() or Path(f"{output}.meta.json").exists():
                    raise ValueError(f"existing evaluation: {output}")
                print(f"EVALUATE {arm} seed {seed} iteration {iteration}", flush=True)
                gated([
                    str(PYTHON), "tools/eval_paired_v2.py", "--checkpoint", str(checkpoint),
                    "--clips", str(ROOT / "reports/g_segment/panel/panel.txt"),
                    "--bank", str(ROOT / "bank/amass"),
                    "--common-reference-bank", str(ROOT / "bank/amass"),
                    "--conditions", str(CONDITIONS),
                    "--episodes", "4", "--window", "3", "--seed", "20260910",
                    "--joint-noise-seed", "20260911", "--joint-noise", "0.05",
                    "--nconmax", "70", "--out", str(output),
                ], output.with_suffix(".log"), seed)
                cell["evaluations"][str(iteration)] = {
                    "csv": str(output), "checkpoint": str(checkpoint),
                }
            run_map["arms"][arm]["seeds"][str(seed)] = cell
    map_path = OUT / "run_map.json"
    write_once(map_path, run_map)
    bound = build_manifest(map_path, CONDITIONS, STRATA, PANEL, DESIGN, CALIBRATION)
    manifest_path = OUT / "run_manifest.json"
    write_once(manifest_path, bound)
    subprocess.run([
        str(PYTHON), "tools/analyze_g_segment.py", "--manifest", str(manifest_path),
        "--out", str(OUT / "result.json"),
    ], check=True)
    print("DONE E4 frozen confirmation analysis", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
