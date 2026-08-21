#!/usr/bin/env python3
"""Root/contact-IK repair operator for DFRP v0.

The operator lowers the root only on frames with no collision geometry inside
the pinned contact band. If smoothing leaves the selected leg support geometry
above the target clearance, a bounded damped-least-squares IK correction uses
only that leg's hip/knee/ankle joints. Non-leg contacts remain root-only and are
reported explicitly rather than being treated as successful IK.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

OPERATOR = "dfrp_root_contact_ik_v1"


def sha256_file(path: Path) -> str:
    """Hash one repair input for provenance."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def smooth_1d(values: np.ndarray, sigma_frames: float) -> np.ndarray:
    """Gaussian-smooth one scalar timeline with edge replication."""
    if sigma_frames <= 0.0:
        return values.copy()
    width = int(4.0 * sigma_frames) | 1
    positions = np.arange(width) - width // 2
    kernel = np.exp(-0.5 * (positions / sigma_frames) ** 2)
    kernel /= kernel.sum()
    return np.convolve(
        np.pad(values, width // 2, mode="edge"), kernel, mode="valid"
    )


def _short_name(model: mujoco.MjModel, kind: mujoco.mjtObj, index: int) -> str:
    return (mujoco.mj_id2name(model, kind, index) or "").split("/")[-1]


def _leg_joint_ids(model: mujoco.MjModel) -> dict[str, list[int]]:
    result = {"left": [], "right": []}
    for joint_id in range(model.njnt):
        name = _short_name(model, mujoco.mjtObj.mjOBJ_JOINT, joint_id)
        for side, joint_ids in result.items():
            if name.startswith(f"{side}_") and any(
                token in name for token in ("hip", "knee", "ankle")
            ):
                joint_ids.append(joint_id)
    if any(len(ids) != 6 for ids in result.values()):
        raise ValueError(f"expected six leg joints per side, got {result}")
    return result


def _support_side(geom_name: str) -> str | None:
    if geom_name.startswith("left_") and any(
        token in geom_name for token in ("foot", "shin", "linkage")
    ):
        return "left"
    if geom_name.startswith("right_") and any(
        token in geom_name for token in ("foot", "shin", "linkage")
    ):
        return "right"
    return None


def _angular_velocity(quaternions_wxyz: np.ndarray, fps: float) -> np.ndarray:
    """Return centered world-frame angular velocity from wxyz quaternions."""
    xyzw = np.concatenate(
        (quaternions_wxyz[..., 1:4], quaternions_wxyz[..., 0:1]), axis=-1
    )
    rotations = Rotation.from_quat(xyzw.reshape(-1, 4)).as_matrix().reshape(
        *xyzw.shape[:-1], 3, 3
    )
    frames, bodies = xyzw.shape[:2]
    velocity = np.zeros((frames, bodies, 3), dtype=np.float64)
    for frame in range(frames):
        before = max(frame - 1, 0)
        after = min(frame + 1, frames - 1)
        dt = (after - before) / fps
        if dt == 0.0:
            continue
        delta = rotations[after] @ np.swapaxes(rotations[before], -1, -2)
        velocity[frame] = Rotation.from_matrix(delta).as_rotvec() / dt
    return velocity


def repair_motion(
    *,
    motion_path: Path,
    model_path: Path,
    output_path: Path,
    gap_m: float = 0.06,
    clearance_m: float = 0.003,
    smoothing_s: float = 0.24,
    ik_tolerance_m: float = 0.001,
    ik_iterations: int = 15,
) -> dict[str, Any]:
    """Repair one motion and return provenance/fidelity diagnostics."""
    if gap_m <= clearance_m or clearance_m < 0.0:
        raise ValueError("require gap_m > clearance_m >= 0")
    if ik_tolerance_m <= 0.0 or ik_iterations <= 0:
        raise ValueError("IK tolerance and iteration count must be positive")
    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)
    plane_ids = [
        index
        for index in range(model.ngeom)
        if model.geom_type[index] == mujoco.mjtGeom.mjGEOM_PLANE
    ]
    if len(plane_ids) != 1:
        raise ValueError("DFRP v0 requires exactly one plane terrain geom")
    plane_id = plane_ids[0]
    collision_ids = [
        index
        for index in range(model.ngeom)
        if index != plane_id
        and (model.geom_contype[index] or model.geom_conaffinity[index])
    ]
    leg_joints = _leg_joint_ids(model)

    with np.load(motion_path) as archive:
        motion = {name: np.asarray(archive[name]).copy() for name in archive.files}
    required = (
        "joint_pos",
        "joint_vel",
        "body_pos_w",
        "body_quat_w",
        "body_lin_vel_w",
        "body_ang_vel_w",
        "fps",
    )
    missing = [name for name in required if name not in motion]
    if missing:
        raise ValueError(f"motion lacks fields {missing}")
    frames = int(motion["joint_pos"].shape[0])
    fps = float(np.asarray(motion["fps"]).reshape(-1)[0])
    if model.nq != motion["joint_pos"].shape[1] + 7:
        raise ValueError("motion joint order does not match the MuJoCo model")
    if motion["body_pos_w"].shape[1] != model.nbody - 2:
        raise ValueError("motion body order does not match the MuJoCo model")

    qpos = np.zeros((frames, model.nq), dtype=np.float64)
    qpos[:, :3] = motion["body_pos_w"][:, 0]
    qpos[:, 3:7] = motion["body_quat_w"][:, 0]
    qpos[:, 7:] = motion["joint_pos"]
    minimum_distance = np.zeros(frames, dtype=np.float64)
    support_geom = np.zeros(frames, dtype=np.int32)
    from_to = np.zeros(6, dtype=np.float64)
    for frame in range(frames):
        data.qpos[:] = qpos[frame]
        mujoco.mj_forward(model, data)
        distances = [
            mujoco.mj_geomDistance(
                model, data, geom_id, plane_id, 10.0, from_to
            )
            for geom_id in collision_ids
        ]
        local_index = int(np.argmin(distances))
        minimum_distance[frame] = distances[local_index]
        support_geom[frame] = collision_ids[local_index]

    needs_support = minimum_distance > gap_m
    raw_offset = np.where(
        needs_support, np.maximum(minimum_distance - clearance_m, 0.0), 0.0
    )
    smoothed = smooth_1d(raw_offset, smoothing_s * fps)
    root_offset = np.where(
        needs_support,
        np.minimum(smoothed, np.maximum(minimum_distance - clearance_m, 0.0)),
        0.0,
    )
    qpos[:, 2] -= root_offset

    if not bool(needs_support.any()):
        joint_limits_valid = True
        for joint_id in range(1, model.njnt):
            if not model.jnt_limited[joint_id]:
                continue
            qpos_id = model.jnt_qposadr[joint_id]
            low, high = model.jnt_range[joint_id]
            joint_limits_valid &= bool(
                (
                    (qpos[:, qpos_id] >= low - 1.0e-4)
                    & (qpos[:, qpos_id] <= high + 1.0e-4)
                ).all()
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(motion_path, output_path)
        return {
            "operator": OPERATOR,
            "operator_sha256": sha256_file(Path(__file__).resolve()),
            "input_motion_sha256": sha256_file(motion_path),
            "model_sha256": sha256_file(model_path),
            "clip": motion_path.stem,
            "frames": frames,
            "fps": fps,
            "gap_m": gap_m,
            "clearance_m": clearance_m,
            "smoothing_s": smoothing_s,
            "frames_needing_support": 0,
            "needs_frac": 0.0,
            "offset_max_m": 0.0,
            "offset_mean_when_active_m": 0.0,
            "joint_delta_rad_p95": 0.0,
            "joint_delta_rad_max": 0.0,
            "joint_limits_valid": joint_limits_valid,
            "ik_frames": 0,
            "ik_iterations_max": 0,
            "ik_contact_residual_m": 0.0,
            "nonleg_support_frames": 0,
        }

    ik_used = np.zeros(frames, dtype=bool)
    ik_iterations_used = np.zeros(frames, dtype=np.int32)
    contact_residual = np.zeros(frames, dtype=np.float64)
    nonleg_support_frames = 0
    jac_position = np.zeros((3, model.nv), dtype=np.float64)
    jac_rotation = np.zeros((3, model.nv), dtype=np.float64)
    for frame in np.flatnonzero(needs_support):
        geom_id = int(support_geom[frame])
        geom_name = _short_name(model, mujoco.mjtObj.mjOBJ_GEOM, geom_id)
        side = _support_side(geom_name)
        data.qpos[:] = qpos[frame]
        mujoco.mj_forward(model, data)
        distance = mujoco.mj_geomDistance(
            model, data, geom_id, plane_id, 10.0, from_to
        )
        if side is None:
            nonleg_support_frames += 1
            contact_residual[frame] = max(distance - clearance_m, 0.0)
            continue
        joint_ids = leg_joints[side]
        dof_ids = np.array([model.jnt_dofadr[joint_id] for joint_id in joint_ids])
        qpos_ids = np.array([model.jnt_qposadr[joint_id] for joint_id in joint_ids])
        for iteration in range(ik_iterations):
            distance = mujoco.mj_geomDistance(
                model, data, geom_id, plane_id, 10.0, from_to
            )
            error = max(distance - clearance_m, 0.0)
            if error <= ik_tolerance_m:
                break
            point = from_to[:3].copy()
            mujoco.mj_jac(
                model,
                data,
                jac_position,
                jac_rotation,
                point,
                model.geom_bodyid[geom_id],
            )
            jacobian = jac_position[2, dof_ids]
            denominator = float(jacobian @ jacobian + 1.0e-5)
            delta = np.clip(-error * jacobian / denominator, -0.05, 0.05)
            data.qpos[qpos_ids] += delta
            for joint_id, qpos_id in zip(joint_ids, qpos_ids, strict=True):
                if model.jnt_limited[joint_id]:
                    low, high = model.jnt_range[joint_id]
                    data.qpos[qpos_id] = np.clip(data.qpos[qpos_id], low, high)
            mujoco.mj_forward(model, data)
            ik_used[frame] = True
            ik_iterations_used[frame] = iteration + 1
        qpos[frame] = data.qpos
        distance = mujoco.mj_geomDistance(
            model, data, geom_id, plane_id, 10.0, from_to
        )
        contact_residual[frame] = max(distance - clearance_m, 0.0)

    joint_limits_valid = True
    for joint_id in range(1, model.njnt):
        if not model.jnt_limited[joint_id]:
            continue
        qpos_id = model.jnt_qposadr[joint_id]
        low, high = model.jnt_range[joint_id]
        joint_limits_valid &= bool(
            (
                (qpos[:, qpos_id] >= low - 1.0e-4)
                & (qpos[:, qpos_id] <= high + 1.0e-4)
            ).all()
        )

    body_position = np.zeros_like(motion["body_pos_w"], dtype=np.float64)
    body_quaternion = np.zeros_like(motion["body_quat_w"], dtype=np.float64)
    for frame in range(frames):
        data.qpos[:] = qpos[frame]
        mujoco.mj_forward(model, data)
        body_position[frame] = data.xpos[2:]
        body_quaternion[frame] = data.xquat[2:]
    body_linear_velocity = np.gradient(body_position, 1.0 / fps, axis=0)
    body_angular_velocity = _angular_velocity(body_quaternion, fps)
    joint_position = qpos[:, 7:]
    joint_velocity = np.gradient(joint_position, 1.0 / fps, axis=0)

    output = dict(motion)
    output["joint_pos"] = joint_position.astype(motion["joint_pos"].dtype)
    output["joint_vel"] = joint_velocity.astype(motion["joint_vel"].dtype)
    output["body_pos_w"] = body_position.astype(motion["body_pos_w"].dtype)
    output["body_quat_w"] = body_quaternion.astype(motion["body_quat_w"].dtype)
    output["body_lin_vel_w"] = body_linear_velocity.astype(
        motion["body_lin_vel_w"].dtype
    )
    output["body_ang_vel_w"] = body_angular_velocity.astype(
        motion["body_ang_vel_w"].dtype
    )
    if not all(bool(np.isfinite(value).all()) for value in output.values()):
        raise ValueError("repair produced a non-finite motion")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output_path, **output)

    joint_delta = np.abs(joint_position - motion["joint_pos"])
    return {
        "operator": OPERATOR,
        "operator_sha256": sha256_file(Path(__file__).resolve()),
        "input_motion_sha256": sha256_file(motion_path),
        "model_sha256": sha256_file(model_path),
        "clip": motion_path.stem,
        "frames": frames,
        "fps": fps,
        "gap_m": gap_m,
        "clearance_m": clearance_m,
        "smoothing_s": smoothing_s,
        "frames_needing_support": int(needs_support.sum()),
        "needs_frac": float(needs_support.mean()),
        "offset_max_m": float(root_offset.max(initial=0.0)),
        "offset_mean_when_active_m": (
            float(root_offset[needs_support].mean()) if needs_support.any() else 0.0
        ),
        "joint_delta_rad_p95": float(np.percentile(joint_delta, 95)),
        "joint_delta_rad_max": float(joint_delta.max(initial=0.0)),
        "joint_limits_valid": joint_limits_valid,
        "ik_frames": int(ik_used.sum()),
        "ik_iterations_max": int(ik_iterations_used.max(initial=0)),
        "ik_contact_residual_m": float(contact_residual.max(initial=0.0)),
        "nonleg_support_frames": nonleg_support_frames,
    }


