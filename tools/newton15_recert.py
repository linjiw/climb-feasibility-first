#!/usr/bin/env python3
"""Recertify Newton 1.5 against mjlab on two exact DFRP v1 units.

The six checks are placement, first observation, first action, state evolution,
contact/termination timing, and deterministic repeatability. This script does
not measure the later Newton predictive feature gate and does not train.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


QPOS_TOL = 1.0e-5
QVEL_TOL = 3.0e-5
OBS_TOL = 1.0e-6
ACTION_TOL = 1.0e-6
PLACEMENT_TOL = 1.0e-7


def sha256_file(path: Path) -> str:
    """Return a file's SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_array(value: np.ndarray) -> str:
    """Hash an array with shape and dtype binding."""
    digest = hashlib.sha256()
    digest.update(str(value.dtype).encode())
    digest.update(str(value.shape).encode())
    digest.update(np.ascontiguousarray(value).tobytes())
    return digest.hexdigest()


def flatten_observation(value: Any) -> torch.Tensor:
    """Flatten tensor or nested-dict observations in stable key order."""
    if isinstance(value, torch.Tensor):
        return value.reshape(value.shape[0], -1)
    if isinstance(value, dict) or (
        hasattr(value, "keys") and hasattr(value, "__getitem__")
    ):
        keys = sorted(value.keys(), key=str)
        return torch.cat(
            [flatten_observation(value[key]) for key in keys], dim=1
        )
    raise TypeError(f"unsupported observation type: {type(value)!r}")


def normalize_geom_name(name: str | None, geom_id: int) -> str:
    """Normalize replicated/imported geom names for cross-stack comparison."""
    if not name:
        return f"geom_{geom_id}"
    short_name = re.sub(r"_\d+$", "", name.rsplit("/", 1)[-1])
    if short_name in {"terrain", "ground_plane"}:
        return "ground"
    return short_name


def contact_snapshot(
    data: Any, model: Any, num_envs: int
) -> tuple[
    tuple[tuple[tuple[str, str], ...], ...],
    tuple[tuple[dict[str, Any], ...], ...],
]:
    """Return contact-pair signatures and raw active records per world."""
    import mujoco
    import warp as wp

    nacon = int(wp.to_torch(data.nacon)[0])
    contacts: list[list[tuple[str, str]]] = [[] for _ in range(num_envs)]
    records: list[list[dict[str, Any]]] = [[] for _ in range(num_envs)]
    if nacon == 0:
        empty = tuple(() for _ in range(num_envs))
        return empty, empty
    geoms = wp.to_torch(data.contact.geom)[:nacon].detach().cpu().numpy()
    worlds = wp.to_torch(data.contact.worldid)[:nacon].detach().cpu().numpy()
    distances = wp.to_torch(data.contact.dist)[:nacon].detach().cpu().numpy()
    for pair, world, distance in zip(geoms, worlds, distances, strict=True):
        if float(distance) > 0.0:
            continue
        names = []
        for geom in pair:
            geom_id = int(geom)
            name = mujoco.mj_id2name(
                model, mujoco.mjtObj.mjOBJ_GEOM, geom_id
            )
            names.append(normalize_geom_name(name, geom_id))
        pair_names = tuple(sorted(names))
        world_index = int(world)
        contacts[world_index].append(pair_names)
        records[world_index].append(
            {
                "pair": pair_names,
                "geom_ids": tuple(int(value) for value in pair),
                "distance": float(distance),
            }
        )
    signature = tuple(tuple(sorted(set(values))) for values in contacts)
    details = tuple(
        tuple(sorted(values, key=lambda row: (row["pair"], row["distance"])))
        for values in records
    )
    return signature, details


def configure_sensor_module_nondeterministic() -> None:
    """Keep MJWarp sensors usable under deterministic physics reductions.

    Warp 1.16 cannot compile the shared sensor module in deterministic mode
    because its tactile kernel mixes max and add reductions into one array.
    Those sensor reductions do not feed physics state. Pin only that module to
    the ordinary path while keeping the dynamics/contact modules run-to-run
    deterministic.
    """
    import warp as wp
    from mujoco_warp._src import sensor as mjw_sensor

    wp.set_module_options(
        {
            "deterministic": wp.DeterministicMode.NOT_GUARANTEED,
            "deterministic_max_records": 0,
        },
        module=mjw_sensor,
    )


