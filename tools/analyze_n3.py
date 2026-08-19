#!/usr/bin/env python3
"""N3 frozen analysis — implements EXACTLY the sealed criteria of
plan/PREREGISTRATION_N3_coverage.md (af1b7c9f) + the D1 strata (a93a87a0).

FROZEN before any N3 outcome exists (v6 rule). This file's sha256 is recorded in
plan/N3_PREFLIGHT.md at freeze time; it must not change after the N3 chain starts.
Synthetic dry-run: `analyze_n3.py --synthetic` fabricates outcome files for all four
decision-tree branches and asserts the verdict logic (no real data touched).

Inputs (produced by tools/eval_stratified.py and tools/climb_eval.py):
  --strat <arm>=<csv>      stratified-start CSV per arm; arms: base_s1 base_s2 base_s3
                           aug_s1 aug_s2 (keystone) aug_adapt rand_s1
  --heldout <arm>=<csv>    heldout100 eval CSV per arm (regression check)
  --telemetry <csv>        adaptive-on-augmented sampler telemetry: iter,top1_prob[,top1_clip]
Clip roles are fixed by the seal: #44 = BMLmovi_..._64_F_9; easy = CMU_76_02, BMLhandball_S07;
ground16 members = bank/tiers/aug_ground16.txt.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys

import numpy as np

C44 = "BMLmovi_Subject_64_F_MoSh_Subject_64_F_9_poses_120_jpos"
EASY = ["CMU_76_76_02_poses_120_jpos", "BMLhandball_S07_Expert_Trial_upper_left_right_037_poses_120_jpos"]
KNEEL_OFFSETS = {2.0, 3.0, 4.0, 6.0}      # sealed: feasible kneel/crawl phase
DESCENT_OFFSETS = {0.0, 1.0}              # sealed: reported separately, predicted <= 0.25
G16 = "/data/robotixx/climb/bank/tiers/aug_ground16.txt"
FEAS = "/data/robotixx/climb/reports/feasibility_e3/feasibility.csv"


def read_strat(path_or_text):
    fh = io.StringIO(path_or_text) if "\n" in str(path_or_text) else open(path_or_text)
    rows = [r for r in csv.DictReader(fh) if r["offset_s"] != "mean"]
    out = {}
    for r in rows:
        out.setdefault(r["clip"], {})[float(r["offset_s"])] = float(r["survival"])
    return out


def phase_mean(strat, clip, offsets):
    d = strat.get(clip, {})
    vals = [d[o] for o in sorted(offsets) if o in d]
    return float(np.mean(vals)) if vals else float("nan"), len(vals)


def verdict(strats, heldout=None, telemetry=None, feas_csv=FEAS):
    """strats: dict arm -> {clip -> {offset -> survival}}. Returns the sealed verdict structure."""
    out = {"seal": "af1b7c9f", "E1": {}, "E2": {}, "E3": {}, "E4": {}, "E5": {}, "descent": {}}
    # E1 keystone: both augmented-uniform seeds >= 0.25 on the kneel/crawl phase
    for arm in ("aug_s1", "aug_s2"):
        m, n = phase_mean(strats[arm], C44, KNEEL_OFFSETS)
        out["E1"][arm] = {"kneel_phase_survival": m, "n_offsets": n, "pass": bool(m >= 0.25)}
    for arm in [a for a in strats if a.startswith("base")]:
        m, _ = phase_mean(strats[arm], C44, KNEEL_OFFSETS)
        out["E1"][f"baseline_{arm}"] = {"kneel_phase_survival": m}
    out["E1"]["pass"] = bool(all(out["E1"][a]["pass"] for a in ("aug_s1", "aug_s2")))
    # descent, reported separately (prediction: stays <= 0.25; not a pass/fail gate)
    for arm in ("aug_s1", "aug_s2"):
        m, _ = phase_mean(strats[arm], C44, DESCENT_OFFSETS)
        out["descent"][arm] = {"survival": m, "prediction_upheld": bool(m <= 0.25)}
    # E4 specificity: random16 arm < 0.10 on the kneel/crawl phase
    m, n = phase_mean(strats["rand_s1"], C44, KNEEL_OFFSETS)
    out["E4"] = {"kneel_phase_survival": m, "pass": bool(m < 0.10)}
    # E2 no-regression: easy clips >= 0.95 offset-mean in every N3 arm; heldout within +-0.03
    e2 = {}
    for arm, st in strats.items():
        if arm.startswith("base"):
            continue
        for c in EASY:
            offs = st.get(c, {})
            m = float(np.mean(list(offs.values()))) if offs else float("nan")
            e2[f"{arm}:{c[:20]}"] = {"mean": m, "pass": bool(m >= 0.95)}
    out["E2"]["easy"] = e2
    if heldout:
        feas = {r["clip"]: float(r["infeasible_frac"]) for r in csv.DictReader(open(feas_csv))}
        base_arms = [a for a in heldout if a.startswith("base")]
        base_all = float(np.mean([np.mean([float(r["survival_rate"]) for r in csv.DictReader(open(heldout[a]))]) for a in base_arms]))
        for arm, path in heldout.items():
            if arm.startswith("base"):
                continue
            rows = list(csv.DictReader(open(path)))
            allm = float(np.mean([float(r["survival_rate"]) for r in rows]))
            fe = [float(r["survival_rate"]) for r in rows if feas.get(r["clip"], 1.0) <= 0.10]
            out["E2"][arm] = {"heldout_all": allm, "delta_vs_base": allm - base_all,
                              "pass": bool(abs(allm - base_all) <= 0.03),
                              "heldout_feasible_only": (float(np.mean(fe)) if fe else float("nan"))}
    # E3 interaction: adaptive-on-augmented top-1 mass < 0.5 at iter >= 2000
    if telemetry:
        rows = list(csv.DictReader(open(telemetry) if os.path.exists(str(telemetry)) else io.StringIO(telemetry)))
        late = [float(r["top1_prob"]) for r in rows if float(r["iter"]) >= 2000]
        out["E3"] = {"max_top1_after_2000": (max(late) if late else float("nan")),
                     "pass": bool(late and max(late) < 0.5),
                     "comparator": "adaptive-mixed100 s1-s3 max_top1 0.870-0.893 (reports/A5_coverage_dose.json)"}
    # E5 (reported, not gated): ground16 members' own ground-segment survival, aug vs base
    g16 = [l.strip() for l in open(G16) if l.strip()]
    probes = [c for c in g16 if any(c in st for st in strats.values())]
    e5 = {}
    for c in probes:
        b, _ = phase_mean(strats.get("base_s1", {}), c, KNEEL_OFFSETS)
        a1, _ = phase_mean(strats.get("aug_s1", {}), c, KNEEL_OFFSETS)
        e5[c[:40]] = {"base_s1": b, "aug_s1": a1}
    out["E5"] = e5
    # sealed decision rule
    out["DECISION"] = {"coverage_causal": bool(out["E1"]["pass"] and out["E4"]["pass"]),
                       "rule": "E1 (both keystone seeds >= 0.25) AND E4 (random16 < 0.10); E2/E3/E5 reported alongside"}
    return out


# --------------------------------------------------------------------------- #
def synthetic():
    """Dry-run the decision logic on fabricated outcomes for all four branches."""
    def strat_csv(v44_kneel, v44_desc, easy=1.0, g16v=0.6):
        g16 = [l.strip() for l in open(G16) if l.strip()][:3]
        lines = ["clip,offset_s,survival,mean_survival_s,n,window_s"]
        for o in (0.0, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0):
            v = v44_kneel if o in KNEEL_OFFSETS else (v44_desc if o in DESCENT_OFFSETS else 1.0)
            lines.append(f"{C44},{o},{v},2.0,8,3.0")
            for c in EASY:
                lines.append(f"{c},{o},{easy},3.0,8,3.0")
            for c in g16:
                lines.append(f"{c},{o},{g16v},2.0,8,3.0")
        return "\n".join(lines) + "\n"
    cases = {
        "A_confirm":   dict(aug1=0.40, aug2=0.35, rand=0.05, expect=True),
        "B_dose_null": dict(aug1=0.10, aug2=0.05, rand=0.05, expect=False),
        "C_one_seed":  dict(aug1=0.40, aug2=0.15, rand=0.05, expect=False),
        "D_nonspecific": dict(aug1=0.40, aug2=0.35, rand=0.30, expect=False),
    }
    for name, c in cases.items():
        strats = {"base_s1": read_strat(strat_csv(0.0, 0.1)),
                  "aug_s1": read_strat(strat_csv(c["aug1"], 0.15)),
                  "aug_s2": read_strat(strat_csv(c["aug2"], 0.15)),
                  "rand_s1": read_strat(strat_csv(c["rand"], 0.05))}
        v = verdict(strats)
        got = v["DECISION"]["coverage_causal"]
        assert got == c["expect"], (name, got, v)
        print(f"  synthetic {name}: E1 {v['E1']['pass']} E4 {v['E4']['pass']} -> causal={got}  (expected {c['expect']}) OK")
    print("synthetic dry-run: all 4 branches decide as sealed. No real data touched.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--strat", nargs="*", default=[], help="arm=path pairs")
    ap.add_argument("--heldout", nargs="*", default=[])
    ap.add_argument("--telemetry", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.synthetic:
        return synthetic()
    strats = {k: read_strat(v) for k, v in (x.split("=", 1) for x in a.strat)}
    heldout = {k: v for k, v in (x.split("=", 1) for x in a.heldout)} or None
    v = verdict(strats, heldout, a.telemetry)
    print(json.dumps(v, indent=1))
    if a.out:
        json.dump(v, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
