#!/usr/bin/env python3
"""F3 — clip #44 anatomy, four panels: (a) stick frames incl. airborne window; (b) unsupported
force; (c) stratified start-offset deaths; (d) paired fragility F(t) at the same-solver floor.
Data: reports/N1_clip44_knee_id.json, reports/N3_baseline_uniform-s1_strat.csv, reports/G1/run0/g1_summary.json."""
import csv, json, glob, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import mujoco
R = "/data/robotixx/climb/"
CLIP = "BMLmovi_Subject_64_F_MoSh_Subject_64_F_9_poses_120_jpos"
m = mujoco.MjModel.from_xml_path(sorted(glob.glob('/tmp/s1_*/g1_compiled.xml.mj.xml'), key=os.path.getmtime)[-1])
dat = np.load(R + f"bank/amass/{CLIP}.npz"); fps = 50.0
n1 = json.load(open(R + "reports/N1_clip44_knee_id.json")); fr = n1["frames"]
t1 = np.array([x["t"] for x in fr]); nc = np.array([x["n_contacts"] == 0 for x in fr])
tl = np.array([x["real"]["tl_unsupported_force_N"] if x["real"]["tl_unsupported_force_N"] is not None
               else (x["real"]["unsupported_force_N"] if x["n_contacts"] == 0 else 0.0) for x in fr])
fig = plt.figure(figsize=(11, 6.6))
gs = fig.add_gridspec(3, 5, height_ratios=[1.25, 0.8, 0.9], hspace=0.55)
par = {i - 2: m.body_parentid[i] - 2 for i in range(3, m.nbody)}
for ax_i, tt in enumerate([0.5, 1.0, 1.3, 1.6, 2.5]):
    ax = fig.add_subplot(gs[0, ax_i]); k = int(tt * fps); P = dat["body_pos_w"][k]
    for c, p in par.items():
        if p >= 0: ax.plot([P[c, 0], P[p, 0]], [P[c, 2], P[p, 2]], "-", color="#0B7285", lw=1.5)
    ax.scatter(P[:, 0], P[:, 2], s=5, color="#15222B", zorder=3)
    ax.axhline(0, color="#8a6d1a", lw=2)
    j = int(np.argmin(np.abs(t1 - tt)))
    if nc[j]: ax.set_facecolor("#FBEAEA"); ax.set_title(f"t={tt}s — NO CONTACT", fontsize=8, color="#B3261E")
    else: ax.set_title(f"t={tt}s", fontsize=8)
    ax.set_xlim(P[0, 0] - 0.6, P[0, 0] + 0.6); ax.set_ylim(-0.07, 1.05); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
ax = fig.add_subplot(gs[1, :])
ax.fill_between(t1, tl, color="#B3261E", alpha=0.35, step="mid"); ax.plot(t1, tl, color="#B3261E", lw=0.9)
ax.axhline(327, color="#5C6B75", ls="--", lw=1); ax.text(9.85, 337, "robot weight 327 N", fontsize=7.5, ha="right", color="#5C6B75")
ax.set_ylabel("unsupported\nforce [N]", fontsize=8.5); ax.set_xlim(0, 9.9); ax.set_ylim(0, 385); ax.set_xlabel("clip time [s]", fontsize=8.5)
ax.set_title("(b) torque-limited unsupported wrench of the reference [measured]", fontsize=9, loc="left")
axc = fig.add_subplot(gs[2, 0:2])
rows = [r for r in csv.DictReader(open(R + "reports/N3_baseline_uniform-s1_strat.csv")) if r["clip"] == CLIP and r["offset_s"] != "mean"]
offs = [float(r["offset_s"]) for r in rows]; surv = [float(r["survival"]) for r in rows]
axc.bar([str(int(o)) for o in offs], surv, color=["#B3261E" if s < 0.5 else "#2E7D4F" for s in surv], width=0.62)
axc.set_xlabel("start offset [s]", fontsize=8.5); axc.set_ylabel("survival (3 s window)", fontsize=8.5); axc.set_ylim(0, 1.05)
axc.set_title("(c) stratified starts: 0.00 everywhere\nin the ground segment [measured]", fontsize=9, loc="left")
axd = fig.add_subplot(gs[2, 2:])
g1 = json.load(open(R + "reports/G1/run0/g1_summary.json")); dt = 0.02
cols = {"delay": "#0B7285", "motor": "#B7791F", "fric": "#2E7D4F", "solref": "#7A5195", "com": "#B3261E", "condim": "#4B5563"}
for kx, c in cols.items():
    Ft = np.array(g1["axes"][kx][CLIP]["_Ft_body_pos_err"], dtype=float)
    axd.plot(np.arange(len(Ft)) * dt, Ft * 100, color=c, lw=1.0, label=kx)
axd.axhline(g1["noise_floor"][CLIP]["body_pos_err"] * 100, color="#666", ls=":", lw=1, label="same-solver floor")
axd.set_xlim(0, 3.1); axd.set_ylim(0, 6); axd.set_xlabel("clip time [s]", fontsize=8.5); axd.set_ylabel("|Δ body err| [cm]", fontsize=8.5)
axd.legend(fontsize=6.5, ncol=4, frameon=False)
axd.set_title("(d) no physics axis separates from the floor before the fall [sealed ✗, kept]", fontsize=9, loc="left")
for a in fig.axes:
    for sp in ("top", "right"): a.spines[sp].set_visible(False)
fig.suptitle("(a–d) Anatomy of the attractor: a kinematically clean, dynamically impossible reference", fontsize=11, y=0.99)
for ext in ("png", "pdf"): fig.savefig(R + f"paper/figures/f3_anatomy.{ext}", dpi=150, bbox_inches="tight")
print("wrote f3_anatomy")
