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

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import climb  # noqa: E402,F401  (import registers the Climb-* tasks)
from mjlab.scripts.train import main  # noqa: E402

if __name__ == "__main__":
    if not os.environ.get("CLIMB_CLIPS"):
        sys.exit("set CLIMB_CLIPS to a clip list (and CLIMB_BANK to the bank dir)")
    main()
