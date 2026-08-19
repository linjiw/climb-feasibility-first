#!/usr/bin/env python3
"""G1 -- the clip #44 gate: paired-counterfactual fragility on Newton/SolverMuJoCo.

Pre-registered in plan/PREREGISTRATION_G1_clip44.md (read it first; nothing here
may deviate from it without a dated addendum). Six clips, R replicate initial
conditions, and per replicate a set of paired worlds that differ from the base
world in exactly one physical parameter:

    base | delay+ | motor-/+ | friction-/+ | solref-/+ | com-/+       (arm A, one model)
    condim+ (non-foot contacts frictional)                            (arm B, condim is per-model)
    stock mjlab baseline                                              (arm C, noise floor)

All worlds of a replicate share (obs, state) at t=0. Every rollout records the
phi vector per control step; analysis is in analyze_g1.py.

Usage:
    g1_clip44_gate.py --checkpoint model_3999.pt --out reports/G1/run0 [--replicates 8]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import s1_newton_conformance as S1  # noqa: E402

BANK = "/data/robotixx/climb/bank/amass"
CLIPS_FILE = "/data/robotixx/climb/plan/G1_clips.txt"

# (name, one_sided, magnitude) -- pre-registered
CONFIGS = [
    ("base", None, 0.0),
    ("delay+", "delay", +1),        # +1 control step = 20 ms (one-sided, base = 0)
    ("motor-", "motor", -0.15), ("motor+", "motor", +0.15),
    ("fric-", "fric", -0.2), ("fric+", "fric", +0.2),          # foot mu 0.6 -> 0.4 / 0.8
    ("solref-", "solref", -0.008), ("solref+", "solref", +0.008),  # 0.020 -> 0.012 / 0.028
    ("com-", "com", -0.02), ("com+", "com", +0.02),           # torso ipos x, m
]
DELTA = {"delay": 0.02, "motor": 0.15, "fric": 0.2, "solref": 0.008, "com": 0.02, "condim": 1.0}


# --------------------------------------------------------------------------- #
def build_env(clip_paths, num_envs, device):
    import climb  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.rl import RslRlVecEnvWrapper
    from mjlab.tasks.registry import load_rl_cfg, load_runner_cls
    from climb import climb_g1_tracking_env_cfg

    task = "Climb-Tracking-Flat-Unitree-G1"
    env_cfg = climb_g1_tracking_env_cfg(motion_files=list(clip_paths), sampling_mode="uniform")
    env_cfg.scene.num_envs = num_envs
    env_cfg.commands["motion"].resampling_time_range = (1.0e9, 1.0e9)
    # Nominal robot for the gate: no startup DR, no pushes, no obs noise
    # (pre-registration "Base configuration").
    for k in ("push_robot", "base_com", "foot_friction", "encoder_bias"):
        env_cfg.events.pop(k, None)
    for grp in env_cfg.observations.values():
        grp.enable_corruption = False
    agent_cfg = load_rl_cfg(task)
    env = ManagerBasedRlEnv(cfg=env_cfg, device=device)
    wrapped = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)
    return env, wrapped, agent_cfg, load_runner_cls(task)


# --------------------------------------------------------------------------- #
class Interventions:
    """Per-world parameter edits on Newton's MJWarp model + a per-world ctrl delay."""

    def __init__(self, phys, world_cfg: list[str], device):
        import mujoco
        import mujoco_warp as mjw
        import warp as wp
        from mjlab.sim.randomization import expand_model_fields

        self.phys = phys
        self.n = phys.n_env
        self.device = device
        m = phys.solver.mj_model
        M = phys.solver.mjw_model
        maps = phys._entity_maps()
        gname = lambda i: (mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, i) or "")
        bname = lambda i: (mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, i) or "")
        self.foot_geoms = [i for i in range(m.ngeom) if "foot" in gname(i) and "collision" in gname(i)]
        self.ground_geoms = [i for i in range(m.ngeom) if "ground" in gname(i)]
        self.nonfoot_geoms = [i for i in range(m.ngeom) if "collision" in gname(i) and "foot" not in gname(i)]
        self.torso = [i for i in range(m.nbody) if bname(i).endswith("torso_link")][0]
        assert len(self.foot_geoms) == 14 and len(self.nonfoot_geoms) == 19, (len(self.foot_geoms), len(self.nonfoot_geoms))
        self.left_feet = [i for i in self.foot_geoms if "left" in gname(i)]
        self.right_feet = [i for i in self.foot_geoms if "right" in gname(i)]

        fields = ["actuator_gainprm", "actuator_biasprm", "actuator_forcerange", "geom_friction", "geom_solref", "body_ipos"]
        with wp.ScopedDevice(device):
            expand_model_fields(M, self.n, fields)
        T = lambda f: wp.to_torch(getattr(M, f))
        gain, bias, frange = T("actuator_gainprm"), T("actuator_biasprm"), T("actuator_forcerange")
        fric, solref, ipos = T("geom_friction"), T("geom_solref"), T("body_ipos")
        self.nominal_forcerange = frange.clone()
        self.delay = torch.zeros(self.n, dtype=torch.long, device=device)
        for w, name in enumerate(world_cfg):
            kind, mag = next((k, v) for c, k, v in CONFIGS if c == name)
            if kind is None:
                continue
            if kind == "delay":
                self.delay[w] = int(mag)
            elif kind == "motor":
                s = 1.0 + mag
                gain[w, :, 0] *= s; bias[w, :, 1] *= s; bias[w, :, 2] *= s; frange[w] *= s
            elif kind == "fric":
                fric[w, self.foot_geoms, 0] = 0.6 + mag
            elif kind == "solref":
                solref[w, :, 0] = 0.02 + mag
            elif kind == "com":
                ipos[w, self.torso, 0] += mag
        with wp.ScopedDevice(device):
            mjw.set_const(M, phys.solver.mjw_data)
        self.forcerange = frange
        # ctrl FIFO for the delay axis: substep granularity, delay in control steps (x4 substeps)
        self.max_delay_sub = int(self.delay.max().item()) * phys.decimation
        self.hist = None
        self.head = 0
        phys.ctrl_for_substep = self._delayed_ctrl

    def _delayed_ctrl(self):
        cur = self.phys.env.sim.data.ctrl
        if self.max_delay_sub == 0:
            return cur
        if self.hist is None:
            L = self.max_delay_sub + 1
            self.hist = cur.unsqueeze(0).repeat(L, 1, 1).clone()
            self.head = 0
        self.head = (self.head + 1) % self.hist.shape[0]
        self.hist[self.head] = cur
        idx = (self.head - self.delay * self.phys.decimation) % self.hist.shape[0]
        return self.hist[idx, torch.arange(self.n, device=self.device)]

    def reset_delay(self):
        self.hist = None

    def set_condim_nonfoot(self, condim: int, mu: float | None):
        """Arm B: make the 19 non-foot robot geoms frictional (model-wide; condim is not per-world)."""
        import warp as wp
        M = self.phys.solver.mjw_model
        cd = wp.to_torch(M.geom_condim)
        cd[self.nonfoot_geoms] = condim
        self.phys.solver.mj_model.geom_condim[self.nonfoot_geoms] = condim
        if mu is not None:
            fric = wp.to_torch(M.geom_friction)
            fric[:, self.nonfoot_geoms, 0] = mu
        # MJWarp caches per-pair condim/params? contact.dim is computed at collision time from geom_condim.


