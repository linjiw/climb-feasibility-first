#!/usr/bin/env python3
"""Trace exact segment trial frames and time-outs in a vectorized mjlab env."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import cast

import torch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def _observations_are_finite(
    observations: dict[str, torch.Tensor | dict[str, torch.Tensor]],
) -> bool:
    for value in observations.values():
        tensors = value.values() if isinstance(value, dict) else (value,)
        if any(not bool(torch.isfinite(tensor).all()) for tensor in tensors):
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--clips", default="reports/segment_v2_smoke/clips.txt", type=Path
    )
    parser.add_argument("--bank", default="bank/amass", type=Path)
    parser.add_argument(
        "--manifest",
        default="reports/segment_v2_smoke/unit_table.json",
        type=Path,
    )
    parser.add_argument(
        "--out",
        default="reports/segment_v2_smoke/timeline_trace.json",
        type=Path,
    )
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--num-envs", type=int, default=8)
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20260820)
    args = parser.parse_args()
    if args.num_envs < 2 or args.cycles <= 0:
        parser.error("the vector trace needs at least two envs and one cycle")
    device = torch.device(args.device)

    from mjlab.envs import ManagerBasedRlEnv

    from climb.env_cfg import read_clip_list
    from climb.segment_command import SegmentNativeMotionCommand
    from climb.segment_env_cfg import segment_native_g1_tracking_env_cfg

    motion_files = read_clip_list(str(args.clips.resolve()), str(args.bank.resolve()))
    cfg = segment_native_g1_tracking_env_cfg(
        motion_files=motion_files,
        segment_manifest=str(args.manifest.resolve()),
        segment_sampling_mode="adaptive",
        sampler_seed=args.seed,
        env_seed=args.seed,
        failure_penalty=0.0,
    )
    cfg.scene.num_envs = args.num_envs
    cfg.commands["motion"].debug_vis = False
    cfg.commands["motion"].pose_range = {}
    cfg.commands["motion"].velocity_range = {}
    cfg.commands["motion"].joint_position_range = (0.0, 0.0)
    cfg.events = {}
    for name in ("anchor_pos", "anchor_ori", "ee_body_pos"):
        cfg.terminations.pop(name, None)

    if args.device.startswith("cuda"):
        torch.cuda.set_device(device)
        device_index = torch.cuda.current_device()
        torch.cuda.reset_peak_memory_stats(device_index)
        free_before, total_memory = torch.cuda.mem_get_info(device_index)
    else:
        device_index = -1
        free_before = total_memory = 0

    env = ManagerBasedRlEnv(cfg=cfg, device=args.device)
    try:
        observations, _ = env.reset()
        command = env.command_manager.get_term("motion")
        if not isinstance(command, SegmentNativeMotionCommand):
            raise TypeError("smoke constructed the wrong command type")
        horizon = command.sampler.horizon_steps
        actions = torch.zeros(
            (args.num_envs, env.action_manager.total_action_dim),
            device=args.device,
        )
        all_assignments: list[tuple[int, int]] = []
        cycle_rows: list[dict[str, object]] = []

        for cycle in range(args.cycles):
            starts = command.local_start_steps.clone()
            units = command.active_unit_ids.clone()
            ends = command.local_trial_end_steps.clone()
            first_refs = command.time_steps - command.motion.clip_start[command.clip_ids]
            if not torch.equal(first_refs, starts + 1):
                raise AssertionError("first policy observation is not start+1")
            if not _observations_are_finite(observations):
                raise AssertionError("reset observations contain non-finite values")
            all_assignments.extend(zip(units.cpu().tolist(), starts.cpu().tolist()))

            for step in range(1, horizon + 1):
                pre_refs = (
                    command.time_steps - command.motion.clip_start[command.clip_ids]
                ).clone()
                expected = starts + step
                if not torch.equal(pre_refs, expected):
                    raise AssertionError(
                        f"cycle {cycle} step {step}: reference timeline mismatch"
                    )
                if bool((pre_refs >= command.local_segment_stop_steps).any()):
                    raise AssertionError("policy consumed an invalid segment frame")

                observations, rewards, terminated, truncated, _ = env.step(actions)
                if not bool(torch.isfinite(rewards).all()):
                    raise AssertionError("reward contains non-finite values")
                if step < horizon:
                    if bool(terminated.any()) or bool(truncated.any()):
                        raise AssertionError("segment ended before its declared horizon")
                else:
                    if bool(terminated.any()) or not bool(truncated.all()):
                        raise AssertionError(
                            "Hth transition must be a pure time-out for every env"
                        )
                    segment_term = env.termination_manager.get_term("segment_trial")
                    if not bool(segment_term.all()):
                        raise AssertionError("truncation did not come from segment_trial")

            post_refs = command.time_steps - command.motion.clip_start[command.clip_ids]
            if not torch.equal(post_refs, command.local_start_steps + 1):
                raise AssertionError("auto-reset did not expose the new start+1 frame")
            cycle_rows.append(
                {
                    "cycle": cycle,
                    "first_local_reference_min": int((starts + 1).min().item()),
                    "first_local_reference_max": int((starts + 1).max().item()),
                    "terminal_local_reference_min": int(ends.min().item()),
                    "terminal_local_reference_max": int(ends.max().item()),
                    "truncated_envs": args.num_envs,
                    "terminated_envs": 0,
                }
            )

        telemetry = command.segment_telemetry()
        expected_trials = args.num_envs * args.cycles
        if telemetry["completed_trials"] != expected_trials:
            raise AssertionError(
                f"attributed {telemetry['completed_trials']} trials, expected "
                f"{expected_trials}"
            )
        if telemetry["failed_trials"] != 0 or telemetry["censored_resets"] != 0:
            raise AssertionError("pure timeout trace produced failures or censoring")
        if (
            telemetry["invalid_start_count"] != 0
            or telemetry["invalid_reference_frame_count"] != 0
        ):
            raise AssertionError("segment validity counter is nonzero")
        lifetime_attempts = telemetry["lifetime_attempts"]
        if not isinstance(lifetime_attempts, list) or (
            sum(cast(list[int], lifetime_attempts)) != expected_trials
        ):
            raise AssertionError("stable unit attribution lost completed trials")
        if len(set(all_assignments)) < 2:
            raise AssertionError("vector sampler broadcast one assignment to every env")

        if args.device.startswith("cuda"):
            torch.cuda.synchronize(device_index)
            free_after, _ = torch.cuda.mem_get_info(device_index)
            peak_allocated = torch.cuda.max_memory_allocated(device_index)
            peak_reserved = torch.cuda.max_memory_reserved(device_index)
        else:
            free_after = peak_allocated = peak_reserved = 0
        result = {
            "schema_version": "segment_timeline_trace/1",
            "classification": "unsealed mechanics gate",
            "status": "passed",
            "device": args.device,
            "seed": args.seed,
            "num_envs": args.num_envs,
            "cycles": args.cycles,
            "horizon_steps": horizon,
            "step_dt": env.step_dt,
            "assignments_observed": len(set(all_assignments)),
            "cycles_trace": cycle_rows,
            "telemetry": telemetry,
            "gpu": {
                "total_bytes": total_memory,
                "free_before_bytes": free_before,
                "free_after_bytes": free_after,
                "peak_allocated_bytes": peak_allocated,
                "peak_reserved_bytes": peak_reserved,
            },
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=1) + "\n")
        print(
            f"PASS: {expected_trials} trials, {horizon} steps each, "
            f"{len(set(all_assignments))} distinct assignments; wrote {args.out}"
        )
    finally:
        env.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
