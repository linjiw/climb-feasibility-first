#!/usr/bin/env python3
"""Atlas v2.1: intrinsic + feasibility features (pre-registered F1-F3 in plan/PREREGISTRATION_ATLAS_v21.md).
Also the free re-analysis of the campaign endpoints on feasible-only clips (advisor step 2b)."""
import csv, json, os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_atlas_transfer import FEATURES, fit_predict, per_clip_difficulty, spearman
from analyze_atlas_support import support_features, loo_predict, CLIP44
R = '/data/robotixx/climb/'
feats = {r['name']: r for r in csv.DictReader(open(R+'reports/features_amass.csv'))}
feas = {r['clip']: r for r in csv.DictReader(open(R+'reports/feasibility_e3/feasibility.csv'))}
FEAS = ['infeasible_frac', 'airborne_frac', 'unsupported_impulse_per_weight_s']
def X_of(clips, extra=None):
    cols = [[float(feats[c][f]) for f in FEATURES] + ([float(feas[c][f]) for f in FEAS] if extra else []) for c in clips]
    return np.array(cols)
out = {}
bank = [l.strip() for l in open(R+'bank/tiers/tier_mixed100.txt') if l.strip()]
sup, h = support_features(feats, bank)
rng = np.random.default_rng(0)
print("F1 — training tier, LOO ridge, uniform-s1 labels")
out['F1'] = {}
for tag, path in (("fixed_start", R+"reports/eval_tier_mixed100_fixed.csv"), ("random_start", R+"reports/eval_tier_mixed100_rand.csv")):
    d = {r['clip']: 1.0 - float(r['survival_rate']) for r in csv.DictReader(open(path))}
    clips = sorted(set(d) & set(feas) & set(feats)); y = np.array([d[c] for c in clips]); i44 = clips.index(CLIP44)
    Xi = X_of(clips); Xf = X_of(clips, extra=True)
    S = np.array([sup[c]['knn_dist'] for c in clips]); IF = np.array([float(feas[c]['infeasible_frac']) for c in clips])
    pi = loo_predict(Xi, y); pf = loo_predict(Xf, y)
    ri, rf = spearman(pi, y), spearman(pf, y)
    perm = np.array([spearman(loo_predict(np.c_[Xi, rng.standard_normal((len(clips), 3))], y), y) for _ in range(100)])
    res_i = np.abs(y - pi); res_f = np.abs(y - pf)
    rank_i = int((res_i > res_i[i44]).sum()) + 1; rank_f = int((res_f > res_f[i44]).sum()) + 1
    out['F1'][tag] = {'n': len(clips), 'loo_intrinsic': ri, 'loo_intrinsic+feas': rf, 'perm_random3_p95': float(np.percentile(perm, 95)), 'perm_mean': float(perm.mean()),
                      'clip44_resid_rank_intrinsic': rank_i, 'clip44_resid_rank_feas': rank_f,
                      'F3_rho_resid_infeasible_intrinsic': spearman(res_i, IF), 'F3_rho_resid_infeasible_feas': spearman(res_f, IF),
                      'F3_rho_resid_knn_intrinsic': spearman(res_i, S), 'F3_rho_resid_knn_feas': spearman(res_f, S),
                      'rho_y_infeasible': spearman(y, IF), 'rho_y_airborne': spearman(y, np.array([float(feas[c]['airborne_frac']) for c in clips]))}
    print(f"  [{tag}] LOO rho intrinsic {ri:+.3f} -> +feasibility {rf:+.3f} (random-3 mean {perm.mean():+.3f}, p95 {np.percentile(perm,95):+.3f}) | #44 resid rank {rank_i} -> {rank_f} | rho(|res|,infeas) {spearman(res_i, IF):+.3f} -> {spearman(res_f, IF):+.3f} | rho(|res|,knn) {spearman(res_i, S):+.3f} -> {spearman(res_f, S):+.3f} | rho(y,infeas) {spearman(y, IF):+.3f}")
print("\nF2 — held-out transfer (A3 protocol) with feasibility features")
diff = {a: per_clip_difficulty(R+'reports/campaign', a)[0] for a in ('uniform','adaptive','grounded')}
hclips = sorted(set.intersection(*(set(v) for v in diff.values())) & set(feats) & set(feas))
Xi = X_of(hclips); Xf = X_of(hclips, extra=True)
out['F2'] = {}
for src in diff:
    for dst in diff:
        if src == dst: continue
        ytr = np.array([diff[src][c] for c in hclips]); yte = np.array([diff[dst][c] for c in hclips])
        r_i = spearman(fit_predict(Xi, ytr, Xi), yte); r_f = spearman(fit_predict(Xf, ytr, Xf), yte)
        perm = np.array([spearman(fit_predict(np.c_[Xi, Rr], ytr, np.c_[Xi, Rr]), yte) for Rr in (rng.standard_normal((len(hclips), 3)) for _ in range(200))])
        p = float((perm >= r_f).mean())
        out['F2'][f'{src}->{dst}'] = {'intrinsic': r_i, 'intrinsic+feas': r_f, 'perm_mean': float(perm.mean()), 'perm_p95': float(np.percentile(perm,95)), 'p_perm': p}
        print(f"  {src:>9s} -> {dst:<9s} intrinsic {r_i:+.3f}  +feasibility {r_f:+.3f}  random-3 mean {perm.mean():+.3f} p95 {np.percentile(perm,95):+.3f}  p={p:.3f}")
IFh = np.array([float(feas[c]['infeasible_frac']) for c in hclips])
for a in diff:
    y = np.array([diff[a][c] for c in hclips]); print(f"  direct rho(difficulty_{a}, infeasible_frac) {spearman(y, IFh):+.3f}, airborne {spearman(y, np.array([float(feas[c]['airborne_frac']) for c in hclips])):+.3f}")
    out['F2'][f'direct_{a}'] = {'rho_infeasible': spearman(y, IFh)}
# ---- 2b: campaign endpoints feasible-only vs all
print("\n2b — campaign endpoints (held-out survival, it3999, seed mean) all vs feasible-only (infeasible_frac <= 0.10)")
feasible = [c for c in hclips if float(feas[c]['infeasible_frac']) <= 0.10]
out['endpoints_2b'] = {'n_all': len(hclips), 'n_feasible': len(feasible), 'arms': {}}
for a in diff:
    all_s = 1 - np.mean([diff[a][c] for c in hclips]); fe_s = 1 - np.mean([diff[a][c] for c in feasible]); inf_s = 1 - np.mean([diff[a][c] for c in hclips if c not in feasible]) if len(feasible) < len(hclips) else float('nan')
    out['endpoints_2b']['arms'][a] = {'all': all_s, 'feasible': fe_s, 'infeasible': inf_s}
    print(f"  {a:9s} all {all_s:.3f}   feasible-only {fe_s:.3f} (n={len(feasible)})   infeasible-only {inf_s:.3f} (n={len(hclips)-len(feasible)})")
json.dump(out, open(R+'reports/N_atlas_v21.json','w'), indent=1); print("wrote reports/N_atlas_v21.json")