# --------------------------------------------------------------------------- #
def foot_contacts(data, left_ids, right_ids, ground_ids, n_env, device):
    """(n_env, 2) bool: any left/right foot geom in contact with the ground this substep."""
    import warp as wp
    nacon = int(wp.to_torch(data.nacon)[0])
    out = torch.zeros(n_env, 2, dtype=torch.bool, device=device)
    if nacon == 0:
        return out
    g = wp.to_torch(data.contact.geom)[:nacon]
    w = wp.to_torch(data.contact.worldid)[:nacon].long()
    d = wp.to_torch(data.contact.dist)[:nacon]
    ng = int(max(g.max().item() + 1, max(left_ids + right_ids + ground_ids) + 1))
    side = torch.full((ng,), -1, dtype=torch.long, device=device)
    side[torch.tensor(left_ids, device=device)] = 0
    side[torch.tensor(right_ids, device=device)] = 1
    isg = torch.zeros(ng, dtype=torch.bool, device=device)
    isg[torch.tensor(ground_ids, device=device)] = True
    s0, s1 = side[g[:, 0]], side[g[:, 1]]
    ok = (d < 0) & ((isg[g[:, 0]] & (s1 >= 0)) | (isg[g[:, 1]] & (s0 >= 0)))
    sd = torch.where(s1 >= 0, s1, s0)
    out[w[ok], sd[ok]] = True
    return out


