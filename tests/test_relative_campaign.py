"""Campaign aggregation and gate ordering, using synthetic endpoint fixtures."""

import csv
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import analyze_relative_campaign as campaign


@pytest.fixture
def verified_cells(tmp_path, monkeypatch):
    clips = [f"clip{index:03}" for index in range(100)]
    strata = {clip: "feasible_hard_reference" if index < 25 else "feasible_remainder"
              for index, clip in enumerate(clips)}
    conditions = [{"condition_id": f"{clip}@0:r0", "clip": clip, "start_frame": 0,
                   "replicate": 0, "horizon_steps": 150, "full_window": True} for clip in clips]
    condition_path = tmp_path / "conditions.json"
    condition_path.write_text(json.dumps({"conditions": conditions}))
    contract = {"conditions": {"path": str(condition_path), "sha256": campaign.sha256(condition_path)}}
    cells = []
    for arm in sorted(campaign.ARMS):
        for seed in sorted(campaign.SEEDS):
            for iteration in sorted(campaign.ITERATIONS):
                target = 0.5 + ((0.04 + (seed - 22) * 0.001) * iteration / 3999 if arm == "R" else 0.0)
                path = tmp_path / f"{arm}_{seed}_{iteration}.csv"
                rows = [{**row, "survival_s": 3.0, "actual_window_s": 3.0,
                         "success": 1, "absolute_mechanical_work_per_actuator_j": 6.0,
                         "common_root_relative_mpkpe_m_mean": -0.3 * np.log(target),
                         "common_anchor_orientation_error_rad_mean": 0.0} for row in conditions]
                with path.open("w", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(rows)
                cells.append({"arm": arm, "seed": seed, "iteration": iteration,
                              "csv": str(path), "csv_sha256": campaign.sha256(path)})
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{}")
    # Component provenance tests independently exercise the real verification;
    # this fixture isolates aggregation and whether outcomes follow the gate.
    monkeypatch.setattr(campaign, "preflight", lambda _: (contract, strata, cells, {}))
    return manifest_path, cells


def test_complete_scores_and_learning_curve_area(verified_cells):
    path, _ = verified_cells
    result = campaign.analyze(path)
    assert result["status"] == "positive"
    assert result["primary_R_minus_U"]["mean"] == pytest.approx(0.04)
    assert result["AULC_R_minus_U_descriptive"]["mean"] == pytest.approx(0.04 * (1 + 1000 / 3999) / 2)
    assert len(result["per_clip_final_R_minus_U"]) == 100
    assert result["policy_endpoints_opened"] is True


def test_failed_manipulation_stops_before_outcomes(monkeypatch, tmp_path):
    def fail(_):
        raise campaign.NotTested("synthetic manipulation failure")
    monkeypatch.setattr(campaign, "preflight", fail)
    result = campaign.analyze(tmp_path / "absent.json")
    assert result["status"] == "not_tested"
    assert result["policy_endpoints_opened"] is False


def test_draft_contract_never_opens_outcomes(tmp_path):
    contract = tmp_path / "contract.json"
    contract.write_text(json.dumps({"status": "draft"}))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": "relative_campaign_manifest/1",
                                   "contract": {"path": str(contract), "sha256": campaign.sha256(contract)}}))
    result = campaign.analyze(manifest)
    assert result["status"] == "invalid"
    assert result["policy_endpoints_opened"] is False


def test_cli_writes_closed_failure_without_traceback(tmp_path):
    output = tmp_path / "result.json"
    process = subprocess.run([sys.executable, str(ROOT / "tools/analyze_relative_campaign.py"),
                              "--manifest", str(tmp_path / "missing.json"), "--out", str(output)],
                             capture_output=True, text=True, cwd=ROOT)
    assert process.returncode == 1
    assert "Traceback" not in process.stderr
    assert json.loads(output.read_text())["policy_endpoints_opened"] is False


def test_changed_first_csv_is_caught_before_parsing(verified_cells):
    path, cells = verified_cells
    Path(cells[0]["csv"]).write_text("replaced")
    result = campaign.analyze(path)
    assert result["status"] == "invalid"
    assert result["policy_endpoints_opened"] is False


def test_missing_condition_is_not_silently_dropped(verified_cells):
    path, cells = verified_cells
    csv_path = Path(cells[0]["csv"])
    csv_path.write_text("\n".join(csv_path.read_text().splitlines()[:-1]) + "\n")
    cells[0]["csv_sha256"] = campaign.sha256(csv_path)
    result = campaign.analyze(path)
    assert result["status"] == "invalid"
    assert result["policy_endpoints_opened"] is True
    assert "condition" in result["reason"]


def record(path):
    return {"path": str(path), "sha256": campaign.sha256(path)}


