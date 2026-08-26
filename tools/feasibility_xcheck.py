#!/usr/bin/env python3
"""Prepare and aggregate the 20+20 cross-implementation feasibility check.

The two production screens use different motion containers and isolated Python
environments.  ``prepare`` selects the panel without seeing cross-screen
outcomes and writes lossless, joint-order-preserving adapters for the opposite
screen.  Run the existing CLIMB/refeas and SONIC screen entry points on those
adapters, then use ``analyze`` to join their outputs with the durable native
bank screens and write the agreement statistics and completion sentinel.

This tool does not implement either feasibility screen.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import random
import sys
from typing import Any
import xml.etree.ElementTree as ET

import numpy as np


SELECTION_SEED = 260826
FLAG_THRESHOLD = 0.10
CLIP_44 = "BMLmovi_Subject_64_F_MoSh_Subject_64_F_9_poses_120_jpos"


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of one file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV into plain dictionaries."""
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write dictionaries with LF line endings and stable field order."""
    if not rows:
        raise ValueError(f"refusing to write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def stable_sample(values: list[str], count: int, rng: random.Random) -> list[str]:
    """Sample from a sorted population and return a sorted selection."""
    if len(values) < count:
        raise ValueError(f"cannot sample {count} from {len(values)} values")
    return sorted(rng.sample(sorted(values), count))


def select_panel(
    sonic_rows: list[dict[str, str]],
    climb_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Select 7+13 BONES and 10+10 AMASS clips before cross-screening."""
    rng = random.Random(SELECTION_SEED)
    sonic = {row["motion_key"]: row for row in sonic_rows}
    climb = {row["clip"]: row for row in climb_rows}

    sonic_flagged = sorted(
        key for key, row in sonic.items() if float(row["infeasible_frac"]) > FLAG_THRESHOLD
    )
    if len(sonic_flagged) != 7:
        raise ValueError(f"expected 7 flagged BONES clips, found {len(sonic_flagged)}")
    sonic_feasible = stable_sample(
        [
            key
            for key, row in sonic.items()
            if float(row["infeasible_frac"]) <= FLAG_THRESHOLD
        ],
        13,
        rng,
    )

    if CLIP_44 not in climb:
        raise ValueError(f"clip #44 is missing from the AMASS screen: {CLIP_44}")
    climb_other_flagged = stable_sample(
        [
            key
            for key, row in climb.items()
            if key != CLIP_44 and float(row["infeasible_frac"]) > FLAG_THRESHOLD
        ],
        9,
        rng,
    )
    climb_flagged = sorted([CLIP_44, *climb_other_flagged])
    climb_feasible = stable_sample(
        [
            key
            for key, row in climb.items()
            if float(row["infeasible_frac"]) <= FLAG_THRESHOLD
        ],
        10,
        rng,
    )

    panel: list[dict[str, str]] = []
    for bank, stratum, clips, rows, native_impl in (
        ("BONES-SEED", "flagged", sonic_flagged, sonic, "sonic"),
        ("BONES-SEED", "feasible", sonic_feasible, sonic, "sonic"),
        ("AMASS-wbt-G1", "flagged", climb_flagged, climb, "climb"),
        ("AMASS-wbt-G1", "feasible", climb_feasible, climb, "climb"),
    ):
        for clip in clips:
            row = rows[clip]
            panel.append(
                {
                    "bank": bank,
                    "stratum": stratum,
                    "clip": clip,
                    "native_impl": native_impl,
                    "native_infeasible_frac": row["infeasible_frac"],
                    "native_airborne_frac": row["airborne_frac"],
                }
            )
    return panel


def add_sonic_repo(sonic_repo: Path) -> None:
    """Expose the SONIC repository to the isolated adapter process."""
    resolved = str(sonic_repo.resolve())
    if resolved not in sys.path:
        sys.path.insert(0, resolved)


