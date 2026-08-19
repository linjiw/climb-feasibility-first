#!/usr/bin/env python3
"""A7 — stale estimator, or attractor clip?

Exp-1 established that the error-adaptive sampler collapses onto one clip. Two
mechanisms produce that picture and they imply different fixes:

  stale estimator   the failure EMA lags. Mass piles onto clips that *were* hard
                    and have since been learned. The dominant clip should differ
                    across seeds, and its eval-measured survival at the time of
                    domination should be high. Fix class: estimator liveness --
                    keep every clip measured (the epsilon floor doing double duty
                    as coverage for the learner and refresh for the estimator).

  attractor clip    one clip is irreducibly hard, fails forever, and therefore
                    accumulates failure mass without bound. The dominant clip
                    should be the *same* across seeds, with near-zero eval
                    survival and a poor atlas feasibility profile. Fix class: a
                    per-clip mass cap -- an atlas-free L1 variant.

The discriminators are cheap and already on disk: sampling_top1_bin is logged
every iteration (recovering the dominant clip's identity), and the eval ladder
gives that clip's measured survival at each checkpoint.

Also computes band throughput -- clips crossing p=0.5 per 1k iterations -- which
should favour uniform if the collapsed arm is genuinely failing to move clips
through the frontier.

Usage:
    analyze_attractor.py --logs logs/campaign --dir reports/campaign \
                         --clips bank/tiers/tier_mixed100.txt --features reports/features_amass.csv
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
from collections import Counter, defaultdict

import numpy as np

RUN = re.compile(r"^(?P<arm>uniform|adaptive|grounded)-(?P<bank>[^-]+)-s(?P<seed>\d+)\.log$")
EVAL = re.compile(
    r"^(?P<arm>uniform|adaptive|grounded)-(?P<bank>[^-]+)-s(?P<seed>\d+)_it(?P<it>\d+)\.csv$"
)
TOP1BIN = re.compile(r"sampling_top1_bin:\s*([0-9.]+)")
TOP1P = re.compile(r"sampling_top1_prob:\s*([0-9.]+)")


def series(log: str):
    b, p = [], []
    for line in open(log, errors="ignore"):
        m = TOP1BIN.search(line)
        if m:
            b.append(float(m.group(1)))
            continue
        m = TOP1P.search(line)
        if m:
            p.append(float(m.group(1)))
    n = min(len(b), len(p))
    return np.array(b[:n]), np.array(p[:n])


def eval_traj(dir_: str, arm: str, seed: int):
    """iter -> {clip: survival}"""
    out = {}
    for path in glob.glob(os.path.join(dir_, f"{arm}-*-s{seed}_it*.csv")):
        m = EVAL.match(os.path.basename(path))
        if not m or m["arm"] != arm or int(m["seed"]) != seed:
            continue
        out[int(m["it"])] = {r["clip"]: float(r["survival_rate"])
                             for r in csv.DictReader(open(path))}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--logs", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--clips", required=True)
    ap.add_argument("--features")
    ap.add_argument("--out")
    args = ap.parse_args()

    names = [ln.strip() for ln in open(args.clips) if ln.strip()]
    N = len(names)
    feats = ({r["name"]: r for r in csv.DictReader(open(args.features))}
             if args.features else {})
    out: dict = {"n_clips": N, "arms": {}}

    for arm in ("adaptive", "grounded"):
        logs = sorted(g for g in glob.glob(os.path.join(args.logs, f"{arm}-*-s*.log"))
                      if RUN.match(os.path.basename(g)))
        if not logs:
            continue
        print(f"\n=== {arm} ===")
        dominants, per_seed = [], {}
        for log in logs:
            seed = int(RUN.match(os.path.basename(log))["seed"])
            b, p = series(log)
            if not len(b):
                continue
            idx = np.rint(b * N).astype(int).clip(0, N - 1)
            # "Dominant" = the clip holding top-1 while the distribution is
            # actually concentrated; top-1 during a near-uniform phase is noise.
            conc = p > 0.2
            c = Counter(idx[conc].tolist())
            if not c:
                continue
            top, cnt = c.most_common(1)[0]
            share = cnt / max(int(conc.sum()), 1)
            dominants.append(top)
            per_seed[seed] = {"clip_idx": int(top), "clip": names[top],
                              "share_of_concentrated_iters": round(float(share), 3),
                              "n_distinct_dominants": len(c)}
            print(f"  seed {seed}: dominant clip #{top} "
                  f"({names[top][:44]}) for {share:.0%} of concentrated iterations; "
                  f"{len(c)} distinct clips ever dominant")

        if not dominants:
            continue
        same = len(set(dominants)) == 1
        print(f"  --> same dominant clip across {len(dominants)} seeds? "
              f"{'YES' if same else 'NO'}  ({sorted(set(dominants))})")

        # Was the dominant clip mastered while it was being hammered?
        rows = []
        for log in logs:
            seed = int(RUN.match(os.path.basename(log))["seed"])
            if seed not in per_seed:
                continue
            traj = eval_traj(args.dir, arm, seed)
            clip = per_seed[seed]["clip"]
            surv = {it: traj[it].get(clip) for it in sorted(traj) if clip in traj[it]}
            if surv:
                vals = [v for v in surv.values() if v is not None]
                per_seed[seed]["dominant_survival_by_iter"] = {
                    int(k): v for k, v in surv.items()}
                per_seed[seed]["dominant_survival_mean"] = round(float(np.mean(vals)), 3)
                per_seed[seed]["dominant_survival_final"] = float(vals[-1])
                rows.append((seed, clip, np.mean(vals), vals[-1]))
        if rows:
            print(f"  {'seed':>5s} {'mean surv':>10s} {'final surv':>11s}  dominant clip")
            for seed, clip, mean_s, fin in rows:
                print(f"  {seed:5d} {mean_s:10.3f} {fin:11.3f}  {clip[:46]}")
            mean_all = float(np.mean([r[2] for r in rows]))
            if mean_all < 0.2:
                reading = ("ATTRACTOR — the dominated clip is near-unlearnable, so failure "
                           "mass accumulates without bound. Fix class: per-clip mass cap.")
            elif mean_all > 0.6:
                reading = ("STALE ESTIMATOR — the dominated clip was largely mastered while "
                           "still absorbing the mass. Fix class: estimator liveness.")
            else:
                reading = ("MIXED — the dominated clip sits mid-difficulty; neither pure "
                           "attractor nor pure staleness.")
            print(f"  --> mean survival of dominated clip = {mean_all:.3f}: {reading}")
            out["arms"].setdefault(arm, {})["reading"] = reading
            out["arms"][arm]["dominant_survival_mean"] = round(mean_all, 3)

        if feats:
            for seed, info in per_seed.items():
                f = feats.get(info["clip"])
                if f:
                    info["atlas"] = {k: float(f[k]) for k in
                                     ("required_mu_p95", "vert_force_bw_max",
                                      "flight_phase_frac", "duration_s",
                                      "foot_clearance_p50") if k in f}
            shown = next((i for i in per_seed.values() if "atlas" in i), None)
            if shown:
                print(f"  atlas profile of a dominated clip: {shown['atlas']}")

        out["arms"].setdefault(arm, {})["same_clip_across_seeds"] = bool(same)
        out["arms"][arm]["per_seed"] = per_seed

    # --- band throughput -------------------------------------------------
    print("\n=== band throughput (clips crossing p=0.5 per 1k iterations) ===")
    for arm in ("uniform", "adaptive", "grounded"):
        seeds = sorted({int(EVAL.match(os.path.basename(p))["seed"])
                        for p in glob.glob(os.path.join(args.dir, f"{arm}-*_it*.csv"))
                        if EVAL.match(os.path.basename(p))})
        if not seeds:
            continue
        rates = []
        for s in seeds:
            traj = eval_traj(args.dir, arm, s)
            its = sorted(traj)
            if len(its) < 2:
                continue
            clips = sorted(traj[its[0]])
            up = down = 0
            for c in clips:
                v = [traj[i].get(c) for i in its]
                v = [x for x in v if x is not None]
                for a, b in zip(v, v[1:]):
                    if a < 0.5 <= b:
                        up += 1
                    elif b < 0.5 <= a:
                        down += 1
            span = (its[-1] - its[0]) / 1000.0
            rates.append((up / span, down / span, (up - down) / span))
        if rates:
            u, d, net = (float(np.mean([r[i] for r in rates])) for i in range(3))
            # Total crossings conflate progress with churn: a clip oscillating
            # across the threshold contributes as much as one that learns and
            # stays learned. Net upward is the quantity that means "clips are
            # being carried through the frontier".
            print(f"  {arm:>9s}: up {u:5.1f}  down {d:5.1f}  NET {net:+6.1f} "
                  f"per 1k iters (n={len(rates)} seeds)")
            out.setdefault("band_throughput", {})[arm] = {
                "up_per_1k": round(u, 2), "down_per_1k": round(d, 2),
                "net_per_1k": round(net, 2)}

    if args.out:
        json.dump(out, open(args.out, "w"), indent=2)
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
