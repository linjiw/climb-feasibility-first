#!/usr/bin/env python3
"""Exercise the S1 intervention operators on G1 in a CPU actuator fixture."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import time

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["WANDB_MODE"] = "offline"
os.environ["OMP_NUM_THREADS"] = "1"

import numpy as np
import torch

from physics_sensitivity import (
    CONDITIONS, KNEES, apply_friction, apply_knee_spec, compiled_parameters,
    condition, foot_ids, robot_config,
)

TASK = "Climb-G1-Physics-Sensitivity-Actuator-Fixture"
SEED = 26090641
WORLDS = 2
STEPS = 12


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tensor_hash(values: dict) -> str:
    h = hashlib.sha256()
    for key, value in sorted(values.items()):
        h.update(f"{key}:{value.dtype}:{tuple(value.shape)}".encode())
        h.update(value.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def exercise(base, sim_cfg, name: str, traces: dict) -> dict:
    from mjlab.sim.sim import Simulation
    selected = condition(name)
    torch.manual_seed(SEED)
    entity = robot_config(base, name).build()
    apply_knee_spec(entity, name)
    # The standalone robot fixture has a plane; no reference motion or policy.
    entity.spec.worldbody.add_geom(name="fixture_ground", type=0, size=[0, 0, 0.1])
    model = entity.compile()
    sim = Simulation(num_envs=WORLDS, cfg=deepcopy(sim_cfg), model=model, device="cpu")
    entity.initialize(model, sim.model, sim.data, "cpu")
    sim.expand_model_fields(("geom_friction",))
    qpos = torch.tensor(model.key_qpos[0] if model.nkey else model.qpos0, dtype=torch.float32)
    sim.data.qpos[:] = qpos
    sim.data.qvel.zero_()
    # This independent fixture stream is common across all conditions. It is
    # not a reproduction of training/evaluator startup randomization.
    generator = torch.Generator(device="cpu").manual_seed(SEED)
    startup_friction = 0.3 + 0.9 * torch.rand((WORLDS, 1), generator=generator)
    feet = foot_ids(model)
    sim.model.geom_friction[:, feet, 0] = startup_friction
    common = {"qpos": sim.data.qpos.clone(), "qvel": sim.data.qvel.clone(),
              "friction": sim.model.geom_friction.clone(), "rng": generator.get_state()}
    pre_hash = tensor_hash(common)
    rng_before = torch.get_rng_state().clone()
    apply_friction(sim, name)
    if not torch.equal(rng_before, torch.get_rng_state()):
        raise ValueError("friction intervention consumed global RNG")
    expected_friction = common["friction"].clone()
    if selected["foot_friction"] is not None:
        expected_friction[:, feet, 0] = selected["foot_friction"]
    if not torch.equal(expected_friction, sim.model.geom_friction):
        raise ValueError("friction override changed unrelated coefficients")
    sim.forward()
    entity.update(sim_cfg.mujoco.timestep)
    target_index = [list(entity.joint_names).index(model.joint(int(model.actuator_trnid[i, 0])).name)
                    for i in range(model.nu)]
    targets = [torch.arange(entity.num_joints).float()[None, :].repeat(WORLDS, 1) * 0.001
               + 0.01 * (step + 1) for step in range(STEPS)]
    controls, positions = [], []
    for step, target in enumerate(targets):
        entity.set_joint_position_target(target)
        entity.write_data_to_sim()
        expected = targets[max(0, step - selected["delay_steps"])][:, target_index]
        if not torch.equal(sim.data.ctrl, expected):
            raise ValueError(f"{name}: incorrect command delay at physics step {step}")
        controls.append(sim.data.ctrl.clone())
        sim.step()
        entity.update(sim_cfg.mujoco.timestep)
        if not torch.isfinite(sim.data.qpos).all() or not torch.isfinite(sim.data.qvel).all():
            raise ValueError("nonfinite fixture trajectory")
        positions.append(sim.data.qpos.clone())
    # Probe both clamp signs at a common fixed state without integrating it.
    forces = []
    for sign in (1, -1):
        sim.data.qpos[:] = qpos
        sim.data.qvel.zero_()
        entity.reset(torch.arange(WORLDS))
        entity.set_joint_position_target(torch.full((WORLDS, entity.num_joints), 1000.0 * sign))
        entity.write_data_to_sim()
        sim.forward()
        actual = sim.data.actuator_force.clone()
        limit = torch.tensor(model.actuator_forcerange[:, 1 if sign == 1 else 0], dtype=actual.dtype)
        if not torch.allclose(actual, limit[None, :].expand_as(actual), atol=1e-4, rtol=0):
            raise ValueError("saturated force does not equal configured actuator clamp")
        forces.append(actual)
    # Partial reset: first target backfills the reset row, the other row keeps
    # its history. This is upstream command-buffer semantics, not a warm history.
    entity.reset(torch.tensor([0]))
    reset_target = torch.full((WORLDS, entity.num_joints), 0.123)
    entity.set_joint_position_target(reset_target)
    entity.write_data_to_sim()
    if not torch.equal(sim.data.ctrl[0], reset_target[0, target_index]):
        raise ValueError("first post-reset target did not backfill reset row")
    expected_other = reset_target[1, target_index] if selected["delay_steps"] == 0 else torch.full((model.nu,), -1000.0)
    if not torch.equal(sim.data.ctrl[1], expected_other):
        raise ValueError("partial reset disturbed another world's delay history")
    traces[name] = {"initial": common, "controls": torch.stack(controls),
                    "positions": torch.stack(positions), "saturation_forces": torch.stack(forces),
                    "friction_after": sim.model.geom_friction.clone(),
                    "partial_reset_ctrl": sim.data.ctrl.clone()}
    return {"condition": name, "status": "instrumentation_pass", "parameters": selected,
            "initial_fixture_sha256": pre_hash, "compiled": compiled_parameters(model),
            "physics_timestep_s": sim_cfg.mujoco.timestep, "worlds": WORLDS,
            "integrated_physics_steps_per_world": STEPS,
            "delay_trace_exact": True, "both_force_clamp_signs_verified": True,
            "friction_target_and_untargeted_values_verified": True,
            "partial_reset_buffer_verified": True}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-root", type=Path, required=True)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.campaign_root.resolve()
    sys.path[:0] = [str(root / "tools"), str(root)]
    from relative_confirmation_setup import build_configs, verify_contract
    path = root / "reports/relative_progress_2026-09-05/confirmation_freeze/contract.json"
    contract = verify_contract(path, args.contract_sha256)
    profiles = json.loads(Path(contract["profiles"]["path"]).read_text())
    cfg, _ = build_configs("U", 21, profiles, contract)
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    sources = [Path(__file__).resolve(), Path(__file__).with_name("physics_sensitivity.py").resolve()]
    design = {"classification": "development CPU actuator fixture, not policy evaluation",
              "task_id": TASK, "seed": SEED, "device": "cpu", "worlds": WORLDS,
              "conditions": CONDITIONS, "steps_per_condition_per_world": STEPS,
              "baseline_repeat": True, "total_integrated_world_physics_steps": 9 * WORLDS * STEPS,
              "contract_sha256": args.contract_sha256, "runtime_inventory": contract["runtime_inventory"],
              "sources": {str(p): digest(p) for p in sources},
              "confirmation_endpoints_opened": False, "full_evaluation_enabled": False,
              "limitations": ["No trained policy, tracking reference, reward or success metric.",
                              "Fixture initial states are matched; actual evaluator startup pairing remains untested.",
                              "Friction tensor values verified, not contact forces or hardware contact fidelity.",
                              "First target backfills delay history at reset; not a prewarmed physical command history.",
                              "CPU checks do not establish GPU graph behavior."]}
    (out / "design.json").write_text(json.dumps(design, indent=2) + "\n")
    start = time.monotonic()
    traces, results = {}, []
    try:
        for name in CONDITIONS:
            result = exercise(cfg.scene.entities["robot"], cfg.sim, name, traces)
            results.append(result)
            print(f"{name}: instrumentation pass", flush=True)
        repeat_traces = {}
        repeated = exercise(cfg.scene.entities["robot"], cfg.sim, "unchanged", repeat_traces)
        if repeated != results[0] or any(not torch.equal(traces["unchanged"][k], repeat_traces["unchanged"][k])
                                      for k in ("controls", "positions", "saturation_forces", "friction_after")):
            raise ValueError("unchanged fixture does not reproduce exactly")
        if len({row["initial_fixture_sha256"] for row in results}) != 1:
            raise ValueError("fixture startup differs across conditions")
        base_parameters = results[0]["compiled"]
        for row in results:
            expected = deepcopy(base_parameters)
            cap = row["parameters"]["knee_cap_nm"]
            if cap is not None:
                for knee in KNEES:
                    expected["actuators"][knee]["force_range"] = [-cap, cap]
            if row["compiled"] != expected:
                raise ValueError("compiled intervention changed unrelated physics parameters")
        traces["unchanged_repeat"] = repeat_traces["unchanged"]
        torch.save(traces, out / "traces.pt")
        output = {"status": "s1_cpu_instrumentation_pass", "classification": design["classification"],
                  "task_id": TASK, "seed": SEED, "conditions": results,
                  "matched_fixture_startup": True, "unchanged_repeat_exact": True,
                  "intervention_specificity_verified": True, "elapsed_s": time.monotonic() - start,
                  "design_sha256": digest(out / "design.json"), "traces_sha256": digest(out / "traces.pt"),
                  "confirmation_endpoints_opened": False, "full_evaluation_enabled": False}
        (out / "result.json").write_text(json.dumps(output, indent=2) + "\n")
    except Exception as exc:
        (out / "failure.json").write_text(json.dumps({"status": "instrumentation_failed", "reason": str(exc)}, indent=2) + "\n")
        raise


if __name__ == "__main__":
    torch.set_num_threads(1)
    main()
