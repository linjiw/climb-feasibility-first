#!/usr/bin/env python3
"""Full-bank feasibility prevalence by category (advisor step 2c). Run after reports/feasibility_all/feasibility.csv exists."""
import csv, sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_atlas_support import category
R = '/data/robotixx/climb/'
feats = {r['name']: r for r in csv.DictReader(open(R+'reports/features_amass.csv'))}
path = sys.argv[1] if len(sys.argv) > 1 else R+'reports/feasibility_all/feasibility.csv'
feas = list(csv.DictReader(open(path)))
rows = [(r['clip'], category(feats[r['clip']]), float(r['infeasible_frac']), float(r['airborne_frac']), float(r['unsupported_impulse_per_weight_s']), float(feats[r['clip']]['duration_s'])) for r in feas if r['clip'] in feats]
print(f"clips screened: {len(rows)}")
cats = sorted(set(c for _, c, *_ in rows))
print(f"{'category':12s} {'n':>6s} {'>10% infeasible':>16s} {'>25%':>7s} {'median infeas':>13s} {'median airborne':>15s} {'dur share flagged':>18s}")
tot_dur = sum(d for *_, d in rows)
for c in cats + ['ALL']:
    sel = [r for r in rows if c == 'ALL' or r[1] == c]
    inf = np.array([r[2] for r in sel]); air = np.array([r[3] for r in sel]); dur = np.array([r[5] for r in sel])
    print(f"{c:12s} {len(sel):6d} {(inf>0.10).mean()*100:15.1f}% {(inf>0.25).mean()*100:6.1f}% {np.median(inf)*100:12.1f}% {np.median(air)*100:14.1f}% {dur[inf>0.10].sum()/dur.sum()*100:17.1f}%")
# family view: dataset prefix
pref = {}
for name, c, inf, air, imp, d in rows:
    p = name.split('_')[0]; pref.setdefault(p, []).append(inf)
print("\nby source dataset (>10% infeasible share):")
for p, v in sorted(pref.items(), key=lambda kv: -len(kv[1]))[:12]:
    print(f"  {p:14s} n={len(v):5d}  {np.mean(np.array(v)>0.10)*100:5.1f}%")
