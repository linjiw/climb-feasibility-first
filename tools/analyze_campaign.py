#!/usr/bin/env python3
"""Compare sampler arms by compute-matched learning curve and AULC.

The plan's claim is about held-out performance *per unit compute*, so the
comparison is between learning curves, not endpoints: a curriculum that reaches
the same final score sooner and a curriculum that reaches a higher final score
are different claims, and only a curve separates them.

Curves are indexed by training iteration rather than wall-clock. On a shared GPU
wall-clock varies with whatever else is running, which would otherwise show up
as a sampler effect. Iteration count is invariant to that; GPU-hours can be
recovered afterwards by multiplying through a measured s/iteration.

Reports per-arm mean and spread across seeds, plus an exact paired sign-flip
test over seeds at the final iteration. With 3 seeds the smallest attainable
one-sided p is 0.125, so this cannot reach conventional significance -- it is
reported to keep the honest bound visible, not to claim one.

Usage:
    analyze_campaign.py --dir reports/campaign [--out campaign_summary.json]
"""

from __future__ import annotations

import argparse
import csv
import glob
import itertools
import json
import os
import re
from collections import defaultdict

import numpy as np

NAME = re.compile(r"^(?P<arm>uniform|adaptive|grounded)-(?P<bank>[^-]+)-s(?P<seed>\d+)_it(?P<it>\d+)\.csv$")


def load(d: str):
    out: dict[tuple[str, int, int], float] = {}
    for path in sorted(glob.glob(os.path.join(d, "*.csv"))):
        m = NAME.match(os.path.basename(path))
        if not m:
            continue
        rows = list(csv.DictReader(open(path)))
        if not rows:
            continue
        sr = float(np.mean([float(r["survival_rate"]) for r in rows]))
        out[(m["arm"], int(m["seed"]), int(m["it"]))] = sr
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out")
    ap.add_argument("--target", type=float, default=0.810,
                    help="co-primary target held-out survival (pre-registered)")
    args = ap.parse_args()

    data = load(args.dir)
    if not data:
        print(f"no campaign CSVs in {args.dir}")
        return 1
    arms = sorted({k[0] for k in data})
    seeds = sorted({k[1] for k in data})
    iters = sorted({k[2] for k in data})
    print(f"arms={arms} seeds={seeds} checkpoints={len(iters)}\n")

    print(f"{'iter':>6s} " + " ".join(f"{a:>18s}" for a in arms) + "     delta")
    curves = defaultdict(list)
    for it in iters:
        cells, line = {}, f"{it:6d} "
        for a in arms:
            v = [data[(a, s, it)] for s in seeds if (a, s, it) in data]
            cells[a] = v
            curves[a].append(np.mean(v) if v else np.nan)
            line += (f"{np.mean(v):>10.3f}±{np.std(v):<7.3f}" if v else f"{'-':>18s}")
        if len(arms) == 2 and all(cells[a] for a in arms):
            line += f"  {np.mean(cells[arms[1]]) - np.mean(cells[arms[0]]):+.3f}"
        print(line)

    summary = {"arms": arms, "seeds": seeds, "iters": iters}
    print()
    for a in arms:
        c = np.array(curves[a], dtype=float)
        ok = ~np.isnan(c)
        # Trapezoid AUC over iterations, normalised to a mean survival so the
        # number stays comparable if the ladder length changes.
        aulc = (np.trapezoid(c[ok], np.array(iters)[ok]) /
                (np.array(iters)[ok][-1] - np.array(iters)[ok][0])) if ok.sum() > 1 else float("nan")
        # Co-primary (pre-registered in A2): iterations to reach the target,
        # fixed at 0.810 from the uniform control's Exp-1 endpoint before any
        # other arm was analysed. First checkpoint meeting it, no interpolation;
        # right-censored if never reached.
        it_arr = np.array(iters)[ok]
        hit = np.flatnonzero(c[ok] >= args.target)
        ttt = int(it_arr[hit[0]]) if hit.size else None
        summary[a] = {"final": round(float(c[ok][-1]), 4) if ok.any() else None,
                      "aulc": round(float(aulc), 4),
                      "iters_to_target": ttt, "target": args.target,
                      "censored": ttt is None}
        ttt_s = str(ttt) if ttt is not None else f"censored (>{int(it_arr[-1])})"
        print(f"{a:>10s}  final={summary[a]['final']}  normalised AULC={summary[a]['aulc']}"
              f"  iters-to-{args.target}={ttt_s}")

    # Every arm is compared against the uniform control, not against whichever
    # arm sorts first -- with three arms the alphabetical pair would silently
    # become adaptive-vs-grounded and skip the control entirely.
    base = "uniform" if "uniform" in arms else arms[0]
    summary["paired"] = {}
    for other in [a for a in arms if a != base]:
        last = iters[-1]
        pairs = [(data[(base, s, last)] - data[(other, s, last)])
                 for s in seeds
                 if all((a, s, last) in data for a in (base, other))]
        n = len(pairs)
        if n:
            wins = sum(1 for d in pairs if d > 0)
            # Exact one-sided sign-flip test: enumerate every assignment of
            # signs to the paired differences.
            obs = float(np.mean(pairs))
            flips = [float(np.mean([s * d for s, d in zip(signs, pairs)]))
                     for signs in itertools.product([1, -1], repeat=n)]
            p = float(np.mean([f >= obs for f in flips]))
            print(f"\n{base} vs {other}, paired over {n} seeds at iter {last}: "
                  f"mean delta = {obs:+.4f}, {wins}/{n} seeds favour {base}")
            print(f"exact one-sided sign-flip p = {p:.3f} "
                  f"(floor at n={n} is {1/2**n:.3f})")
            cell = {"n_seeds": n, "mean_delta": round(obs, 4),
                    "wins_for_" + base: wins, "p_one_sided": round(p, 4),
                    "p_floor": round(1 / 2 ** n, 4)}
            summary["paired"][f"{base}_vs_{other}"] = cell

            # The sign-flip test throws away magnitude, so its p cannot go below
            # 1/2^n however large the effect. These runs are far more
            # reproducible than that assumes -- the uniform arm's seed spread is
            # ~0.001 at the endpoint -- so a magnitude-aware summary carries the
            # information the sign test discards. Reported alongside, not
            # instead: the sign test needs no distributional assumption.
            if n >= 2:
                sd = float(np.std(pairs, ddof=1))
                if sd > 0:
                    t = obs / (sd / np.sqrt(n))
                    print(f"effect size: mean delta / seed sd = {obs/sd:+.1f}  "
                          f"(paired t = {t:+.2f}, df = {n-1})")
                    cell.update(seed_sd=round(sd, 5),
                                cohens_dz=round(obs / sd, 3),
                                t_stat=round(float(t), 3))
                else:
                    print(f"effect size: all {n} seed deltas identical "
                          f"({obs:+.4f}); seed sd = 0")

    if args.out:
        json.dump(summary, open(args.out, "w"), indent=2)
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
