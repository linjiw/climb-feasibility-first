#!/usr/bin/env python3
"""Kinodynamic contact projection — the lightweight repair baseline (N7 operator; v6-legal:
this builds and validates the *operator* on CPU; the sealed N7 *training* experiment is untouched).

Defect class it targets: retargets that float (airborne frames demanding support), from the #44
descent to whole CNRS walks. Repair: lower the root just enough that the lowest collision geom
touches the plane wherever the reference is unsupported, smoothly blended, never raising, joints
untouched — i.e. project the root trajectory onto the contact manifold, preserving the motion's
intent. Then re-run FK for body poses, re-derive velocities, and re-screen.

Per clip outputs: repaired .npz + a JSON report {infeasible_frac before/after, offset stats,
kinematic deviation}. Deviation budget: a repair "succeeds" if infeasible_frac_after <= 0.05 and
max root offset <= 0.15 m (else flagged as needing a stronger operator, e.g. IK/time-warp).

Usage:
  repair_contact_projection.py --clip NAME [--out-dir bank/repaired] [--report r.json]
  repair_contact_projection.py --census flagged_list.txt --out-dir /tmp/rep --report-dir reports/repair_census
"""
from __future__ import annotations

import argparse
import glob
import json
import os

import mujoco
import numpy as np

BANK = "/data/robotixx/climb/bank/amass"
CLEAR = 0.003          # target clearance under the lowest geom in unsupported frames [m]
SMOOTH_S = 0.24        # gaussian smoothing of the offset profile [s]
W_FRAC = 0.5           # unsupported > W_FRAC * weight marks a frame as needing support (matches screen)
GAP = 0.06


def model():
    xs = sorted(glob.glob("/tmp/s1_*/g1_compiled.xml.mj.xml"), key=os.path.getmtime)
    return mujoco.MjModel.from_xml_path(xs[-1])


