#!/usr/bin/env python3
"""A1 — is the frontier band populated, and for how long?

A frontier / ZPD sampler assumes a standing population of clips near
p(success) ~ 0.5 to concentrate on. Experiment 1 showed per-clip survival is
close to bimodal: a clip is mostly mastered or mostly failed. But bimodality at
any single checkpoint is compatible with two very different worlds, and they
have opposite implications for whether frontier sampling can work at all:

  static     clips sit at 0 or 1 and rarely move. The band is empty because
             there is nothing in it -- a frontier sampler has no target and the
             premise fails outright.

  temporal   every clip passes through the band, but crosses it fast. The band
             is empty *at any instant* while still being where all the learning
             happens. A frontier sampler then has a target, but only a narrow
             window per clip, and a slow EMA will always be aiming at where the
             clip used to be.

Distinguishing them needs the per-clip trajectory across checkpoints, not the
marginal distribution at one. This computes, per arm:

  band mass   fraction of clips inside [lo, hi] at each checkpoint
  dwell       how many checkpoints a clip spends in the band over its lifetime
  flux        clips entering or leaving the band between adjacent checkpoints
  transit     net movement from below the band to above it

Usage:
    analyze_frontier_band.py --dir reports/campaign [--lo 0.3 --hi 0.7]
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


def load(d: str) -> dict:
    """(arm, seed) -> {iter: {clip: survival}}"""
    out: dict = defaultdict(dict)
    for path in sorted(glob.glob(os.path.join(d, "*.csv"))):
        m = NAME.match(os.path.basename(path))
        if not m:
            continue
        rows = list(csv.DictReader(open(path)))
        if not rows:
            continue
        out[(m["arm"], int(m["seed"]))][int(m["it"])] = {
            r["clip"]: float(r["survival_rate"]) for r in rows
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--lo", type=float, default=0.3)
    ap.add_argument("--hi", type=float, default=0.7)
    ap.add_argument("--out")
    args = ap.parse_args()

    runs = load(args.dir)
    if not runs:
        print(f"no campaign CSVs in {args.dir}")
        return 1
    arms = sorted({a for a, _ in runs})
    summary: dict = {"band": [args.lo, args.hi], "arms": {}}

    for arm in arms:
        cells = [(a, s) for (a, s) in runs if a == arm]
        iters = sorted(runs[cells[0]])
        print(f"\n=== {arm}  ({len(cells)} seeds, {len(iters)} checkpoints) ===")

        # --- band mass per checkpoint ------------------------------------
        print(f"{'iter':>6s} {'band mass':>10s} {'below':>7s} {'above':>7s}")
        mass_by_it = []
        for it in iters:
            inb, below, above = [], [], []
            for cell in cells:
                v = np.array(list(runs[cell][it].values()))
                inb.append(float(((v >= args.lo) & (v <= args.hi)).mean()))
                below.append(float((v < args.lo).mean()))
                above.append(float((v > args.hi).mean()))
            mass_by_it.append(float(np.mean(inb)))
            print(f"{it:6d} {np.mean(inb):10.3f} {np.mean(below):7.3f} {np.mean(above):7.3f}")

        # --- dwell and flux, per clip trajectory -------------------------
        dwell_all, flux_all, transit_all, never_all = [], [], [], []
        for cell in cells:
            clips = sorted(runs[cell][iters[0]])
            traj = np.array([[runs[cell][it][c] for it in iters] for c in clips])
            inband = (traj >= args.lo) & (traj <= args.hi)
            dwell_all.append(inband.sum(axis=1))                  # checkpoints in band
            never_all.append(float((inband.sum(axis=1) == 0).mean()))
            flux_all.append(float((inband[:, 1:] != inband[:, :-1]).sum(axis=1).mean()))
            transit_all.append(float(((traj[:, 0] < args.lo) & (traj[:, -1] > args.hi)).mean()))

        dwell = np.concatenate(dwell_all)
        print(f"\n  band mass: peak {max(mass_by_it):.3f} @ iter "
              f"{iters[int(np.argmax(mass_by_it))]}, final {mass_by_it[-1]:.3f}")
        print(f"  dwell (checkpoints in band, of {len(iters)}): "
              f"mean {dwell.mean():.2f}  median {np.median(dwell):.1f}  max {dwell.max()}")
        print(f"  clips never in band, any checkpoint: {np.mean(never_all):.1%}")
        print(f"  band crossings per clip: {np.mean(flux_all):.2f}")
        print(f"  clips transiting below -> above: {np.mean(transit_all):.1%}")

        summary["arms"][arm] = {
            "iters": iters,
            "band_mass": [round(m, 4) for m in mass_by_it],
            "dwell_mean": round(float(dwell.mean()), 3),
            "dwell_median": float(np.median(dwell)),
            "never_in_band_frac": round(float(np.mean(never_all)), 4),
            "crossings_per_clip": round(float(np.mean(flux_all)), 3),
            "transit_below_to_above_frac": round(float(np.mean(transit_all)), 4),
        }

    # --- verdict ---------------------------------------------------------
    print("\n" + "=" * 62)
    ref = summary["arms"].get("uniform") or next(iter(summary["arms"].values()))
    # Peak band mass is not the discriminator: it is dominated by the early
    # transient, when the whole bank is briefly mid-learning at once. What
    # separates a static from a temporal frontier is whether clips *move
    # through* the band -- transit fraction -- against how long they stay in it.
    steady = float(np.mean(ref["band_mass"][2:]))
    transit = ref["transit_below_to_above_frac"]
    never = ref["never_in_band_frac"]
    dwell_frac = ref["dwell_mean"] / len(ref["iters"])
    print(f"reference arm: steady-state band mass {steady:.3f} "
          f"(peak {max(ref['band_mass']):.3f} is the iter-500 transient), "
          f"transit {transit:.0%}, {never:.0%} never enter, "
          f"mean dwell {dwell_frac:.0%} of the run")
    if transit < 0.25 and never > 0.5:
        verdict = ("STATIC bimodality — most clips never occupy the band and few move "
                   "through it. A frontier sampler has no target; the ZPD premise fails "
                   "outright on this bank.")
    elif transit > 0.5 and dwell_frac < 0.30:
        verdict = ("TEMPORAL frontier — most clips DO cross the band, but each spends "
                   "only a small fraction of the run inside it, so the band is sparse at "
                   "any instant. Frontier sampling has a target that moves faster than a "
                   "slow failure EMA can track: the sampler aims at where clips used to "
                   "be. Predicts that estimator responsiveness, not the utility function, "
                   "is the binding constraint.")
    else:
        verdict = ("POPULATED band — a standing frontier exists and frontier sampling has "
                   "a well-defined, persistent target.")
    print(f"verdict: {verdict}")
    summary["verdict"] = verdict

    if args.out:
        json.dump(summary, open(args.out, "w"), indent=2)
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
