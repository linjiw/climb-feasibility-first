"""Descriptive paired pose/work summaries with explicit survivor denominators."""

from __future__ import annotations

import numpy as np

from analyze_relative_policy import aggregate_rows

POSE_METRICS = ("common_root_relative_mpkpe_m_mean",
                "common_anchor_orientation_error_rad_mean")
WORK = "absolute_mechanical_work_per_actuator_j"


def mean_or_none(values: list[float]) -> float | None:
    return float(np.mean(values)) if values else None


def paired_secondary(left: list[dict], right: list[dict], conditions: list[dict],
                     clips: list[str]) -> dict:
    """Pair full-horizon successes for pose; retain every condition for work.

    Caller authenticates artifacts before providing rows. Pose summaries are
    conditioned on both arms succeeding and cannot replace all-panel outcomes.
    Work is accumulated until failure/horizon, not battery energy or efficiency.
    """
    for rows in (left, right):
        aggregate_rows(rows, conditions, clips)
        for row in rows:
            if str(row["success"]) not in ("0", "1"):
                raise ValueError("invalid success flag")
            work = float(row[WORK])
            if not np.isfinite(work) or work < 0:
                raise ValueError("invalid mechanical work")
            if str(row["success"]) == "1" and abs(float(row["survival_s"]) - 3.0) > 1e-6:
                raise ValueError("success flag contradicts survived horizon")
            if float(row["survival_s"]) == 0 and work != 0:
                raise ValueError("nonzero work without observed exposure")
    maps = [{row["condition_id"]: row for row in rows} for rows in (left, right)]
    grouped = {clip: [] for clip in clips}
    for condition in conditions:
        grouped[condition["clip"]].append(condition["condition_id"])
    per_clip = {}
    for clip, identities in grouped.items():
        common = [identity for identity in identities
                  if all(str(rows[identity]["success"]) == "1" for rows in maps)]
        counts = {"conditions": len(identities), "common_successes": len(common)}
        work = {}
        pose = {}
        for label, rows in zip(("left", "right"), maps):
            counts[f"{label}_successes"] = sum(str(rows[i]["success"]) == "1" for i in identities)
            total_work = sum(float(rows[i][WORK]) for i in identities)
            exposure = sum(float(rows[i]["survival_s"]) for i in identities)
            work[label] = {"total_work_per_actuator_j": total_work,
                           "observed_exposure_s": exposure,
                           "work_per_condition_j": total_work / len(identities),
                           "observed_time_per_condition_s": exposure / len(identities),
                           "exposure_weighted_power_per_actuator_w": total_work / exposure if exposure else None}
            pose[label] = {key: mean_or_none([float(rows[i][key]) for i in common]) for key in POSE_METRICS}
        per_clip[clip] = {"counts": counts, "work_all_conditions": work,
                          "pose_common_successes": pose,
                          "pose_left_minus_right": {key: pose["left"][key] - pose["right"][key]
                                                    if common else None for key in POSE_METRICS},
                          "work_left_minus_right_j": work["left"]["work_per_condition_j"] - work["right"]["work_per_condition_j"]}
    covered = [row for row in per_clip.values() if row["counts"]["common_successes"]]
    return {"classification": "descriptive; outcome-conditioned pose and all-condition work",
            "panel_clips": len(clips), "covered_pose_clips": len(covered),
            "conditions": len(conditions),
            "common_successes": sum(row["counts"]["common_successes"] for row in per_clip.values()),
            "pose_left_minus_right_covered_clip_mean": {
                key: mean_or_none([row["pose_left_minus_right"][key] for row in covered]) for key in POSE_METRICS},
            "work_left_minus_right_all_clip_mean_j": mean_or_none([
                row["work_left_minus_right_j"] for row in per_clip.values()]),
            "per_clip": per_clip,
            "limitations": ["Common-success pose changes its population across arm pairs and seeds.",
                            "Empty common-success cells remain null with zero counts; never impute zero error.",
                            "Less work can reflect earlier failure; interpret with exposure and primary survival.",
                            "Work is absolute mechanical work per actuator during observed steps, not battery energy."]}
