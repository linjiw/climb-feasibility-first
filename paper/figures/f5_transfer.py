#!/usr/bin/env python3
"""F5 — cross-policy transfer lift. Data: reports/N2_atlas_support.json, reports/N_atlas_v21.json."""
import json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
R = "/data/robotixx/climb/"
n2 = json.load(open(R + "reports/N2_atlas_support.json"))["T2"]
v21 = json.load(open(R + "reports/N_atlas_v21.json"))["F2"]
pairs = ["adaptive->uniform", "uniform->adaptive", "grounded->uniform", "grounded->adaptive", "uniform->grounded", "adaptive->grounded"]
lab = [p.replace("->", "→") for p in pairs]
xi = np.arange(len(pairs))
fig, ax = plt.subplots(figsize=(8.8, 3.6))
intr = [v21[p]["intrinsic"] for p in pairs]
sup = [n2[p]["intrinsic+support"] for p in pairs]
fea = [v21[p]["intrinsic+feas"] for p in pairs]
p95 = [v21[p]["perm_p95"] for p in pairs]
ax.scatter(xi - 0.18, intr, s=44, color="#5C6B75", label="intrinsic atlas", zorder=3)
ax.scatter(xi, sup, s=44, color="#B7791F", marker="s", label="+ support (N2 — null)", zorder=3)
ax.scatter(xi + 0.18, fea, s=54, color="#0B7285", marker="D", label="+ feasibility (v2.1)", zorder=3)
for x, lo, hi in zip(xi, intr, p95):
    ax.plot([x - 0.30, x + 0.30], [hi, hi], color="#B3261E", lw=1.2, ls=":")
ax.plot([], [], color="#B3261E", lw=1.2, ls=":", label="random-3-feature p95")
for x, p in zip(xi, pairs):
    pv = v21[p]["p_perm"]
    if pv < 0.05:
        ax.text(x + 0.18, fea[pairs.index(p)] + 0.008, f"p={pv:.3f}", fontsize=7.5, ha="center", color="#0B7285")
ax.set_xticks(xi, lab, fontsize=8.5)
ax.set_ylabel("cross-policy Spearman ρ\n(fit on src arm, predict dst arm)")
ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="lower right")
ax.set_title("Feasibility is the difficulty component that transfers across policies", fontsize=11)
for s in ("top", "right"): ax.spines[s].set_visible(False)
fig.tight_layout()
for ext in ("png", "pdf"): fig.savefig(R + f"paper/figures/f5_transfer.{ext}", dpi=160, bbox_inches="tight")
print("wrote f5_transfer.png/pdf")
