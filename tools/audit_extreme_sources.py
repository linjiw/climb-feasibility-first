#!/usr/bin/env python3
"""Build the 5+5 CNRS/Transitions geometry audit and inspection panel.

Selection is deterministic and spans the native strict-flag severity range.
The tool recomputes lowest collision-geometry clearance directly from each
reference pose under the pinned CLIMB G1 MJCF, writes frame-level traces, and
renders one panel containing a representative airborne pose and its trace for
every clip.  Human verdicts live in a separate JSON and are joined only after
the panel has been inspected.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mujoco
import numpy as np


FLAG_THRESHOLD = 0.10
GAP_M = 0.06
SOURCE_PREFIXES = {
    "CNRS": "CNRS_",
    "Transitions": "Transitions_",
}


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of one file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV as dictionaries."""
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write dictionaries with stable columns and LF endings."""
    if not rows:
        raise ValueError(f"refusing to write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def select_clips(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Select five strict-flag severity quantiles from each source."""
    selected: list[dict[str, Any]] = []
    quantiles = np.linspace(0.0, 1.0, 5)
    for source, prefix in SOURCE_PREFIXES.items():
        candidates = sorted(
            [
                row
                for row in rows
                if row["clip"].startswith(prefix)
                and float(row["infeasible_frac"]) > FLAG_THRESHOLD
            ],
            key=lambda row: (float(row["infeasible_frac"]), row["clip"]),
        )
        indices = np.rint(np.linspace(0, len(candidates) - 1, 5)).astype(int)
        for quantile, index in zip(quantiles, indices):
            row = candidates[int(index)]
            selected.append(
                {
                    "source": source,
                    "severity_quantile": float(quantile),
                    "clip": row["clip"],
                    "screen_infeasible_frac": float(row["infeasible_frac"]),
                    "screen_airborne_frac": float(row["airborne_frac"]),
                    "source_flagged_count": len(candidates),
                }
            )
    return selected


def robot_layout(model: mujoco.MjModel) -> tuple[int, list[int], list[tuple[int, int]]]:
    """Return plane, collision geoms, and NPZ-body skeleton edges."""
    plane = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "terrain")
    if plane < 0:
        raise ValueError("pinned model has no terrain geom")
    collision = [
        geom
        for geom in range(model.ngeom)
        if geom != plane and (model.geom_contype[geom] or model.geom_conaffinity[geom])
    ]
    robot_model_bodies = [
        index
        for index in range(1, model.nbody)
        if (mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, index) or "").startswith("robot/")
    ]
    if len(robot_model_bodies) != 30:
        raise ValueError(f"expected 30 robot bodies, found {len(robot_model_bodies)}")
    npz_index = {model_index: index for index, model_index in enumerate(robot_model_bodies)}
    edges: list[tuple[int, int]] = []
    for model_body in robot_model_bodies:
        parent = int(model.body_parentid[model_body])
        if parent in npz_index:
            edges.append((npz_index[parent], npz_index[model_body]))
    return int(plane), collision, edges


def longest_true_run(mask: np.ndarray) -> tuple[int, int]:
    """Return inclusive bounds of the longest true run, or the global maximum slot."""
    padded = np.pad(mask.astype(np.int8), (1, 1))
    changes = np.flatnonzero(np.diff(padded))
    if changes.size:
        starts = changes[0::2]
        stops = changes[1::2] - 1
        lengths = stops - starts + 1
        best = int(np.argmax(lengths))
        return int(starts[best]), int(stops[best])
    return 0, 0