def live_model_diff(physics: Any) -> dict[str, Any]:
    """Compare mapped live MJWarp model fields after all S1 mirrors."""
    import warp as wp

    source = physics.env.sim.wp_model
    target = physics.solver.mjw_model
    source_model = physics.env.sim.mj_model
    target_model = physics.solver.mj_model
    maps = physics._entity_maps()
    # Newton replaces mjlab's named terrain geom with its own ground plane.
    maps["ngeom"][0] = 0
    axes = {
        "nbody": (source_model.nbody, target_model.nbody),
        "ngeom": (source_model.ngeom, target_model.ngeom),
        "njnt": (source_model.njnt, target_model.njnt),
        "nv": (source_model.nv, target_model.nv),
        "nu": (source_model.nu, target_model.nu),
    }
    fields = {
        "nbody": (
            "body_pos",
            "body_quat",
            "body_ipos",
            "body_iquat",
            "body_mass",
            "body_inertia",
        ),
        "ngeom": (
            "geom_pos",
            "geom_quat",
            "geom_size",
            "geom_friction",
            "geom_solref",
            "geom_solimp",
            "geom_margin",
            "geom_gap",
            "geom_condim",
            "geom_contype",
            "geom_conaffinity",
            "geom_priority",
            "geom_solmix",
            "geom_type",
        ),
        "njnt": (
            "jnt_pos",
            "jnt_axis",
            "jnt_range",
            "jnt_margin",
            "jnt_solref",
            "jnt_solimp",
            "jnt_stiffness",
            "jnt_type",
            "jnt_limited",
        ),
        "nv": (
            "dof_armature",
            "dof_damping",
            "dof_frictionloss",
            "dof_solref",
            "dof_solimp",
        ),
        "nu": (
            "actuator_gainprm",
            "actuator_biasprm",
            "actuator_dynprm",
            "actuator_forcerange",
            "actuator_ctrlrange",
            "actuator_gaintype",
            "actuator_biastype",
            "actuator_dyntype",
            "actuator_ctrllimited",
            "actuator_forcelimited",
        ),
    }

    def canonical(
        array: torch.Tensor, entity_count: int, ids: torch.Tensor
    ) -> torch.Tensor:
        if (
            array.ndim >= 2
            and array.shape[0] in (1, physics.n_env)
            and array.shape[1] == entity_count
        ):
            value = array[:, ids]
            if value.shape[0] == 1:
                value = value.expand(physics.n_env, *value.shape[1:])
            return value
        if array.ndim >= 1 and array.shape[0] == entity_count:
            value = array[ids]
            return value.unsqueeze(0).expand(physics.n_env, *value.shape)
        raise ValueError(f"unrecognized entity layout {tuple(array.shape)}")

    rows: dict[str, Any] = {}
    for axis, axis_fields in fields.items():
        mapping = maps[axis]
        source_count, target_count = axes[axis]
        source_ids = torch.tensor(sorted(mapping), device=physics.wp_device)
        target_ids = torch.tensor(
            [mapping[int(index)] for index in source_ids.tolist()],
            device=physics.wp_device,
        )
        for field in axis_fields:
            if not hasattr(source, field) or not hasattr(target, field):
                continue
            try:
                left = canonical(
                    wp.to_torch(getattr(source, field)), source_count, source_ids
                )
                right = canonical(
                    wp.to_torch(getattr(target, field)), target_count, target_ids
                )
            except (TypeError, ValueError):
                continue
            if left.shape != right.shape:
                rows[field] = {
                    "axis": axis,
                    "shape_equal": False,
                    "source_shape": tuple(left.shape),
                    "target_shape": tuple(right.shape),
                }
                continue
            left_cpu = left.detach().cpu()
            right_cpu = right.detach().cpu()
            exact = bool(torch.equal(left_cpu, right_cpu))
            if left_cpu.dtype.is_floating_point:
                max_abs = float(
                    (left_cpu.to(torch.float64) - right_cpu.to(torch.float64))
                    .abs()
                    .max()
                )
            else:
                max_abs = 0.0 if exact else None
            rows[field] = {
                "axis": axis,
                "shape_equal": True,
                "exact": exact,
                "max_abs_delta": max_abs,
            }
    mismatches = {
        name: row
        for name, row in rows.items()
        if not row.get("shape_equal", False) or not row.get("exact", False)
    }
    return {
        "mapped_counts": {axis: len(mapping) for axis, mapping in maps.items()},
        "fields_checked": len(rows),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }


