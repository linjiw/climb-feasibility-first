#!/usr/bin/env python3
"""Record command-driven robot resets as well as environment reset boundaries."""

from __future__ import annotations

from contextlib import contextmanager
import os

import torch

import eval_natural_lifecycle as natural
from eval_physics_reset_fixture import copy_tensor, reset_state


original_context = natural.inject_fixed_lifecycle


@contextmanager
def record_entity_resets(design: dict, payload: dict):
    import mjlab.envs

    if design.get("entity_reset_recording") is not True:
        raise ValueError("requires separately recorded entity-reset design")
    payload["entity_resets"] = []
    with original_context(design, payload):
        original_env = mjlab.envs.ManagerBasedRlEnv

        class Environment(original_env):
            def __init__(self, *, cfg, device):
                self._inside_environment_reset = False
                super().__init__(cfg=cfg, device=device)
                robot = self.scene["robot"]
                original_reset = robot.reset

                def entity_reset(env_ids=None):
                    if self._fixture_step == 0:
                        return original_reset(env_ids=env_ids)
                    indices = torch.arange(self.num_envs, device=self.device)
                    ids = indices if env_ids is None else indices[env_ids] if isinstance(env_ids, slice) else env_ids
                    row = {"step": self._fixture_step, "physics_index": len(payload["physics"]),
                           "ids": copy_tensor(ids), "before": reset_state(self),
                           "source": "environment_reset" if self._inside_environment_reset else "motion_resample"}
                    result = original_reset(env_ids=env_ids)
                    row["after"] = reset_state(self)
                    payload["entity_resets"].append(row)
                    return result

                robot.reset = entity_reset

            def reset(self, *, seed=None, env_ids=None, options=None):
                self._inside_environment_reset = True
                try:
                    return super().reset(seed=seed, env_ids=env_ids, options=options)
                finally:
                    self._inside_environment_reset = False

        mjlab.envs.ManagerBasedRlEnv = Environment
        try:
            yield
        finally:
            mjlab.envs.ManagerBasedRlEnv = original_env


if __name__ == "__main__":
    os.environ.update(CUDA_VISIBLE_DEVICES="", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
                      WANDB_MODE="offline", MUJOCO_GL="egl")
    torch.set_num_threads(1)
    natural.inject_fixed_lifecycle = record_entity_resets
    natural.main()
