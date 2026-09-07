#!/usr/bin/env python3
"""Run bound development-only S1 cells through the original paired evaluator."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass, fields
import hashlib
import json
import os
from pathlib import Path
import sys

import torch

from physics_sensitivity import CONDITIONS, apply_friction, apply_knee_spec, robot_config


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@contextmanager
def instrument(name: str, payload: dict):
    """Scope instrumentation to this isolated process and restore all imports."""
    import mjlab.envs
    import mjlab.rl
    from mjlab.entity import EntityCfg
    from eval_paired_v2 import sha256_tensors

    original_env = mjlab.envs.ManagerBasedRlEnv
    original_wrapper = mjlab.rl.RslRlVecEnvWrapper

    @dataclass(kw_only=True)
    class RobotCfg(EntityCfg):
        def build(self):
            entity = super().build()
            apply_knee_spec(entity, name)
            return entity

    class Environment(original_env):
        def __init__(self, *, cfg, device):
            robot = robot_config(cfg.scene.entities["robot"], name)
            cfg.scene.entities["robot"] = RobotCfg(**{f.name: getattr(robot, f.name) for f in fields(robot)})
            super().__init__(cfg=cfg, device=device)
            self._physics_trace = []
            self._first_step = True
            robot = self.scene["robot"]
            payload["startup_before_intervention"] = {
                "body_ipos": self.sim.model.body_ipos.clone().cpu(),
                "encoder_bias": robot.data.encoder_bias.clone().cpu(),
                "geom_friction": self.sim.model.geom_friction.clone().cpu(),
                "rng_cpu": torch.get_rng_state().clone(),
            }
            apply_friction(self.sim, name)
            payload["friction_after_intervention"] = self.sim.model.geom_friction.clone().cpu()
            payload["force_ranges"] = torch.tensor(self.sim.mj_model.actuator_forcerange.copy())
            payload["actuator_names"] = [self.sim.mj_model.actuator(i).name for i in range(self.sim.mj_model.nu)]
            payload["geom_names"] = [self.sim.mj_model.geom(i).name for i in range(self.sim.mj_model.ngeom)]
            joint_names = list(robot.joint_names)
            target_order = [joint_names.index(self.sim.mj_model.joint(int(self.sim.mj_model.actuator_trnid[i, 0])).name.split("/")[-1])
                            for i in range(self.sim.mj_model.nu)]
            original_step = self.sim.step

            def physics_step():
                self._physics_trace.append({
                    "desired": robot.data.joint_pos_target[:, target_order].detach().cpu().clone(),
                    "ctrl": self.sim.data.ctrl.detach().cpu().clone(),
                })
                original_step()
                self._physics_trace[-1]["force"] = self.sim.data.actuator_force.detach().cpu().clone()

            self.sim.step = physics_step

        def step(self, action):
            if self._first_step:
                self._first_step = False
                payload["initial_state"] = {"qpos": self.sim.data.qpos.clone().cpu(),
                                            "qvel": self.sim.data.qvel.clone().cpu()}
                payload["initial_state_sha256"] = sha256_tensors(payload["initial_state"])
                payload["first_action"] = action.detach().clone().cpu()
                payload["first_observation"] = payload["last_observation"]
            return super().step(action)

        def close(self):
            payload["physics"] = self._physics_trace
            return super().close()

    class Wrapper(original_wrapper):
        def get_observations(self):
            obs = super().get_observations()
            payload["last_observation"] = {k: v.detach().clone().cpu() for k, v in obs.items()}
            return obs

    mjlab.envs.ManagerBasedRlEnv = Environment
    mjlab.rl.RslRlVecEnvWrapper = Wrapper
    try:
        yield
    finally:
        mjlab.envs.ManagerBasedRlEnv = original_env
        mjlab.rl.RslRlVecEnvWrapper = original_wrapper


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--design-sha256", required=True)
    parser.add_argument("--condition", choices=("original", *CONDITIONS), required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    if sha256(args.design) != args.design_sha256:
        raise ValueError("development design changed")
    design = json.loads(args.design.read_text())
    if design.get("full_evaluation_enabled") is not False or design.get("stage") != "development_cpu":
        raise ValueError("this adapter accepts only the fixed CPU development smoke")
    for path, digest in design["bindings"].items():
        if sha256(Path(path)) != digest:
            raise ValueError(f"development input/source changed: {path}")
    root = Path(design["root"])
    sys.path[:0] = [str(root / "tools"), str(root)]
    import eval_paired_v2 as original
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    eval_args = argparse.Namespace(**design["evaluator_arguments"])
    for key in ("checkpoint", "clips", "bank", "common_reference_bank", "conditions"):
        setattr(eval_args, key, Path(getattr(eval_args, key)))
    eval_args.out = out / "evaluation.csv"
    payload = {"condition": args.condition, "design_sha256": args.design_sha256,
               "classification": "development policy rollout lifecycle; not confirmation or robustness efficacy"}
    try:
        if args.condition == "original":
            rc = original.evaluate(eval_args)
        else:
            with instrument(args.condition, payload):
                rc = original.evaluate(eval_args)
            payload.pop("last_observation", None)
            torch.save(payload, out / "instrumentation.pt")
        if rc:
            raise ValueError(f"original evaluator returned {rc}")
        receipt = {"status": "development_cell_completed", "condition": args.condition,
                   "design_sha256": args.design_sha256, "csv_sha256": sha256(eval_args.out),
                   "metadata_sha256": sha256(Path(str(eval_args.out) + ".meta.json")),
                   "confirmation_endpoints_opened": False}
        if args.condition != "original":
            receipt["instrumentation_sha256"] = sha256(out / "instrumentation.pt")
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    except Exception as exc:
        (out / "failure.json").write_text(json.dumps({"status": "development_failed", "reason": str(exc)}, indent=2) + "\n")
        raise


if __name__ == "__main__":
    os.environ.update(CUDA_VISIBLE_DEVICES="", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", WANDB_MODE="offline", MUJOCO_GL="egl")
    torch.set_num_threads(1)
    main()
