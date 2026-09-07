"""Cross-bind synthetic endpoint artifacts without reading policy outcomes."""

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from relative_policy_provenance import ARMS, ITERATIONS, SEEDS, sha256, verify_cell, verify_pairing


def record(path):
    return {"path": str(path.resolve()), "sha256": sha256(path)}


@pytest.fixture
def cell(tmp_path):
    conditions_path = ROOT / "reports/g_segment/eval_conditions.json"
    panel_path = ROOT / "reports/g_segment/panel/panel_manifest.json"
    conditions = json.loads(conditions_path.read_text())
    panel = json.loads(panel_path.read_text())
    profiles = json.loads((ROOT / "plan/R3_BASELINE_CONTRACT_2026-09-05.json").read_text())
    profiles["confirmation"]["enabled"] = True
    profile_path = tmp_path / "profiles.json"
    profile_path.write_text(json.dumps(profiles))
    source_path = tmp_path / "synthetic_source.py"
    source_path.write_text("# synthetic source fixture only\n")
    contract = {"conditions": record(conditions_path), "panel": record(panel_path),
                "profiles": record(profile_path), "evaluator": record(source_path),
                "training_entrypoint": record(source_path),
                "evaluator_sources": {"fixture": record(source_path)},
                "training_sources": {"fixture": record(source_path)},
                "software_versions": {"fixture": "1"}}
    checkpoint = tmp_path / "model_3999.pt"
    checkpoint.write_bytes(b"synthetic checkpoint; not a policy")
    csv_path = tmp_path / "eval.csv"
    csv_path.write_text("This is deliberately not a valid endpoint CSV.\n")
    hashes = {"fixture": sha256(source_path)}
    metadata = {"schema_version": "paired_eval_output/1", "task": "Climb-Tracking-Flat-Unitree-G1",
                "checkpoint": str(checkpoint), "checkpoint_sha256": sha256(checkpoint),
                "output": str(csv_path), "conditions": str(conditions_path),
                "conditions_sha256": sha256(conditions_path), "clips_sha256": conditions["panel_txt_sha256"],
                "evaluator_sha256": sha256(source_path), "selected_reference_sha256": panel["motion_sha256"],
                "common_reference_sha256": panel["motion_sha256"], "nominal": conditions["nominal"],
                "joint_noise": conditions["joint_noise"], "nconmax_per_world": conditions["nconmax_per_world"],
                "worlds": 2800, "full_window_worlds": 2800, "source_sha256": hashes,
                "software_versions": contract["software_versions"],
                "startup_randomization_sha256": "a" * 64, "initial_state_sha256": "b" * 64}
    segment = {"sampler_seed": 21, "training_seed": 21, "horizon_steps": 50,
               "unit_table_sha256": profiles["unit_table_sha256"],
               **{key: profiles["arms"]["R"][key] for key in ("mode", "rank", "exploration_ratio",
                                                            "difficulty_power", "progress_floor")},
               **{key: profiles["common"][key] for key in ("progress_window", "max_unit_probability",
                                                          "max_clip_probability")},
               "invalid_start_count": 0, "invalid_reference_frame_count": 0, "censored_resets": 0,
               "relative_progress_factor": 2.0, "allocation_protocol": "relative_progress_alp/1"}
    ledger = {"iteration": 3999, "relative_policy_arm": "R", "relative_policy_stage": "confirmation",
              "num_envs": 512, "profile": profiles["arms"]["R"], "profile_contract_sha256": sha256(profile_path),
              "source_hashes_at_launch": hashes, "training_entrypoint_sha256": sha256(source_path),
              "checkpoint": record(checkpoint), "segment": segment}
    metadata_path = tmp_path / "eval.csv.meta.json"
    metadata_path.write_text(json.dumps(metadata))
    ledger_path = tmp_path / "model_3999_segment.json"
    ledger_path.write_text(json.dumps(ledger))
    return {"csv": record(csv_path), "metadata": record(metadata_path),
            "checkpoint": record(checkpoint), "ledger": record(ledger_path)}, contract


def test_valid_cell_checks_bindings_without_parsing_csv(cell):
    data, contract = cell
    result = verify_cell(data, contract, arm="R", seed=21, iteration=3999)
    assert result["csv_sha256"] == data["csv"]["sha256"]


@pytest.mark.parametrize("field", ["checkpoint_sha256", "conditions_sha256", "common_reference_sha256",
                                   "source_sha256", "joint_noise", "worlds", "initial_state_sha256"])
def test_rehashed_wrong_metadata_still_fails(cell, field):
    data, contract = cell
    path = Path(data["metadata"]["path"])
    metadata = json.loads(path.read_text())
    metadata[field] = "wrong"
    path.write_text(json.dumps(metadata))
    data["metadata"] = record(path)
    with pytest.raises(ValueError):
        verify_cell(data, contract, arm="R", seed=21, iteration=3999)


def test_changed_csv_fails_hash_before_endpoint_parsing(cell):
    data, contract = cell
    Path(data["csv"]["path"]).write_text("different endpoint bytes")
    with pytest.raises(ValueError, match="csv"):
        verify_cell(data, contract, arm="R", seed=21, iteration=3999)


def test_wrong_training_seed_is_not_a_replication(cell):
    data, contract = cell
    with pytest.raises(ValueError, match="sampler"):
        verify_cell(data, contract, arm="R", seed=22, iteration=3999)


def test_development_profiles_do_not_enable_real_analysis(cell):
    data, contract = cell
    contract["profiles"] = record(ROOT / "plan/R3_BASELINE_CONTRACT_2026-09-05.json")
    with pytest.raises(ValueError, match="development"):
        verify_cell(data, contract, arm="R", seed=21, iteration=3999)


def test_full_panel_requires_paired_randomization_and_no_missing_cells():
    cells = [{"arm": arm, "seed": seed, "iteration": iteration,
              "startup_randomization_sha256": "a" * 64, "initial_state_sha256": "b" * 64}
             for arm in ARMS for seed in SEEDS for iteration in ITERATIONS]
    verify_pairing(cells)
    with pytest.raises(ValueError, match="incomplete"):
        verify_pairing(cells[:-1])
    cells[0]["initial_state_sha256"] = "c" * 64
    with pytest.raises(ValueError, match="pairing"):
        verify_pairing(cells)
