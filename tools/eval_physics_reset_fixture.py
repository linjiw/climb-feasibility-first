#!/usr/bin/env python3
"""Exercise original evaluator retirement/reset paths with explicit injected failures."""

from __future__ import annotations

import argparse
from contextlib import contextmanager, nullcontext
import json
import os
from pathlib import Path
import sys

import torch

from audit_policy_immutability import observe_policy, verify_payload
from eval_physics_development import instrument, sha256
from physics_sensitivity import CONDITIONS


def copy_tensor(value):
    return value.detach().cpu().clone()


def reset_state(env) -> dict:
    robot = env.scene["robot"]
    state = {"qpos": copy_tensor(env.sim.data.qpos), "qvel": copy_tensor(env.sim.data.qvel),
             "motion_time": copy_tensor(env.command_manager.get_term("motion").time_steps)}
    seen = set()
    for actuator in robot.actuators:
        buffer = actuator._delay_buffer
        if buffer is None or id(buffer) in seen:
            continue
        index = len(seen)
        seen.add(id(buffer))
        if buffer.is_initialized:
            state.update({f"delay_{index}_peek": copy_tensor(buffer.peek()),
                          f"delay_{index}_count": copy_tensor(buffer._step_count),
                          f"delay_{index}_length": copy_tensor(buffer._buffer.current_length),
                          f"delay_{index}_lag": copy_tensor(buffer.current_lags)})
    return state


@contextmanager
def inject_lifecycle(design: dict, payload: dict):
    import mjlab.envs
    from mjlab.managers import TerminationTermCfg

    original_env = mjlab.envs.ManagerBasedRlEnv
    schedule = {int(step): ids for step, ids in design["injected_failures"].items()}
    payload.update(steps=[], resets=[], physics=[])

    def injected_failure(env):
        mask = torch.zeros(env.num_envs, dtype=torch.bool, device=env.device)
        mask[schedule.get(env._fixture_step, [])] = True
        return mask

    class Environment(original_env):
        def __init__(self, *, cfg, device):
            self._fixture_step = 0
            cfg.terminations["fixture_injected_failure"] = TerminationTermCfg(func=injected_failure)
            super().__init__(cfg=cfg, device=device)
            robot = self.scene["robot"]
            joint_names = list(robot.joint_names)
            target_order = [joint_names.index(self.sim.mj_model.joint(
                int(self.sim.mj_model.actuator_trnid[i, 0])).name.split("/")[-1])
                for i in range(self.sim.mj_model.nu)]
            original_step = self.sim.step

            def physics_step():
                row = {"desired": copy_tensor(robot.data.joint_pos_target[:, target_order]),
                       "ctrl": copy_tensor(self.sim.data.ctrl)}
                original_step()
                row["force"] = copy_tensor(self.sim.data.actuator_force)
                payload["physics"].append(row)

            self.sim.step = physics_step

        def step(self, action):
            self._fixture_step += 1
            result = super().step(action)
            tm = self.termination_manager
            payload["steps"].append({
                "step": self._fixture_step, "terminated": copy_tensor(tm.terminated),
                "dones": copy_tensor(tm.dones),
                "terms": {k: copy_tensor(tm.get_term(k)) for k in tm.active_terms},
                "metrics": {k: copy_tensor(v) for k, v in
                            self.command_manager.get_term("motion").metrics.items()},
            })
            return result

        def reset(self, *, seed=None, env_ids=None, options=None):
            if self._fixture_step == 0:
                return super().reset(seed=seed, env_ids=env_ids, options=options)
            ids = torch.arange(self.num_envs, device=self.device) if env_ids is None else env_ids
            row = {"after_step": self._fixture_step, "ids": copy_tensor(ids),
                   "physics_index": len(payload["physics"]), "before": reset_state(self)}
            result = super().reset(seed=seed, env_ids=env_ids, options=options)
            row["after"] = reset_state(self)
            payload["resets"].append(row)
            return result

    mjlab.envs.ManagerBasedRlEnv = Environment
    try:
        yield
    finally:
        mjlab.envs.ManagerBasedRlEnv = original_env


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--design-sha256", required=True)
    parser.add_argument("--condition", choices=("original", *CONDITIONS), required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    if sha256(args.design) != args.design_sha256:
        raise ValueError("reset fixture design changed")
    design = json.loads(args.design.read_text())
    if design.get("stage") != "injected_reset_cpu" or design.get("full_evaluation_enabled") is not False:
        raise ValueError("requires development-only injected reset design")
    for path, digest in design["bindings"].items():
        if sha256(Path(path)) != digest:
            raise ValueError(f"reset fixture source/input changed: {path}")
    root = Path(design["root"])
    sys.path[:0] = [str(root / "tools"), str(root)]
    import eval_paired_v2 as original

    args.out_dir.mkdir(parents=True, exist_ok=False)
    eval_args = argparse.Namespace(**design["evaluator_arguments"])
    for key in ("checkpoint", "clips", "bank", "common_reference_bank", "conditions"):
        setattr(eval_args, key, Path(getattr(eval_args, key)))
    eval_args.out = args.out_dir / "evaluation.csv"
    policy = {}
    physical = {}
    lifecycle = {"condition": args.condition, "design_sha256": args.design_sha256,
                 "classification": "injected termination software fixture, not policy failure evidence"}
    physical_context = nullcontext() if args.condition == "original" else instrument(args.condition, physical)
    with observe_policy(policy), physical_context, inject_lifecycle(design, lifecycle):
        rc = original.evaluate(eval_args)
    if rc:
        raise ValueError(f"original evaluator failed: {rc}")
    verify_payload(policy)
    for name, data in (("lifecycle", lifecycle), ("policy", policy), ("physical", physical)):
        torch.save(data, args.out_dir / f"{name}.pt")
    artifacts = {p.name: sha256(p) for p in args.out_dir.iterdir() if p.is_file()}
    receipt = {"status": "injected_reset_fixture_completed", "condition": args.condition,
               "design_sha256": args.design_sha256, "artifacts": artifacts,
               "confirmation_endpoints_opened": False, "full_evaluation_enabled": False}
    (args.out_dir / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    os.environ.update(CUDA_VISIBLE_DEVICES="", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
                      WANDB_MODE="offline", MUJOCO_GL="egl")
    torch.set_num_threads(1)
    main()