def mirror_newton15_live_fields(physics: Any) -> list[str]:
    """Mirror Newton-1.5 import residuals from mjlab's live MJWarp model."""
    import mujoco_warp as mjw
    import warp as wp

    source = physics.env.sim.wp_model
    target = physics.solver.mjw_model
    source_model = physics.env.sim.mj_model
    target_model = physics.solver.mj_model
    maps = physics._entity_maps()
    maps["ngeom"][0] = 0
    axes = {
        "ngeom": (source_model.ngeom, target_model.ngeom),
        "njnt": (source_model.njnt, target_model.njnt),
        "nu": (source_model.nu, target_model.nu),
    }
    fields = {
        "ngeom": ("geom_size", "geom_contype", "geom_conaffinity"),
        "njnt": ("jnt_range",),
        "nu": (
            "actuator_gainprm",
            "actuator_biasprm",
            "actuator_ctrlrange",
        ),
    }
    mirrored = []
    for axis, axis_fields in fields.items():
        mapping = maps[axis]
        source_count, target_count = axes[axis]
        source_ids = torch.tensor(sorted(mapping), device=physics.wp_device)
        target_ids = torch.tensor(
            [mapping[int(index)] for index in source_ids.tolist()],
            device=physics.wp_device,
        )
        for field in axis_fields:
            left = wp.to_torch(getattr(source, field))
            right = wp.to_torch(getattr(target, field))
            left_world = (
                left.ndim >= 2
                and left.shape[0] in (1, physics.n_env)
                and left.shape[1] == source_count
            )
            right_world = (
                right.ndim >= 2
                and right.shape[0] in (1, physics.n_env)
                and right.shape[1] == target_count
            )
            if left_world and right_world:
                source_values = left[:, source_ids]
                if source_values.shape[0] == 1 and right.shape[0] > 1:
                    source_values = source_values.expand(
                        right.shape[0], *source_values.shape[1:]
                    )
                right[:, target_ids] = source_values.to(right.dtype)
            elif not left_world and not right_world:
                right[target_ids] = left[source_ids].to(right.dtype)
            else:
                raise ValueError(
                    f"mixed world layout for {field}: "
                    f"{tuple(left.shape)} vs {tuple(right.shape)}"
                )
            mirrored.append(field)
    with wp.ScopedDevice(physics.wp_device):
        mjw.set_const(target, physics.solver.mjw_data)
    return mirrored


def build_env(
    *,
    checkpoint: Path,
    table_path: Path,
    bank: Path,
    selection: dict[str, Any],
    seed: int,
    device: str,
) -> tuple[Any, Any, Any, Any]:
    """Build the exact segment environment and load one frozen policy."""
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
    table = json.loads(table_path.read_text())
    motion_files = [str((bank / f"{row['clip']}.npz").resolve()) for row in table["sources"]]
    cfg = segment_native_g1_tracking_env_cfg(
        motion_files=motion_files,
        segment_manifest=str(table_path.resolve()),
        segment_sampling_mode="uniform",
        sampler_seed=seed,
        env_seed=seed,
        failure_penalty=0.0,
    )
    cfg.scene.num_envs = 2
    cfg.auto_reset = False
    cfg.events.pop("push_robot", None)
    for group in cfg.observations.values():
        group.enable_corruption = False

    agent_cfg = unitree_g1_tracking_ppo_runner_cfg()
    env = ManagerBasedRlEnv(cfg=cfg, device=device)
    wrapped = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)
    runner = MotionTrackingOnPolicyRunner(
        wrapped, asdict(agent_cfg), device=device
    )
    runner.load(
        str(checkpoint.resolve()),
        load_cfg={"actor": True},
        strict=True,
        map_location=device,
    )
    policy = runner.get_inference_policy(device=device)
    command = env.command_manager.get_term("motion")
    if not isinstance(command, SegmentNativeMotionCommand):
        raise TypeError("recertification command is not segment-native")

    entries = [selection["easy"], selection["contact_rich"]]
    table_indices = torch.tensor(
        [row["table_index"] for row in entries],
        dtype=torch.long,
        device=device,
    )
    starts = torch.tensor(
        [row["start_frame"] for row in entries],
        dtype=torch.long,
        device=device,
    )
    command.assign_segments(table_indices, starts)
    # A teleport changes qpos/qvel without defining a compatible constraint
    # warm start. Clear the constructor/reset residue so both solvers begin the
    # exact unit from the same canonical state.
    env.sim.data.qacc_warmstart.zero_()
    # assign_segments() teleports the robot and replaces the command after the
    # constructor's reset observation has already been cached. Treat this as a
    # fresh placement: clear observation-side state, backfill the exact first
    # frame, and bind env.obs_buf before the policy sees it. This is the G0
    # "stale first observation" integration check.
    env_ids = torch.arange(env.num_envs, device=device)
    env.observation_manager.reset(env_ids)
    env.obs_buf = env.observation_manager.compute(
        update_history=True, env_ids=env_ids
    )
    observations = wrapped.get_observations()
    return env, wrapped, policy, observations


