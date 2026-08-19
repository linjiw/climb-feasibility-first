#!/usr/bin/env python3
"""A3 — does the difficulty atlas describe the motions, or just one training run?

RQ1 established that physics features predict per-clip difficulty out-of-fold at
rho ~ 0.74. That was a single policy, so it cannot distinguish two readings:

  motion property   difficulty is intrinsic to the clip, and a model fit on one
                    policy predicts another policy's difficulty. The atlas is
                    usable as a prior for bank construction and for shaping a
                    sampler (plan v2, L3 grounding).

  run property      the fit is partly memorising which clips this policy happened
                    to struggle with. The atlas stays a descriptive contribution
                    and the L3 branch closes.

The test is a genuine transfer: fit features -> difficulty on the policies of one
arm, evaluate on the policies of a *different* arm. Both arms see the same clips
and the same budget, so a drop in rho is attributable to the policy rather than
to the data or the evaluation protocol.

Plan v2 criterion: rho >= 0.6 on transfer.

Usage:
    analyze_atlas_transfer.py --features features_amass.csv --dir reports/campaign
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
from collections import defaultdict

import numpy as np

NAME = re.compile(
    r"^(?P<arm>uniform|adaptive|grounded)-(?P<bank>[^-]+)-s(?P<seed>\d+)_it(?P<it>\d+)\.csv$"
)
KINEMATIC = ["com_speed_p95", "com_height_range", "joint_vel_p95", "jerk_p95", "angmom_peak"]
DYNAMIC = ["required_mu_p95", "vert_force_bw_max", "contact_switch_rate",
           "flight_phase_frac", "support_margin_mean", "cop_margin_mean"]
FEATURES = KINEMATIC + DYNAMIC   # nonfoot_ground_frac excluded: 6% support (RQ1)


def spearman(a, b):
    ra, rb = (np.argsort(np.argsort(v)).astype(float) for v in (a, b))
    return float(np.corrcoef(ra, rb)[0, 1]) if ra.std() and rb.std() else float("nan")


def per_clip_difficulty(d: str, arm: str, it: int | None = None):
    """Mean 1 - survival per clip, averaged over that arm's seeds."""
    acc = defaultdict(list)
    chosen = it
    for path in sorted(glob.glob(os.path.join(d, "*.csv"))):
        m = NAME.match(os.path.basename(path))
        if not m or m["arm"] != arm:
            continue
        if chosen is None:
            chosen = max(int(NAME.match(os.path.basename(p))["it"])
                         for p in glob.glob(os.path.join(d, f"{arm}-*.csv")))
        if int(m["it"]) != chosen:
            continue
        for r in csv.DictReader(open(path)):
            acc[r["clip"]].append(1.0 - float(r["survival_rate"]))
    return {c: float(np.mean(v)) for c, v in acc.items()}, chosen


def fit_predict(Xtr, ytr, Xte, ridge=1.0):
    mu, sd = Xtr.mean(0), Xtr.std(0)
    sd[sd < 1e-6] = 1.0
    Ztr = np.c_[(Xtr - mu) / sd, np.ones(len(Xtr))]
    Zte = np.c_[(Xte - mu) / sd, np.ones(len(Xte))]
    reg = ridge * np.eye(Ztr.shape[1])
    reg[-1, -1] = 0.0
    w = np.linalg.solve(Ztr.T @ Ztr + reg, Ztr.T @ ytr)
    return Zte @ w


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--features", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--criterion", type=float, default=0.6)
    ap.add_argument("--out")
    args = ap.parse_args()

    feats = {r["name"]: r for r in csv.DictReader(open(args.features))}
    arms = sorted({NAME.match(os.path.basename(p))["arm"]
                   for p in glob.glob(os.path.join(args.dir, "*.csv"))
                   if NAME.match(os.path.basename(p))})
    diff = {}
    for a in arms:
        d, it = per_clip_difficulty(args.dir, a)
        if d:
            diff[a] = d
            print(f"{a:>9s}: {len(d)} clips at iter {it}, "
                  f"difficulty mean {np.mean(list(d.values())):.3f} "
                  f"sd {np.std(list(d.values())):.3f}")
    if len(diff) < 2:
        print("\nneed at least two arms to test transfer")
        return 1

    clips = sorted(set.intersection(*(set(d) for d in diff.values())) & set(feats))
    X = np.array([[float(feats[c][f]) for f in FEATURES] for c in clips])
    print(f"\n{len(clips)} clips common to all arms and the atlas\n")

    # How much do the two arms' difficulty rankings agree to begin with? This is
    # the ceiling for any transfer: the atlas cannot predict arm B's difficulty
    # better than arm A's difficulty itself does.
    print("agreement between arms (ceiling for transfer):")
    ceilings = {}
    for i, a in enumerate(arms):
        for b in arms[i + 1:]:
            if a in diff and b in diff:
                r = spearman(np.array([diff[a][c] for c in clips]),
                             np.array([diff[b][c] for c in clips]))
                ceilings[f"{a}|{b}"] = round(r, 4)
                print(f"   rho({a}, {b}) = {r:+.3f}")

    print(f"\ntransfer: fit on one arm's policies, predict another's "
          f"(criterion rho >= {args.criterion})")
    results = {}
    for src in diff:
        for dst in diff:
            if src == dst:
                continue
            ytr = np.array([diff[src][c] for c in clips])
            yte = np.array([diff[dst][c] for c in clips])
            pred = fit_predict(X, ytr, X)          # in-sample fit, out-of-policy test
            r = spearman(pred, yte)
            ss_res = float(((yte - pred) ** 2).sum())
            ss_tot = float(((yte - yte.mean()) ** 2).sum())
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
            results[f"{src}->{dst}"] = {"spearman": round(r, 4), "r2": round(r2, 4)}
            flag = "PASS" if r >= args.criterion else "fail"
            print(f"   {src:>9s} -> {dst:<9s} rho={r:+.3f}  R2={r2:+.3f}   [{flag}]")

    rhos = [v["spearman"] for v in results.values()]
    ok = all(r >= args.criterion for r in rhos)
    print(f"\nH1 (atlas is a motion property): "
          f"{'SUPPORTED' if ok else 'NOT SUPPORTED'} "
          f"— min transfer rho {min(rhos):+.3f} vs criterion {args.criterion}")
    if ok:
        print("   L3 (physics-shaped prior, plan v2 §2) stays open.")
    else:
        print("   L3 gated off; atlas remains descriptive.")

    if args.out:
        json.dump({"criterion": args.criterion, "arm_agreement": ceilings,
                   "transfer": results, "supported": bool(ok)},
                  open(args.out, "w"), indent=2)
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
