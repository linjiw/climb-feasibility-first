#!/usr/bin/env python3
"""Segment-level reducer over the dynamic-feasibility screen.

The bank-wide screen (`reports/feasibility_all/`) was run with `--brief`, so it kept only
per-clip scalars. Feasibility-grounded adaptive sampling (FGAS) needs the segment structure
underneath: which *parts* of a clip are trackable, and therefore which sampler bins may carry
failure priority. This module turns the screen's full (non-brief) per-frame output into

    severe_mask[T] -> guard-band expansion -> contiguous feasible segments -> m_b on a bin grid

and nothing else. It does no physics; `tools/n1_knee_id.py` owns that. Keeping the reduction
separate means the eligibility mask can be recomputed with a different guard band or bin grid
without paying for a re-screen.

Per-frame definitions are taken verbatim from n1_knee_id.py's own brief-mode reduction
(:213-228) so that `mean(severe_mask)` reconciles with the published `infeasible_frac`:

    tl[k] = tl_unsupported_force_N              when the torque-limited LP solved
          = unsupported_force_N                 when n_contacts == 0 (airborne: nothing to solve)
          = NaN                                 when the LP was infeasible *while in contact*
    infeasible[k]       = nan_to_num(tl) > 0.5 * W          (W = total mass * 9.81)
    torque_infeasible[k]= tl is None and n_contacts > 0
    airborne[k]         = n_contacts == 0

Note the asymmetry that inherits from the screen: a frame whose LP is infeasible *in contact*
scores 0 in `infeasible_frac` (NaN -> 0) but is counted in `torque_infeasible_frac`. For
eligibility we must not inherit that hole, so `severe = infeasible OR torque_infeasible`.
`--severity infeasible` reproduces the published scalar exactly if you need to reconcile.

GUARD BAND. A bin being feasible does not make an episode started there safe: the episode can
run forward into an infeasible window, and in a framework whose observation includes future
reference the policy is asked to represent that window before reaching it. The required width
is therefore framework-specific and is NOT a physics constant:

    mjlab   : observation is the current anchor only (`command`, `motion_anchor_pos_b`,
              `motion_anchor_ori_b`) -> no representational lookahead. Guard band covers only
              forward travel during an episode.
    SONIC   : `sonic_bones_seed.yaml` sets num_future_frames=10 x dt_future_ref_frames=0.1
              -> 1.0 s of future reference inside the observation (base default 5 x 0.1 = 0.5 s).
              Guard band must be >= that, or the encoder still sees impossible targets.

The default here is 0.0 (measure first, then choose). Pass --guard-s explicitly per framework.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys

import numpy as np

DEFAULT_BIN_FRAMES = 50  # SONIC's adaptive_sampling.bin_size, on the 50 Hz timeline
PRODUCTION_GAP_M = 0.06  # the gap the bank-wide screen used (tools/screen_feasibility.sh)


def sha256_file(path: str) -> str:
    """Hash a reducer input or implementation for provenance."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def per_frame(summary: dict, model: str = "real") -> dict:
    """Per-frame arrays from a full-mode n1_knee_id.py summary. Definitions above."""
    rows = summary["frames"]
    if not rows:
        raise ValueError(f"{summary.get('clip')}: full-mode output has no 'frames' array")
    weight_n = float(summary["total_mass_kg"]) * 9.81

    n_contacts = np.array([r["n_contacts"] for r in rows], dtype=int)
    unsup = np.array([r[model]["unsupported_force_N"] for r in rows], dtype=float)

    # Archived artifacts are not all one schema: reports/N1_clip44_knee_id.json carries the
    # torque-limited LP fields, reports/N1_CMU76_knee_id.json (older screen build) carries none
    # of them. Degrade explicitly rather than silently mixing two definitions -- the pre-LP
    # numbers are an UPPER bound on support (no actuator limits), so they are not comparable.
    has_tl = "tl_unsupported_force_N" in rows[0][model]
    if not has_tl:
        return {
            "t": np.array([r["t"] for r in rows], dtype=float),
            "airborne": n_contacts == 0,
            "infeasible": unsup > 0.5 * weight_n,
            "torque_infeasible": np.zeros(len(rows), dtype=bool),
            "unsupported_ratio": unsup / weight_n,
            "weight_N": weight_n,
            "schema": "pre_torque_limited",
        }
    tl_raw = [r[model]["tl_unsupported_force_N"] for r in rows]

    tl = np.array(
        [
            (tl_raw[k] if tl_raw[k] is not None else (unsup[k] if n_contacts[k] == 0 else np.nan))
            for k in range(len(rows))
        ],
        dtype=float,
    )
    torque_infeasible = np.array(
        [tl_raw[k] is None and n_contacts[k] > 0 for k in range(len(rows))], dtype=bool
    )
    tl0 = np.nan_to_num(tl, nan=0.0)
    return {
        "t": np.array([r["t"] for r in rows], dtype=float),
        "airborne": n_contacts == 0,
        "infeasible": tl0 > 0.5 * weight_n,
        "torque_infeasible": torque_infeasible,
        "unsupported_ratio": tl0 / weight_n,
        "weight_N": weight_n,
        "schema": "torque_limited",
    }


