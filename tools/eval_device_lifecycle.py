#!/usr/bin/env python3
"""Run source-bound development lifecycle cells with device/graph receipts."""

from __future__ import annotations

import argparse
from contextlib import contextmanager, nullcontext
import json
import os
from pathlib import Path
import sys

import torch

from audit_policy_immutability import observe_policy
from eval_natural_entity_lifecycle import record_entity_resets
from eval_natural_lifecycle import verify_policy
from eval_physics_development import instrument, sha256
from physics_sensitivity import CONDITIONS


@contextmanager
def observe_graphs(payload: dict):
    import mjlab.envs
    import warp as wp

    original_env = mjlab.envs.ManagerBasedRlEnv
    original_launch = wp.capture_launch
    observed = []
    payload["launches"] = {k: 0 for k in ("step", "forward", "reset", "sense")}

    class Environment(original_env):
        def __init__(self, *, cfg, device):
            super().__init__(cfg=cfg, device=device)
            observed.append(self.sim)
            payload.update(device=str(self.device), use_cuda_graph=bool(self.sim.use_cuda_graph),
                           graphs={k: getattr(self.sim, f"{k}_graph") is not None for k in payload["launches"]})

    def capture_launch(graph, *args, **kwargs):
        for sim in observed:
            for key in payload["launches"]:
                if graph is getattr(sim, f"{key}_graph"):
                    payload["launches"][key] += 1
        return original_launch(graph, *args, **kwargs)

    mjlab.envs.ManagerBasedRlEnv = Environment
    wp.capture_launch = capture_launch
    try:
        yield
    finally:
        mjlab.envs.ManagerBasedRlEnv = original_env
        wp.capture_launch = original_launch


def verify_graphs(graphs: dict, device: str, physics_steps: int) -> None:
    if graphs["device"] != device:
        raise ValueError("actual device differs from bound design")
    if device == "cpu":
        if graphs["use_cuda_graph"] or any(graphs["graphs"].values()) or any(graphs["launches"].values()):
            raise ValueError("CPU run reports CUDA graphs")
    elif device == "cuda:0":
        if not graphs["use_cuda_graph"] or not all(graphs["graphs"].values()):
            raise ValueError("required CUDA graphs absent")
        if graphs["launches"]["step"] != physics_steps:
            raise ValueError("CUDA step graph launch count differs from recorded physics")
        if any(graphs["launches"][k] <= 0 for k in ("forward", "reset", "sense")):
            raise ValueError("CUDA lifecycle graph coverage missing")
    else:
        raise ValueError("unsupported development device")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--design-sha256", required=True)
    parser.add_argument("--condition", choices=("original", *CONDITIONS), required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    if sha256(args.design) != args.design_sha256:
        raise ValueError("device lifecycle design changed")
    design = json.loads(args.design.read_text())
    if (design.get("stage") != "device_lifecycle_development" or design.get("injected_failures") != {}
            or design.get("full_evaluation_enabled") is not False or args.condition not in design["conditions"]):
        raise ValueError("requires bound device development design")
    for path, digest in design["bindings"].items():
        if sha256(Path(path)) != digest:
            raise ValueError(f"device lifecycle dependency changed: {path}")
    device = design["evaluator_arguments"]["device"]
    os.environ.update(CUDA_VISIBLE_DEVICES="" if device == "cpu" else "0")
    root = Path(design["root"])
    sys.path[:0] = [str(root / "tools"), str(root)]
    import eval_paired_v2 as original

    args.out_dir.mkdir(parents=True, exist_ok=False)
    eval_args = argparse.Namespace(**design["evaluator_arguments"])
    for key in ("checkpoint", "clips", "bank", "common_reference_bank", "conditions"):
        setattr(eval_args, key, Path(getattr(eval_args, key)))
    eval_args.out = args.out_dir / "evaluation.csv"
    policy, physical, graphs = {}, {}, {}
    lifecycle = {"condition": args.condition, "design_sha256": args.design_sha256,
                 "classification": "device development lifecycle; selected training clips"}
    physical_context = nullcontext() if args.condition == "original" else instrument(args.condition, physical)
    with observe_policy(policy), physical_context, record_entity_resets(design, lifecycle), observe_graphs(graphs):
        rc = original.evaluate(eval_args)
    if rc:
        raise ValueError(f"original evaluator failed: {rc}")
    policy_result = verify_policy(policy, len(lifecycle["steps"]))
    verify_graphs(graphs, device, len(lifecycle["physics"]))
    for name, value in (("policy", policy), ("physical", physical), ("lifecycle", lifecycle)):
        torch.save(value, args.out_dir / f"{name}.pt")
    (args.out_dir / "graphs.json").write_text(json.dumps(graphs, indent=2) + "\n")
    receipt = {"status": "device_lifecycle_completed", "condition": args.condition,
               "design_sha256": args.design_sha256, "policy": policy_result, "device": device,
               "artifacts": {p.name: sha256(p) for p in args.out_dir.iterdir() if p.is_file()},
               "confirmation_endpoints_opened_by_this_job": False, "full_evaluation_enabled": False}
    (args.out_dir / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    os.environ.update(OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", WANDB_MODE="offline", MUJOCO_GL="egl")
    torch.set_num_threads(1)
    main()