def compute_clip(
    path: Path,
    model: mujoco.MjModel,
    plane: int,
    collision: list[int],
) -> tuple[dict[str, Any], list[dict[str, Any]], np.ndarray, np.ndarray]:
    """Compute geometry clearance and select a representative airborne frame."""
    with np.load(path) as data:
        joint_pos = np.asarray(data["joint_pos"], dtype=np.float64)
        body_pos = np.asarray(data["body_pos_w"], dtype=np.float64)
        body_quat = np.asarray(data["body_quat_w"], dtype=np.float64)
        fps = float(np.asarray(data["fps"]).reshape(-1)[0])
    frames = joint_pos.shape[0]
    data = mujoco.MjData(model)
    clearance = np.empty(frames, dtype=np.float64)
    fromto = np.zeros(6, dtype=np.float64)
    for frame in range(frames):
        data.qpos[:3] = body_pos[frame, 0]
        data.qpos[3:7] = body_quat[frame, 0]
        data.qpos[7:] = joint_pos[frame]
        mujoco.mj_forward(model, data)
        clearance[frame] = min(
            float(mujoco.mj_geomDistance(model, data, geom, plane, 2.0, fromto))
            for geom in collision
        )

    airborne = clearance > GAP_M
    run_start, run_stop = longest_true_run(airborne)
    if airborne.any():
        representative = (run_start + run_stop) // 2
    else:
        representative = int(np.argmax(clearance))
    root_xy = body_pos[:, 0, :2]
    root_path_m = float(np.linalg.norm(np.diff(root_xy, axis=0), axis=1).sum())
    summary = {
        "frames": frames,
        "fps": fps,
        "duration_s": frames / fps,
        "clearance_m_p50": float(np.percentile(clearance, 50)),
        "clearance_m_p90": float(np.percentile(clearance, 90)),
        "clearance_m_max": float(clearance.max()),
        "geometry_airborne_frac": float(airborne.mean()),
        "longest_airborne_start_s": run_start / fps,
        "longest_airborne_stop_s": run_stop / fps,
        "longest_airborne_duration_s": (run_stop - run_start + 1) / fps if airborne.any() else 0.0,
        "representative_frame": representative,
        "representative_time_s": representative / fps,
        "representative_clearance_m": float(clearance[representative]),
        "root_z_m_p50": float(np.percentile(body_pos[:, 0, 2], 50)),
        "root_z_m_min": float(body_pos[:, 0, 2].min()),
        "root_z_m_max": float(body_pos[:, 0, 2].max()),
        "root_xy_path_m": root_path_m,
    }
    trace = [
        {
            "frame": frame,
            "time_s": frame / fps,
            "lowest_geom_clearance_m": float(clearance[frame]),
            "geometry_airborne": int(airborne[frame]),
        }
        for frame in range(frames)
    ]
    return summary, trace, body_pos, clearance


def travel_axis(body_pos: np.ndarray) -> np.ndarray:
    """Choose a horizontal projection axis from net root travel."""
    delta = body_pos[-1, 0, :2] - body_pos[0, 0, :2]
    norm = float(np.linalg.norm(delta))
    if norm < 0.05:
        return np.array([1.0, 0.0])
    return delta / norm


def short_clip(clip: str, limit: int = 41) -> str:
    """Shorten long clip labels without losing their action suffix."""
    if len(clip) <= limit:
        return clip
    return f"{clip[:18]}…{clip[-(limit - 19):]}"


def draw_pose(
    axis: plt.Axes,
    body_pos: np.ndarray,
    frame: int,
    edges: list[tuple[int, int]],
    clearance_m: float,
    title: str,
) -> None:
    """Draw a travel-plane stick view at one inspected frame."""
    direction = travel_axis(body_pos)
    points = body_pos[frame]
    horizontal = points[:, :2] @ direction
    horizontal -= float(points[0, :2] @ direction)
    vertical = points[:, 2]
    for parent, child in edges:
        axis.plot(
            [horizontal[parent], horizontal[child]],
            [vertical[parent], vertical[child]],
            color="#263238",
            linewidth=1.7,
            solid_capstyle="round",
        )
    color = "#c62828" if clearance_m > GAP_M else "#1565c0"
    axis.scatter(horizontal, vertical, s=11, color=color, zorder=3)
    axis.axhline(0.0, color="#6d4c41", linewidth=1.2)
    axis.fill_between([-0.8, 0.8], -0.04, 0.0, color="#d7ccc8", alpha=0.7)
    axis.set_xlim(-0.75, 0.75)
    axis.set_ylim(-0.05, max(1.25, float(vertical.max()) + 0.1))
    axis.set_aspect("equal", adjustable="box")
    axis.set_title(title, fontsize=8.2, loc="left")
    axis.set_xlabel("travel axis [m]", fontsize=7)
    axis.set_ylabel("z [m]", fontsize=7)
    axis.tick_params(labelsize=7)


def draw_trace(
    axis: plt.Axes,
    clearance: np.ndarray,
    fps: float,
    frame: int,
    title: str,
) -> None:
    """Draw the full lowest-geometry clearance trace."""
    time_s = np.arange(clearance.size) / fps
    axis.plot(time_s, 100.0 * clearance, color="#37474f", linewidth=1.0)
    axis.fill_between(
        time_s,
        100.0 * clearance,
        100.0 * GAP_M,
        where=clearance > GAP_M,
        color="#ef5350",
        alpha=0.28,
        interpolate=True,
    )
    axis.axhline(100.0 * GAP_M, color="#c62828", linestyle="--", linewidth=1.0)
    axis.axvline(frame / fps, color="#ff8f00", linewidth=1.0)
    axis.set_title(title, fontsize=8.2, loc="left")
    axis.set_xlabel("time [s]", fontsize=7)
    axis.set_ylabel("lowest clearance [cm]", fontsize=7)
    axis.tick_params(labelsize=7)
    low = min(-2.0, float(100.0 * clearance.min()) - 1.0)
    high = max(12.0, float(np.percentile(100.0 * clearance, 99)) + 2.0)
    axis.set_ylim(low, high)
    axis.grid(alpha=0.18, linewidth=0.5)


