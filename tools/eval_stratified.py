#!/usr/bin/env python3
"""Stratified-start evaluation (N4 protocol): survival over a fixed window from fixed start offsets.

Start-offset-averaged survival ("random start") confounds *where* in a clip a policy fails with
*how much* of the clip is failable -- #44 read 0.31 because episodes that began after its ground
segment survived. This tool evaluates each clip from a grid of start offsets, K episodes each
(small joint-position noise), over a `--window` seconds horizon (or to the clip end, whichever is
first), and reports survival per (clip, offset) plus the offset-averaged aggregate.

Usage:
    eval_stratified.py --checkpoint model_3999.pt --clips clips.txt --offsets 0,1,2,3,4,6,8 \
        --window 3 --episodes 8 --out reports/strat.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import asdict

import torch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--clips", required=True, help="clip list file (names) or comma-separated names")
    ap.add_argument("--bank", default="/data/robotixx/climb/bank/amass")
    ap.add_argument("--offsets", default="0,1,2,3,4,6,8", help="start offsets [s], comma-separated")
    ap.add_argument("--window", type=float, default=3.0)
    ap.add_argument("--episodes", type=int, default=8)
    ap.add_argument("--noise", type=float, default=0.05, help="joint-position IC noise [rad]")
    ap.add_argument("--nominal", action="store_true", help="disable startup DR + pushes (nominal robot)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    import climb  # noqa: PLC0415,F401
    from mjlab.envs import ManagerBasedRlEnv  # noqa: PLC0415
    from mjlab.rl import RslRlVecEnvWrapper  # noqa: PLC0415
    from mjlab.tasks.registry import load_rl_cfg, load_runner_cls  # noqa: PLC0415
    from climb import climb_g1_tracking_env_cfg  # noqa: PLC0415

    if os.path.exists(args.clips):
        names = [l.strip() for l in open(args.clips) if l.strip()]
    else:
        names = [c.strip() for c in args.clips.split(",") if c.strip()]
    files = [os.path.join(args.bank, n + ".npz") for n in names]
    offsets = [float(x) for x in args.offsets.split(",")]
    K = args.episodes
    # world layout: clip-major, then offset, then episode
    layout = [(ci, oi) for ci in range(len(names)) for oi in range(len(offsets)) for _ in range(K)]
    N = len(layout)
    print(f"[strat] {len(names)} clips x {len(offsets)} offsets x {K} episodes = {N} envs; window {args.window}s")

    task = "Climb-Tracking-Flat-Unitree-G1"
    env_cfg = climb_g1_tracking_env_cfg(motion_files=files, sampling_mode="uniform")
    env_cfg.scene.num_envs = N
    env_cfg.commands["motion"].resampling_time_range = (1.0e9, 1.0e9)
    if args.nominal:
        for k in ("push_robot", "base_com", "foot_friction", "encoder_bias"):
            env_cfg.events.pop(k, None)
    else:
        env_cfg.events.pop("push_robot", None)
    for grp in env_cfg.observations.values():
        grp.enable_corruption = False
    agent_cfg = load_rl_cfg(task)
    env = ManagerBasedRlEnv(cfg=env_cfg, device=args.device)
    wrapped = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)
    runner = load_runner_cls(task)(wrapped, asdict(agent_cfg), device=args.device)
    runner.load(args.checkpoint, load_cfg={"actor": True}, strict=True, map_location=args.device)
    policy = runner.get_inference_policy(device=args.device)

    cmd = env.command_manager.get_term("motion")
    dev = args.device
    clip_ids = torch.tensor([ci for ci, _ in layout], dtype=torch.long, device=dev)
    off = torch.tensor([offsets[oi] for _, oi in layout], device=dev)
    obs, _ = wrapped.reset()
    cmd.assign_clips(clip_ids, at_start=True)
    fps = float(cmd.motion.fps)
    starts = cmd.motion.clip_start[clip_ids]
    lens = cmd.motion.clip_len[clip_ids]
    local = torch.minimum((off * fps).long(), lens - 2)
    cmd.time_steps[:] = starts + local
    cmd._finalize_reference(torch.arange(N, device=dev))
    g = torch.Generator(device="cpu").manual_seed(args.seed)
    env.sim.data.qpos[:, 7:] += ((torch.rand(N, env.sim.mj_model.nq - 7, generator=g) * 2 - 1) * args.noise).to(dev)
    env.sim.forward()
    obs = wrapped.get_observations()
    # per-env horizon: window or remaining clip
    remaining_s = (lens - local).float() / fps
    horizon_env = torch.clamp(torch.minimum(torch.full_like(remaining_s, args.window), remaining_s) / env.step_dt, min=1).long()
    H = int(horizon_env.max().item())
    alive = torch.ones(N, dtype=torch.bool, device=dev)
    done_ok = torch.zeros(N, dtype=torch.bool, device=dev)
    surv_steps = torch.zeros(N, device=dev)
    with torch.inference_mode():
        for k in range(H):
            obs, _, _, _ = wrapped.step(policy(obs))
            failed = env.termination_manager.terminated.bool()
            reached = (k + 1) >= horizon_env
            surv_steps += alive.float()
            done_ok |= alive & reached & ~failed
            alive &= ~(failed | reached)
            if not alive.any():
                break
    ok = (done_ok | alive).float().cpu().numpy()
    ss = (surv_steps * env.step_dt).cpu().numpy()
    rows = []
    import numpy as np
    for ci, name in enumerate(names):
        per_off = []
        for oi, o in enumerate(offsets):
            idx = [i for i, (c, oo) in enumerate(layout) if c == ci and oo == oi]
            s = float(ok[idx].mean()); ms = float(ss[idx].mean())
            per_off.append(s)
            rows.append({"clip": name, "offset_s": o, "survival": round(s, 4), "mean_survival_s": round(ms, 3), "n": len(idx),
                         "window_s": round(float(horizon_env[idx[0]].item() * env.step_dt), 2)})
        rows.append({"clip": name, "offset_s": "mean", "survival": round(float(np.mean(per_off)), 4), "mean_survival_s": "", "n": len(offsets) * K, "window_s": args.window})
        print(f"  {name[:50]:52s} " + " ".join(f"{o:g}s:{s:.2f}" for o, s in zip(offsets, per_off)) + f"  | mean {np.mean(per_off):.3f}")
    with open(args.out, "w") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print("[strat] wrote", args.out)
    env.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
