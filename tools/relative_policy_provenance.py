"""Verify one prospective R3 evaluation cell before parsing its outcome rows.

This is an input-validation component, not a complete benchmark analyzer. The
future campaign gate must authenticate its frozen contract and all manipulation
results before using these verified cell paths. No CLI opens real endpoints.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from check_relative_progress_probe import sha256

ARMS = {"U", "A", "R", "D"}
SEEDS = {21, 22, 23}
ITERATIONS = {1000, 2000, 3000, 3999}


def verified(record: dict[str, str], label: str) -> Path:
    if not isinstance(record, dict) or set(record) != {"path", "sha256"}:
        raise ValueError(f"{label}: expected exact path/hash record")
    path = Path(record["path"]).resolve()
    if not path.is_file() or sha256(path) != record["sha256"]:
        raise ValueError(f"{label}: missing or changed artifact")
    return path


def path_matches(value: Any, expected: Path) -> bool:
    return isinstance(value, str) and Path(value).resolve() == expected


def verify_cell(cell: dict, contract: dict, *, arm: str, seed: int, iteration: int) -> dict:
    """Hash/check all cross-links, returning a CSV path without parsing endpoints."""
    if arm not in ARMS or seed not in SEEDS or iteration not in ITERATIONS:
        raise ValueError("not a fixed confirmation arm/seed/checkpoint")
    if set(cell) != {"csv", "metadata", "checkpoint", "ledger"}:
        raise ValueError("cell must bind CSV, metadata, checkpoint and training ledger")
    conditions_path = verified(contract["conditions"], "conditions")
    panel_path = verified(contract["panel"], "panel")
    profile_path = verified(contract["profiles"], "profiles")
    verified(contract["evaluator"], "evaluator")
    verified(contract["training_entrypoint"], "training entrypoint")
    conditions = json.loads(conditions_path.read_text())
    panel = json.loads(panel_path.read_text())
    profiles = json.loads(profile_path.read_text())
    if profiles["confirmation"]["enabled"] is not True:
        raise ValueError("prospective development profile cannot authorize confirmation analysis")
    if (conditions["schema_version"] != "paired_eval_conditions/2"
            or panel["schema_version"] != "g_segment_eval_panel/1"):
        raise ValueError("unsupported condition/panel schema")
    condition_rows = conditions["conditions"]
    identities = [row["condition_id"] for row in condition_rows]
    reference_hashes = panel["motion_sha256"]
    if (len(identities) != 2800 or len(set(identities)) != 2800 or len(reference_hashes) != 100
            or {row["clip"] for row in condition_rows} != set(reference_hashes)
            or not all(row["full_window"] is True for row in condition_rows)):
        raise ValueError("wrong fixed full-window evaluation population")
    evaluator_sources = {name: record["sha256"] for name, record in contract["evaluator_sources"].items()}
    training_sources = {name: record["sha256"] for name, record in contract["training_sources"].items()}
    for group in ("evaluator_sources", "training_sources"):
        for name, record in contract[group].items():
            verified(record, name)
    paths = {name: verified(record, name) for name, record in cell.items()}
    metadata = json.loads(paths["metadata"].read_text())
    ledger = json.loads(paths["ledger"].read_text())
    expected_metadata = {
        "schema_version": "paired_eval_output/1", "task": "Climb-Tracking-Flat-Unitree-G1",
        "checkpoint_sha256": cell["checkpoint"]["sha256"],
        "conditions_sha256": contract["conditions"]["sha256"],
        "clips_sha256": conditions["panel_txt_sha256"],
        "evaluator_sha256": contract["evaluator"]["sha256"],
        "selected_reference_sha256": reference_hashes, "common_reference_sha256": reference_hashes,
        "nominal": conditions["nominal"], "joint_noise": conditions["joint_noise"],
        "nconmax_per_world": conditions["nconmax_per_world"], "worlds": 2800,
        "full_window_worlds": 2800, "source_sha256": evaluator_sources,
        "software_versions": contract["software_versions"],
    }
    if contract.get("schema_version") == "relative_confirmation_contract/1":
        from eval_relative_confirmation import adapter_record
        verified(contract["evaluator_adapter"], "evaluator adapter")
        adapter = adapter_record()
        if ({key: adapter[key] for key in ("path", "sha256")} != contract["evaluator_adapter"]
                or metadata.get("execution_adapter") != adapter):
            raise ValueError("evaluation adapter identity mismatch")
    for key, value in expected_metadata.items():
        if metadata.get(key) != value:
            raise ValueError(f"evaluation metadata mismatch: {key}")
    for key, path in (("checkpoint", paths["checkpoint"]), ("output", paths["csv"]),
                      ("conditions", conditions_path)):
        if not path_matches(metadata.get(key), path):
            raise ValueError(f"evaluation path mismatch: {key}")
    expected_ledger = {
        "iteration": iteration, "relative_policy_arm": arm, "relative_policy_stage": "confirmation",
        "num_envs": 512, "profile": profiles["arms"][arm],
        "profile_contract_sha256": contract["profiles"]["sha256"],
        "source_hashes_at_launch": training_sources,
        "training_entrypoint_sha256": contract["training_entrypoint"]["sha256"],
    }
    for key, value in expected_ledger.items():
        if ledger.get(key) != value:
            raise ValueError(f"training ledger mismatch: {key}")
    checkpoint_link = ledger["checkpoint"]
    if (not path_matches(checkpoint_link.get("path"), paths["checkpoint"])
            or checkpoint_link.get("sha256") != cell["checkpoint"]["sha256"]):
        raise ValueError("evaluated checkpoint is not linked to this training ledger")
    segment = ledger["segment"]
    selected = profiles["arms"][arm]
    expected_segment = {"sampler_seed": seed, "training_seed": seed, "horizon_steps": 50,
                        "unit_table_sha256": profiles["unit_table_sha256"],
                        **{key: selected[key] for key in ("mode", "rank", "exploration_ratio",
                                                          "difficulty_power", "progress_floor")},
                        **{key: profiles["common"][key] for key in ("progress_window",
                              "max_unit_probability", "max_clip_probability")}}
    if any(segment.get(key) != value for key, value in expected_segment.items()):
        raise ValueError("training sampler profile/seed/support mismatch")
    if arm == "R" and (segment.get("relative_progress_factor") != 2.0
                       or segment.get("allocation_protocol") != "relative_progress_alp/1"):
        raise ValueError("relative allocator identity mismatch")
    for key in ("invalid_start_count", "invalid_reference_frame_count", "censored_resets"):
        if segment[key] != 0:
            raise ValueError(f"training ledger has nonzero {key}")
    for key in ("startup_randomization_sha256", "initial_state_sha256"):
        value = metadata.get(key)
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError(f"missing paired randomization identity: {key}")
    return {"csv": str(paths["csv"]), "csv_sha256": cell["csv"]["sha256"],
            "arm": arm, "seed": seed, "iteration": iteration,
            "startup_randomization_sha256": metadata["startup_randomization_sha256"],
            "initial_state_sha256": metadata["initial_state_sha256"]}


def verify_pairing(cells: list[dict]) -> None:
    """Require every U/A/R/D seed/checkpoint and identical evaluation randomization."""
    expected = {(arm, seed, iteration) for arm in ARMS for seed in SEEDS for iteration in ITERATIONS}
    actual = {(cell["arm"], cell["seed"], cell["iteration"]) for cell in cells}
    if len(cells) != 48 or actual != expected:
        raise ValueError("incomplete or duplicate four-arm, three-seed, four-checkpoint panel")
    for key in ("startup_randomization_sha256", "initial_state_sha256"):
        if len({cell[key] for cell in cells}) != 1:
            raise ValueError(f"evaluation pairing mismatch: {key}")
