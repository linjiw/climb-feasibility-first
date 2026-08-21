#!/usr/bin/env python3
# =============================================================================
# tools/analyze_sat_at_fall.py -- PROVENANCE SCRIPT (added 2026-08-19)
#
# WHY THIS FILE EXISTS
#   reports/effort_sat_at_fall.json was hand-computed and shipped without a
#   generator, while being cited as measured evidence in three draft documents.
#   This script regenerates it from the primary rollout streams so the number
#   has a reproducible chain.  It writes to a NEW path and never touches the
#   original artifact.
#
# WHERE THE DEFINITIONS LIVE  (read these before changing anything here)
#   * effort_sat, the quantity being summarised:
#       tools/g1_clip44_gate.py, in rollout():
#           sat = (af.abs() >= 0.98 * frange[:, :, 1]).float().mean(dim=1)
#       -> per control step, per world: the FRACTION of the robot's 29
#          actuators whose |actuator_force| is at or above 98 % of the UPPER
#          bound of that actuator's forcerange.  Stored in
#          reports/G1/run0/arm{A,B,C}.npz under key "effort_sat", shape
#          (horizon=500, worlds=480) float32.  Per-actuator identity is
#          ALREADY REDUCED AWAY at write time and is not recoverable here.
#   * world layout / step_dt / clip order: reports/G1/run0/meta.json, written
#     by the same script (clip-major, then replicate, then config).
#   * the experiment itself: plan/PREREGISTRATION_G1_clip44.md
#   * companion provenance script for the other undocumented artifact:
#     tools/analyze_wasted_exposure.py
#
# CPU-only.  Loads .npz + .json, imports nothing that touches CUDA.
# =============================================================================
"""Regenerate the "saturation at fall" artifact from the G1 clip-#44 gate rollouts.

PAPER CLAIMS THIS SCRIPT BACKS
------------------------------
The artifact reports/effort_sat_at_fall.json is cited, as *measured*, by:

  paper/RESULTS_LOG.md:35
      "effort saturation: 0/29 actuators supported phase; 5/29 (17.2 %) at
       >=98 % force within 0.6 s of post-airborne contact, 8/8 replicates"
  paper/companion/companion_note_draft.md:230  (section 5b)
      "zero of 29 actuators saturate at any point in the supported phase;
       within 0.6 s of the post-airborne contact event, 5/29 actuators
       (wrists, waist) pin at >= 98 % of force range, in 8/8 replicates"
  paper/flagship/S6_screen_at_scale.md:55
      "saturates zero actuators until contact, then pins 5/29 at >= 98 % force
       range within 0.6 s, in 8/8 replicates"
  plan/PERFORMANCE_PAYOFF_PLAN.md:85  (section 3)
      "0 of 29 actuators saturate during the entire supported phase; within
       0.6 s of the post-airborne contact, 17 % of actuators (5/29 -- wrists,
       waist) pin at >= 98 % of force range in 8/8 replicates"

WHICH "SATURATION"?  (DEFINITION HAZARD -- READ THIS)
-----------------------------------------------------
Three mutually incompatible definitions of "saturation" are in circulation in
this project.  They are NOT interchangeable and must never be pooled, averaged,
or compared across scripts:

  (1) CLOSED-LOOP ACTUATOR SATURATION  <-- THE ONE THIS SCRIPT IMPLEMENTS
      tools/g1_clip44_gate.py:~242
          |actuator_force| >= 0.98 * actuator_forcerange[:, 1]
      Measured on a *policy-driven rollout* in the simulator.  It asks: is the
      realised motor command pinned against the model's force limit right now?
      Reported as a fraction of the 29 actuators, per control step, per world.
      Bounded in [0, 1].  Requires a trained policy and a simulation.

  (2) OPEN-LOOP INVERSE-DYNAMICS RATIO
      tools/n1_knee_id.py:~172   tau / limit > 1.0
      Computed by inverse dynamics on the *reference motion*, with no policy
      and no closed-loop simulation.  It asks: would tracking this reference
      exactly require more torque than the joint can produce?  Unbounded above
      (can be 3x), uses a strict > 1.0 threshold, not >= 0.98.  A clip can
      score high here while a policy never saturates in closed loop, because
      the policy simply fails to track the reference.

  (3) A THIRD DEFINITION IN THE SONIC CODEBASE
      Not implemented here and not reproduced here.  Do not cite (1) or (2)
      against SONIC numbers without first restating its definition.

This script implements (1) ONLY, on stored rollout output.  Numbers it emits
must be labelled "closed-loop actuator saturation" wherever they are cited.

WHAT IT COMPUTES
----------------
For a selected clip x arm x world-config group (default: clip #44, arm A,
config "base" -> the 8 replicate worlds), and for each world independently:

  sat_frac_max_pre     max over the SUPPORTED window of effort_sat
  sat_frac_max_fall    max over the FALL window of effort_sat

then the across-world mean of each.  Two window conventions are reported side
by side because the original artifact used the first and the papers describe
the second:

  A. FIXED (reproduces the cited artifact exactly)
       supported = t <  --pre-end     (default 2.0 s)
       fall      = --fall-start <= t <= --fall-end   (default 2.2 s .. 3.0 s)
     These bounds are hard-coded constants; nothing in the primary data derives
     them.  They are the literal keys of the shipped JSON
     ("sat_frac_max_pre2s", "sat_frac_max_fall_2.2-3.0s").

  B. CONTACT-DERIVED (robustness check, per world)
       support-loss onset = the earliest alive control step from which the
         forward foot-contact duty cycle (fraction of the next --duty-window
         seconds with >=1 foot geom in contact) stays below --duty-threshold
         all the way to episode termination.  Foot contact is the "contact"
         stream of the same .npz (left foot, right foot booleans).
       supported = alive steps strictly before that onset
       fall      = onset .. onset + --fall-horizon (default 0.6 s), clipped at
                   termination
     This is what the prose "within 0.6 s of the post-airborne contact event"
     actually describes -- except that the detected event is support LOSS, not
     a landing: in this rollout every replicate terminates while still
     descending, so no landing contact exists in the data.

Frames after episode termination are excluded by default (--alive-only).  The
gate harness keeps stepping terminated worlds because other clips in the same
batch are still alive, so post-termination samples belong to a fresh, reset
episode and are not part of the fall.

Determinism: pure arithmetic over stored arrays, no RNG, no sorting by dict
order.  Repeated runs on the same inputs are bit-identical.

USAGE
    tools/analyze_sat_at_fall.py                       # defaults reproduce the artifact
    tools/analyze_sat_at_fall.py --out /tmp/x.json --arm C
    tools/analyze_sat_at_fall.py --compare reports/effort_sat_at_fall.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEF_RUN = os.path.join(REPO, "reports", "G1", "run0")
DEF_OUT = os.path.join(REPO, "reports", "effort_sat_at_fall_regen.json")
DEF_CITED = os.path.join(REPO, "reports", "effort_sat_at_fall.json")

# The G1 gate ran 6 clips; index 0 of plan/G1_clips.txt is
# BMLmovi_Subject_64_F_MoSh_Subject_64_F_9_poses_120_jpos, which is index 44 of
# bank/tiers/tier_mixed100.txt -- "clip #44" throughout the papers.
DEF_CLIP = "BMLmovi_Subject_64_F_MoSh_Subject_64_F_9_poses_120_jpos"


def support_loss_onset(contact_any: np.ndarray, death: int, w_steps: int,
                       duty_thresh: float) -> int:
    """Earliest alive step from which foot-support duty stays below threshold.

    contact_any : (T,) bool, True when >=1 foot geom is in contact
    death       : first terminated step (== T if the world never terminated)
    Returns `death` if support is never lost.
    """
    if death <= 0:
        return 0
    c = contact_any[:death].astype(np.float64)
    duty = np.empty(death, dtype=np.float64)
    for k in range(death):
        duty[k] = c[k:min(k + w_steps, death)].mean()
    onset = death
    for k in range(death - 1, -1, -1):
        if duty[k] < duty_thresh:
            onset = k
        else:
            break
    return onset


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", default=DEF_RUN,
                    help="G1 gate output dir holding meta.json and arm*.npz "
                         f"(default: {DEF_RUN})")
    ap.add_argument("--arm", default="A", choices=["A", "B", "C"],
                    help="A = Newton/MJWarp interventions, B = condim+, "
                         "C = stock mjlab noise floor (default: A)")
    ap.add_argument("--clip", default=DEF_CLIP,
                    help="clip name as listed in meta.json['clips'] "
                         "(default: the clip the papers call #44)")
    ap.add_argument("--config", default="base",
                    help="world config to select, e.g. base, motor+, fric- "
                         "(default: base -> the 8 unperturbed replicates)")
    ap.add_argument("--n-actuators", type=int, default=29,
                    help="actuator count used only to render fractions as k/N "
                         "in the human-readable output (default: 29)")
    # --- fixed-window convention (reproduces the shipped artifact) ---
    ap.add_argument("--pre-end", type=float, default=2.0,
                    help="supported window is t < PRE_END seconds (default: 2.0)")
    ap.add_argument("--fall-start", type=float, default=2.2,
                    help="fall window starts at this time in seconds (default: 2.2)")
    ap.add_argument("--fall-end", type=float, default=3.0,
                    help="fall window ends at this time, inclusive (default: 3.0)")
    # --- contact-derived convention (robustness check) ---
    ap.add_argument("--fall-horizon", type=float, default=0.6,
                    help="length of the fall window measured from the detected "
                         "support-loss onset, in seconds (default: 0.6, the "
                         "figure the prose quotes)")
    ap.add_argument("--duty-window", type=float, default=0.2,
                    help="forward window for the foot-contact duty cycle used "
                         "to detect support loss, in seconds (default: 0.2)")
    ap.add_argument("--duty-threshold", type=float, default=0.5,
                    help="duty cycle below which support counts as lost "
                         "(default: 0.5)")
    ap.add_argument("--alive-only", dest="alive_only", action="store_true",
                    default=True, help="mask out post-termination steps (default)")
    ap.add_argument("--no-alive-only", dest="alive_only", action="store_false",
                    help="include post-termination steps (these belong to the "
                         "reset episode; only for diagnosing the original)")
    ap.add_argument("--compare", nargs="?", const=DEF_CITED, default=None,
                    help="also diff against a cited artifact JSON "
                         f"(bare flag uses {DEF_CITED})")
    ap.add_argument("--out", default=DEF_OUT,
                    help=f"output JSON path (default: {DEF_OUT}). Refuses to "
                         "overwrite the cited artifact.")
    args = ap.parse_args()

    if os.path.abspath(args.out) == os.path.abspath(DEF_CITED):
        print("refusing to overwrite the cited artifact; pick another --out",
              file=sys.stderr)
        return 2

    meta = json.load(open(os.path.join(args.run, "meta.json")))
    dt = float(meta["step_dt"])
    clips = meta["clips"]
    if args.clip not in clips:
        print(f"clip {args.clip!r} not in {clips}", file=sys.stderr)
        return 2
    ci = clips.index(args.clip)

    npz = np.load(os.path.join(args.run, f"arm{args.arm}.npz"))
    sat_all = npz["effort_sat"]                 # (T, W) float32
    alive_all = npz["alive"]                    # (T, W) bool
    con_all = npz["contact"]                    # (T, W, 2) bool
    T = sat_all.shape[0]
    t = np.arange(T) * dt

    wc = np.asarray(meta["world_clip"])
    wcfg = np.asarray(meta["world_cfg"])
    wrep = np.asarray(meta["world_rep"])
    sel = np.flatnonzero((wc == ci) & (wcfg == args.config))
    if sel.size == 0:
        print(f"no worlds for clip idx {ci} config {args.config!r}", file=sys.stderr)
        return 2
    order = np.argsort(wrep[sel], kind="stable")     # replicate order, deterministic
    sel = sel[order]

    sat = sat_all[:, sel]
    alive = alive_all[:, sel]
    con = con_all[:, sel].any(axis=-1)
    nW = sel.size
    N = args.n_actuators

    death = np.array([int(np.argmax(~alive[:, j])) if (~alive[:, j]).any() else T
                      for j in range(nW)])

    def wmax(j, lo, hi):
        """max effort_sat for world j over integer step range [lo, hi)."""
        hi = min(hi, death[j]) if args.alive_only else min(hi, T)
        if hi <= lo:
            return 0.0, None
        seg = sat[lo:hi, j]
        return float(seg.max()), int(lo + int(seg.argmax()))

    # ---------------- convention A: fixed windows (the shipped artifact) -----
    pre_hi = int(np.searchsorted(t, args.pre_end, side="left"))
    f_lo = int(np.searchsorted(t, args.fall_start, side="left"))
    f_hi = int(np.searchsorted(t, args.fall_end, side="right"))
    fixed_pre, fixed_fall, fixed_fall_arg = [], [], []
    for j in range(nW):
        v, _ = wmax(j, 0, pre_hi)
        fixed_pre.append(v)
        v, k = wmax(j, f_lo, f_hi)
        fixed_fall.append(v)
        fixed_fall_arg.append(k)

    # ---------------- convention B: contact-derived --------------------------
    w_steps = max(1, int(round(args.duty_window / dt)))
    h_steps = max(1, int(round(args.fall_horizon / dt)))
    onset = np.array([support_loss_onset(con[:, j], int(death[j]), w_steps,
                                         args.duty_threshold) for j in range(nW)])
    cd_pre, cd_fall = [], []
    for j in range(nW):
        v, _ = wmax(j, 0, int(onset[j]))
        cd_pre.append(v)
        v, _ = wmax(j, int(onset[j]), int(onset[j]) + h_steps)
        cd_fall.append(v)

    def blk(pre, fall):
        pre = np.asarray(pre, dtype=np.float64)
        fall = np.asarray(fall, dtype=np.float64)
        return {
            "sat_frac_max_pre": [float(x) for x in pre],
            "sat_frac_max_fall": [float(x) for x in fall],
            "n_actuators_pre": [int(round(x * N)) for x in pre],
            "n_actuators_fall": [int(round(x * N)) for x in fall],
            "mean_pre": float(pre.mean()),
            "mean_fall": float(fall.mean()),
            "worlds_at_5_of_29_fall": int(sum(round(x * N) == 5 for x in fall)),
            "worlds_with_any_fall_saturation": int((fall > 0).sum()),
            "worlds_with_any_pre_saturation": int((pre > 0).sum()),
        }

    out = {
        "_script": "tools/analyze_sat_at_fall.py",
        "_regenerates": "reports/effort_sat_at_fall.json",
        "_saturation_definition": (
            "closed-loop actuator saturation: |actuator_force| >= 0.98 * "
            "actuator_forcerange upper bound, fraction of 29 actuators, per "
            "control step (tools/g1_clip44_gate.py rollout()). NOT the "
            "open-loop tau/limit > 1.0 definition of tools/n1_knee_id.py, and "
            "NOT the SONIC definition. The three are not interchangeable."
        ),
        "inputs": {
            "run_dir": os.path.relpath(args.run, REPO),
            "arm": args.arm,
            "clip": args.clip,
            "clip_index_in_gate": ci,
            "config": args.config,
            "worlds": [int(x) for x in sel],
            "replicates": [int(x) for x in wrep[sel]],
            "step_dt": dt,
            "horizon_steps": T,
            "checkpoint": meta.get("checkpoint"),
            "alive_only": bool(args.alive_only),
        },
        "termination": {
            "death_step": [int(x) for x in death],
            "death_time_s": [round(float(x * dt), 4) for x in death],
            "all_worlds_terminate_before_fall_window_end":
                bool((death * dt <= args.fall_end).all()),
        },
        "fixed_window": {
            "definition": (f"supported: t < {args.pre_end} s; "
                           f"fall: {args.fall_start} s <= t <= {args.fall_end} s "
                           "(hard-coded constants, matching the shipped artifact's keys)"),
            "argmax_step_fall": fixed_fall_arg,
            "argmax_time_fall_s": [None if k is None else round(k * dt, 4)
                                   for k in fixed_fall_arg],
            **blk(fixed_pre, fixed_fall),
        },
        "contact_derived_window": {
            "definition": (
                f"support-loss onset = earliest alive step from which the foot-contact "
                f"duty cycle over the next {args.duty_window} s stays < {args.duty_threshold} "
                f"until termination; supported: steps before onset; "
                f"fall: onset .. onset + {args.fall_horizon} s, clipped at termination"),
            "support_loss_onset_step": [int(x) for x in onset],
            "support_loss_onset_time_s": [round(float(x * dt), 4) for x in onset],
            **blk(cd_pre, cd_fall),
        },
        "not_recoverable_from_this_artifact": [
            "which actuators saturate (the papers say 'wrists, waist'): "
            "g1_clip44_gate.py reduces over the actuator axis with .mean(dim=1) "
            "before storing, so per-actuator identity is absent from the .npz. "
            "Verifying that phrase requires a new GPU rollout.",
            "a landing/touchdown contact event: every replicate terminates while "
            "root_z is still decreasing, so the data contain no post-airborne "
            "landing contact.",
        ],
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=False)
        fh.write("\n")

    fw, cd = out["fixed_window"], out["contact_derived_window"]
    print(f"[sat-at-fall] {args.clip[:46]}  arm {args.arm}  config {args.config}  "
          f"{nW} worlds")
    print(f"  definition: closed-loop |tau| >= 0.98 * forcerange_hi, fraction of {N}")
    print(f"  FIXED   pre (t<{args.pre_end}s)   max/world {fw['n_actuators_pre']} /{N}"
          f"   mean {fw['mean_pre']:.17f}")
    print(f"  FIXED   fall ({args.fall_start}-{args.fall_end}s) max/world "
          f"{fw['n_actuators_fall']} /{N}   mean {fw['mean_fall']:.17f}")
    print(f"  CONTACT pre  (t<onset)     max/world {cd['n_actuators_pre']} /{N}"
          f"   mean {cd['mean_pre']:.17f}")
    print(f"  CONTACT fall (onset+{args.fall_horizon}s) max/world "
          f"{cd['n_actuators_fall']} /{N}   mean {cd['mean_fall']:.17f}")
    print(f"  support-loss onset (s): {cd['support_loss_onset_time_s']}")
    print(f"  termination      (s): {out['termination']['death_time_s']}")

    if args.compare:
        cited = json.load(open(args.compare))
        key = next(iter(cited))
        c = cited[key]
        print(f"\n  --- diff vs {os.path.relpath(args.compare, REPO)} [{key}] ---")
        for ck, mine in (("sat_frac_max_pre2s", fw["sat_frac_max_pre"]),
                         ("sat_frac_max_fall_2.2-3.0s", fw["sat_frac_max_fall"])):
            if ck in c:
                a = np.asarray(c[ck], dtype=np.float64)
                b = np.asarray(mine, dtype=np.float64)
                if a.shape != b.shape:
                    print(f"  {ck}: SHAPE MISMATCH cited {a.shape} vs regen {b.shape}")
                else:
                    print(f"  {ck}: max |delta| = {np.abs(a - b).max():.3e} "
                          f"(cited rounded to 3 dp in the artifact)")
        for ck, mine in (("mean_pre", fw["mean_pre"]), ("mean_fall", fw["mean_fall"])):
            if ck in c:
                print(f"  {ck}: cited {c[ck]!r}  regen {mine!r}  "
                      f"delta {mine - float(c[ck]):+.3e}")

    print(f"\n  wrote {os.path.relpath(args.out, REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
