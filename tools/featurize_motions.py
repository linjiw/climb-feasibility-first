#!/usr/bin/env python3
"""Compute physics-grounded difficulty features for G1 motion clips (RQ1).

Produces the offline half of the difficulty atlas: the per-clip covariates that
H1 predicts will explain tracking difficulty better than clip length or raw
kinematic magnitude. The empirical half (success-rate EMA, learning-progress
slope) only exists once training runs, and is joined on ``name`` later.

Features fall into two families, which is the comparison H1 actually rests on:

  kinematic  -- CoM speed and excursion, whole-body angular momentum, joint
                velocity and jerk percentiles
  dynamic    -- flight-phase fraction, contact-switch rate, support-polygon
                margin, and inverse-dynamics torque demand against the real
                per-motor effort limits

Torque comes from MuJoCo inverse dynamics on the mjlab-compiled model, so it
carries the actuator armature and the parallel-linkage ankle/waist treatment
that the raw XML does not have.

Usage:
    featurize_motions.py --bank BANK_DIR --out features.csv
    featurize_motions.py --bank BANK_DIR --out f.csv --segment-seconds 2.0
"""

from __future__ import annotations

import argparse
import csv
import glob
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def quat_to_mat(q: np.ndarray) -> np.ndarray:
    q = q / np.linalg.norm(q, axis=-1, keepdims=True)
    w, x, y, z = q[..., 0], q[..., 1], q[..., 2], q[..., 3]
    return np.stack(
        [
            1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y),
            2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x),
            2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y),
        ],
        axis=-1,
    ).reshape(*q.shape[:-1], 3, 3)


class G1Model:
    """The mjlab-compiled G1: actuated, with armature and effort limits."""

    def __init__(self, device: str = "cpu"):
        import mujoco  # noqa: PLC0415
        from mjlab.scene import Scene  # noqa: PLC0415
        from mjlab.tasks.tracking.config.g1.env_cfgs import (  # noqa: PLC0415
            unitree_g1_flat_tracking_env_cfg,
        )

        self.mujoco = mujoco
        scene = Scene(unitree_g1_flat_tracking_env_cfg().scene, device=device)
        spec = scene.compile()
        self.m = spec if isinstance(spec, mujoco.MjModel) else mujoco.MjModel.from_spec(spec)
        self.d = mujoco.MjData(self.m)

        # The compiled scene is world + terrain + the robot's 30 bodies under a
        # "robot/" prefix. Only the robot bodies correspond to the npz body axis.
        all_names = [mujoco.mj_id2name(self.m, mujoco.mjtObj.mjOBJ_BODY, i)
                     for i in range(self.m.nbody)]
        self.body_ids = [i for i, n in enumerate(all_names)
                         if n and n.startswith("robot/")]
        if not self.body_ids:
            raise RuntimeError(f"no robot/* bodies in compiled scene: {all_names[:6]}")
        self.mass = self.m.body_mass[self.body_ids].copy()
        self.total_mass = float(self.mass.sum())
        self.inertia = self.m.body_inertia[self.body_ids].copy()
        self.nbody = len(self.body_ids)

        # Per-DoF effort limits from the compiled actuators, mapped to joint dofs.
        self.effort = np.full(self.m.nv, np.nan)
        for a in range(self.m.nu):
            trnid = self.m.actuator_trnid[a, 0]
            if self.m.actuator_trntype[a] == mujoco.mjtTrn.mjTRN_JOINT:
                dof = self.m.jnt_dofadr[trnid]
                fr = self.m.actuator_forcerange[a]
                gear = self.m.actuator_gear[a, 0] or 1.0
                if self.m.actuator_forcelimited[a] and fr[1] > 0:
                    self.effort[dof] = float(fr[1] * abs(gear))
        self.n_effort = int(np.isfinite(self.effort).sum())

        # Contact is measured against the real terrain geom rather than inferred
        # from body heights, so there is no ground level to estimate.
        self.floor_geom = next(
            (i for i in range(self.m.ngeom)
             if self.m.geom_type[i] == mujoco.mjtGeom.mjGEOM_PLANE), None)
        if self.floor_geom is None:
            raise RuntimeError("no plane geom in the compiled scene")

        self.foot_geoms = {"left": [], "right": []}
        other = []
        for gi in range(self.m.ngeom):
            n = mujoco.mj_id2name(self.m, mujoco.mjtObj.mjOBJ_GEOM, gi)
            if not n or gi == self.floor_geom:
                continue
            if "left_foot" in n:
                self.foot_geoms["left"].append(gi)
            elif "right_foot" in n:
                self.foot_geoms["right"].append(gi)
            elif n.startswith("robot/"):
                other.append(gi)
        self.other_geoms = other

        # Indices into the npz body axis (i.e. positions within body_ids).
        self.body_names = [all_names[i].split("/", 1)[1] for i in self.body_ids]
        self.foot_body = {
            "left": self.body_names.index("left_ankle_roll_link"),
            "right": self.body_names.index("right_ankle_roll_link"),
        }

    def floor_distances(self, qpos: np.ndarray) -> tuple[float, float, float]:
        """Exact (left foot, right foot, everything else) clearance above the floor."""
        mj = self.mujoco
        self.d.qpos[:] = qpos
        mj.mj_kinematics(self.m, self.d)
        f = self.floor_geom
        dl = min(mj.mj_geomDistance(self.m, self.d, f, gi, 2.0, None)
                 for gi in self.foot_geoms["left"])
        dr = min(mj.mj_geomDistance(self.m, self.d, f, gi, 2.0, None)
                 for gi in self.foot_geoms["right"])
        do = min((mj.mj_geomDistance(self.m, self.d, f, gi, 2.0, None)
                  for gi in self.other_geoms), default=9.0)
        return dl, dr, do


