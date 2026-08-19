#!/usr/bin/env python3
"""Batch-convert retargeted G1 motion CSVs into mjlab tracking .npz files.

mjlab ships ``mjlab.scripts.csv_to_npz``, but it rebuilds the whole Scene and
Simulation per clip, writes to a hard-coded ``/tmp/motion.npz`` and then
unconditionally uploads to Weights & Biases -- none of which survives a
10k-clip bank build.  This driver imports mjlab's own ``MotionLoader`` so the
resampling and finite-difference velocities stay bit-identical to upstream,
then compiles the robot once and streams every clip through it.

Every output is validated before it is kept.  That check is not optional: a
motion exported in Isaac Lab / PhysX breadth-first body order has exactly the
same shape as a MuJoCo depth-first one, so mjlab loads it happily and trains
against the wrong links.  See ``validate_motion_npz.py``.

Usage:
    build_motion_bank.py --input-dir DIR --output-dir DIR --input-fps 30
    build_motion_bank.py --input-list FILE --output-dir DIR --input-fps 120
    build_motion_bank.py --input-dir DIR --output-dir DIR --limit 5 --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import traceback

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# The 29 actuated G1 joints in mjlab's depth-first order. Copied from
# mjlab.scripts.csv_to_npz.main so CSV columns map onto the same joints.
G1_JOINT_NAMES = [
    "left_hip_pitch_joint", "left_hip_roll_joint", "left_hip_yaw_joint",
    "left_knee_joint", "left_ankle_pitch_joint", "left_ankle_roll_joint",
    "right_hip_pitch_joint", "right_hip_roll_joint", "right_hip_yaw_joint",
    "right_knee_joint", "right_ankle_pitch_joint", "right_ankle_roll_joint",
    "waist_yaw_joint", "waist_roll_joint", "waist_pitch_joint",
    "left_shoulder_pitch_joint", "left_shoulder_roll_joint",
    "left_shoulder_yaw_joint", "left_elbow_joint", "left_wrist_roll_joint",
    "left_wrist_pitch_joint", "left_wrist_yaw_joint",
    "right_shoulder_pitch_joint", "right_shoulder_roll_joint",
    "right_shoulder_yaw_joint", "right_elbow_joint", "right_wrist_roll_joint",
    "right_wrist_pitch_joint", "right_wrist_yaw_joint",
]

LOG_KEYS = ("joint_pos", "joint_vel", "body_pos_w", "body_quat_w",
            "body_lin_vel_w", "body_ang_vel_w")

# The AMASS retargets do not share one source frame rate -- the directory mixes
# 120, 100, 60, 250, 59 and 150 fps, encoded in the filename as "..._<fps>_jpos".
# Converting all of them at a single --input-fps silently retimes 59% of the
# bank (100 fps read as 120 plays 20% fast; 60 fps plays double speed), which
# corrupts every velocity, acceleration and dynamics-derived feature.
_FPS_IN_NAME = re.compile(r"_(\d{2,3})_jpos$")


def infer_input_fps(csv_path: str, fallback: float) -> tuple[float, bool]:
    """Read the source frame rate out of the filename, else use the fallback."""
    stem = os.path.splitext(os.path.basename(csv_path))[0]
    m = _FPS_IN_NAME.search(stem)
    if m:
        fps = float(m.group(1))
        if 20.0 <= fps <= 500.0:
            return fps, True
    return fallback, False


class Converter:
    """Compiles the G1 scene once and converts clips through it."""

    def __init__(self, device: str = "cuda:0", output_fps: float = 50.0):
        import torch  # noqa: PLC0415
        from mjlab.scene import Scene  # noqa: PLC0415
        from mjlab.sim.sim import Simulation, SimulationCfg  # noqa: PLC0415
        from mjlab.tasks.tracking.config.g1.env_cfgs import (  # noqa: PLC0415
            unitree_g1_flat_tracking_env_cfg,
        )

        if device.startswith("cuda") and not torch.cuda.is_available():
            print("[warn] CUDA unavailable, falling back to CPU (slow)")
            device = "cpu"
        self.torch = torch
        self.device = device
        self.output_fps = output_fps

        cfg = SimulationCfg()
        cfg.mujoco.timestep = 1.0 / output_fps
        self.scene = Scene(unitree_g1_flat_tracking_env_cfg().scene, device=device)
        model = self.scene.compile()
        self.sim = Simulation(num_envs=1, cfg=cfg, model=model, device=device)
        self.scene.initialize(self.sim.mj_model, self.sim.model, self.sim.data)
        self.robot = self.scene["robot"]
        self.joint_idx = self.robot.find_joints(G1_JOINT_NAMES, preserve_order=True)[0]

    def convert(self, csv_path: str, input_fps: float) -> dict[str, np.ndarray]:
        from mjlab.scripts.csv_to_npz import MotionLoader  # noqa: PLC0415

        # A few clips in the AMASS retargets hold a single frame. np.loadtxt
        # collapses those to 1-D, and mjlab's loader then fails deep inside with
        # "too many indices for tensor of dimension 1"; say so plainly instead.
        with open(csv_path) as fh:
            if sum(1 for _ in zip(fh, range(2))) < 2:
                raise ValueError("clip has fewer than 2 frames")

        motion = MotionLoader(
            motion_file=csv_path,
            input_fps=input_fps,
            output_fps=self.output_fps,
            device=self.sim.device,
        )
        robot, scene, sim = self.robot, self.scene, self.sim
        log: dict[str, list] = {k: [] for k in LOG_KEYS}
        scene.reset()

        done = False
        while not done:
            (base_pos, base_rot, base_lin, base_ang, dof_pos, dof_vel), reset = (
                motion.get_next_state()
            )
            root = robot.data.default_root_state.clone()
            root[:, 0:3] = base_pos
            root[:, :2] += scene.env_origins[:, :2]
            root[:, 3:7] = base_rot
            root[:, 7:10] = base_lin
            root[:, 10:] = base_ang
            robot.write_root_state_to_sim(root)

            jp = robot.data.default_joint_pos.clone()
            jv = robot.data.default_joint_vel.clone()
            jp[:, self.joint_idx] = dof_pos
            jv[:, self.joint_idx] = dof_vel
            robot.write_joint_state_to_sim(jp, jv)

            sim.forward()
            scene.update(sim.mj_model.opt.timestep)

            d = robot.data
            log["joint_pos"].append(d.joint_pos[0].cpu().numpy().copy())
            log["joint_vel"].append(d.joint_vel[0].cpu().numpy().copy())
            log["body_pos_w"].append(d.body_link_pos_w[0].cpu().numpy().copy())
            log["body_quat_w"].append(d.body_link_quat_w[0].cpu().numpy().copy())
            log["body_lin_vel_w"].append(d.body_link_lin_vel_w[0].cpu().numpy().copy())
            log["body_ang_vel_w"].append(d.body_link_ang_vel_w[0].cpu().numpy().copy())
            done = bool(reset)

        out = {k: np.stack(v, axis=0) for k, v in log.items()}
        out["fps"] = np.array([self.output_fps])
        return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--input-dir", help="directory of .csv clips")
    src.add_argument("--input-list", help="file with one csv path per line")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--input-fps", type=float, required=True,
                    help="source frame rate; used as the fallback when --infer-fps "
                         "is set and the filename carries no rate (30 for the LAFAN1 "
                         "retargets, 120 for GRAB)")
    ap.add_argument("--infer-fps", action="store_true",
                    help="read each clip's source fps from a '_<fps>_jpos' filename "
                         "suffix. Required for the AMASS retargets, which mix 120/100/"
                         "60/250/59/150 fps in one directory.")
    ap.add_argument("--output-fps", type=float, default=50.0)
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--dry-run", action="store_true",
                    help="list what would be converted and exit")
    args = ap.parse_args()

    if args.input_dir:
        files = sorted(
            os.path.join(args.input_dir, f)
            for f in os.listdir(args.input_dir)
            if f.endswith(".csv")
        )
    else:
        with open(args.input_list) as fh:
            files = [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]
    if args.limit:
        files = files[: args.limit]
    if not files:
        print("no input csv files found", file=sys.stderr)
        return 1

    os.makedirs(args.output_dir, exist_ok=True)
    todo = [
        f for f in files
        if args.overwrite
        or not os.path.exists(
            os.path.join(args.output_dir,
                         os.path.splitext(os.path.basename(f))[0] + ".npz"))
    ]
    print(f"{len(files)} inputs, {len(todo)} to convert "
          f"({len(files) - len(todo)} already present)")
    if args.dry_run:
        for f in todo[:20]:
            print("  ", f)
        if len(todo) > 20:
            print(f"   ... and {len(todo) - 20} more")
        return 0
    if not todo:
        return 0

    from validate_motion_npz import check, reference_profile  # noqa: PLC0415

    xml = ("/data/robotixx/climb/mjlab-1.6.0/src/mjlab/asset_zoo/robots/"
           "unitree_g1/xmls/g1.xml")
    ref = reference_profile(xml) if os.path.exists(xml) else None

    conv = Converter(device=args.device, output_fps=args.output_fps)
    manifest_path = os.path.join(args.output_dir, "manifest.jsonl")
    n_ok = n_bad = n_fallback = 0
    fps_counts: dict[float, int] = {}
    t0 = time.time()

    with open(manifest_path, "a") as manifest:
        for i, csv_path in enumerate(todo, 1):
            stem = os.path.splitext(os.path.basename(csv_path))[0]
            out_path = os.path.join(args.output_dir, stem + ".npz")
            in_fps, from_name = (infer_input_fps(csv_path, args.input_fps)
                                 if args.infer_fps else (args.input_fps, False))
            fps_counts[in_fps] = fps_counts.get(in_fps, 0) + 1
            n_fallback += not from_name
            rec: dict = {"name": stem, "source_csv": csv_path,
                         "input_fps": in_fps, "input_fps_from_name": from_name,
                         "output_fps": args.output_fps}
            try:
                data = conv.convert(csv_path, in_fps)
                tmp = out_path + ".tmp.npz"
                np.savez(tmp, **data)
                ok, problems, info = check(tmp, ref)
                if not ok:
                    os.remove(tmp)
                    n_bad += 1
                    rec.update(status="INVALID", problems=problems, **info)
                    print(f"[{i}/{len(todo)}] INVALID {stem}: {problems}")
                else:
                    os.replace(tmp, out_path)
                    n_ok += 1
                    rec.update(status="OK", **info)
                    rate = i / max(time.time() - t0, 1e-9)
                    eta = (len(todo) - i) / max(rate, 1e-9)
                    print(f"[{i}/{len(todo)}] OK {stem} "
                          f"{info['frames']}f {info['duration_s']:.1f}s "
                          f"({rate:.2f} clip/s, ETA {eta / 60:.1f}m)")
            except Exception as exc:  # noqa: BLE001
                n_bad += 1
                rec.update(status="ERROR", error=f"{type(exc).__name__}: {exc}")
                print(f"[{i}/{len(todo)}] ERROR {stem}: {exc}")
                traceback.print_exc(limit=2)
            manifest.write(json.dumps(rec) + "\n")
            manifest.flush()

    print(f"\n{n_ok} converted, {n_bad} failed, in {(time.time() - t0) / 60:.1f} min")
    if args.infer_fps:
        spread = ", ".join(f"{int(k)}fps x{v}" for k, v in sorted(fps_counts.items()))
        print(f"source frame rates: {spread}")
        if n_fallback:
            print(f"  {n_fallback} clips had no rate in the filename and used the "
                  f"--input-fps {args.input_fps:g} fallback")
    print(f"manifest: {manifest_path}")
    return 0 if n_bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