def run_rescreen(
    *,
    clip: str,
    bank: Path,
    model: Path,
    gap_m: float,
    brief_out: Path,
    full_out: Path,
    sidecar_dir: Path,
) -> dict[str, Any]:
    """Run the released screen over the full repaired timeline and reduce it."""
    repo = Path(__file__).resolve().parents[1]
    environment = dict(os.environ)
    python_path = str(repo / "refeas")
    environment["PYTHONPATH"] = (
        f"{python_path}:{environment['PYTHONPATH']}"
        if environment.get("PYTHONPATH")
        else python_path
    )
    base = [
        sys.executable,
        "-m",
        "refeas.screen",
        "--clip",
        clip,
        "--bank",
        str(bank),
        "--model",
        str(model),
        "--t0",
        "0",
        "--t1",
        "1e9",
        "--gap",
        str(gap_m),
    ]
    brief_out.parent.mkdir(parents=True, exist_ok=True)
    full_out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [*base, "--brief", "--out", str(brief_out)],
        check=True,
        env=environment,
    )
    subprocess.run([*base, "--out", str(full_out)], check=True, env=environment)
    subprocess.run(
        [
            sys.executable,
            str(repo / "tools" / "screen_segments.py"),
            "--json",
            str(full_out),
            "--guard-s",
            "0",
            "--guard-mode",
            "symmetric",
            "--min-seg-s",
            "1.0",
            "--severity",
            "severe",
            "--model",
            "real",
            "--out-dir",
            str(sidecar_dir),
        ],
        check=True,
        env=environment,
    )
    return json.loads(brief_out.read_text())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clip", required=True)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--screen-before", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--record-dir", type=Path, required=True)
    parser.add_argument("--full-screen-dir", type=Path, required=True)
    parser.add_argument("--brief-screen-dir", type=Path, required=True)
    parser.add_argument("--sidecar-dir", type=Path, required=True)
    parser.add_argument("--gap-m", type=float, default=0.06)
    parser.add_argument("--clearance-m", type=float, default=0.003)
    parser.add_argument("--smoothing-s", type=float, default=0.24)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    source = args.bank / f"{args.clip}.npz"
    output = args.out_dir / f"{args.clip}.npz"
    record_path = args.record_dir / f"{args.clip}.json"
    destinations = (output, record_path)
    if any(path.exists() for path in destinations) and not args.force:
        raise SystemExit("repair output exists; pass --force to replace this clip")
    before = json.loads(args.screen_before.read_text())
    if before.get("clip") != args.clip:
        raise SystemExit("--screen-before names a different clip")
    record = repair_motion(
        motion_path=source,
        model_path=args.model,
        output_path=output,
        gap_m=args.gap_m,
        clearance_m=args.clearance_m,
        smoothing_s=args.smoothing_s,
    )
    after = run_rescreen(
        clip=args.clip,
        bank=args.out_dir,
        model=args.model,
        gap_m=args.gap_m,
        brief_out=args.brief_screen_dir / f"{args.clip}.json",
        full_out=args.full_screen_dir / f"{args.clip}.json",
        sidecar_dir=args.sidecar_dir,
    )
    record.update(
        {
            "infeasible_frac_before": float(before["infeasible_frac"]),
            "airborne_frac_before": float(before["airborne_frac"]),
            "infeasible_frac_after": float(after["infeasible_frac"]),
            "airborne_frac_after": float(after["airborne_frac"]),
            "primary_candidate": bool(
                after["infeasible_frac"] <= 0.05
                and record["offset_max_m"] <= 0.08
                and record["joint_limits_valid"]
                and record["ik_contact_residual_m"] <= 0.01
            ),
            "exploratory_candidate": bool(
                after["infeasible_frac"] <= 0.05
                and record["offset_max_m"] <= 0.15
                and record["joint_limits_valid"]
            ),
        }
    )
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps(record, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
