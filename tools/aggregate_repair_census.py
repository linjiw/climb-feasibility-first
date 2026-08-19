#!/usr/bin/env python3
"""Aggregate the repair census into the advisor's 2x2 main table:
rows = contamination severity (flagged >10% vs >25%), cols = auto-recoverable (root projection,
success budget) vs needs higher-order repair / refusal. Plus per-category and per-source splits."""
import csv, glob, json, os, sys
sys.path.insert(0, '/data/robotixx/climb/tools')
import numpy as np
from analyze_atlas_support import category
R = '/data/robotixx/climb/'
feats = {r['name']: r for r in csv.DictReader(open(R+'reports/features_amass.csv'))}
rows = []
for p in glob.glob(R+'reports/repair_census/json/*.json'):
    try: rows.append(json.load(open(p)))
    except Exception: pass
print(f"census records: {len(rows)}")
for r in rows:
    r['cat'] = category(feats[r['clip']]) if r['clip'] in feats else '?'
    r['src'] = r['clip'].split('_')[0]
    r['sev'] = '>25%' if r['infeasible_frac_before'] > 0.25 else '>10%'
def tab(sel, name):
    n = len(sel); ok = sum(r['success'] for r in sel)
    res_after = np.mean([r['infeasible_frac_after'] for r in sel]) if sel else float('nan')
    off = np.mean([r['offset_max_m'] for r in sel]) if sel else float('nan')
    return {'n': n, 'auto_recoverable': ok, 'pct': round(ok/n*100,1) if n else None,
            'mean_infeas_after': round(float(res_after),3), 'mean_offset_max_m': round(float(off),3)}
out = {'total': tab(rows, 'all'),
       'matrix': {sev: tab([r for r in rows if r['sev']==sev], sev) for sev in ('>10%','>25%')},
       'by_category': {c: tab([r for r in rows if r['cat']==c], c) for c in sorted({r['cat'] for r in rows})},
       'by_source': {s: tab([r for r in rows if r['src']==s], s) for s in sorted({r['src'] for r in rows})
                     if sum(r['src']==s for r in rows) >= 30}}
json.dump(out, open(R+'reports/repair_census/summary.json','w'), indent=1)
md = ["# Repair census — 2×2 main table (auto-generated)\n",
      "| severity stratum | n | auto-recoverable (root projection, ≤15 cm, ≤5 % residual) | needs higher-order repair or refusal |",
      "|---|---:|---:|---:|"]
for sev in ('>10%','>25%'):
    t = out['matrix'][sev]
    md.append(f"| flagged {sev} of frames | {t['n']} | **{t['auto_recoverable']} ({t['pct']} %)** | {t['n']-t['auto_recoverable']} ({round(100-t['pct'],1)} %) |")
t = out['total']
md.append(f"| **all flagged** | **{t['n']}** | **{t['auto_recoverable']} ({t['pct']} %)** | {t['n']-t['auto_recoverable']} |")
md.append("\n## By category\n\n| category | n | auto-recoverable |")
md.append("|---|---:|---:|")
for c, t in out['by_category'].items():
    md.append(f"| {c} | {t['n']} | {t['auto_recoverable']} ({t['pct']} %) |")
md.append("\n## By source (n ≥ 30)\n\n| source | n | auto-recoverable |")
md.append("|---|---:|---:|")
for s, t in out['by_source'].items():
    md.append(f"| {s} | {t['n']} | {t['auto_recoverable']} ({t['pct']} %) |")
open(R+'reports/repair_census/summary.md','w').write("\n".join(md)+"\n")
print("\n".join(md))
