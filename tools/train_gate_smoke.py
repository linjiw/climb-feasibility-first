#!/usr/bin/env python3
"""Run only a fixed 8-environment, 20-iteration development PPO lifecycle smoke."""

from __future__ import annotations

import argparse
from dataclasses import asdict, fields
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import torch

from climb.env_cfg import read_clip_list
from climb.gate_ablation import GateAblationCommandCfg, file_digest, rejection_telemetry, sampler_for, verified_manifest
from climb.segment_env_cfg import segment_native_g1_tracking_env_cfg
from mjlab.scripts.train import TrainConfig, run_train
from mjlab.tasks.registry import register_mjlab_task
from mjlab.tasks.tracking.config.g1.rl_cfg import unitree_g1_tracking_ppo_runner_cfg
from mjlab.tasks.tracking.rl import MotionTrackingOnPolicyRunner
from relative_confirmation_setup import canonical


def actor_digest(actor) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(actor.state_dict().items()):
        digest.update(f"{name}:{tensor.dtype}:{tuple(tensor.shape)}".encode())
        digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def configs(manifest: Path, digest: str, arm: str, clips: Path, bank: Path):
    verified_manifest(manifest, digest, arm)
    cfg = segment_native_g1_tracking_env_cfg(
        motion_files=read_clip_list(str(clips), str(bank)), segment_manifest=str(manifest),
        segment_sampling_mode="adaptive", sampler_seed=71, env_seed=71,
        segment_rank="failure", segment_exploration_ratio=0.8, segment_difficulty_power=1.0,
        segment_progress_window=10, segment_progress_floor=0.0,
        max_unit_probability=0.05, max_clip_probability=0.25,
        verify_motion_hashes=True, failure_penalty=-10)
    command = cfg.commands["motion"]
    cfg.commands["motion"] = GateAblationCommandCfg(
        **{f.name: getattr(command, f.name) for f in fields(command)},
        gate_admission=arm, gate_manifest_sha256=digest)
    cfg.scene.num_envs = 8
    agent = unitree_g1_tracking_ppo_runner_cfg()
    agent.seed = 71
    agent.max_iterations = 20
    agent.save_interval = 100
    agent.run_name = f"gate_{arm}_smoke_s71"
    return cfg, agent


