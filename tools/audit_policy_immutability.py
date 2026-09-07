#!/usr/bin/env python3
"""Audit inference parameters/buffers without changing the bound evaluator."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys

import torch

from eval_physics_development import main as evaluate_main, sha256


def snapshot(policy: torch.nn.Module) -> dict:
    """Include nonpersistent buffers as well as parameters and module modes."""
    return {
        "parameters": {k: v.detach().cpu().clone() for k, v in policy.named_parameters()},
        "buffers": {k: v.detach().cpu().clone() for k, v in policy.named_buffers()},
        "training": {k: v.training for k, v in policy.named_modules()},
    }


def verify_payload(payload: dict) -> dict:
    before, after = payload["before"], payload["after"]
    if payload["inference_policy_calls"] != 1 or payload["forward_calls"] != 50:
        raise ValueError("unexpected inference lifecycle")
    if payload["training_mode_observed"]:
        raise ValueError("training mode observed during inference")
    counts = {}
    for group in ("parameters", "buffers"):
        if not before[group] or before[group].keys() != after[group].keys():
            raise ValueError(f"missing or changed {group}")
        for name, tensor in before[group].items():
            other = after[group][name]
            if (tensor.dtype != other.dtype or tensor.shape != other.shape
                    or not torch.isfinite(tensor).all() or not torch.isfinite(other).all()
                    or not torch.equal(tensor, other)):
                raise ValueError(f"inference mutated {group}: {name}")
        counts[group] = len(before[group])
    for modes in (before["training"], after["training"]):
        if not modes or any(modes.values()):
            raise ValueError("policy is not in evaluation mode")
    if before["training"].keys() != after["training"].keys():
        raise ValueError("policy module structure changed")
    normalizer_buffers = [k for k in before["buffers"] if "norm" in k.lower()]
    if not normalizer_buffers:
        raise ValueError("normalizer coverage missing")
    return {"status": "inference_immutability_pass", "tensor_counts": counts,
            "normalizer_buffers": normalizer_buffers, "forward_calls": 50}


@contextmanager
def observe_policy(payload: dict):
    import mjlab.tasks.registry as registry

    original_loader = registry.load_runner_cls
    captured = []
    hooks = []
    payload.update(inference_policy_calls=0, forward_calls=0, training_mode_observed=False)

    def loader(task):
        original_runner = original_loader(task)
        if original_runner is None:
            return None

        class Runner(original_runner):
            def get_inference_policy(self, device=None):
                policy = super().get_inference_policy(device=device)
                payload["inference_policy_calls"] += 1
                if captured:
                    raise ValueError("multiple inference policies")
                captured.append(policy)
                payload["before"] = snapshot(policy)

                def before_forward(module, inputs):
                    payload["forward_calls"] += 1
                    payload["training_mode_observed"] |= any(m.training for m in module.modules())

                hooks.append(policy.register_forward_pre_hook(before_forward))
                return policy

        return Runner

    registry.load_runner_cls = loader
    try:
        yield
        if len(captured) != 1:
            raise ValueError("inference policy was not observed")
        payload["after"] = snapshot(captured[0])
    finally:
        for hook in hooks:
            hook.remove()
        registry.load_runner_cls = original_loader


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--design-sha256", required=True)
    parser.add_argument("--condition", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    if sha256(args.design) != args.design_sha256:
        raise ValueError("immutability design changed")
    design = json.loads(args.design.read_text())
    if design.get("policy_immutability_audit") is not True:
        raise ValueError("missing prospective audit designation")
    root = Path(design["root"])
    sys.path[:0] = [str(root / "tools"), str(root)]
    payload = {"condition": args.condition, "design_sha256": args.design_sha256}
    with observe_policy(payload):
        evaluate_main()
    trace = args.out_dir / "policy_immutability.pt"
    torch.save(payload, trace)
    result = verify_payload(payload)
    expected = design["previous_csv"][args.condition]
    if sha256(args.out_dir / "evaluation.csv") != expected["sha256"]:
        raise ValueError("audit changed the previous development CSV")
    result.update(condition=args.condition, design_sha256=args.design_sha256,
                  trace_sha256=sha256(trace), previous_csv_exact_match=True,
                  confirmation_endpoints_opened=False, full_evaluation_enabled=False)
    (args.out_dir / "immutability_verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    os.environ.update(CUDA_VISIBLE_DEVICES="", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
                      WANDB_MODE="offline", MUJOCO_GL="egl")
    torch.set_num_threads(1)
    main()
