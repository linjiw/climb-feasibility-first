#!/usr/bin/env python3
"""Keep delayed G1 command history on the physics clock during partial reset."""

from __future__ import annotations

from contextlib import contextmanager
import os

import torch

import eval_physics_reset_fixture as fixture


@contextmanager
def preserve_delay_clock(env, env_ids):
    """Write reset-world controls without appending a fictitious physics frame.

    Restricted to the audited G1 built-in delayed-actuator configuration. The
    ordinary Entity.reset still clears selected buffers; their first physics
    command backfills them. Unselected controls and histories stay untouched.
    """
    robot = env.scene["robot"]
    groups = robot._builtin_group._delayed_groups
    if not groups or env_ids is None or len(env_ids) == env.num_envs:
        yield
        return
    if robot._custom_actuators or robot._builtin_group._index_groups:
        raise ValueError("reset adapter supports only the audited all-delayed builtin G1")
    original_write = robot.write_data_to_sim

    def write_reset_controls():
        for group in groups:
            targets = getattr(robot.data, group.target_attr)
            robot.data.write_ctrl(targets[env_ids][:, group.target_ids],
                                  group.ctrl_ids, env_ids)

    robot.write_data_to_sim = write_reset_controls
    try:
        yield
    finally:
        robot.write_data_to_sim = original_write


original_inject = fixture.inject_lifecycle


@contextmanager
def inject_fixed_lifecycle(design: dict, payload: dict):
    import mjlab.envs

    if design.get("reset_delay_write_fix") is not True:
        raise ValueError("requires separate recorded reset-fix design")
    with original_inject(design, payload):
        original_env = mjlab.envs.ManagerBasedRlEnv

        class Environment(original_env):
            def reset(self, *, seed=None, env_ids=None, options=None):
                if self._fixture_step == 0:
                    return super().reset(seed=seed, env_ids=env_ids, options=options)
                with preserve_delay_clock(self, env_ids):
                    return super().reset(seed=seed, env_ids=env_ids, options=options)

        mjlab.envs.ManagerBasedRlEnv = Environment
        try:
            yield
        finally:
            mjlab.envs.ManagerBasedRlEnv = original_env


if __name__ == "__main__":
    os.environ.update(CUDA_VISIBLE_DEVICES="", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
                      WANDB_MODE="offline", MUJOCO_GL="egl")
    torch.set_num_threads(1)
    fixture.inject_lifecycle = inject_fixed_lifecycle
    fixture.main()
