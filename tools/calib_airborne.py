#!/usr/bin/env python3
"""Instrument calibration: does the feasibility screen distinguish ballistic flight from floating?

Builds three synthetic root trajectories from one standing pose (donor: a clean stand clip) and
runs the pinned screen (gap 0.06, --brief thresholds) on them plus one real jump:
  ballistic  -- projectile arc, airborne 100% of the clip: momentum change fully explained by
                gravity, so required external wrench ~ 0 -> must PASS;
  hover      -- constant height, zero velocity: needs +mg with no contact -> must FLAG;
  slow_sink  -- constant 0.3 m/s descent (clip #44's failure mode): needs ~mg of brake force
                with no contact -> must FLAG.
The screen flags unexplained momentum change, not absence of contact; free fall is exempt by
construction of the inverse dynamics, not by a whitelist. Outputs land in
reports/calibration_airborne/. See summary.md there for the verdicts and known biases.
"""
import glob
import json
import os
import subprocess
import sys

import numpy as np

R = "/data/robotixx/climb"
OUT = f"{R}/reports/calibration_airborne"
DONOR = "ACCAD_Female1General_c3d_A1_-_Stand_poses_120_jpos"
JUMP = "DFaust_67_50020_50020_one_leg_jump_poses_60_jpos"
G = 9.81


def build_synthetics(tmp):
    d = np.load(f"{R}/bank/amass/{DONOR}.npz")
    fps = float(np.asarray(d["fps"]).reshape(-1)[0])
    k0 = d["joint_pos"].shape[0] // 2
    T = int(1.2 * fps)
    t = np.arange(T) / fps

    def make(name, z_of_t, vz_of_t):
        out = {}
        for key in d.files:
            arr = np.asarray(d[key])
            if arr.ndim == 0 or key == "fps":
                out[key] = arr
                continue
            out[key] = np.repeat(arr[k0:k0 + 1], T, axis=0)
        out["joint_vel"] = np.zeros_like(out["joint_vel"])
        for key in ("body_lin_vel_w", "body_ang_vel_w"):
            out[key] = np.zeros_like(out[key])
        out["body_pos_w"] = out["body_pos_w"].copy()
        out["body_pos_w"][:, :, 2] += z_of_t(t)[:, None]   # rigid vertical shift of all bodies
        out["body_lin_vel_w"][:, :, 2] = vz_of_t(t)[:, None]
        np.savez(os.path.join(tmp, name + ".npz"), **out)

    v0 = G * t[-1] / 2                    # symmetric arc; never lands inside the clip
    make("calib_ballistic", lambda t: 0.20 + v0 * t - 0.5 * G * t**2, lambda t: v0 - G * t)
    make("calib_hover", lambda t: 0.50 + 0 * t, lambda t: 0 * t)
    make("calib_slowsink", lambda t: 0.60 - 0.3 * t, lambda t: 0 * t - 0.3)


def screen(clip, bank, xml, out_json, brief=True):
    cmd = [f"{R}/bridge/.venv/bin/python", f"{R}/refeas/refeas/screen.py", "--clip", clip,
           "--bank", bank, "--model", xml, "--t0", "0", "--t1", "1e9", "--gap", "0.06",
           "--out", out_json] + (["--brief"] if brief else [])
    subprocess.run(cmd, check=True, capture_output=True, env={**os.environ, "CUDA_VISIBLE_DEVICES": ""})
    return json.load(open(out_json))


def main():
    os.makedirs(OUT, exist_ok=True)
    xmls = sorted(glob.glob("/tmp/s1_*/g1_compiled.xml.mj.xml"), key=os.path.getmtime)
    if not xmls:
        sys.exit("no compiled G1 xml; run the S1 harness once")
    xml = xmls[-1]
    tmp = os.path.join(OUT, "npz")
    os.makedirs(tmp, exist_ok=True)
    build_synthetics(tmp)
    res = {"model": xml, "gap": 0.06, "flag_threshold_frac": 0.10, "cases": {}}
    for clip, expect in (("calib_ballistic", "PASS"), ("calib_hover", "FLAG"), ("calib_slowsink", "FLAG")):
        b = screen(clip, tmp, xml, f"{OUT}/{clip}.json")
        got = "FLAG" if b["infeasible_frac"] > 0.10 else "PASS"
        # boundary-corrected: the zero-padded smoother corrupts ~5 frames per clip end, so the
        # synthetic verdict uses interior frames only (real clips absorb this in the 10% threshold)
        full = screen(clip, tmp, xml, f"{OUT}/{clip}_full.json", brief=False)
        uf = np.array([f["real"]["unsupported_force_N"] for f in full["frames"]])
        W = full["total_mass_kg"] * G
        interior = uf[5:-5]
        res["cases"][clip] = {"expect": expect, "brief": b, "verdict_raw": got,
                              "interior_unsup_F_median_N": float(np.median(interior)),
                              "interior_unsup_F_max_N": float(interior.max()),
                              "interior_frac_over_half_weight": float((interior > 0.5 * W).mean())}
        print(f"{clip:16s} airborne={b['airborne_frac']:.2f} infeasible={b['infeasible_frac']:.3f} "
              f"interior_max={interior.max():.1f}N  expect={expect}")
    # real jump: mid-flight must be clean; over-threshold frames must hug contact transitions
    full = screen(JUMP, f"{R}/bank/amass", xml, f"{OUT}/real_jump_full.json", brief=False)
    fr = full["frames"]
    W = full["total_mass_kg"] * G
    air = np.array([f["n_contacts"] == 0 for f in fr])
    uf = np.array([f["real"]["unsupported_force_N"] for f in fr])
    over = np.where((uf > 0.5 * W) & air)[0]
    trans = np.where(np.diff(air.astype(int)) != 0)[0]
    dists = [int(np.min(np.abs(trans - i))) for i in over]
    res["real_jump"] = {"clip": JUMP, "frames": len(fr), "airborne": int(air.sum()),
                        "airborne_unsup_F_median_N": float(np.median(uf[air])),
                        "n_over_threshold": len(over),
                        "max_dist_to_contact_transition_frames": max(dists) if dists else 0}
    print(f"real jump: {air.sum()} airborne frames, median unsupported {np.median(uf[air]):.1f} N, "
          f"{len(over)} over threshold, all within {max(dists) if dists else 0} frames of takeoff/landing")
    json.dump(res, open(f"{OUT}/calibration.json", "w"), indent=1)
    print("wrote", f"{OUT}/calibration.json")


if __name__ == "__main__":
    main()
