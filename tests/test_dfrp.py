"""DFRP routing and exact segment-integration tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from climb.dfrp import (
    DfrpConfig,
    build_dfrp_manifest,
    validate_dfrp_manifest,
)
from climb.segment_runtime import SegmentSampler
from tools.analyze_dfrp_manifest import summarize
from tools.build_segment_unit_table import build_manifest as build_unit_table
from tools.dfrp_pipeline import materialize_training_view


def write_motion(path: Path, *, frames: int = 80, root_drop: float = 0.0) -> None:
    """Write the minimum valid DFRP motion archive."""
    joint_pos = np.zeros((frames, 2), dtype=np.float32)
    body_pos = np.zeros((frames, 2, 3), dtype=np.float32)
    body_pos[:, 0, 2] = 0.8 - root_drop
    body_pos[:, 1, 2] = 0.1 - root_drop
    body_velocity = np.zeros_like(body_pos)
    np.savez(
        path,
        joint_pos=joint_pos,
        body_pos_w=body_pos,
        body_lin_vel_w=body_velocity,
        fps=np.array([50.0]),
    )


def write_screen(path: Path, name: str, infeasible: float, *, frames: int = 80) -> None:
    path.write_text(
        json.dumps(
            {
                "clip": name,
                "frames": frames,
                "fps": 50.0,
                "gap": 0.06,
                "airborne_frac": infeasible,
                "infeasible_frac": infeasible,
                "torque_infeasible_frac": 0.0,
                "unsupported_impulse_per_weight_s": infeasible,
            }
        )
    )


def write_sidecar(
    path: Path,
    name: str,
    *,
    frames: int = 80,
    feasible: list[list[int]] | None = None,
) -> None:
    root = path.parent.parent
    motion_dir = "bank" if path.parent.name == "raw_sidecars" else "repaired"
    motion_path = root / motion_dir / f"{name}.npz"
    feasible = feasible or [[0, frames]]
    severe: list[list[int]] = [] if feasible == [[0, frames]] else [[30, 40]]
    records = [
        {
            "start_frame": start,
            "stop_frame": stop,
            "unsupported_ratio_mean": 0.0,
            "unsupported_ratio_p95": 0.0,
            "unsupported_ratio_max": 0.0,
        }
        for start, stop in feasible
    ]
    path.write_text(
        json.dumps(
            {
                "clip": name,
                "frames": frames,
                "fps": 50.0,
                "guard_s": 0.0,
                "guard_mode": "symmetric",
                "severity": "severe",
                "source_screen_sha256": "a" * 64,
                "source_motion_sha256": hashlib.sha256(
                    motion_path.read_bytes()
                ).hexdigest(),
                "reducer_sha256": "b" * 64,
                "feasible_segments_frames": feasible,
                "feasible_segment_records": records,
                "guarded_severe_windows_frames": severe,
                "excluded_windows_frames": severe,
            }
        )
    )


def write_repair(
    path: Path,
    name: str,
    *,
    after: float,
    offset: float,
    complete: bool,
) -> None:
    record = {
        "clip": name,
        "frames": 80,
        "fps": 50.0,
        "infeasible_frac_before": 0.2,
        "infeasible_frac_after": after,
        "offset_max_m": offset,
    }
    if complete:
        root = path.parent.parent
        record.update(
            {
                "operator": "dfrp_root_contact_ik_v1",
                "input_motion_sha256": hashlib.sha256(
                    (root / "bank" / f"{name}.npz").read_bytes()
                ).hexdigest(),
                "model_sha256": hashlib.sha256(
                    (root / "robot.xml").read_bytes()
                ).hexdigest(),
                "joint_limits_valid": True,
                "ik_contact_residual_m": 0.002,
            }
        )
    path.write_text(json.dumps(record))


def fixture_dirs(tmp_path: Path, names: list[str]) -> dict[str, Path]:
    paths = {
        key: tmp_path / key
        for key in (
            "bank",
            "screens",
            "repairs",
            "repaired",
            "raw_sidecars",
            "repaired_sidecars",
        )
    }
    for path in paths.values():
        path.mkdir()
    paths["clips"] = tmp_path / "clips.txt"
    paths["clips"].write_text("".join(f"{name}\n" for name in names))
    paths["model"] = tmp_path / "robot.xml"
    paths["model"].write_text("<mujoco/>")
    for name in names:
        write_motion(paths["bank"] / f"{name}.npz")
    return paths


def build(paths: dict[str, Path]) -> dict:
    return build_dfrp_manifest(
        clips_path=paths["clips"],
        bank=paths["bank"],
        screen_dir=paths["screens"],
        model_path=paths["model"],
        repair_records_dir=paths["repairs"],
        repaired_bank=paths["repaired"],
        raw_sidecar_dir=paths["raw_sidecars"],
        repaired_sidecar_dir=paths["repaired_sidecars"],
        config=DfrpConfig(horizon_steps=20),
        root=paths["model"].parent,
    )


def test_threshold_is_strict_and_raw_route_requires_exact_support(
    tmp_path: Path,
) -> None:
    paths = fixture_dirs(tmp_path, ["equal", "below"])
    write_screen(paths["screens"] / "equal.json", "equal", 0.10)
    write_screen(paths["screens"] / "below.json", "below", 0.02)
    write_sidecar(paths["raw_sidecars"] / "equal.json", "equal")

    manifest = build(paths)
    rows = {row["name"]: row for row in manifest["clips"]}
    assert rows["equal"]["flagged"] is False
    assert rows["equal"]["route"] == "raw_feasible"
    assert rows["equal"]["training_eligible"] is True
    assert rows["below"]["route"] == "raw_feasible"
    assert rows["below"]["training_eligible"] is False
    assert "exact_training_support_not_ready" in rows["below"]["route_reasons"]
    validate_dfrp_manifest(manifest)


@pytest.mark.parametrize(
    ("offset", "after", "complete", "expected_route"),
    [
        (0.08, 0.05, True, "repair_primary"),
        (0.12, 0.01, True, "repair_exploratory"),
        (0.16, 0.01, True, "quarantine"),
        (0.04, 0.06, True, "quarantine"),
    ],
)
def test_two_tier_repair_routing(
    tmp_path: Path,
    offset: float,
    after: float,
    complete: bool,
    expected_route: str,
) -> None:
    paths = fixture_dirs(tmp_path, ["clip"])
    write_screen(paths["screens"] / "clip.json", "clip", 0.2)
    write_repair(
        paths["repairs"] / "clip.json",
        "clip",
        after=after,
        offset=offset,
        complete=complete,
    )
    write_motion(paths["repaired"] / "clip.npz", root_drop=offset)
    if expected_route == "repair_primary":
        write_sidecar(paths["repaired_sidecars"] / "clip.json", "clip")

    row = build(paths)["clips"][0]
    assert row["route"] == expected_route
    assert row["training_eligible"] is (expected_route == "repair_primary")


def test_legacy_primary_candidate_cannot_enter_training(tmp_path: Path) -> None:
    paths = fixture_dirs(tmp_path, ["clip"])
    write_screen(paths["screens"] / "clip.json", "clip", 0.2)
    write_repair(
        paths["repairs"] / "clip.json",
        "clip",
        after=0.01,
        offset=0.04,
        complete=False,
    )
    write_motion(paths["repaired"] / "clip.npz", root_drop=0.04)
    write_sidecar(paths["repaired_sidecars"] / "clip.json", "clip")

    row = build(paths)["clips"][0]
    assert row["route"] == "repair_primary"
    assert row["repair"]["qualification"] == "incomplete"
    assert row["training_eligible"] is False


def test_failed_repair_keeps_exact_raw_segments(tmp_path: Path) -> None:
    paths = fixture_dirs(tmp_path, ["clip"])
    write_screen(paths["screens"] / "clip.json", "clip", 0.2)
    write_repair(
        paths["repairs"] / "clip.json",
        "clip",
        after=0.2,
        offset=0.02,
        complete=True,
    )
    write_motion(paths["repaired"] / "clip.npz", root_drop=0.02)
    write_sidecar(
        paths["raw_sidecars"] / "clip.json",
        "clip",
        feasible=[[0, 30], [40, 80]],
    )

    row = build(paths)["clips"][0]
    assert row["route"] == "segment_only"
    assert row["training_eligible"] is True
    assert row["training_sidecar"]["legal_starts"] == 30


def test_manifest_hash_detects_tampering(tmp_path: Path) -> None:
    paths = fixture_dirs(tmp_path, ["clip"])
    write_screen(paths["screens"] / "clip.json", "clip", 0.0)
    write_sidecar(paths["raw_sidecars"] / "clip.json", "clip")
    manifest = build(paths)
    manifest["clips"][0]["route"] = "quarantine"
    with pytest.raises(ValueError, match="payload hash mismatch"):
        validate_dfrp_manifest(manifest)


def test_exact_sidecar_is_bound_to_selected_motion(tmp_path: Path) -> None:
    paths = fixture_dirs(tmp_path, ["clip"])
    write_screen(paths["screens"] / "clip.json", "clip", 0.0)
    write_sidecar(paths["raw_sidecars"] / "clip.json", "clip")
    write_motion(paths["bank"] / "clip.npz", root_drop=0.01)
    with pytest.raises(ValueError, match="source-motion hash mismatch"):
        build(paths)


def test_materialized_view_contains_only_training_ready_rows(tmp_path: Path) -> None:
    paths = fixture_dirs(tmp_path, ["ready", "pending"])
    write_screen(paths["screens"] / "ready.json", "ready", 0.0)
    write_screen(paths["screens"] / "pending.json", "pending", 0.0)
    write_sidecar(paths["raw_sidecars"] / "ready.json", "ready")
    manifest = build(paths)
    overlay = tmp_path / "overlay"
    sidecars = tmp_path / "selected_sidecars"
    clips = tmp_path / "selected.txt"

    materialize_training_view(
        manifest,
        overlay_dir=overlay,
        sidecar_overlay_dir=sidecars,
        clips_out=clips,
        root=tmp_path,
        force=False,
    )
    assert clips.read_text() == "ready\n"
    assert (overlay / "ready.npz").is_symlink()
    assert (sidecars / "ready.json").is_symlink()
    assert not (overlay / "pending.npz").exists()


def test_summary_preserves_two_tier_counts(tmp_path: Path) -> None:
    paths = fixture_dirs(tmp_path, ["clip"])
    write_screen(paths["screens"] / "clip.json", "clip", 0.2)
    write_repair(
        paths["repairs"] / "clip.json",
        "clip",
        after=0.01,
        offset=0.04,
        complete=False,
    )
    write_motion(paths["repaired"] / "clip.npz", root_drop=0.04)
    summary = summarize(build(paths))
    assert summary["strict_flagged"] == 1
    assert summary["primary_8cm_legacy_candidates"] == 1
    assert summary["primary_qualification_complete"] == 0


def test_unit_table_accepts_only_hash_matched_dfrp_inputs(tmp_path: Path) -> None:
    paths = fixture_dirs(tmp_path, ["clip"])
    write_screen(paths["screens"] / "clip.json", "clip", 0.2)
    write_repair(
        paths["repairs"] / "clip.json",
        "clip",
        after=0.01,
        offset=0.04,
        complete=True,
    )
    write_motion(paths["repaired"] / "clip.npz", root_drop=0.04)
    write_sidecar(paths["repaired_sidecars"] / "clip.json", "clip")
    manifest = build(paths)
    manifest_path = tmp_path / "dfrp.json"
    manifest_path.write_text(json.dumps(manifest))

    table = build_unit_table(
        paths["clips"],
        paths["repaired"],
        paths["repaired_sidecars"],
        horizon_steps=20,
        dfrp_manifest_path=manifest_path,
    )
    assert table["sources"][0]["dfrp_route"] == "repair_primary"
    assert (
        table["sources"][0]["dfrp_manifest_payload_sha256"]
        == manifest["payload_sha256"]
    )
    table_path = tmp_path / "unit_table.json"
    table_path.write_text(json.dumps(table))
    sampler = SegmentSampler(table_path, mode="uniform", seed=7)
    assert sampler.num_units == 1

    manifest_path.write_text(manifest_path.read_text() + "\n")
    with pytest.raises(ValueError, match="DFRP manifest file hash mismatch"):
        SegmentSampler(table_path, mode="uniform", seed=7)
    manifest_path.write_text(json.dumps(manifest))

    write_motion(paths["repaired"] / "clip.npz", root_drop=0.03)
    with pytest.raises(ValueError, match="motion does not match"):
        build_unit_table(
            paths["clips"],
            paths["repaired"],
            paths["repaired_sidecars"],
            horizon_steps=20,
            dfrp_manifest_path=manifest_path,
        )
