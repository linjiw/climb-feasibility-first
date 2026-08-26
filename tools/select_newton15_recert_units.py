#!/usr/bin/env python3
"""Select two hash-bound DFRP v1 units for Newton 1.5 recertification.

This is a CPU-only preflight. It evaluates the midpoint legal 50-frame window of
every admissible exact unit under the pinned feasibility MJCF. The easy unit is
selected among byte-identical raw-feasible controls by minimum reference motion;
the contact-rich unit maximizes multi-contact occupancy and contact-set changes.
No policy or solver outcome is read.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any

import mujoco
import numpy as np


def sha256_file(path: Path) -> str:
    """Return a file's SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def contact_class(name: str) -> str:
    """Collapse the many foot capsules into left/right contact classes."""
    if "left_foot" in name:
        return "left_foot"
    if "right_foot" in name:
        return "right_foot"
    return name


def unit_diagnostics(
    unit: dict[str, Any],
    *,
    bank: Path,
    model: mujoco.MjModel,
    plane: int,
    robot_geoms: list[int],
    horizon: int,
    gap_m: float,
    expected_motion_hash: str,
) -> dict[str, Any]:
    """Compute reference-only kinematic and near-contact diagnostics."""
    motion_path = bank / f"{unit['clip']}.npz"
    with np.load(motion_path) as motion:
        joint_pos = np.asarray(motion["joint_pos"], dtype=np.float64)
        joint_vel = np.asarray(motion["joint_vel"], dtype=np.float64)
        body_pos = np.asarray(motion["body_pos_w"], dtype=np.float64)
        body_quat = np.asarray(motion["body_quat_w"], dtype=np.float64)
        body_lin_vel = np.asarray(motion["body_lin_vel_w"], dtype=np.float64)

    actual_hash = sha256_file(motion_path)
    if actual_hash != expected_motion_hash:
        raise ValueError(f"motion hash mismatch for {motion_path}")

    count = int(unit["legal_start_count"])
    start = int(unit["admissible_start_first"]) + (count - 1) // 2
    stop = start + horizon
    if stop >= int(unit["segment_stop"]):
        raise ValueError(f"unit {unit['unit_id']} midpoint window escapes support")

    data = mujoco.MjData(model)
    contact_sets: list[tuple[str, ...]] = []
    fromto = np.zeros(6, dtype=np.float64)
    for frame in range(start, stop):
        data.qpos[:3] = body_pos[frame, 0]
        data.qpos[3:7] = body_quat[frame, 0]
        data.qpos[7:] = joint_pos[frame]
        mujoco.mj_forward(model, data)
        active: set[str] = set()
        for geom in robot_geoms:
            distance = mujoco.mj_geomDistance(
                model, data, geom, plane, gap_m + 0.02, fromto
            )
            if distance <= gap_m:
                active.add(contact_class(model.geom(geom).name or f"geom_{geom}"))
        contact_sets.append(tuple(sorted(active)))

    changes = sum(
        current != previous
        for previous, current in itertools.pairwise(contact_sets)
    )
    class_counts = np.asarray([len(value) for value in contact_sets], dtype=float)
    nonfoot_frames = np.asarray(
        [any(value not in {"left_foot", "right_foot"} for value in values)
         for values in contact_sets],
        dtype=float,
    )
    return {
        "table_index": int(unit["table_index"]),
        "unit_id": int(unit["unit_id"]),
        "clip_id": int(unit["clip_id"]),
        "clip": str(unit["clip"]),
        "start_frame": start,
        "stop_frame_exclusive": stop,
        "legal_start_count": count,
        "unsupported_ratio_p95": float(unit["unsupported_ratio_p95"]),
        "joint_speed_rms_rad_s": float(
            np.sqrt(np.square(joint_vel[start:stop]).mean())
        ),
        "root_speed_mean_m_s": float(
            np.linalg.norm(body_lin_vel[start:stop, 0], axis=1).mean()
        ),
        "mean_contact_classes": float(class_counts.mean()),
        "multi_contact_fraction": float((class_counts >= 2).mean()),
        "nonfoot_candidate_fraction": float(nonfoot_frames.mean()),
        "contact_set_changes": int(changes),
        "motion_sha256": actual_hash,
    }


def main() -> int:
    """Select and record the two recertification units."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unit-table", type=Path, required=True)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--gap", type=float, default=0.06)
    args = parser.parse_args()

    table = json.loads(args.unit_table.read_text())
    horizon = int(table["horizon_steps"])
    sources = {int(row["clip_id"]): row for row in table["sources"]}
    model = mujoco.MjModel.from_xml_path(str(args.model))
    plane = mujoco.mj_name2id(
        model, mujoco.mjtObj.mjOBJ_GEOM, "terrain"
    )
    if plane < 0:
        raise ValueError("selection model has no terrain geom")
    robot_geoms = [
        geom
        for geom in range(model.ngeom)
        if geom != plane
        and (model.geom_contype[geom] or model.geom_conaffinity[geom])
    ]

    rows = [
        unit_diagnostics(
            unit,
            bank=args.bank,
            model=model,
            plane=plane,
            robot_geoms=robot_geoms,
            horizon=horizon,
            gap_m=args.gap,
            expected_motion_hash=str(sources[int(unit["clip_id"])]["motion_sha256"]),
        )
        for unit in table["admissible_units"]
        if int(unit["legal_start_count"]) >= 50
    ]
    for row in rows:
        row["dfrp_route"] = str(sources[row["clip_id"]]["dfrp_route"])

    controls = [row for row in rows if row["dfrp_route"] == "raw_feasible"]
    if not controls:
        raise ValueError("no raw-feasible control unit has at least 50 legal starts")
    easy = min(
        controls,
        key=lambda row: (
            row["joint_speed_rms_rad_s"],
            row["root_speed_mean_m_s"],
            row["contact_set_changes"],
            row["unsupported_ratio_p95"],
            row["table_index"],
        ),
    )
    contact_rich = max(
        rows,
        key=lambda row: (
            row["multi_contact_fraction"],
            row["contact_set_changes"],
            row["nonfoot_candidate_fraction"],
            row["mean_contact_classes"],
            -row["table_index"],
        ),
    )
    if easy["table_index"] == contact_rich["table_index"]:
        raise ValueError("easy and contact-rich selectors chose the same unit")

    result = {
        "schema_version": "newton15_recert_unit_selection/1",
        "classification": "unsealed CPU preflight; no policy or solver outcome read",
        "unit_table_file_sha256": sha256_file(args.unit_table),
        "unit_table_payload_sha256": table["unit_table_sha256"],
        "motion_bank": str(args.bank.resolve()),
        "model": str(args.model.resolve()),
        "model_sha256": sha256_file(args.model),
        "horizon_steps": horizon,
        "contact_candidate_gap_m": args.gap,
        "eligibility": "admissible exact units with at least 50 legal starts",
        "easy_rule": (
            "among raw_feasible controls, lexicographic minimum of joint-speed RMS, "
            "root speed, contact-set changes, unsupported-ratio p95, table index"
        ),
        "contact_rich_rule": (
            "lexicographic maximum of multi-contact fraction, contact-set changes, "
            "non-foot candidate fraction, mean contact classes, then lower table index"
        ),
        "easy": easy,
        "contact_rich": contact_rich,
        "eligible_unit_diagnostics": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(
        f"easy: table {easy['table_index']} {easy['clip']} start {easy['start_frame']}"
    )
    print(
        "contact-rich: table "
        f"{contact_rich['table_index']} {contact_rich['clip']} "
        f"start {contact_rich['start_frame']}"
    )
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