def run_arm(
    arm: str,
    *,
    checkpoint: Path,
    table_path: Path,
    bank: Path,
    selection: dict[str, Any],
    seed: int,
    device: str,
    probe_steps: int,
    forced_actions: np.ndarray | None = None,
    shadow_reference: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run one stock or Newton arm from the same exact-unit contract.

    The stock arm records the canonical frozen-policy action stream. Newton
    replays that stream after its independently computed first action has been
    checked, isolating physics conformance from closed-loop amplification.
    """
    import s1_newton_conformance as s1

    env, wrapped, policy, observations = build_env(
        checkpoint=checkpoint,
        table_path=table_path,
        bank=bank,
        selection=selection,
        seed=seed,
        device=device,
    )
    physics = None
    model_diff = None
    try:
        initial_observation = flatten_observation(observations).detach().cpu().numpy()
        with torch.inference_mode():
            first_action = policy(observations)
        qpos = [env.sim.data.qpos.detach().cpu().numpy().copy()]
        qvel = [env.sim.data.qvel.detach().cpu().numpy().copy()]
        actions: list[np.ndarray] = []
        terminated: list[np.ndarray] = []
        contacts: list[tuple[tuple[tuple[str, str], ...], ...]] = []
        contact_details: list[tuple[tuple[dict[str, Any], ...], ...]] = []
        substep_pre_qpos: list[np.ndarray] = []
        substep_pre_qvel: list[np.ndarray] = []
        substep_pre_warmstart: list[np.ndarray] = []
        substep_ctrl: list[np.ndarray] = []
        conformance_qpos: list[np.ndarray] = []
        conformance_qvel: list[np.ndarray] = []
        conformance_contacts: list[
            tuple[tuple[tuple[str, str], ...], ...]
        ] = []
        conformance_contact_details: list[
            tuple[tuple[dict[str, Any], ...], ...]
        ] = []

        if arm == "newton":
            physics = s1.NewtonPhysics(env, "mjw", device)
            # SolverMuJoCo applies deterministic options to all loaded MJWarp
            # modules. Restore the sensor-only exception before mjlab computes
            # policy observations from the synchronized state.
            configure_sensor_module_nondeterministic()
            before_mirror = live_model_diff(physics)
            mirrored_fields = mirror_newton15_live_fields(physics)
            model_diff = {
                "before_mirror": before_mirror,
                "mirrored_fields": mirrored_fields,
                "after_mirror": live_model_diff(physics),
            }
            physics.sync_from_mjlab()
            contact_data = physics.solver.mjw_data
            contact_model = physics.solver.mj_model

            if shadow_reference is None:
                raise ValueError("Newton arm requires a stock canonical shadow reference")
            initial_state = {
                "qpos": env.sim.data.qpos.clone(),
                "qvel": env.sim.data.qvel.clone(),
                "warmstart": env.sim.data.qacc_warmstart.clone(),
                "ctrl": env.sim.data.ctrl.clone(),
            }
            import warp as wp

            solver_warmstart = wp.to_torch(
                physics.solver.mjw_data.qacc_warmstart
            )
            for q_in, qd_in, warmstart_in, ctrl_in in zip(
                shadow_reference["substep_pre_qpos"],
                shadow_reference["substep_pre_qvel"],
                shadow_reference["substep_pre_warmstart"],
                shadow_reference["substep_ctrl"],
                strict=True,
            ):
                env.sim.data.qpos.copy_(torch.as_tensor(q_in, device=device))
                env.sim.data.qvel.copy_(torch.as_tensor(qd_in, device=device))
                env.sim.data.qacc_warmstart.copy_(
                    torch.as_tensor(warmstart_in, device=device)
                )
                env.sim.data.ctrl.copy_(torch.as_tensor(ctrl_in, device=device))
                env.sim.forward()
                physics.sync_from_mjlab()
                solver_warmstart.copy_(
                    torch.as_tensor(warmstart_in, device=device)
                )
                physics.substep_from_ctrl()
                conformance_qpos.append(
                    env.sim.data.qpos.detach().cpu().numpy().copy()
                )
                conformance_qvel.append(
                    env.sim.data.qvel.detach().cpu().numpy().copy()
                )
                shadow_signature, shadow_details = contact_snapshot(
                    physics.solver.mjw_data,
                    physics.solver.mj_model,
                    env.num_envs,
                )
                conformance_contacts.append(shadow_signature)
                conformance_contact_details.append(shadow_details)

            env.sim.data.qpos.copy_(initial_state["qpos"])
            env.sim.data.qvel.copy_(initial_state["qvel"])
            env.sim.data.qacc_warmstart.copy_(initial_state["warmstart"])
            env.sim.data.ctrl.copy_(initial_state["ctrl"])
            env.sim.forward()
            physics.sync_from_mjlab()
            solver_warmstart.copy_(initial_state["warmstart"])
        elif arm == "stock":
            contact_data = env.sim.wp_data
            contact_model = env.sim.mj_model
        else:
            raise ValueError(f"unknown arm {arm!r}")
        action = first_action
        with torch.inference_mode():
            for step in range(probe_steps):
                if forced_actions is not None:
                    action = torch.as_tensor(
                        forced_actions[step], device=device, dtype=first_action.dtype
                    )
                actions.append(action.detach().cpu().numpy().copy())
                if physics is None:
                    real_step = env.sim.step

                    def captured_step() -> None:
                        substep_pre_qpos.append(
                            env.sim.data.qpos.detach().cpu().numpy().copy()
                        )
                        substep_pre_qvel.append(
                            env.sim.data.qvel.detach().cpu().numpy().copy()
                        )
                        substep_pre_warmstart.append(
                            env.sim.data.qacc_warmstart.detach().cpu().numpy().copy()
                        )
                        substep_ctrl.append(
                            env.sim.data.ctrl.detach().cpu().numpy().copy()
                        )
                        real_step()
                        conformance_qpos.append(
                            env.sim.data.qpos.detach().cpu().numpy().copy()
                        )
                        conformance_qvel.append(
                            env.sim.data.qvel.detach().cpu().numpy().copy()
                        )
                        stock_signature, stock_details = contact_snapshot(
                            env.sim.wp_data, env.sim.mj_model, env.num_envs
                        )
                        conformance_contacts.append(stock_signature)
                        conformance_contact_details.append(stock_details)

                    env.sim.step = captured_step
                    try:
                        observations, _, dones, _ = wrapped.step(action)
                    finally:
                        env.sim.step = real_step
                    contact_data = env.sim.wp_data
                    contact_model = env.sim.mj_model
                else:
                    observations, _, dones, _ = s1._step_with_external_physics(
                        env, wrapped, action, physics
                    )
                    # Newton's solver contact buffer still describes the
                    # pre-integration state of its last substep. The coupling
                    # has already written qpos/qvel back and run mjlab forward,
                    # so use mjlab's post-step observer on both arms to compare
                    # contact timing at the same state phase.
                    contact_data = env.sim.wp_data
                    contact_model = env.sim.mj_model
                qpos.append(env.sim.data.qpos.detach().cpu().numpy().copy())
                qvel.append(env.sim.data.qvel.detach().cpu().numpy().copy())
                terminated.append(
                    env.termination_manager.terminated.detach().cpu().numpy().copy()
                )
                signature, details = contact_snapshot(
                    contact_data, contact_model, env.num_envs
                )
                contacts.append(signature)
                contact_details.append(details)
                if bool(dones.any()):
                    break
                if forced_actions is None:
                    action = policy(observations)

        return {
            "initial_observation": initial_observation,
            "first_action": first_action.detach().cpu().numpy(),
            "qpos": np.stack(qpos),
            "qvel": np.stack(qvel),
            "actions": np.stack(actions),
            "terminated": np.stack(terminated),
            "contacts": contacts,
            "contact_details": contact_details,
            "substep_pre_qpos": (
                np.stack(substep_pre_qpos)
                if substep_pre_qpos
                else np.asarray(shadow_reference["substep_pre_qpos"]).copy()
            ),
            "substep_pre_qvel": (
                np.stack(substep_pre_qvel)
                if substep_pre_qvel
                else np.asarray(shadow_reference["substep_pre_qvel"]).copy()
            ),
            "substep_pre_warmstart": (
                np.stack(substep_pre_warmstart)
                if substep_pre_warmstart
                else np.asarray(shadow_reference["substep_pre_warmstart"]).copy()
            ),
            "substep_ctrl": (
                np.stack(substep_ctrl)
                if substep_ctrl
                else np.asarray(shadow_reference["substep_ctrl"]).copy()
            ),
            "conformance_qpos": np.stack(conformance_qpos),
            "conformance_qvel": np.stack(conformance_qvel),
            "conformance_contacts": conformance_contacts,
            "conformance_contact_details": conformance_contact_details,
            "live_model_diff": model_diff,
            "absorbed_state_writes": (
                physics.absorbed_writes if physics is not None else None
            ),
        }
    finally:
        env.close()


def max_delta(left: np.ndarray, right: np.ndarray) -> float:
    """Return max absolute delta, rejecting shape disagreement."""
    if left.shape != right.shape:
        return float("inf")
    return float(np.max(np.abs(left.astype(np.float64) - right.astype(np.float64))))


def first_contact_mismatch(
    left: list[tuple[tuple[tuple[str, str], ...], ...]],
    right: list[tuple[tuple[tuple[str, str], ...], ...]],
) -> dict[str, Any] | None:
    """Describe the first contact-signature mismatch, if one exists."""
    for step, (left_frame, right_frame) in enumerate(
        zip(left, right, strict=False), start=1
    ):
        for unit, (left_pairs, right_pairs) in enumerate(
            zip(left_frame, right_frame, strict=False)
        ):
            if left_pairs != right_pairs:
                return {
                    "step": step,
                    "unit_index": unit,
                    "left": left_pairs,
                    "right": right_pairs,
                }
        if len(left_frame) != len(right_frame):
            return {
                "step": step,
                "unit_index": min(len(left_frame), len(right_frame)),
                "left": left_frame,
                "right": right_frame,
            }
    if len(left) != len(right):
        return {
            "step": min(len(left), len(right)) + 1,
            "unit_index": None,
            "left": "missing" if len(left) < len(right) else left[-1],
            "right": "missing" if len(right) < len(left) else right[-1],
        }
    return None


def compare_runs(stock: dict[str, Any], newton: dict[str, Any]) -> dict[str, Any]:
    """Apply the six recertification checks to two arm records."""
    placement_qpos = max_delta(stock["qpos"][0], newton["qpos"][0])
    placement_qvel = max_delta(stock["qvel"][0], newton["qvel"][0])
    observation = max_delta(
        stock["initial_observation"], newton["initial_observation"]
    )
    first_action = max_delta(stock["first_action"], newton["first_action"])
    qpos = max_delta(stock["conformance_qpos"], newton["conformance_qpos"])
    qvel = max_delta(stock["conformance_qvel"], newton["conformance_qvel"])
    closed_loop_qpos = max_delta(stock["qpos"], newton["qpos"])
    closed_loop_qvel = max_delta(stock["qvel"], newton["qvel"])
    contact_mismatch = first_contact_mismatch(
        stock["contacts"], newton["contacts"]
    )
    if contact_mismatch is not None and contact_mismatch["unit_index"] is not None:
        step_index = int(contact_mismatch["step"]) - 1
        unit_index = int(contact_mismatch["unit_index"])
        contact_mismatch["left_records"] = stock["contact_details"][step_index][
            unit_index
        ]
        contact_mismatch["right_records"] = newton["contact_details"][step_index][
            unit_index
        ]
    contact_equal = contact_mismatch is None
    conformance_contact_mismatch = first_contact_mismatch(
        stock["conformance_contacts"], newton["conformance_contacts"]
    )
    if (
        conformance_contact_mismatch is not None
        and conformance_contact_mismatch["unit_index"] is not None
    ):
        step_index = int(conformance_contact_mismatch["step"]) - 1
        unit_index = int(conformance_contact_mismatch["unit_index"])
        conformance_contact_mismatch["left_records"] = stock[
            "conformance_contact_details"
        ][step_index][unit_index]
        conformance_contact_mismatch["right_records"] = newton[
            "conformance_contact_details"
        ][step_index][unit_index]
    conformance_contact_equal = conformance_contact_mismatch is None
    termination_equal = bool(
        np.array_equal(stock["terminated"], newton["terminated"])
    )
    return {
        "placement": {
            "max_abs_qpos": placement_qpos,
            "max_abs_qvel": placement_qvel,
            "threshold": PLACEMENT_TOL,
            "pass": placement_qpos <= PLACEMENT_TOL
            and placement_qvel <= PLACEMENT_TOL,
        },
        "first_observation": {
            "max_abs_delta": observation,
            "threshold": OBS_TOL,
            "pass": observation <= OBS_TOL,
        },
        "first_action": {
            "max_abs_delta": first_action,
            "threshold": ACTION_TOL,
            "pass": first_action <= ACTION_TOL,
        },
        "state_evolution": {
            "protocol": "per-substep resynchronization from stock canonical state, warm start, and control",
            "max_abs_qpos": qpos,
            "qpos_threshold": QPOS_TOL,
            "max_abs_qvel": qvel,
            "qvel_threshold": QVEL_TOL,
            "closed_loop_diagnostic_max_abs_qpos": closed_loop_qpos,
            "closed_loop_diagnostic_max_abs_qvel": closed_loop_qvel,
            "pass": qpos <= QPOS_TOL and qvel <= QVEL_TOL,
        },
        "contact_and_termination_timing": {
            "post_control_observer_contact_equal": contact_equal,
            "first_post_control_contact_mismatch": contact_mismatch,
            "solver_substep_contact_equal": conformance_contact_equal,
            "first_solver_substep_contact_mismatch": conformance_contact_mismatch,
            "termination_equal": termination_equal,
            "pass": contact_equal
            and conformance_contact_equal
            and termination_equal,
        },
    }


def compare_repeated_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Require exact trajectories across independent same-seed rebuilds."""
    reference = runs[0]
    deltas: dict[str, float] = {}
    for key in (
        "initial_observation",
        "first_action",
        "qpos",
        "qvel",
        "actions",
        "conformance_qpos",
        "conformance_qvel",
    ):
        deltas[key] = max(
            max_delta(reference[key], repeat[key]) for repeat in runs[1:]
        )
    contact_mismatches = [
        first_contact_mismatch(reference["contacts"], repeat["contacts"])
        for repeat in runs[1:]
    ]
    contacts_equal = all(row is None for row in contact_mismatches)
    conformance_contact_mismatches = [
        first_contact_mismatch(
            reference["conformance_contacts"], repeat["conformance_contacts"]
        )
        for repeat in runs[1:]
    ]
    conformance_contacts_equal = all(
        row is None for row in conformance_contact_mismatches
    )
    terminations_equal = all(
        np.array_equal(reference["terminated"], repeat["terminated"])
        for repeat in runs[1:]
    )
    passed = (
        all(value == 0.0 for value in deltas.values())
        and contacts_equal
        and conformance_contacts_equal
        and terminations_equal
    )
    return {
        "max_abs_deltas": deltas,
        "contact_equal": contacts_equal,
        "first_contact_mismatches": contact_mismatches,
        "conformance_contact_equal": conformance_contacts_equal,
        "first_conformance_contact_mismatches": conformance_contact_mismatches,
        "termination_equal": terminations_equal,
        "pass": passed,
    }


def synthetic_result() -> dict[str, Any]:
    """Exercise both comparator branches without simulator outcomes."""
    base = {
        "initial_observation": np.zeros((4, 4), dtype=np.float32),
        "first_action": np.zeros((4, 3), dtype=np.float32),
        "qpos": np.zeros((3, 4, 5), dtype=np.float32),
        "qvel": np.zeros((3, 4, 4), dtype=np.float32),
        "actions": np.zeros((2, 4, 3), dtype=np.float32),
        "terminated": np.zeros((2, 4), dtype=bool),
        "contacts": [((), (), (), ()), ((), (), (), ()), ((), (), (), ())],
        "conformance_contacts": [((), (), (), ()), ((), (), (), ())],
        "conformance_qpos": np.zeros((2, 4, 5), dtype=np.float32),
        "conformance_qvel": np.zeros((2, 4, 4), dtype=np.float32),
    }
    passing = compare_runs(base, base)
    perturbed = {
        **base,
        "qvel": base["qvel"].copy(),
        "conformance_qvel": base["conformance_qvel"].copy(),
    }
    perturbed["qvel"][1, 0, 0] = 2.0 * QVEL_TOL
    perturbed["conformance_qvel"][1, 0, 0] = 2.0 * QVEL_TOL
    failing = compare_runs(base, perturbed)
    repeats = compare_repeated_runs([base, base])
    ok = (
        all(row["pass"] for row in passing.values())
        and not failing["state_evolution"]["pass"]
        and repeats["pass"]
    )
    return {
        "synthetic": True,
        "pass": ok,
        "passing_case": passing,
        "failing_case": failing,
        "repeat_case": repeats,
    }


def main() -> int:
    """Run the synthetic dry-run or the two-unit recertification."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--unit-table", type=Path)
    parser.add_argument("--bank", type=Path)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260826)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--probe-steps", type=int, default=12)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--deterministic-max-records", type=int, default=630)
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()

    if args.synthetic:
        result = synthetic_result()
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=1) + "\n")
        print(f"synthetic comparator: {'PASS' if result['pass'] else 'FAIL'}")
        return 0 if result["pass"] else 1
    if args.repeats < 2:
        parser.error("real recertification requires at least two deterministic repeats")
    if args.deterministic_max_records < 1:
        parser.error("--deterministic-max-records must be positive")
    for name in ("selection", "unit_table", "bank", "checkpoint"):
        if getattr(args, name) is None:
            parser.error(f"--{name.replace('_', '-')} is required without --synthetic")

    selection = json.loads(args.selection.read_text())
    if sha256_file(args.unit_table) != selection["unit_table_file_sha256"]:
        raise ValueError("selection and exact unit-table file hashes differ")
    checkpoint_hash = sha256_file(args.checkpoint)
    if not 1 <= args.probe_steps <= int(selection["horizon_steps"]):
        parser.error("--probe-steps must fit inside the exact segment horizon")

    # Newton 1.5 exposes Warp's run-to-run deterministic atomics for the
    # SolverMuJoCo/MJWarp path. Set the global mode before mjlab imports or
    # compiles any MJWarp kernels so the stock and Newton arms use the same
    # deterministic reduction contract. The record bound matches Newton's
    # model-derived maximum for this G1: max(250 constraint rows,
    # 35*36/2 Hessian entries) = 630.
    import warp as wp

    wp.config.deterministic = wp.DeterministicMode.RUN_TO_RUN
    wp.config.deterministic_max_records = args.deterministic_max_records
    configure_sensor_module_nondeterministic()
    repeated_runs: dict[str, list[dict[str, Any]]] = {}
    for arm in ("stock", "newton"):
        repeated_runs[arm] = []
        for repeat in range(args.repeats):
            print(
                f"[{arm}] independent deterministic repeat "
                f"{repeat + 1}/{args.repeats}"
            )
            repeated_runs[arm].append(
                run_arm(
                    arm,
                    checkpoint=args.checkpoint,
                    table_path=args.unit_table,
                    bank=args.bank,
                    selection=selection,
                    seed=args.seed,
                    device=args.device,
                    probe_steps=args.probe_steps,
                    forced_actions=(
                        repeated_runs["stock"][0]["actions"]
                        if arm == "newton"
                        else None
                    ),
                    shadow_reference=(
                        repeated_runs["stock"][0]
                        if arm == "newton"
                        else None
                    ),
                )
            )
    runs = {arm: arm_runs[0] for arm, arm_runs in repeated_runs.items()}

    cross_stack = compare_runs(runs["stock"], runs["newton"])
    repeatability = {
        arm: compare_repeated_runs(arm_runs)
        for arm, arm_runs in repeated_runs.items()
    }
    six_checks = {
        **cross_stack,
        "deterministic_repeats": {
            "arms": repeatability,
            "pass": all(row["pass"] for row in repeatability.values()),
        },
    }
    passed = all(row["pass"] for row in six_checks.values())

    args.out.parent.mkdir(parents=True, exist_ok=True)
    trajectory_path = args.out.with_name("trajectories.npz")
    arrays: dict[str, np.ndarray] = {}
    trajectory_hashes: dict[str, list[dict[str, str]]] = {}
    for arm, arm_runs in repeated_runs.items():
        trajectory_hashes[arm] = []
        for repeat, run in enumerate(arm_runs):
            repeat_hashes = {}
            for key in (
                "initial_observation",
                "first_action",
                "qpos",
                "qvel",
                "actions",
                "terminated",
                "substep_pre_qpos",
                "substep_pre_qvel",
                "substep_pre_warmstart",
                "substep_ctrl",
                "conformance_qpos",
                "conformance_qvel",
            ):
                array = run[key]
                arrays[f"{arm}_repeat{repeat}_{key}"] = array
                repeat_hashes[key] = sha256_array(array)
            trajectory_hashes[arm].append(repeat_hashes)
    np.savez_compressed(trajectory_path, **arrays)

    result = {
        "schema_version": "newton15_recert_result/2",
        "classification": "unsealed measured conformance result; not a policy-benefit claim",
        "pass": passed,
        "seed": args.seed,
        "repeats": args.repeats,
        "probe_steps": args.probe_steps,
        "device": args.device,
        "warp_deterministic_mode": "RUN_TO_RUN",
        "warp_deterministic_max_records": args.deterministic_max_records,
        "action_protocol": (
            "stock canonical frozen-policy actions replayed in Newton after "
            "an independently checked first action"
        ),
        "selection_sha256": sha256_file(args.selection),
        "unit_table_file_sha256": sha256_file(args.unit_table),
        "unit_table_payload_sha256": selection["unit_table_payload_sha256"],
        "checkpoint": str(args.checkpoint.resolve()),
        "checkpoint_sha256": checkpoint_hash,
        "units": [selection["easy"], selection["contact_rich"]],
        "six_checks": six_checks,
        "absorbed_state_writes": {
            arm: [run["absorbed_state_writes"] for run in arm_runs]
            for arm, arm_runs in repeated_runs.items()
        },
        "live_model_diff": runs["newton"]["live_model_diff"],
        "trajectory_hashes": trajectory_hashes,
        "trajectory_npz": str(trajectory_path.resolve()),
        "trajectory_npz_sha256": sha256_file(trajectory_path),
    }
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    sentinel = {
        "kind": "newton15_recert",
        "exit_code": 0,
        "result_pass": passed,
        "result": str(args.out.resolve()),
        "result_sha256": sha256_file(args.out),
        "trajectory_sha256": result["trajectory_npz_sha256"],
    }
    args.out.with_name("COMPLETED.json").write_text(
        json.dumps(sentinel, indent=1) + "\n"
    )
    print(f"six-step recertification: {'PASS' if passed else 'FAIL'}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
