"""CLIMB — curriculum learning over imitation motion banks.

An mjlab extension: multi-clip motion conditioning plus clip-level samplers for
the G1 tracking task. Importing this module registers the task ids, so any mjlab
entry point (``train``, ``play``, ``list-envs``) picks them up via
``--task Climb-Tracking-Flat-Unitree-G1``.

The bank itself is chosen at launch through ``--env.commands.motion.motion-files``
or, more usually, by pointing the training script at a tier list from
``screen_bank.py``.
"""

from __future__ import annotations

import os

from mjlab.tasks.registry import register_mjlab_task
from mjlab.tasks.tracking.config.g1.rl_cfg import unitree_g1_tracking_ppo_runner_cfg
from mjlab.tasks.tracking.rl import MotionTrackingOnPolicyRunner

from .commands import MultiClipMotionCommand, MultiClipMotionCommandCfg
from .env_cfg import climb_g1_tracking_env_cfg, read_clip_list
from .motion_bank import MotionBank

__all__ = [
    "MotionBank",
    "MultiClipMotionCommand",
    "MultiClipMotionCommandCfg",
    "climb_g1_tracking_env_cfg",
    "read_clip_list",
]


def _clips_from_env() -> list[str]:
    """Resolve the bank from CLIMB_CLIPS / CLIMB_BANK.

    Passing a 50- to 800-element path list through tyro on the command line is
    not workable, and baking a bank into the task id would make the bank-size
    axis invisible in the run config. An env var keeps mjlab's entire CLI
    (num-envs, max-iterations, logger, ...) usable unchanged while the bank
    stays an explicit, logged launch parameter.
    """
    listing = os.environ.get("CLIMB_CLIPS")
    if not listing:
        return []
    bank = os.environ.get("CLIMB_BANK", os.path.dirname(listing))
    return read_clip_list(listing, bank)


_CLIPS = _clips_from_env()
_ELIGIBILITY_PATH = os.environ.get("CLIMB_ELIGIBILITY_PATH")
_ELIGIBILITY_MODE = os.environ.get("CLIMB_ELIGIBILITY_MODE", "off")
_ELIGIBILITY_THRESHOLD = float(
    os.environ.get("CLIMB_ELIGIBILITY_HARD_THRESHOLD", "0.5")
)

# One task id per sampling arm. Registering them separately keeps the
# manipulated variable visible in the run name and in `list-envs` rather than
# hidden inside a CLI override.
for _task, _mode in (
    ("Climb-Tracking-Flat-Unitree-G1", "uniform"),
    ("Climb-Tracking-Flat-Unitree-G1-Adaptive", "adaptive"),
    ("Climb-Tracking-Flat-Unitree-G1-Grounded", "grounded"),
):
    register_mjlab_task(
        task_id=_task,
        env_cfg=climb_g1_tracking_env_cfg(
            motion_files=_CLIPS,
            sampling_mode=_mode,
            eligibility_path=_ELIGIBILITY_PATH,
            eligibility_mode=_ELIGIBILITY_MODE,
            eligibility_hard_threshold=_ELIGIBILITY_THRESHOLD,
        ),
        play_env_cfg=climb_g1_tracking_env_cfg(
            motion_files=_CLIPS,
            sampling_mode=_mode,
            eligibility_path=_ELIGIBILITY_PATH,
            eligibility_mode=_ELIGIBILITY_MODE,
            eligibility_hard_threshold=_ELIGIBILITY_THRESHOLD,
            play=True,
        ),
        rl_cfg=unitree_g1_tracking_ppo_runner_cfg(),
        runner_cls=MotionTrackingOnPolicyRunner,
    )
