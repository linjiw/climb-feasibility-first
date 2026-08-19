#!/usr/bin/env python3
"""Census/repair figure: recoverable share by severity band + category. Data: reports/repair_census/summary.json."""
import json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
R = "/data/robotixx/climb/"
s = json.load(open(R + "reports/repair_census/summary.json"))
fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.2))
ax = axes[0]
rows = [("10–25 % band", s["matrix"]["10-25%"]), ("> 25 % band", s["matrix"][">25%"]), ("all flagged", s["total"])]
ys = range(len(rows))
ax.barh(list(ys), [r[1]["pct"] for r in rows], color="#0B7285", alpha=0.9)
ax.barh(list(ys), [100 - r[1]["pct"] for r in rows], left=[r[1]["pct"] for r in rows], color="#D8DFE3")
for y, (lab, t) in zip(ys, rows):
    ax.text(t["pct"] - 2, y, f"{t['pct']}%", va="center", ha="right", color="white", fontsize=9, fontweight="bold")
ax.set_yticks(list(ys), [f"{lab}\n(n={t['n']:,})" for lab, t in rows], fontsize=8.5)
ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("auto-recoverable by 3-s root projection [%]")
ax.set_title("(a) by severity", fontsize=10)
ax = axes[1]
cats = sorted(s["by_category"].items(), key=lambda kv: -kv[1]["pct"])
ys = range(len(cats))
ax.barh(list(ys), [t["pct"] for _, t in cats], color=["#2E7D4F" if t["pct"] >= 65 else "#B7791F" for _, t in cats], alpha=0.9)
ax.set_yticks(list(ys), [f"{c} (n={t['n']:,})" for c, t in cats], fontsize=8.5)
ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("auto-recoverable [%]")
for y, (c, t) in zip(ys, cats): ax.text(t["pct"] + 1.2, y, f"{t['pct']}%", va="center", fontsize=8.5)
ax.set_title("(b) by category — ballistics correctly resist repair", fontsize=10)
for a in axes:
    for sp in ("top", "right"): a.spines[sp].set_visible(False)
fig.suptitle("Two-thirds of flagged clips are a 3-second fix; the rest need upstream regeneration", fontsize=11, y=1.04)
fig.tight_layout()
for ext in ("png", "pdf"): fig.savefig(R + f"paper/figures/f_census_repair.{ext}", dpi=160, bbox_inches="tight")
print("wrote f_census_repair")
