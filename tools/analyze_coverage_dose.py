#!/usr/bin/env python3
"""A5 — does realized sampling coverage predict held-out performance?

Experiment 1 showed the error-adaptive arm collapses and loses. That pairs a
mechanism with an outcome, but only at the level of "arm A collapsed and arm A
lost", which is two data points dressed as an explanation. If coverage is really
the operative variable, it should behave like a dose: runs that hold more of it
should do better, and the relationship should hold *across* arms rather than
merely between them.

This regresses held-out AULC on realized coverage over every run, treating
coverage as a measured property of what the run actually did rather than as a
label for which arm it was. That distinction is the point -- the configured
curriculum and the delivered curriculum diverged in Exp-1, and only the
delivered one can be causal.

Coverage is summarised two ways, because they answer different questions:
  mean entropy   how spread the clip distribution was on average
  min entropy    how bad the worst collapse got

Usage:
    analyze_coverage_dose.py --logs logs/campaign --dir reports/campaign
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re

import numpy as np

RUN = re.compile(r"^(?P<arm>uniform|adaptive|grounded)-(?P<bank>[^-]+)-s(?P<seed>\d+)\.log$")
EVAL = re.compile(
    r"^(?P<arm>uniform|adaptive|grounded)-(?P<bank>[^-]+)-s(?P<seed>\d+)_it(?P<it>\d+)\.csv$"
)
MET = re.compile(r"sampling_clip_(entropy|top1_prob):\s*([0-9.]+)")


def coverage(log_path: str):
    ent, top = [], []
    for line in open(log_path, errors="ignore"):
        m = MET.search(line)
        if m:
            (ent if m.group(1) == "entropy" else top).append(float(m.group(2)))
    if not ent:
        return None
    e, t = np.array(ent), np.array(top)
    return {"mean_entropy": float(e.mean()), "min_entropy": float(e.min()),
            "max_top1": float(t.max()), "mean_top1": float(t.mean())}


def aulc(dir_: str, arm: str, seed: int):
    pts = {}
    for path in glob.glob(os.path.join(dir_, f"{arm}-*-s{seed}_it*.csv")):
        m = EVAL.match(os.path.basename(path))
        if not m or m["arm"] != arm or int(m["seed"]) != seed:
            continue
        rows = list(csv.DictReader(open(path)))
        if rows:
            pts[int(m["it"])] = float(np.mean([float(r["survival_rate"]) for r in rows]))
    if len(pts) < 2:
        return None, None
    it = np.array(sorted(pts))
    y = np.array([pts[i] for i in it])
    return float(np.trapezoid(y, it) / (it[-1] - it[0])), float(y[-1])


def spearman(a, b):
    ra, rb = (np.argsort(np.argsort(v)).astype(float) for v in (a, b))
    return float(np.corrcoef(ra, rb)[0, 1]) if ra.std() and rb.std() else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--logs", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out")
    args = ap.parse_args()

    rows = []
    for log in sorted(glob.glob(os.path.join(args.logs, "*.log"))):
        m = RUN.match(os.path.basename(log))
        if not m:
            continue
        cov = coverage(log)
        if not cov:
            continue
        a, final = aulc(args.dir, m["arm"], int(m["seed"]))
        if a is None:
            continue
        rows.append({"arm": m["arm"], "seed": int(m["seed"]), "aulc": a,
                     "final": final, **cov})

    if len(rows) < 4:
        print(f"only {len(rows)} complete runs — too few for a dose-response")
        for r in rows:
            print(f"   {r['arm']}-s{r['seed']}")
        return 1

    print(f"{'run':>20s} {'meanH':>7s} {'minH':>7s} {'maxTop1':>8s} {'AULC':>7s} {'final':>7s}")
    for r in sorted(rows, key=lambda r: -r["mean_entropy"]):
        print(f"{r['arm']+'-s'+str(r['seed']):>20s} {r['mean_entropy']:7.3f} "
              f"{r['min_entropy']:7.3f} {r['max_top1']:8.3f} {r['aulc']:7.3f} {r['final']:7.3f}")

    arms = sorted({r["arm"] for r in rows})
    print(f"\n{len(rows)} runs across {len(arms)} arms: {arms}")
    out = {"n_runs": len(rows), "arms": arms, "runs": rows, "correlations": {}}

    for xk in ("mean_entropy", "min_entropy", "max_top1"):
        for yk in ("aulc", "final"):
            x = np.array([r[xk] for r in rows])
            y = np.array([r[yk] for r in rows])
            r_ = spearman(x, y)
            out["correlations"][f"{xk}~{yk}"] = round(r_, 4)
            print(f"   rho({xk:>12s}, {yk:>5s}) = {r_:+.3f}")

    if len(arms) < 3:
        print("\nCaveat: with two arms, coverage is nearly collinear with arm identity, so\n"
              "these correlations cannot yet separate 'coverage matters' from 'this arm\n"
              "is worse for some other reason'. The grounded arm is the run that breaks\n"
              "the collinearity: it prioritises like adaptive but keeps coverage like\n"
              "uniform, so it sits between them on the x-axis and off the arm-identity\n"
              "line. Re-run once it lands.")
    else:
        # With three arms, within-arm variation lets coverage be tested as a
        # continuous variable rather than a proxy for the arm label.
        print("\nwithin-arm coverage-performance association (breaks collinearity):")
        for a in arms:
            sub = [r for r in rows if r["arm"] == a]
            if len(sub) >= 3:
                r_ = spearman(np.array([s["mean_entropy"] for s in sub]),
                              np.array([s["aulc"] for s in sub]))
                print(f"   {a:>9s} (n={len(sub)}): rho = {r_:+.3f}")
                out["correlations"][f"within_{a}"] = round(r_, 4)

    if args.out:
        json.dump(out, open(args.out, "w"), indent=2)
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
