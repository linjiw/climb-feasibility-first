#!/usr/bin/env python3
"""N5 -- instrument calibration: F redefined so it can resolve signal below the chaos floor.

The pre-registered G1 statistic (mean |phi+ - phi-| along paired single trajectories) is dominated
by chaotic divergence: identical physics from identical states already differs by 2.5-8 mm of
body-position error within seconds. Three replacements, each with the noise floor measured the
same way from the stock-mjlab arm (A base vs C base):

  S  signed replicate-mean effect  E_r[ mean_t (phi+ - phi-) ]  with paired bootstrap CI  (shrinks with R)
  D  distributional distance      W1( {phi+(t)} , {phi-(t)} ) over paired-alive frames pooled across replicates,
                                  minus the same for A-base vs C-base                       (chaos cancels in expectation)
  T  timing / survival            first-termination time shift (paired, mean over replicates), first-contact-onset shift
                                  per foot, and P(alive at clip end) difference

Everything is per (clip, axis); the floor is per clip. A statistic is 'resolved' when |effect| exceeds
2x the floor's bootstrap 95% half-width. This is method development, not a second bite at P1.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_g1 import AXES, load, world_index, get  # noqa: E402

METRICS = ["root_pos_err", "root_ori_err", "body_pos_err", "joint_pos_err"]


def w1(a, b):
    a = np.sort(a); b = np.sort(b)
    q = np.linspace(0, 1, 201)
    return float(np.abs(np.quantile(a, q) - np.quantile(b, q)).mean())


def pair_frames(meta, arms, idx, ci, plus_spec, minus_arm, minus_cfg, key):
    """Yield per replicate (a_plus, a_minus, T) already truncated to clip length; a_* are 1-D arrays of key."""
    T_clip = int(min(meta["horizon"], round(meta["clip_len_s"][ci] / meta["step_dt"])))
    out = []
    for r in range(meta["replicates"]):
        wp_ = idx[(ci, r, plus_spec.split(":")[-1])]; wm_ = idx[(ci, r, minus_cfg)]
        alive_p = get(arms, plus_spec, "alive", wp_); alive_m = arms[minus_arm]["alive"][:, wm_]
        T = min(len(alive_p), len(alive_m), T_clip)
        both = alive_p[:T].astype(bool) & alive_m[:T].astype(bool)
        out.append((get(arms, plus_spec, key, wp_)[:T], arms[minus_arm][key][:T, wm_], both, alive_p[:T_clip], alive_m[:T_clip]))
    return out, T_clip


def first_true(a):
    z = np.nonzero(a)[0]
    return int(z[0]) if len(z) else None


def stats_for(meta, arms, idx, ci, plus_spec, minus_arm, minus_cfg, dt, rng, nboot=1000):
    res = {}
    for key in METRICS:
        pairs, T_clip = pair_frames(meta, arms, idx, ci, plus_spec, minus_arm, minus_cfg, key)
        per_rep = [float((p[b] - m[b]).mean()) for p, m, b, _, _ in pairs if b.any()]
        pooled_p = np.concatenate([p[b] for p, m, b, _, _ in pairs if b.any()]) if per_rep else np.array([])
        pooled_m = np.concatenate([m[b] for p, m, b, _, _ in pairs if b.any()]) if per_rep else np.array([])
        v = np.array(per_rep)
        if v.size:
            boots = np.array([rng.choice(v, v.size, replace=True).mean() for _ in range(nboot)])
            res[key] = {"S_mean": float(v.mean()), "S_ci": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
                        "S_n": int(v.size), "D_w1": w1(pooled_p, pooled_m), "paired_frames": int(pooled_p.size)}
        else:
            res[key] = {"S_mean": None, "S_ci": None, "S_n": 0, "D_w1": None, "paired_frames": 0}
    # timing / survival
    pairs, T_clip = pair_frames(meta, arms, idx, ci, plus_spec, minus_arm, minus_cfg, "alive")
    dterm = []; alive_end_p = []; alive_end_m = []
    for _, _, _, ap, am in pairs:
        tp = first_true(~ap.astype(bool)); tm = first_true(~am.astype(bool))
        tp = (tp if tp is not None else len(ap)) * dt; tm = (tm if tm is not None else len(am)) * dt
        dterm.append(tp - tm)
        alive_end_p.append(float(ap[min(len(ap), T_clip) - 1])); alive_end_m.append(float(am[min(len(am), T_clip) - 1]))
    # contact onset shift per foot
    pairs_c, _ = pair_frames(meta, arms, idx, ci, plus_spec, minus_arm, minus_cfg, "contact")
    onset = {0: [], 1: []}
    for p, m, b, _, _ in pairs_c:
        for f in (0, 1):
            op = first_true(p[:, f].astype(bool)); om = first_true(m[:, f].astype(bool))
            if op is not None and om is not None:
                onset[f].append((op - om) * dt)
    res["T"] = {"first_termination_shift_s": float(np.mean(dterm)), "first_termination_shift_sd": float(np.std(dterm)),
                "P_alive_end_plus": float(np.mean(alive_end_p)), "P_alive_end_minus": float(np.mean(alive_end_m)),
                "contact_onset_shift_L_s": (float(np.mean(onset[0])) if onset[0] else None),
                "contact_onset_shift_R_s": (float(np.mean(onset[1])) if onset[1] else None)}
    return res


def main():
    run = sys.argv[1]
    meta, arms = load(run)
    idx = world_index(meta)
    clips = meta["clips"]; dt = meta["step_dt"]; delta = meta["delta"]
    rng = np.random.default_rng(0)
    out = {"clips": clips, "floor": {}, "axes": {}}
    # floor: A base vs C base
    for ci, c in enumerate(clips):
        out["floor"][c] = stats_for(meta, arms, idx, ci, "base", "C", "base", dt, rng)
    for k, (plus_cfg, minus_cfg, div) in AXES.items():
        if k == "condim" and "B" not in arms:
            continue
        out["axes"][k] = {}
        for ci, c in enumerate(clips):
            st = stats_for(meta, arms, idx, ci, plus_cfg, "A", minus_cfg, dt, rng)
            for key in METRICS:
                s = st[key]; f = out["floor"][c][key]
                if s["S_mean"] is not None and f["S_ci"] is not None:
                    half = (f["S_ci"][1] - f["S_ci"][0]) / 2
                    s["S_resolved"] = bool(abs(s["S_mean"]) > 2 * half and (s["S_ci"][0] > 0 or s["S_ci"][1] < 0))
                    s["S_over_floor_halfwidth"] = float(abs(s["S_mean"]) / max(half, 1e-9))
                    s["D_w1_minus_floor"] = float(s["D_w1"] - f["D_w1"]) if s["D_w1"] is not None else None
                    s["S_per_delta"] = float(s["S_mean"] / (div * delta[k]))
            out["axes"][k][c] = st
    json.dump(out, open(os.path.join(run, "g1_v2_summary.json"), "w"), indent=1)
    # tables
    short = [c[:26] for c in clips]
    md = ["# G1 instrument calibration (N5) — redefined statistics\n",
          "Signed replicate-mean effect S on body_pos_err [mm] (+ = +δ world tracks worse), 95% paired-bootstrap CI; ‡ = resolved (|S| > 2× floor half-width and CI excludes 0). Floor row: A-base vs C-base (identical physics).\n",
          "| axis | " + " | ".join(short) + " |", "|---|" + "---|" * len(clips)]
    for k in out["axes"]:
        cells = []
        for c in clips:
            s = out["axes"][k][c]["body_pos_err"]
            if s["S_mean"] is None: cells.append("–"); continue
            cells.append(f"{s['S_mean']*1000:+.1f} [{s['S_ci'][0]*1000:+.1f},{s['S_ci'][1]*1000:+.1f}]{'‡' if s.get('S_resolved') else ''}")
        md.append(f"| {k} | " + " | ".join(cells) + " |")
    md.append("| *floor (A base − C base)* | " + " | ".join(f"{out['floor'][c]['body_pos_err']['S_mean']*1000:+.1f} [{out['floor'][c]['body_pos_err']['S_ci'][0]*1000:+.1f},{out['floor'][c]['body_pos_err']['S_ci'][1]*1000:+.1f}]" if out['floor'][c]['body_pos_err']['S_mean'] is not None else "–" for c in clips) + " |")
    md += ["\nDistributional distance D = W1(φ⁺, φ⁻) − W1(A base, C base), body_pos_err [mm] (positive = the intervention separates the distributions beyond chaos)\n",
           "| axis | " + " | ".join(short) + " |", "|---|" + "---|" * len(clips)]
    for k in out["axes"]:
        md.append(f"| {k} | " + " | ".join((f"{out['axes'][k][c]['body_pos_err']['D_w1_minus_floor']*1000:+.1f}" if out['axes'][k][c]['body_pos_err'].get('D_w1_minus_floor') is not None else "–") for c in clips) + " |")
    md.append("| *floor W1* | " + " | ".join(f"{out['floor'][c]['body_pos_err']['D_w1']*1000:.1f}" for c in clips) + " |")
    md += ["\nTiming: first-termination shift (+δ − −δ) [s], mean ± sd over replicates; and P(alive at clip end) +δ / −δ\n",
           "| axis | " + " | ".join(short) + " |", "|---|" + "---|" * len(clips)]
    for k in out["axes"]:
        md.append(f"| {k} | " + " | ".join(f"{out['axes'][k][c]['T']['first_termination_shift_s']:+.2f}±{out['axes'][k][c]['T']['first_termination_shift_sd']:.2f} ({out['axes'][k][c]['T']['P_alive_end_plus']:.2f}/{out['axes'][k][c]['T']['P_alive_end_minus']:.2f})" for c in clips) + " |")
    md.append("| *floor* | " + " | ".join(f"{out['floor'][c]['T']['first_termination_shift_s']:+.2f}±{out['floor'][c]['T']['first_termination_shift_sd']:.2f}" for c in clips) + " |")
    md += ["\nContact-onset shift, left/right foot [s] (+δ − −δ)\n", "| axis | " + " | ".join(short) + " |", "|---|" + "---|" * len(clips)]
    for k in out["axes"]:
        md.append(f"| {k} | " + " | ".join((f"{out['axes'][k][c]['T']['contact_onset_shift_L_s']:+.2f}/{out['axes'][k][c]['T']['contact_onset_shift_R_s']:+.2f}" if out['axes'][k][c]['T']['contact_onset_shift_L_s'] is not None and out['axes'][k][c]['T']['contact_onset_shift_R_s'] is not None else "–") for c in clips) + " |")
    text = "\n".join(md)
    open(os.path.join(run, "g1_v2_tables.md"), "w").write(text)
    print(text)


if __name__ == "__main__":
    main()
