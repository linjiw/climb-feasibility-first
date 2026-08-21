#!/usr/bin/env python3
"""Does dynamic feasibility predict policy failure *beyond* kinematics?

Evidence layer 1 of the FGAS plan (`plan/FGAS_DIRECTIVE_2026-08-19.md`). A screen that
merely re-encodes "this clip jumps" or "this clip crouches" would correlate with failure
while adding nothing: those motions are hard for reasons a kinematic descriptor already
sees. The claim worth defending is narrower -- that a *dynamic* feasibility measure carries
information about failure that kinematic descriptors do not.

So the headline number here is not the raw correlation. It is the **partial** correlation
after residualising against a battery of kinematic descriptors, plus the cross-validated
incremental R^2 from adding the feasibility block to a kinematic-only model.

Outcome: per-clip endpoints at iteration 3999, averaged over the seeds of one arm
(`reports/campaign/<arm>-mixed100-s*_it3999.csv`). Two outcomes are reported because they
disagree, and the disagreement is itself a finding: `survival_rate` (did the episode last)
and `mean_body_pos_err` (how well it tracked while it lasted), sign-flipped so that higher
is always better.

IMPORTANT, and easy to get wrong: those CSVs score `bank/tiers/heldout100.txt`, which is
**disjoint from the training bank** `tier_mixed100.txt` (verified: 0 of 100 shared). So this
is a ZERO-SHOT measurement -- feasibility predicting how well a policy tracks references it
never trained on. That is the cleaner claim, and it removes a confound that would exist on
training clips: a failure-adaptive sampler trains *more* on the clips that fail, so per-clip
survival there would partly reflect exposure rather than difficulty.

Everything is rank-transformed (Spearman throughout), so nothing here assumes linearity.

CPU-only, no GPU, no training. Reads only artifacts already on disk.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import sys

import numpy as np
from scipy import stats

R = "/data/robotixx/climb"
DEF_FEAS = f"{R}/reports/feasibility_all/feasibility.csv"
DEF_FEAT = f"{R}/reports/features_amass.csv"
DEF_CAMP = f"{R}/reports/campaign"

# Kinematic control battery: descriptors computable without any inverse dynamics, chosen to
# cover the explanations a reviewer reaches for first -- posture excursion, flight, jerk,
# required friction, joint speed, non-foot contact, translation speed, length, contact churn,
# ground clearance.
KINEMATIC = [
    "com_height_range", "flight_phase_frac", "jerk_p95", "required_mu_p95", "joint_vel_p95",
    "nonfoot_contact_frac", "com_speed_p95", "duration_s", "contact_switch_rate",
    "foot_clearance_p1",
]
# Feasibility block, from the inverse-dynamics + friction-cone + torque-limited LP screen.
FEASIBILITY = [
    "unsupported_impulse_per_weight_s",  # continuous severity: unsupported force x time / weight
    "infeasible_frac",                   # the binary-threshold basis (> 0.10 flags a clip)
    "airborne_frac",                     # no contact candidate within the gap
    "max_tau_ratio_p95",                 # torque headroom (from the torque-blind NNLS solve)
]


def _rank(v: np.ndarray) -> np.ndarray:
    r = stats.rankdata(v)
    return (r - r.mean()) / (r.std() + 1e-12)


def _residual(v: np.ndarray, X: np.ndarray) -> np.ndarray:
    A = np.column_stack([np.ones(len(v)), X])
    return v - A @ np.linalg.lstsq(A, v, rcond=None)[0]


def _ridge_cv_r2(X, y, folds=5, repeats=20, alphas=np.logspace(-2, 3, 20)) -> float:
    """Out-of-fold R^2 of a ridge fit, alpha chosen inside each training fold."""
    n = len(y)
    scores = []
    for seed in range(repeats):
        idx = np.random.default_rng(seed).permutation(n)
        for k in range(folds):
            te = idx[k::folds]
            tr = np.setdiff1d(idx, te)
            mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
            Xtr, Xte = (X[tr] - mu) / sd, (X[te] - mu) / sd
            ym = y[tr].mean()
            # inner selection on the training fold only
            best = None
            for a in alphas:
                inner = np.random.default_rng(seed + 991).permutation(len(tr))
                itr, ite = inner[: max(2, len(tr) * 4 // 5)], inner[max(2, len(tr) * 4 // 5):]
                if len(ite) < 2:
                    continue
                w = np.linalg.solve(
                    Xtr[itr].T @ Xtr[itr] + a * np.eye(X.shape[1]),
                    Xtr[itr].T @ (y[tr][itr] - y[tr][itr].mean()),
                )
                err = float(((y[tr][ite] - y[tr][itr].mean() - Xtr[ite] @ w) ** 2).mean())
                if best is None or err < best[0]:
                    best = (err, a)
            a = best[1] if best else 1.0
            w = np.linalg.solve(Xtr.T @ Xtr + a * np.eye(X.shape[1]), Xtr.T @ (y[tr] - ym))
            scores.append(
                1 - ((y[te] - ym - Xte @ w) ** 2).sum() / ((y[te] - ym) ** 2).sum()
            )
    return float(np.mean(scores))


def load(feas_path, feat_path):
    feas = {r["clip"]: r for r in csv.DictReader(open(feas_path))}
    feat = {r["name"]: r for r in csv.DictReader(open(feat_path))}
    return feas, feat


def outcome(camp_dir, arm, column, min_seeds=2):
    acc = {}
    for f in glob.glob(f"{camp_dir}/{arm}-mixed100-s*_it3999.csv"):
        for r in csv.DictReader(open(f)):
            try:
                acc.setdefault(r["clip"], []).append(float(r[column]))
            except (KeyError, ValueError):
                pass
    return {k: float(np.mean(v)) for k, v in acc.items() if len(v) >= min_seeds}


def analyse(arm, column, feas, feat, camp_dir):
    sign = 1.0 if column == "survival_rate" else -1.0  # higher is always better
    out = outcome(camp_dir, arm, column)
    clips = sorted(c for c in out if c in feas and c in feat)
    if len(clips) < 30:
        return None
    y = _rank(np.array([sign * out[c] for c in clips]))

    def col(name):
        src = feas if name in FEASIBILITY else feat
        return _rank(np.array([float(src[c][name]) for c in clips]))

    Xk = np.column_stack([col(n) for n in KINEMATIC])
    Xf = np.column_stack([col(n) for n in FEASIBILITY])
    ry = _residual(y, Xk)

    raw, partial = {}, {}
    for n in FEASIBILITY + KINEMATIC:
        x = col(n)
        rho, p = stats.spearmanr(x, y)
        raw[n] = {"rho": float(rho), "p": float(p)}
    for n in FEASIBILITY:
        rho, p = stats.spearmanr(_residual(col(n), Xk), ry)
        partial[n] = {"rho": float(rho), "p": float(p)}

    r_kin = _ridge_cv_r2(Xk, y)
    r_feas = _ridge_cv_r2(Xf, y)
    r_both = _ridge_cv_r2(np.column_stack([Xk, Xf]), y)
    return {
        "arm": arm, "outcome": column, "n_clips": len(clips),
        "raw_spearman": raw, "partial_spearman_control_kinematic": partial,
        "cv_r2": {"kinematic_only": r_kin, "feasibility_only": r_feas, "both": r_both,
                  "incremental_from_feasibility": r_both - r_kin},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--feasibility", default=DEF_FEAS)
    ap.add_argument("--features", default=DEF_FEAT)
    ap.add_argument("--campaign", default=DEF_CAMP)
    ap.add_argument("--arms", nargs="+", default=["uniform", "adaptive", "grounded"])
    ap.add_argument("--outcomes", nargs="+", default=["survival_rate", "mean_body_pos_err"])
    ap.add_argument("--out", default=f"{R}/reports/feasibility_predicts_failure.json")
    args = ap.parse_args()

    feas, feat = load(args.feasibility, args.features)
    results = []
    for arm in args.arms:
        for col in args.outcomes:
            r = analyse(arm, col, feas, feat, args.campaign)
            if r:
                results.append(r)
    if not results:
        print("no usable arm x outcome combination", file=sys.stderr)
        return 1

    def star(p):
        return "***" if p < 0.001 else "** " if p < 0.01 else "*  " if p < 0.05 else "   "

    print("PARTIAL Spearman with the endpoint, controlling for "
          f"{len(KINEMATIC)} kinematic descriptors")
    print(f"{'arm':<10}{'outcome':<16}{'n':>4}  " + "".join(f"{n[:22]:>24}" for n in FEASIBILITY))
    print("-" * (32 + 24 * len(FEASIBILITY)))
    for r in results:
        cells = "".join(
            f"{r['partial_spearman_control_kinematic'][n]['rho']:>21.3f}"
            f"{star(r['partial_spearman_control_kinematic'][n]['p'])}"
            for n in FEASIBILITY)
        lbl = "survival" if r["outcome"] == "survival_rate" else "-body_pos_err"
        print(f"{r['arm']:<10}{lbl:<16}{r['n_clips']:>4}  {cells}")

    print("\nCross-validated predictive R^2 (5-fold x 20 repeats, ridge on rank features)")
    print(f"{'arm':<10}{'outcome':<16}{'kinematic':>11}{'feasibility':>13}{'both':>8}{'incr':>8}")
    print("-" * 66)
    for r in results:
        c = r["cv_r2"]
        lbl = "survival" if r["outcome"] == "survival_rate" else "-body_pos_err"
        print(f"{r['arm']:<10}{lbl:<16}{c['kinematic_only']:>11.3f}"
              f"{c['feasibility_only']:>13.3f}{c['both']:>8.3f}"
              f"{c['incremental_from_feasibility']:>+8.3f}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump({"kinematic_controls": KINEMATIC, "feasibility_block": FEASIBILITY,
               "results": results}, open(args.out, "w"), indent=1)
    print(f"\nwrote {args.out}")
    print("\nCaveats: n = 100 clips on one bank, one eval protocol; ten controls on n = 100 is a "
          "lot of conditioning; and this is correlational -- the repaired-vs-raw paired "
          "intervention is the causal test, not this.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
