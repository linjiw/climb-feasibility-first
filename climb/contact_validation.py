"""Outcome-blind scoring utilities for contact-proxy validation."""

from __future__ import annotations

import csv
from collections import defaultdict
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np

from .contact_timing import EVENT_NAMES, FOOT_NAMES, match_event_frames

EventKey = tuple[str, str, str]


def read_annotation_csv(
    path: Path,
    *,
    allowed_clips: set[str],
    frame_counts: dict[str, int],
) -> tuple[str, dict[EventKey, np.ndarray], set[tuple[str, str, str, int]]]:
    """Read and strictly validate an independent or consensus annotation file."""
    expected_fields = [
        "rater_id",
        "clip",
        "foot",
        "event",
        "frame",
        "uncertain",
        "notes",
    ]
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != expected_fields:
            raise ValueError(f"{path}: expected columns {expected_fields}")
        rows = list(reader)
    rater_ids = {row["rater_id"] for row in rows}
    if len(rater_ids) != 1 or "" in rater_ids:
        raise ValueError(f"{path}: exactly one nonempty rater_id is required")

    frames: dict[EventKey, list[int]] = defaultdict(list)
    uncertain: set[tuple[str, str, str, int]] = set()
    seen: set[tuple[str, str, str, int]] = set()
    sequences: dict[tuple[str, str], list[tuple[int, str]]] = defaultdict(list)
    for row in rows:
        clip = row["clip"]
        foot = row["foot"]
        event = row["event"]
        if clip not in allowed_clips:
            raise ValueError(f"{path}: undeclared clip {clip}")
        if foot not in FOOT_NAMES or event not in EVENT_NAMES:
            raise ValueError(f"{path}: invalid foot/event {foot}/{event}")
        try:
            frame = int(row["frame"])
        except ValueError as error:
            raise ValueError(f"{path}: noninteger frame") from error
        if not 0 <= frame < frame_counts[clip]:
            raise ValueError(f"{path}: frame out of range for {clip}: {frame}")
        if row["uncertain"] not in {"0", "1"}:
            raise ValueError(f"{path}: uncertain must be 0 or 1")
        identity = (clip, foot, event, frame)
        if identity in seen:
            raise ValueError(f"{path}: duplicate event {identity}")
        seen.add(identity)
        frames[(clip, foot, event)].append(frame)
        sequences[(clip, foot)].append((frame, event))
        if row["uncertain"] == "1":
            uncertain.add(identity)

    for identity, sequence in sequences.items():
        ordered = sorted(sequence)
        if any(
            earlier[1] == later[1] or earlier[0] == later[0]
            for earlier, later in pairwise(ordered)
        ):
            raise ValueError(f"{path}: events do not alternate for {identity}")
    arrays = {
        key: np.asarray(sorted(values), dtype=np.int64)
        for key, values in frames.items()
    }
    return next(iter(rater_ids)), arrays, uncertain


def read_completion_csv(
    path: Path,
    *,
    expected_clips: set[str],
    expected_rater_id: str,
) -> None:
    """Require an explicit completed row for every clip, including zero-event clips."""
    expected_fields = ["rater_id", "clip", "complete"]
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != expected_fields:
            raise ValueError(f"{path}: expected columns {expected_fields}")
        rows = list(reader)
    if any(
        row["rater_id"] != expected_rater_id or row["complete"] != "1"
        for row in rows
    ):
        raise ValueError(f"{path}: rater mismatch or incomplete row")
    clips = [row["clip"] for row in rows]
    if len(clips) != len(set(clips)) or set(clips) != expected_clips:
        raise ValueError(f"{path}: completion coverage mismatch")


def score_event_maps(
    expected: dict[EventKey, np.ndarray],
    observed: dict[EventKey, np.ndarray],
    *,
    clips: set[str],
    tolerance_frames: int,
) -> dict[str, Any]:
    """Score pooled and foot/event-subgroup event agreement."""
    total = {"tp": 0, "fp": 0, "fn": 0}
    errors: list[int] = []
    subgroup: dict[str, Any] = {}
    empty = np.empty(0, dtype=np.int64)
    for foot in FOOT_NAMES:
        for event in EVENT_NAMES:
            counts = {"tp": 0, "fp": 0, "fn": 0}
            group_errors: list[int] = []
            for clip in sorted(clips):
                match = match_event_frames(
                    expected.get((clip, foot, event), empty),
                    observed.get((clip, foot, event), empty),
                    tolerance_frames,
                )
                for name in counts:
                    counts[name] += int(match[name])
                group_errors.extend(abs(value) for value in match["signed_errors_frames"])
            denominator = 2 * counts["tp"] + counts["fp"] + counts["fn"]
            name = f"{foot}_{event}"
            subgroup[name] = {
                **counts,
                "f1": (
                    float(2 * counts["tp"] / denominator)
                    if denominator
                    else float("nan")
                ),
                "median_absolute_timing_error_frames": (
                    float(np.median(group_errors))
                    if group_errors
                    else float("nan")
                ),
            }
            for count_name in total:
                total[count_name] += counts[count_name]
            errors.extend(group_errors)

    denominator = 2 * total["tp"] + total["fp"] + total["fn"]
    subgroup_f1 = [record["f1"] for record in subgroup.values()]
    finite_subgroup_f1 = [value for value in subgroup_f1 if np.isfinite(value)]
    return {
        **total,
        "expected_events": total["tp"] + total["fn"],
        "observed_events": total["tp"] + total["fp"],
        "micro_f1": float(2 * total["tp"] / denominator) if denominator else float("nan"),
        "minimum_subgroup_f1": (
            float(min(finite_subgroup_f1))
            if finite_subgroup_f1
            else float("nan")
        ),
        "median_absolute_timing_error_frames": (
            float(np.median(errors)) if errors else float("nan")
        ),
        "subgroups": subgroup,
        "tolerance_frames": tolerance_frames,
    }


def filter_uncertain(
    events: dict[EventKey, np.ndarray],
    uncertain: set[tuple[str, str, str, int]],
) -> dict[EventKey, np.ndarray]:
    """Remove consensus events marked uncertain for sensitivity analysis."""
    filtered = {}
    for key, frames in events.items():
        clip, foot, event = key
        filtered[key] = np.asarray(
            [
                frame
                for frame in frames
                if (clip, foot, event, int(frame)) not in uncertain
            ],
            dtype=np.int64,
        )
    return filtered
