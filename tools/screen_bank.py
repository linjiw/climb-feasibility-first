#!/usr/bin/env python3
"""Screen a featurized bank for physical plausibility and emit sampling tiers.

The retargets contain clips that are geometrically valid -- correct body order,
correct frame rate, grounded -- and still physically untrackable: kinematic
retargeting without dynamics constraints produces motions demanding a friction
coefficient of 13, peak ground reaction of 43 bodyweights, or joint speeds past
what the G1's actuators can reach. Training on those teaches a policy to chase
references no controller can realise, and they contaminate a difficulty atlas by
occupying the "hard" tail for the wrong reason.

Measured on the 10,705-clip AMASS bank, the screens below reject 20.4%.

Emits a clip list, and optionally difficulty-stratified tiers for the bank-size
axis of the experiment matrix. Stratification is on a rank-averaged composite of
the dynamic-feasibility features rather than clip length or CoM speed, because
those rank motions differently -- see the atlas.

Usage:
    screen_bank.py --features features_amass.csv --out-dir tiers/
    screen_bank.py --features f.csv --tiers 50 200 800 --out-dir tiers/
"""

from __future__ import annotations

import argparse
import csv
import json
import os

import numpy as np

# (column, comparison, threshold, why)
SCREENS = [
    ("required_mu_p95", ">", 1.0, "demands more friction than rubber on dry floor"),
    ("vert_force_bw_max", ">", 5.0, "implausible peak ground reaction"),
    ("joint_vel_max", ">", 30.0, "beyond G1 actuator speed"),
    ("foot_clearance_p50", ">", 0.05, "hovers >5 cm on the median frame"),
    ("body_penetration_max", ">", 0.10, "sinks >10 cm into the floor"),
    ("duration_s", "<", 1.0, "too short to track"),
]

# Rank-averaged into the difficulty composite. Dynamic feasibility only: the
# atlas shows kinematic magnitude ranks motions differently, and CoM speed alone
# would sort sprints to the top while missing every multi-contact clip.
DIFFICULTY = [
    ("required_mu_p95", +1),
    ("vert_force_bw_max", +1),
    ("contact_switch_rate", +1),
    ("flight_phase_frac", +1),
    ("nonfoot_ground_frac", +1),
    ("angmom_peak", +1),
    ("support_margin_mean", -1),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--features", required=True, help="CSV from featurize_motions.py")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--tiers", type=int, nargs="*", default=[50, 200, 800])
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.features)))
    if not rows:
        print("empty feature file")
        return 1
    n = len(rows)

    def col(k):
        return np.array([float(r[k]) for r in rows])

    bad = np.zeros(n, bool)
    print(f"bank: {n} clips\n{'screen':58s} {'rejected':>9s}")
    report = []
    for key, op, thr, why in SCREENS:
        if key not in rows[0]:
            print(f"  (skipping {key}: not in feature file)")
            continue
        m = col(key) > thr if op == ">" else col(key) < thr
        bad |= m
        print(f"{key + ' ' + op + ' ' + str(thr):58s} {m.sum():6d} {100*m.mean():5.1f}%")
        report.append({"screen": f"{key} {op} {thr}", "why": why,
                       "rejected": int(m.sum()), "pct": round(100 * float(m.mean()), 2)})
    keep = ~bad
    print(f"\n{'clean':58s} {keep.sum():6d} {100*keep.mean():5.1f}%")

    # Rank-average composite over the clean subset only, so rejected outliers do
    # not compress the scale everything else is ranked on.
    idx = np.flatnonzero(keep)
    score = np.zeros(len(idx))
    used = []
    for key, sign in DIFFICULTY:
        if key not in rows[0]:
            continue
        v = col(key)[idx]
        r = np.argsort(np.argsort(sign * v)).astype(float) / max(len(idx) - 1, 1)
        score += r
        used.append(key)
    score /= max(len(used), 1)
    print(f"difficulty composite over {len(used)} features: "
          f"p10={np.percentile(score,10):.3f} p50={np.percentile(score,50):.3f} "
          f"p90={np.percentile(score,90):.3f}")

    os.makedirs(args.out_dir, exist_ok=True)
    order = idx[np.argsort(score)]
    with open(os.path.join(args.out_dir, "clean.txt"), "w") as fh:
        for i in order:
            fh.write(rows[i]["name"] + "\n")
    with open(os.path.join(args.out_dir, "screen_report.json"), "w") as fh:
        json.dump({"n_total": n, "n_clean": int(keep.sum()), "screens": report,
                   "difficulty_features": used}, fh, indent=2)

    # Difficulty-stratified tiers: sample evenly across the composite's range so
    # a small bank still spans easy-to-hard rather than clustering in the middle.
    rng = np.random.default_rng(args.seed)
    srt = score[np.argsort(score)]
    for t in args.tiers:
        if t > len(order):
            print(f"tier {t}: only {len(order)} clean clips available, skipping")
            continue
        edges = np.linspace(0, len(order), t + 1).astype(int)
        pick = [order[rng.integers(a, b)] for a, b in zip(edges[:-1], edges[1:]) if b > a]
        path = os.path.join(args.out_dir, f"tier_{t}.txt")
        with open(path, "w") as fh:
            for i in pick:
                fh.write(rows[i]["name"] + "\n")
        hrs = sum(float(rows[i]["duration_s"]) for i in pick) / 3600
        print(f"tier {t:5d}: {len(pick):5d} clips, {hrs:6.2f} h -> {path}")

    print(f"\nclean list: {os.path.join(args.out_dir, 'clean.txt')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
