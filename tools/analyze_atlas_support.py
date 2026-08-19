#!/usr/bin/env python3
"""N2 -- relational atlas v2: intrinsic features + *support* features.

Support = how much of the policy's training bank lies near a clip in atlas
space, and how much training time its motion category received. Computed
relative to a given training bank (tier file), so the same clip has a
different support under a different bank -- which is what makes support a
transferable, testable object for E3.

Two tests on data already on disk (campaign at it3999, tier_mixed100):
  T1  atlas residuals (intrinsic-only fit) concentrate on low-support clips,
      with clip #44 the extreme point;
  T2  intrinsic+support lifts cross-policy transfer (A3 protocol) above the
      intrinsic-only 0.567 / 0.579, beyond what random extra features give.

Usage:
    analyze_atlas_support.py --features reports/features_amass.csv \
        --bank bank/tiers/tier_mixed100.txt --dir reports/campaign --out reports/N2_atlas_support.json
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_atlas_transfer import FEATURES, fit_predict, per_clip_difficulty, spearman  # noqa: E402

CLIP44 = "BMLmovi_Subject_64_F_MoSh_Subject_64_F_9_poses_120_jpos"


def category(r):
    """Coarse motion category from atlas features (rule-based, bank-independent).

    flight_phase_frac is not used: the bank's feet float ~3 cm above the plane
    (retarget/ground-alignment offset, see N1), which makes 'flight' fire on 80%
    of ordinary clips."""
    if float(r["nonfoot_ground_frac"]) > 0.10:
        return "ground"
    if float(r["com_speed_p95"]) > 1.2:
        return "dynamic"
    if float(r["com_speed_p95"]) < 0.35:
        return "quiet"
    return "locomotion"


def support_features(feats, bank_clips, query_clips=None, k=5, ref_clips=None, h=None):
    """Support of each query clip relative to the training bank.

    knn_dist: mean z-scored atlas distance to the k nearest bank clips (self excluded);
    support_density: duration-weighted Gaussian kernel mass of the bank around the clip;
    category_mass: duration share of the clip's motion category in the bank.

    z-scaling uses `ref_clips` (default: the bank itself) and the kernel bandwidth `h` (default:
    the bank's median NN spacing). To compare support ACROSS banks (E3: 100 -> 800), pass the same
    ref_clips and the same h for both calls so the density is a comparable duration fraction.
    """
    names = [c for c in bank_clips if c in feats]
    if query_clips is None:
        query_clips = names
    q = [c for c in query_clips if c in feats]
    X = np.array([[float(feats[c][f]) for f in FEATURES] for c in names])
    dur = np.array([float(feats[c]["duration_s"]) for c in names])
    ref = [c for c in (ref_clips or names) if c in feats]
    XR = np.array([[float(feats[c][f]) for f in FEATURES] for c in ref])
    mu, sd = XR.mean(0), XR.std(0)
    sd[sd < 1e-9] = 1.0
    Z = (X - mu) / sd
    Q = (np.array([[float(feats[c][f]) for f in FEATURES] for c in q]) - mu) / sd
    D = np.sqrt(((Q[:, None, :] - Z[None, :, :]) ** 2).sum(-1))       # (nq, nbank)
    for i, c in enumerate(q):                                          # exclude self
        if c in names:
            D[i, names.index(c)] = np.inf
    if h is None:
        Db = np.sqrt(((Z[:, None, :] - Z[None, :, :]) ** 2).sum(-1)); np.fill_diagonal(Db, np.inf)
        h = float(np.median(np.sort(Db, axis=1)[:, 0]))                # bandwidth from the bank's NN spacing
    knn = np.sort(D, axis=1)[:, :k].mean(1)
    Dk = D.copy(); Dk[~np.isfinite(Dk)] = 1e9
    dens = (np.exp(-Dk ** 2 / (2 * h * h)) * dur[None, :]).sum(1) / dur.sum()
    bank_cats = [category(feats[c]) for c in names]
    cat_dur = {}
    for c, d in zip(bank_cats, dur):
        cat_dur[c] = cat_dur.get(c, 0.0) + d
    cats = [category(feats[c]) for c in q]
    cat_mass = np.array([cat_dur.get(c, 0.0) / dur.sum() for c in cats])
    return {c: {"knn_dist": float(knn[i]), "support_density": float(dens[i]), "category": cats[i],
                "category_mass": float(cat_mass[i]), "duration_s": float(feats[c]["duration_s"])} for i, c in enumerate(q)}, h


def loo_predict(X, y, ridge=1.0):
    pred = np.zeros_like(y)
    for i in range(len(y)):
        m = np.ones(len(y), bool); m[i] = False
        pred[i] = fit_predict(X[m], y[m], X[i:i + 1], ridge)[0]
    return pred


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--features", default="/data/robotixx/climb/reports/features_amass.csv")
    ap.add_argument("--bank", default="/data/robotixx/climb/bank/tiers/tier_mixed100.txt")
    ap.add_argument("--dir", default="/data/robotixx/climb/reports/campaign")
    ap.add_argument("--extra-bank", default="/data/robotixx/climb/bank/tiers/tier_800.txt")
    ap.add_argument("--out", default="/data/robotixx/climb/reports/N2_atlas_support.json")
    ap.add_argument("--perm", type=int, default=200)
    args = ap.parse_args()

    feats = {r["name"]: r for r in csv.DictReader(open(args.features))}
    bank = [l.strip() for l in open(args.bank) if l.strip()]
    sup, h = support_features(feats, bank)
    print(f"support features over {len(sup)} bank clips (kernel h = {h:.3f} z-units)")
    cats = {}
    for c, s in sup.items():
        cats.setdefault(s["category"], []).append(s["duration_s"])
    print("category composition of the training bank (duration share):")
    tot = sum(sum(v) for v in cats.values())
    for k, v in sorted(cats.items(), key=lambda kv: -sum(kv[1])):
        print(f"   {k:11s} {len(v):3d} clips  {sum(v)/tot*100:5.1f}% of duration")

    # ---- T1: training-tier per-clip difficulty of the uniform-s1 policy (fixed frame-0 starts and random starts)
    print("\nT1 — where does the intrinsic atlas fail on the TRAINING tier?  (LOO ridge fit; support = kNN within the bank, self excluded)")
    out = {"bank": args.bank, "kernel_h": h,
           "category_composition": {k: {"clips": len(v), "duration_share": sum(v) / tot} for k, v in cats.items()},
           "T1": {}, "T2": {}, "support_of_clip44": sup.get(CLIP44)}
    for tag, path in (("fixed_start", "/data/robotixx/climb/reports/eval_tier_mixed100_fixed.csv"),
                      ("random_start", "/data/robotixx/climb/reports/eval_tier_mixed100_rand.csv")):
        if not os.path.exists(path):
            continue
        d = {r["clip"]: 1.0 - float(r["survival_rate"]) for r in csv.DictReader(open(path))}
        clips = sorted(set(sup) & set(d))
        Xi = np.array([[float(feats[c][f]) for f in FEATURES] for c in clips])
        S = np.array([[sup[c]["knn_dist"], np.log(sup[c]["support_density"] + 1e-6), sup[c]["category_mass"]] for c in clips])
        y = np.array([d[c] for c in clips]); i44 = clips.index(CLIP44) if CLIP44 in clips else None
        pred = loo_predict(Xi, y); res = np.abs(y - pred)
        pred_s = loo_predict(np.c_[Xi, S], y)
        r_knn = spearman(res, S[:, 0]); r_dens = spearman(res, S[:, 1]); r_cat = spearman(res, S[:, 2])
        rank_res = int((res > res[i44]).sum()) + 1 if i44 is not None else None
        rank_knn = int((S[:, 0] > S[i44, 0]).sum()) + 1 if i44 is not None else None
        rank_dens = int((S[:, 1] < S[i44, 1]).sum()) + 1 if i44 is not None else None
        top = np.argsort(-res)[:6]
        out["T1"][tag] = {"n": len(clips), "loo_spearman_intrinsic": spearman(pred, y), "loo_spearman_intrinsic+support": spearman(pred_s, y),
                          "rho_resid_knn": r_knn, "rho_resid_logdensity": r_dens, "rho_resid_catmass": r_cat,
                          "clip44_rank_residual": rank_res, "clip44_rank_knn": rank_knn, "clip44_rank_lowdensity": rank_dens,
                          "clip44_difficulty": (float(y[i44]) if i44 is not None else None),
                          "top_residual_clips": [(clips[i], round(float(res[i]), 3), round(float(S[i, 0]), 2), sup[clips[i]]["category"]) for i in top]}
        print(f"  [{tag}] n={len(clips)}  LOO rho intrinsic {spearman(pred, y):+.3f} -> +support {spearman(pred_s, y):+.3f} | rho(|resid|, knn) {r_knn:+.3f}  rho(|resid|, log dens) {r_dens:+.3f}  rho(|resid|, cat mass) {r_cat:+.3f}"
              f" | #44: difficulty {y[i44] if i44 is not None else None}, residual rank {rank_res}/{len(clips)}, knn rank {rank_knn}, low-density rank {rank_dens}")
        for i in top:
            print(f"      {clips[i][:44]:46s} y {y[i]:.2f} pred {pred[i]:.2f} |resid| {res[i]:.3f}  knn {S[i,0]:.2f}  dens {np.exp(S[i,1]):.3f}  {sup[clips[i]]['category']}")

    # ---- T2: HELD-OUT clips, per-arm difficulty (campaign it3999), support relative to the training bank
    diff = {}
    for arm in ("uniform", "adaptive", "grounded"):
        d, it = per_clip_difficulty(args.dir, arm)
        if d:
            diff[arm] = d
    hclips = sorted(set.intersection(*(set(d) for d in diff.values())) & set(feats))
    supH, _ = support_features(feats, bank, hclips)
    clips = [c for c in hclips if c in supH]
    Xi = np.array([[float(feats[c][f]) for f in FEATURES] for c in clips])
    S = np.array([[supH[c]["knn_dist"], np.log(supH[c]["support_density"] + 1e-6), supH[c]["category_mass"]] for c in clips])
    Xs = np.c_[Xi, S]
    print(f"\nT2 — cross-policy transfer on {len(clips)} HELD-OUT clips (fit on src arm, predict dst arm; A3 protocol) — support relative to the training bank")
    rng = np.random.default_rng(0)
    for src in diff:
        for dst in diff:
            if src == dst:
                continue
            ytr = np.array([diff[src][c] for c in clips]); yte = np.array([diff[dst][c] for c in clips])
            r_i = spearman(fit_predict(Xi, ytr, Xi), yte); r_s = spearman(fit_predict(Xs, ytr, Xs), yte)
            r_i_loo = spearman(loo_predict(Xi, ytr), yte); r_s_loo = spearman(loo_predict(Xs, ytr), yte)
            perm = np.array([spearman(fit_predict(np.c_[Xi, R], ytr, np.c_[Xi, R]), yte) for R in (rng.standard_normal(S.shape) for _ in range(args.perm))])
            p = float((perm >= r_s).mean())
            out["T2"][f"{src}->{dst}"] = {"intrinsic": r_i, "intrinsic+support": r_s, "intrinsic_loo": r_i_loo, "intrinsic+support_loo": r_s_loo,
                                          "perm_mean": float(perm.mean()), "perm_p95": float(np.percentile(perm, 95)), "p_perm": p}
            print(f"  {src:>9s} -> {dst:<9s}  intrinsic {r_i:+.3f} (LOO {r_i_loo:+.3f})   +support {r_s:+.3f} (LOO {r_s_loo:+.3f})   random-3 mean {perm.mean():+.3f} p95 {np.percentile(perm,95):+.3f}  p={p:.3f}")
    # support -> held-out difficulty directly (is low support itself predictive?)
    for arm in diff:
        y = np.array([diff[arm][c] for c in clips])
        print(f"  direct: rho(difficulty_{arm}, knn_dist) {spearman(y, S[:,0]):+.3f}  rho(difficulty, log density) {spearman(y, S[:,1]):+.3f}  rho(difficulty, cat mass) {spearman(y, S[:,2]):+.3f}")
        out["T2"][f"direct_{arm}"] = {"rho_knn": spearman(y, S[:, 0]), "rho_logdens": spearman(y, S[:, 1]), "rho_catmass": spearman(y, S[:, 2])}
    ph = "/data/robotixx/climb/reports/support_features_heldout100_wrt_mixed100.csv"
    with open(ph, "w") as fh:
        w = csv.writer(fh); w.writerow(["clip", "knn_dist", "support_density", "category", "category_mass", "duration_s"])
        for c in clips:
            s_ = supH[c]; w.writerow([c, f"{s_['knn_dist']:.4f}", f"{s_['support_density']:.5f}", s_["category"], f"{s_['category_mass']:.4f}", f"{s_['duration_s']:.2f}"])

    # ---- support features for another bank (E3 pre-registration input)
    if args.extra_bank and os.path.exists(args.extra_bank):
        eb = [l.strip() for l in open(args.extra_bank) if l.strip()]
        sup8, h8 = support_features(feats, eb)
        base = os.path.splitext(os.path.basename(args.extra_bank))[0]
        p8 = f"/data/robotixx/climb/reports/support_features_{base}.csv"
        with open(p8, "w") as fh:
            w = csv.writer(fh); w.writerow(["clip", "knn_dist", "support_density", "category", "category_mass", "duration_s"])
            for c, s in sup8.items():
                w.writerow([c, f"{s['knn_dist']:.4f}", f"{s['support_density']:.5f}", s["category"], f"{s['category_mass']:.4f}", f"{s['duration_s']:.2f}"])
        # change in support 100 -> 800 for the mixed100 clips that are also in the 800 bank
        common = [c for c in sup if c in sup8]
        dk = [(c, sup[c]["knn_dist"], sup8[c]["knn_dist"], sup[c]["support_density"], sup8[c]["support_density"]) for c in common]
        out["extra_bank"] = {"path": args.extra_bank, "n": len(sup8), "kernel_h": h8, "csv": p8, "n_common_with_bank": len(common),
                             "clip44_support_800": sup8.get(CLIP44)}
        print(f"\nsupport features for {base}: {len(sup8)} clips -> {p8}; {len(common)} of the {len(sup)} mixed100 clips are in it")
        if CLIP44 in sup8:
            print(f"  #44 support: mixed100 knn {sup[CLIP44]['knn_dist']:.2f} dens {sup[CLIP44]['support_density']:.4f} | 800 knn {sup8[CLIP44]['knn_dist']:.2f} dens {sup8[CLIP44]['support_density']:.4f} (category {sup8[CLIP44]['category']}, mass {sup8[CLIP44]['category_mass']:.3f})")
    p1 = "/data/robotixx/climb/reports/support_features_mixed100.csv"
    with open(p1, "w") as fh:
        w = csv.writer(fh); w.writerow(["clip", "knn_dist", "support_density", "category", "category_mass", "duration_s"])
        for c, s in sup.items():
            w.writerow([c, f"{s['knn_dist']:.4f}", f"{s['support_density']:.5f}", s["category"], f"{s['category_mass']:.4f}", f"{s['duration_s']:.2f}"])
    json.dump(out, open(args.out, "w"), indent=1)
    print(f"\nwrote {args.out}, {p1}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
