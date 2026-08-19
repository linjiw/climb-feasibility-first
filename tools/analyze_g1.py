#!/usr/bin/env python3
"""Analyse a G1 gate run (tools/g1_clip44_gate.py) exactly as pre-registered.

Outputs (in the run dir): g1_summary.json, g1_tables.md, fig_F_*.png
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

METRICS = ["root_pos_err", "root_ori_err", "body_pos_err", "joint_pos_err", "foot_slip", "target_gap", "effort_sat"]
AXES = {  # k -> (plus config, minus config or "base", divisor)
    "delay": ("delay+", "base", 1),
    "motor": ("motor+", "motor-", 2),
    "fric": ("fric+", "fric-", 2),
    "solref": ("solref+", "solref-", 2),
    "com": ("com+", "com-", 2),
    "condim": ("B:base", "base", 1),
}


def load(run):
    meta = json.load(open(os.path.join(run, "meta.json")))
    arms = {}
    for a in "ABC":
        p = os.path.join(run, f"arm{a}.npz")
        if os.path.exists(p):
            arms[a] = dict(np.load(p))
    return meta, arms


def world_index(meta):
    idx = {}
    for w, (c, r, cfg) in enumerate(zip(meta["world_clip"], meta["world_rep"], meta["world_cfg"])):
        idx[(c, r, cfg)] = w
    return idx


def get(arms, spec, key, w):
    """spec 'B:base' -> arm B; else arm A. Returns (T,) or (T,2) series for world w."""
    arm = "A"
    if spec.startswith("B:"):
        arm = "B"
    return arms[arm][key][:, w]


def paired_series(meta, arms, idx, clip_i, k, key, arm_minus="A"):
    """Return list over replicates of (dphi(t), both_alive(t)) restricted to clip length."""
    plus_cfg, minus_cfg, div = AXES[k]
    T_clip = int(min(meta["horizon"], round(meta["clip_len_s"][clip_i] / meta["step_dt"])))
    out = []
    for r in range(meta["replicates"]):
        wp_ = idx[(clip_i, r, plus_cfg.split(":")[-1])]
        wm_ = idx[(clip_i, r, minus_cfg)]
        a_plus = get(arms, plus_cfg, "alive", wp_)
        a_minus = arms[arm_minus]["alive"][:, wm_]
        T = min(len(a_plus), len(a_minus), T_clip)
        both = a_plus[:T].astype(bool) & a_minus[:T].astype(bool)
        if key == "contact":
            d = (get(arms, plus_cfg, key, wp_)[:T] != arms[arm_minus][key][:T, wm_]).astype(float).mean(axis=1)
        elif key == "alive":
            d = (a_plus[:T].astype(float) - a_minus[:T].astype(float))
            both = np.ones(T, dtype=bool)
        else:
            d = np.abs(get(arms, plus_cfg, key, wp_)[:T] - arms[arm_minus][key][:T, wm_])
        out.append((d, both, T))
    return out, div


def summarize(meta, arms):
    idx = world_index(meta)
    clips = meta["clips"]
    dt = meta["step_dt"]
    delta = meta["delta"]
    res = {"clips": clips, "axes": {}, "noise_floor": {}, "termination": {}, "peaks": {}}
    # noise floor: arm C base vs arm A base (raw |dphi|)
    if "C" in arms:
        for ci in range(len(clips)):
            T_clip = int(min(meta["horizon"], round(meta["clip_len_s"][ci] / dt)))
            fl = {}
            for key in METRICS + ["contact"]:
                vals = []
                for r in range(meta["replicates"]):
                    w = idx[(ci, r, "base")]
                    aA = arms["A"]["alive"][:, w]; aC = arms["C"]["alive"][:, w]
                    T = min(len(aA), len(aC), T_clip); both = aA[:T].astype(bool) & aC[:T].astype(bool)
                    if key == "contact":
                        d = (arms["A"][key][:T, w] != arms["C"][key][:T, w]).astype(float).mean(axis=1)
                    else:
                        d = np.abs(arms["A"][key][:T, w] - arms["C"][key][:T, w])
                    if both.any():
                        vals.append(float(d[both].mean()))
                fl[key] = float(np.mean(vals)) if vals else float("nan")
            # survival difference
            sA = np.mean([float(arms["A"]["alive"][min(len(arms["A"]["alive"]), T_clip) - 1, idx[(ci, r, "base")]]) for r in range(meta["replicates"])])
            sC = np.mean([float(arms["C"]["alive"][min(len(arms["C"]["alive"]), T_clip) - 1, idx[(ci, r, "base")]]) for r in range(meta["replicates"])])
            fl["survival_A"] = sA; fl["survival_C"] = sC
            res["noise_floor"][clips[ci]] = fl
    for k in AXES:
        if k == "condim" and "B" not in arms:
            continue
        res["axes"][k] = {}
        for ci in range(len(clips)):
            entry = {}
            for key in METRICS + ["contact"]:
                series, div = paired_series(meta, arms, idx, ci, k, key)
                num = 0.0; den = 0
                per_t = None; cnt_t = None
                for d, both, T in series:
                    if both.any():
                        num += float(d[both].sum()); den += int(both.sum())
                    if per_t is None:
                        per_t = np.zeros(int(min(meta["horizon"], round(meta["clip_len_s"][ci] / dt)))); cnt_t = np.zeros_like(per_t)
                    per_t[:T] += np.where(both, d, 0.0); cnt_t[:T] += both
                raw = num / den if den else float("nan")
                entry[key] = {"raw": raw, "F": raw / (div * delta[k]) if den else float("nan"), "paired_alive_frames": den}
                if key == "body_pos_err":
                    Ft = np.where(cnt_t > 0, per_t / np.maximum(cnt_t, 1), np.nan)
                    entry["_Ft_body_pos_err"] = Ft.tolist()
            # termination fragility: P(alive at clip end)
            T_clip = int(min(meta["horizon"], round(meta["clip_len_s"][ci] / dt)))
            plus_cfg, minus_cfg, _ = AXES[k]
            ap = []; am = []; first_term = []
            for r in range(meta["replicates"]):
                wp_ = idx[(ci, r, plus_cfg.split(":")[-1])]; wm_ = idx[(ci, r, minus_cfg)]
                a_plus = get(arms, plus_cfg, "alive", wp_); a_minus = arms["A"]["alive"][:, wm_]
                tp = min(len(a_plus), T_clip) - 1; tm = min(len(a_minus), T_clip) - 1
                ap.append(float(a_plus[tp])); am.append(float(a_minus[tm]))
                for a in (a_plus, a_minus):
                    z = np.nonzero(~a[:T_clip].astype(bool))[0]
                    if len(z):
                        first_term.append(float(z[0] * dt))
            entry["termination"] = {"P_alive_plus": float(np.mean(ap)), "P_alive_minus": float(np.mean(am)),
                                    "abs_diff": abs(float(np.mean(ap)) - float(np.mean(am))),
                                    "first_termination_s": (min(first_term) if first_term else None)}
            res["axes"][k][clips[ci]] = entry
    # EXPLORATORY (not pre-registered): signed effect = mean over replicates of the
    # time-mean of (phi+ - phi-) on paired-alive frames, with a paired bootstrap CI.
    # The pre-registered mean |dphi| is dominated by chaotic divergence that does
    # not shrink with R; the signed mean does, so it separates a systematic
    # parameter effect from divergence noise. Reported alongside, never instead.
    rng = np.random.default_rng(0)
    res["signed_effect"] = {}
    for k in res["axes"]:
        res["signed_effect"][k] = {}
        plus_cfg, minus_cfg, div = AXES[k]
        for ci in range(len(clips)):
            T_clip = int(min(meta["horizon"], round(meta["clip_len_s"][ci] / dt)))
            per_rep = {key: [] for key in ("body_pos_err", "root_ori_err", "joint_pos_err")}
            for r in range(meta["replicates"]):
                wp_ = idx[(ci, r, plus_cfg.split(":")[-1])]; wm_ = idx[(ci, r, minus_cfg)]
                a_plus = get(arms, plus_cfg, "alive", wp_); a_minus = arms["A"]["alive"][:, wm_]
                T = min(len(a_plus), len(a_minus), T_clip); both = a_plus[:T].astype(bool) & a_minus[:T].astype(bool)
                for key in per_rep:
                    if both.any():
                        d = get(arms, plus_cfg, key, wp_)[:T] - arms["A"][key][:T, wm_]
                        per_rep[key].append(float(d[both].mean()))
            out = {}
            for key, vals in per_rep.items():
                v = np.array(vals)
                if v.size == 0:
                    out[key] = None; continue
                boots = [float(rng.choice(v, size=v.size, replace=True).mean()) for _ in range(2000)]
                out[key] = {"mean": float(v.mean()), "ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))], "n": int(v.size),
                            "per_delta": float(v.mean() / (div * delta[k]))}
            # survival signed effect
            ap = []; am = []
            for r in range(meta["replicates"]):
                wp_ = idx[(ci, r, plus_cfg.split(":")[-1])]; wm_ = idx[(ci, r, minus_cfg)]
                a_plus = get(arms, plus_cfg, "alive", wp_); a_minus = arms["A"]["alive"][:, wm_]
                ap.append(float(a_plus[min(len(a_plus), T_clip) - 1])); am.append(float(a_minus[min(len(a_minus), T_clip) - 1]))
            out["alive"] = {"plus": float(np.mean(ap)), "minus": float(np.mean(am)), "diff": float(np.mean(ap) - np.mean(am))}
            res["signed_effect"][k][clips[ci]] = out
    # ratios vs matched-easy mean and localisation
    easy = clips[1:3]
    res["ratios"] = {}
    for k in res["axes"]:
        res["ratios"][k] = {}
        for key in METRICS + ["contact"]:
            e = np.nanmean([res["axes"][k][c][key]["raw"] for c in easy])
            res["ratios"][k][key] = {c: (res["axes"][k][c][key]["raw"] / e if e and not np.isnan(e) and e > 0 else None) for c in clips}
    for k in res["axes"]:
        res["peaks"][k] = {}
        for c in clips:
            Ft = np.array(res["axes"][k][c].get("_Ft_body_pos_err", []), dtype=float)
            if Ft.size == 0 or np.all(np.isnan(Ft)):
                continue
            win = max(1, int(round(0.5 / dt)))
            f = np.nan_to_num(Ft, nan=0.0)
            sm = np.convolve(f, np.ones(win) / win, mode="same")
            valid = ~np.isnan(Ft)
            sm[~valid] = -1
            tpk = float(np.argmax(sm) * dt)
            res["peaks"][k][c] = {"t_peak_s": tpk, "F_peak": float(sm.max()), "F_median": float(np.nanmedian(Ft)),
                                  "first_termination_s": res["axes"][k][c]["termination"]["first_termination_s"]}
    return res


def tables(meta, res):
    clips = meta["clips"]; short = [c[:34] for c in clips]
    md = ["# G1 gate — pre-registered statistics\n"]
    md.append("## Clip-level fragility, raw mean |Δφ| over paired-alive frames (body_pos_err [m])\n")
    md.append("| axis | " + " | ".join(short) + " |")
    md.append("|---|" + "---|" * len(clips))
    for k in res["axes"]:
        md.append(f"| {k} | " + " | ".join(f"{res['axes'][k][c]['body_pos_err']['raw']:.4f}" for c in clips) + " |")
    if res["noise_floor"]:
        md.append("| *same-solver floor (A base vs C base)* | " + " | ".join(f"{res['noise_floor'][c]['body_pos_err']:.4f}" for c in clips) + " |")
    md.append("\n## Ratio to matched-easy mean (body_pos_err)\n")
    md.append("| axis | " + " | ".join(short) + " |")
    md.append("|---|" + "---|" * len(clips))
    for k in res["ratios"]:
        md.append(f"| {k} | " + " | ".join((f"{res['ratios'][k]['body_pos_err'][c]:.2f}" if res['ratios'][k]['body_pos_err'][c] is not None else "–") for c in clips) + " |")
    md.append("\n## Termination fragility |P(alive+) − P(alive−)| at clip end\n")
    md.append("| axis | " + " | ".join(short) + " |")
    md.append("|---|" + "---|" * len(clips))
    for k in res["axes"]:
        md.append(f"| {k} | " + " | ".join(f"{res['axes'][k][c]['termination']['abs_diff']:.2f} ({res['axes'][k][c]['termination']['P_alive_plus']:.2f}/{res['axes'][k][c]['termination']['P_alive_minus']:.2f})" for c in clips) + " |")
    md.append("\n## Peak localisation of F(t) (body_pos_err, 0.5 s smoothing)\n")
    md.append("| axis | " + " | ".join(short) + " |")
    md.append("|---|" + "---|" * len(clips))
    for k in res["peaks"]:
        md.append(f"| {k} | " + " | ".join((f"t={res['peaks'][k][c]['t_peak_s']:.1f}s pk/med={res['peaks'][k][c]['F_peak']/max(res['peaks'][k][c]['F_median'],1e-9):.1f} fail@{res['peaks'][k][c]['first_termination_s']}" if c in res['peaks'][k] else "–") for c in clips) + " |")
    md.append("\n## EXPLORATORY (not pre-registered): signed effect, mean over replicates of time-mean (φ⁺−φ⁻), body_pos_err [m], 95% paired bootstrap CI\n")
    md.append("| axis | " + " | ".join(short) + " |")
    md.append("|---|" + "---|" * len(clips))
    for k in res.get("signed_effect", {}):
        cells = []
        for c in clips:
            e = res["signed_effect"][k][c]["body_pos_err"]
            if e is None: cells.append("–"); continue
            star = "*" if (e["ci95"][0] > 0 or e["ci95"][1] < 0) else ""
            cells.append(f"{e['mean']:+.4f} [{e['ci95'][0]:+.4f},{e['ci95'][1]:+.4f}]{star}")
        md.append(f"| {k} | " + " | ".join(cells) + " |")
    md.append("\n(* = CI excludes zero; sign: + means the +δ world tracks worse)")
    md.append("\n## Survival at clip end, +δ / −δ (or +δ / base)\n")
    md.append("| axis | " + " | ".join(short) + " |")
    md.append("|---|" + "---|" * len(clips))
    for k in res.get("signed_effect", {}):
        md.append(f"| {k} | " + " | ".join(f"{res['signed_effect'][k][c]['alive']['plus']:.2f}/{res['signed_effect'][k][c]['alive']['minus']:.2f}" for c in clips) + " |")
    if res["noise_floor"]:
        md.append("\n## Same-solver survival (A base vs C base)\n")
        md.append("| clip | Newton | mjlab |"); md.append("|---|---|---|")
        for c in clips:
            md.append(f"| {c[:40]} | {res['noise_floor'][c]['survival_A']:.2f} | {res['noise_floor'][c]['survival_C']:.2f} |")
    return "\n".join(md)


def figures(meta, res, run):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    clips = meta["clips"]; dt = meta["step_dt"]
    axes = list(res["axes"])
    fig, axs = plt.subplots(len(clips), 1, figsize=(10, 2.2 * len(clips)), sharex=True)
    for i, c in enumerate(clips):
        ax = axs[i]
        for k in axes:
            Ft = np.array(res["axes"][k][c].get("_Ft_body_pos_err", []), dtype=float)
            if Ft.size:
                ax.plot(np.arange(len(Ft)) * dt, Ft, label=k, lw=1)
        ft = res["axes"][axes[0]][c]["termination"]["first_termination_s"]
        if ft is not None:
            ax.axvline(ft, color="k", ls="--", lw=0.8)
        ax.set_ylabel("|Δ body_pos_err| [m]"); ax.set_title(c[:60], fontsize=9)
        if i == 0:
            ax.legend(ncol=len(axes), fontsize=8)
    axs[-1].set_xlabel("t [s]")
    fig.tight_layout(); fig.savefig(os.path.join(run, "fig_F_body_pos_err.png"), dpi=120); plt.close(fig)


def main():
    run = sys.argv[1]
    meta, arms = load(run)
    res = summarize(meta, arms)
    json.dump(res, open(os.path.join(run, "g1_summary.json"), "w"), indent=1)
    md = tables(meta, res)
    open(os.path.join(run, "g1_tables.md"), "w").write(md)
    print(md)
    figures(meta, res, run)


if __name__ == "__main__":
    main()
