"""Deterministic artifact contract for dynamic feasibility and repair.

DFRP deliberately separates a scientific routing decision (for example, a
repair is inside the primary displacement budget) from readiness for training.
Training readiness additionally requires an exact, full-horizon support
sidecar produced from the selected motion and complete repair qualification.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np

SCHEMA_VERSION = "dfrp_bank_manifest/1"
Route = Literal[
    "raw_feasible",
    "repair_primary",
    "repair_exploratory",
    "segment_only",
    "quarantine",
]


@dataclass(frozen=True)
class DfrpConfig:
    """Frozen thresholds used to route one bank."""

    contact_gap_m: float = 0.06
    flag_infeasible_frac: float = 0.10
    recovered_infeasible_frac: float = 0.05
    primary_root_offset_m: float = 0.08
    exploratory_root_offset_m: float = 0.15
    horizon_steps: int = 50
    ik_contact_residual_m: float = 0.01

    def validate(self) -> None:
        """Reject ambiguous or internally inconsistent routing policies."""
        if not 0.0 < self.contact_gap_m:
            raise ValueError("contact_gap_m must be positive")
        if not 0.0 <= self.recovered_infeasible_frac <= self.flag_infeasible_frac < 1.0:
            raise ValueError("feasibility thresholds are inconsistent")
        if not 0.0 < self.primary_root_offset_m <= self.exploratory_root_offset_m:
            raise ValueError("repair displacement budgets are inconsistent")
        if self.horizon_steps <= 0:
            raise ValueError("horizon_steps must be positive")
        if self.ik_contact_residual_m <= 0.0:
            raise ValueError("ik_contact_residual_m must be positive")


def sha256_file(path: Path) -> str:
    """Hash a file without loading it all into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_hash(value: Any) -> str:
    """Hash a JSON-compatible value independently of whitespace."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def read_clip_names(path: Path) -> list[str]:
    """Read a comment-tolerant, duplicate-free clip list."""
    names = [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not names:
        raise ValueError("clip list is empty")
    if len(names) != len(set(names)):
        raise ValueError("clip list contains duplicates")
    return names


def _relative(path: Path, root: Path) -> str:
    return os.path.relpath(path.resolve(), root.resolve())


def _motion_facts(path: Path) -> tuple[int, float, dict[str, np.ndarray]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with np.load(path) as archive:
        required = ("joint_pos", "body_pos_w", "body_lin_vel_w", "fps")
        missing = [name for name in required if name not in archive]
        if missing:
            raise ValueError(f"{path}: missing NPZ fields {missing}")
        arrays = {name: np.asarray(archive[name]) for name in required[:-1]}
        frames = int(arrays["joint_pos"].shape[0])
        fps = float(np.asarray(archive["fps"]).reshape(-1)[0])
    if frames <= 0 or not math.isfinite(fps) or fps <= 0.0:
        raise ValueError(f"{path}: invalid motion timeline")
    if any(array.shape[0] != frames for array in arrays.values()):
        raise ValueError(f"{path}: motion arrays disagree on frame count")
    return frames, fps, arrays


def _validate_screen(
    screen: dict[str, Any],
    *,
    clip: str,
    frames: int,
    fps: float,
    config: DfrpConfig,
) -> None:
    required = (
        "clip",
        "frames",
        "fps",
        "gap",
        "infeasible_frac",
        "airborne_frac",
        "torque_infeasible_frac",
        "unsupported_impulse_per_weight_s",
    )
    missing = [field for field in required if field not in screen]
    if missing:
        raise ValueError(f"{clip}: screen lacks fields {missing}")
    if screen["clip"] != clip or int(screen["frames"]) != frames:
        raise ValueError(f"{clip}: screen timeline does not match motion")
    if abs(float(screen["fps"]) - fps) > 1.0e-9:
        raise ValueError(f"{clip}: screen fps does not match motion")
    if abs(float(screen["gap"]) - config.contact_gap_m) > 1.0e-9:
        raise ValueError(
            f"{clip}: screen gap {screen['gap']} is not the pinned "
            f"{config.contact_gap_m} m"
        )
    for field in (
        "infeasible_frac",
        "airborne_frac",
        "torque_infeasible_frac",
    ):
        value = float(screen[field])
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError(f"{clip}: invalid screen field {field}")


def _exact_support_facts(
    path: Path | None,
    *,
    clip: str,
    frames: int,
    fps: float,
    horizon_steps: int,
    expected_motion_sha256: str,
    root: Path,
) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    sidecar = json.loads(path.read_text())
    if (
        sidecar.get("clip") != clip
        or int(sidecar.get("frames", -1)) != frames
        or abs(float(sidecar.get("fps", -1.0)) - fps) > 1.0e-9
    ):
        raise ValueError(f"{clip}: exact sidecar timeline does not match motion")
    if sidecar.get("source_motion_sha256") != expected_motion_sha256:
        raise ValueError(f"{clip}: exact sidecar source-motion hash mismatch")
    runs = sidecar.get("feasible_segments_frames")
    if not isinstance(runs, list):
        raise TypeError(f"{clip}: exact sidecar lacks feasible_segments_frames")
    excluded = sidecar.get("excluded_windows_frames")
    if not isinstance(excluded, list):
        raise TypeError(f"{clip}: exact sidecar lacks excluded_windows_frames")
    legal_starts = 0
    previous_stop = 0
    feasible_mask = np.zeros(frames, dtype=bool)
    for index, run in enumerate(runs):
        if (
            not isinstance(run, list)
            or len(run) != 2
            or not all(isinstance(value, int) for value in run)
        ):
            raise ValueError(f"{clip}: invalid feasible run {index}")
        start, stop = run
        if start < previous_stop or start < 0 or stop <= start or stop > frames:
            raise ValueError(f"{clip}: feasible runs are not an exact ordered partition")
        legal_starts += max(stop - start - horizon_steps, 0)
        feasible_mask[start:stop] = True
        previous_stop = stop
    excluded_mask = np.zeros(frames, dtype=bool)
    previous_stop = 0
    for index, run in enumerate(excluded):
        if (
            not isinstance(run, list)
            or len(run) != 2
            or not all(isinstance(value, int) for value in run)
        ):
            raise ValueError(f"{clip}: invalid excluded run {index}")
        start, stop = run
        if start < previous_stop or start < 0 or stop <= start or stop > frames:
            raise ValueError(f"{clip}: excluded runs are not exact and ordered")
        excluded_mask[start:stop] = True
        previous_stop = stop
    if bool((feasible_mask & excluded_mask).any()) or not bool(
        (feasible_mask | excluded_mask).all()
    ):
        raise ValueError(f"{clip}: exact support is not a frame partition")
    return {
        "path": _relative(path, root),
        "sha256": sha256_file(path),
        "source_motion_sha256": expected_motion_sha256,
        "legal_starts": legal_starts,
        "support_ready": legal_starts > 0,
    }


def _repair_fidelity(
    original: dict[str, np.ndarray],
    repaired: dict[str, np.ndarray],
    *,
    fps: float,
) -> dict[str, Any]:
    if any(original[name].shape != repaired[name].shape for name in original):
        raise ValueError("repaired motion changes an array shape")
    finite = all(bool(np.isfinite(array).all()) for array in repaired.values())
    joint_delta = np.abs(repaired["joint_pos"] - original["joint_pos"])
    root_delta = np.linalg.norm(
        repaired["body_pos_w"][:, 0] - original["body_pos_w"][:, 0], axis=-1
    )
    body_delta = np.linalg.norm(
        repaired["body_pos_w"] - original["body_pos_w"], axis=-1
    )
    root_velocity_delta = np.linalg.norm(
        repaired["body_lin_vel_w"][:, 0]
        - original["body_lin_vel_w"][:, 0],
        axis=-1,
    )
    root_acceleration_delta = np.linalg.norm(
        np.gradient(
            repaired["body_lin_vel_w"][:, 0], 1.0 / fps, axis=0
        )
        - np.gradient(
            original["body_lin_vel_w"][:, 0], 1.0 / fps, axis=0
        ),
        axis=-1,
    )
    return {
        "finite": finite,
        "joint_delta_rad_p95": float(np.percentile(joint_delta, 95)),
        "joint_delta_rad_max": float(joint_delta.max(initial=0.0)),
        "root_displacement_m_p95": float(np.percentile(root_delta, 95)),
        "root_displacement_m_max": float(root_delta.max(initial=0.0)),
        "body_mpjpe_m_mean": float(body_delta.mean()),
        "body_mpjpe_m_p95": float(np.percentile(body_delta, 95)),
        "body_mpjpe_m_max": float(body_delta.max(initial=0.0)),
        "root_velocity_delta_mps_p95": float(
            np.percentile(root_velocity_delta, 95)
        ),
        "root_velocity_delta_mps_max": float(
            root_velocity_delta.max(initial=0.0)
        ),
        "root_acceleration_delta_mps2_p95": float(
            np.percentile(root_acceleration_delta, 95)
        ),
        "root_acceleration_delta_mps2_max": float(
            root_acceleration_delta.max(initial=0.0)
        ),
    }


def _repair_qualification(
    repair: dict[str, Any],
    fidelity: dict[str, Any],
    *,
    config: DfrpConfig,
    expected_motion_sha256: str,
    expected_model_sha256: str,
    expected_operator_sha256: str | None,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if not fidelity["finite"]:
        reasons.append("nonfinite_repaired_motion")
    if repair.get("joint_limits_valid") is False:
        reasons.append("joint_limit_violation")
    residual = repair.get("ik_contact_residual_m")
    if residual is not None and float(residual) > config.ik_contact_residual_m:
        reasons.append("ik_contact_residual")
    if repair.get("input_motion_sha256") not in (None, expected_motion_sha256):
        reasons.append("repair_input_motion_mismatch")
    if repair.get("model_sha256") not in (None, expected_model_sha256):
        reasons.append("repair_model_mismatch")
    if expected_operator_sha256 is not None and repair.get(
        "operator_sha256"
    ) != expected_operator_sha256:
        reasons.append("repair_operator_mismatch")
    required_checks = [
        "joint_limits_valid",
        "ik_contact_residual_m",
        "operator",
        "input_motion_sha256",
        "model_sha256",
    ]
    if expected_operator_sha256 is not None:
        required_checks.append("operator_sha256")
    if any(field not in repair for field in required_checks):
        reasons.append("legacy_repair_checks_incomplete")
    return ("complete" if not reasons else "incomplete"), reasons


def _route_clip(
    *,
    flagged: bool,
    repair: dict[str, Any] | None,
    repaired_exists: bool,
    raw_support: dict[str, Any] | None,
    repair_qualification: str | None,
    config: DfrpConfig,
) -> tuple[Route, list[str]]:
    if not flagged:
        return "raw_feasible", []
    if repair is None:
        if raw_support and raw_support["support_ready"]:
            return "segment_only", ["missing_repair_record"]
        return "quarantine", ["missing_repair_record", "no_legal_raw_segment"]
    after = float(repair["infeasible_frac_after"])
    offset = float(repair["offset_max_m"])
    if after <= config.recovered_infeasible_frac and repaired_exists:
        if offset <= config.primary_root_offset_m:
            reasons = []
            if repair_qualification != "complete":
                reasons.append("repair_qualification_incomplete")
            return "repair_primary", reasons
        if offset <= config.exploratory_root_offset_m:
            return "repair_exploratory", ["root_offset_above_primary_budget"]
    reasons = []
    if after > config.recovered_infeasible_frac:
        reasons.append("residual_infeasibility")
    if offset > config.exploratory_root_offset_m:
        reasons.append("root_offset_above_exploratory_budget")
    if not repaired_exists:
        reasons.append("missing_repaired_motion")
    if raw_support and raw_support["support_ready"]:
        return "segment_only", reasons
    return "quarantine", [*reasons, "no_legal_raw_segment"]


def build_dfrp_manifest(
    *,
    clips_path: Path,
    bank: Path,
    screen_dir: Path,
    model_path: Path,
    repair_records_dir: Path | None = None,
    repaired_bank: Path | None = None,
    raw_sidecar_dir: Path | None = None,
    repaired_sidecar_dir: Path | None = None,
    screen_tool_path: Path | None = None,
    repair_tool_path: Path | None = None,
    config: DfrpConfig | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Build a deterministic, fail-closed routing manifest."""
    config = config or DfrpConfig()
    config.validate()
    root = (root or Path.cwd()).resolve()
    paths = (clips_path, bank, screen_dir, model_path)
    if any(not path.exists() for path in paths):
        missing = [str(path) for path in paths if not path.exists()]
        raise FileNotFoundError(f"missing DFRP inputs: {missing}")
    names = read_clip_names(clips_path)
    model_sha256 = sha256_file(model_path)
    screen_tool_sha256 = (
        sha256_file(screen_tool_path) if screen_tool_path is not None else None
    )
    repair_tool_sha256 = (
        sha256_file(repair_tool_path) if repair_tool_path is not None else None
    )
    clip_rows: list[dict[str, Any]] = []

    for name in names:
        original_path = bank / f"{name}.npz"
        frames, fps, original_arrays = _motion_facts(original_path)
        original_sha256 = sha256_file(original_path)
        screen_path = screen_dir / f"{name}.json"
        if not screen_path.is_file():
            raise FileNotFoundError(f"{name}: missing screen {screen_path}")
        screen = json.loads(screen_path.read_text())
        _validate_screen(
            screen, clip=name, frames=frames, fps=fps, config=config
        )
        flagged = float(screen["infeasible_frac"]) > config.flag_infeasible_frac

        raw_sidecar_path = (
            raw_sidecar_dir / f"{name}.json" if raw_sidecar_dir else None
        )
        raw_support = _exact_support_facts(
            raw_sidecar_path,
            clip=name,
            frames=frames,
            fps=fps,
            horizon_steps=config.horizon_steps,
            expected_motion_sha256=original_sha256,
            root=root,
        )

        repair_path = (
            repair_records_dir / f"{name}.json" if repair_records_dir else None
        )
        repair = (
            json.loads(repair_path.read_text())
            if repair_path is not None and repair_path.is_file()
            else None
        )
        repaired_path = repaired_bank / f"{name}.npz" if repaired_bank else None
        repaired_exists = repaired_path is not None and repaired_path.is_file()
        fidelity = None
        qualification = None
        qualification_reasons: list[str] = []
        repaired_support = None
        if repair is not None:
            required = (
                "clip",
                "frames",
                "fps",
                "offset_max_m",
                "infeasible_frac_before",
                "infeasible_frac_after",
            )
            missing = [field for field in required if field not in repair]
            if missing:
                raise ValueError(f"{name}: repair record lacks fields {missing}")
            if (
                repair["clip"] != name
                or int(repair["frames"]) != frames
                or abs(float(repair["fps"]) - fps) > 1.0e-9
            ):
                raise ValueError(f"{name}: repair record timeline does not match")
            if repaired_exists:
                repaired_frames, repaired_fps, repaired_arrays = _motion_facts(
                    repaired_path
                )
                repaired_sha256 = sha256_file(repaired_path)
                if repaired_frames != frames or abs(repaired_fps - fps) > 1.0e-9:
                    raise ValueError(f"{name}: repaired motion timeline does not match")
                fidelity = _repair_fidelity(
                    original_arrays, repaired_arrays, fps=fps
                )
                qualification, qualification_reasons = _repair_qualification(
                    repair,
                    fidelity,
                    config=config,
                    expected_motion_sha256=original_sha256,
                    expected_model_sha256=model_sha256,
                    expected_operator_sha256=repair_tool_sha256,
                )
                repaired_sidecar_path = (
                    repaired_sidecar_dir / f"{name}.json"
                    if repaired_sidecar_dir
                    else None
                )
                repaired_support = _exact_support_facts(
                    repaired_sidecar_path,
                    clip=name,
                    frames=frames,
                    fps=fps,
                    horizon_steps=config.horizon_steps,
                    expected_motion_sha256=repaired_sha256,
                    root=root,
                )

        route, reasons = _route_clip(
            flagged=flagged,
            repair=repair,
            repaired_exists=repaired_exists,
            raw_support=raw_support,
            repair_qualification=qualification,
            config=config,
        )
        if route == "repair_primary":
            training_path = repaired_path
            exact_support = repaired_support
            training_eligible = bool(
                qualification == "complete"
                and exact_support
                and exact_support["support_ready"]
            )
        elif route in ("raw_feasible", "segment_only"):
            training_path = original_path
            exact_support = raw_support
            training_eligible = bool(exact_support and exact_support["support_ready"])
        else:
            training_path = None
            exact_support = None
            training_eligible = False
        if not training_eligible and route in (
            "raw_feasible",
            "repair_primary",
            "segment_only",
        ):
            reasons.append("exact_training_support_not_ready")

        repair_row = None
        if repair is not None:
            repair_row = {
                "record_path": _relative(repair_path, root),
                "record_sha256": sha256_file(repair_path),
                "motion_path": (
                    _relative(repaired_path, root) if repaired_exists else None
                ),
                "motion_sha256": (
                    sha256_file(repaired_path) if repaired_exists else None
                ),
                "operator": repair.get("operator", "legacy_root_projection_v1"),
                "infeasible_frac_before": float(repair["infeasible_frac_before"]),
                "infeasible_frac_after": float(repair["infeasible_frac_after"]),
                "offset_max_m": float(repair["offset_max_m"]),
                "qualification": qualification,
                "qualification_reasons": qualification_reasons,
                "fidelity": fidelity,
                "exact_support": repaired_support,
            }

        clip_rows.append(
            {
                "name": name,
                "original": {
                    "path": _relative(original_path, root),
                    "sha256": original_sha256,
                    "frames": frames,
                    "fps": fps,
                },
                "screen": {
                    "path": _relative(screen_path, root),
                    "sha256": sha256_file(screen_path),
                    "infeasible_frac": float(screen["infeasible_frac"]),
                    "airborne_frac": float(screen["airborne_frac"]),
                    "torque_infeasible_frac": float(
                        screen["torque_infeasible_frac"]
                    ),
                    "unsupported_impulse_per_weight_s": float(
                        screen["unsupported_impulse_per_weight_s"]
                    ),
                },
                "flagged": flagged,
                "repair": repair_row,
                "raw_exact_support": raw_support,
                "route": route,
                "route_reasons": sorted(set(reasons)),
                "training_eligible": training_eligible,
                "training_motion": (
                    {
                        "path": _relative(training_path, root),
                        "sha256": sha256_file(training_path),
                    }
                    if training_path is not None and training_path.is_file()
                    else None
                ),
                "training_sidecar": exact_support,
            }
        )

    route_counts: dict[str, int] = {}
    reason_counts: dict[str, int] = {}
    for row in clip_rows:
        route_counts[row["route"]] = route_counts.get(row["route"], 0) + 1
        for reason in row["route_reasons"]:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    flagged_names = {row["name"] for row in clip_rows if row["flagged"]}
    repair_record_names: set[str] = set()
    if repair_records_dir is not None and repair_records_dir.is_dir():
        repair_record_names = {
            path.stem for path in repair_records_dir.glob("*.json") if path.is_file()
        }
    missing_repair_records = sorted(flagged_names - repair_record_names)
    out_of_scope_repair_records = sorted(repair_record_names - flagged_names)
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "classification": (
            "unsealed DFRP v0 routing artifact; routes are not policy-benefit claims"
        ),
        "config": asdict(config),
        "inputs": {
            "clips": _relative(clips_path, root),
            "clips_sha256": sha256_file(clips_path),
            "bank": _relative(bank, root),
            "screen_dir": _relative(screen_dir, root),
            "model": _relative(model_path, root),
            "model_sha256": model_sha256,
            "manifest_builder": _relative(Path(__file__), root),
            "manifest_builder_sha256": sha256_file(Path(__file__)),
            "screen_tool": (
                _relative(screen_tool_path, root) if screen_tool_path else None
            ),
            "screen_tool_sha256": screen_tool_sha256,
            "repair_tool": (
                _relative(repair_tool_path, root) if repair_tool_path else None
            ),
            "repair_tool_sha256": repair_tool_sha256,
            "repair_records_dir": (
                _relative(repair_records_dir, root) if repair_records_dir else None
            ),
            "repaired_bank": (
                _relative(repaired_bank, root) if repaired_bank else None
            ),
            "raw_sidecar_dir": (
                _relative(raw_sidecar_dir, root) if raw_sidecar_dir else None
            ),
            "repaired_sidecar_dir": (
                _relative(repaired_sidecar_dir, root)
                if repaired_sidecar_dir
                else None
            ),
        },
        "counts": {
            "clips": len(clip_rows),
            "flagged": sum(bool(row["flagged"]) for row in clip_rows),
            "training_eligible": sum(
                bool(row["training_eligible"]) for row in clip_rows
            ),
            "by_route": route_counts,
            "by_reason": reason_counts,
        },
        "integrity": {
            "flagged_missing_repair_records": missing_repair_records,
            "repair_records_outside_strict_flag_set": out_of_scope_repair_records,
        },
        "clips": clip_rows,
    }
    payload["payload_sha256"] = canonical_hash(payload)
    return payload


