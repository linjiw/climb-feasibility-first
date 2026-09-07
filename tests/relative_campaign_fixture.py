"""Construct synthetic artifacts for real campaign preflight; never run a policy."""

import csv
import json
from pathlib import Path

import numpy as np
import torch

import analyze_relative_campaign as campaign
from check_relative_progress_probe import check_run, sha256
from run_relative_failure_calibration import TRAINING_SOURCES, verify_calibration

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "plan/R3_BASELINE_CONTRACT_2026-09-05.json"
MANIFEST = ROOT / "reports/g_segment/unit_table.json"


def record(path):
    return {"path": str(path.resolve()), "sha256": sha256(path)}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, allow_nan=False))
    return record(path)


def write_run(directory, arm, seed, stage, profile_path, contract_hash=None):
    """Create constructed histories, not simulated trajectories or checkpoints."""
    directory.mkdir(parents=True)
    profiles = json.loads(profile_path.read_text())
    selected = profiles["arms"][arm]
    cls = campaign.RelativeProgressSampler if arm == "R" else campaign.SegmentSampler
    kwargs = {"relative_factor": 2.0} if arm == "R" else {}
    sampler = cls(MANIFEST, mode=selected["mode"], seed=seed, rank=selected["rank"],
                  exploration_ratio=selected["exploration_ratio"], difficulty_power=selected["difficulty_power"],
                  progress_window=10, progress_floor=selected["progress_floor"],
                  max_unit_probability=0.05, max_clip_probability=0.25, **kwargs)
    is_probe = stage in ("smoke", "long")
    names = list(TRAINING_SOURCES)
    if is_probe:
        names[0] = "tools/train_relative_progress_probe.py"
    sources = {name: sha256(ROOT / name) for name in names}
    ids = torch.arange(sampler.num_units).repeat(10)
    repetitions = torch.arange(10).repeat_interleave(sampler.num_units)
    failed = repetitions < torch.where(ids % 2 == 0, 9, 1)
    snapshots = []
    iterations = [0, 19] if stage == "smoke" else [*range(0, 4000, 100), 3999]
    for iteration in iterations:
        sampler.record_completed_trials(ids, failed)
        sampler.advance_clock()
        # Synthetic nonzero rank vector; no claim these histories arise under PPO.
        rates = sampler.conditional_success_rates()
        sampler.rate_history = rates.repeat(11, 1)
        sampler.rate_history[0, ::2] -= 0.05
        sampler.probabilities = sampler._compute_probabilities()
        checkpoint = directory / f"model_{iteration}.pt"
        checkpoint.write_bytes(f"SYNTHETIC, NOT A POLICY: {arm} {seed} {iteration}".encode())
        state_path = directory / f"model_{iteration}_segment_sampler.pt"
        torch.save({"iteration": iteration, "sampler": sampler.state_dict()}, state_path)
        segment = {"sampler_seed": seed, "training_seed": seed, "horizon_steps": 50,
                   "unit_table_sha256": profiles["unit_table_sha256"],
                   **{key: selected[key] for key in ("mode", "rank", "exploration_ratio", "difficulty_power", "progress_floor")},
                   **{key: profiles["common"][key] for key in ("progress_window", "max_unit_probability", "max_clip_probability")},
                   "completed_trials": int(sampler.lifetime_attempts.sum()),
                   "failed_trials": int(sampler.lifetime_failures.sum()),
                   "invalid_start_count": 0, "invalid_reference_frame_count": 0, "censored_resets": 0,
                   "rank_saturation_fraction": sampler.saturation_fraction(),
                   "probabilities": sampler.probabilities.tolist()}
        if arm == "R":
            segment.update(relative_progress_factor=2.0, allocation_protocol="relative_progress_alp/1")
        ledger = {"iteration": iteration, "num_envs": 8 if stage == "smoke" else 512,
                  "relative_policy_arm": arm, "relative_policy_stage": stage,
                  "source_hashes_at_launch": sources, "training_entrypoint_sha256": sources[names[0]],
                  "profile": selected, "profile_contract_sha256": sha256(profile_path),
                  "campaign_contract_sha256": contract_hash, "checkpoint": record(checkpoint), "segment": segment}
        ledger_record = write_json(directory / f"model_{iteration}_segment.json", ledger)
        snapshots.append({"ledger": ledger_record, "checkpoint": record(checkpoint), "sampler": record(state_path)})
    log = directory / "SYNTHETIC_training.log"
    log.write_text("LAUNCH attempt=1 baseline_vram_mib=1000 2026-09-05T18:00:00-04:00\n"
                   f"[INFO] Logging experiment in directory: {directory}\n"
                   f"[INFO] Training with: device=cuda:0, seed={seed}, rank=0\n"
                   "DONE rc=0 attempt=1 elapsed_s=36 gpu_hours=0.010000 baseline_vram_mib=1000 "
                   "peak_total_vram_mib=12000 peak_delta_mib=11000 2026-09-05T18:00:36-04:00\n")
    return {"snapshots": snapshots, "execution_log": record(log)}


