#!/usr/bin/env python3
"""Does the environment admit the kneel/crawl skill at all?  (N3 analysis precondition)

Before N3's augmentation result is read as a coverage result, verify that a *perfect* tracker of
the kneel/crawl phase would survive the live env's terminations. Two oracles, both from stratified
start offsets inside the phase, K episodes each, DR on (training distribution) unless --nominal:

  follow   stiff PD mocap-follow: every control step the action is set so the PD target equals the
           reference joint pose of the current command frame (a policy that always outputs the
           reference), optionally with actuator gains scaled by --gain-scale;
  playback kinematic playback: after every physics step the robot is teleported onto the current
           reference (root + joints); terminations must not fire on the reference itself.

Logs per (clip, offset): survival, first-termination time, which termination channel fired, mean
tracking error, and the per-term reward rates. If `follow` survives the phase, the env admits the
skill and N3 reads clean; if `playback` itself terminates, the thresholds are sized against the
motion by construction (exposure layer: harness/task).
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import asdict

import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clips", default="/data/robotixx/climb/plan/N3_probe_clips.txt")
    ap.add_argument("--bank", default="/data/robotixx/climb/bank/amass")
    ap.add_argument("--offsets", default="0,2,3,4,6")
    ap.add_argument("--window", type=float, default=3.0)
    ap.add_argument("--episodes", type=int, default=8)
    ap.add_argument("--mode", choices=["follow", "playback"], default="follow")
    ap.add_argument("--gain-scale", type=float, default=1.0)
    ap.add_argument("--nominal", action="store_true")
    ap.add_argument("--noise", type=float, default=0.02)
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    import warp as wp  # noqa: PLC0415
    import climb  # noqa: PLC0415,F401
    from mjlab.envs import ManagerBasedRlEnv  # noqa: PLC0415
    from mjlab.tasks.registry import load_rl_cfg  # noqa: PLC0415
    from climb import climb_g1_tracking_env_cfg  # noqa: PLC0415

    names = [l.strip() for l in open(args.clips) if l.strip()] if os.path.exists(args.clips) else args.clips.split(",")
    files = [os.path.join(args.bank, n + ".npz") for n in names]
    offsets = [float(x) for x in args.offsets.split(",")]
    K = args.episodes
    layout = [(ci, oi) for ci in range(len(names)) for oi in range(len(offsets)) for _ in range(K)]
    N = len(layout)
    env_cfg = climb_g1_tracking_env_cfg(motion_files=files, sampling_mode="uniform")
    env_cfg.scene.num_envs = N
    env_cfg.commands["motion"].resampling_time_range = (1.0e9, 1.0e9)
    env_cfg.events.pop("push_robot", None)
    if args.nominal:
        for k in ("base_com", "foot_friction", "encoder_bias"):
            env_cfg.events.pop(k, None)
    for grp in env_cfg.observations.values():
        grp.enable_corruption = False
    _ = load_rl_cfg("Climb-Tracking-Flat-Unitree-G1")
    env = ManagerBasedRlEnv(cfg=env_cfg, device=args.device)
    dev = args.device
    cmd = env.command_manager.get_term("motion")
    tm = env.termination_manager
    rm = env.reward_manager
    act_term = env.action_manager.get_term("joint_pos")
    scale = act_term._scale            # float or (N, 29) per-joint tensor
    offset = act_term._offset            # (N, 29) default joint pos
    if args.gain_scale != 1.0:
        M = env.sim.wp_model
        g = wp.to_torch(M.actuator_gainprm); b = wp.to_torch(M.actuator_biasprm)
        g[..., 0] *= args.gain_scale; b[..., 1] *= args.gain_scale; b[..., 2] *= args.gain_scale
        print(f"[admit] actuator gains scaled x{args.gain_scale}")

    clip_ids = torch.tensor([ci for ci, _ in layout], dtype=torch.long, device=dev)
    off = torch.tensor([offsets[oi] for _, oi in layout], device=dev)
    env.reset()
    cmd.assign_clips(clip_ids, at_start=True)
    fps = float(cmd.motion.fps)
    starts = cmd.motion.clip_start[clip_ids]; lens = cmd.motion.clip_len[clip_ids]
    local = torch.minimum((off * fps).long(), lens - 2)
    cmd.time_steps[:] = starts + local
    all_ids = torch.arange(N, device=dev)
    cmd._finalize_reference(all_ids)
    g_ = torch.Generator(device="cpu").manual_seed(0)
    env.sim.data.qpos[:, 7:] += ((torch.rand(N, env.sim.mj_model.nq - 7, generator=g_) * 2 - 1) * args.noise).to(dev)
    env.sim.forward()
    remaining_s = (lens - local).float() / fps
    horizon_env = torch.clamp(torch.minimum(torch.full_like(remaining_s, args.window), remaining_s) / env.step_dt, min=1).long()
    H = int(horizon_env.max().item())
    alive = torch.ones(N, dtype=torch.bool, device=dev); done_ok = torch.zeros(N, dtype=torch.bool, device=dev)
    surv = torch.zeros(N, device=dev); err_sum = torch.zeros(N, device=dev); err_n = torch.zeros(N, device=dev)
    cause = [""] * N
    rew_sums = {n: torch.zeros(N, device=dev) for n in rm.active_terms}
    with torch.inference_mode():
        for k in range(H):
            q_ref = cmd.joint_pos                                  # reference joints at the current command frame
            action = (q_ref - offset) / scale
            env.step(action)
            if args.mode == "playback":
                cmd._finalize_reference(all_ids)                   # teleport onto the (already advanced) reference
            failed = tm.terminated.bool()
            for i in torch.nonzero(failed & alive).flatten().tolist():
                cause[i] = ",".join(n for n in tm.active_terms if bool(tm.get_term(n)[i]))
            e = cmd.metrics["error_body_pos"]
            err_sum += torch.where(alive, e, torch.zeros_like(e)); err_n += alive.float()
            for n in rm.active_terms:
                v = rm._step_reward[:, rm.active_terms.index(n)] if hasattr(rm, "_step_reward") else None
                if v is not None:
                    rew_sums[n] += torch.where(alive, v, torch.zeros_like(v))
            reached = (k + 1) >= horizon_env
            surv += alive.float()
            done_ok |= alive & reached & ~failed
            alive &= ~(failed | reached)
            if not alive.any():
                break
    ok = (done_ok | alive).float().cpu().numpy(); ss = (surv * env.step_dt).cpu().numpy(); me = (err_sum / err_n.clamp(min=1)).cpu().numpy()
    rows = []
    print(f"[admit] mode={args.mode} gain x{args.gain_scale} nominal={args.nominal}")
    for ci, name in enumerate(names):
        line = []
        for oi, o in enumerate(offsets):
            idx = [i for i, (c, oo) in enumerate(layout) if c == ci and oo == oi]
            s = float(ok[idx].mean()); t = float(ss[idx].mean()); er = float(me[idx].mean())
            causes = {}
            for i in idx:
                if cause[i]:
                    for c_ in cause[i].split(","):
                        causes[c_] = causes.get(c_, 0) + 1
            rr = {n: round(float(rew_sums[n][idx].sum() / max(surv[idx].sum().item(), 1)), 4) for n in rm.active_terms}
            rows.append({"clip": name, "offset_s": o, "mode": args.mode, "gain_scale": args.gain_scale, "survival": round(s, 3),
                         "mean_survival_s": round(t, 2), "mean_body_pos_err": round(er, 4), "causes": ";".join(f"{a}:{b}" for a, b in causes.items()), **{f"r_{n}": v for n, v in rr.items()}})
            line.append(f"{o:g}s:{s:.2f}({t:.1f}s,e{er:.3f}{',' + '/'.join(causes) if causes else ''})")
        print(f"  {name[:44]:46s} " + "  ".join(line))
    with open(args.out, "w") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print("[admit] wrote", args.out)
    env.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
