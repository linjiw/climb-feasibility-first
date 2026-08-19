#!/usr/bin/env python3
"""Test H1: do dynamic-feasibility features predict tracking difficulty better
than kinematic magnitude or clip length?

Joins the offline physics atlas (featurize_motions.py) to measured per-clip
difficulty (climb_eval.py) and compares nested feature sets by cross-validated
R-squared. Cross-validation is not optional here: with ~50 clips and ~8
predictors, in-sample R-squared rises with any feature you add, so a
within-sample comparison would "confirm" H1 no matter what the features
contain. Out-of-fold prediction is the only version of the question that can
come back negative.

Feature sets, nested so each comparison isolates one claim:

    length     duration alone            -- the null H1 is stated against
    kinematic  magnitude of the motion   -- speed, excursion, jerk, momentum
    dynamic    feasibility for this robot-- friction demand, GRF, contact, margins
    all        kinematic + dynamic

Usage:
    analyze_rq1.py --features features_amass.csv --eval eval_tier50.csv \
                   --out rq1_report.json
"""

from __future__ import annotations

import argparse
import csv
import json
import math

import numpy as np

LENGTH = ["duration_s"]
KINEMATIC = ["com_speed_p95", "com_height_range", "joint_vel_p95", "jerk_p95",
             "angmom_peak"]
DYNAMIC = ["required_mu_p95", "vert_force_bw_max", "contact_switch_rate",
           "flight_phase_frac", "nonfoot_ground_frac", "support_margin_mean",
           "cop_margin_mean"]
