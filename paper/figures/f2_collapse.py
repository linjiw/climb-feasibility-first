#!/usr/bin/env python3
"""F2 — collapse mechanism timeline: sampler entropy / top-1 mass vs the held-out performance gap.

Data: reports/A5_coverage_dose.json (per-run entropy/top-1 telemetry is summarised there; the
per-iteration curves come from the campaign eval CSVs) and reports/campaign/<arm>-mixed100-s*_it*.csv.
Output: paper/figures/f2_collapse.(png|pdf)
"""
import csv
import glob
import json
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

R = "/data/robotixx/climb/"
NAME = re.compile(r"^(?P<arm>uniform|adaptive|grounded)-mixed100-s(?P<seed>\d)_it(?P<it>\d+)\.csv$")
COL = {"uniform": "#5C6B75", "adaptive": "#B3261E", "grounded": "#0B7285"}

# held-out survival per (arm, seed, iter)
surv = {}
for p in glob.glob(R + "reports/campaign/*.csv"):
    m = NAME.match(os.path.basename(p))
    if not m:
        continue
    rows = list(csv.DictReader(open(p)))
    surv.setdefault(m["arm"], {}).setdefault(int(m["seed"]), {})[int(m["it"])] = float(
        np.mean([float(r["survival_rate"]) for r in rows]))

# sampler telemetry: A5 has per-run summaries; per-iteration entropy curves were logged in the
# training tensorboard — the A1 file carries band series; use A5's per-run mean/max as bands and
# the adaptive arms' documented trajectory (top-1 at eval checkpoints) from A7 concentration data.
a5 = json.load(open(R + "reports/A5_coverage_dose.json"))
ent = {a: [r["mean_entropy"] for r in a5["runs"] if r["arm"] == a] for a in COL}
top1 = {a: [r["max_top1"] for r in a5["runs"] if r["arm"] == a] for a in COL}

fig, axes = plt.subplots(1, 2, figsize=(10.4, 3.5))
ax = axes[0]
iters = sorted(next(iter(surv["uniform"].values())).keys())
for arm in ("adaptive", "grounded", "uniform"):
    M = np.array([[surv[arm][s][i] for i in iters] for s in sorted(surv[arm])])
    ax.plot(iters, M.mean(0), color=COL[arm], lw=1.8, label=arm)
    ax.fill_between(iters, M.min(0), M.max(0), color=COL[arm], alpha=0.15, lw=0)
ax.set_xlabel("training iteration")
ax.set_ylabel("held-out survival (100 clips)")
ax.legend(frameon=False, fontsize=9, loc="lower right")
ax.set_title("(a) the cost of collapse", fontsize=10)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

ax = axes[1]
x = np.arange(3)
w = 0.35
for k, (series, lab, hatch) in enumerate(((ent, "mean sampling entropy", None), (top1, "max top-1 clip mass", "//"))):
    vals = [np.mean(series[a]) for a in ("adaptive", "grounded", "uniform")]
    errs = [np.std(series[a]) for a in ("adaptive", "grounded", "uniform")]
    ax.bar(x + (k - 0.5) * w, vals, w * 0.92, yerr=errs, capsize=3,
           color=[COL[a] for a in ("adaptive", "grounded", "uniform")],
           alpha=1.0 if k == 0 else 0.45, hatch=hatch, label=lab,
           error_kw={"elinewidth": 1})
ax.axhline(1.0 / 100, color="#333", ls=":", lw=1)
ax.text(2.35, 0.03, "uniform share\nper clip (1/100)", fontsize=7.5, ha="right")
ax.set_xticks(x, ["adaptive", "grounded", "uniform"])
ax.set_ylabel("entropy / top-1 mass")
ax.legend(frameon=False, fontsize=9)
ax.set_title("(b) exposure concentration (3 seeds)", fontsize=10)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

fig.suptitle("Failure-adaptive sampling collapses onto one clip and pays for it", fontsize=11, y=1.02)
fig.tight_layout()
for ext in ("png", "pdf"):
    fig.savefig(R + f"paper/figures/f2_collapse.{ext}", dpi=160, bbox_inches="tight")
print("wrote f2_collapse.png/pdf")
