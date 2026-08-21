#!/usr/bin/env python3
# =============================================================================
# tools/analyze_wasted_exposure.py -- PROVENANCE SCRIPT (added 2026-08-19)
#
# WHY THIS FILE EXISTS
#   reports/wasted_exposure_accounting.json was hand-computed and shipped
#   without a generator, while being cited as measured evidence in four draft
#   documents (including a Contributions bullet).  This script regenerates it
#   from primary data and writes to a NEW path; it never touches the original.
#
# WHERE THE DEFINITIONS LIVE  (read these before changing anything here)
#   * infeasible_frac, the per-clip screen output:
#       reports/feasibility_all/feasibility.csv  (10,705 clips, whole bank)
#       reports/feasibility_e3/feasibility.csv   (979 clips, E3 subset)
#       column "infeasible_frac" = share of a clip's frames the offline screen
#       marks physically infeasible.  Flag rule used by the shipped prevalence
#       table (reports/feasibility_all/prevalence_report.txt, ">10% infeasible"
#       column) is infeasible_frac > 0.10.
#   * the sampler telemetry:
#       climb/commands.py:159-160  (READ ONLY -- live-imported by training)
#           sampling_top1_prob = p.max()                       # max over clips
#           sampling_top1_bin  = p.argmax() / num_clips        # WHICH clip
#       logged once per training iteration into logs/campaign/<run>.log as
#           Metrics/motion/sampling_top1_prob:  <float>
#           Metrics/motion/sampling_top1_bin:   <float>
#       (Metrics/motion/sampling_clip_top1_prob is the same number under a
#       second name; this script reads the un-prefixed one.)
#   * the intermediate artifact the shipped JSON actually copied from:
#       reports/A5_coverage_dose.json, produced by tools/analyze_coverage_dose.py
#       fields mean_top1 / max_top1 per (arm, seed).
#   * companion provenance script for the other undocumented artifact:
#       tools/analyze_sat_at_fall.py
#
# CPU-only.  Reads CSV/JSON/plain-text logs; imports nothing that touches CUDA.
# =============================================================================
"""Regenerate the wasted-exposure ledger: how much sampling mass goes to flagged content.

PAPER CLAIMS THIS SCRIPT BACKS
------------------------------
The artifact reports/wasted_exposure_accounting.json is cited, as *measured*, by:

  paper/RESULTS_LOG.md:34
      "wasted exposure: adaptive mean 48.8 % of clip draws to the impossible
       clip (peak 87-89 %); clip-uniform 25 % draws / 6.1 % frames to flagged
       (mixed100); bank 22.8 % clips / 27.4 % duration / 9.8 % mean frames"
  paper/flagship/S1_intro.md:73-75   (Contribution 1)
      "the shipped sampler spends a mean 48.8 % of all clip draws (peak
       87-89 %) on a single impossible clip"
  paper/companion/companion_note_draft.md:197-198   (section 8)
      "a failure-weighted sampler spent a mean 48.8 % of its draws on one
       impossible clip"
  plan/PERFORMANCE_PAYOFF_PLAN.md:10-16   (section 0, the efficiency ledger)
      the three-row table reproduced by the three blocks below.

METRIC DEFINITIONS
------------------
TIER BLOCK  (default tier: bank/tiers/tier_mixed100.txt, 100 clips)
  flagged_clips
      count of tier clips with infeasible_frac > --flag-threshold (0.10).
  clip_draw_share_to_flagged
      flagged_clips / n_clips.  This is the share of DRAWS only under a
      clip-uniform sampler, which is exactly the arm it is quoted for.  It is
      a property of the bank composition, not a measurement of any run.
  expected_infeasible_frame_share_clip_uniform
      unweighted mean of infeasible_frac over the tier = expected share of a
      drawn FRAME being infeasible when each clip is equally likely to be drawn
      and each clip contributes its whole timeline.
  infeasible_frame_share_duration_weighted
      sum(infeasible_frac * frames) / sum(frames): the same quantity when draw
      probability is proportional to clip duration.  (Every clip in this bank
      is at 50 fps, so frame-weighting and second-weighting coincide; the
      script reports both so that stops being an accident.)

BANK BLOCK  (default: reports/feasibility_all/feasibility.csv, 10,705 clips)
  flagged_clip_share, flagged_duration_share, mean_infeasible_frame_share
      the same three quantities over the whole screened bank.

ADAPTIVE BLOCK  (from the training logs, 3 seeds x 4,000 iterations)
  mean_top1_mass
      mean over logged iterations, then over seeds, of sampling_top1_prob =
      max_c P(clip = c).  This is "how concentrated the sampler was", and it is
      IDENTITY-BLIND: the clip holding the maximum changes over training.
  top1_identity_share_attractor
      fraction of logged iterations whose argmax clip is --attractor-index.
  attractor_mass_lower_bound
      mean over iterations of sampling_top1_prob * 1[argmax == attractor].
      This IS a share of draws going to the named clip -- a LOWER bound,
      because the attractor can hold mass in iterations where some other clip
      is the argmax.  The upper bound is mean_top1_mass.  The telemetry logs
      only the argmax and its probability, never the full probability vector,
      so the true share cannot be pinned down from data on disk.
  peak_top1_mass / peak_top1_clip
      max over iterations of sampling_top1_prob, and which clip held it.

DEFINITION HAZARD CARRIED IN FROM THE SIBLING SCRIPT
----------------------------------------------------
"infeasible_frac" here is the OFFLINE KINEMATIC/CONTACT SCREEN's per-frame
infeasibility share.  It is a different quantity from every "saturation"
measure in this repo, and those are three mutually incompatible things in
their own right:
  (1) closed-loop actuator saturation, |actuator_force| >= 0.98 * forcerange
      upper bound -- tools/g1_clip44_gate.py:~242, summarised by
      tools/analyze_sat_at_fall.py;
  (2) open-loop inverse-dynamics ratio tau/limit > 1.0 --
      tools/n1_knee_id.py:~172, computed on the reference with no policy;
  (3) a third definition in the SONIC codebase, not implemented here.
None of (1)-(3) may be substituted for infeasible_frac, nor for each other.

Determinism: fixed file order, fixed seed order, no RNG, no dict iteration
over unsorted keys.  Repeated runs on the same inputs are bit-identical.

USAGE
    tools/analyze_wasted_exposure.py                     # defaults reproduce the artifact
    tools/analyze_wasted_exposure.py --feasibility reports/feasibility_e3/feasibility.csv
    tools/analyze_wasted_exposure.py --compare
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEF_FEAS = os.path.join(REPO, "reports", "feasibility_all", "feasibility.csv")
DEF_TIER = os.path.join(REPO, "bank", "tiers", "tier_mixed100.txt")
DEF_LOGS = os.path.join(REPO, "logs", "campaign")
DEF_OUT = os.path.join(REPO, "reports", "wasted_exposure_accounting_regen.json")
DEF_CITED = os.path.join(REPO, "reports", "wasted_exposure_accounting.json")

# NB: the negative lookbehind keeps this from also matching
# "Metrics/motion/sampling_clip_top1_prob", which carries the same value.
RE_TOP1P = re.compile(r"(?<!_)sampling_top1_prob:\s*([0-9.]+)")
RE_TOP1B = re.compile(r"sampling_top1_bin:\s*([0-9.]+)")


def read_feasibility(path: str) -> dict:
    out = {}
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            out[r["clip"]] = (float(r["infeasible_frac"]), float(r["frames"]),
                              float(r["fps"]))
    return out


def shares(inf: np.ndarray, frames: np.ndarray, fps: np.ndarray,
           thr: float, op: str) -> dict:
    flag = (inf >= thr) if op == "ge" else (inf > thr)
    dur = frames / fps
    return {
        "n_clips": int(inf.size),
        "flagged_clips": int(flag.sum()),
        "flagged_clip_share": float(flag.mean()),
        "flagged_frame_share": float(frames[flag].sum() / frames.sum()),
        "flagged_duration_share": float(dur[flag].sum() / dur.sum()),
        "mean_infeasible_frame_share": float(inf.mean()),
        "infeasible_frame_share_frame_weighted": float((inf * frames).sum() / frames.sum()),
        "infeasible_frame_share_duration_weighted": float((inf * dur).sum() / dur.sum()),
    }


def sampler_series(log_path: str):
    """(top1_prob, top1_bin) aligned per logged training iteration."""
    p, b = [], []
    with open(log_path, errors="ignore") as fh:
        for line in fh:
            m = RE_TOP1B.search(line)
            if m:
                b.append(float(m.group(1)))
                continue
            m = RE_TOP1P.search(line)
            if m:
                p.append(float(m.group(1)))
    n = min(len(p), len(b))
    return np.asarray(p[:n], dtype=np.float64), np.asarray(b[:n], dtype=np.float64)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--feasibility", default=DEF_FEAS,
                    help="screen output CSV with an infeasible_frac column "
                         f"(default: {DEF_FEAS}; the E3 subset lives at "
                         "reports/feasibility_e3/feasibility.csv and carries "
                         "identical rows for every tier_mixed100 clip)")
    ap.add_argument("--tier", default=DEF_TIER,
                    help=f"clip list for the tier block (default: {DEF_TIER})")
    ap.add_argument("--flag-threshold", type=float, default=0.10,
                    help="a clip is flagged when infeasible_frac crosses this "
                         "(default: 0.10, the '>10%% infeasible' rule of "
                         "reports/feasibility_all/prevalence_report.txt)")
    ap.add_argument("--flag-op", choices=["gt", "ge"], default="gt",
                    help="strict > (default, reproduces the prevalence table) "
                         "or >= (reproduces the repair census's 2,443 count)")
    ap.add_argument("--logs", default=DEF_LOGS,
                    help=f"training log dir (default: {DEF_LOGS})")
    ap.add_argument("--arm", default="adaptive",
                    help="log filename arm prefix (default: adaptive)")
    ap.add_argument("--bank-tag", default="mixed100",
                    help="log filename bank tag (default: mixed100)")
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3],
                    help="seeds to pool, in this order (default: 1 2 3)")
    ap.add_argument("--attractor-index", type=int, default=44,
                    help="0-based index in --tier of the clip the papers call "
                         "'the impossible clip' (default: 44)")
    ap.add_argument("--compare", nargs="?", const=DEF_CITED, default=None,
                    help=f"diff against a cited artifact (bare flag uses {DEF_CITED})")
    ap.add_argument("--out", default=DEF_OUT,
                    help=f"output JSON path (default: {DEF_OUT}). Refuses to "
                         "overwrite the cited artifact.")
    args = ap.parse_args()

    if os.path.abspath(args.out) == os.path.abspath(DEF_CITED):
        print("refusing to overwrite the cited artifact; pick another --out",
              file=sys.stderr)
        return 2

    feas = read_feasibility(args.feasibility)
    tier = [ln.strip() for ln in open(args.tier) if ln.strip()]
    missing = [c for c in tier if c not in feas]
    if missing:
        print(f"{len(missing)} tier clips absent from {args.feasibility}: "
              f"{missing[:3]}", file=sys.stderr)
        return 2

    tv = np.asarray([feas[c] for c in tier], dtype=np.float64)
    tier_blk = shares(tv[:, 0], tv[:, 1], tv[:, 2], args.flag_threshold, args.flag_op)
    tier_blk["clip_draw_share_to_flagged"] = tier_blk["flagged_clip_share"]
    tier_blk["expected_infeasible_frame_share_clip_uniform"] = \
        tier_blk["mean_infeasible_frame_share"]

    bank_names = sorted(feas)                      # deterministic order
    bv = np.asarray([feas[c] for c in bank_names], dtype=np.float64)
    bank_blk = shares(bv[:, 0], bv[:, 1], bv[:, 2], args.flag_threshold, args.flag_op)

    # ---- sampler telemetry --------------------------------------------------
    n_clips = len(tier)
    per_seed, missing_logs = {}, []
    for s in args.seeds:
        lp = os.path.join(args.logs, f"{args.arm}-{args.bank_tag}-s{s}.log")
        if not os.path.exists(lp):
            missing_logs.append(lp)
            continue
        p, b = sampler_series(lp)
        if p.size == 0:
            missing_logs.append(lp)
            continue
        idx = np.rint(b * n_clips).astype(int)     # bin was logged as argmax/num_clips
        is_att = idx == args.attractor_index
        k = int(p.argmax())
        per_seed[str(s)] = {
            "log": os.path.relpath(lp, REPO),
            "iterations_logged": int(p.size),
            "mean_top1_mass": float(p.mean()),
            "peak_top1_mass": float(p.max()),
            "peak_top1_clip_index": int(idx[k]),
            "peak_top1_is_attractor": bool(is_att[k]),
            "top1_identity_share_attractor": float(is_att.mean()),
            "attractor_mass_lower_bound": float((p * is_att).mean()),
            "peak_top1_mass_while_attractor_is_top1":
                float(p[is_att].max()) if is_att.any() else 0.0,
            "mean_top1_mass_while_attractor_is_top1":
                float(p[is_att].mean()) if is_att.any() else 0.0,
            "n_distinct_top1_clips": int(np.unique(idx).size),
        }

    def across(key):
        vals = [per_seed[str(s)][key] for s in args.seeds if str(s) in per_seed]
        return float(np.mean(vals)) if vals else None

    adaptive_blk = {
        "per_seed": per_seed,
        "mean_top1_mass": across("mean_top1_mass"),
        "peak_top1_mass_per_seed": [per_seed[str(s)]["peak_top1_mass"]
                                    for s in args.seeds if str(s) in per_seed],
        "attractor_clip_index": args.attractor_index,
        "attractor_clip": tier[args.attractor_index] if args.attractor_index < len(tier) else None,
        "top1_identity_share_attractor": across("top1_identity_share_attractor"),
        "attractor_mass_lower_bound": across("attractor_mass_lower_bound"),
        "attractor_mass_upper_bound": across("mean_top1_mass"),
        "note": (
            "mean_top1_mass is identity-blind: it is the mean of max_c P(c), "
            "pooled over whichever clip held the maximum at each iteration. "
            "The share attributable to the attractor clip is bracketed by "
            "[attractor_mass_lower_bound, attractor_mass_upper_bound]; the "
            "sampler telemetry logs only the argmax and its probability, so "
            "the exact share is not recoverable from data on disk."
        ),
    }
    if missing_logs:
        adaptive_blk["missing_logs"] = [os.path.relpath(x, REPO) for x in missing_logs]

    out = {
        "_script": "tools/analyze_wasted_exposure.py",
        "_regenerates": "reports/wasted_exposure_accounting.json",
        "inputs": {
            "feasibility_csv": os.path.relpath(args.feasibility, REPO),
            "tier": os.path.relpath(args.tier, REPO),
            "flag_rule": f"infeasible_frac {'>=' if args.flag_op == 'ge' else '>'} "
                         f"{args.flag_threshold}",
            "logs": os.path.relpath(args.logs, REPO),
            "arm": args.arm,
            "seeds": list(args.seeds),
        },
        "tier": tier_blk,
        "bank": bank_blk,
        "adaptive": adaptive_blk,
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=False)
        fh.write("\n")

    t, bk, ad = tier_blk, bank_blk, adaptive_blk
    print(f"[wasted-exposure] flag rule: {out['inputs']['flag_rule']}")
    print(f"  TIER {os.path.basename(args.tier)} (n={t['n_clips']}): "
          f"flagged {t['flagged_clips']}  clip-uniform draw share "
          f"{t['clip_draw_share_to_flagged']:.6f}")
    print(f"       E[infeasible frame | clip-uniform] "
          f"{t['expected_infeasible_frame_share_clip_uniform']:.17f}")
    print(f"       duration-weighted                 "
          f"{t['infeasible_frame_share_duration_weighted']:.17f}")
    print(f"  BANK (n={bk['n_clips']}): flagged clips {bk['flagged_clips']} "
          f"({bk['flagged_clip_share']:.6f})  duration {bk['flagged_duration_share']:.6f}  "
          f"mean frames {bk['mean_infeasible_frame_share']:.17f}")
    print(f"  ADAPTIVE ({len(per_seed)} seeds): mean_top1_mass "
          f"{ad['mean_top1_mass']!r}   peaks {ad['peak_top1_mass_per_seed']}")
    print(f"       attractor = #{ad['attractor_clip_index']} {str(ad['attractor_clip'])[:40]}")
    print(f"       top-1 identity share on attractor "
          f"{ad['top1_identity_share_attractor']:.4f}")
    print(f"       mass to attractor bracketed [{ad['attractor_mass_lower_bound']:.6f}, "
          f"{ad['attractor_mass_upper_bound']:.6f}]")
    for s in args.seeds:
        if str(s) in per_seed:
            d = per_seed[str(s)]
            print(f"         s{s}: mean_top1 {d['mean_top1_mass']:.6f}  peak "
                  f"{d['peak_top1_mass']:.4f} held by clip #{d['peak_top1_clip_index']}"
                  f"{' (attractor)' if d['peak_top1_is_attractor'] else ''}  "
                  f"attractor top-1 in {d['top1_identity_share_attractor']:.1%} of iters  "
                  f"lower-bound mass {d['attractor_mass_lower_bound']:.6f}")

    if args.compare:
        cited = json.load(open(args.compare))
        print(f"\n  --- diff vs {os.path.relpath(args.compare, REPO)} ---")
        pairs = [
            ("mixed100.flagged_clips", cited.get("mixed100", {}).get("flagged_clips"),
             t["flagged_clips"]),
            ("mixed100.clip_draw_share_to_flagged",
             cited.get("mixed100", {}).get("clip_draw_share_to_flagged"),
             t["clip_draw_share_to_flagged"]),
            ("mixed100.expected_infeasible_frame_share_clip_uniform",
             cited.get("mixed100", {}).get("expected_infeasible_frame_share_clip_uniform"),
             t["expected_infeasible_frame_share_clip_uniform"]),
            ("mixed100.infeasible_frame_share_duration_weighted",
             cited.get("mixed100", {}).get("infeasible_frame_share_duration_weighted"),
             t["infeasible_frame_share_duration_weighted"]),
            ("bank.flagged_clip_share", cited.get("bank", {}).get("flagged_clip_share"),
             bk["flagged_clip_share"]),
            ("bank.flagged_duration_share",
             cited.get("bank", {}).get("flagged_duration_share"),
             bk["flagged_duration_share"]),
            ("bank.mean_infeasible_frame_share",
             cited.get("bank", {}).get("mean_infeasible_frame_share"),
             bk["mean_infeasible_frame_share"]),
            ("adaptive.mean_top1_mass", cited.get("adaptive", {}).get("mean_top1_mass"),
             ad["mean_top1_mass"]),
            ("adaptive.exposure_to_impossible_clip_mean",
             cited.get("adaptive", {}).get("exposure_to_impossible_clip_mean"),
             ad["attractor_mass_lower_bound"]),
        ]
        for name, c, r in pairs:
            if c is None:
                print(f"  {name}: absent from cited artifact")
                continue
            d = float(r) - float(c)
            tag = "OK" if abs(d) < 1e-12 else ("rounding" if abs(d) < 6e-4 else "**DIFFERS**")
            print(f"  {name}: cited {c!r}  regen {r!r}  delta {d:+.4e}  [{tag}]")
        print("  NOTE adaptive.exposure_to_impossible_clip_mean is compared against the "
              "LOWER bound; the cited artifact set it equal to mean_top1_mass, which is "
              "the UPPER bound and is identity-blind.")

    print(f"\n  wrote {os.path.relpath(args.out, REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
