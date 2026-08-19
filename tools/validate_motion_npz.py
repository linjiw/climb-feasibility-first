#!/usr/bin/env python3
"""Validate a motion .npz against mjlab's tracking-task contract.

mjlab's ``MotionLoader`` indexes ``body_pos_w`` with body indices taken from the
compiled MuJoCo model, but the npz carries no body names and the loader asserts
nothing.  A file exported in Isaac Lab / PhysX breadth-first body order has the
same shape as a MuJoCo depth-first one (30 bodies, 29 joints for the G1), so it
loads cleanly and silently attaches every tracking target to the wrong link.

The discriminator used here is the pelvis-frame lateral offset profile, which is
invariant to the robot's pose (unlike "the two lowest bodies are the feet",
which misfires on kneeling/sitting/ground motions):

    depth-first : bodies 1..6 are the whole left leg   (y > 0)
                  bodies 7..12 are the whole right leg (y < 0)
    breadth-first: legs interleave, so each group averages to ~0

Usage:
    validate_motion_npz.py FILE [FILE ...]
    validate_motion_npz.py --dir DIR [--limit N]
    validate_motion_npz.py --xml PATH FILE      # override the reference model
"""

from __future__ import annotations

import argparse
import glob
import os
import sys

import numpy as np

DEFAULT_XML = (
    "/data/robotixx/climb/mjlab-1.6.0/src/mjlab/asset_zoo/robots/unitree_g1/xmls/g1.xml"
)

REQUIRED_KEYS = (
    "fps",
    "joint_pos",
    "joint_vel",
    "body_pos_w",
    "body_quat_w",
    "body_lin_vel_w",
    "body_ang_vel_w",
)


def quat_to_mat(q: np.ndarray) -> np.ndarray:
    """Rotation matrices from wxyz quaternions, shape (..., 4) -> (..., 3, 3)."""
    q = q / np.linalg.norm(q, axis=-1, keepdims=True)
    w, x, y, z = q[..., 0], q[..., 1], q[..., 2], q[..., 3]
    return np.stack(
        [
            1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y),
            2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x),
            2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y),
        ],
        axis=-1,
    ).reshape(*q.shape[:-1], 3, 3)


def reference_profile(xml_path: str) -> np.ndarray:
    """Pelvis-frame lateral offset per body for the compiled reference model."""
    import mujoco  # noqa: PLC0415

    m = mujoco.MjModel.from_xml_path(xml_path)
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    pos = d.xpos[1:].copy()
    rot = np.zeros(9)
    mujoco.mju_quat2Mat(rot, d.xquat[1])
    return ((pos - pos[0]) @ rot.reshape(3, 3))[:, 1]


def pelvis_frame_lateral(body_pos_w: np.ndarray, body_quat_w: np.ndarray,
                         max_frames: int = 200) -> np.ndarray:
    """Mean pelvis-frame lateral (y) offset per body, averaged over frames."""
    n = body_pos_w.shape[0]
    idx = np.linspace(0, n - 1, min(max_frames, n)).astype(int)
    pos, quat = body_pos_w[idx], body_quat_w[idx]
    rel = pos - pos[:, :1, :]
    rot = quat_to_mat(quat[:, 0])                       # (F, 3, 3)
    local = np.einsum("fij,fbi->fbj", rot, rel)          # R^T @ rel
    return local[..., 1].mean(axis=0)


def classify(lateral: np.ndarray) -> tuple[str, dict]:
    """Classify body ordering from three proximal pelvis-frame lateral offsets.

    Bodies 1, 2 and 7 are the discriminator because their origins sit at fixed
    (or hinge-invariant) transforms from the pelvis, so their pelvis-frame y is
    constant no matter what the robot is doing.  Measured across 40 clips that
    include falls, fights and jumps, the spread is exactly zero:

        depth-first    y[1]=+0.0645  y[2]=+0.1165  y[7]=-0.0645
        breadth-first  y[1]=+0.0645  y[2]=-0.0645  y[7]=+0.1238

    ``sign(y[2])`` alone separates them; y[7] confirms.  An earlier version
    averaged y over whole limbs and compared the profile against the neutral
    pose, which wrongly rejected calibration, lying and kicking clips whose
    legs cross the midline.
    """
    y1, y2, y7 = (float(lateral[i]) for i in (1, 2, 7))
    stats = {"y_body1": y1, "y_body2": y2, "y_body7": y7}
    if y1 > 0.02 and y2 > 0.05 and y7 < -0.02:
        return "depth-first (mjlab/MuJoCo)", stats
    if y1 > 0.02 and y2 < -0.02 and y7 > 0.02:
        return "breadth-first (Isaac Lab/PhysX)", stats
    return "unknown", stats