@pytest.fixture
def training_records(tmp_path):
    """Exercise real training replay with synthetic uniform-arm trial histories."""
    profile_path = ROOT / "plan/R3_BASELINE_CONTRACT_2026-09-05.json"
    profiles = json.loads(profile_path.read_text())
    selected = profiles["arms"]["U"]
    manifest = ROOT / "reports/g_segment/unit_table.json"
    source = ROOT / "tools/train_relative_policy.py"
    contract = {"profiles": record(profile_path), "unit_table": record(manifest),
                "training_sources": {"tools/train_relative_policy.py": record(source)},
                "training_entrypoint": record(source)}
    contract_hash = "synthetic-contract-not-a-freeze"
    sampler = campaign.SegmentSampler(manifest, mode=selected["mode"], seed=21, rank=selected["rank"],
                exploration_ratio=selected["exploration_ratio"], difficulty_power=selected["difficulty_power"],
                progress_window=10, progress_floor=selected["progress_floor"],
                max_unit_probability=0.05, max_clip_probability=0.25)
    snapshots = []
    for iteration in [*range(0, 4000, 100), 3999]:
        sampler.record_completed_trials(torch.tensor([0, 1]), torch.tensor([False, True]))
        sampler.advance_clock()
        checkpoint = tmp_path / f"model_{iteration}.pt"
        checkpoint.write_bytes(f"synthetic checkpoint {iteration}".encode())
        state = tmp_path / f"sampler_{iteration}.pt"
        torch.save({"iteration": iteration, "sampler": sampler.state_dict()}, state)
        ledger = tmp_path / f"ledger_{iteration}.json"
        segment = {"training_seed": 21, "sampler_seed": 21, "horizon_steps": 50,
                   "unit_table_sha256": profiles["unit_table_sha256"],
                   **{key: selected[key] for key in ("mode", "rank", "exploration_ratio",
                                                     "difficulty_power", "progress_floor")},
                   **{key: profiles["common"][key] for key in ("progress_window",
                                         "max_unit_probability", "max_clip_probability")},
                   "probabilities": sampler.probabilities.tolist(), "invalid_start_count": 0,
                   "invalid_reference_frame_count": 0, "censored_resets": 0,
                   "completed_trials": int(sampler.lifetime_attempts.sum()),
                   "failed_trials": int(sampler.lifetime_failures.sum())}
        ledger.write_text(json.dumps({"iteration": iteration, "relative_policy_arm": "U",
                 "relative_policy_stage": "confirmation", "num_envs": 512, "profile": selected,
                 "profile_contract_sha256": contract["profiles"]["sha256"],
                 "campaign_contract_sha256": contract_hash,
                 "source_hashes_at_launch": {"tools/train_relative_policy.py": campaign.sha256(source)},
                 "training_entrypoint_sha256": campaign.sha256(source),
                 "checkpoint": record(checkpoint), "segment": segment}))
        snapshots.append({"ledger": record(ledger), "checkpoint": record(checkpoint), "sampler": record(state)})
    log = tmp_path / "training.log"
    log.write_text("LAUNCH attempt=1 baseline_vram_mib=1000 2026-09-05T18:00:00-04:00\n"
                   f"[INFO] Logging experiment in directory: {tmp_path}\n"
                   "[INFO] Training with: device=cuda:0, seed=21, rank=0\n"
                   "DONE rc=0 attempt=1 elapsed_s=36 gpu_hours=0.010000 baseline_vram_mib=1000 "
                   "peak_total_vram_mib=12000 peak_delta_mib=11000 2026-09-05T18:00:36-04:00\n")
    return {"snapshots": snapshots, "execution_log": record(log)}, contract, contract_hash


def test_all_training_states_replay(training_records):
    run, contract, digest = training_records
    result = campaign.verify_training(run, contract, digest, arm="U", seed=21)
    assert len(result["snapshots"]) == 41
    assert result["mean_tv"] == pytest.approx(0.0)


def test_failed_training_log_cannot_pass_campaign_gate(training_records):
    run, contract, digest = training_records
    path = Path(run["execution_log"]["path"])
    path.write_text(path.read_text().replace("rc=0", "rc=1"))
    run["execution_log"] = record(path)
    with pytest.raises(ValueError, match="successful execution terminal"):
        campaign.verify_training(run, contract, digest, arm="U", seed=21)


@pytest.mark.parametrize("wrong", ["directory", "seed"])
def test_rehashed_other_run_cost_log_cannot_be_substituted(training_records, wrong):
    run, contract, digest = training_records
    path = Path(run["execution_log"]["path"])
    log = path.read_text()
    log = log.replace(str(path.parent), "/another/run") if wrong == "directory" else log.replace("seed=21", "seed=23")
    path.write_text(log)
    run["execution_log"] = record(path)
    with pytest.raises(ValueError, match="different training run or seed"):
        campaign.verify_training(run, contract, digest, arm="U", seed=21)


def test_copied_history_cannot_pass_training_gate(training_records):
    run, contract, digest = training_records
    previous, final = run["snapshots"][-2:]
    state = torch.load(previous["sampler"]["path"], weights_only=True)
    state["iteration"] = 3999
    state_path = Path(final["sampler"]["path"])
    torch.save(state, state_path)
    final["sampler"] = record(state_path)
    ledger_path = Path(final["ledger"]["path"])
    ledger = json.loads(ledger_path.read_text())
    ledger["segment"] = json.loads(Path(previous["ledger"]["path"]).read_text())["segment"]
    ledger_path.write_text(json.dumps(ledger))
    final["ledger"] = record(ledger_path)
    with pytest.raises(ValueError, match="do not advance"):
        campaign.verify_training(run, contract, digest, arm="U", seed=21)


def test_intermediate_invalid_event_cannot_hide_between_evaluations(training_records):
    run, contract, digest = training_records
    entry = run["snapshots"][15]
    ledger_path = Path(entry["ledger"]["path"])
    ledger = json.loads(ledger_path.read_text())
    ledger["segment"]["invalid_start_count"] = 1
    ledger_path.write_text(json.dumps(ledger))
    entry["ledger"] = record(ledger_path)
    with pytest.raises(ValueError, match="invalid/censored"):
        campaign.verify_training(run, contract, digest, arm="U", seed=21)