def smooth1d(x, sigma_frames):
    if sigma_frames <= 0:
        return x
    n = int(4 * sigma_frames) | 1
    k = np.exp(-0.5 * ((np.arange(n) - n // 2) / sigma_frames) ** 2)
    k /= k.sum()
    return np.convolve(np.pad(x, n // 2, mode="edge"), k, mode="valid")


def repair(clip, out_dir, m=None, d=None):
    m = m or model()
    d = d or mujoco.MjData(m)
    gname = lambda i: (mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, i) or "").split("/")[-1]
    coll = [i for i in range(m.ngeom) if (m.geom_contype[i] or m.geom_conaffinity[i]) and gname(i) != "terrain"]
    plane = [i for i in range(m.ngeom) if gname(i) == "terrain"][0]
    dat = dict(np.load(os.path.join(BANK, clip + ".npz")))
    fps = float(np.asarray(dat["fps"]).reshape(-1)[0])
    T = dat["joint_pos"].shape[0]
    W = float(m.body_mass.sum()) * 9.81
    ft = np.zeros(6)

    # pass 1: per-frame lowest-geom distance and a cheap unsupported test
    # (needs-support proxy: no geom within GAP; the full LP is only needed for the re-screen)
    mind = np.zeros(T)
    for k in range(T):
        d.qpos[:3] = dat["body_pos_w"][k, 0]
        d.qpos[3:7] = dat["body_quat_w"][k, 0]
        d.qpos[7:] = dat["joint_pos"][k]
        mujoco.mj_forward(m, d)
        mind[k] = min(mujoco.mj_geomDistance(m, d, g, plane, 1.0, ft) for g in coll)
    needs = mind > GAP                      # nothing to push on within the screen's band
    # offset: exactly enough to land the lowest geom, only where needed; never raise (offset >= 0)
    raw = np.where(needs, np.maximum(mind - CLEAR, 0.0), 0.0)
    off = smooth1d(raw, SMOOTH_S * fps)
    off = np.minimum(off, np.maximum(mind - CLEAR, 0.0))   # smoothing must not push geoms below floor
    off = np.maximum(off, 0.0)

    # pass 2: apply to root z, re-run FK for all body poses, re-derive velocities
    bp = dat["body_pos_w"].copy()
    bq = dat["body_quat_w"].copy()
    for k in range(T):
        d.qpos[:3] = dat["body_pos_w"][k, 0]
        d.qpos[2] -= off[k]
        d.qpos[3:7] = dat["body_quat_w"][k, 0]
        d.qpos[7:] = dat["joint_pos"][k]
        mujoco.mj_forward(m, d)
        bp[k] = d.xpos[2:]
        bq[k] = d.xquat[2:]
    blv = np.gradient(bp, 1.0 / fps, axis=0)
    # angular velocities unchanged (orientations untouched by a pure z shift)
    out = dict(dat)
    out["body_pos_w"] = bp
    out["body_quat_w"] = bq
    out["body_lin_vel_w"] = blv
    os.makedirs(out_dir, exist_ok=True)
    np.savez_compressed(os.path.join(out_dir, clip + ".npz"), **out)
    return {"clip": clip, "frames": T, "fps": fps,
            "frames_needing_support": int(needs.sum()), "needs_frac": float(needs.mean()),
            "offset_max_m": float(off.max()), "offset_mean_when_active_m": float(off[off > 1e-4].mean()) if (off > 1e-4).any() else 0.0,
            "root_z_deviation_max_m": float(off.max()),
            "peak_added_downward_vel_mps": float(np.abs(np.gradient(off, 1.0 / fps)).max())}


def screen(clip, bank, tag):
    import subprocess
    outp = f"/tmp/rescreen_{tag}_{clip[:24]}.json"
    subprocess.run(["/data/robotixx/climb/bridge/.venv/bin/python", "/data/robotixx/climb/tools/n1_knee_id.py",
                    "--clip", clip, "--t0", "0", "--t1", "1e9", "--gap", str(GAP), "--brief", "--out", outp],
                   check=True, capture_output=True,
                   env={**os.environ, "CUDA_VISIBLE_DEVICES": ""})
    return json.load(open(outp))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--clip")
    ap.add_argument("--census", help="file of clip names to repair+rescreen")
    ap.add_argument("--out-dir", default="/data/robotixx/climb/bank/repaired")
    ap.add_argument("--report", default=None)
    ap.add_argument("--report-dir", default=None)
    a = ap.parse_args()
    m = model(); d = mujoco.MjData(m)
    global BANK
    clips = [a.clip] if a.clip else [l.strip() for l in open(a.census) if l.strip()]
    for clip in clips:
        rep = repair(clip, a.out_dir, m, d)
        before = screen(clip, BANK, "b")
        _bank = BANK
        BANK_saved = BANK
        # re-screen the repaired file by pointing the screen at out-dir via a symlinked bank? simplest: n1 takes --bank? it doesn't; use env override
        rep_after = screen_repaired(clip, a.out_dir)
        rep.update({"infeasible_frac_before": before["infeasible_frac"], "airborne_frac_before": before["airborne_frac"],
                    "infeasible_frac_after": rep_after["infeasible_frac"], "airborne_frac_after": rep_after["airborne_frac"],
                    "success": bool(rep_after["infeasible_frac"] <= 0.05 and rep["offset_max_m"] <= 0.15)})
        line = (f"{clip[:52]:54s} infeas {rep['infeasible_frac_before']:.2f}->{rep['infeasible_frac_after']:.2f} "
                f"offmax {rep['offset_max_m']:.3f} m  addvel {rep['peak_added_downward_vel_mps']:.2f} m/s  "
                f"{'OK' if rep['success'] else 'NEEDS-STRONGER-OP'}")
        print(line, flush=True)
        if a.report:
            json.dump(rep, open(a.report, "w"), indent=1)
        if a.report_dir:
            os.makedirs(a.report_dir, exist_ok=True)
            json.dump(rep, open(os.path.join(a.report_dir, clip + ".json"), "w"))


def screen_repaired(clip, rep_dir):
    """Run the screen against the repaired npz (screen reads BANK; copy via bank override)."""
    import subprocess, tempfile
    outp = f"/tmp/rescreen_a_{clip[:24]}.json"
    # n1_knee_id hardcodes BANK; run it with a patched env var via a tiny -c wrapper
    code = (
        "import sys; sys.path.insert(0,'/data/robotixx/climb/tools');\n"
        "import n1_knee_id as N; N.BANK = %r; sys.argv = ['x','--clip',%r,'--t0','0','--t1','1e9','--gap',%r,'--brief','--out',%r]; N.main()\n"
        % (rep_dir, clip, str(GAP), outp))
    subprocess.run(["/data/robotixx/climb/bridge/.venv/bin/python", "-c", code], check=True, capture_output=True,
                   env={**os.environ, "CUDA_VISIBLE_DEVICES": ""})
    return json.load(open(outp))


if __name__ == "__main__":
    main()