def xml_hinge_layout(path: Path) -> tuple[list[str], np.ndarray]:
    """Read hinge names and axes from one flattened MJCF without compiling it."""
    root = ET.parse(path).getroot()
    hinges = [
        joint
        for joint in root.iter("joint")
        if joint.attrib.get("type", "hinge") == "hinge"
    ]
    names = [joint.attrib["name"].split("/")[-1] for joint in hinges]
    axes = np.asarray(
        [[float(value) for value in joint.attrib.get("axis", "0 0 1").split()] for joint in hinges]
    )
    return names, axes


def quat_wxyz_to_matrix(quaternion: np.ndarray) -> np.ndarray:
    """Convert one unit WXYZ quaternion to a 3x3 rotation matrix."""
    import mujoco

    matrix = np.zeros(9, dtype=np.float64)
    mujoco.mju_quat2Mat(matrix, np.asarray(quaternion, dtype=np.float64))
    return matrix.reshape(3, 3)


def adapt_bones_to_npz(source: Path, destination: Path, sonic_mjcf: Path) -> str:
    """Adapt a BONES motion to the CLIMB NPZ contract at SONIC's 50 Hz timeline."""
    import mujoco

    from gear_sonic.research.hygiene.motion_io import load_motion, resample_to

    motion = resample_to(load_motion(source), 50)
    model = mujoco.MjModel.from_xml_path(str(sonic_mjcf))
    frames = motion.num_frames
    dt = 1.0 / float(motion.fps)
    qpos = np.zeros((frames, model.nq), dtype=np.float64)
    qpos[:, :3] = motion.root_trans_offset
    quat_wxyz = motion.root_rot[:, [3, 0, 1, 2]].astype(np.float64)
    quat_wxyz /= np.linalg.norm(quat_wxyz, axis=1, keepdims=True)
    qpos[:, 3:7] = quat_wxyz
    qpos[:, 7:] = motion.dof

    qvel = np.zeros((frames, model.nv), dtype=np.float64)
    scratch = np.zeros(model.nv, dtype=np.float64)
    for frame in range(frames):
        lo = max(frame - 1, 0)
        hi = min(frame + 1, frames - 1)
        mujoco.mj_differentiatePos(model, scratch, (hi - lo) * dt, qpos[lo], qpos[hi])
        qvel[frame] = scratch

    body_pos = np.zeros((frames, 30, 3), dtype=np.float32)
    body_quat = np.zeros((frames, 30, 4), dtype=np.float32)
    body_lin_vel = np.zeros((frames, 30, 3), dtype=np.float32)
    body_ang_vel = np.zeros((frames, 30, 3), dtype=np.float32)
    body_pos[:, 0] = motion.root_trans_offset
    body_quat[..., 0] = 1.0
    body_quat[:, 0] = quat_wxyz
    body_lin_vel[:, 0] = qvel[:, :3]
    for frame in range(frames):
        body_ang_vel[frame, 0] = (
            quat_wxyz_to_matrix(quat_wxyz[frame]) @ qvel[frame, 3:6]
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        destination,
        joint_pos=motion.dof.astype(np.float32),
        joint_vel=qvel[:, 6:].astype(np.float32),
        body_pos_w=body_pos,
        body_quat_w=body_quat,
        body_lin_vel_w=body_lin_vel,
        body_ang_vel_w=body_ang_vel,
        fps=np.array([float(motion.fps)], dtype=np.float64),
    )
    return sha256_file(destination)