def rollout(env, wrapped, policy, phys, clip_ids, ic_noise, horizon, arm, itv=None, mjlab_geoms=None):
    """Roll all worlds; return dict of per-step arrays. Same IC per replicate group."""
    import warp as wp
    cmd = env.command_manager.get_term("motion")
    n = env.num_envs
    dev = env.device
    obs, _ = wrapped.reset()
    cmd.assign_clips(clip_ids, at_start=True)
    # replicate noise on top of the frame-0 teleport (pre-registered magnitudes), identical within a group
    q = env.sim.data.qpos
    qd = env.sim.data.qvel
    q[:, 7:] += ic_noise["joint"]
    qd[:, 0:3] += ic_noise["lin"]
    qd[:, 3:6] += ic_noise["ang"]
    env.sim.forward()
    obs = wrapped.get_observations()
    # identical solver warm-start at t=0 in every arm (they otherwise carry the previous rollout's)
    wp.to_torch(env.sim.wp_data.qacc_warmstart).zero_()
    if phys is not None:
        phys.sync_from_mjlab()
        wp.to_torch(phys.solver.mjw_data.qacc_warmstart).zero_()
        if itv is not None:
            itv.reset_delay()
    m = env.sim.mj_model
    lank = [i for i in range(m.nbody) if (m.body(i).name or "").endswith("left_ankle_roll_link")][0]
    rank = [i for i in range(m.nbody) if (m.body(i).name or "").endswith("right_ankle_roll_link")][0]
    act_qadr = torch.tensor([m.jnt_qposadr[m.actuator_trnid[i, 0]] for i in range(m.nu)], device=dev)
    frange = (itv.forcerange if (itv is not None and phys is not None) else
              torch.tensor(m.actuator_forcerange, dtype=torch.float32, device=dev)[None].repeat(n, 1, 1))
    alive = torch.ones(n, dtype=torch.bool, device=dev)
    rec = {k: [] for k in ("root_pos_err", "root_ori_err", "body_pos_err", "joint_pos_err", "contact", "foot_slip", "target_gap", "effort_sat", "alive", "root_z")}
    prev_ank = None
    t0 = time.time()
    with torch.no_grad():
        for k in range(horizon):
            act = policy(obs)
            if phys is None:
                obs, _, _, _ = wrapped.step(act)
                data = env.sim.wp_data
                cont = foot_contacts(data, mjlab_geoms[0], mjlab_geoms[1], mjlab_geoms[2], n, dev)
                af = wp.to_torch(data.actuator_force)
            else:
                obs, _, _, _ = S1._step_with_external_physics(env, wrapped, act, phys)
                data = phys.solver.mjw_data
                cont = foot_contacts(data, itv.left_feet, itv.right_feet, itv.ground_geoms, n, dev)
                af = wp.to_torch(data.actuator_force)
            failed = env.termination_manager.terminated.bool()
            alive &= ~failed
            xp = env.sim.data.xpos
            ank = torch.stack([xp[:, lank, :2], xp[:, rank, :2]], dim=1)   # (n,2,2)
            slip = torch.zeros(n, device=dev)
            if prev_ank is not None:
                v = (ank - prev_ank).norm(dim=-1) / env.step_dt        # (n,2)
                slip = torch.where(cont, v, torch.zeros_like(v)).sum(dim=1) / cont.sum(dim=1).clamp(min=1)
            prev_ank = ank
            gap = (env.sim.data.ctrl - env.sim.data.qpos[:, act_qadr]).abs().mean(dim=1)
            sat = (af.abs() >= 0.98 * frange[:, :, 1]).float().mean(dim=1)
            rec["root_pos_err"].append(cmd.metrics["error_anchor_pos"].clone())
            rec["root_ori_err"].append(cmd.metrics["error_anchor_rot"].clone())
            rec["body_pos_err"].append(cmd.metrics["error_body_pos"].clone())
            rec["joint_pos_err"].append(cmd.metrics["error_joint_pos"].clone())
            rec["contact"].append(cont.clone())
            rec["foot_slip"].append(slip)
            rec["target_gap"].append(gap)
            rec["effort_sat"].append(sat)
            rec["alive"].append(alive.clone())
            rec["root_z"].append(env.sim.data.qpos[:, 2].clone())
            if not alive.any():
                break
    out = {k: torch.stack(v).cpu().numpy() for k, v in rec.items()}
    out["wall_s"] = time.time() - t0
    print(f"  [{arm}] {len(rec['alive'])} steps, survivors {int(alive.sum())}/{n}, {out['wall_s']:.0f}s")
    return out


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--replicates", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--out", required=True)
    ap.add_argument("--arms", nargs="+", default=["A", "B", "C"])
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    clips = [l.strip() for l in open(CLIPS_FILE) if l.strip()]
    clip_paths = [os.path.join(BANK, c + ".npz") for c in clips]
    R = args.replicates
    names = [c[0] for c in CONFIGS]
    # world layout: clip-major, then replicate, then config
    world_clip, world_rep, world_cfg = [], [], []
    for ci in range(len(clips)):
        for r in range(R):
            for nm in names:
                world_clip.append(ci); world_rep.append(r); world_cfg.append(nm)
    N = len(world_cfg)
    print(f"[G1] {len(clips)} clips x {R} replicates x {len(names)} configs = {N} worlds")

    env, wrapped, agent_cfg, runner_cls = build_env(clip_paths, N, args.device)
    policy = S1.load_policy(runner_cls, wrapped, agent_cfg, args.checkpoint, args.device)
    horizon = int(10.0 / env.step_dt)      # 10 s; analysis restricts each clip to its own length
    bank = env.command_manager.get_term("motion").motion
    clip_len_s = [float(bank.clip_len[i]) / float(bank.fps) for i in range(len(clips))]
    dev = args.device
    clip_ids = torch.tensor(world_clip, dtype=torch.long, device=dev)

    # replicate IC noise: one draw per (clip, replicate), broadcast to its configs
    g = torch.Generator(device="cpu").manual_seed(args.seed)
    nq_j = env.sim.mj_model.nq - 7
    keyR = torch.tensor([ci * R + r for ci, r in zip(world_clip, world_rep)])
    J = (torch.rand(len(clips) * R, nq_j, generator=g) * 2 - 1) * 0.05
    L = (torch.rand(len(clips) * R, 3, generator=g) * 2 - 1) * 0.1
    A = (torch.rand(len(clips) * R, 3, generator=g) * 2 - 1) * 0.2
    ic_noise = {"joint": J[keyR].to(dev), "lin": L[keyR].to(dev), "ang": A[keyR].to(dev)}

    meta = {"clips": clips, "replicates": R, "configs": names, "world_clip": world_clip, "world_rep": world_rep,
            "world_cfg": world_cfg, "delta": DELTA, "horizon": horizon, "step_dt": env.step_dt, "seed": args.seed,
            "checkpoint": args.checkpoint, "clip_len_s": clip_len_s}
    json.dump(meta, open(os.path.join(args.out, "meta.json"), "w"), indent=2)

    import mujoco
    mA = env.sim.mj_model
    gnA = lambda i: (mujoco.mj_id2name(mA, mujoco.mjtObj.mjOBJ_GEOM, i) or "")
    mjlab_geoms = ([i for i in range(mA.ngeom) if "left_foot" in gnA(i)], [i for i in range(mA.ngeom) if "right_foot" in gnA(i)],
                   [i for i in range(mA.ngeom) if gnA(i) == "terrain"])

    if "C" in args.arms:
        print("[G1] arm C: stock mjlab (noise floor)")
        outC = rollout(env, wrapped, policy, None, clip_ids, ic_noise, horizon, "C", mjlab_geoms=mjlab_geoms)
        np.savez_compressed(os.path.join(args.out, "armC.npz"), **outC)

    phys = S1.NewtonPhysics(env, "mjw", dev)
    itv = Interventions(phys, world_cfg, dev)
    if "A" in args.arms:
        print("[G1] arm A: Newton, paired interventions")
        outA = rollout(env, wrapped, policy, phys, clip_ids, ic_noise, horizon, "A", itv=itv)
        np.savez_compressed(os.path.join(args.out, "armA.npz"), **outA)
    if "B" in args.arms:
        print("[G1] arm B: Newton, non-foot contacts frictional (condim 3, mu 0.6)")
        itv.set_condim_nonfoot(3, 0.6)
        outB = rollout(env, wrapped, policy, phys, clip_ids, ic_noise, horizon, "B", itv=itv)
        np.savez_compressed(os.path.join(args.out, "armB.npz"), **outB)
    print("[G1] done ->", args.out)
    env.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
