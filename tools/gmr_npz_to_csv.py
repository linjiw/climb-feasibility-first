#!/usr/bin/env python3
"""Convert GMR retargeting output (.npz with ``qpos``) into mjlab-style CSV.

GMR writes MuJoCo ``qpos`` directly: ``[pos(3), quat_wxyz(4), joints(29)]``.
mjlab's CSV reader wants ``[pos(3), quat_xyzw(4), joints(29)]`` -- it applies
``[:, [3, 0, 1, 2]]`` to move w back to the front (csv_to_npz.py:60-63).  So the
only transformation needed is moving the scalar component from first to last.

The joint block needs no permutation: GMR's ``g1_mocap_29dof.xml`` declares its
29 hinges in the same depth-first order as mjlab's ``g1.xml``.  This script
verifies that assumption against both compiled models before writing anything,
rather than trusting it.

Usage:
    gmr_npz_to_csv.py --input-dir /data/robotixx/pairs/unitree_g1 \
                      --output-dir /data/robotixx/climb/bank/csv/lafan1_gmr
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np

MJLAB_XML = ("/data/robotixx/climb/mjlab-1.6.0/src/mjlab/asset_zoo/robots/"
             "unitree_g1/xmls/g1.xml")
GMR_XML = "/home/robotixx/GMR/assets/unitree_g1/g1_mocap_29dof.xml"


def hinge_order(xml_path: str) -> list[str]:
    import mujoco  # noqa: PLC0415

    m = mujoco.MjModel.from_xml_path(xml_path)
    names = []
    for i in range(m.njnt):
        if m.jnt_type[i] == mujoco.mjtJoint.mjJNT_HINGE:
            names.append(mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, i))
    return names


def verify_joint_order() -> tuple[bool, str]:
    """Confirm GMR and mjlab agree on hinge ordering before converting."""
    if not (os.path.exists(MJLAB_XML) and os.path.exists(GMR_XML)):
        return False, "one or both reference XMLs are missing; cannot verify"
    a, b = hinge_order(MJLAB_XML), hinge_order(GMR_XML)
    if a == b:
        return True, f"verified: {len(a)} hinges in identical order"
    diff = [f"{i}: mjlab={x} gmr={y}"
            for i, (x, y) in enumerate(zip(a, b)) if x != y]
    return False, (f"ORDER MISMATCH ({len(a)} vs {len(b)} hinges); "
                   f"first diffs: {diff[:5]}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--skip-verify", action="store_true",
                    help="convert even if the joint-order check cannot run")
    args = ap.parse_args()

    ok, msg = verify_joint_order()
    print(f"[joint order] {msg}")
    if not ok and not args.skip_verify:
        print("refusing to convert; pass --skip-verify to override", file=sys.stderr)
        return 2

    os.makedirs(args.output_dir, exist_ok=True)
    files = sorted(f for f in os.listdir(args.input_dir) if f.endswith(".npz"))
    if args.limit:
        files = files[: args.limit]

    n = 0
    fps_seen: set[float] = set()
    for name in files:
        z = np.load(os.path.join(args.input_dir, name), allow_pickle=True)
        if "qpos" not in z:
            print(f"  skip {name}: no qpos key")
            continue
        q = np.asarray(z["qpos"], dtype=np.float64)
        if q.shape[1] != 36:
            print(f"  skip {name}: qpos width {q.shape[1]} != 36")
            continue
        # wxyz -> xyzw, joints untouched.
        csv = np.hstack([q[:, 0:3], q[:, [4, 5, 6, 3]], q[:, 7:]])
        out = os.path.join(args.output_dir, os.path.splitext(name)[0] + ".csv")
        np.savetxt(out, csv, delimiter=",", fmt="%.6f")
        if "fps" in z:
            fps_seen.add(float(np.asarray(z["fps"]).reshape(-1)[0]))
        n += 1
        print(f"  {name} -> {os.path.basename(out)}  ({q.shape[0]} frames)")

    print(f"\n{n} clips written to {args.output_dir}")
    if fps_seen:
        print(f"source fps: {sorted(fps_seen)} "
              f"-> pass --input-fps {sorted(fps_seen)[0]:g} to build_motion_bank.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
