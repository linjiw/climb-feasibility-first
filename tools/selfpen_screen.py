#!/usr/bin/env python3
"""P-TAX companion: per-clip self-collision tax fraction on the reference, then the sealed
partial correlations (plan/PREREGISTRATION_P_TAX.md, sealed 7960057a before any result).

Tax fraction = fraction of reference frames (stride 2) with any robot-robot contact at
penetration > 1 cm, by forward kinematics on the pinned screen's model XML.
"""

from __future__ import annotations

import csv
import glob
import json
import os
import sys

import mujoco
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_atlas_transfer import FEATURES, per_clip_difficulty, spearman  # noqa: E402
from analyze_atlas_support import loo_predict  # noqa: E402

R = "/data/robotixx/climb/"
STRIDE = 2
THRESH = 0.01


def tax_fraction(m, d, clip, terrain):
    dat = np.load(R + "bank/amass/" + clip + ".npz")
    T = dat["joint_pos"].shape[0]
    n = 0
    hit = 0
    for k in range(0, T, STRIDE):
        d.qpos[:3] = dat["body_pos_w"][k, 0]
        d.qpos[3:7] = dat["body_quat_w"][k, 0]
        d.qpos[7:] = dat["joint_pos"][k]
        d.qvel[:] = 0
        mujoco.mj_forward(m, d)
        n += 1
        for i in range(d.ncon):
            c = d.contact[i]
            if c.geom1 == terrain or c.geom2 == terrain:
                continue
            if c.dist < -THRESH:
                hit += 1
                break
    return hit / max(n, 1)


def partial_spearman(x, y, z, nboot=2000, rng=None):
    """Spearman of rank residuals of x and y after linear removal of z (the flag)."""
    rk = lambda v: np.argsort(np.argsort(v)).astype(float)
    def resid(v):
        rv = rk(v)
        Z = np.c_[z, np.ones_like(z)]
        w = np.linalg.lstsq(Z, rv, rcond=None)[0]
        return rv - Z @ w
    rx, ry = resid(x), resid(y)
    r = float(np.corrcoef(rx, ry)[0, 1])
    rng = rng or np.random.default_rng(0)
    n = len(x)
    boots = []
    for _ in range(nboot):
        i = rng.integers(0, n, n)
        if np.std(x[i]) < 1e-12 or np.std(y[i]) < 1e-12:
            continue
        rxi, ryi = resid(x[i]), resid(y[i])
        boots.append(float(np.corrcoef(rxi, ryi)[0, 1]))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return r, float(lo), float(hi)


def main():
    xml = sorted(glob.glob("/tmp/s1_*/g1_compiled.xml.mj.xml"), key=os.path.getmtime)[-1]
    m = mujoco.MjModel.from_xml_path(xml)
    d = mujoco.MjData(m)
    gname = lambda i: (mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, i) or "")
    terrain = [i for i in range(m.ngeom) if gname(i).endswith("terrain")][0]
    feats = {r["name"]: r for r in csv.DictReader(open(R + "reports/features_amass.csv"))}
    feas = {r["clip"]: float(r["infeasible_frac"]) for r in csv.DictReader(open(R + "reports/feasibility_e3/feasibility.csv"))}
    mixed = [l.strip() for l in open(R + "bank/tiers/tier_mixed100.txt") if l.strip()]
    held = [l.strip() for l in open(R + "bank/tiers/heldout100.txt") if l.strip()]
    out_csv = R + "reports/P_TAX_tax_fractions.csv"
    if os.path.exists(out_csv):
        tax = {r["clip"]: float(r["tax_fraction"]) for r in csv.DictReader(open(out_csv))}
    else:
        tax = {}
        for i, c in enumerate(sorted(set(mixed + held))):
            tax[c] = tax_fraction(m, d, c, terrain)
            if i % 25 == 0:
                print(f"  tax {i}/200 …", flush=True)
        with open(out_csv, "w") as fh:
            w = csv.writer(fh)
            w.writerow(["clip", "tax_fraction"])
            for c, v in sorted(tax.items()):
                w.writerow([c, f"{v:.4f}"])
    print(f"tax fractions: n={len(tax)}, median {np.median(list(tax.values())):.3f}, "
          f">0.1: {np.mean(np.array(list(tax.values()))>0.1)*100:.0f}%  -> {out_csv}")

    results = {"tool": "selfpen_screen.py", "stride": STRIDE, "thresh": THRESH, "T1": {}, "T2": {}}
    rng = np.random.default_rng(0)
    # ---- T1: training tier, atlas LOO residuals (uniform-s1), both protocols
    for tag, path in (("fixed", R + "reports/eval_tier_mixed100_fixed.csv"),
                      ("random", R + "reports/eval_tier_mixed100_rand.csv")):
        dd = {r["clip"]: 1.0 - float(r["survival_rate"]) for r in csv.DictReader(open(path))}
        clips = sorted(set(dd) & set(tax) & set(feats) & set(feas))
        Xi = np.array([[float(feats[c][f]) for f in FEATURES] for c in clips])
        y = np.array([dd[c] for c in clips])
        res = np.abs(y - loo_predict(Xi, y))
        tx = np.array([tax[c] for c in clips])
        fl = np.array([1.0 if feas[c] > 0.10 else 0.0 for c in clips])
        r, lo, hi = partial_spearman(tx, res, fl, rng=rng)
        r0 = spearman(tx, res)
        results["T1"][tag] = {"n": len(clips), "partial_r": r, "ci": [lo, hi], "raw_spearman": r0}
        print(f"T1[{tag}] partial rho(tax, |atlas resid| | flag) = {r:+.3f} [{lo:+.3f},{hi:+.3f}] (raw {r0:+.3f}, n={len(clips)})")
        # T2 training tier
        r2, lo2, hi2 = partial_spearman(tx, y, fl, rng=rng)
        results["T2"][f"train_{tag}"] = {"n": len(clips), "partial_r": r2, "ci": [lo2, hi2], "raw_spearman": spearman(tx, y)}
        print(f"T2[train_{tag}] partial rho(tax, difficulty | flag) = {r2:+.3f} [{lo2:+.3f},{hi2:+.3f}]")
    # ---- T2: heldout, per arm (sealed decision population)
    passes = 0
    for arm in ("uniform", "adaptive", "grounded"):
        dd, _ = per_clip_difficulty(R + "reports/campaign", arm)
        clips = sorted(set(dd) & set(tax) & set(feas))
        y = np.array([dd[c] for c in clips])
        tx = np.array([tax[c] for c in clips])
        fl = np.array([1.0 if feas[c] > 0.10 else 0.0 for c in clips])
        r, lo, hi = partial_spearman(tx, y, fl, rng=rng)
        sig = lo > 0
        passes += int(sig)
        results["T2"][f"heldout_{arm}"] = {"n": len(clips), "partial_r": r, "ci": [lo, hi],
                                           "raw_spearman": spearman(tx, y), "ci_excludes_zero_positive": bool(sig)}
        print(f"T2[heldout_{arm}] partial rho = {r:+.3f} [{lo:+.3f},{hi:+.3f}] raw {spearman(tx, y):+.3f} {'*' if sig else ''}")
    results["sealed_rule"] = {"needed": "positive CI excluding zero on >=2 heldout arms",
                              "arms_passing": passes, "paper_claim": bool(passes >= 2)}
    print(f"\nSEALED RULE: {passes}/3 heldout arms positive with CI excluding zero -> paper claim: {passes >= 2}")
    json.dump(results, open(R + "reports/P_TAX_result.json", "w"), indent=1)
    print("wrote reports/P_TAX_result.json")


if __name__ == "__main__":
    main()
