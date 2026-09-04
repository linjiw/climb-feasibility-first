#!/usr/bin/env python3
"""Validate the fixed contact proxy against blinded manual event labels."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from climb.contact_timing import EVENT_NAMES, FOOT_NAMES, event_frames
from climb.contact_validation import (
    EventKey,
    filter_uncertain,
    read_annotation_csv,
    read_completion_csv,
    score_event_maps,
)

SCHEMA_VERSION = "contact_proxy_validation/1"
TOLERANCE_FRAMES = 2
GATES = {
    "minimum_total_consensus_events": 40,
    "minimum_consensus_events_per_subgroup": 8,
    "minimum_inter_rater_micro_f1": 0.90,
    "minimum_inter_rater_subgroup_f1": 0.80,
    "minimum_proxy_micro_f1": 0.85,
    "minimum_proxy_subgroup_f1": 0.75,
    "maximum_proxy_median_timing_error_frames": 2.0,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _artifact(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise FileNotFoundError(path)
    return {"path": str(path), "sha256": sha256_file(path)}


def _write_immutable(path: Path, payload: bytes) -> None:
    if path.exists():
        if path.read_bytes() != payload:
            raise FileExistsError(f"refusing to replace differing artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _selected_validation_clips(path: Path) -> set[str]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    clips = {row["clip"] for row in rows if row["split"] == "validation"}
    if len(clips) != 10:
        raise ValueError("contact-validation panel must contain 10 held-out clips")
    return clips


def _proxy_events(
    proxy_manifest_path: Path,
    *,
    clips: set[str],
    expected_motion_hashes: dict[str, str],
) -> tuple[dict[EventKey, np.ndarray], dict[str, int], dict[str, Any]]:
    manifest = json.loads(proxy_manifest_path.read_text())
    if manifest.get("schema_version") != "reference_contact_proxy/1":
        raise ValueError("unsupported reference-contact proxy manifest")
    builder = Path("tools/build_reference_contact_labels.py")
    if manifest.get("builder_sha256") != sha256_file(builder):
        raise ValueError("reference-contact builder hash mismatch")
    model_record = manifest.get("inputs", {}).get("model", {})
    model_path = Path(model_record.get("path", ""))
    if not model_path.is_file() or model_record.get("sha256") != sha256_file(model_path):
        raise ValueError("reference-contact model hash mismatch")
    records = manifest.get("clips", {})
    if not clips.issubset(records):
        raise ValueError("proxy manifest does not cover held-out clips")

    events: dict[EventKey, np.ndarray] = {}
    frame_counts: dict[str, int] = {}
    for clip in sorted(clips):
        record = records[clip]
        if record.get("source_motion_sha256") != expected_motion_hashes[clip]:
            raise ValueError(f"proxy source hash mismatch: {clip}")
        artifact = record.get("artifact", {})
        label_path = Path(artifact.get("path", ""))
        if not label_path.is_file() or artifact.get("sha256") != sha256_file(label_path):
            raise ValueError(f"proxy artifact hash mismatch: {clip}")
        with np.load(label_path, allow_pickle=False) as arrays:
            contact = np.asarray(arrays["contact"], dtype=bool)
            fps = float(arrays["fps"])
        if contact.ndim != 2 or contact.shape[1] != 2:
            raise ValueError(f"invalid contact-mask shape: {clip}")
        if int(record.get("frames", -1)) != contact.shape[0] or not np.isclose(
            fps, 50.0
        ):
            raise ValueError(f"proxy frame/fps mismatch: {clip}")
        frame_counts[clip] = contact.shape[0]
        for foot_index, foot in enumerate(FOOT_NAMES):
            transitions = event_frames(contact[:, foot_index])
            for event in EVENT_NAMES:
                events[(clip, foot, event)] = transitions[event]
    return events, frame_counts, manifest


def _consensus_support(events: dict[EventKey, np.ndarray]) -> dict[str, Any]:
    counts = {
        f"{foot}_{event}": int(
            sum(
                len(frames)
                for (clip_name, key_foot, key_event), frames in events.items()
                if key_foot == foot and key_event == event
            )
        )
        for foot in FOOT_NAMES
        for event in EVENT_NAMES
    }
    return {
        "total_events": sum(counts.values()),
        "minimum_subgroup_events": min(counts.values()),
        "subgroups": counts,
    }


def _status(
    support: dict[str, Any],
    inter_rater: dict[str, Any],
    proxy: dict[str, Any],
) -> tuple[str, dict[str, bool]]:
    support_gates = {
        "total_consensus_events": (
            support["total_events"] >= GATES["minimum_total_consensus_events"]
        ),
        "consensus_events_per_subgroup": (
            support["minimum_subgroup_events"]
            >= GATES["minimum_consensus_events_per_subgroup"]
        ),
    }
    if not all(support_gates.values()):
        return "insufficient_support", support_gates
    validation_gates = {
        **support_gates,
        "inter_rater_micro_f1": (
            inter_rater["micro_f1"] >= GATES["minimum_inter_rater_micro_f1"]
        ),
        "inter_rater_subgroup_f1": (
            inter_rater["minimum_subgroup_f1"]
            >= GATES["minimum_inter_rater_subgroup_f1"]
        ),
        "proxy_micro_f1": proxy["micro_f1"] >= GATES["minimum_proxy_micro_f1"],
        "proxy_subgroup_f1": (
            proxy["minimum_subgroup_f1"] >= GATES["minimum_proxy_subgroup_f1"]
        ),
        "proxy_median_timing_error": (
            proxy["median_absolute_timing_error_frames"]
            <= GATES["maximum_proxy_median_timing_error_frames"]
        ),
    }
    return (
        "validated" if all(validation_gates.values()) else "failed_validation",
        validation_gates,
    )


def validate(
    panel_path: Path,
    panel_manifest_path: Path,
    proxy_manifest_path: Path,
    render_manifest_path: Path,
    rater_a_path: Path,
    rater_a_completion_path: Path,
    rater_b_path: Path,
    rater_b_completion_path: Path,
    consensus_path: Path,
    consensus_completion_path: Path,
) -> dict[str, Any]:
    """Validate artifacts, calculate agreement, and apply all declared gates."""
    panel_manifest = json.loads(panel_manifest_path.read_text())
    if panel_manifest.get("schema_version") != "contact_validation_panel/1":
        raise ValueError("unsupported contact-validation panel manifest")
    if panel_manifest.get("output", {}).get("sha256") != sha256_file(panel_path):
        raise ValueError("contact-validation panel hash mismatch")
    selector = Path("tools/build_contact_validation_panel.py")
    if panel_manifest.get("builder_sha256") != sha256_file(selector):
        raise ValueError("contact-validation selector hash mismatch")
    clips = _selected_validation_clips(panel_path)
    motion_hashes = panel_manifest.get("motion_sha256", {})
    if not clips.issubset(motion_hashes):
        raise ValueError("validation panel lacks source-motion hashes")

    proxy_events, frame_counts, proxy_manifest = _proxy_events(
        proxy_manifest_path,
        clips=clips,
        expected_motion_hashes=motion_hashes,
    )
    render_manifest = json.loads(render_manifest_path.read_text())
    if render_manifest.get("schema_version") != "contact_annotation_renders/1":
        raise ValueError("unsupported contact-annotation render manifest")
    renderer = Path("tools/render_contact_validation.py")
    if render_manifest.get("renderer_sha256") != sha256_file(renderer):
        raise ValueError("contact-annotation renderer hash mismatch")
    if render_manifest.get("inputs", {}).get("panel_manifest", {}).get(
        "sha256"
    ) != sha256_file(panel_manifest_path):
        raise ValueError("render manifest does not bind the validation panel")
    if render_manifest.get("inputs", {}).get("model", {}).get(
        "sha256"
    ) != proxy_manifest.get("inputs", {}).get("model", {}).get("sha256"):
        raise ValueError("render and proxy model hashes differ")
    render_outputs = render_manifest.get("outputs", {})
    if not clips.issubset(render_outputs):
        raise ValueError("render manifest does not cover held-out clips")
    for clip in clips:
        render = render_outputs[clip]
        artifact = render.get("artifact", {})
        video_path = Path(artifact.get("path", ""))
        if (
            render.get("source_motion_sha256") != motion_hashes[clip]
            or not video_path.is_file()
            or artifact.get("sha256") != sha256_file(video_path)
        ):
            raise ValueError(f"render provenance mismatch: {clip}")
    rater_a_id, rater_a, _ = read_annotation_csv(
        rater_a_path, allowed_clips=clips, frame_counts=frame_counts
    )
    rater_b_id, rater_b, _ = read_annotation_csv(
        rater_b_path, allowed_clips=clips, frame_counts=frame_counts
    )
    consensus_id, consensus, uncertain = read_annotation_csv(
        consensus_path, allowed_clips=clips, frame_counts=frame_counts
    )
    if rater_a_id == rater_b_id or consensus_id != "consensus":
        raise ValueError("independent raters must differ and consensus id must be 'consensus'")
    read_completion_csv(
        rater_a_completion_path,
        expected_clips=clips,
        expected_rater_id=rater_a_id,
    )
    read_completion_csv(
        rater_b_completion_path,
        expected_clips=clips,
        expected_rater_id=rater_b_id,
    )
    read_completion_csv(
        consensus_completion_path,
        expected_clips=clips,
        expected_rater_id=consensus_id,
    )

    inter_rater = score_event_maps(
        rater_a,
        rater_b,
        clips=clips,
        tolerance_frames=TOLERANCE_FRAMES,
    )
    proxy = score_event_maps(
        consensus,
        proxy_events,
        clips=clips,
        tolerance_frames=TOLERANCE_FRAMES,
    )
    sensitivity = score_event_maps(
        filter_uncertain(consensus, uncertain),
        proxy_events,
        clips=clips,
        tolerance_frames=TOLERANCE_FRAMES,
    )
    support = _consensus_support(consensus)
    status, gates = _status(support, inter_rater, proxy)
    inputs = {
        "panel": _artifact(panel_path),
        "panel_manifest": _artifact(panel_manifest_path),
        "proxy_manifest": _artifact(proxy_manifest_path),
        "render_manifest": _artifact(render_manifest_path),
        "rater_a": _artifact(rater_a_path),
        "rater_a_completion": _artifact(rater_a_completion_path),
        "rater_b": _artifact(rater_b_path),
        "rater_b_completion": _artifact(rater_b_completion_path),
        "consensus": _artifact(consensus_path),
        "consensus_completion": _artifact(consensus_completion_path),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "classification": "measured held-out contact-instrument validation",
        "status": status,
        "tolerance_frames": TOLERANCE_FRAMES,
        "gates": GATES,
        "gate_results": gates,
        "consensus_support": support,
        "inter_rater": inter_rater,
        "proxy_vs_consensus": proxy,
        "sensitivity_excluding_uncertain_consensus_events": sensitivity,
        "uncertain_consensus_events": len(uncertain),
        "inputs": inputs,
        "proxy_builder_sha256": proxy_manifest["builder_sha256"],
        "scorer_sha256": sha256_file(Path(__file__).resolve()),
    }


def _synthetic_events(
    *, missing_proxy_events: bool = False, clips_count: int = 10
) -> tuple[set[str], dict[EventKey, np.ndarray], dict[EventKey, np.ndarray]]:
    clips = {f"clip_{index:02d}" for index in range(clips_count)}
    consensus: dict[EventKey, np.ndarray] = {}
    proxy: dict[EventKey, np.ndarray] = {}
    for index, clip in enumerate(sorted(clips)):
        for foot_index, foot in enumerate(FOOT_NAMES):
            touchdown = 10 + index * 5 + foot_index
            liftoff = touchdown + 3
            consensus[(clip, foot, "touchdown")] = np.asarray([touchdown])
            consensus[(clip, foot, "liftoff")] = np.asarray([liftoff])
            proxy[(clip, foot, "touchdown")] = np.asarray([touchdown + 1])
            proxy[(clip, foot, "liftoff")] = np.asarray([liftoff - 1])
    if missing_proxy_events:
        for clip in clips:
            proxy[(clip, "right", "liftoff")] = np.empty(0, dtype=np.int64)
    return clips, consensus, proxy


def synthetic_report() -> dict[str, Any]:
    """Exercise passing, failed, and insufficient-support verdict branches."""
    clips, truth, proxy = _synthetic_events()
    agreement = score_event_maps(
        truth, truth, clips=clips, tolerance_frames=TOLERANCE_FRAMES
    )
    passing_proxy = score_event_maps(
        truth, proxy, clips=clips, tolerance_frames=TOLERANCE_FRAMES
    )
    passing = _status(_consensus_support(truth), agreement, passing_proxy)[0]

    _, truth_failed, proxy_failed = _synthetic_events(missing_proxy_events=True)
    failed_proxy = score_event_maps(
        truth_failed,
        proxy_failed,
        clips=clips,
        tolerance_frames=TOLERANCE_FRAMES,
    )
    failed = _status(_consensus_support(truth_failed), agreement, failed_proxy)[0]

    small_clips, small_truth, small_proxy = _synthetic_events(clips_count=2)
    small_agreement = score_event_maps(
        small_truth,
        small_truth,
        clips=small_clips,
        tolerance_frames=TOLERANCE_FRAMES,
    )
    small_score = score_event_maps(
        small_truth,
        small_proxy,
        clips=small_clips,
        tolerance_frames=TOLERANCE_FRAMES,
    )
    insufficient = _status(
        _consensus_support(small_truth), small_agreement, small_score
    )[0]
    if (passing, failed, insufficient) != (
        "validated",
        "failed_validation",
        "insufficient_support",
    ):
        raise AssertionError("synthetic contact-validation branch mismatch")
    return {
        "schema_version": SCHEMA_VERSION,
        "classification": "synthetic control-flow test; not empirical evidence",
        "branches": {
            "passing": passing,
            "failed": failed,
            "insufficient": insufficient,
        },
        "scorer_sha256": sha256_file(Path(__file__).resolve()),
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument(
        "--panel",
        type=Path,
        default=Path("reports/g_segment/contact_validation/panel.csv"),
    )
    parser.add_argument(
        "--panel-manifest",
        type=Path,
        default=Path("reports/g_segment/contact_validation/panel.manifest.json"),
    )
    parser.add_argument(
        "--proxy-manifest",
        type=Path,
        default=Path("reports/g_segment/reference_contact_proxy/manifest.json"),
    )
    parser.add_argument(
        "--render-manifest",
        type=Path,
        default=Path("reports/g_segment/contact_validation/renders/all.manifest.json"),
    )
    parser.add_argument("--rater-a", type=Path)
    parser.add_argument("--rater-a-completion", type=Path)
    parser.add_argument("--rater-b", type=Path)
    parser.add_argument("--rater-b-completion", type=Path)
    parser.add_argument("--consensus", type=Path)
    parser.add_argument("--consensus-completion", type=Path)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("reports/g_segment/contact_validation/result.json"),
    )
    args = parser.parse_args()
    if args.synthetic:
        report = synthetic_report()
    else:
        required = {
            "rater-a": args.rater_a,
            "rater-a-completion": args.rater_a_completion,
            "rater-b": args.rater_b,
            "rater-b-completion": args.rater_b_completion,
            "consensus": args.consensus,
            "consensus-completion": args.consensus_completion,
        }
        missing = [name for name, path in required.items() if path is None]
        if missing:
            parser.error(f"real validation requires: {', '.join(missing)}")
        report = validate(
            args.panel,
            args.panel_manifest,
            args.proxy_manifest,
            args.render_manifest,
            args.rater_a,
            args.rater_a_completion,
            args.rater_b,
            args.rater_b_completion,
            args.consensus,
            args.consensus_completion,
        )
    payload = (json.dumps(_json_safe(report), indent=1, sort_keys=True) + "\n").encode()
    output_path = args.out
    if args.synthetic and output_path == Path(
        "reports/g_segment/contact_validation/result.json"
    ):
        output_path = Path("reports/g_segment/contact_validation/SYNTHETIC.json")
    _write_immutable(output_path, payload)
    print(json.dumps({"status": report.get("status"), "output": str(output_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