def verify_smoke(run: Path, manifest: Path, digest: str, arm: str) -> dict:
    verified_manifest(manifest, digest, arm)
    paths = sorted(run.glob("model_*_gate.json"), key=lambda p: int(p.stem.split("_")[1]))
    if [int(p.stem.split("_")[1]) for p in paths] != [0, 19]:
        raise ValueError("smoke requires exactly checkpoints 0 and 19")
    sampler = sampler_for(manifest, 71)
    records = []
    for path in paths:
        row = json.loads(path.read_text())
        if row["seed"] != 71 or row["num_envs"] != 8 or row["admission"] != arm:
            raise ValueError("wrong development smoke identity")
        state_path = run / f"model_{row['iteration']}_sampler.pt"
        checkpoint = run / f"model_{row['iteration']}.pt"
        if file_digest(checkpoint) != row["checkpoint_sha256"] or file_digest(state_path) != row["sampler_sha256"]:
            raise ValueError("smoke state or checkpoint changed")
        sampler.load_state_dict(torch.load(state_path, map_location="cpu", weights_only=True))
        telemetry = row["segment"]
        if any(telemetry[key] != 0 for key in ("invalid_start_count", "invalid_reference_frame_count", "censored_resets")):
            raise ValueError("invalid/censored smoke events")
        if (not torch.equal(sampler.probabilities, torch.tensor(telemetry["probabilities"], dtype=torch.float64))
                or telemetry["completed_trials"] != int(sampler.lifetime_attempts.sum())
                or telemetry["failed_trials"] != int(sampler.lifetime_failures.sum())
                or telemetry["gate_ablation"] != rejection_telemetry(sampler)):
            raise ValueError("smoke sampler/event telemetry does not replay")
        records.append({"iteration": row["iteration"], "checkpoint_sha256": row["checkpoint_sha256"],
                        "ledger_sha256": file_digest(path), "sampler_sha256": row["sampler_sha256"]})
    trial_count = int(sampler.lifetime_attempts.sum())
    rejected = rejection_telemetry(sampler)
    if trial_count <= 0 or (arm == "on" and (rejected["rejected_completed_trials"] or rejected["post_cap_rejected_mass"])):
        raise ValueError("gate or completed-event smoke condition failed")
    if arm == "off" and rejected["rejected_completed_trials"] <= 0:
        raise ValueError("gate-off smoke did not exercise restored support")
    return {"status": "gate_smoke_pass", "classification": "development PPO lifecycle only; no policy-benefit comparison",
            "admission": arm, "seed": 71, "num_envs": 8, "iterations": 20,
            "transitions": 3840, "completed_trials": trial_count,
            "failed_trials": int(sampler.lifetime_failures.sum()),
            "invalid_start_count": 0, "invalid_reference_frame_count": 0, "censored_resets": 0,
            "final_allocation": rejected, "checkpoints": records,
            "initial_actor": json.loads((run / "initial_actor.json").read_text()),
            "full_training_enabled": False, "heldout_endpoints_opened": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--admission", choices=("on", "off"), required=True)
    parser.add_argument("--clips", type=Path, required=True)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda:0"), default="cpu")
    args = parser.parse_args()
    cfg, agent = configs(args.manifest.resolve(), args.manifest_sha256, args.admission,
                         args.clips.resolve(), args.bank.resolve())
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    run = out / "run"
    run.mkdir()
    os.environ.update(CUDA_VISIBLE_DEVICES="" if args.device == "cpu" else "0",
                      MUJOCO_GL="egl", WANDB_MODE="offline")
    task = f"Climb-Tracking-Flat-Unitree-G1-Gate-{args.admission.title()}-Development"
    sources = [Path(__file__), ROOT/"climb/gate_ablation.py", ROOT/"climb/segment_command.py",
               ROOT/"climb/segment_runtime.py", ROOT/"climb/segment_curriculum.py", ROOT/"climb/segment_env_cfg.py"]
    bindings = {str(p): file_digest(p) for p in sources}
    (out / "design.json").write_text(json.dumps({"task": task, "classification": "development smoke only",
        "config": canonical(cfg), "agent": canonical(agent), "device": args.device,
        "manifest": {"path": str(args.manifest.resolve()), "sha256": args.manifest_sha256},
        "sources": bindings, "full_training_enabled": False}, indent=2)+"\n")

    class GateSmokeRunner(MotionTrackingOnPolicyRunner):
        def __init__(self, *runner_args, **kwargs):
            super().__init__(*runner_args, **kwargs)
            (run / "initial_actor.json").write_text(json.dumps({"sha256": actor_digest(self.alg.get_policy()),
                                                               "seed": 71}, indent=2)+"\n")

        def save(self, path, infos=None):
            super().save(path, infos)
            command = self.env.unwrapped.command_manager.get_term("motion")
            checkpoint = Path(path)
            state_path = checkpoint.with_name(f"{checkpoint.stem}_sampler.pt")
            torch.save(command.sampler.state_dict(), state_path)
            row = {"iteration": int(self.current_learning_iteration), "seed": 71,
                   "num_envs": self.env.unwrapped.num_envs, "admission": args.admission,
                   "segment": command.segment_telemetry(), "sources": bindings,
                   "checkpoint_sha256": file_digest(checkpoint), "sampler_sha256": file_digest(state_path)}
            checkpoint.with_name(f"{checkpoint.stem}_gate.json").write_text(json.dumps(row, indent=2)+"\n")

    register_mjlab_task(task_id=task, env_cfg=cfg, play_env_cfg=cfg, rl_cfg=agent, runner_cls=GateSmokeRunner)
    try:
        run_train(task, TrainConfig(env=cfg, agent=agent, log_root=str(out)), run)
        result = verify_smoke(run, args.manifest.resolve(), args.manifest_sha256, args.admission)
        (out / "result.json").write_text(json.dumps(result, indent=2)+"\n")
        print(json.dumps(result), flush=True)
    except Exception as exc:
        (out / "failure.json").write_text(json.dumps({"status": "gate_smoke_failed", "reason": str(exc)}, indent=2)+"\n")
        raise


if __name__ == "__main__":
    main()
