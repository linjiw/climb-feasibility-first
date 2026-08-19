#!/usr/bin/env python3
"""P-SIGN analysis, exactly as sealed (plan/PREREGISTRATION_P_SIGN.md, c7916e8c).

Windows per clip from the full screen (tools/n1_knee_id.py, gap 6 cm), computed from the
reference only: airborne = no contact candidate AND torque-limited unsupported > 0.5*weight,
dilated +-0.1 s; standing = unsupported <= 0.1*weight, dilated, non-overlapping.
Statistic: signed replicate-mean S on body_pos_err (N5), floor from arm C base worlds per run.

Usage: analyze_p_sign.py reports/P_SIGN/run0
"""
from __future__ import annotations
import json, os, subprocess, sys
import numpy as np

R = "/data/robotixx/climb/"
BOOT = 2000


def windows_for(clip, dt, T, weight=327.0):
    p = R + f"reports/P_SIGN/screens/{clip}.json"
    if not os.path.exists(p):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        subprocess.run([R + "bridge/.venv/bin/python", R + "tools/n1_knee_id.py", "--clip", clip,
                        "--t0", "0", "--t1", "1e9", "--gap", "0.06", "--out", p],
                       check=True, capture_output=True, env={**os.environ, "CUDA_VISIBLE_DEVICES": ""})
    fr = json.load(open(p))["frames"]
    t = np.array([x["t"] for x in fr])
    tl = np.array([x["real"]["tl_unsupported_force_N"] if x["real"]["tl_unsupported_force_N"] is not None
                   else (x["real"]["unsupported_force_N"] if x["n_contacts"] == 0 else 0.0) for x in fr])
    nc = np.array([x["n_contacts"] == 0 for x in fr])
    air_f = nc & (tl > 0.5 * weight)
    stand_f = tl <= 0.1 * weight
    def to_steps(mask):
        out = np.zeros(T, bool)
        for k in range(T):
            tt = k * dt
            j = np.argmin(np.abs(t - tt))
            lo, hi = tt - 0.1, tt + 0.1
            sel = (t >= lo) & (t <= hi)
            out[k] = bool(mask[sel].any()) if sel.any() else bool(mask[j])
        return out
    air = to_steps(air_f)
    stand = to_steps(stand_f) & ~air
    return air, stand


def signed_S(arms, idx, meta, ci, key, mask=None):
    """per-replicate mean of (motor+ - motor-) on paired-alive (optionally masked) steps."""
    dt = meta["step_dt"]
    T_clip = int(min(meta["horizon"], round(meta["clip_len_s"][ci] / dt)))
    per = []
    for r in range(meta["replicates"]):
        wp_ = idx[(ci, r, "motor+")]; wm_ = idx[(ci, r, "motor-")]
        p = arms["A"][key][:, wp_]; m = arms["A"][key][:, wm_]
        ap = arms["A"]["alive"][:, wp_].astype(bool); am = arms["A"]["alive"][:, wm_].astype(bool)
        T = min(len(p), len(m), T_clip)
        both = ap[:T] & am[:T]
        if mask is not None:
            both = both & mask[:T]
        if both.any():
            per.append(float((p[:T][both] - m[:T][both]).mean()))
    return np.array(per)