SETS = {
    "length": LENGTH,
    "kinematic": KINEMATIC,
    "dynamic": DYNAMIC,
    "kinematic+dynamic": KINEMATIC + DYNAMIC,
    "all+length": LENGTH + KINEMATIC + DYNAMIC,
}


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    if ra.std() == 0 or rb.std() == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def cv_r2(X: np.ndarray, y: np.ndarray, folds: int, ridge: float,
          seed: int = 0) -> tuple[float, float]:
    """Out-of-fold R^2 and Spearman for a ridge fit."""
    n = len(y)
    rng = np.random.default_rng(seed)
    order = rng.permutation(n)
    pred = np.zeros(n)
    for k in range(folds):
        test = order[k::folds]
        train = np.setdiff1d(order, test)
        Xtr, ytr = X[train], y[train]
        mu, sd = Xtr.mean(0), Xtr.std(0)
        # A near-constant column (nonfoot_ground_frac is 0 for ~94% of clips)
        # gives a tiny but nonzero sd, and dividing a held-out outlier by it
        # blows the prediction up -- that is what produced a CV R^2 of -77.
        sd[sd < 1e-6] = 1.0
        Ztr = np.c_[(Xtr - mu) / sd, np.ones(len(train))]
        Zte = np.c_[(X[test] - mu) / sd, np.ones(len(test))]
        # Ridge, leaving the intercept unpenalised.
        p = Ztr.shape[1]
        reg = ridge * np.eye(p)
        reg[-1, -1] = 0.0
        w = np.linalg.solve(Ztr.T @ Ztr + reg, Ztr.T @ ytr)
        pred[test] = Zte @ w
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return (1 - ss_res / ss_tot if ss_tot > 0 else float("nan")), spearman(pred, y)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--features", required=True)
    ap.add_argument("--eval", required=True)
    ap.add_argument("--out")
    ap.add_argument("--target", default="difficulty",
                    choices=["difficulty", "mean_body_pos_err", "mean_survival_s"])
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--ridge", type=float, default=1.0)
    ap.add_argument("--min-support", type=float, default=0.15,
                    help="drop predictors nonzero in fewer than this fraction of clips")
    args = ap.parse_args()

    feats = {r["clip"] if "clip" in r else r["name"]: r
             for r in csv.DictReader(open(args.features))}
    evals = list(csv.DictReader(open(args.eval)))
    rows = [(e, feats[e["clip"]]) for e in evals if e["clip"] in feats]
    if len(rows) < 20:
        print(f"only {len(rows)} clips joined — too few to regress")
        return 1
    print(f"joined {len(rows)}/{len(evals)} evaluated clips to the atlas\n")

    if args.target == "difficulty":
        y = np.array([1.0 - float(e["survival_rate"]) for e, _ in rows])
    else:
        y = np.array([float(e[args.target]) for e, _ in rows])

    if y.std() == 0:
        print(f"target '{args.target}' has zero variance across clips "
              f"(all = {y[0]:.3f}) — the policy does not separate this bank, "
              f"so H1 is untestable on it. Train longer or use an easier bank.")
        return 2

    print(f"target = {args.target}: mean={y.mean():.3f} sd={y.std():.3f} "
          f"min={y.min():.3f} max={y.max():.3f}\n")

    print("univariate Spearman vs difficulty:")
    uni = {}
    for name in LENGTH + KINEMATIC + DYNAMIC:
        if name not in rows[0][1]:
            continue
        x = np.array([float(f[name]) for _, f in rows])
        r = spearman(x, y)
        uni[name] = round(r, 4)
        fam = ("len" if name in LENGTH else "kin" if name in KINEMATIC else "dyn")
        print(f"   [{fam}] {name:24s} {r:+.3f}")

    # Drop predictors with too little support to estimate. nonfoot_ground_frac
    # is nonzero in 6 of 100 clips here; in folds whose training split holds few
    # of those, standardisation hands held-out clips a huge z-score and the
    # prediction explodes -- that single column took the dynamic set's CV R^2
    # from +0.21 to -142 while its own rank correlation was -0.04. Excluding it
    # is a support rule, not a choice about which answer to get: it is applied
    # before any set is scored, and reported.
    dropped = {}
    for name in set(LENGTH + KINEMATIC + DYNAMIC):
        if name not in rows[0][1]:
            continue
        x = np.array([float(f[name]) for _, f in rows])
        support = float((x != 0).mean())
        if support < args.min_support or x.std() < 1e-8:
            dropped[name] = round(support, 3)
    if dropped:
        print("\nexcluded for insufficient support "
              f"(<{args.min_support:.0%} nonzero): "
              + ", ".join(f"{k} ({v:.0%})" for k, v in sorted(dropped.items())))

    print(f"\n{args.folds}-fold cross-validated prediction (ridge={args.ridge}):")
    print(f"   {'feature set':22s} {'k':>3s} {'CV R^2':>8s} {'CV rho':>8s}")
    results = {}
    for label, names in SETS.items():
        cols = [n for n in names if n in rows[0][1] and n not in dropped]
        if not cols:
            continue
        X = np.array([[float(f[c]) for c in cols] for _, f in rows])
        r2, rho = cv_r2(X, y, args.folds, args.ridge)
        results[label] = {"features": cols, "cv_r2": round(r2, 4),
                          "cv_spearman": round(rho, 4)}
        print(f"   {label:22s} {len(cols):3d} {r2:8.3f} {rho:8.3f}")

    kin = results.get("kinematic", {}).get("cv_r2", float("nan"))
    dyn = results.get("dynamic", {}).get("cv_r2", float("nan"))
    ln = results.get("length", {}).get("cv_r2", float("nan"))
    print("\nH1 (dynamic beats kinematic magnitude and clip length):")
    if not (math.isnan(kin) or math.isnan(dyn) or math.isnan(ln)):
        verdict = "SUPPORTED" if dyn > kin and dyn > ln else "NOT SUPPORTED"
        print(f"   dynamic {dyn:+.3f} vs kinematic {kin:+.3f} vs length {ln:+.3f}"
              f"  ->  {verdict}")
        print("   (single seed, single bank, single policy — a direction, not a result)")

    if args.out:
        json.dump({"n_clips": len(rows), "target": args.target,
                   "univariate_spearman": uni, "excluded_low_support": dropped,
                   "cv": results},
                  open(args.out, "w"), indent=2)
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
