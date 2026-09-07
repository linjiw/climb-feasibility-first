#!/usr/bin/env python3
"""Train one fixed confirmation cell only after the frozen launch contract passes."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import torch

from mjlab.scripts.train import TrainConfig, run_train
import climb_segment_train as base
from check_relative_progress_probe import sha256
from relative_confirmation_setup import build_configs, config_digest, fixed_profiles, verify_contract
from climb.relative_progress import RelativeProgressSampler
from climb.segment_runtime import SegmentSampler


def install_ledger(contract: dict, digest: str, arm: str, seed: int, configuration: str,
                   *, stage: str = "confirmation", num_envs: int = 512) -> None:
    """Bind every checkpoint to the frozen campaign and the exact fixed config."""
    original = base.MotionTrackingOnPolicyRunner.save
    sources = {name: record["sha256"] for name, record in contract["training_sources"].items()}
    profiles = fixed_profiles(Path(contract["profiles"]["path"]))

    def save(self, path: str, infos=None):
        original(self, path, infos)
        command = self.env.unwrapped.command_manager.get_term("motion")
        stats = command.per_clip_stats()
        segment = stats["segment"]
        if (segment["training_seed"] != seed or segment["sampler_seed"] != seed
                or self.env.unwrapped.num_envs != num_envs):
            raise ValueError("actual seed or environment count differs from frozen confirmation")
        checkpoint = Path(path).resolve()
        stats.update({"iteration": int(self.current_learning_iteration), "num_envs": num_envs,
                      "classification": f"{stage} training telemetry; no policy endpoint",
                      "relative_policy_arm": arm, "relative_policy_stage": stage,
                      "campaign_contract_sha256": digest, "configuration_sha256": configuration,
                      "profile": profiles["arms"][arm], "profile_contract_sha256": contract["profiles"]["sha256"],
                      "source_hashes_at_launch": sources,
                      "training_entrypoint_sha256": sha256(Path(__file__)),
                      "checkpoint": {"path": str(checkpoint), "sha256": sha256(checkpoint)}})
        checkpoint.with_name(f"{checkpoint.stem}_segment.json").write_text(json.dumps(stats, indent=1) + "\n")
        torch.save({"iteration": int(self.current_learning_iteration), "sampler": command.sampler.state_dict()},
                   checkpoint.with_name(f"{checkpoint.stem}_segment_sampler.pt"))

    base.MotionTrackingOnPolicyRunner.save = save


def smoke_configs(arm: str, profiles: dict, contract: dict):
    cfg, agent = build_configs(arm, 21, profiles, contract)
    cfg.seed = cfg.commands["motion"].sampler_seed = agent.seed = 51
    cfg.scene.num_envs = 8
    agent.max_iterations = 20
    agent.run_name = f"relative_confirmation_smoke_{arm}_s51"
    return cfg, agent


def verify_entrypoint_smoke(run: Path, contract: dict, draft_record: dict, arm: str) -> dict:
    """Check both checkpoint ledgers and replay actual sampler states for seed 51."""
    profiles = fixed_profiles(Path(contract["profiles"]["path"]))
    expected_config = config_digest(*smoke_configs(arm, profiles, contract))
    selected = profiles["arms"][arm]
    cls = RelativeProgressSampler if arm == "R" else SegmentSampler
    extra = {"relative_factor": 2.0} if arm == "R" else {}
    sampler = cls(Path(contract["unit_table"]["path"]), mode=selected["mode"], seed=51, rank=selected["rank"],
                  exploration_ratio=selected["exploration_ratio"], difficulty_power=selected["difficulty_power"],
                  progress_window=10, progress_floor=selected["progress_floor"],
                  max_unit_probability=0.05, max_clip_probability=0.25, **extra)
    paths = list(run.glob("model_*_segment.json"))
    if sorted(int(path.stem.split("_")[1]) for path in paths) != [0, 19]:
        raise ValueError("entrypoint smoke requires exactly two checkpoints")
    bindings, final_trials = {}, 0
    for path in sorted(paths, key=lambda path: int(path.stem.split("_")[1])):
        row = json.loads(path.read_text())
        iteration = int(path.stem.split("_")[1])
        expected = {"relative_policy_arm": arm, "relative_policy_stage": "entrypoint_smoke", "num_envs": 8,
                    "iteration": iteration, "configuration_sha256": expected_config,
                    "campaign_contract_sha256": draft_record["sha256"], "profile": selected,
                    "profile_contract_sha256": contract["profiles"]["sha256"],
                    "training_entrypoint_sha256": sha256(Path(__file__)),
                    "source_hashes_at_launch": {name: record["sha256"] for name, record in contract["training_sources"].items()}}
        if any(row.get(key) != value for key, value in expected.items()):
            raise ValueError("entrypoint smoke configuration/source identity mismatch")
        checkpoint = run / f"model_{iteration}.pt"
        if row["checkpoint"] != {"path": str(checkpoint.resolve()), "sha256": sha256(checkpoint)}:
            raise ValueError("entrypoint smoke checkpoint link mismatch")
        state_path = run / f"model_{iteration}_segment_sampler.pt"
        state = torch.load(state_path, map_location="cpu", weights_only=True)
        if state["iteration"] != iteration:
            raise ValueError("entrypoint smoke sampler iteration mismatch")
        sampler.load_state_dict(state["sampler"])
        segment = row["segment"]
        expected_segment = {"unit_table_sha256": profiles["unit_table_sha256"],
                            **{key: selected[key] for key in ("mode", "rank", "exploration_ratio", "difficulty_power", "progress_floor")},
                            "progress_window": 10, "max_unit_probability": 0.05, "max_clip_probability": 0.25}
        if any(segment.get(key) != value for key, value in expected_segment.items()):
            raise ValueError("entrypoint smoke actual sampler profile mismatch")
        if arm == "R" and (segment.get("allocation_protocol") != "relative_progress_alp/1"
                           or segment.get("relative_progress_factor") != 2.0):
            raise ValueError("entrypoint smoke relative allocator identity mismatch")
        if (segment["training_seed"] != 51 or segment["sampler_seed"] != 51 or segment["horizon_steps"] != 50
                or any(segment[key] != 0 for key in ("invalid_start_count", "invalid_reference_frame_count", "censored_resets"))
                or not torch.equal(torch.tensor(segment["probabilities"], dtype=torch.float64), sampler.probabilities)
                or segment["completed_trials"] != int(sampler.lifetime_attempts.sum())
                or segment["failed_trials"] != int(sampler.lifetime_failures.sum())):
            raise ValueError("entrypoint smoke trial accounting/replay mismatch")
        final_trials = segment["completed_trials"]
        bindings[str(path)] = {"ledger": sha256(path), "sampler": sha256(state_path), "checkpoint": sha256(checkpoint)}
    if final_trials <= 0:
        raise ValueError("entrypoint smoke has no completed trials")
    return {"status": "entrypoint_smoke_pass", "arm": arm, "seed": 51, "run_dir": str(run),
            "draft_contract": draft_record, "completed_trials": final_trials, "bindings": bindings,
            "policy_endpoints_opened": False, "checker_sha256": sha256(Path(__file__))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--arm", choices=("U", "A", "R", "D"), required=True)
    parser.add_argument("--seed", type=int, choices=(21, 22, 23, 51), required=True)
    parser.add_argument("--smoke", action="store_true", help="Use only seed 51, 8 environments and 20 iterations")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    if (args.seed == 51) != args.smoke:
        parser.error("seed 51 is reserved for --smoke; confirmation uses seeds 21/22/23")
    contract = verify_contract(args.contract, args.contract_sha256, smoke=args.smoke)
    profiles = fixed_profiles(Path(contract["profiles"]["path"]))
    cfg, agent = smoke_configs(args.arm, profiles, contract) if args.smoke else build_configs(args.arm, args.seed, profiles, contract)
    identity = config_digest(cfg, agent)
    if not args.smoke and identity != contract["configuration_sha256"][args.arm][str(args.seed)]:
        raise ValueError("constructed configuration differs from prospective freeze")
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    log_dir = out / "g1_tracking" / agent.run_name
    with (out / "launch.json").open("x") as handle:
        json.dump({"contract": str(args.contract.resolve()), "campaign_contract_sha256": args.contract_sha256,
                   "arm": args.arm, "seed": args.seed, "configuration_sha256": identity,
                   "run_dir": str(log_dir), "policy_endpoints_opened": False}, handle, indent=2)
        handle.write("\n")
    os.environ.update(CUDA_VISIBLE_DEVICES="0", MUJOCO_GL="egl", WANDB_MODE="offline")
    task = f"Climb-Tracking-Flat-Unitree-G1-Policy-{args.arm}-{'ConfirmationSmoke' if args.smoke else 'Confirmation'}"
    base.register_mjlab_task(task_id=task, env_cfg=cfg, play_env_cfg=cfg, rl_cfg=agent,
                            runner_cls=base.MotionTrackingOnPolicyRunner)
    install_ledger(contract, args.contract_sha256, args.arm, args.seed, identity,
                   stage="entrypoint_smoke" if args.smoke else "confirmation", num_envs=8 if args.smoke else 512)
    run_train(task, TrainConfig(env=cfg, agent=agent, log_root=str(out)), log_dir)
    if args.smoke:
        result = verify_entrypoint_smoke(log_dir, contract,
                      {"path": str(args.contract.resolve()), "sha256": args.contract_sha256}, args.arm)
        with (out / "smoke_result.json").open("x") as handle:
            json.dump(result, handle, indent=2)
            handle.write("\n")


if __name__ == "__main__":
    main()