def load_verdicts(path: Path | None) -> dict[str, dict[str, str]]:
    """Load the separately authored hand-inspection verdicts."""
    if path is None:
        return {}
    with path.open(encoding="utf-8") as handle:
        verdicts = json.load(handle)
    for clip, record in verdicts.items():
        if record.get("verdict") not in {"ingest", "content", "scene-mismatch"}:
            raise ValueError(f"{clip}: invalid verdict {record.get('verdict')!r}")
        if not record.get("note"):
            raise ValueError(f"{clip}: verdict needs a non-empty note")
    return verdicts


def main() -> int:
    """Run the deterministic audit."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--verdicts", type=Path)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    selected = select_clips(read_csv(args.features))
    verdicts = load_verdicts(args.verdicts)
    model = mujoco.MjModel.from_xml_path(str(args.model))
    plane, collision, edges = robot_layout(model)
    computed: dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]] = {}
    summaries: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []

    for selected_row in selected:
        clip = selected_row["clip"]
        path = args.bank / f"{clip}.npz"
        summary, trace, body_pos, clearance = compute_clip(path, model, plane, collision)
        review = verdicts.get(clip, {"verdict": "pending", "note": "visual review pending"})
        summaries.append(
            {
                **selected_row,
                **summary,
                "verdict": review["verdict"],
                "verdict_note": review["note"],
                "motion_sha256": sha256_file(path),
            }
        )
        traces.extend({"source": selected_row["source"], "clip": clip, **row} for row in trace)
        computed[clip] = (summary, body_pos, clearance)

    figure, axes = plt.subplots(5, 4, figsize=(17, 18), constrained_layout=True)
    for row_index, quantile in enumerate(np.linspace(0.0, 1.0, 5)):
        for column_pair, source in enumerate(("CNRS", "Transitions")):
            selected_row = next(
                row
                for row in summaries
                if row["source"] == source and row["severity_quantile"] == quantile
            )
            clip = selected_row["clip"]
            summary, body_pos, clearance = computed[clip]
            pose_axis = axes[row_index, column_pair * 2]
            trace_axis = axes[row_index, column_pair * 2 + 1]
            quantile_label = int(round(100 * quantile))
            draw_pose(
                pose_axis,
                body_pos,
                int(summary["representative_frame"]),
                edges,
                float(summary["representative_clearance_m"]),
                f"{source} q{quantile_label}: {short_clip(clip)}\n"
                f"t={summary['representative_time_s']:.2f}s, clearance "
                f"{100 * summary['representative_clearance_m']:.1f} cm",
            )
            draw_trace(
                trace_axis,
                clearance,
                float(summary["fps"]),
                int(summary["representative_frame"]),
                f"I={selected_row['screen_infeasible_frac']:.3f}, "
                f"A={selected_row['screen_airborne_frac']:.3f}, "
                f"median={100 * summary['clearance_m_p50']:.1f} cm",
            )
    figure.suptitle(
        "Extreme-source audit: representative airborne poses and lowest-geometry clearance\n"
        "red fill = clearance above the pinned 6 cm contact-candidate gap; orange = rendered frame",
        fontsize=14,
    )
    panel_path = args.out / "extreme_source_panel.png"
    figure.savefig(panel_path, dpi=180, facecolor="white")
    plt.close(figure)

    summary_path = args.out / "clips.csv"
    trace_path = args.out / "clearance_trace.csv"
    write_csv(summary_path, summaries)
    write_csv(trace_path, traces)
    completion = {
        "kind": "extreme_source_audit",
        "exit_code": 0,
        "selection": "strict-flag severity quantiles 0/25/50/75/100 within source",
        "flag_rule": f"infeasible_frac > {FLAG_THRESHOLD}",
        "gap_m": GAP_M,
        "rows": len(summaries),
        "trace_rows": len(traces),
        "verdicts_complete": all(row["verdict"] != "pending" for row in summaries),
        "model_sha256": sha256_file(args.model),
        "features_sha256": sha256_file(args.features),
        "tool_sha256": sha256_file(Path(__file__)),
        "clips_csv_sha256": sha256_file(summary_path),
        "trace_csv_sha256": sha256_file(trace_path),
        "panel_sha256": sha256_file(panel_path),
        "verdicts_sha256": sha256_file(args.verdicts) if args.verdicts else None,
    }
    completed_path = args.out / "COMPLETED.json"
    completed_path.write_text(
        json.dumps(completion, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(completion, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
