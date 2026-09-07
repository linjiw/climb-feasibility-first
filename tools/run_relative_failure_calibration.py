#!/usr/bin/env python3
"""Validate the single fixed D baseline on fresh seeds after four-arm smokes."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import torch

from check_relative_progress_probe import sha256
from continue_relative_progress import wait_for_gpu, wait_for_terminal
from run_relative_policy_smokes import verify_smoke
from run_relative_progress_study import write_once
from train_relative_policy import CONTRACT, profile
from climb.segment_runtime import SegmentSampler

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / "mjlab-1.6.0/.venv/bin/python"
MANIFEST = ROOT / "reports/g_segment/unit_table.json"
TRAINING_SOURCES = ("tools/train_relative_policy.py", "climb/relative_progress.py",
                    "climb/segment_runtime.py", "climb/segment_curriculum.py",
                    "climb/segment_command.py", "climb/segment_env_cfg.py")


def verify_calibration(run: Path, seed: int, sources: dict[str, str]) -> dict:
    """Reproduce every saved D distribution and enforce fixed long-run gates."""
    contract, selected = profile("D", "calibration", seed)
    paths = list(run.glob("model_*_segment.json"))
    ledgers = [json.loads(path.read_text()) for path in paths]
    if sorted(row["iteration"] for row in ledgers) != [*range(0, 4000, 100), 3999]:
        raise ValueError("calibration requires all 41 ledger snapshots")
    for name, digest in sources.items():
        if sha256(ROOT / name) != digest:
            raise ValueError(f"source changed: {name}")
    sampler = SegmentSampler(MANIFEST, mode="adaptive", seed=seed, rank="failure",
                             exploration_ratio=0.8, difficulty_power=1.0,
                             progress_window=10, progress_floor=0.0,
                             max_unit_probability=0.05, max_clip_probability=0.25)
    base = sampler.deployment_mass.double()
    base /= base.sum()
    rows = []
    bindings = {}
    previous_trials = -1
    for path, ledger in sorted(zip(paths, ledgers), key=lambda pair: pair[1]["iteration"]):
        expected = {"relative_policy_arm": "D", "relative_policy_stage": "calibration", "num_envs": 512,
                    "profile": selected, "profile_contract_sha256": sha256(CONTRACT),
                    "training_entrypoint_sha256": sources["tools/train_relative_policy.py"],
                    "source_hashes_at_launch": {name: sources[name] for name in TRAINING_SOURCES}}
        if any(ledger.get(key) != value for key, value in expected.items()):
            raise ValueError("calibration identity/profile/source mismatch")
        segment = ledger["segment"]
        expected_segment = {"training_seed": seed, "sampler_seed": seed, "horizon_steps": 50,
                            "unit_table_sha256": contract["unit_table_sha256"],
                            **{key: selected[key] for key in ("mode", "rank", "exploration_ratio",
                                                              "difficulty_power", "progress_floor")},
                            **{key: contract["common"][key] for key in ("progress_window",
                                              "max_unit_probability", "max_clip_probability")}}
        if any(segment.get(key) != value for key, value in expected_segment.items()):
            raise ValueError("actual sampler settings differ from fixed D profile")
        checkpoint = run / f"model_{ledger['iteration']}.pt"
        if ledger["checkpoint"] != {"path": str(checkpoint.resolve()), "sha256": sha256(checkpoint)}:
            raise ValueError("checkpoint identity mismatch")
        state_path = run / f"model_{ledger['iteration']}_segment_sampler.pt"
        state = torch.load(state_path, map_location="cpu", weights_only=True)
        if state["iteration"] != ledger["iteration"]:
            raise ValueError("state iteration mismatch")
        sampler.load_state_dict(state["sampler"])
        probabilities = torch.tensor(segment["probabilities"], dtype=torch.float64)
        if not torch.equal(probabilities, sampler.probabilities):
            raise ValueError("D probabilities do not replay")
        for key in ("invalid_start_count", "invalid_reference_frame_count", "censored_resets"):
            if segment[key] != 0:
                raise ValueError(f"nonzero {key}")
        trials = int(sampler.lifetime_attempts.sum())
        if (segment["completed_trials"] != trials or trials < previous_trials
                or segment["failed_trials"] != int(sampler.lifetime_failures.sum())):
            raise ValueError("trial accounting mismatch")
        previous_trials = trials
        clip_mass = torch.bincount(sampler.intervals.clip_ids, weights=probabilities)
        if (bool((probabilities + 1e-12 < 0.8 * base).any())
                or float(probabilities.max()) > 0.05 + 1e-12 or float(clip_mass.max()) > 0.25 + 1e-12):
            raise ValueError("probability floor/cap violation")
        concentration = sampler.concentration()
        rows.append({"iteration": ledger["iteration"], "tv": sampler.adaptation_total_variation(),
                     "effective_units": concentration.entropy_effective_units,
                     "top1_unit_mass": concentration.top1_probability,
                     "max_clip_mass": float(clip_mass.max()),
                     "saturation": sampler.saturation_fraction(), "completed_trials": trials})
        bindings[str(path)] = {"ledger": sha256(path), "state": sha256(state_path),
                               "checkpoint": ledger["checkpoint"]["sha256"]}
    if previous_trials <= 0:
        raise ValueError("no completed calibration trials")
    selected_rows = [row for row in rows if row["iteration"] >= 400]
    mean_tv = sum(row["tv"] for row in selected_rows) / len(selected_rows)
    gates = {"mean_tv": mean_tv, "tv_pass": mean_tv >= contract["calibration"]["minimum_mean_tv"],
             "effective_units_pass": min(row["effective_units"] for row in selected_rows) >= 12,
             "saturation_pass": rows[-1]["saturation"] < 0.9}
    passed = all(value for key, value in gates.items() if key.endswith("_pass"))
    return {"schema_version": "relative_failure_calibration/1", "seed": seed,
            "status": "calibration_pass" if passed else "calibration_fail",
            "classification": "exploratory fixed-baseline manipulation calibration",
            "policy_endpoints_opened": False, "gate": gates, "snapshots": rows, "bindings": bindings,
            "profile_contract_sha256": sha256(CONTRACT), "verifier_sha256": sha256(Path(__file__))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--wait-seconds", type=int, default=21600)
    args = parser.parse_args()
    if args.wait_seconds <= 0:
        parser.error("wait budget must be positive")
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    names = (*TRAINING_SOURCES, "tools/run_relative_failure_calibration.py",
             "tools/run_relative_policy_smokes.py", "tools/continue_relative_progress.py",
             "tools/run_when_free.sh", "tools/climb_segment_train.py",
             "plan/R3_BASELINE_CONTRACT_2026-09-05.json")
    sources = {name: sha256(ROOT / name) for name in names}
    write_once(out / "design.json", {"schema_version": "relative_failure_execution/1", "sources": sources,
                                    "arm": "D", "seeds": [31, 32], "num_envs": 512, "iterations": 4000,
                                    "prerequisite": str(args.smoke_dir.resolve()),
                                    "policy_endpoints_opened": False, "selection": "none; fixed candidate pass/fail"})
    deadline = time.monotonic() + args.wait_seconds
    try:
        print("Waiting for verified four-arm lifecycle smokes", flush=True)
        wait_for_terminal(args.smoke_dir, deadline, None)
        terminal = json.loads((args.smoke_dir / "terminal_status.json").read_text())
        if terminal["status"] != "four_arm_smoke_pass":
            raise ValueError("four-arm smoke prerequisite failed")
        smoke_design = json.loads((args.smoke_dir / "design.json").read_text())
        for arm in ("U", "A", "R", "D"):
            saved = json.loads((args.smoke_dir / f"{arm}_result.json").read_text())
            parents = {Path(name).parent for name in saved["bindings"]}
            if len(parents) != 1 or verify_smoke(parents.pop(), arm, smoke_design["sources"]) != saved:
                raise ValueError(f"{arm} smoke does not reproduce")
        for seed in (31, 32):
            for name, digest in sources.items():
                if sha256(ROOT / name) != digest:
                    raise ValueError(f"source changed while waiting: {name}")
            wait_for_gpu(deadline)
            env = dict(os.environ, CLIMB_BANK=str(ROOT / "bank/amass"),
                       CLIMB_CLIPS=str(ROOT / "bank/tiers/tier_800.txt"),
                       CLIMB_SEGMENT_MANIFEST=str(MANIFEST), CLIMB_POLICY_ARM="D",
                       CLIMB_POLICY_STAGE="calibration", CLIMB_POLICY_SEED=str(seed),
                       WANDB_MODE="offline", ATTEMPTS="1", MUJOCO_GL="egl")
            log_root = out / f"seed{seed}"
            command = [str(PYTHON), str(ROOT / "tools/train_relative_policy.py"),
                       "Climb-Tracking-Flat-Unitree-G1-Policy-D-Development",
                       "--env.scene.num-envs", "512", "--agent.max-iterations", "4000",
                       "--agent.logger", "tensorboard", "--agent.run-name", f"D_calibration_s{seed}",
                       "--log-root", str(log_root)]
            write_once(out / f"seed{seed}_launch.json", {"argv": command,
                       "environment": {key: env[key] for key in env if key.startswith("CLIMB_")}})
            log = out / f"seed{seed}.log"
            subprocess.run([str(ROOT / "tools/run_when_free.sh"), "14000", str(log), "--", *command],
                           env=env, cwd=ROOT, check=True)
            if "DONE rc=0 " not in log.read_text():
                raise ValueError("missing training completion sentinel")
            runs = list(log_root.glob("g1_tracking/*"))
            if len(runs) != 1:
                raise ValueError("ambiguous calibration run")
            result = verify_calibration(runs[0], seed, sources)
            write_once(out / f"seed{seed}_result.json", result)
            print(json.dumps({"seed": seed, "status": result["status"], "gate": result["gate"]}), flush=True)
            if result["status"] != "calibration_pass":
                final = {"status": "baseline_calibration_fail", "failed_seed": seed,
                         "next": "new design required; do not select another parameter"}
                break
        else:
            final = {"status": "baseline_calibration_pass", "seeds": [31, 32],
                     "next": "freeze complete prospective campaign before any confirmation launch"}
    except Exception as exc:
        final = {"status": "execution_stopped", "reason": str(exc)}
    final["policy_endpoints_opened"] = False
    write_once(out / "terminal_status.json", final)
    print(json.dumps(final), flush=True)
    if final["status"] != "baseline_calibration_pass":
        sys.exit(1)


if __name__ == "__main__":
    main()
