#!/usr/bin/env python3
"""P-SIGN -- generality of the motor-strength sign reversal (seal: plan/PREREGISTRATION_P_SIGN.md, c7916e8c).

24 clips (12 N1-flagged family + 12 feasible ground controls) x 8 replicate ICs x
{base, motor-15%, motor+15%} on Newton (arm A) + stock-mjlab base worlds (arm C, per-run floor).
GPU gap capacity only. Analysis: tools/analyze_p_sign.py.

Usage: p_sign_gate.py --checkpoint model_3999.pt --out reports/P_SIGN/run0
"""
from __future__ import annotations
import argparse, json, os, sys
import numpy as np, torch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import g1_clip44_gate as G
import s1_newton_conformance as S1

CONFIGS = [("base", None, 0.0), ("motor-", "motor", -0.15), ("motor+", "motor", +0.15)]

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--replicates", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    G.CONFIGS = CONFIGS                      # the seal's configs, in place of the G1 set
    fam = [l.strip() for l in open("/data/robotixx/climb/plan/P_SIGN_clips_family.txt") if l.strip()]
    ctl = [l.strip() for l in open("/data/robotixx/climb/plan/P_SIGN_clips_controls.txt") if l.strip()]
    clips = fam + ctl
    clip_paths = [os.path.join(G.BANK, c + ".npz") for c in clips]
    R = args.replicates
    names = [c[0] for c in CONFIGS]
    world_clip, world_rep, world_cfg = [], [], []
    for ci in range(len(clips)):
        for r in range(R):
            for nm in names:
                world_clip.append(ci); world_rep.append(r); world_cfg.append(nm)
    N = len(world_cfg)
    print(f"[P-SIGN] {len(clips)} clips ({len(fam)} family + {len(ctl)} controls) x {R} x {len(names)} = {N} worlds")
    env, wrapped, agent_cfg, runner_cls = G.build_env(clip_paths, N, args.device)
    policy = S1.load_policy(runner_cls, wrapped, agent_cfg, args.checkpoint, args.device)
    horizon = int(10.0 / env.step_dt)
    bank = env.command_manager.get_term("motion").motion
    clip_len_s = [float(bank.clip_len[i]) / float(bank.fps) for i in range(len(clips))]
    dev = args.device
    clip_ids = torch.tensor(world_clip, dtype=torch.long, device=dev)
    g = torch.Generator(device="cpu").manual_seed(args.seed)
    nq_j = env.sim.mj_model.nq - 7
    keyR = torch.tensor([ci * R + r for ci, r in zip(world_clip, world_rep)])
    J = (torch.rand(len(clips) * R, nq_j, generator=g) * 2 - 1) * 0.05
    L = (torch.rand(len(clips) * R, 3, generator=g) * 2 - 1) * 0.1
    A_ = (torch.rand(len(clips) * R, 3, generator=g) * 2 - 1) * 0.2
    ic_noise = {"joint": J[keyR].to(dev), "lin": L[keyR].to(dev), "ang": A_[keyR].to(dev)}
    json.dump({"clips": clips, "n_family": len(fam), "replicates": R, "configs": names,
               "world_clip": world_clip, "world_rep": world_rep, "world_cfg": world_cfg,
               "delta": {"motor": 0.15}, "horizon": horizon, "step_dt": env.step_dt,
               "seed": args.seed, "checkpoint": args.checkpoint, "clip_len_s": clip_len_s,
               "seal": "plan/PREREGISTRATION_P_SIGN.md c7916e8c"},
              open(os.path.join(args.out, "meta.json"), "w"), indent=2)
    import mujoco
    mA = env.sim.mj_model
    gnA = lambda i: (mujoco.mj_id2name(mA, mujoco.mjtObj.mjOBJ_GEOM, i) or "")
    mjlab_geoms = ([i for i in range(mA.ngeom) if "left_foot" in gnA(i)],
                   [i for i in range(mA.ngeom) if "right_foot" in gnA(i)],
                   [i for i in range(mA.ngeom) if gnA(i) == "terrain"])
    print("[P-SIGN] arm C: stock mjlab (per-run floor)")
    outC = G.rollout(env, wrapped, policy, None, clip_ids, ic_noise, horizon, "C", mjlab_geoms=mjlab_geoms)
    np.savez_compressed(os.path.join(args.out, "armC.npz"), **outC)
    phys = S1.NewtonPhysics(env, "mjw", dev)
    itv = G.Interventions(phys, world_cfg, dev)
    print("[P-SIGN] arm A: Newton, motor +/-15%")
    outA = G.rollout(env, wrapped, policy, phys, clip_ids, ic_noise, horizon, "A", itv=itv)
    np.savez_compressed(os.path.join(args.out, "armA.npz"), **outA)
    print("[P-SIGN] done ->", args.out)
    env.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