def ci95(v, rng):
    boots = np.array([rng.choice(v, v.size, replace=True).mean() for _ in range(BOOT)])
    return float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def main():
    run = sys.argv[1]
    meta = json.load(open(os.path.join(run, "meta.json")))
    arms = {a: dict(np.load(os.path.join(run, f"arm{a}.npz"))) for a in "AC" if os.path.exists(os.path.join(run, f"arm{a}.npz"))}
    idx = {(c, r, cfg): w for w, (c, r, cfg) in enumerate(zip(meta["world_clip"], meta["world_rep"], meta["world_cfg"]))}
    clips = meta["clips"]; nfam = meta["n_family"]; dt = meta["step_dt"]
    rng = np.random.default_rng(0)
    out = {"seal": meta["seal"], "clips": {}, "floor": {}}
    # per-run floor: arm A base vs arm C base, whole clip
    for ci, c in enumerate(clips):
        T_clip = int(min(meta["horizon"], round(meta["clip_len_s"][ci] / dt)))
        per = []
        for r in range(meta["replicates"]):
            w = idx[(ci, r, "base")]
            pA = arms["A"]["body_pos_err"][:, w]; pC = arms["C"]["body_pos_err"][:, w]
            aA = arms["A"]["alive"][:, w].astype(bool); aC = arms["C"]["alive"][:, w].astype(bool)
            T = min(len(pA), len(pC), T_clip); both = aA[:T] & aC[:T]
            if both.any():
                per.append(float((pA[:T][both] - pC[:T][both]).mean()))
        v = np.array(per)
        out["floor"][c] = {"mean_mm": float(v.mean() * 1000), "ci_mm": [x * 1000 for x in ci95(v, rng)]} if v.size else None
    crit1 = crit2 = crit3 = 0
    for ci, c in enumerate(clips):
        fam = ci < nfam
        T_clip = int(min(meta["horizon"], round(meta["clip_len_s"][ci] / dt)))
        rec = {"family": fam}
        if fam:
            air, stand = windows_for(c, dt, T_clip)
            rec["airborne_steps"] = int(air.sum()); rec["standing_steps"] = int(stand.sum())
            for nm, msk in (("airborne", air), ("standing", stand)):
                v = signed_S(arms, idx, meta, ci, "body_pos_err", msk)
                rec[nm] = {"S_mm": float(v.mean() * 1000), "ci_mm": [x * 1000 for x in ci95(v, rng)], "n": int(v.size)} if v.size else None
            a = rec.get("airborne"); s = rec.get("standing")
            p1 = bool(a and a["S_mm"] >= 5.0 and a["ci_mm"][0] > 0)
            p3 = bool(a and s and abs(s["S_mm"]) > 1e-9 and abs(a["S_mm"]) >= 3 * abs(s["S_mm"])) or bool(a and s and abs(s["S_mm"]) <= 1e-9 and abs(a["S_mm"]) > 0)
            rec["passes_i"] = p1; rec["passes_iii"] = bool(p1 and p3)
            crit1 += p1; crit3 += (p1 and p3)
        else:
            v = signed_S(arms, idx, meta, ci, "body_pos_err")
            rec["whole"] = {"S_mm": float(v.mean() * 1000), "ci_mm": [x * 1000 for x in ci95(v, rng)], "n": int(v.size)} if v.size else None
            p2 = bool(rec["whole"] and abs(rec["whole"]["S_mm"]) < 2.0)
            rec["passes_ii"] = p2; crit2 += p2
        out["clips"][c] = rec
    out["verdict"] = {"i_family_pass": f"{crit1}/12 (need >=8)", "ii_controls_pass": f"{crit2}/12 (need >=8)",
                      "iii_localised_among_i": f"{crit3}", "PASS": bool(crit1 >= 8 and crit2 >= 8 and crit3 >= 8)}
    json.dump(out, open(os.path.join(run, "p_sign_summary.json"), "w"), indent=1)
    print(json.dumps(out["verdict"], indent=1))
    for c, rec in out["clips"].items():
        if rec["family"]:
            a = rec.get("airborne"); s = rec.get("standing")
            print(f"  FAM {c[:46]:48s} air {a['S_mm']:+6.1f} [{a['ci_mm'][0]:+.1f},{a['ci_mm'][1]:+.1f}]  stand {s['S_mm'] if s else float('nan'):+6.1f}  i={rec['passes_i']} iii={rec['passes_iii']}" if a else f"  FAM {c}: no paired-alive airborne steps")
        else:
            w = rec.get("whole")
            print(f"  CTL {c[:46]:48s} whole {w['S_mm']:+6.1f} [{w['ci_mm'][0]:+.1f},{w['ci_mm'][1]:+.1f}]  ii={rec['passes_ii']}" if w else f"  CTL {c}: none")


if __name__ == "__main__":
    main()