def dilate(mask: np.ndarray, half_width: int, mode: str = "symmetric") -> np.ndarray:
    """Widen True frames symmetrically or backward for future lookahead."""
    if mode not in ("symmetric", "backward"):
        raise ValueError("guard mode must be 'symmetric' or 'backward'")
    if half_width <= 0 or not mask.any():
        return mask.copy()
    out = mask.copy()
    (idx,) = np.nonzero(mask)
    for i in idx:
        stop = i + half_width + 1 if mode == "symmetric" else i + 1
        out[max(0, i - half_width) : stop] = True
    return out


def runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Contiguous [start, end) runs of True."""
    out, start = [], None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        elif not v and start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(mask)))
    return out


def bin_eligibility(feasible: np.ndarray, bin_frames: int, min_frac: float) -> np.ndarray:
    """m_b over a fixed-size bin grid: a bin is eligible iff >= min_frac of it is feasible.

    Mirrors the bin construction both samplers use (fixed-size bins from frame 0, a short
    final bin absorbing the remainder).
    """
    n = len(feasible)
    edges = list(range(0, n, bin_frames))
    return np.array([feasible[s : min(s + bin_frames, n)].mean() >= min_frac for s in edges], dtype=bool)


def reduce_clip(summary: dict, *, guard_s: float, min_seg_s: float, bin_frames: int,
                min_bin_frac: float, severity: str, model: str = "real",
                guard_mode: str = "symmetric") -> dict:
    pf = per_frame(summary, model=model)
    fps = float(summary["fps"])
    n = len(pf["t"])

    # Archived artifacts do not all share the production screen parameters. reports/
    # N1_clip44_knee_id.json was run at the production gap of 0.06 m; N1_CMU76_knee_id.json used
    # the argparse default 0.03 m, which registers 200/485 frames as contact-free against 62/496
    # -- a difference large enough to move infeasible_frac from a few percent to 41%. Eligibility
    # masks built from mixed-parameter artifacts are silently wrong, so say so.
    gap = float(summary.get("gap", float("nan")))
    if not (abs(gap - PRODUCTION_GAP_M) < 1e-9):
        print(f"WARNING {summary['clip']}: screened at gap={gap} m, not the production "
              f"{PRODUCTION_GAP_M} m. A tighter gap inflates the airborne (and hence infeasible) "
              f"fraction. Do not mix gaps within one eligibility mask.", file=sys.stderr)

    severe = pf["infeasible"] if severity == "infeasible" else (pf["infeasible"] | pf["torque_infeasible"])
    if pf["schema"] == "pre_torque_limited":
        print(f"WARNING {summary['clip']}: screen output predates the torque-limited LP; "
              f"feasibility is computed WITHOUT actuator limits and is an upper bound on "
              f"support. Not comparable to torque-limited clips. Re-screen to compare.",
              file=sys.stderr)
    guarded = dilate(severe, round(guard_s * fps), mode=guard_mode)
    feasible = ~guarded

    min_seg_frames = max(1, round(min_seg_s * fps))
    segs = [(a, b) for a, b in runs(feasible) if (b - a) >= min_seg_frames]
    kept = np.zeros(n, dtype=bool)
    for a, b in segs:
        kept[a:b] = True

    m_b = bin_eligibility(kept, bin_frames, min_bin_frac)
    segment_records = [
        {
            "start_frame": int(a),
            "stop_frame": int(b),
            "unsupported_ratio_mean": float(pf["unsupported_ratio"][a:b].mean()),
            "unsupported_ratio_p95": float(
                np.percentile(pf["unsupported_ratio"][a:b], 95)
            ),
            "unsupported_ratio_max": float(pf["unsupported_ratio"][a:b].max()),
        }
        for a, b in segs
    ]
    return {
        "clip": summary["clip"],
        "fps": fps,
        "frames": n,
        "guard_s": guard_s,
        "guard_mode": guard_mode,
        "min_seg_s": min_seg_s,
        "bin_frames": bin_frames,
        "severity": severity,
        "screen_schema": pf["schema"],
        "screen_gap_m": gap,
        "airborne_frac": float(pf["airborne"].mean()),
        "infeasible_frac": float(pf["infeasible"].mean()),
        "torque_infeasible_frac": float(pf["torque_infeasible"].mean()),
        "severe_frac": float(severe.mean()),
        "severe_frac_guarded": float(guarded.mean()),
        "feasible_frac_kept": float(kept.mean()),
        "n_severe_windows": len(runs(severe)),
        "n_feasible_segments": len(segs),
        "feasible_segments_frames": [[int(a), int(b)] for a, b in segs],
        "feasible_segment_records": segment_records,
        "feasible_segments_s": [[round(a / fps, 3), round(b / fps, 3)] for a, b in segs],
        "severe_windows_frames": [[int(a), int(b)] for a, b in runs(severe)],
        "guarded_severe_windows_frames": [
            [int(a), int(b)] for a, b in runs(guarded)
        ],
        "severe_windows_s": [[round(a / fps, 3), round(b / fps, 3)] for a, b in runs(severe)],
        "n_bins": len(m_b),
        "n_bins_eligible": int(m_b.sum()),
        "bin_eligible_frac": float(m_b.mean()) if len(m_b) else 0.0,
        "bin_eligible": m_b.astype(int).tolist(),
        "unsupported_ratio_p95": float(np.percentile(pf["unsupported_ratio"], 95)),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", nargs="+", required=True,
                    help="full-mode n1_knee_id.py output JSON(s) (NOT --brief output)")
    ap.add_argument("--guard-s", type=float, default=0.0,
                    help="guard band half-width in seconds. mjlab: 0 (no obs lookahead). "
                         "SONIC: >= 1.0 (num_future_frames*dt). Default 0 = measure first.")
    ap.add_argument("--guard-mode", choices=("symmetric", "backward"),
                    default="symmetric",
                    help="symmetric preserves the published reducer; backward expands only "
                         "before severe frames for forward-reference lookahead")
    ap.add_argument("--min-seg-s", type=float, default=1.0,
                    help="drop feasible segments shorter than this")
    ap.add_argument("--bin-frames", type=int, default=DEFAULT_BIN_FRAMES,
                    help=f"sampler bin size in frames (default {DEFAULT_BIN_FRAMES} = SONIC bin_size)")
    ap.add_argument("--min-bin-frac", type=float, default=1.0,
                    help="a bin is eligible iff at least this fraction of it is feasible "
                         "(1.0 = strict: any severe frame disqualifies the bin)")
    ap.add_argument("--severity", choices=("severe", "infeasible"), default="severe",
                    help="'severe' = infeasible OR torque-infeasible (default, closes the "
                         "in-contact LP hole); 'infeasible' reproduces the published scalar")
    ap.add_argument("--model", choices=("real", "sim"), default="real")
    ap.add_argument("--out-dir", default=None, help="write one JSON per clip here")
    ap.add_argument("--out-csv", default=None, help="write a one-row-per-clip summary CSV here")
    args = ap.parse_args()

    scalar_fields = [
        "clip", "fps", "frames", "guard_s", "guard_mode", "min_seg_s", "bin_frames", "severity",
        "source_screen_sha256", "reducer_sha256",
        "airborne_frac", "infeasible_frac", "torque_infeasible_frac", "severe_frac",
        "severe_frac_guarded", "feasible_frac_kept", "n_severe_windows",
        "screen_schema", "screen_gap_m", "n_feasible_segments", "n_bins", "n_bins_eligible", "bin_eligible_frac",
        "unsupported_ratio_p95",
    ]
    results = []
    for path in args.json:
        try:
            with open(path) as handle:
                summary = json.load(handle)
        except Exception as exc:  # noqa: BLE001
            print(f"SKIP {path}: {exc}", file=sys.stderr)
            continue
        if "frames" not in summary or not isinstance(summary.get("frames"), list):
            print(f"SKIP {path}: not full-mode output (no 'frames' array). "
                  f"Re-run n1_knee_id.py without --brief.", file=sys.stderr)
            continue
        res = reduce_clip(summary, guard_s=args.guard_s, min_seg_s=args.min_seg_s,
                          bin_frames=args.bin_frames, min_bin_frac=args.min_bin_frac,
                          severity=args.severity, model=args.model,
                          guard_mode=args.guard_mode)
        res["source_screen_sha256"] = sha256_file(path)
        res["reducer_sha256"] = sha256_file(__file__)
        results.append(res)
        if args.out_dir:
            os.makedirs(args.out_dir, exist_ok=True)
            out_path = os.path.join(args.out_dir, res["clip"] + ".json")
            with open(out_path, "w") as handle:
                json.dump(res, handle, indent=1)

    if not results:
        print("no usable input", file=sys.stderr)
        return 1

    for r in results:
        print(f"\n{r['clip']}  ({r['frames']} frames @ {r['fps']:.0f} Hz, guard {r['guard_s']}s)")
        print(f"  airborne {r['airborne_frac']:.3f}  infeasible {r['infeasible_frac']:.3f}  "
              f"torque-infeasible {r['torque_infeasible_frac']:.3f}  -> severe {r['severe_frac']:.3f}"
              f"  (guarded {r['severe_frac_guarded']:.3f})")
        print(f"  severe windows: {r['severe_windows_s']}")
        print(f"  feasible segments (>= {r['min_seg_s']}s): {r['feasible_segments_s']}")
        print(f"  bins eligible: {r['n_bins_eligible']}/{r['n_bins']} "
              f"({r['bin_eligible_frac']:.2f}) at bin_frames={r['bin_frames']}")

    if args.out_csv:
        with open(args.out_csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=scalar_fields)
            w.writeheader()
            for r in results:
                w.writerow({k: r[k] for k in scalar_fields})
        print(f"\nwrote {args.out_csv} ({len(results)} clips)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
