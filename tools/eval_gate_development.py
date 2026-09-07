#!/usr/bin/env python3
"""Authenticate both H1 CPU training smokes before development policy evaluation."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys

import torch

from audit_policy_immutability import observe_policy
from eval_natural_lifecycle import verify_policy
from eval_physics_development import sha256


def verify_inputs(path: Path, digest: str) -> tuple[dict, dict]:
    if sha256(path) != digest:
        raise ValueError("gate development design changed")
    design = json.loads(path.read_text())
    if design["stage"] != "gate_evaluator_cpu_development" or design["full_evaluation_enabled"] is not False:
        raise ValueError("only the bound H1 CPU development batch is enabled")
    for name, expected in design["bindings"].items():
        if sha256(Path(name)) != expected:
            raise ValueError(f"gate evaluation dependency changed: {name}")
    work = Path(design["gate_worktree"])
    sys.path[:0] = [str(work / "tools"), str(work)]
    from gate_study_setup import verify_contract
    from gate_training_provenance import verify_training

    record = design["gate_contract"]
    contract = verify_contract(Path(record["path"]), record["sha256"], smoke=True)
    checked = {}
    for arm in ("on", "off"):
        result = verify_training(Path(design["training_runs"][arm]), contract, record["sha256"], arm, 81, smoke=True)
        saved = json.loads((Path(design["training_runs"][arm]).parent / "result.json").read_text())
        if result != saved:
            raise ValueError("training smoke does not reproduce")
        checked[arm] = result
    if checked["on"]["initial_actor"] != checked["off"]["initial_actor"]:
        raise ValueError("training initial actor pairing mismatch")
    clips = Path(design["evaluator_arguments"]["clips"]).read_text().splitlines()
    heldout = Path(design["heldout_clip_list"]).read_text().splitlines()
    if set(clips) & set(heldout):
        raise ValueError("development evaluation overlaps held-out panel")
    return design, checked


@contextmanager
def count_steps(payload: dict):
    import mjlab.envs

    original = mjlab.envs.ManagerBasedRlEnv
    payload["steps"] = 0

    class Environment(original):
        def step(self, action):
            payload["steps"] += 1
            return super().step(action)

    mjlab.envs.ManagerBasedRlEnv = Environment
    try:
        yield
    finally:
        mjlab.envs.ManagerBasedRlEnv = original


def verify_loaded_actor(policy: dict, checkpoint: Path) -> None:
    saved = torch.load(checkpoint, map_location="cpu", weights_only=False)["actor_state_dict"]
    observed = {**policy["before"]["parameters"], **policy["before"]["buffers"]}
    if saved.keys() != observed.keys() or any(not torch.equal(v.cpu(), observed[k]) for k, v in saved.items()):
        raise ValueError("inference policy does not match the authenticated checkpoint")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--design-sha256", required=True)
    parser.add_argument("--admission", choices=("on", "off"), required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    design, checked = verify_inputs(args.design, args.design_sha256)
    import eval_paired_v2 as original

    args.out_dir.mkdir(parents=True, exist_ok=False)
    eval_args = argparse.Namespace(**design["evaluator_arguments"])
    for key in ("clips", "bank", "common_reference_bank", "conditions"):
        setattr(eval_args, key, Path(getattr(eval_args, key)))
    eval_args.checkpoint = Path(design["training_runs"][args.admission]) / "model_19.pt"
    eval_args.out = args.out_dir / "evaluation.csv"
    policy, lifecycle = {}, {}
    with observe_policy(policy), count_steps(lifecycle):
        rc = original.evaluate(eval_args)
    if rc:
        raise ValueError(f"paired evaluator failed: {rc}")
    policy_result = verify_policy(policy, lifecycle["steps"])
    verify_loaded_actor(policy, eval_args.checkpoint)
    torch.save(policy, args.out_dir / "policy.pt")
    receipt = {"status": "gate_development_evaluation_completed", "admission": args.admission,
               "design_sha256": args.design_sha256, "policy": policy_result,
               "training_gate": checked[args.admission], "steps": lifecycle["steps"],
               "artifacts": {p.name: sha256(p) for p in args.out_dir.iterdir() if p.is_file()},
               "confirmation_endpoints_opened": False, "full_evaluation_enabled": False}
    (args.out_dir / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k not in ("training_gate", "artifacts")}))


if __name__ == "__main__":
    os.environ.update(CUDA_VISIBLE_DEVICES="", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
                      WANDB_MODE="offline", MUJOCO_GL="egl")
    torch.set_num_threads(1)
    main()
