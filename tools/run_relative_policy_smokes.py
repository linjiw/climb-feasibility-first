#!/usr/bin/env python3
"""After two manipulation passes, smoke the four fixed prospective policy arms."""

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
from continue_relative_progress import verify_study, wait_for_gpu, wait_for_terminal
from run_relative_progress_study import write_once
from train_relative_policy import CONTRACT, profile
from climb.relative_progress import RelativeProgressSampler
from climb.segment_runtime import SegmentSampler

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / "mjlab-1.6.0/.venv/bin/python"
MANIFEST = ROOT / "reports/g_segment/unit_table.json"


def verify_smoke(run: Path, arm: str, sources: dict[str, str]) -> dict:
    contract, selected = profile(arm, "smoke", 41)
    common = contract["common"]
    paths = list(run.glob("model_*_segment.json"))
    rows = [json.loads(path.read_text()) for path in paths]
    if sorted(row["iteration"] for row in rows) != [0, 19]:
        raise ValueError("smoke requires exactly iteration 0 and 19 ledgers")
    for name, digest in sources.items():
        if sha256(ROOT / name) != digest:
            raise ValueError(f"source changed during smoke: {name}")
    sampler_cls = RelativeProgressSampler if arm == "R" else SegmentSampler
    kwargs = {"relative_factor": 2.0} if arm == "R" else {}
    sampler = sampler_cls(MANIFEST, mode=selected["mode"], seed=41, rank=selected["rank"],
                          exploration_ratio=selected["exploration_ratio"],
                          difficulty_power=selected["difficulty_power"], progress_window=10,
                          progress_floor=selected["progress_floor"], max_unit_probability=0.05,
                          max_clip_probability=0.25, **kwargs)
    snapshots = []
    bindings = {}
    for path, row in sorted(zip(paths, rows), key=lambda pair: pair[1]["iteration"]):
        expected = {"relative_policy_arm": arm, "relative_policy_stage": "smoke", "num_envs": 8,
                    "profile": selected, "profile_contract_sha256": sha256(CONTRACT),
                    "training_entrypoint_sha256": sources["tools/train_relative_policy.py"]}
        if any(row.get(key) != value for key, value in expected.items()):
            raise ValueError("smoke identity/profile mismatch")
        source_names = {"tools/train_relative_policy.py", "climb/relative_progress.py",
                        "climb/segment_runtime.py", "climb/segment_curriculum.py",
                        "climb/segment_command.py", "climb/segment_env_cfg.py"}
        if row.get("source_hashes_at_launch") != {name: sources[name] for name in source_names}:
            raise ValueError("training source binding mismatch")
        segment = row["segment"]
        expected_segment = {"sampler_seed": 41, "training_seed": 41,
                            "unit_table_sha256": contract["unit_table_sha256"], "horizon_steps": 50,
                            "mode": selected["mode"], "rank": selected["rank"],
                            "exploration_ratio": selected["exploration_ratio"],
                            "difficulty_power": selected["difficulty_power"],
                            "progress_floor": selected["progress_floor"], "progress_window": 10,
                            "max_unit_probability": common["max_unit_probability"],
                            "max_clip_probability": common["max_clip_probability"]}
        if any(segment.get(key) != value for key, value in expected_segment.items()):
            raise ValueError("actual sampler contract mismatch")
        checkpoint = run / f"model_{row['iteration']}.pt"
        if row["checkpoint"] != {"path": str(checkpoint.resolve()), "sha256": sha256(checkpoint)}:
            raise ValueError("checkpoint link mismatch")
        state_path = run / f"model_{row['iteration']}_segment_sampler.pt"
        state = torch.load(state_path, map_location="cpu", weights_only=True)
        if state["iteration"] != row["iteration"]:
            raise ValueError("sampler state iteration mismatch")
        sampler.load_state_dict(state["sampler"])
        actual = torch.tensor(segment["probabilities"], dtype=torch.float64)
        if not torch.equal(actual, sampler.probabilities):
            raise ValueError("probabilities do not replay exactly")
        for key in ("invalid_start_count", "invalid_reference_frame_count", "censored_resets"):
            if segment[key] != 0:
                raise ValueError(f"nonzero {key}")
        if segment["completed_trials"] != int(sampler.lifetime_attempts.sum()):
            raise ValueError("completed-trial accounting does not match sampler state")
        if segment["failed_trials"] != int(sampler.lifetime_failures.sum()):
            raise ValueError("failed-trial accounting does not match sampler state")
        snapshots.append({"iteration": row["iteration"], "completed_trials": segment["completed_trials"],
                          "tv": sampler.adaptation_total_variation(),
                          "top1_unit_mass": float(actual.max())})
        bindings[str(path)] = {"ledger": sha256(path), "sampler": sha256(state_path),
                               "checkpoint": row["checkpoint"]["sha256"]}
    if snapshots[-1]["completed_trials"] <= 0:
        raise ValueError("no completed trials")
    return {"status": "smoke_pass", "arm": arm, "seed": 41,
            "classification": "development lifecycle only; no policy-benefit result",
            "snapshots": snapshots, "bindings": bindings}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replication-dir", type=Path, required=True)
    parser.add_argument("--seed11-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--wait-seconds", type=int, default=18000)
    args = parser.parse_args()
    if args.wait_seconds <= 0:
        parser.error("wait budget must be positive")
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    names = ("tools/run_relative_policy_smokes.py", "tools/train_relative_policy.py",
             "plan/R3_BASELINE_CONTRACT_2026-09-05.json", "climb/relative_progress.py",
             "climb/segment_runtime.py", "climb/segment_curriculum.py",
             "climb/segment_command.py", "climb/segment_env_cfg.py",
             "tools/continue_relative_progress.py", "tools/check_relative_progress_probe.py",
             "tools/climb_segment_train.py", "tools/run_when_free.sh")
    sources = {name: sha256(ROOT / name) for name in names}
    write_once(out / "design.json", {"schema_version": "relative_policy_smokes/1", "sources": sources,
                                    "arms": ["U", "A", "R", "D"], "seed": 41,
                                    "num_envs": 8, "iterations": 20,
                                    "prerequisite": str(args.replication_dir.resolve()),
                                    "policy_endpoints_opened": False})
    deadline = time.monotonic() + args.wait_seconds
    try:
        print("Waiting for independent manipulation replication", flush=True)
        wait_for_terminal(args.replication_dir, deadline, None)
        terminal = json.loads((args.replication_dir / "terminal_status.json").read_text())
        if terminal["status"] != "replicated_manipulation":
            raise ValueError(f"replication prerequisite did not pass: {terminal['status']}")
        for directory, seed in ((args.seed11_dir, 11), (args.replication_dir / "study_s12", 12)):
            if verify_study(directory.resolve(), seed)["status"] != "pass":
                raise ValueError("manipulation result did not reproduce")
        for arm in ("U", "A", "R", "D"):
            for name, digest in sources.items():
                if sha256(ROOT / name) != digest:
                    raise ValueError(f"source changed while queued: {name}")
            wait_for_gpu(deadline)
            env = dict(os.environ, CLIMB_BANK=str(ROOT / "bank/amass"),
                       CLIMB_CLIPS=str(ROOT / "bank/tiers/tier_800.txt"),
                       CLIMB_SEGMENT_MANIFEST=str(MANIFEST), CLIMB_POLICY_ARM=arm,
                       CLIMB_POLICY_STAGE="smoke", CLIMB_POLICY_SEED="41",
                       WANDB_MODE="offline", ATTEMPTS="1", MUJOCO_GL="egl")
            log_root = out / arm
            command = [str(PYTHON), str(ROOT / "tools/train_relative_policy.py"),
                       f"Climb-Tracking-Flat-Unitree-G1-Policy-{arm}-Development",
                       "--env.scene.num-envs", "8", "--agent.max-iterations", "20",
                       "--agent.logger", "tensorboard", "--agent.run-name", f"policy_{arm}_smoke_s41",
                       "--log-root", str(log_root)]
            write_once(out / f"{arm}_launch.json", {"argv": command,
                       "environment": {key: env[key] for key in env if key.startswith("CLIMB_")}})
            subprocess.run([str(ROOT / "tools/run_when_free.sh"), "14000", str(out / f"{arm}.log"),
                            "--", *command], env=env, cwd=ROOT, check=True)
            if "DONE rc=0 " not in (out / f"{arm}.log").read_text():
                raise ValueError("missing successful smoke sentinel")
            runs = list(log_root.glob("g1_tracking/*"))
            if len(runs) != 1:
                raise ValueError("ambiguous smoke run")
            result = verify_smoke(runs[0], arm, sources)
            write_once(out / f"{arm}_result.json", result)
            print(f"{arm}: smoke_pass", flush=True)
        result = {"status": "four_arm_smoke_pass", "next": "D calibration and evaluator provenance; no confirmation launch"}
    except Exception as exc:
        result = {"status": "execution_stopped", "reason": str(exc)}
    result["policy_endpoints_opened"] = False
    write_once(out / "terminal_status.json", result)
    print(json.dumps(result), flush=True)
    if result["status"] != "four_arm_smoke_pass":
        sys.exit(1)


if __name__ == "__main__":
    main()
