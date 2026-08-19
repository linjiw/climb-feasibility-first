#!/usr/bin/env python3
"""F4 — feasibility prevalence by category and by source. Data: reports/feasibility_all/feasibility.csv."""
import csv, sys, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
sys.path.insert(0, "/data/robotixx/climb/tools")
from analyze_atlas_support import category
R = "/data/robotixx/climb/"
feats = {r["name"]: r for r in csv.DictReader(open(R + "reports/features_amass.csv"))}
rows = [(r["clip"], float(r["infeasible_frac"])) for r in csv.DictReader(open(R + "reports/feasibility_all/feasibility.csv")) if r["clip"] in feats]
cat = {c: category(feats[c]) for c, _ in rows}
src = {c: c.split("_")[0] for c, _ in rows}
fig, axes = plt.subplots(1, 2, figsize=(10.4, 3.6), gridspec_kw={"width_ratios": [1, 1.5]})
ax = axes[0]
cats = ["dynamic", "ground", "locomotion", "quiet"]
frac = [np.mean([f > 0.10 for c, f in rows if cat[c] == k]) * 100 for k in cats]
n = [sum(cat[c] == k for c, _ in rows) for k in cats]
bars = ax.barh(range(len(cats)), frac, color=["#B3261E", "#B3261E", "#B7791F", "#5C6B75"], alpha=0.85)
ax.set_yticks(range(len(cats)), [f"{k}\n(n={m:,})" for k, m in zip(cats, n)], fontsize=8.5)
ax.invert_yaxis(); ax.set_xlabel("% of clips with >10% infeasible frames")
ax.axvline(22.8, color="#0B7285", ls="--", lw=1.2); ax.text(23.5, 3.3, "bank-wide 22.8%", fontsize=8, color="#0B7285")
for b, v in zip(bars, frac): ax.text(v + 1, b.get_y() + b.get_height()/2, f"{v:.1f}%", va="center", fontsize=8.5)
ax.set_title("(a) by motion category", fontsize=10)
ax = axes[1]
srcs = sorted({s for s in src.values()}, key=lambda s: -sum(1 for c, _ in rows if src[c] == s))
srcs = [s for s in srcs if sum(1 for c, _ in rows if src[c] == s) >= 50]
frac_s = [(s, np.mean([f > 0.10 for c, f in rows if src[c] == s]) * 100, sum(1 for c, _ in rows if src[c] == s)) for s in srcs]
frac_s.sort(key=lambda t: t[1])
ys = range(len(frac_s))
ax.barh(list(ys), [t[1] for t in frac_s], color=["#B3261E" if t[1] > 50 else "#0B7285" for t in frac_s], alpha=0.85)
ax.set_yticks(list(ys), [f"{t[0]} (n={t[2]:,})" for t in frac_s], fontsize=8)
ax.set_xlabel("% of clips flagged"); ax.set_xlim(0, 105)
for y, t in zip(ys, frac_s): ax.text(t[1] + 1.2, y, f"{t[1]:.1f}%", va="center", fontsize=8)
ax.set_title("(b) by source dataset — 0.1% → 100% under ONE retargeting pipeline", fontsize=10)
for a in axes:
    for sp in ("top", "right"): a.spines[sp].set_visible(False)
fig.suptitle("Dynamic infeasibility of a 10,705-clip retargeted AMASS→G1 bank", fontsize=11, y=1.03)
fig.tight_layout()
for ext in ("png", "pdf"): fig.savefig(R + f"paper/figures/f4_prevalence.{ext}", dpi=160, bbox_inches="tight")
print("wrote f4_prevalence.png/pdf")
