#!/usr/bin/env python3
"""Paired, phase-stratified evaluation with terminal-state quality metrics.

This is the post-audit evaluator.  It does not replace frozen campaign outputs.
Conditions are stored independently of policy/reference content and replayed by
name, start frame, replicate, environment seed, and joint-noise seed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from dataclasses import asdict
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, cast

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "paired_eval_conditions/2"
DEFAULT_PHASES = "0,0.166667,0.333333,0.5,0.666667,0.833333,1"
ERROR_METRICS = (
    "error_anchor_pos",
    "error_anchor_rot",
    "error_anchor_lin_vel",
    "error_anchor_ang_vel",
    "error_body_pos",
    "error_body_rot",
    "error_body_lin_vel",
    "error_body_ang_vel",
    "error_joint_pos",
    "error_joint_vel",
)

sys.path.insert(0, str(ROOT))

from climb.contact_timing import contact_event_metrics

CONTACT_TOLERANCE_FRAMES = 2


def sha256_file(path: Path) -> str:
    """Hash one artifact without loading it all into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_tensors(tensors: dict[str, torch.Tensor]) -> str:
    """Hash named tensors with shape and dtype metadata."""
    digest = hashlib.sha256()
    for name, tensor in sorted(tensors.items()):
        value = tensor.detach().cpu().contiguous()
        digest.update(name.encode())
        digest.update(str(value.dtype).encode())
        digest.update(str(tuple(value.shape)).encode())
        digest.update(value.numpy().tobytes())
    return digest.hexdigest()


def software_versions() -> dict[str, str]:
    """Record the mechanics stack used by an evaluation cell."""
    result = {
        "python": sys.version.split()[0],
        "torch": torch.__version__,
        "numpy": np.__version__,
    }
    for package in ("mjlab", "mujoco", "mujoco-warp", "rsl-rl-lib"):
        try:
            result[package] = version(package)
        except PackageNotFoundError:
            result[package] = "unavailable"
    return result


def selected_file_hashes(names: list[str], bank: Path) -> dict[str, str]:
    """Hash every selected reference file, keyed by clip identity."""
    return {name: sha256_file(bank / f"{name}.npz") for name in names}