def validate_dfrp_manifest(manifest: dict[str, Any]) -> None:
    """Validate schema, canonical identity, routes, and unique clip names."""
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported DFRP manifest schema")
    expected = manifest.get("payload_sha256")
    payload = {key: value for key, value in manifest.items() if key != "payload_sha256"}
    if expected != canonical_hash(payload):
        raise ValueError("DFRP manifest payload hash mismatch")
    rows = manifest.get("clips")
    if not isinstance(rows, list) or not rows:
        raise ValueError("DFRP manifest has no clips")
    names = [row.get("name") for row in rows]
    if any(not isinstance(name, str) or not name for name in names):
        raise ValueError("DFRP manifest has an invalid clip name")
    if len(names) != len(set(names)):
        raise ValueError("DFRP manifest contains duplicate clips")
    valid_routes = {
        "raw_feasible",
        "repair_primary",
        "repair_exploratory",
        "segment_only",
        "quarantine",
    }
    if any(row.get("route") not in valid_routes for row in rows):
        raise ValueError("DFRP manifest contains an unknown route")
    for row in rows:
        if row.get("training_eligible") and (
            row.get("route") not in ("raw_feasible", "repair_primary", "segment_only")
            or not row.get("training_motion")
            or not row.get("training_sidecar")
        ):
            raise ValueError(f"{row['name']}: invalid training-ready route")
