#!/usr/bin/env python3
"""Launch mjlab training with the CLIMB multi-clip tasks registered.

mjlab's `train` entry point populates its task registry by importing
`mjlab.tasks`; importing `climb` first adds the Climb-* ids alongside, so every
mjlab CLI flag continues to work.

The bank comes from the environment rather than the command line:

    CLIMB_CLIPS=/data/robotixx/climb/bank/tiers/tier_50.txt \
    CLIMB_BANK=/data/robotixx/climb/bank/amass \
    climb_train.py Climb-Tracking-Flat-Unitree-G1 \
        --env.scene.num-envs 4096 --agent.max-iterations 3000 \
        --agent.logger tensorboard
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import climb  # noqa: E402,F401  (import registers the Climb-* tasks)
from mjlab.scripts.train import main  # noqa: E402
from mjlab.tasks.tracking.rl import MotionTrackingOnPolicyRunner  # noqa: E402


def _install_exposure_ledger() -> None:
    """Persist the per-clip exposure ledger beside every checkpoint.

    ``MultiClipMotionCommand.per_clip_stats()`` is the only record of which
    clips a run actually trained on and how often each one failed, and it lives
    in the command term -- it dies with the process. Which clips a sampler
    spent its budget on is the measurement half of the whole sampler argument,
    so it cannot stay in RAM.

    rsl_rl offers no checkpoint callback, so wrap the runner's ``save``: it is
    the one hook that already fires at every checkpoint, on rank 0 only, with
    the run directory in hand. Wrapping here rather than editing
    ``mjlab/tasks/tracking/rl/runner.py`` keeps the vendored upstream tree
    untouched, which matters because sealed campaign arms import it live.

    Telemetry must never take a training run down, so every failure is
    swallowed with a warning.
    """
    _save = MotionTrackingOnPolicyRunner.save

    def save(self, path, infos=None):
        _save(self, path, infos)
        try:
            cmd = self.env.unwrapped.command_manager.get_term("motion")
            stats = cmd.per_clip_stats()
            stats["iteration"] = int(self.current_learning_iteration)
            stats["sampling_mode"] = str(cmd.cfg.sampling_mode)
            stats["eligibility_path"] = getattr(cmd.cfg, "eligibility_path", None)
            stats["eligibility_mode"] = getattr(cmd.cfg, "eligibility_mode", "off")
            out = os.path.splitext(path)[0] + "_exposure.json"
            with open(out, "w") as fh:
                json.dump(stats, fh)
            print(f"[climb] exposure ledger -> {out}")
        except Exception as exc:  # noqa: BLE001 -- telemetry is never fatal
            print(f"[climb] exposure ledger skipped: {exc}")

    MotionTrackingOnPolicyRunner.save = save


if __name__ == "__main__":
    if not os.environ.get("CLIMB_CLIPS"):
        sys.exit("set CLIMB_CLIPS to a clip list (and CLIMB_BANK to the bank dir)")
    _install_exposure_ledger()
    main()