def build_campaign(base):
    profiles = json.loads(PROFILE.read_text())
    profiles["confirmation"]["enabled"] = True
    profile_path = base / "SYNTHETIC_profiles.json"
    write_json(profile_path, profiles)
    contract = {"status": "frozen_before_confirmation", "classification": "SYNTHETIC TEST FIXTURE ONLY",
                "profiles": record(profile_path), "unit_table": record(MANIFEST),
                "conditions": record(ROOT / "reports/g_segment/eval_conditions.json"),
                "panel": record(ROOT / "reports/g_segment/panel/panel_manifest.json"),
                "training_entrypoint": record(ROOT / "tools/train_relative_policy.py"),
                "training_sources": {name: record(ROOT / name) for name in TRAINING_SOURCES},
                "analysis_sources": {name: record(ROOT / "tools" / name) for name in (
                    "analyze_relative_campaign.py", "analyze_relative_policy.py", "relative_policy_provenance.py",
                    "relative_policy_secondaries.py", "analyze_relative_cost.py")},
                "evaluator": record(ROOT / "tools/eval_paired_v2.py"),
                "evaluator_sources": {"tools/eval_paired_v2.py": record(ROOT / "tools/eval_paired_v2.py")},
                "software_versions": {"fixture": "synthetic"}, "relative_replication": {}, "failure_calibration": {}}
    for seed in (11, 12):
        study = base / f"prerequisite_R_{seed}"
        for stage in ("smoke", "long"):
            write_run(study / stage, "R", seed, stage, PROFILE)
            result = check_run(study / stage, MANIFEST, seed=seed, stage=stage)
            assert result["status"] in ("smoke_pass", "manipulation_pass")
            write_json(study / f"{stage}_result.json", result)
        write_json(study / "design.json", {"seed": seed, "policy_endpoints_opened": False,
                                          "sources": {"tools/check_relative_progress_probe.py": sha256(ROOT / "tools/check_relative_progress_probe.py")}})
        write_json(study / "terminal_status.json", {"seed": seed, "status": "completed", "policy_endpoints_opened": False})
        (study / "long.log").write_text("SYNTHETIC TEST SENTINEL ONLY: DONE rc=0 elapsed_s=1\n")
        contract["relative_replication"][str(seed)] = {"study_dir": str(study), "decision": record(study / "long_result.json")}
    sources = {name: sha256(ROOT / name) for name in TRAINING_SOURCES}
    execution = write_json(base / "D_execution.json", {"sources": sources})
    for seed in (31, 32):
        run = base / f"prerequisite_D_{seed}"
        write_run(run, "D", seed, "calibration", PROFILE)
        result = verify_calibration(run, seed, sources)
        assert result["status"] == "calibration_pass"
        contract["failure_calibration"][str(seed)] = {"decision": write_json(base / f"D_{seed}_decision.json", result),
                                                     "execution_design": execution}
    conditions_path = Path(contract["conditions"]["path"])
    conditions = json.loads(conditions_path.read_text())
    panel = json.loads(Path(contract["panel"]["path"]).read_text())
    clips = sorted(panel["motion_sha256"])
    strata_path = base / "strata.csv"
    with strata_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["clip", "stratum"])
        writer.writerows((clip, "feasible_hard_reference" if index < 25 else "feasible_remainder") for index, clip in enumerate(clips))
    contract["strata"] = record(strata_path)
    contract_record = write_json(base / "SYNTHETIC_contract.json", contract)
    manifest = {"schema_version": "relative_campaign_manifest/1", "contract": contract_record, "arms": {}}
    for arm in sorted(campaign.ARMS):
        manifest["arms"][arm] = {}
        for seed in sorted(campaign.SEEDS):
            directory = base / f"confirmation_{arm}_{seed}"
            run = write_run(directory, arm, seed, "confirmation", profile_path, contract_record["sha256"])
            run["evaluations"] = {}
            for iteration in sorted(campaign.ITERATIONS):
                snapshot = next(entry for entry in run["snapshots"] if Path(entry["checkpoint"]["path"]).stem == f"model_{iteration}")
                csv_path = directory / f"eval_{iteration}.csv"
                score = 0.54 if arm == "R" else 0.5
                rows = [{**row, "survival_s": 3.0, "actual_window_s": 3.0, "success": 1,
                         "common_root_relative_mpkpe_m_mean": -0.3 * np.log(score),
                         "common_anchor_orientation_error_rad_mean": 0.0,
                         "absolute_mechanical_work_per_actuator_j": 6.0} for row in conditions["conditions"]]
                with csv_path.open("w", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(rows)
                metadata = {"schema_version": "paired_eval_output/1", "task": "Climb-Tracking-Flat-Unitree-G1",
                            "checkpoint": snapshot["checkpoint"]["path"], "checkpoint_sha256": snapshot["checkpoint"]["sha256"],
                            "output": str(csv_path), "conditions": str(conditions_path),
                            "conditions_sha256": contract["conditions"]["sha256"], "clips_sha256": conditions["panel_txt_sha256"],
                            "evaluator_sha256": contract["evaluator"]["sha256"],
                            "selected_reference_sha256": panel["motion_sha256"], "common_reference_sha256": panel["motion_sha256"],
                            **{key: conditions[key] for key in ("nominal", "joint_noise", "nconmax_per_world")},
                            "worlds": 2800, "full_window_worlds": 2800, "software_versions": contract["software_versions"],
                            "source_sha256": {name: data["sha256"] for name, data in contract["evaluator_sources"].items()},
                            "startup_randomization_sha256": "a" * 64, "initial_state_sha256": "b" * 64}
                run["evaluations"][str(iteration)] = {"csv": record(csv_path),
                       "metadata": write_json(directory / f"eval_{iteration}.meta.json", metadata),
                       "checkpoint": snapshot["checkpoint"], "ledger": snapshot["ledger"]}
            manifest["arms"][arm][str(seed)] = run
    path = base / "SYNTHETIC_manifest.json"
    write_json(path, manifest)
    return path
