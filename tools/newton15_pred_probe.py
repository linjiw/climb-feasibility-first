#!/usr/bin/env python3
"""Measure the sealed Newton 1.5 no-training predictive panel.

The scientific and manipulation contract is sealed in
``plan/PREREGISTRATION_NEWTON_PRED.md``. This implementation writes the 42x3
effect table and a fail-closed probe manifest; it never trains a policy.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import newton15_recert as recert
import s1_newton_conformance as s1

AXES = ("delay_20ms", "motor_clamp_85pct", "newton_contact")
POLICIES = ("development", "adaptive", "grounded")
PROBE_STEPS = 25
REPLICATES = 8
IC_SEED = 20260827
BOOTSTRAP_SEED = 20260828
DETERMINISTIC_MAX_RECORDS = 630


def sha256_file(path: Path) -> str:
    """Return a file's SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def flatten_observation(value: Any) -> torch.Tensor:
    """Flatten a tensor or nested observation mapping in stable key order."""
    if isinstance(value, torch.Tensor):
        return value.reshape(value.shape[0], -1)
    if isinstance(value, dict) or (
        hasattr(value, "keys") and hasattr(value, "__getitem__")
    ):
        return torch.cat(
            [flatten_observation(value[key]) for key in sorted(value.keys(), key=str)],
            dim=1,
        )
    raise TypeError(f"unsupported observation type: {type(value)!r}")


def configure_determinism() -> None:
    """Enable the same deterministic physics mode as Phase N-b."""
    import warp as wp

    wp.config.deterministic = wp.DeterministicMode.RUN_TO_RUN
    wp.config.deterministic_max_records = DETERMINISTIC_MAX_RECORDS
    recert.configure_sensor_module_nondeterministic()


def load_reference_rows(path: Path) -> list[dict[str, Any]]:
    """Load and validate the sealed 42-unit reference table."""
    with path.open(newline="") as handle:
        rows: list[dict[str, Any]] = list(csv.DictReader(handle))
    indices = [int(row["table_index"]) for row in rows]
    if indices != list(range(42)):
        raise ValueError("reference table must be ordered table_index 0..41")
    return rows


def build_conditions(
    reference_rows: list[dict[str, Any]],
    *,
    replicates: int,
    paired: bool,
) -> list[dict[str, Any]]:
    """Build deterministic unit-major, replicate-major condition rows."""
    conditions = []
    for row in reference_rows:
        for replicate in range(replicates):
            for condition in range(2 if paired else 1):
                conditions.append(
                    {
                        "table_index": int(row["table_index"]),
                        "unit_id": int(row["unit_id"]),
                        "clip_id": int(row["clip_id"]),
                        "clip": row["clip"],
                        "replicate": replicate,
                        "condition": condition,
                        "start_frame": int(row["canonical_start_frame"]),
                    }
                )
    return conditions


def build_env(
    *,
    checkpoint: Path,
    unit_table: Path,
    bank: Path,
    num_envs: int,
    seed: int,
    device: str,
) -> tuple[Any, Any, Any, Any]:
    """Build a nominal, segment-native environment and frozen policy."""
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.rl import RslRlVecEnvWrapper
    from mjlab.tasks.tracking.config.g1.rl_cfg import (
        unitree_g1_tracking_ppo_runner_cfg,
    )
    from mjlab.tasks.tracking.rl import MotionTrackingOnPolicyRunner

    from climb.segment_command import SegmentNativeMotionCommand
    from climb.segment_env_cfg import segment_native_g1_tracking_env_cfg

    torch.manual_seed(seed)
    np.random.seed(seed)
    table = json.loads(unit_table.read_text())
    motion_files = [
        str((bank / f"{row['clip']}.npz").resolve()) for row in table["sources"]
    ]
    cfg = segment_native_g1_tracking_env_cfg(
        motion_files=motion_files,
        segment_manifest=str(unit_table.resolve()),
        segment_sampling_mode="uniform",
        sampler_seed=seed,
        env_seed=seed,
        failure_penalty=0.0,
    )
    cfg.scene.num_envs = num_envs
    # Every world shares one origin: MJWarp worlds never interact, and the
    # sealed cross-condition check demands byte-identical canonical states
    # between paired worlds (the default 2 m spacing offsets root x).
    cfg.scene.env_spacing = 0.0
    cfg.auto_reset = False
    for event in ("push_robot", "base_com", "foot_friction", "encoder_bias"):
        cfg.events.pop(event, None)
    for group in cfg.observations.values():
        group.enable_corruption = False

    agent_cfg = unitree_g1_tracking_ppo_runner_cfg()
    env = ManagerBasedRlEnv(cfg=cfg, device=device)
    wrapped = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)
    runner = MotionTrackingOnPolicyRunner(wrapped, asdict(agent_cfg), device=device)
    runner.load(
        str(checkpoint.resolve()),
        load_cfg={"actor": True},
        strict=True,
        map_location=device,
    )
    policy = runner.get_inference_policy(device=device)
    command = env.command_manager.get_term("motion")
    if not isinstance(command, SegmentNativeMotionCommand):
        raise TypeError("Newton predictive probe requires SegmentNativeMotionCommand")
    return env, wrapped, policy, command