def adapt_amass_to_pkl(source: Path, destination: Path) -> str:
    """Adapt an AMASS-wbt NPZ to the SONIC motion container without resampling."""
    import joblib
    from scipy.spatial.transform import Rotation

    from gear_sonic.data_process.convert_soma_csv_to_motion_lib import DOF_AXIS

    with np.load(source) as data:
        dof = np.asarray(data["joint_pos"], dtype=np.float32)
        root_trans = np.asarray(data["body_pos_w"][:, 0], dtype=np.float32)
        root_wxyz = np.asarray(data["body_quat_w"][:, 0], dtype=np.float32)
        fps_value = float(np.asarray(data["fps"]).reshape(-1)[0])
    fps = int(round(fps_value))
    if abs(fps_value - fps) > 1e-6:
        raise ValueError(f"{source}: SONIC container requires integer fps, got {fps_value}")
    root_xyzw = root_wxyz[:, [1, 2, 3, 0]]
    root_xyzw /= np.linalg.norm(root_xyzw, axis=1, keepdims=True)
    pose_aa = np.zeros((dof.shape[0], 30, 3), dtype=np.float32)
    pose_aa[:, 0] = Rotation.from_quat(root_xyzw).as_rotvec().astype(np.float32)
    pose_aa[:, 1:] = DOF_AXIS[None, :, :] * dof[:, :, None]
    payload = {
        source.stem: {
            "root_trans_offset": root_trans,
            "pose_aa": pose_aa,
            "dof": dof,
            "root_rot": root_xyzw.astype(np.float32),
            "smpl_joints": np.zeros((dof.shape[0], 24, 3), dtype=np.float32),
            "fps": fps,
        }
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(payload, destination)
    return sha256_file(destination)


def prepare(args: argparse.Namespace) -> int:
    """Select the panel, verify joint layout, and materialize adapters."""
    add_sonic_repo(args.sonic_repo)
    output = args.output
    adapted_npz = output / "_adapted" / "bones_as_npz"
    adapted_pkl = output / "_adapted" / "amass_as_pkl"
    panel = select_panel(read_csv(args.sonic_csv), read_csv(args.climb_csv))

    climb_joints, climb_axes = xml_hinge_layout(args.climb_mjcf)
    sonic_joints, sonic_axes = xml_hinge_layout(args.sonic_mjcf)
    if len(climb_joints) != 29 or len(sonic_joints) != 29:
        raise ValueError(
            f"expected 29 hinge joints, found CLIMB={len(climb_joints)}, "
            f"SONIC={len(sonic_joints)}"
        )
    if climb_joints != sonic_joints:
        raise ValueError("CLIMB and SONIC hinge-joint names/orders differ")
    if not np.array_equal(climb_axes, sonic_axes):
        raise ValueError("CLIMB and SONIC hinge axes differ")

    selection_rows: list[dict[str, Any]] = []
    for row in panel:
        clip = row["clip"]
        if row["bank"] == "BONES-SEED":
            source = args.bones_bank / f"{clip}.pkl"
            destination = adapted_npz / f"{clip}.npz"
        else:
            source = args.amass_bank / f"{clip}.npz"
            destination = adapted_pkl / f"{clip}.pkl"
        if not source.is_file():
            raise FileNotFoundError(source)
        if row["bank"] == "BONES-SEED":
            adapted_sha = adapt_bones_to_npz(source, destination, args.sonic_mjcf)
        else:
            adapted_sha = adapt_amass_to_pkl(source, destination)
        selection_rows.append(
            {
                **row,
                "source_path": str(source.resolve()),
                "source_sha256": sha256_file(source),
                "adapted_path": str(destination.resolve()),
                "adapted_sha256": adapted_sha,
            }
        )

    write_csv(output / "selection.csv", selection_rows)
    manifest = {
        "kind": "feasibility_xcheck_selection",
        "selection_seed": SELECTION_SEED,
        "flag_rule": f"infeasible_frac > {FLAG_THRESHOLD}",
        "rows": len(selection_rows),
        "counts": {
            "bones_flagged": sum(
                row["bank"] == "BONES-SEED" and row["stratum"] == "flagged"
                for row in selection_rows
            ),
            "bones_feasible": sum(
                row["bank"] == "BONES-SEED" and row["stratum"] == "feasible"
                for row in selection_rows
            ),
            "amass_flagged": sum(
                row["bank"] == "AMASS-wbt-G1" and row["stratum"] == "flagged"
                for row in selection_rows
            ),
            "amass_feasible": sum(
                row["bank"] == "AMASS-wbt-G1" and row["stratum"] == "feasible"
                for row in selection_rows
            ),
        },
        "clip_44_required": CLIP_44,
        "joint_order_check": "29/29 names and axes exact",
        "climb_native_csv": str(args.climb_csv.resolve()),
        "climb_native_csv_sha256": sha256_file(args.climb_csv),
        "sonic_native_csv": str(args.sonic_csv.resolve()),
        "sonic_native_csv_sha256": sha256_file(args.sonic_csv),
        "climb_mjcf": str(args.climb_mjcf.resolve()),
        "climb_mjcf_sha256": sha256_file(args.climb_mjcf),
        "sonic_mjcf": str(args.sonic_mjcf.resolve()),
        "sonic_mjcf_sha256": sha256_file(args.sonic_mjcf),
        "selection_csv_sha256": sha256_file(output / "selection.csv"),
    }
    (output / "SELECTION.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


def spearman(left: list[float], right: list[float]) -> dict[str, float]:
    """Return Spearman rho and its asymptotic p-value."""
    from scipy.stats import spearmanr

    result = spearmanr(np.asarray(left), np.asarray(right))
    return {"rho": float(result.statistic), "pvalue": float(result.pvalue)}


def agreement_matrix(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute the CLIMB-by-SONIC strict-threshold agreement matrix."""
    matrix = {"both_flag": 0, "climb_only": 0, "sonic_only": 0, "neither_flag": 0}
    for row in rows:
        climb_flag = float(row["climb_infeasible_frac"]) > FLAG_THRESHOLD
        sonic_flag = float(row["sonic_infeasible_frac"]) > FLAG_THRESHOLD
        if climb_flag and sonic_flag:
            matrix["both_flag"] += 1
        elif climb_flag:
            matrix["climb_only"] += 1
        elif sonic_flag:
            matrix["sonic_only"] += 1
        else:
            matrix["neither_flag"] += 1
    total = len(rows)
    observed = (matrix["both_flag"] + matrix["neither_flag"]) / total
    climb_rate = (matrix["both_flag"] + matrix["climb_only"]) / total
    sonic_rate = (matrix["both_flag"] + matrix["sonic_only"]) / total
    expected = climb_rate * sonic_rate + (1.0 - climb_rate) * (1.0 - sonic_rate)
    kappa = (observed - expected) / (1.0 - expected) if expected < 1.0 else 1.0
    return {**matrix, "n": total, "agreement": observed, "cohen_kappa": kappa}


def load_json(path: Path) -> dict[str, Any]:
    """Load one JSON result."""
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def analyze(args: argparse.Namespace) -> int:
    """Join native and cross-screen outputs and write measured agreement."""
    selection = read_csv(args.output / "selection.csv")
    rows: list[dict[str, Any]] = []
    result_paths: list[Path] = []
    for selected in selection:
        clip = selected["clip"]
        native_infeasible = float(selected["native_infeasible_frac"])
        native_airborne = float(selected["native_airborne_frac"])
        if selected["bank"] == "BONES-SEED":
            result_path = args.climb_results / f"{clip}.json"
            cross = load_json(result_path)
            climb_infeasible = float(cross["infeasible_frac"])
            climb_airborne = float(cross["airborne_frac"])
            sonic_infeasible = native_infeasible
            sonic_airborne = native_airborne
        else:
            result_path = args.sonic_results / f"{clip}.json"
            cross = load_json(result_path)
            climb_infeasible = native_infeasible
            climb_airborne = native_airborne
            sonic_infeasible = float(cross["infeasible_frac"])
            sonic_airborne = float(cross["airborne_frac"])
        result_paths.append(result_path)
        climb_flag = climb_infeasible > FLAG_THRESHOLD
        sonic_flag = sonic_infeasible > FLAG_THRESHOLD
        rows.append(
            {
                "bank": selected["bank"],
                "stratum": selected["stratum"],
                "clip": clip,
                "climb_infeasible_frac": climb_infeasible,
                "sonic_infeasible_frac": sonic_infeasible,
                "climb_airborne_frac": climb_airborne,
                "sonic_airborne_frac": sonic_airborne,
                "climb_flag": int(climb_flag),
                "sonic_flag": int(sonic_flag),
                "flag_agree": int(climb_flag == sonic_flag),
            }
        )

    write_csv(args.output / "agreement.csv", rows)
    groups: dict[str, list[dict[str, Any]]] = {
        "all": rows,
        "BONES-SEED": [row for row in rows if row["bank"] == "BONES-SEED"],
        "AMASS-wbt-G1": [row for row in rows if row["bank"] == "AMASS-wbt-G1"],
    }
    statistics = {
        group: {
            "infeasible_frac_spearman": spearman(
                [float(row["climb_infeasible_frac"]) for row in subset],
                [float(row["sonic_infeasible_frac"]) for row in subset],
            ),
            "airborne_frac_spearman": spearman(
                [float(row["climb_airborne_frac"]) for row in subset],
                [float(row["sonic_airborne_frac"]) for row in subset],
            ),
            "flag_agreement": agreement_matrix(subset),
        }
        for group, subset in groups.items()
    }
    summary_path = args.output / "summary.json"
    summary_path.write_text(
        json.dumps(statistics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    completion = {
        "kind": "feasibility_xcheck",
        "exit_code": 0,
        "rows": len(rows),
        "flag_rule": f"infeasible_frac > {FLAG_THRESHOLD}",
        "statistics": statistics,
        "selection_sha256": sha256_file(args.output / "selection.csv"),
        "selection_manifest_sha256": sha256_file(args.output / "SELECTION.json"),
        "agreement_sha256": sha256_file(args.output / "agreement.csv"),
        "summary_sha256": sha256_file(summary_path),
        "result_files": len(result_paths),
        "result_sha256": {str(path.resolve()): sha256_file(path) for path in result_paths},
        "climb_screen_sha256": sha256_file(args.climb_screen),
        "sonic_screen_sha256": sha256_file(args.sonic_screen),
        "adapter_aggregator_sha256": sha256_file(Path(__file__)),
        "adapted_intermediates": (
            "not retained after hash verification; regenerate with the prepare subcommand"
        ),
        "sonic_runner_sentinel_sha256": sha256_file(
            args.sonic_results.parent / "COMPLETED.json"
        ),
    }
    completed_path = args.output / "COMPLETED.json"
    completed_path.write_text(
        json.dumps(completion, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(completion, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line interface."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--output", type=Path, required=True)
    prepare_parser.add_argument("--sonic-csv", type=Path, required=True)
    prepare_parser.add_argument("--climb-csv", type=Path, required=True)
    prepare_parser.add_argument("--bones-bank", type=Path, required=True)
    prepare_parser.add_argument("--amass-bank", type=Path, required=True)
    prepare_parser.add_argument("--sonic-repo", type=Path, required=True)
    prepare_parser.add_argument("--sonic-mjcf", type=Path, required=True)
    prepare_parser.add_argument("--climb-mjcf", type=Path, required=True)
    prepare_parser.set_defaults(function=prepare)

    analyze_parser = subparsers.add_parser("analyze")
    analyze_parser.add_argument("--output", type=Path, required=True)
    analyze_parser.add_argument("--climb-results", type=Path, required=True)
    analyze_parser.add_argument("--sonic-results", type=Path, required=True)
    analyze_parser.add_argument("--climb-screen", type=Path, required=True)
    analyze_parser.add_argument("--sonic-screen", type=Path, required=True)
    analyze_parser.set_defaults(function=analyze)
    return parser


def main() -> int:
    """Run the requested cross-check stage."""
    args = build_parser().parse_args()
    return int(args.function(args))


if __name__ == "__main__":
    raise SystemExit(main())
