#!/usr/bin/env python3
"""Evaluate one segment-v2 policy on a frozen exact unit/start panel."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

import torch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import RslRlVecEnvWrapper
from mjlab.tasks.tracking.config.g1.rl_cfg import unitree_g1_tracking_ppo_runner_cfg
from mjlab.tasks.tracking.rl import MotionTrackingOnPolicyRunner

from climb.env_cfg import read_clip_list
from climb.segment_command import SegmentNativeMotionCommand
from climb.segment_env_cfg import segment_native_g1_tracking_env_cfg
from climb.segment_runtime import SegmentSampler


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_tensors(values: dict[str, torch.Tensor]) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(values.items()):
        digest.update(name.encode())
        digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def build_conditions(
    sampler: SegmentSampler, *, phases: tuple[float, ...], reps: int
) -> list[dict[str, int | float | str]]:
    if reps <= 0 or not phases or any(not 0.0 <= phase <= 1.0 for phase in phases):
        raise ValueError("positive reps and phases in [0, 1] are required")
    rows: list[dict[str, int | float | str]] = []
    for table_index in range(sampler.num_units):
        first = int(sampler.intervals.first[table_index])
        count = int(sampler.intervals.counts[table_index])
        for phase_index, phase in enumerate(phases):
            start = first + round(phase * (count - 1))
            for rep in range(reps):
                rows.append(
                    {
                        "world_id": f"u{table_index:04d}-p{phase_index}-r{rep:02d}",
                        "table_index": table_index,
                        "unit_id": int(sampler.intervals.unit_ids[table_index]),
                        "clip_id": int(sampler.intervals.clip_ids[table_index]),
                        "phase": phase,
                        "rep": rep,
                        "start_frame": start,
                    }
                )
    return rows


def load_or_create_conditions(
    path: Path,
    sampler: SegmentSampler,
    *,
    phases: tuple[float, ...],
    reps: int,
) -> list[dict[str, Any]]:
    expected = {
        "schema_version": "segment_eval_conditions/1",
        "classification": "unsealed paired segment-v2 evaluation panel",
        "unit_table_sha256": sampler.manifest["unit_table_sha256"],
        "phases": list(phases),
        "reps": reps,
        "conditions": build_conditions(sampler, phases=phases, reps=reps),
    }
    if path.exists():
        actual = json.loads(path.read_text())
        if actual != expected:
            raise ValueError("existing condition manifest differs from requested panel")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(expected, indent=1) + "\n")
    return cast(list[dict[str, Any]], expected["conditions"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--label", required=True)
    parser.add_argument("--clips", required=True, type=Path)
    parser.add_argument("--bank", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--conditions", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--phases", default="0,0.5,1")
    parser.add_argument("--reps", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260820)
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()

    phases = tuple(float(value) for value in args.phases.split(",") if value)
    sampler = SegmentSampler(args.manifest, mode="uniform", seed=args.seed)
    conditions = load_or_create_conditions(
        args.conditions, sampler, phases=phases, reps=args.reps
    )
    num_envs = len(conditions)
    files = read_clip_list(str(args.clips.resolve()), str(args.bank.resolve()))
    cfg = segment_native_g1_tracking_env_cfg(
        motion_files=files,
        segment_manifest=str(args.manifest.resolve()),
        segment_sampling_mode="uniform",
        sampler_seed=args.seed,
        env_seed=args.seed,
        failure_penalty=0.0,
    )
    cfg.scene.num_envs = num_envs
    cfg.auto_reset = False
    cfg.events.pop("push_robot", None)
    for group in cfg.observations.values():
        group.enable_corruption = False

    agent_cfg = unitree_g1_tracking_ppo_runner_cfg()
    env = ManagerBasedRlEnv(cfg=cfg, device=args.device)
    wrapped = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)
    try:
        runner = MotionTrackingOnPolicyRunner(
            wrapped, asdict(agent_cfg), device=args.device
        )
        runner.load(
            str(args.checkpoint.resolve()),
            load_cfg={"actor": True},
            strict=True,
            map_location=args.device,
        )
        policy = runner.get_inference_policy(device=args.device)
        command = env.command_manager.get_term("motion")
        if not isinstance(command, SegmentNativeMotionCommand):
            raise TypeError("evaluation command is not segment-native")
        device = torch.device(args.device)
        table_indices = torch.tensor(
            [row["table_index"] for row in conditions],
            dtype=torch.long,
            device=device,
        )
        local_starts = torch.tensor(
            [row["start_frame"] for row in conditions],
            dtype=torch.long,
            device=device,
        )
        command.assign_segments(table_indices, local_starts)
        observations = wrapped.get_observations()
        initial_state_sha256 = sha256_tensors(
            {"qpos": env.sim.data.qpos, "qvel": env.sim.data.qvel}
        )
        startup_randomization_sha256 = sha256_tensors(
            {
                "body_ipos": env.sim.model.body_ipos,
                "encoder_bias": command.robot.data.encoder_bias,
                "geom_friction": env.sim.model.geom_friction,
            }
        )

        alive = torch.ones(num_envs, dtype=torch.bool, device=device)
        success = torch.zeros_like(alive)
        survived_steps = torch.zeros(num_envs, dtype=torch.long, device=device)
        causes: list[set[str]] = [set() for _ in range(num_envs)]
        trajectory: list[dict[str, Any]] = []
        horizon = sampler.horizon_steps

        with torch.inference_mode():
            for step in range(1, horizon + 1):
                active = alive.clone()
                actions = policy(observations)
                observations, _, dones, _ = wrapped.step(actions)
                terminated = env.termination_manager.terminated.bool()
                truncated = env.termination_manager.time_outs.bool()
                survived_steps += active.long()

                force = env.sim.data.actuator_force
                joint_velocity = command.robot.data.joint_vel
                work = (force * joint_velocity).abs().mean(dim=1) * env.step_dt
                metrics = {
                    "error_body_pos_m": command.metrics["error_body_pos"],
                    "error_anchor_pos_m": command.metrics["error_anchor_pos"],
                    "error_anchor_rot_rad": command.metrics["error_anchor_rot"],
                    "error_joint_pos_l2": command.metrics["error_joint_pos"],
                    "mechanical_work_per_actuator_j": work,
                }
                active_ids = active.nonzero(as_tuple=False).flatten().cpu().tolist()
                metric_cpu = {name: value.detach().cpu() for name, value in metrics.items()}
                terminated_cpu = terminated.cpu()
                truncated_cpu = truncated.cpu()
                for index in active_ids:
                    trajectory.append(
                        {
                            "policy": args.label,
                            "world_id": conditions[index]["world_id"],
                            "step": step,
                            "terminated": int(terminated_cpu[index]),
                            "truncated": int(truncated_cpu[index]),
                            **{
                                name: float(value[index])
                                for name, value in metric_cpu.items()
                            },
                        }
                    )

                active_failures = active & terminated
                for term_name in env.termination_manager.active_terms:
                    term = env.termination_manager.get_term(term_name)
                    for index in (active_failures & term).nonzero(
                        as_tuple=False
                    ).flatten().cpu().tolist():
                        causes[index].add(term_name)
                newly_done = active & dones.bool()
                success |= newly_done & truncated & ~terminated
                alive &= ~newly_done
                if not bool(alive.any()):
                    break
                reset_ids = dones.bool().nonzero(as_tuple=False).flatten()
                if reset_ids.numel():
                    env.reset(env_ids=reset_ids)
                    observations = wrapped.get_observations()

        if bool(alive.any()):
            raise RuntimeError("evaluation left active worlds beyond the segment horizon")
        summary_rows = [
            {
                **condition,
                "policy": args.label,
                "success": int(success[index]),
                "survival_steps": int(survived_steps[index]),
                "survival_s": float(survived_steps[index]) * env.step_dt,
                "termination_causes": ";".join(sorted(causes[index])),
            }
            for index, condition in enumerate(conditions)
        ]
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0]))
            writer.writeheader()
            writer.writerows(summary_rows)
        trajectory_path = args.out.with_name(f"{args.out.stem}_trajectory.csv")
        with trajectory_path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(trajectory[0]))
            writer.writeheader()
            writer.writerows(trajectory)
        meta = {
            "schema_version": "segment_eval_output/1",
            "classification": "unsealed paired segment-v2 evaluation",
            "policy": args.label,
            "checkpoint": str(args.checkpoint.resolve()),
            "checkpoint_sha256": sha256_file(args.checkpoint.resolve()),
            "unit_table_sha256": sampler.manifest["unit_table_sha256"],
            "conditions_sha256": sha256_file(args.conditions.resolve()),
            "environment_seed": args.seed,
            "initial_state_sha256": initial_state_sha256,
            "startup_randomization_sha256": startup_randomization_sha256,
            "worlds": num_envs,
            "success_rate": float(success.float().mean()),
            "mean_survival_s": float(survived_steps.float().mean()) * env.step_dt,
            "summary": str(args.out.resolve()),
            "trajectory": str(trajectory_path.resolve()),
        }
        Path(f"{args.out}.meta.json").write_text(json.dumps(meta, indent=1) + "\n")
        print(
            f"[{args.label}] worlds={num_envs} success={meta['success_rate']:.4f} "
            f"survival={meta['mean_survival_s']:.4f}s -> {args.out}"
        )
    finally:
        env.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
