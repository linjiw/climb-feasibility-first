#!/usr/bin/env python3
"""Observe natural failures and mixed horizons on a fixed training-only batch."""

from __future__ import annotations

import argparse
from contextlib import nullcontext
import json
import os
from pathlib import Path
import sys

import torch

from audit_policy_immutability import observe_policy
from eval_physics_development import instrument, sha256
from eval_physics_reset_fixed import inject_fixed_lifecycle
from physics_sensitivity import CONDITIONS


def verify_policy(policy: dict, calls: int) -> dict:
    if (policy["inference_policy_calls"] != 1 or policy["forward_calls"] != calls
            or policy["training_mode_observed"]):
        raise ValueError("incorrect inference coverage or training mode")
    for group in ("parameters", "buffers"):
        before, after = policy["before"][group], policy["after"][group]
        if not before or before.keys() != after.keys():
            raise ValueError("missing policy tensors")
        for key, value in before.items():
            other = after[key]
            if (value.dtype != other.dtype or value.shape != other.shape
                    or not torch.isfinite(value).all() or not torch.isfinite(other).all()
                    or not torch.equal(value, other)):
                raise ValueError("policy weights or buffers changed")
    if (policy["before"]["training"] != policy["after"]["training"]
            or any(policy["before"]["training"].values())):
        raise ValueError("policy module mode changed")
    return {"forward_calls": calls, "parameters": len(policy["before"]["parameters"]),
            "buffers": len(policy["before"]["buffers"]), "unchanged": True}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--design-sha256", required=True)
    parser.add_argument("--condition", choices=("original", *CONDITIONS), required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    if sha256(args.design) != args.design_sha256:
        raise ValueError("natural lifecycle design changed")
    design = json.loads(args.design.read_text())
    if (design.get("stage") != "natural_lifecycle_cpu" or design.get("injected_failures") != {}
            or design.get("full_evaluation_enabled") is not False):
        raise ValueError("requires bound training-only natural lifecycle design")
    for path, digest in design["bindings"].items():
        if sha256(Path(path)) != digest:
            raise ValueError(f"source/input changed: {path}")
    root = Path(design["root"])
    sys.path[:0] = [str(root / "tools"), str(root)]
    import eval_paired_v2 as original

    args.out_dir.mkdir(parents=True, exist_ok=False)
    eval_args = argparse.Namespace(**design["evaluator_arguments"])
    for key in ("checkpoint", "clips", "bank", "common_reference_bank", "conditions"):
        setattr(eval_args, key, Path(getattr(eval_args, key)))
    eval_args.out = args.out_dir / "evaluation.csv"
    policy, physical = {}, {}
    lifecycle = {"condition": args.condition, "design_sha256": args.design_sha256,
                 "classification": "natural CPU development lifecycle on selected training clips"}
    physical_context = nullcontext() if args.condition == "original" else instrument(args.condition, physical)
    with observe_policy(policy), physical_context, inject_fixed_lifecycle(design, lifecycle):
        rc = original.evaluate(eval_args)
    if rc:
        raise ValueError(f"evaluator failed: {rc}")
    verified = verify_policy(policy, len(lifecycle["steps"]))
    for name, value in (("policy", policy), ("physical", physical), ("lifecycle", lifecycle)):
        torch.save(value, args.out_dir / f"{name}.pt")
    receipt = {"status": "natural_lifecycle_completed", "condition": args.condition,
               "design_sha256": args.design_sha256, "policy": verified,
               "artifacts": {p.name: sha256(p) for p in args.out_dir.iterdir() if p.is_file()},
               "confirmation_endpoints_opened": False, "full_evaluation_enabled": False}
    (args.out_dir / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    os.environ.update(CUDA_VISIBLE_DEVICES="", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
                      WANDB_MODE="offline", MUJOCO_GL="egl")
    torch.set_num_threads(1)
    main()