def initial_condition_noise(nq_joint: int) -> dict[str, torch.Tensor]:
    """Generate the frozen N5 perturbation matrix once on CPU."""
    generator = torch.Generator(device="cpu").manual_seed(IC_SEED)
    count = 42 * REPLICATES
    return {
        "joint": (torch.rand(count, nq_joint, generator=generator) * 2 - 1) * 0.05,
        "linear": (torch.rand(count, 3, generator=generator) * 2 - 1) * 0.10,
        "angular": (torch.rand(count, 3, generator=generator) * 2 - 1) * 0.20,
    }


def prepare_worlds(
    env: Any,
    wrapped: Any,
    command: Any,
    conditions: list[dict[str, Any]],
    *,
    device: str,
) -> tuple[Any, dict[str, np.ndarray]]:
    """Assign exact starts, apply paired IC noise, and refresh observations."""
    table_indices = torch.tensor(
        [row["table_index"] for row in conditions],
        dtype=torch.long,
        device=device,
    )
    starts = torch.tensor(
        [row["start_frame"] for row in conditions],
        dtype=torch.long,
        device=device,
    )
    command.assign_segments(table_indices, starts)
    noise = initial_condition_noise(env.sim.mj_model.nq - 7)
    noise_indices = torch.tensor(
        [row["table_index"] * REPLICATES + row["replicate"] for row in conditions],
        dtype=torch.long,
    )
    env.sim.data.qpos[:, 7:] += noise["joint"][noise_indices].to(device)
    env.sim.data.qvel[:, 0:3] += noise["linear"][noise_indices].to(device)
    env.sim.data.qvel[:, 3:6] += noise["angular"][noise_indices].to(device)
    env.sim.data.qacc_warmstart.zero_()
    env.sim.forward()
    env_ids = torch.arange(env.num_envs, device=device)
    env.observation_manager.reset(env_ids)
    env.obs_buf = env.observation_manager.compute(update_history=True, env_ids=env_ids)
    observations = wrapped.get_observations()
    command.assert_active_references_valid()
    initial = {
        "qpos": env.sim.data.qpos.detach().cpu().numpy().copy(),
        "qvel": env.sim.data.qvel.detach().cpu().numpy().copy(),
        "warmstart": env.sim.data.qacc_warmstart.detach().cpu().numpy().copy(),
        "observation": flatten_observation(observations).detach().cpu().numpy().copy(),
        "reference_index": command.time_steps.detach().cpu().numpy().copy(),
    }
    return observations, initial


def build_physics(env: Any, device: str, *, mujoco_contacts: bool) -> Any:
    """Create the certified Newton coupling with one selected contact generator."""
    import newton

    original = newton.solvers.SolverMuJoCo
    if mujoco_contacts:
        physics = s1.NewtonPhysics(env, "mjw", device)
    else:

        def contact_solver(*args: Any, **kwargs: Any) -> Any:
            kwargs["use_mujoco_contacts"] = False
            return original(*args, **kwargs)

        newton.solvers.SolverMuJoCo = contact_solver
        try:
            physics = s1.NewtonPhysics(env, "mjw", device)
        finally:
            newton.solvers.SolverMuJoCo = original
    if not mujoco_contacts:
        attach_newton_collision(physics)
    recert.configure_sensor_module_nondeterministic()
    recert.mirror_newton15_live_fields(physics)
    audit = recert.live_model_diff(physics)
    if audit["mismatch_count"] != 0:
        raise RuntimeError(f"Newton live-model mirror failed: {audit['mismatches']}")
    physics.sync_from_mjlab()
    import warp as wp

    wp.to_torch(physics.solver.mjw_data.qacc_warmstart).zero_()
    return physics


def attach_newton_collision(physics: Any) -> None:
    """Route the `newton_contact` axis through Newton's own collision pipeline.

    With ``use_mujoco_contacts=False`` the solver consumes a ``Contacts`` buffer
    instead of running MJWarp collision detection. The S1 wrapper passes
    ``None`` (it only ever ran MuJoCo-native contacts), so wrap ``solver.step``
    to generate contacts from ``state_in`` every substep. The buffer capacity is
    at least MJWarp's ``naconmax`` so no generated contact is dropped by the
    conversion kernel. Determinism: the pipeline uses Newton's deterministic
    sort buffers under the same Warp mode as the solver.
    """
    import newton

    solver = physics.solver
    if bool(wp_scalar(solver.mjw_model.opt.run_collision_detection)):
        raise RuntimeError("newton_contact axis requested but MJWarp collision is still on")
    naconmax = int(solver.mjw_data.naconmax)
    pipeline = newton.CollisionPipeline(
        physics.model, rigid_contact_max=max(naconmax, 1), broad_phase="explicit"
    )
    buffer = pipeline.contacts()
    original_step = solver.step

    def step(state_in: Any, state_out: Any, control: Any, contacts: Any, dt: float) -> None:
        pipeline.collide(state_in, buffer)
        original_step(state_in, state_out, control, buffer, dt)

    solver.step = step
    physics.newton_collision = {
        "pipeline": pipeline,
        "rigid_contact_max": int(pipeline.rigid_contact_max),
        "naconmax": naconmax,
    }