def pct(a: np.ndarray, q: float) -> float:
    return float(np.percentile(a, q)) if a.size else float("nan")


def features_for(z, g: G1Model) -> dict:
    fps = float(np.asarray(z["fps"]).reshape(-1)[0])
    dt = 1.0 / fps
    bp = np.asarray(z["body_pos_w"], dtype=np.float64)      # (T, B, 3)
    bq = np.asarray(z["body_quat_w"], dtype=np.float64)
    bv = np.asarray(z["body_lin_vel_w"], dtype=np.float64)
    bw = np.asarray(z["body_ang_vel_w"], dtype=np.float64)
    jp = np.asarray(z["joint_pos"], dtype=np.float64)       # (T, 29)
    jv = np.asarray(z["joint_vel"], dtype=np.float64)
    T = bp.shape[0]

    m = g.mass[:, None]
    M = g.total_mass

    # --- centre of mass -----------------------------------------------------
    com = (bp * m).sum(axis=1) / M
    com_v = (bv * m).sum(axis=1) / M
    com_speed = np.linalg.norm(com_v[:, :2], axis=1)        # horizontal
    com_h = com[:, 2]

    # --- whole-body angular momentum about the CoM --------------------------
    R = quat_to_mat(bq)                                     # (T, B, 3, 3)
    r = bp - com[:, None, :]
    v = bv - com_v[:, None, :]
    L_orb = np.cross(r, v * m).sum(axis=1)
    I_world = R @ (g.inertia[None, :, :, None] * np.swapaxes(R, -1, -2))
    L_spin = np.einsum("tbij,tbj->tbi", I_world, bw).sum(axis=1)
    L = np.linalg.norm(L_orb + L_spin, axis=1)

    # --- joint kinematics ---------------------------------------------------
    jerk = np.diff(jv, n=2, axis=0) / (dt * dt) if T > 2 else np.zeros((1, jv.shape[1]))

    # --- feet, flight phase, contact switches -------------------------------
    # Contact is measured, not inferred. Successive height heuristics all failed
    # here: a min-over-clip ground reference is destroyed by one penetrating
    # frame, a foot-derived reference is meaningless while the robot is lying
    # down, and body origins are not surfaces. The terrain is a plane at z = 0
    # and exact geom distance costs ~0.1 s for a 13k-frame clip, so every frame
    # is queried directly.
    #
    # Distinguishing "no foot down" from "airborne" matters for this bank in
    # particular: the low-posture and multi-contact families are a deliberate
    # target, and conflating the two ranks fallAndGetUp above jumps for flight.
    ground = 0.0
    qpos = np.empty(g.m.nq)
    dl = np.empty(T)
    dr = np.empty(T)
    do = np.empty(T)
    for t in range(T):
        qpos[0:3] = bp[t, 0]
        qpos[3:7] = bq[t, 0]
        qpos[7:] = jp[t]
        dl[t], dr[t], do[t] = g.floor_distances(qpos)

    # Grounding quality doubles as the "retargeting residual" covariate: a well
    # grounded retarget puts the lower foot within a few mm of the plane, while
    # a floating one never touches. Measured here, the whole_body_tracking
    # retarget sits at a ~5 mm median clearance and the GMR retarget at
    # ~15-29 mm, which inflates every contact-derived feature for GMR clips.
    lower = np.minimum(dl, dr)
    clearance_p1 = float(np.percentile(lower, 1))
    clearance_p50 = float(np.percentile(lower, 50))
    penetration_max = float(-min(lower.min(), 0.0))
    # Penetration over every geom, not just the feet. The AMASS retargets sink
    # low-posture clips deep into the floor -- a crawl reaches 0.16 m median and
    # a lie-to-crouch 0.28 m peak -- which makes those references physically
    # untrackable. Low-posture families are a deliberate CLIMB target, so this
    # has to be screenable rather than discovered during training.
    body_penetration_max = float(-min(do.min(), lower.min(), 0.0))

    CONTACT = 0.02
    l_c, r_c = dl < CONTACT, dr < CONTACT
    other_c = do < CONTACT
    no_foot = ~l_c & ~r_c
    double = float((l_c & r_c).mean())
    flight = float((no_foot & ~other_c).mean())
    # Two different questions. grounded_nonfoot is "off the feet but still on the
    # ground" (a fall, a sit). nonfoot_ground is "anything but a foot is touching"
    # regardless of the feet, which is what actually catches crawling and
    # kneeling -- there the hands and knees are down while the feet are too.
    grounded_nonfoot = float((no_foot & other_c).mean())
    nonfoot_ground = float(other_c.mean())
    state = l_c.astype(np.int8) * 2 + r_c.astype(np.int8)
    switches = int((np.diff(state) != 0).sum())
    switch_rate = switches / (T * dt)

    # --- support-polygon margin ---------------------------------------------
    # Approximates the support polygon by the ankle-roll body positions: a
    # segment in double support, a point in single support. It therefore ignores
    # the ~0.2 x 0.1 m foot area, so margins run pessimistic by roughly a
    # half-foot-length. Fine as a relative difficulty ordering, not an absolute
    # stability criterion.
    margins = []
    for t in range(0, T, max(1, T // 400)):
        pts = []
        if l_c[t]:
            pts.append(bp[t, g.foot_body["left"], :2])
        if r_c[t]:
            pts.append(bp[t, g.foot_body["right"], :2])
        if not pts:
            margins.append(-0.5)                            # airborne
        elif len(pts) == 1:
            margins.append(-float(np.linalg.norm(com[t, :2] - pts[0])))
        else:
            a, b = pts
            ab = b - a
            n = np.linalg.norm(ab)
            if n < 1e-9:
                margins.append(-float(np.linalg.norm(com[t, :2] - a)))
            else:
                tt = np.clip(np.dot(com[t, :2] - a, ab) / (n * n), 0, 1)
                margins.append(-float(np.linalg.norm(com[t, :2] - (a + tt * ab))))
    margins = np.asarray(margins)

    # --- required ground reaction, from contact-free inverse dynamics -------
    #
    # Joint-torque utilisation is NOT computed here. Retargeted mocap does not
    # place the feet consistently on the terrain -- most frames report ncon=0 --
    # so MuJoCo's constraint solve contributes nothing and the resulting joint
    # torques are physically meaningless (a standing frame produced 354 N*m at a
    # 139 N*m motor while the root absorbed the full 327 N bodyweight).
    #
    # What IS well defined without a consistent contact state is the external
    # wrench the ground must supply. Contacts are disabled explicitly, so the
    # free-joint block of qfrc_inverse is exactly that wrench, and from it come
    # three feasibility measures that do not depend on penetration depth:
    #   required_mu  -- friction coefficient the ground must provide
    #   vert_force   -- peak vertical GRF in bodyweights
    #   cop_margin   -- centre of pressure vs the support polygon
    mj, mdl, data = g.mujoco, g.m, g.d
    nv = mdl.nv
    qvel = np.zeros((T, nv))
    qvel[:, 0:3] = bv[:, 0, :]
    qvel[:, 3:6] = np.einsum("tji,tj->ti", R[:, 0], bw[:, 0])   # world -> pelvis local
    qvel[:, 6:] = jv
    qacc = np.zeros_like(qvel)
    if T > 2:
        qacc[1:-1] = (qvel[2:] - qvel[:-2]) / (2 * dt)

    weight = M * abs(float(mdl.opt.gravity[2]))
    saved = mdl.opt.disableflags
    mdl.opt.disableflags = int(saved) | int(mj.mjtDisableBit.mjDSBL_CONTACT)

    step = max(1, T // 300)
    mus, fz_bw, cops = [], [], []
    try:
        for t in range(0, T, step):
            data.qpos[0:3] = bp[t, 0]
            data.qpos[3:7] = bq[t, 0]
            data.qpos[7:] = jp[t]
            data.qvel[:] = qvel[t]
            data.qacc[:] = qacc[t]
            mj.mj_inverse(mdl, data)
            F = data.qfrc_inverse[0:3].copy()               # world frame
            tau_b = data.qfrc_inverse[3:6].copy()           # pelvis frame
            fz = float(F[2])
            fz_bw.append(fz / weight)
            if fz > 0.05 * weight:                          # airborne frames say nothing
                mus.append(float(np.hypot(F[0], F[1]) / fz))
                tau_w = R[t, 0] @ tau_b
                M0 = tau_w + np.cross(bp[t, 0], F)
                cop = np.array([(ground * F[0] - M0[1]) / fz,
                                (M0[0] + ground * F[1]) / fz])
                pts = [bp[t, g.foot_body[s], :2] for s in ("left", "right")
                       if (l_c if s == "left" else r_c)[t]]
                if len(pts) == 2:
                    a, b = pts
                    ab = b - a
                    n = np.linalg.norm(ab)
                    tt = np.clip(np.dot(cop - a, ab) / (n * n), 0, 1) if n > 1e-9 else 0.0
                    cops.append(-float(np.linalg.norm(cop - (a + tt * ab))))
                elif len(pts) == 1:
                    cops.append(-float(np.linalg.norm(cop - pts[0])))
    finally:
        mdl.opt.disableflags = saved

    mus = np.asarray(mus) if mus else np.array([np.nan])
    fz_bw = np.asarray(fz_bw) if fz_bw else np.array([np.nan])
    cops = np.asarray(cops) if cops else np.array([np.nan])

    return {
        "frames": T,
        "duration_s": round(T * dt, 3),
        "fps": fps,
        # kinematic
        "com_speed_mean": round(float(com_speed.mean()), 4),
        "com_speed_p95": round(pct(com_speed, 95), 4),
        "com_height_range": round(float(com_h.max() - com_h.min()), 4),
        "com_height_std": round(float(com_h.std()), 4),
        "angmom_mean": round(float(L.mean()), 4),
        "angmom_peak": round(float(L.max()), 4),
        "joint_vel_p95": round(pct(np.abs(jv), 95), 4),
        "joint_vel_max": round(float(np.abs(jv).max()), 4),
        "jerk_p95": round(pct(np.abs(jerk), 95), 2),
        # dynamic / contact
        "flight_phase_frac": round(flight, 4),
        "nonfoot_contact_frac": round(grounded_nonfoot, 4),
        "nonfoot_ground_frac": round(nonfoot_ground, 4),
        "double_support_frac": round(double, 4),
        # retargeting residual / grounding quality
        "foot_clearance_p1": round(clearance_p1, 5),
        "foot_clearance_p50": round(clearance_p50, 5),
        "foot_penetration_max": round(penetration_max, 5),
        "body_penetration_max": round(body_penetration_max, 5),
        "contact_switch_rate": round(switch_rate, 4),
        "support_margin_mean": round(float(margins.mean()), 4),
        "support_margin_min": round(float(margins.min()), 4),
        # dynamic / required ground reaction
        "required_mu_p50": round(pct(mus, 50), 4),
        "required_mu_p95": round(pct(mus, 95), 4),
        "vert_force_bw_p95": round(pct(fz_bw, 95), 4),
        "vert_force_bw_max": round(float(np.nanmax(fz_bw)), 4),
        "cop_margin_mean": round(float(np.nanmean(cops)), 4),
        "cop_margin_min": round(float(np.nanmin(cops)), 4),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bank", required=True, help="directory of validated .npz clips")
    ap.add_argument("--out", required=True, help="output CSV")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.bank, "*.npz")))
    if args.limit:
        files = files[: args.limit]
    if not files:
        print("no clips found", file=sys.stderr)
        return 1

    g = G1Model()
    print(f"model: {g.nbody} bodies, {g.total_mass:.2f} kg, "
          f"effort limits on {g.n_effort}/{g.m.nv} dofs")
    print(f"featurizing {len(files)} clips -> {args.out}")

    rows = []
    for i, f in enumerate(files, 1):
        name = os.path.splitext(os.path.basename(f))[0]
        try:
            row = {"name": name}
            row.update(features_for(np.load(f), g))
            rows.append(row)
            if i % 25 == 0 or i == len(files):
                print(f"  [{i}/{len(files)}] {name}")
        except Exception as exc:  # noqa: BLE001
            print(f"  [{i}/{len(files)}] FAILED {name}: {type(exc).__name__}: {exc}")

    if not rows:
        return 1
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {len(rows)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
