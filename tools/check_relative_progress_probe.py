#!/usr/bin/env python3
"""Check complete relative-ALP telemetry without opening policy endpoints."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from climb.relative_progress import PROTOCOL, RelativeProgressSampler


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check_run(run_dir: Path, manifest: Path, *, seed: int, stage: str) -> dict:
    """Fail closed on missing snapshots, mismatched sources, or invalid support."""
    final = 19 if stage == "smoke" else 3999
    expected = [0, final] if stage == "smoke" else [*range(0, 4000, 100), final]
    paths = list(run_dir.glob("model_*_segment.json"))
    ledgers = [json.loads(path.read_text()) for path in paths]
    if sorted(row["iteration"] for row in ledgers) != expected:
        raise ValueError("missing, duplicate, or unexpected ledger iterations")
    sampler = RelativeProgressSampler(
        manifest, mode="adaptive", seed=seed, rank="learning_progress",
        difficulty_power=0.0, exploration_ratio=0.4, progress_window=10,
        progress_floor=0.0, relative_factor=2.0,
        max_unit_probability=0.05, max_clip_probability=0.25,
    )
    base = sampler.deployment_mass.numpy().astype(float)
    base /= base.sum()
    clips = np.array([unit["clip_id"] for unit in sampler.manifest["admissible_units"]])
    rows = []
    bindings = {}
    for path, ledger in sorted(zip(paths, ledgers), key=lambda pair: pair[1]["iteration"]):
        segment = ledger["segment"]
        contract = {
            "allocation_protocol": PROTOCOL, "relative_progress_factor": 2.0,
            "sampler_seed": seed, "training_seed": seed, "horizon_steps": 50,
            "mode": "adaptive", "rank": "learning_progress", "exploration_ratio": 0.4,
            "difficulty_power": 0.0, "progress_window": 10, "progress_floor": 0.0,
            "max_unit_probability": 0.05, "max_clip_probability": 0.25,
            "unit_table_sha256": sampler.manifest["unit_table_sha256"],
        }
        if any(segment.get(key) != value for key, value in contract.items()):
            raise ValueError(f"sampler contract mismatch: {path}")
        if ledger.get("num_envs") != (8 if stage == "smoke" else 512):
            raise ValueError("environment count mismatch")
        required_sources = {
            "tools/train_relative_progress_probe.py", "climb/relative_progress.py",
            "climb/segment_runtime.py", "climb/segment_curriculum.py",
            "climb/segment_command.py", "climb/segment_env_cfg.py",
        }
        sources = ledger.get("source_hashes_at_launch", {})
        if set(sources) != required_sources:
            raise ValueError("missing source binding")
        for name, digest in sources.items():
            if sha256(ROOT / name) != digest:
                raise ValueError(f"source changed since launch: {name}")
        checkpoint = run_dir / f"model_{ledger['iteration']}.pt"
        if (Path(ledger["checkpoint"]["path"]).resolve() != checkpoint.resolve()
                or sha256(checkpoint) != ledger["checkpoint"]["sha256"]):
            raise ValueError("checkpoint identity mismatch")
        state_path = checkpoint.with_name(f"{checkpoint.stem}_segment_sampler.pt")
        state = torch.load(state_path, map_location="cpu", weights_only=True)
        if state["iteration"] != ledger["iteration"]:
            raise ValueError("sampler iteration mismatch")
        sampler.load_state_dict(state["sampler"])
        p = np.asarray(segment["probabilities"], dtype=float)
        if (p.shape != base.shape or not np.isfinite(p).all() or (p < 0).any()
                or abs(p.sum() - 1) > 1e-10
                or not np.allclose(p, sampler.probabilities.numpy(), atol=1e-12, rtol=0)):
            raise ValueError("invalid probabilities or sampler replay mismatch")
        if np.any(p + 1e-12 < 0.4 * base):
            raise ValueError("exploration floor violated")
        clip_mass = np.bincount(clips, weights=p)
        if p.max() > 0.05 + 1e-12 or clip_mass.max() > 0.25 + 1e-12:
            raise ValueError("probability cap violated")
        for key in ("censored_resets", "invalid_start_count", "invalid_reference_frame_count"):
            if segment[key] != 0:
                raise ValueError(f"{key} is nonzero")
        tv = float(np.abs(p - base).sum() / 2)
        effective = float(np.exp(-(p[p > 0] * np.log(p[p > 0])).sum()))
        saturation = float(segment["rank_saturation_fraction"])
        if not np.isfinite(saturation) or not 0 <= saturation <= 1:
            raise ValueError("invalid saturation")
        rows.append({"iteration": ledger["iteration"], "tv": tv,
                     "effective_units": effective, "top1_unit_mass": float(p.max()),
                     "max_clip_mass": float(clip_mass.max()), "saturation": saturation,
                     "completed_trials": segment["completed_trials"]})
        bindings[str(path)] = {"ledger": sha256(path), "sampler": sha256(state_path),
                               "checkpoint": ledger["checkpoint"]["sha256"]}
    if rows[-1]["completed_trials"] <= 0:
        raise ValueError("no completed trials")
    selected = [row for row in rows if row["iteration"] >= 400]
    gate = None
    status = "smoke_pass"
    if stage == "long":
        mean_tv = float(np.mean([row["tv"] for row in selected]))
        gate = {
            "mean_tv": mean_tv, "tv_pass": 0.05 <= mean_tv <= 0.15,
            "effective_units_pass": all(row["effective_units"] >= 12 for row in selected),
            "final_saturation_pass": rows[-1]["saturation"] < 0.90,
        }
        status = "manipulation_pass" if all(
            value for key, value in gate.items() if key.endswith("_pass")
        ) else "manipulation_fail"
    return {"schema_version": "relative_progress_probe_result/1", "status": status,
            "classification": "exploratory simulation manipulation; no policy-benefit test",
            "policy_endpoints_opened": False, "seed": seed, "stage": stage,
            "gate": gate, "snapshots": rows, "bindings": bindings,
            "manifest_sha256": sha256(manifest), "checker_sha256": sha256(Path(__file__))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=ROOT / "reports/g_segment/unit_table.json")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--stage", choices=("smoke", "long"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = check_run(args.run_dir, args.manifest, seed=args.seed, stage=args.stage)
    except (ValueError, KeyError, OSError, TypeError, RuntimeError) as exc:
        result = {"status": "invalid", "reason": str(exc), "seed": args.seed,
                  "stage": args.stage, "policy_endpoints_opened": False}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({key: result[key] for key in ("status", "seed", "stage")}))
    if result["status"] not in ("smoke_pass", "manipulation_pass"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
