#!/usr/bin/env python3
"""E-HYG frozen analysis — implements EXACTLY plan/PREREGISTRATION_E_HYG.md. Frozen before any
outcome exists; sha recorded in plan/E_HYG_FREEZE.sha256. `--synthetic` dry-runs the decision
logic on fabricated stratified CSVs (no real data).

Inputs: stratified CSVs (tools/eval_stratified.py) for comparator and pruned arm on heldout100,
zs_ground, zs_dynamic. Flags from the pinned screen CSV.
"""
from __future__ import annotations

import argparse
import csv
import io
import json

import numpy as np

FEAS = "/data/robotixx/climb/reports/feasibility_e3/feasibility.csv"
FEAS_ALL = "/data/robotixx/climb/reports/feasibility_all/feasibility.csv"


def read_strat(path_or_text):
    fh = io.StringIO(path_or_text) if "\n" in str(path_or_text) else open(path_or_text)
    out = {}
    for r in csv.DictReader(fh):
        if r["offset_s"] == "mean":
            continue
        out.setdefault(r["clip"], []).append(float(r["survival"]))
    return {c: float(np.mean(v)) for c, v in out.items()}


def flags():
    f = {}
    for p in (FEAS, FEAS_ALL):
        for r in csv.DictReader(open(p)):
            f.setdefault(r["clip"], float(r["infeasible_frac"]))
    return f


def perm_p(deltas, nperm=5000, rng=None):
    """One-sided sign-flip permutation on per-clip deltas (mean > 0)."""
    rng = rng or np.random.default_rng(0)
    d = np.asarray(deltas)
    obs = d.mean()
    null = [(d * rng.choice([-1, 1], d.size)).mean() for _ in range(nperm)]
    return float(np.mean(np.array(null) >= obs))


def verdict(held_c, held_p, zsg_c, zsg_p, zsd_c, zsd_p, fl=None):
    fl = fl or flags()
    clips = sorted(set(held_c) & set(held_p))
    feas = [c for c in clips if fl.get(c, 1.0) <= 0.10]
    infeas = [c for c in clips if fl.get(c, 1.0) > 0.10]
    d_feas = [held_p[c] - held_c[c] for c in feas]
    out = {"seal": "PREREGISTRATION_E_HYG.md", "n_heldout": len(clips), "n_feasible": len(feas)}
    out["P1"] = {"delta_feasible_mean": float(np.mean(d_feas)), "perm_p_onesided": perm_p(d_feas),
                 "pass": bool(np.mean(d_feas) >= 0.015)}
    # P2: concentration — comparator's worst decile of feasible vs best half; easy stratum
    order = sorted(feas, key=lambda c: held_c[c])
    k10 = max(1, len(order) // 10)
    worst = order[:k10]
    besthalf = order[len(order) // 2:]
    dw = float(np.mean([held_p[c] - held_c[c] for c in worst]))
    db = float(np.mean([held_p[c] - held_c[c] for c in besthalf]))
    easy = [c for c in clips if held_c[c] >= 0.95]
    de = float(np.mean([held_p[c] - held_c[c] for c in easy])) if easy else 0.0
    out["P2"] = {"delta_worst_decile": dw, "delta_best_half": db, "delta_easy": de,
                 "pass": bool(dw >= 2 * db and abs(de) <= 0.02)}
    # P3: ZS-ground bracket; ZS-dynamic descriptive
    zg = sorted(set(zsg_c) & set(zsg_p))
    dzg = float(np.mean([zsg_p[c] - zsg_c[c] for c in zg]))
    zd = sorted(set(zsd_c) & set(zsd_p))
    dzd = float(np.mean([zsd_p[c] - zsd_c[c] for c in zd])) if zd else float("nan")
    out["P3"] = {"delta_zs_ground": dzg, "in_bracket": bool(-0.05 <= dzg <= 0.02),
                 "delta_zs_dynamic_descriptive": dzd}
    out["P4"] = {"delta_infeasible_stratum": (float(np.mean([held_p[c] - held_c[c] for c in infeas])) if infeas else float("nan"))}
    out["DECISION"] = {"hygiene_confirmed": bool(out["P1"]["pass"] and out["P2"]["pass"]),
                       "rule": "P1 AND P2; P3 bracket reported either way"}
    return out


def synthetic():
    fl = {}
    def mk(vals):  # dict clip->survival
        return dict(vals)
    rng = np.random.default_rng(2)
    feas_clips = [f"F{i}" for i in range(70)]
    inf_clips = [f"I{i}" for i in range(30)]
    for c in feas_clips: fl[c] = 0.05
    for c in inf_clips: fl[c] = 0.5
    zsg = [f"G{i}" for i in range(60)]; zsd = [f"D{i}" for i in range(60)]
    for c in zsg + zsd: fl[c] = 0.05
    base_h = {c: float(np.clip(rng.uniform(0.2, 1.0), 0, 1)) for c in feas_clips}
    base_h.update({c: 0.5 for c in inf_clips})
    zg_c = {c: 0.5 for c in zsg}; zd_c = {c: 0.6 for c in zsd}
    def arm(gain_worst, gain_best, easy_shift=0.0, zg_shift=0.0):
        order = sorted(feas_clips, key=lambda c: base_h[c])
        p = dict(base_h)
        for c in order[:7]: p[c] = min(1, p[c] + gain_worst)
        for c in order[35:]: p[c] = min(1, p[c] + gain_best)
        for c in feas_clips:
            if base_h[c] >= 0.95: p[c] = min(1, base_h[c] + easy_shift)
        return p, {c: zg_c[c] + zg_shift for c in zsg}, dict(zd_c)
    cases = {
        "CONFIRM":   (arm(0.20, 0.02), True),
        "VOLUME":    (arm(0.05, 0.05), False),   # uniform gain -> P2 fails (no concentration)
        "NULL":      (arm(0.005, 0.0), False),   # P1 fails
        "ZS_BREACH": (arm(0.20, 0.02, zg_shift=0.10), True),  # decision still P1&P2; P3 reported out-of-bracket
    }
    for name, ((p, zg_p, zd_p), expect) in cases.items():
        v = verdict(base_h, p, zg_c, zg_p, zd_c, zd_p, fl)
        got = v["DECISION"]["hygiene_confirmed"]
        assert got == expect, (name, v)
        extra = "" if name != "ZS_BREACH" else f" (P3 in_bracket={v['P3']['in_bracket']} as designed: reported, not adjudicated)"
        print(f"  synthetic {name}: P1={v['P1']['pass']} P2={v['P2']['pass']} -> confirmed={got} OK{extra}")
    print("E-HYG synthetic dry-run: all 4 branches decide as sealed. No real data touched.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--held-c"); ap.add_argument("--held-p")
    ap.add_argument("--zsg-c"); ap.add_argument("--zsg-p")
    ap.add_argument("--zsd-c"); ap.add_argument("--zsd-p")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.synthetic:
        return synthetic()
    v = verdict(read_strat(a.held_c), read_strat(a.held_p), read_strat(a.zsg_c), read_strat(a.zsg_p),
                read_strat(a.zsd_c), read_strat(a.zsd_p))
    print(json.dumps(v, indent=1))
    if a.out:
        json.dump(v, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
