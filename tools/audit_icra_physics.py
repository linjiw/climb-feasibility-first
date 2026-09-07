#!/usr/bin/env python3
"""Reproduce frozen configurations and compile their robot for a CPU-only audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-root", type=Path, required=True)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.campaign_root.resolve()
    path = root / "reports/relative_progress_2026-09-05/confirmation_freeze/contract.json"
    if sha256(path) != args.contract_sha256:
        raise ValueError("contract hash mismatch")
    sys.path[:0] = [str(root / "tools"), str(root)]
    from relative_confirmation_setup import build_configs, canonical, config_digest, verify_contract
    contract = verify_contract(path, args.contract_sha256)
    profiles = json.loads(Path(contract["profiles"]["path"]).read_text())
    configs = {}
    for arm in ("U", "A", "R", "D"):
        for seed in (21, 22, 23):
            cfg, runner = build_configs(arm, seed, profiles, contract)
            digest = config_digest(cfg, runner)
            if digest != contract["configuration_sha256"][arm][str(seed)]:
                raise ValueError("configuration differs from frozen identity")
            configs[f"{arm}:{seed}"] = digest
    cfg, runner = build_configs("U", 21, profiles, contract)
    robot = cfg.scene.entities["robot"].build()
    model = robot.compile()
    actuators = []
    for i in range(model.nu):
        joint_id = int(model.actuator_trnid[i, 0])
        actuators.append({"actuator": model.actuator(i).name,
                          "joint": model.joint(joint_id).name,
                          "force_limited": bool(model.actuator_forcelimited[i]),
                          "force_range_nm": model.actuator_forcerange[i].tolist(),
                          "gear": model.actuator_gear[i].tolist()})
    conditions = json.loads(Path(contract["conditions"]["path"]).read_text())
    actuator_cfgs = cfg.scene.entities["robot"].articulation.actuators
    output = {
        "classification": "measured configuration and CPU model compilation; no policy rollout or hardware validation",
        "contract_sha256": args.contract_sha256, "verified_configurations": configs,
        "policy_endpoints_opened": False, "cpu_compiled_actuators": actuators,
        "configured_actuators": [canonical(a) for a in actuator_cfgs],
        "command_delay_physics_steps": [[a.delay_min_lag, a.delay_max_lag] for a in actuator_cfgs],
        "physics_timestep_s": cfg.sim.mujoco.timestep, "control_decimation": cfg.decimation,
        "control_timestep_s": cfg.sim.mujoco.timestep * cfg.decimation,
        "training_steps_per_iteration": runner.num_steps_per_env,
        "training_envs": cfg.scene.num_envs,
        "terrain": canonical(cfg.scene.terrain), "training_events": canonical(cfg.events),
        "robot_collisions": canonical(cfg.scene.entities["robot"].collisions),
        "evaluation_nominal": conditions["nominal"],
        "evaluation_source_observation": "eval_paired_v2.py removes push and observation corruption; nominal also removes startup COM/friction/encoder events",
        "manufacturer_reference": {
            "url": "https://www.unitree.com/g1/", "checked_date": "2026-09-06",
            "maximum_knee_torque_nm": {"G1": 90, "G1_EDU": 120},
            "scope": "public product specification, not calibration of a particular robot or complete motor curves"},
        "limitations": [
            "CPU compilation verifies configured force clamps, not realized saturation during policy rollouts.",
            "No identified robot serial/revision, measured latency, thermal derating or torque-speed validation.",
            "Nominal linkage armatures are approximations documented in g1_constants.py.",
            "Friction randomization and collision configuration are not measured contact fidelity.",
            "Command delay is distinct from motor response lag and observation latency.",
            "Do not modify the frozen model; sensitivity tests require a separate prospective protocol."],
        "tool_sha256": sha256(Path(__file__)),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as handle:
        json.dump(output, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"configurations": len(configs), "compiled_actuators": model.nu,
                      "nominal_evaluation": conditions["nominal"], "policy_endpoints_opened": False}))


if __name__ == "__main__":
    main()