def wp_scalar(value: Any) -> Any:
    """Return a Python scalar from a Warp array, tensor, or plain value."""
    if hasattr(value, "numpy"):
        array = value.numpy()
        return array.reshape(-1)[0] if getattr(array, "size", 1) else array
    return value


class PairedDelay:
    """Apply a one-control-step target FIFO only to condition-one worlds."""

    def __init__(self, physics: Any, delayed: torch.Tensor):
        self.physics = physics
        self.delayed = delayed
        self.length = physics.decimation + 1
        self.history: torch.Tensor | None = None
        self.head = 0
        physics.ctrl_for_substep = self.control

    def control(self) -> torch.Tensor:
        """Return the nominal or one-control-step delayed target per world."""
        current = self.physics.env.sim.data.ctrl
        if self.history is None:
            self.history = current.unsqueeze(0).repeat(self.length, 1, 1).clone()
        self.head = (self.head + 1) % self.length
        self.history[self.head] = current
        delayed_index = (self.head - self.physics.decimation) % self.length
        output = current.clone()
        output[self.delayed] = self.history[delayed_index, self.delayed]
        return output


def apply_motor_clamp(physics: Any, clamped: torch.Tensor) -> torch.Tensor:
    """Set condition-one effort limits to exactly 85% of nominal."""
    import mujoco_warp as mjw
    import warp as wp
    from mjlab.sim.randomization import expand_model_fields

    with wp.ScopedDevice(physics.wp_device):
        expand_model_fields(
            physics.solver.mjw_model,
            physics.n_env,
            ["actuator_forcerange"],
        )
    force_range = wp.to_torch(physics.solver.mjw_model.actuator_forcerange)
    nominal = force_range.clone()
    force_range[clamped] = nominal[clamped] * 0.85
    with wp.ScopedDevice(physics.wp_device):
        mjw.set_const(physics.solver.mjw_model, physics.solver.mjw_data)
    if not torch.equal(force_range[~clamped], nominal[~clamped]):
        raise RuntimeError("motor clamp changed a nominal world")
    ratio = force_range[clamped] / nominal[clamped]
    finite = nominal[clamped] != 0
    if not torch.allclose(
        ratio[finite], torch.full_like(ratio[finite], 0.85), rtol=0.0, atol=1.0e-7
    ):
        raise RuntimeError("motor-clamp force range is not exactly 85%")
    return force_range


def rollout(
    env: Any,
    wrapped: Any,
    policy: Any,
    command: Any,
    physics: Any,
    observations: Any,
    *,
    effort_limits: torch.Tensor | None = None,
) -> dict[str, Any]:
    """Run a 25-step closed-loop Newton probe with no reset after termination."""
    import warp as wp

    alive = torch.ones(env.num_envs, dtype=torch.bool, device=env.device)
    escaped_reference_frames = 0
    records: dict[str, list[np.ndarray]] = {
        name: []
        for name in (
            "body_pos_err",
            "anchor_ori_err",
            "mechanical_work",
            "effort_saturation",
            "alive",
            "qpos",
            "qvel",
            "actions",
            "reference_index",
        )
    }
    contacts = []
    if not hasattr(env, "_manual_reset_pending"):
        raise AttributeError("mjlab env lacks _manual_reset_pending; probe contract unknown")
    with torch.inference_mode():
        for _ in range(PROBE_STEPS):
            actions = policy(observations)
            # Sealed contract: no reset after termination. mjlab refuses to step
            # a terminated world when auto_reset=False; clear its pending flag so
            # fallen worlds keep evolving physically while ``alive`` masks them
            # out of every paired statistic. No RNG is consumed and no new
            # segment is assigned.
            env._manual_reset_pending.zero_()
            observations, _, _, _ = s1._step_with_external_physics(
                env, wrapped, actions, physics
            )
            terminated = env.termination_manager.terminated.bool()
            alive &= ~terminated
            command.assert_active_references_valid()
            local = command.time_steps - command.motion.clip_start[command.clip_ids]
            escaped = (local < command.local_start_steps) | (
                local >= command.local_trial_end_steps
            )
            escaped_reference_frames += int(escaped.sum())

            actuator_force = wp.to_torch(physics.solver.mjw_data.actuator_force)
            if effort_limits is None:
                force_range = wp.to_torch(physics.solver.mjw_model.actuator_forcerange)
                if force_range.ndim == 2:
                    force_range = force_range.unsqueeze(0).expand(
                        env.num_envs, *force_range.shape
                    )
            else:
                force_range = effort_limits
            limit = force_range[:, :, 1].abs().clamp(min=1.0e-9)
            saturation = (actuator_force.abs() >= 0.999 * limit).float().mean(dim=1)
            work = (actuator_force * command.robot.data.joint_vel).abs().mean(
                dim=1
            ) * env.step_dt
            values = {
                "body_pos_err": command.metrics["error_body_pos"],
                "anchor_ori_err": command.metrics["error_anchor_rot"],
                "mechanical_work": work,
                "effort_saturation": saturation,
                "alive": alive,
                "qpos": env.sim.data.qpos,
                "qvel": env.sim.data.qvel,
                "actions": actions,
                "reference_index": command.time_steps,
            }
            for name, value in values.items():
                records[name].append(value.detach().cpu().numpy().copy())
            signature, _ = recert.contact_snapshot(
                physics.solver.mjw_data, physics.solver.mj_model, env.num_envs
            )
            contacts.append(signature)
    telemetry = command.segment_telemetry()
    return {
        **{name: np.stack(value) for name, value in records.items()},
        "contacts": contacts,
        "escaped_reference_frames": escaped_reference_frames,
        "invalid_starts": int(telemetry["invalid_start_count"]),
        "invalid_reference_frames": int(telemetry["invalid_reference_frame_count"]),
    }


