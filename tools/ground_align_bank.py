#!/usr/bin/env python3
"""Shift motion clips vertically so the feet rest on the floor.

The AMASS retargets in ``train_converted_complete`` store the root height
*relative* to the standing pose -- root z averages -0.004 m, against 0.767 m for
the LAFAN1 retargets in the same schema. Converted as-is, the G1 is buried to
the pelvis: shins sit 0.5 m below the floor plane and a "Stand" clip reports
0.79 m of penetration. Nothing in mjlab checks this, and the body-order
validator passes such files because the ordering is fine -- only the height is
wrong.

The correction is a rigid vertical translation, so it can be applied to finished
npz rather than by re-converting: shifting the root in z moves every body by the
same amount and leaves joint angles, orientations and all velocities untouched.
The offset is self-calibrating per clip -- the 1st percentile of the lower
foot's clearance, so a clip with genuine flight phases is still aligned on its
touchdowns rather than on its apex.

Idempotent: a clip already within tolerance is left alone.

Usage:
    ground_align_bank.py --bank DIR [--tolerance 0.005] [--dry-run]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bank", required=True)
    ap.add_argument("--tolerance", type=float, default=0.005,
                    help="leave a clip alone if |offset| is below this (m)")
    ap.add_argument("--percentile", type=float, default=1.0,
                    help="clearance percentile driving the shift")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.bank, "*.npz")))
    if args.limit:
        files = files[: args.limit]
    if not files:
        print("no clips found", file=sys.stderr)
        return 1

    from featurize_motions import G1Model  # noqa: PLC0415

    g = G1Model()
    qpos = np.empty(g.m.nq)
    log_path = os.path.join(args.bank, "ground_align.jsonl")
    shifted = ok = 0
    offsets = []

    with open(os.devnull if args.dry_run else log_path, "a") as log:
        for i, path in enumerate(files, 1):
            z = dict(np.load(path))
            bp, bq, jp = z["body_pos_w"], z["body_quat_w"], z["joint_pos"]
            # Subsample: the offset is a single scalar per clip, so a few hundred
            # frames pin the touchdown percentile perfectly well.
            step = max(1, len(bp) // 400)
            low = []
            for t in range(0, len(bp), step):
                qpos[0:3] = bp[t, 0]
                qpos[3:7] = bq[t, 0]
                qpos[7:] = jp[t]
                dl, dr, _ = g.floor_distances(qpos)
                low.append(min(dl, dr))
            offset = float(np.percentile(low, args.percentile))
            offsets.append(offset)

            if abs(offset) < args.tolerance:
                ok += 1
            else:
                shifted += 1
                if not args.dry_run:
                    z["body_pos_w"] = bp.copy()
                    z["body_pos_w"][:, :, 2] -= offset
                    tmp = path + ".tmp.npz"
                    np.savez(tmp, **z)
                    os.replace(tmp, path)
                    log.write(json.dumps({"name": os.path.basename(path),
                                          "offset_m": round(offset, 5)}) + "\n")
            if i % 250 == 0 or i == len(files):
                print(f"  [{i}/{len(files)}] shifted={shifted} already-ok={ok}")

    o = np.asarray(offsets)
    verb = "would shift" if args.dry_run else "shifted"
    print(f"\n{verb} {shifted}, left {ok} within {args.tolerance*1000:.0f} mm")
    print(f"offset distribution (m): min={o.min():+.4f} p50={np.median(o):+.4f} "
          f"p95={np.percentile(o,95):+.4f} max={o.max():+.4f}")
    if not args.dry_run and shifted:
        print(f"log: {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
