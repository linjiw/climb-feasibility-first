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


def synthetic():
    """Fabricate outcomes for pass/fail branches in a temp dir; assert verdict logic. No real data."""
    import tempfile
    fam = [l.strip() for l in open(R + "plan/P_SIGN_clips_family.txt") if l.strip()]
    ctl = [l.strip() for l in open(R + "plan/P_SIGN_clips_controls.txt") if l.strip()]
    rng = np.random.default_rng(1)

    def fabricate(tmp, air_mm, ctl_mm, n_fam_effect):
        clips = fam + ctl
        names = ["base", "motor-", "motor+"]
        R_ = 8
        layout = [(ci, r, nm) for ci in range(len(clips)) for r in range(R_) for nm in names]
        T = 150
        N = len(layout)
        err = np.zeros((T, N)); alive = np.ones((T, N))
        # synthetic windows: steps 40-90 airborne for family clips (monkeypatched below)
        for w, (ci, r, nm) in enumerate(layout):
            base = 0.03 + rng.normal(0, 0.0005, T).cumsum() * 0  # flat base + tiny noise
            e = base + rng.normal(0, 0.0002, T)
            if nm == "motor+" and ci < n_fam_effect:            # effect only inside airborne window
                e[40:90] += air_mm / 1000.0
            if nm == "motor+" and ci >= len(fam):                # controls: whole-clip offset
                e += ctl_mm / 1000.0
            err[:, w] = e
        contact = np.zeros((T, N, 2), bool)
        np.savez_compressed(os.path.join(tmp, "armA.npz"), body_pos_err=err, alive=alive, contact=contact)
        np.savez_compressed(os.path.join(tmp, "armC.npz"),
                            body_pos_err=err[:, [i for i, (ci, r, nm) in enumerate(layout)]] + rng.normal(0, 0.0002, err.shape),
                            alive=alive, contact=contact)
        json.dump({"clips": clips, "n_family": len(fam), "replicates": R_, "configs": names,
                   "world_clip": [l[0] for l in layout], "world_rep": [l[1] for l in layout],
                   "world_cfg": [l[2] for l in layout], "horizon": T, "step_dt": 0.02,
                   "clip_len_s": [3.0] * len(clips), "seal": "SYNTHETIC", "seed": 0,
                   "checkpoint": "SYNTHETIC"}, open(os.path.join(tmp, "meta.json"), "w"))

    global windows_for
    real_windows = windows_for
    def _synth_windows(clip, dt, T, weight=327.0):
        return (np.arange(T) >= 40) & (np.arange(T) < 90), (np.arange(T) < 30)
    windows_for = _synth_windows
    try:
        for name, (air, ctlmm, nfx, expect) in {
            "PASS":        (8.0, 0.5, 12, True),
            "FAIL_gen":    (8.0, 0.5, 5, False),   # only 5/12 family clips carry the effect
            "FAIL_ctrl":   (8.0, 4.0, 12, False),  # controls contaminated
        }.items():
            with tempfile.TemporaryDirectory() as tmp:
                fabricate(tmp, air, ctlmm, nfx)
                v = run_analysis(tmp, quiet=True)
                got = v["verdict"]["PASS"]
                assert got == expect, (name, v["verdict"])
                print(f"  synthetic {name}: {v['verdict']} OK")
    finally:
        windows_for = real_windows
    print("P-SIGN synthetic dry-run: all 3 branches decide as sealed. No real data touched.")


def run_analysis(run, quiet=False):
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
    if quiet:
        return out
    print(json.dumps(out["verdict"], indent=1))
    for c, rec in out["clips"].items():
        if rec["family"]:
            a = rec.get("airborne"); s = rec.get("standing")
            print(f"  FAM {c[:46]:48s} air {a['S_mm']:+6.1f} [{a['ci_mm'][0]:+.1f},{a['ci_mm'][1]:+.1f}]  stand {s['S_mm'] if s else float('nan'):+6.1f}  i={rec['passes_i']} iii={rec['passes_iii']}" if a else f"  FAM {c}: no paired-alive airborne steps")
        else:
            w = rec.get("whole")
            print(f"  CTL {c[:46]:48s} whole {w['S_mm']:+6.1f} [{w['ci_mm'][0]:+.1f},{w['ci_mm'][1]:+.1f}]  ii={rec['passes_ii']}" if w else f"  CTL {c}: none")
    return out


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--synthetic":
        return synthetic()
    run_analysis(sys.argv[1])


if __name__ == "__main__":
    main()