BATCH_WORLDS = 8
OOM_RETRIES = 240
OOM_WAIT_S = 60
"""Worlds per vectorized build.

Warp's run-to-run deterministic scatter buffers grow roughly quadratically with
the number of worlds under the 630-record G1 bound (int32 overflow at 42
worlds, ~2.4 GB at 8). Conditions are therefore executed in fixed-size batches
of independent worlds; every batch is an independent build with the same
sealed starts, noise draws (keyed by unit and replicate), and physics contract.
Paired base/perturbed worlds always share a batch.
"""


def _merge_batch_results(
    parts: list[tuple[dict[str, Any], dict[str, np.ndarray], dict[str, Any]]],
) -> tuple[dict[str, Any], dict[str, np.ndarray], dict[str, Any]]:
    """Concatenate per-batch rollouts along the world axis."""
    results = [part[0] for part in parts]
    initials = [part[1] for part in parts]
    manipulations = [part[2] for part in parts]
    result: dict[str, Any] = {}
    for key, value in results[0].items():
        if isinstance(value, np.ndarray):
            result[key] = np.concatenate([r[key] for r in results], axis=1)
        elif key == "contacts":
            result[key] = [
                [world for r in results for world in r[key][step]]
                for step in range(len(value))
            ]
        elif isinstance(value, (int, np.integer)):
            result[key] = int(sum(int(r[key]) for r in results))
        else:
            raise TypeError(f"cannot merge rollout field {key!r}")
    initial = {
        key: np.concatenate([i[key] for i in initials], axis=0) for key in initials[0]
    }
    manipulation: dict[str, Any] = {}
    for key, value in manipulations[0].items():
        if key in {"delayed_worlds", "clamped_worlds"}:
            manipulation[key] = int(sum(int(m[key]) for m in manipulations))
        else:
            if any(m[key] != value for m in manipulations):
                raise ValueError(f"manipulation field {key!r} differs across batches")
            manipulation[key] = value
    manipulation["batches"] = len(parts)
    manipulation["batch_worlds"] = BATCH_WORLDS
    return result, initial, manipulation


def _worker_batch(payload_path: Path) -> int:
    """Child-process entry: execute one batch and pickle the result."""
    import pickle

    payload = pickle.loads(payload_path.read_bytes())
    configure_determinism()
    part = _run_condition_batch(
        checkpoint=Path(payload["checkpoint"]),
        unit_table=Path(payload["unit_table"]),
        bank=Path(payload["bank"]),
        conditions=payload["conditions"],
        device=payload["device"],
        axis=payload["axis"],
        mujoco_contacts=payload["mujoco_contacts"],
    )
    Path(payload["result_path"]).write_bytes(pickle.dumps(part))
    return 0