def load_validated_contact_proxy(
    proxy_manifest_path: Path,
    validation_report_path: Path,
    names: list[str],
    source_hashes: dict[str, str],
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Load contact masks only through a passing, hash-bound validation report."""
    proxy_manifest_path = proxy_manifest_path.resolve()
    validation_report_path = validation_report_path.resolve()
    proxy_manifest_sha256 = sha256_file(proxy_manifest_path)
    report = json.loads(validation_report_path.read_text())
    gate_results = report.get("gate_results")
    if (
        report.get("schema_version") != "contact_proxy_validation/1"
        or report.get("classification")
        != "measured held-out contact-instrument validation"
        or report.get("status") != "validated"
        or report.get("tolerance_frames") != CONTACT_TOLERANCE_FRAMES
        or not isinstance(gate_results, dict)
        or not gate_results
        or not all(value is True for value in gate_results.values())
    ):
        raise ValueError("contact validation report is absent, failed, or incompatible")
    scorer_path = ROOT / "tools" / "validate_contact_proxy.py"
    if report.get("scorer_sha256") != sha256_file(scorer_path):
        raise ValueError("contact validation scorer hash mismatch")
    linked_proxy = report.get("inputs", {}).get("proxy_manifest", {})
    if (
        Path(linked_proxy.get("path", "")).resolve() != proxy_manifest_path
        or linked_proxy.get("sha256") != proxy_manifest_sha256
    ):
        raise ValueError("validation report does not bind the requested proxy manifest")

    manifest = json.loads(proxy_manifest_path.read_text())
    if manifest.get("schema_version") != "reference_contact_proxy/1":
        raise ValueError("unsupported reference-contact proxy manifest")
    builder_path = ROOT / "tools" / "build_reference_contact_labels.py"
    if manifest.get("builder_sha256") != sha256_file(builder_path):
        raise ValueError("reference-contact proxy builder hash mismatch")
    records = manifest.get("clips", {})
    if not set(names).issubset(records):
        raise ValueError("reference-contact proxy does not cover selected clips")

    masks: dict[str, np.ndarray] = {}
    artifacts: dict[str, str] = {}
    for name in names:
        record = records[name]
        if record.get("source_motion_sha256") != source_hashes[name]:
            raise ValueError(f"reference-contact source hash mismatch: {name}")
        artifact = record.get("artifact", {})
        path = Path(artifact.get("path", ""))
        if not path.is_file() or artifact.get("sha256") != sha256_file(path):
            raise ValueError(f"reference-contact artifact hash mismatch: {name}")
        with np.load(path, allow_pickle=False) as arrays:
            mask = np.asarray(arrays["contact"], dtype=bool)
            fps = float(arrays["fps"])
        if (
            mask.ndim != 2
            or mask.shape[1] != 2
            or mask.shape[0] != int(record.get("frames", -1))
            or not np.isclose(fps, 50.0)
        ):
            raise ValueError(f"invalid reference-contact artifact: {name}")
        masks[name] = mask
        artifacts[name] = artifact["sha256"]
    provenance = {
        "proxy_manifest": {
            "path": str(proxy_manifest_path),
            "sha256": proxy_manifest_sha256,
        },
        "validation_report": {
            "path": str(validation_report_path),
            "sha256": sha256_file(validation_report_path),
        },
        "label_artifact_sha256": artifacts,
        "tolerance_frames": CONTACT_TOLERANCE_FRAMES,
    }
    return masks, provenance


def score_contact_window(
    reference_contact: np.ndarray,
    observed_contact: np.ndarray,
    *,
    start_frame: int,
    fps: float,
) -> dict[str, Any]:
    """Align post-step contacts to reference frames and flatten event metrics."""
    observed = np.asarray(observed_contact, dtype=bool)
    if observed.ndim != 2 or observed.shape[1] != 2:
        raise ValueError("observed contact must have shape [survived_steps, 2]")
    stop = start_frame + 1 + observed.shape[0]
    reference = np.asarray(reference_contact, dtype=bool)[start_frame + 1 : stop]
    if reference.shape != observed.shape:
        raise ValueError("reference-contact window escaped its source timeline")
    metrics = contact_event_metrics(
        reference,
        observed,
        tolerance_frames=CONTACT_TOLERANCE_FRAMES,
    )
    flat: dict[str, Any] = {
        "reference_contact_event_count": metrics["reference_event_count"],
        "observed_contact_event_count": metrics["observed_event_count"],
        "contact_event_tp": metrics["tp"],
        "contact_event_fp": metrics["fp"],
        "contact_event_fn": metrics["fn"],
        "contact_event_precision": metrics["precision"],
        "contact_event_recall": metrics["recall"],
        "contact_event_f1": metrics["f1"],
        "contact_event_timing_mae_s": metrics["matched_timing_mae_frames"] / fps,
        "contact_state_iou": metrics["contact_state_iou"],
        "contact_scored_frames": observed.shape[0],
    }
    for foot in ("left", "right"):
        for event in ("touchdown", "liftoff"):
            detail = metrics["detail"][foot][event]
            prefix = f"contact_{foot}_{event}"
            flat[f"{prefix}_tp"] = detail["tp"]
            flat[f"{prefix}_fp"] = detail["fp"]
            flat[f"{prefix}_fn"] = detail["fn"]
            flat[f"{prefix}_f1"] = detail["f1"]
            flat[f"{prefix}_timing_mae_s"] = (
                detail["matched_timing_mae_frames"] / fps
            )
    return flat


def quaternion_angle_error(first: torch.Tensor, second: torch.Tensor) -> torch.Tensor:
    """Shortest unsigned quaternion angle in radians."""
    denominator = torch.linalg.vector_norm(first, dim=-1) * torch.linalg.vector_norm(
        second, dim=-1
    )
    cosine = (first * second).sum(dim=-1) / denominator.clamp_min(1.0e-12)
    cosine = cosine.abs().clamp(max=1.0)
    angle = 2.0 * torch.acos(cosine)
    return torch.where(cosine > 1.0 - 1.0e-7, torch.zeros_like(angle), angle)


def read_names(path: Path) -> list[str]:
    """Read a comment-tolerant clip list."""
    return [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]


def motion_metadata(names: list[str], bank: Path) -> list[dict[str, Any]]:
    """Read only timeline metadata needed to construct conditions."""
    records = []
    for name in names:
        path = bank / f"{name}.npz"
        if not path.is_file():
            raise FileNotFoundError(path)
        with np.load(path) as archive:
            frames = len(archive["joint_pos"])
            fps = float(np.asarray(archive["fps"]).reshape(-1)[0])
        if frames < 2 or fps <= 0.0:
            raise ValueError(f"{name}: invalid timeline frames={frames}, fps={fps}")
        records.append({"clip": name, "frames": frames, "fps": fps})
    return records


def build_conditions(
    metadata: list[dict[str, Any]],
    phases: list[float],
    episodes: int,
    window_s: float,
    env_seed: int,
    joint_noise_seed: int,
    joint_noise: float,
    nominal: bool,
    nconmax: int,
) -> dict[str, Any]:
    """Build unique, horizon-safe phase conditions across each full clip."""
    if episodes <= 0 or window_s <= 0.0:
        raise ValueError("episodes and window_s must be positive")
    if not phases or any(not 0.0 <= phase <= 1.0 for phase in phases):
        raise ValueError("phases must be a non-empty list in [0, 1]")

    conditions = []
    world_id = 0
    for record in metadata:
        frames = int(record["frames"])
        fps = float(record["fps"])
        requested_horizon = round(window_s * fps)
        horizon = min(max(requested_horizon, 1), frames - 1)
        max_start = frames - horizon - 1
        starts = sorted({round(phase * max_start) for phase in phases})
        for start in starts:
            actual_phase = start / max(max_start, 1)
            for replicate in range(episodes):
                conditions.append(
                    {
                        "world_id": world_id,
                        "condition_id": (f"{record['clip']}@{start}:r{replicate}"),
                        "clip": record["clip"],
                        "start_frame": start,
                        "phase": actual_phase,
                        "replicate": replicate,
                        "horizon_steps": horizon,
                        "full_window": requested_horizon <= frames - 1,
                    }
                )
                world_id += 1
    return {
        "schema_version": SCHEMA,
        "window_s": window_s,
        "requested_phases": phases,
        "episodes_per_start": episodes,
        "environment_seed": env_seed,
        "joint_noise_seed": joint_noise_seed,
        "joint_noise": joint_noise,
        "nominal": nominal,
        "nconmax_per_world": nconmax,
        "motions": metadata,
        "conditions": conditions,
    }


def load_or_create_manifest(
    path: Path,
    metadata: list[dict[str, Any]],
    phases: list[float],
    episodes: int,
    window_s: float,
    env_seed: int,
    joint_noise_seed: int,
    joint_noise: float,
    nominal: bool,
    nconmax: int,
) -> dict[str, Any]:
    """Create conditions once or validate an existing manifest exactly."""
    expected = build_conditions(
        metadata,
        phases,
        episodes,
        window_s,
        env_seed,
        joint_noise_seed,
        joint_noise,
        nominal,
        nconmax,
    )
    if path.exists():
        actual = json.loads(path.read_text())
        if actual != expected:
            raise ValueError(
                f"{path}: existing condition manifest differs from requested setup"
            )
        return actual
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(expected, indent=1) + "\n")
    return expected


def evaluate(args: argparse.Namespace) -> int:
    """Run one policy/reference cell under a frozen condition manifest."""
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.rl import RslRlVecEnvWrapper
    from mjlab.sensor import ContactMatch, ContactSensorCfg
    from mjlab.tasks.registry import load_rl_cfg, load_runner_cls

    import climb  # noqa: F401
    from climb import climb_g1_tracking_env_cfg
    from climb.motion_bank import MotionBank

    clips_path = args.clips.resolve()
    bank = args.bank.resolve()
    checkpoint = args.checkpoint.resolve()
    names = read_names(clips_path)
    metadata = motion_metadata(names, bank)
    active_reference_sha256 = selected_file_hashes(names, bank)
    if (args.reference_contact_manifest is None) != (
        args.contact_validation_report is None
    ):
        raise ValueError(
            "reference-contact manifest and validation report must be supplied together"
        )
    reference_contact: dict[str, np.ndarray] | None = None
    contact_provenance: dict[str, Any] | None = None
    if args.reference_contact_manifest is not None:
        reference_contact, contact_provenance = load_validated_contact_proxy(
            args.reference_contact_manifest,
            args.contact_validation_report,
            names,
            active_reference_sha256,
        )
    phases = [float(value) for value in args.phases.split(",") if value]
    manifest = load_or_create_manifest(
        args.conditions.resolve(),
        metadata,
        phases,
        args.episodes,
        args.window,
        args.seed,
        args.joint_noise_seed,
        args.joint_noise,
        args.nominal,
        args.nconmax,
    )
    conditions = manifest["conditions"]
    num_envs = len(conditions)
    if num_envs == 0:
        raise ValueError("condition manifest contains no worlds")

    files = [str(bank / f"{name}.npz") for name in names]
    clip_index = {name: index for index, name in enumerate(names)}
    task = "Climb-Tracking-Flat-Unitree-G1"
    env_cfg = climb_g1_tracking_env_cfg(
        motion_files=files,
        sampling_mode="uniform",
    )
    env_cfg.scene.num_envs = num_envs
    env_cfg.seed = int(manifest["environment_seed"])
    env_cfg.auto_reset = False
    env_cfg.sim.nconmax = max(env_cfg.sim.nconmax or 0, args.nconmax)
    feet_ground_cfg = ContactSensorCfg(
        name="eval_feet_ground_contact",
        primary=ContactMatch(
            mode="subtree",
            pattern=r"^(left_ankle_roll_link|right_ankle_roll_link)$",
            entity="robot",
        ),
        secondary=ContactMatch(mode="body", pattern="terrain"),
        fields=("found", "force", "dist"),
        reduce="mindist",
        num_slots=1,
        track_air_time=True,
        history_length=env_cfg.decimation,
    )
    env_cfg.scene.sensors = (env_cfg.scene.sensors or ()) + (feet_ground_cfg,)
    env_cfg.commands["motion"].resampling_time_range = (1.0e9, 1.0e9)
    env_cfg.events.pop("push_robot", None)
    if args.nominal:
        for name in ("base_com", "foot_friction", "encoder_bias"):
            env_cfg.events.pop(name, None)
    for group in env_cfg.observations.values():
        group.enable_corruption = False

    agent_cfg = load_rl_cfg(task)
    env = ManagerBasedRlEnv(cfg=env_cfg, device=args.device)
    wrapped = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)
    runner_cls = load_runner_cls(task)
    if runner_cls is None:
        raise RuntimeError(f"{task}: no registered runner class")
    runner = runner_cls(wrapped, asdict(agent_cfg), device=args.device)
    runner.load(
        str(checkpoint),
        load_cfg={"actor": True},
        strict=True,
        map_location=args.device,
    )
    policy = runner.get_inference_policy(device=args.device)

    cmd = cast(Any, env.command_manager.get_term("motion"))
    foot_sensor = cast(Any, env.scene["eval_feet_ground_contact"])
    expected_foot_names = (
        "left_ankle_roll_link",
        "right_ankle_roll_link",
    )
    if tuple(foot_sensor.primary_names) != expected_foot_names:
        raise RuntimeError(
            "foot sensor order mismatch: "
            f"{tuple(foot_sensor.primary_names)} != {expected_foot_names}"
        )
    foot_body_indexes = torch.tensor(
        [cmd.cfg.body_names.index(name) for name in expected_foot_names],
        dtype=torch.long,
        device=torch.device(args.device),
    )
    startup_randomization_sha256 = sha256_tensors(
        {
            "body_ipos": env.sim.model.body_ipos,
            "encoder_bias": cmd.robot.data.encoder_bias,
            "geom_friction": env.sim.model.geom_friction,
        }
    )
    device = torch.device(args.device)
    common_reference_path = (
        None
        if args.common_reference_bank is None
        else args.common_reference_bank.resolve()
    )
    common_motion: MotionBank | None = None
    if common_reference_path is not None:
        common_files = [str(common_reference_path / f"{name}.npz") for name in names]
        common_motion = MotionBank(
            common_files,
            cmd.body_indexes,
            device=args.device,
            expected_fps=cmd.motion.fps,
        )
        if common_motion.clip_names != names or not torch.equal(
            common_motion.clip_len, cmd.motion.clip_len
        ):
            raise ValueError(
                "common-reference bank must match active clip names and lengths"
            )
    clip_ids = torch.tensor(
        [clip_index[row["clip"]] for row in conditions],
        dtype=torch.long,
        device=device,
    )
    local_starts = torch.tensor(
        [row["start_frame"] for row in conditions],
        dtype=torch.long,
        device=device,
    )
    horizons = torch.tensor(
        [row["horizon_steps"] for row in conditions],
        dtype=torch.long,
        device=device,
    )
    if reference_contact is not None:
        if any(not np.isclose(record["fps"], 50.0) for record in metadata):
            raise ValueError("validated contact timing currently requires 50 Hz references")
        if not np.isclose(env.step_dt, 1.0 / 50.0):
            raise ValueError("environment step does not align with 50 Hz contact labels")

    cmd.assign_clips(clip_ids, at_start=True)
    cmd.time_steps[:] = cmd.motion.clip_start[clip_ids] + local_starts
    env_ids = torch.arange(num_envs, device=device)
    cmd._finalize_reference(env_ids)

    joint_shape = env.sim.data.qpos[:, 7:].shape
    generator = torch.Generator(device="cpu").manual_seed(
        int(manifest["joint_noise_seed"])
    )
    joint_noise = (
        torch.rand(joint_shape, generator=generator) * 2.0 - 1.0
    ) * args.joint_noise
    env.sim.data.qpos[:, 7:] += joint_noise.to(device)
    env.sim.forward()
    cmd.update_relative_body_poses()
    obs = wrapped.get_observations()
    initial_state_sha256 = sha256_tensors(
        {
            "qpos": env.sim.data.qpos,
            "qvel": env.sim.data.qvel,
        }
    )

    alive = torch.ones(num_envs, dtype=torch.bool, device=device)
    success = torch.zeros(num_envs, dtype=torch.bool, device=device)
    survived_steps = torch.zeros(num_envs, device=device)
    causes: list[list[str]] = [[] for _ in range(num_envs)]

    available_metrics = [name for name in ERROR_METRICS if name in cmd.metrics]
    metric_sum = {
        name: torch.zeros(num_envs, device=device) for name in available_metrics
    }
    metric_last = {
        name: torch.zeros(num_envs, device=device) for name in available_metrics
    }
    common_metric_names = (
        "common_anchor_position_error_m",
        "common_anchor_orientation_error_rad",
        "common_root_relative_mpkpe_m",
        "common_body_orientation_error_rad",
        "common_root_relative_velocity_error_mps",
        "common_joint_position_error_rad",
        "common_joint_velocity_error_rps",
        "active_to_common_root_relative_mpkpe_m",
        "active_to_common_body_orientation_error_rad",
        "active_to_common_root_relative_velocity_error_mps",
        "common_body_acceleration_error_mps2",
        "common_body_jerk_error_mps3",
    )
    common_metric_sum = {
        name: torch.zeros(num_envs, device=device) for name in common_metric_names
    }
    common_acceleration_count = torch.zeros(num_envs, device=device)
    common_jerk_count = torch.zeros(num_envs, device=device)

    force_hi = torch.tensor(
        env.sim.mj_model.actuator_forcerange[:, 1].copy(),
        dtype=torch.float32,
        device=device,
    )
    force_limited = force_hi > 0
    saturation_threshold = 0.98 * force_hi
    limited_count = max(int(force_limited.sum()), 1)
    effort_sum = torch.zeros(num_envs, device=device)
    effort_peak = torch.zeros(num_envs, device=device)
    effort_last = torch.zeros(num_envs, device=device)
    work_sum = torch.zeros(num_envs, device=device)
    action_rate_sum = torch.zeros(num_envs, device=device)
    action_rate_count = torch.zeros(num_envs, device=device)
    joint_limit_sum = torch.zeros(num_envs, device=device)
    foot_contact_sum = torch.zeros(num_envs, device=device)
    foot_slip_sum = torch.zeros(num_envs, device=device)
    foot_penetration_sum = torch.zeros(num_envs, device=device)
    foot_switch_sum = torch.zeros(num_envs, device=device)
    foot_switch_count = torch.zeros(num_envs, device=device)
    acceleration_error_sum = torch.zeros(num_envs, device=device)
    acceleration_error_count = torch.zeros(num_envs, device=device)
    jerk_error_sum = torch.zeros(num_envs, device=device)
    jerk_error_count = torch.zeros(num_envs, device=device)
    previous_actions: torch.Tensor | None = None
    previous_contact: torch.Tensor | None = None
    previous_robot_velocity: torch.Tensor | None = None
    previous_reference_velocity: torch.Tensor | None = None
    previous_common_velocity: torch.Tensor | None = None
    previous_robot_acceleration: torch.Tensor | None = None
    previous_reference_acceleration: torch.Tensor | None = None
    previous_common_acceleration: torch.Tensor | None = None

    max_steps = int(horizons.max())
    contact_history = (
        None
        if reference_contact is None
        else torch.zeros((max_steps, num_envs, 2), dtype=torch.bool, device=device)
    )
    with torch.inference_mode():
        for step in range(max_steps):
            actions = policy(obs)
            active = alive.clone()
            obs, _, dones, _ = wrapped.step(actions)
            failed = env.termination_manager.terminated.bool()

            survived_steps += active.float()
            for name in available_metrics:
                value = cmd.metrics[name]
                metric_sum[name] += torch.where(active, value, torch.zeros_like(value))
                metric_last[name] = torch.where(active, value, metric_last[name])

            common_velocity: torch.Tensor | None = None
            if common_motion is not None:
                local_steps = cmd.time_steps - cmd.motion.clip_start[clip_ids]
                active_local_steps = local_steps[active]
                if bool((active_local_steps < 0).any()) or bool(
                    (
                        active_local_steps
                        >= common_motion.clip_len[clip_ids][active]
                    ).any()
                ):
                    raise RuntimeError("active reference escaped common timeline")
                # Retired vector worlds continue to advance and may be reset while
                # other worlds finish. Clamp their unused lookup indices; every
                # accumulator below is masked by `active`.
                safe_local_steps = local_steps.clamp_min(0).minimum(
                    common_motion.clip_len[clip_ids] - 1
                )
                common_steps = common_motion.clip_start[clip_ids] + safe_local_steps
                common_position = (
                    common_motion.body_pos_w[common_steps]
                    + env.scene.env_origins[:, None, :]
                )
                common_orientation = common_motion.body_quat_w[common_steps]
                common_velocity = common_motion.body_lin_vel_w[common_steps]
                common_joint_position = common_motion.joint_pos[common_steps]
                common_joint_velocity = common_motion.joint_vel[common_steps]
                robot_position = cmd.robot_body_pos_w
                robot_orientation = cmd.robot_body_quat_w
                robot_velocity_now = cmd.robot_body_lin_vel_w
                anchor_index = cmd.motion_anchor_body_index
                robot_relative_position = (
                    robot_position - robot_position[:, anchor_index : anchor_index + 1]
                )
                common_relative_position = (
                    common_position
                    - common_position[:, anchor_index : anchor_index + 1]
                )
                active_position = cmd.body_pos_w
                active_relative_position = (
                    active_position
                    - active_position[:, anchor_index : anchor_index + 1]
                )
                robot_relative_velocity = (
                    robot_velocity_now
                    - robot_velocity_now[:, anchor_index : anchor_index + 1]
                )
                common_relative_velocity = (
                    common_velocity
                    - common_velocity[:, anchor_index : anchor_index + 1]
                )
                active_velocity = cmd.body_lin_vel_w
                active_relative_velocity = (
                    active_velocity
                    - active_velocity[:, anchor_index : anchor_index + 1]
                )
                common_values = {
                    "common_anchor_position_error_m": torch.linalg.vector_norm(
                        robot_position[:, anchor_index]
                        - common_position[:, anchor_index],
                        dim=-1,
                    ),
                    "common_anchor_orientation_error_rad": quaternion_angle_error(
                        robot_orientation[:, anchor_index],
                        common_orientation[:, anchor_index],
                    ),
                    "common_root_relative_mpkpe_m": torch.linalg.vector_norm(
                        robot_relative_position - common_relative_position,
                        dim=-1,
                    ).mean(dim=1),
                    "common_body_orientation_error_rad": quaternion_angle_error(
                        robot_orientation, common_orientation
                    ).mean(dim=1),
                    "common_root_relative_velocity_error_mps": (
                        torch.linalg.vector_norm(
                            robot_relative_velocity - common_relative_velocity,
                            dim=-1,
                        ).mean(dim=1)
                    ),
                    "common_joint_position_error_rad": (
                        cmd.robot.data.joint_pos - common_joint_position
                    )
                    .abs()
                    .mean(dim=1),
                    "common_joint_velocity_error_rps": (
                        cmd.robot.data.joint_vel - common_joint_velocity
                    )
                    .abs()
                    .mean(dim=1),
                    "active_to_common_root_relative_mpkpe_m": (
                        torch.linalg.vector_norm(
                            active_relative_position - common_relative_position,
                            dim=-1,
                        ).mean(dim=1)
                    ),
                    "active_to_common_body_orientation_error_rad": (
                        quaternion_angle_error(
                            cmd.body_quat_w, common_orientation
                        ).mean(dim=1)
                    ),
                    "active_to_common_root_relative_velocity_error_mps": (
                        torch.linalg.vector_norm(
                            active_relative_velocity - common_relative_velocity,
                            dim=-1,
                        ).mean(dim=1)
                    ),
                }
                for name, value in common_values.items():
                    common_metric_sum[name] += torch.where(
                        active, value, torch.zeros_like(value)
                    )

            force = env.sim.data.actuator_force
            saturation = (
                (force.abs() >= saturation_threshold) & force_limited
            ).float().sum(dim=1) / limited_count
            effort_sum += torch.where(active, saturation, torch.zeros_like(saturation))
            effort_peak = torch.where(
                active, torch.maximum(effort_peak, saturation), effort_peak
            )
            effort_last = torch.where(active, saturation, effort_last)

            joint_velocity = cmd.robot.data.joint_vel
            if joint_velocity.shape[1] == force.shape[1]:
                power = (force * joint_velocity).abs().mean(dim=1) * env.step_dt
                work_sum += torch.where(active, power, torch.zeros_like(power))

            limits = cmd.robot.data.soft_joint_pos_limits
            joint_position = cmd.robot.data.joint_pos
            span = (limits[:, :, 1] - limits[:, :, 0]).clamp_min(1.0e-6)
            margin = 0.02 * span
            near_limit = (
                (
                    (joint_position <= limits[:, :, 0] + margin)
                    | (joint_position >= limits[:, :, 1] - margin)
                )
                .float()
                .mean(dim=1)
            )
            joint_limit_sum += torch.where(
                active, near_limit, torch.zeros_like(near_limit)
            )

            found = foot_sensor.data.found
            distance = foot_sensor.data.dist
            force_history = foot_sensor.data.force_history
            if found is None or distance is None:
                raise RuntimeError("foot contact sensor did not expose found/dist")
            contact = found > 0
            if force_history is not None:
                contact |= (torch.linalg.vector_norm(force_history, dim=-1) > 1.0).any(
                    dim=2
                )
            if contact.shape != (num_envs, 2):
                raise RuntimeError(
                    f"unexpected foot-contact shape {tuple(contact.shape)}"
                )
            if contact_history is not None:
                contact_history[step] = contact & active[:, None]
            contact_fraction = contact.float().mean(dim=1)
            foot_velocity = cmd.robot_body_lin_vel_w[:, foot_body_indexes, :2]
            foot_speed = torch.linalg.vector_norm(foot_velocity, dim=-1)
            contact_count = contact.float().sum(dim=1).clamp_min(1.0)
            foot_slip = (foot_speed * contact).sum(dim=1) / contact_count
            penetration = ((-distance).clamp_min(0.0) * contact).sum(
                dim=1
            ) / contact_count
            foot_contact_sum += torch.where(
                active, contact_fraction, torch.zeros_like(contact_fraction)
            )
            foot_slip_sum += torch.where(active, foot_slip, torch.zeros_like(foot_slip))
            foot_penetration_sum += torch.where(
                active, penetration, torch.zeros_like(penetration)
            )
            if previous_contact is not None:
                switched = (contact != previous_contact).float().mean(dim=1)
                foot_switch_sum += torch.where(
                    active, switched, torch.zeros_like(switched)
                )
                foot_switch_count += active.float()
            previous_contact = contact.clone()

            robot_velocity = cmd.robot_body_lin_vel_w
            reference_velocity = cmd.body_lin_vel_w
            if (
                previous_robot_velocity is not None
                and previous_reference_velocity is not None
            ):
                robot_acceleration = (
                    robot_velocity - previous_robot_velocity
                ) / env.step_dt
                reference_acceleration = (
                    reference_velocity - previous_reference_velocity
                ) / env.step_dt
                acceleration_error = torch.linalg.vector_norm(
                    robot_acceleration - reference_acceleration, dim=-1
                ).mean(dim=1)
                acceleration_error_sum += torch.where(
                    active, acceleration_error, torch.zeros_like(acceleration_error)
                )
                acceleration_error_count += active.float()
                common_acceleration: torch.Tensor | None = None
                if common_velocity is not None and previous_common_velocity is not None:
                    common_acceleration = (
                        common_velocity - previous_common_velocity
                    ) / env.step_dt
                    common_acceleration_error = torch.linalg.vector_norm(
                        robot_acceleration - common_acceleration, dim=-1
                    ).mean(dim=1)
                    common_metric_sum["common_body_acceleration_error_mps2"] += (
                        torch.where(
                            active,
                            common_acceleration_error,
                            torch.zeros_like(common_acceleration_error),
                        )
                    )
                    common_acceleration_count += active.float()
                if (
                    previous_robot_acceleration is not None
                    and previous_reference_acceleration is not None
                ):
                    jerk_error = (
                        torch.linalg.vector_norm(
                            (robot_acceleration - previous_robot_acceleration)
                            - (
                                reference_acceleration - previous_reference_acceleration
                            ),
                            dim=-1,
                        ).mean(dim=1)
                        / env.step_dt
                    )
                    jerk_error_sum += torch.where(
                        active, jerk_error, torch.zeros_like(jerk_error)
                    )
                    jerk_error_count += active.float()
                    if (
                        common_acceleration is not None
                        and previous_common_acceleration is not None
                    ):
                        common_jerk_error = (
                            torch.linalg.vector_norm(
                                (robot_acceleration - previous_robot_acceleration)
                                - (common_acceleration - previous_common_acceleration),
                                dim=-1,
                            ).mean(dim=1)
                            / env.step_dt
                        )
                        common_metric_sum["common_body_jerk_error_mps3"] += torch.where(
                            active,
                            common_jerk_error,
                            torch.zeros_like(common_jerk_error),
                        )
                        common_jerk_count += active.float()
                previous_robot_acceleration = robot_acceleration.clone()
                previous_reference_acceleration = reference_acceleration.clone()
                if common_acceleration is not None:
                    previous_common_acceleration = common_acceleration.clone()
            previous_robot_velocity = robot_velocity.clone()
            previous_reference_velocity = reference_velocity.clone()
            if common_velocity is not None:
                previous_common_velocity = common_velocity.clone()

            if previous_actions is not None:
                action_rate = (actions - previous_actions).abs().mean(dim=1)
                action_rate_sum += torch.where(
                    active, action_rate, torch.zeros_like(action_rate)
                )
                action_rate_count += active.float()
            previous_actions = actions.clone()

            active_failures = active & failed
            for term_name in env.termination_manager.active_terms:
                term = env.termination_manager.get_term(term_name)
                indices = torch.where(active_failures & term)[0].cpu().tolist()
                for index in indices:
                    causes[index].append(term_name)

            reached = (step + 1) >= horizons
            success |= active & reached & ~failed
            alive &= ~(failed | reached)
            if not bool(alive.any()):
                break

            # auto_reset=False preserves terminal state for the reads above.
            # Clear every simulator termination before the next vector step,
            # including already-retired worlds that later drift into a limit.
            reset_ids = torch.where(dones.bool())[0]
            if reset_ids.numel() > 0:
                env.reset(env_ids=reset_ids)
                obs = wrapped.get_observations()

    denominator = survived_steps.clamp_min(1.0)
    rows = []
    for index, condition in enumerate(conditions):
        row: dict[str, Any] = {
            **condition,
            "actual_window_s": round(
                float(condition["horizon_steps"]) * env.step_dt, 6
            ),
            "success": int(success[index]),
            "survival_s": round(float(survived_steps[index]) * env.step_dt, 6),
            "termination_causes": ";".join(sorted(set(causes[index]))),
            "effort_sat_mean": float(effort_sum[index] / denominator[index]),
            "effort_sat_peak": float(effort_peak[index]),
            "effort_sat_terminal": float(effort_last[index]),
            "absolute_mechanical_work_per_actuator_j": float(work_sum[index]),
            "action_delta_mean_per_step": float(
                action_rate_sum[index] / action_rate_count[index].clamp_min(1.0)
            ),
            "joint_limit_exposure": float(joint_limit_sum[index] / denominator[index]),
            "foot_contact_fraction": float(
                foot_contact_sum[index] / denominator[index]
            ),
            "contacting_ankle_link_speed_mean_mps": float(
                foot_slip_sum[index] / denominator[index]
            ),
            "foot_penetration_mean_m": float(
                foot_penetration_sum[index] / denominator[index]
            ),
            "foot_contact_switch_rate_hz": float(
                foot_switch_sum[index]
                / (foot_switch_count[index].clamp_min(1.0) * env.step_dt)
            ),
            "body_acceleration_error_mean_mps2": float(
                acceleration_error_sum[index]
                / acceleration_error_count[index].clamp_min(1.0)
            ),
            "body_jerk_error_mean_mps3": float(
                jerk_error_sum[index] / jerk_error_count[index].clamp_min(1.0)
            ),
        }
        for name in available_metrics:
            row[f"{name}_mean"] = float(metric_sum[name][index] / denominator[index])
            row[f"{name}_terminal"] = float(metric_last[name][index])
        if common_motion is not None:
            for name in common_metric_names:
                count = denominator[index]
                if name == "common_body_acceleration_error_mps2":
                    count = common_acceleration_count[index].clamp_min(1.0)
                elif name == "common_body_jerk_error_mps3":
                    count = common_jerk_count[index].clamp_min(1.0)
                row[f"{name}_mean"] = float(common_metric_sum[name][index] / count)
        if reference_contact is not None and contact_history is not None:
            survived = int(survived_steps[index])
            observed = contact_history[:survived, index].cpu().numpy()
            row.update(
                score_contact_window(
                    reference_contact[condition["clip"]],
                    observed,
                    start_frame=int(condition["start_frame"]),
                    fps=50.0,
                )
            )
        rows.append(row)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    meta_path = Path(f"{args.out}.meta.json")
    meta = {
        "schema_version": "paired_eval_output/1",
        "classification": "post-audit evaluator; does not replace sealed outputs",
        "task": task,
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": sha256_file(checkpoint),
        "clips": str(clips_path),
        "clips_sha256": sha256_file(clips_path),
        "bank": str(bank),
        "selected_reference_sha256": active_reference_sha256,
        "common_reference_bank": (
            None if common_reference_path is None else str(common_reference_path)
        ),
        "common_reference_sha256": (
            None
            if common_reference_path is None
            else selected_file_hashes(names, common_reference_path)
        ),
        "conditions": str(args.conditions.resolve()),
        "conditions_sha256": sha256_file(args.conditions.resolve()),
        "validated_reference_contact": contact_provenance,
        "evaluator_sha256": sha256_file(Path(__file__).resolve()),
        "device": args.device,
        "nominal": args.nominal,
        "joint_noise": args.joint_noise,
        "nconmax_per_world": env_cfg.sim.nconmax,
        "startup_randomization_sha256": startup_randomization_sha256,
        "initial_state_sha256": initial_state_sha256,
        "software_versions": software_versions(),
        "source_sha256": {
            str(path.relative_to(ROOT)): sha256_file(path)
            for path in (
                ROOT / "climb" / "commands.py",
                ROOT / "climb" / "env_cfg.py",
                ROOT / "climb" / "motion_bank.py",
                ROOT / "climb" / "contact_timing.py",
                ROOT
                / "mjlab-1.6.0"
                / "src"
                / "mjlab"
                / "envs"
                / "manager_based_rl_env.py",
                ROOT
                / "mjlab-1.6.0"
                / "src"
                / "mjlab"
                / "tasks"
                / "tracking"
                / "mdp"
                / "commands.py",
            )
        },
        "worlds": num_envs,
        "full_window_worlds": sum(row["full_window"] for row in conditions),
        "output": str(args.out.resolve()),
    }
    meta_path.write_text(json.dumps(meta, indent=1) + "\n")
    print(f"[paired-v2] wrote {args.out} ({num_envs} episode rows)")
    print(f"[paired-v2] metadata -> {meta_path}")
    env.close()
    return 0


def synthetic() -> None:
    """Check unique phase coverage and the no-wrap horizon invariant."""
    metadata = [
        {"clip": "long", "frames": 501, "fps": 50.0},
        {"clip": "short", "frames": 101, "fps": 50.0},
    ]
    result = build_conditions(
        metadata,
        [0.0, 0.5, 1.0],
        episodes=2,
        window_s=3.0,
        env_seed=7,
        joint_noise_seed=11,
        joint_noise=0.05,
        nominal=False,
        nconmax=70,
    )
    long = [row for row in result["conditions"] if row["clip"] == "long"]
    short = [row for row in result["conditions"] if row["clip"] == "short"]
    assert {row["start_frame"] for row in long} == {0, 175, 350}
    assert {row["start_frame"] for row in short} == {0}
    assert all(row["start_frame"] + row["horizon_steps"] < 501 for row in long)
    assert all(row["start_frame"] + row["horizon_steps"] < 101 for row in short)
    assert all(row["full_window"] for row in long)
    assert not any(row["full_window"] for row in short)
    print("paired evaluator synthetic phase and horizon invariants pass")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--clips", type=Path)
    parser.add_argument("--bank", type=Path)
    parser.add_argument("--common-reference-bank", type=Path)
    parser.add_argument("--reference-contact-manifest", type=Path)
    parser.add_argument("--contact-validation-report", type=Path)
    parser.add_argument("--conditions", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--phases", default=DEFAULT_PHASES)
    parser.add_argument("--episodes", type=int, default=8)
    parser.add_argument("--window", type=float, default=3.0)
    parser.add_argument("--seed", type=int, default=20260820)
    parser.add_argument("--joint-noise-seed", type=int, default=20260821)
    parser.add_argument("--joint-noise", type=float, default=0.05)
    parser.add_argument("--nconmax", type=int, default=70)
    parser.add_argument("--nominal", action="store_true")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    if args.synthetic:
        synthetic()
        return 0
    required = (args.checkpoint, args.clips, args.bank, args.conditions, args.out)
    if any(value is None for value in required):
        parser.error(
            "--checkpoint, --clips, --bank, --conditions, and --out are required"
        )
    return evaluate(args)


if __name__ == "__main__":
    raise SystemExit(main())