def check(path: str, ref: np.ndarray | None) -> tuple[bool, list[str], dict]:
    problems: list[str] = []
    info: dict = {}
    try:
        z = np.load(path)
    except Exception as exc:  # noqa: BLE001
        return False, [f"cannot load: {exc}"], info

    missing = [k for k in REQUIRED_KEYS if k not in z]
    if missing:
        problems.append(f"missing keys: {missing}")
        return False, problems, info

    bp, bq = z["body_pos_w"], z["body_quat_w"]
    jp, jv = z["joint_pos"], z["joint_vel"]
    info["frames"] = int(bp.shape[0])
    info["bodies"] = int(bp.shape[1])
    info["joints"] = int(jp.shape[1])
    info["fps"] = float(np.asarray(z["fps"]).reshape(-1)[0])
    info["duration_s"] = info["frames"] / info["fps"] if info["fps"] else float("nan")

    if ref is not None and bp.shape[1] != ref.shape[0]:
        problems.append(f"body count {bp.shape[1]} != model {ref.shape[0]}")
    if jp.shape[0] != bp.shape[0] or jv.shape != jp.shape:
        problems.append("frame counts disagree across arrays")
    for name in ("body_pos_w", "body_quat_w", "joint_pos", "joint_vel"):
        if not np.isfinite(z[name]).all():
            problems.append(f"{name} contains non-finite values")

    order, stats = classify(pelvis_frame_lateral(bp, bq))
    info["order"] = order
    info.update(stats)
    if not order.startswith("depth-first"):
        problems.append(f"body order is {order}; mjlab requires depth-first")

    if ref is not None and order.startswith("depth-first"):
        # Recorded, never fatal. This compares the whole-skeleton profile against
        # the neutral standing pose, so any motion that is not roughly upright
        # scores low while being perfectly valid -- seated GRAB manipulation
        # clips reach -0.6. The proximal-body test in classify() is the gate;
        # this is only a covariate for spotting unusual posture in bulk.
        info["profile_corr_vs_model"] = float(
            np.corrcoef(pelvis_frame_lateral(bp, bq), ref)[0, 1]
        )

    return not problems, problems, info


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="npz files to validate")
    ap.add_argument("--dir", help="validate every .npz under this directory")
    ap.add_argument("--limit", type=int, default=0, help="cap files checked with --dir")
    ap.add_argument("--xml", default=DEFAULT_XML, help="reference MuJoCo model")
    ap.add_argument("--quiet", action="store_true", help="only print failures")
    args = ap.parse_args()

    files = list(args.files)
    if args.dir:
        files += sorted(glob.glob(os.path.join(args.dir, "**", "*.npz"), recursive=True))
    if args.limit:
        files = files[: args.limit]
    if not files:
        ap.error("no files given")

    ref = None
    if os.path.exists(args.xml):
        try:
            ref = reference_profile(args.xml)
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] reference model unavailable ({exc}); "
                  "running structural checks only", file=sys.stderr)

    n_ok = 0
    for path in files:
        ok, problems, info = check(path, ref)
        n_ok += ok
        if ok and args.quiet:
            continue
        tag = "PASS" if ok else "FAIL"
        head = f"[{tag}] {os.path.basename(path)}"
        if info:
            head += (f"  {info.get('frames','?')}f @ {info.get('fps','?')}Hz"
                     f"  {info.get('duration_s',float('nan')):.1f}s"
                     f"  bodies={info.get('bodies','?')} joints={info.get('joints','?')}")
        print(head)
        if not ok:
            print(f"        order: {info.get('order','?')}"
                  f"  (y1={info.get('y_body1', float('nan')):+.4f},"
                  f" y2={info.get('y_body2', float('nan')):+.4f},"
                  f" y7={info.get('y_body7', float('nan')):+.4f})")
            for p in problems:
                print(f"        - {p}")

    print(f"\n{n_ok}/{len(files)} passed")
    return 0 if n_ok == len(files) else 1


if __name__ == "__main__":
    raise SystemExit(main())