def run_condition_set(
    *,
    checkpoint: Path,
    unit_table: Path,
    bank: Path,
    conditions: list[dict[str, Any]],
    device: str,
    axis: str,
    mujoco_contacts: bool = True,
) -> tuple[dict[str, Any], dict[str, np.ndarray], dict[str, Any]]:
    """Execute a condition set in world batches and merge in condition order.

    Each batch runs in a fresh child process: Warp's memory pool does not return
    a closed environment's allocations to the device, so in-process batches
    accumulate until the shared GPU is exhausted.
    """
    import pickle
    import subprocess
    import sys
    import tempfile

    if BATCH_WORLDS < 2 or BATCH_WORLDS % 2:
        raise ValueError("BATCH_WORLDS must be an even positive integer")
    parts = []
    total = (len(conditions) + BATCH_WORLDS - 1) // BATCH_WORLDS
    with tempfile.TemporaryDirectory(prefix="newton15_pred_batch_") as tmp:
        for offset in range(0, len(conditions), BATCH_WORLDS):
            chunk = conditions[offset : offset + BATCH_WORLDS]
            index = offset // BATCH_WORLDS + 1
            print(f"    batch {index}/{total} ({len(chunk)} worlds)", flush=True)
            payload_path = Path(tmp) / f"payload_{index}.pkl"
            result_path = Path(tmp) / f"result_{index}.pkl"
            payload_path.write_bytes(
                pickle.dumps(
                    {
                        "checkpoint": str(checkpoint),
                        "unit_table": str(unit_table),
                        "bank": str(bank),
                        "conditions": chunk,
                        "device": device,
                        "axis": axis,
                        "mujoco_contacts": mujoco_contacts,
                        "result_path": str(result_path),
                    }
                )
            )
            for attempt in range(OOM_RETRIES + 1):
                completed = subprocess.run(
                    [sys.executable, str(Path(__file__).resolve()), "--worker-batch", str(payload_path)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if completed.returncode == 0 and result_path.exists():
                    break
                tail = (completed.stderr or "")[-4000:]
                lowered = tail.lower()
                transient = "out of memory" in lowered or "failed to allocate" in lowered
                if not transient or attempt == OOM_RETRIES:
                    sys.stderr.write(tail)
                    raise RuntimeError(f"batch {index} failed (rc={completed.returncode})")
                print(
                    f"    out of memory on attempt {attempt + 1}; waiting {OOM_WAIT_S}s",
                    flush=True,
                )
                time.sleep(OOM_WAIT_S)
            parts.append(pickle.loads(result_path.read_bytes()))
            result_path.unlink()
    return _merge_batch_results(parts)


def pair_delta(
    initial: dict[str, np.ndarray], conditions: list[dict[str, Any]]
) -> float:
    """Return the maximum initial-state/observation delta across paired worlds."""
    lookup: dict[tuple[int, int], dict[int, int]] = {}
    for index, row in enumerate(conditions):
        lookup.setdefault((row["table_index"], row["replicate"]), {})[
            row["condition"]
        ] = index
    maximum = 0.0
    for pair in lookup.values():
        for value in initial.values():
            left = np.asarray(value[pair[0]])
            right = np.asarray(value[pair[1]])
            maximum = max(
                maximum,
                float(
                    np.max(np.abs(left.astype(np.float64) - right.astype(np.float64)))
                ),
            )
    return maximum


def cross_run_initial_delta(
    left: dict[str, np.ndarray], right: dict[str, np.ndarray]
) -> float:
    """Return maximum initial canonical delta across independent builds."""
    maximum = 0.0
    for name, value in left.items():
        maximum = max(maximum, recert.max_delta(value, right[name]))
    return maximum


def _run_condition_batch(
    *,
    checkpoint: Path,
    unit_table: Path,
    bank: Path,
    conditions: list[dict[str, Any]],
    device: str,
    axis: str,
    mujoco_contacts: bool = True,
) -> tuple[dict[str, Any], dict[str, np.ndarray], dict[str, Any]]:
    """Build and execute one vectorized batch of conditions."""
    env, wrapped, policy, command = build_env(
        checkpoint=checkpoint,
        unit_table=unit_table,
        bank=bank,
        num_envs=len(conditions),
        seed=IC_SEED,
        device=device,
    )
    try:
        observations, initial = prepare_worlds(
            env, wrapped, command, conditions, device=device
        )
        physics = build_physics(env, device, mujoco_contacts=mujoco_contacts)
        condition_one = torch.tensor(
            [row["condition"] == 1 for row in conditions],
            dtype=torch.bool,
            device=device,
        )
        effort_limits = None
        manipulation: dict[str, Any] = {
            "axis": axis,
            "mujoco_contacts": mujoco_contacts,
        }
        if axis == "delay_20ms":
            PairedDelay(physics, condition_one)
            manipulation["delayed_worlds"] = int(condition_one.sum())
            manipulation["delay_control_steps"] = 1
        elif axis == "motor_clamp_85pct":
            effort_limits = apply_motor_clamp(physics, condition_one)
            manipulation["clamped_worlds"] = int(condition_one.sum())
            manipulation["effort_limit_ratio"] = 0.85
        elif axis not in {"newton_contact", "preflight"}:
            raise ValueError(f"unknown axis {axis!r}")
        result = rollout(
            env,
            wrapped,
            policy,
            command,
            physics,
            observations,
            effort_limits=effort_limits,
        )
        return result, initial, manipulation
    finally:
        env.close()


def numeric_max_delta(left: dict[str, Any], right: dict[str, Any]) -> float:
    """Compare all deterministic numeric trajectory arrays."""
    keys = (
        "body_pos_err",
        "anchor_ori_err",
        "mechanical_work",
        "effort_saturation",
        "alive",
        "qpos",
        "qvel",
        "actions",
        "reference_index",
    )
    return max(recert.max_delta(left[key], right[key]) for key in keys)


def deterministic_preflight(
    *,
    checkpoint: Path,
    unit_table: Path,
    bank: Path,
    reference_rows: list[dict[str, Any]],
    device: str,
) -> dict[str, Any]:
    """Run two independent nominal rebuilds on all 42 replicate-zero states."""
    conditions = build_conditions(reference_rows, replicates=1, paired=False)
    runs = []
    initials = []
    for repeat in range(2):
        print(f"  deterministic nominal rebuild {repeat + 1}/2")
        result, initial, _ = run_condition_set(
            checkpoint=checkpoint,
            unit_table=unit_table,
            bank=bank,
            conditions=conditions,
            device=device,
            axis="preflight",
        )
        runs.append(result)
        initials.append(initial)
    contacts_equal = runs[0]["contacts"] == runs[1]["contacts"]
    return {
        "numeric_max_abs_delta": numeric_max_delta(runs[0], runs[1]),
        "initial_max_abs_delta": cross_run_initial_delta(initials[0], initials[1]),
        "contacts_equal": contacts_equal,
        "invalid_starts": sum(run["invalid_starts"] for run in runs),
        "invalid_reference_frames": sum(
            run["invalid_reference_frames"] for run in runs
        ),
        "escaped_reference_frames": sum(
            run["escaped_reference_frames"] for run in runs
        ),
    }


def split_paired(
    result: dict[str, Any], conditions: list[dict[str, Any]]
) -> tuple[dict[tuple[int, int], int], dict[tuple[int, int], int]]:
    """Return base and intervention indices keyed by unit and replicate."""
    base = {}
    perturbed = {}
    for index, row in enumerate(conditions):
        key = (int(row["table_index"]), int(row["replicate"]))
        (perturbed if int(row["condition"]) else base)[key] = index
    if set(base) != set(perturbed):
        raise ValueError("paired condition set is incomplete")
    return base, perturbed


def paired_effects(
    base_result: dict[str, Any],
    perturbed_result: dict[str, Any],
    base_indices: dict[tuple[int, int], int],
    perturbed_indices: dict[tuple[int, int], int],
) -> dict[int, dict[str, Any]]:
    """Compute N5 signed effects and diagnostics for every unit."""
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    output = {}
    units = sorted({unit for unit, _ in base_indices})
    if set(base_indices) != set(perturbed_indices):
        raise ValueError("base and perturbed effect indices differ")
    for unit in units:
        body_effect = []
        anchor_effect = []
        work_effect = []
        saturation_effect = []
        rmst_effect = []
        alive_points = 0
        clamp_realized = False
        for replicate in range(REPLICATES):
            key = (unit, replicate)
            base_index = base_indices[key]
            perturbed_index = perturbed_indices[key]
            base_alive = base_result["alive"][:, base_index].astype(bool)
            perturbed_alive = perturbed_result["alive"][:, perturbed_index].astype(bool)
            paired_alive = base_alive & perturbed_alive
            alive_points += int(paired_alive.sum())
            if not paired_alive.any():
                body_effect.append(float("nan"))
                anchor_effect.append(float("nan"))
                work_effect.append(float("nan"))
                saturation_effect.append(float("nan"))
            else:
                for values, name in (
                    (body_effect, "body_pos_err"),
                    (anchor_effect, "anchor_ori_err"),
                    (work_effect, "mechanical_work"),
                    (saturation_effect, "effort_saturation"),
                ):
                    delta = (
                        perturbed_result[name][:, perturbed_index]
                        - base_result[name][:, base_index]
                    )
                    values.append(float(np.mean(delta[paired_alive])))
            rmst_effect.append(float(perturbed_alive.sum() - base_alive.sum()) * 0.02)
            clamp_realized |= bool(
                np.any(perturbed_result["effort_saturation"][:, perturbed_index] > 0.0)
            )
        body = np.asarray(body_effect, dtype=np.float64)
        finite = np.isfinite(body)
        if not finite.all():
            ci = [float("nan"), float("nan")]
        else:
            boots = np.asarray(
                [rng.choice(body, len(body), replace=True).mean() for _ in range(2000)]
            )
            ci = [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]
        output[unit] = {
            "s_mm": float(np.mean(body) * 1000.0),
            "ci_low_mm": ci[0] * 1000.0,
            "ci_high_mm": ci[1] * 1000.0,
            "replicates": REPLICATES,
            "paired_alive_fraction": alive_points / (REPLICATES * PROBE_STEPS),
            "anchor_ori_s_rad": float(np.mean(anchor_effect)),
            "mechanical_work_s_j": float(np.mean(work_effect)),
            "effort_saturation_s": float(np.mean(saturation_effect)),
            "rmst_regret_s": float(np.mean(rmst_effect)),
            "clamp_realized": clamp_realized,
        }
    return output


def run_axis(
    *,
    checkpoint: Path,
    unit_table: Path,
    bank: Path,
    reference_rows: list[dict[str, Any]],
    device: str,
    axis: str,
) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    """Run one paired axis for one policy."""
    if axis in {"delay_20ms", "motor_clamp_85pct"}:
        conditions = build_conditions(
            reference_rows, replicates=REPLICATES, paired=True
        )
        result, initial, manipulation = run_condition_set(
            checkpoint=checkpoint,
            unit_table=unit_table,
            bank=bank,
            conditions=conditions,
            device=device,
            axis=axis,
        )
        base_indices, perturbed_indices = split_paired(result, conditions)
        effects = paired_effects(result, result, base_indices, perturbed_indices)
        checks = {
            **manipulation,
            "initial_pair_max_abs_delta": pair_delta(initial, conditions),
            "invalid_starts": result["invalid_starts"],
            "invalid_reference_frames": result["invalid_reference_frames"],
            "escaped_reference_frames": result["escaped_reference_frames"],
        }
        return effects, checks

    conditions = build_conditions(reference_rows, replicates=REPLICATES, paired=False)
    base_result, base_initial, base_manipulation = run_condition_set(
        checkpoint=checkpoint,
        unit_table=unit_table,
        bank=bank,
        conditions=conditions,
        device=device,
        axis=axis,
        mujoco_contacts=True,
    )
    perturbed_result, perturbed_initial, perturbed_manipulation = run_condition_set(
        checkpoint=checkpoint,
        unit_table=unit_table,
        bank=bank,
        conditions=conditions,
        device=device,
        axis=axis,
        mujoco_contacts=False,
    )
    indices = {
        (int(row["table_index"]), int(row["replicate"])): index
        for index, row in enumerate(conditions)
    }
    effects = paired_effects(base_result, perturbed_result, indices, indices)
    checks = {
        "axis": axis,
        "base_mujoco_contacts": base_manipulation["mujoco_contacts"],
        "perturbed_mujoco_contacts": perturbed_manipulation["mujoco_contacts"],
        "initial_pair_max_abs_delta": cross_run_initial_delta(
            base_initial, perturbed_initial
        ),
        "invalid_starts": base_result["invalid_starts"]
        + perturbed_result["invalid_starts"],
        "invalid_reference_frames": base_result["invalid_reference_frames"]
        + perturbed_result["invalid_reference_frames"],
        "escaped_reference_frames": base_result["escaped_reference_frames"]
        + perturbed_result["escaped_reference_frames"],
    }
    return effects, checks


def write_effects(
    path: Path,
    reference_rows: list[dict[str, Any]],
    measurements: dict[str, dict[str, dict[int, dict[str, Any]]]],
) -> None:
    """Write the exact 126-row analyzer input."""
    rows = []
    for reference in reference_rows:
        unit = int(reference["table_index"])
        for axis in AXES:
            row: dict[str, Any] = {
                "table_index": unit,
                "unit_id": int(reference["unit_id"]),
                "clip_id": int(reference["clip_id"]),
                "clip": reference["clip"],
                "axis": axis,
            }
            for policy in POLICIES:
                for name, value in measurements[policy][axis][unit].items():
                    row[f"{policy}_{name}"] = value
            rows.append(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def synthetic(out: Path) -> int:
    """Exercise the effect summarizer and manifest decision without simulation."""
    shape = (PROBE_STEPS, 2)
    base = {
        "body_pos_err": np.zeros(shape),
        "anchor_ori_err": np.zeros(shape),
        "mechanical_work": np.zeros(shape),
        "effort_saturation": np.zeros(shape),
        "alive": np.ones(shape, dtype=bool),
    }
    perturbed = {name: value.copy() for name, value in base.items()}
    perturbed["body_pos_err"][:, 1] = 0.01
    base_indices = {(0, replicate): 0 for replicate in range(REPLICATES)}
    perturbed_indices = {(0, replicate): 1 for replicate in range(REPLICATES)}
    effect = paired_effects(base, perturbed, base_indices, perturbed_indices)[0]
    passed = (
        abs(effect["s_mm"] - 10.0) < 1.0e-9
        and effect["replicates"] == 8
        and effect["paired_alive_fraction"] == 1.0
    )
    result = {
        "schema_version": "newton15_pred_probe_synthetic/1",
        "synthetic": True,
        "pass": passed,
        "effect": effect,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1) + "\n")
    print(f"Newton predictive probe synthetic: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


def main() -> int:
    """Run the synthetic check or the complete sealed no-training probe."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unit-table", type=Path)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--bank", type=Path)
    parser.add_argument("--development", type=Path)
    parser.add_argument("--adaptive", type=Path)
    parser.add_argument("--grounded", type=Path)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--batch-worlds", type=int, default=BATCH_WORLDS)
    parser.add_argument("--worker-batch", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker_batch is not None:
        return _worker_batch(args.worker_batch)
    if args.out_dir is None:
        parser.error("--out-dir is required")
    if args.synthetic:
        return synthetic(args.out_dir / "SYNTHETIC_PROBE.json")
    for name in (
        "unit_table",
        "reference",
        "bank",
        "development",
        "adaptive",
        "grounded",
    ):
        if getattr(args, name) is None:
            parser.error(f"--{name.replace('_', '-')} is required without --synthetic")

    globals()["BATCH_WORLDS"] = int(args.batch_worlds)
    configure_determinism()
    reference_rows = load_reference_rows(args.reference)
    checkpoints = {policy: getattr(args, policy) for policy in POLICIES}
    preflight = {}
    measurements: dict[str, dict[str, dict[int, dict[str, Any]]]] = {}
    manipulation: dict[str, dict[str, Any]] = {}
    # Completed stages are cached under the probe's own SHA so a late harness or
    # GPU failure does not discard a day of finished, hash-bound stages. A
    # changed probe file never reuses a cache.
    import pickle

    cache_dir = args.out_dir / "cache" / sha256_file(Path(__file__).resolve())[:16]
    cache_dir.mkdir(parents=True, exist_ok=True)

    def cached(name: str, compute: Any) -> Any:
        path = cache_dir / f"{name}.pkl"
        if path.exists():
            print(f"    cached stage {name}", flush=True)
            return pickle.loads(path.read_bytes())
        value = compute()
        path.write_bytes(pickle.dumps(value))
        return value

    for policy, checkpoint in checkpoints.items():
        print(f"[{policy}] deterministic preflight")
        preflight[policy] = cached(
            f"{policy}_preflight",
            lambda: deterministic_preflight(
                checkpoint=checkpoint,
                unit_table=args.unit_table,
                bank=args.bank,
                reference_rows=reference_rows,
                device=args.device,
            ),
        )
        measurements[policy] = {}
        manipulation[policy] = {}
        for axis in AXES:
            print(f"[{policy}] {axis}")
            effects, checks = cached(
                f"{policy}_{axis}",
                lambda: run_axis(
                    checkpoint=checkpoint,
                    unit_table=args.unit_table,
                    bank=args.bank,
                    reference_rows=reference_rows,
                    device=args.device,
                    axis=axis,
                ),
            )
            measurements[policy][axis] = effects
            manipulation[policy][axis] = checks

    effects_path = args.out_dir / "effects.csv"
    write_effects(effects_path, reference_rows, measurements)
    deterministic_delta = max(
        max(row["numeric_max_abs_delta"], row["initial_max_abs_delta"])
        for row in preflight.values()
    )
    initial_delta = max(
        row["initial_pair_max_abs_delta"]
        for policy in manipulation.values()
        for row in policy.values()
    )
    invalid_starts = sum(row["invalid_starts"] for row in preflight.values()) + sum(
        row["invalid_starts"]
        for policy in manipulation.values()
        for row in policy.values()
    )
    invalid_reference_frames = sum(
        row["invalid_reference_frames"] for row in preflight.values()
    ) + sum(
        row["invalid_reference_frames"]
        for policy in manipulation.values()
        for row in policy.values()
    )
    escaped_reference_frames = sum(
        row["escaped_reference_frames"] for row in preflight.values()
    ) + sum(
        row["escaped_reference_frames"]
        for policy in manipulation.values()
        for row in policy.values()
    )
    contacts_equal = all(row["contacts_equal"] for row in preflight.values())
    clamped_units = {
        policy: sum(
            bool(measurements[policy]["motor_clamp_85pct"][unit]["clamp_realized"])
            for unit in range(42)
        )
        for policy in POLICIES
    }
    motor_manipulation = min(clamped_units.values()) >= 12
    paired_alive = min(
        row["paired_alive_fraction"]
        for policy in measurements.values()
        for axis in policy.values()
        for row in axis.values()
    )
    pass_preflight = bool(
        deterministic_delta == 0.0
        and contacts_equal
        and initial_delta == 0.0
        and invalid_starts == 0
        and invalid_reference_frames == 0
        and escaped_reference_frames == 0
        and motor_manipulation
        and paired_alive >= 0.80
    )
    manifest = {
        "schema_version": "newton15_pred_probe/1",
        "classification": "sealed-protocol no-training Newton probe",
        "pass_preflight": pass_preflight,
        "deterministic_repeat_max_abs_delta": deterministic_delta,
        "deterministic_contacts_equal": contacts_equal,
        "invalid_starts": invalid_starts,
        "invalid_reference_frames": invalid_reference_frames,
        "escaped_reference_frames": escaped_reference_frames,
        "cross_condition_initial_state_max_abs_delta": initial_delta,
        "motor_clamp_units_realized_by_policy": clamped_units,
        "motor_clamp_manipulation_pass": motor_manipulation,
        "minimum_paired_alive_fraction": paired_alive,
        "unit_table_sha256": sha256_file(args.unit_table),
        "reference_sha256": sha256_file(args.reference),
        "checkpoint_sha256": {
            policy: sha256_file(path) for policy, path in checkpoints.items()
        },
        "probe_tool_sha256": sha256_file(Path(__file__)),
        "batch_worlds": BATCH_WORLDS,
        "effects_csv": str(effects_path.resolve()),
        "effects_csv_sha256": sha256_file(effects_path),
        "preflight": preflight,
        "manipulation": manipulation,
    }
    manifest_path = args.out_dir / "probe_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=1) + "\n")
    sentinel = {
        "schema_version": "newton15_pred_probe_completed/1",
        "pass_preflight": pass_preflight,
        "probe_manifest": str(manifest_path.resolve()),
        "probe_manifest_sha256": sha256_file(manifest_path),
        "effects_csv_sha256": manifest["effects_csv_sha256"],
    }
    (args.out_dir / "COMPLETED.json").write_text(json.dumps(sentinel, indent=1) + "\n")
    print(f"probe {'PASS' if pass_preflight else 'NOT TESTED'} -> {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
