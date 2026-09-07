#!/usr/bin/env python3
"""Authenticate H1 evaluation cells against already verified training records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from eval_gate_development import verify_inputs
from eval_physics_development import sha256

RUNTIME_PATHS = (
    "climb/commands.py", "climb/env_cfg.py", "climb/motion_bank.py", "climb/contact_timing.py",
    "mjlab-1.6.0/src/mjlab/envs/manager_based_rl_env.py",
    "mjlab-1.6.0/src/mjlab/tasks/tracking/mdp/commands.py",
)
PAIR_FIELDS = ("startup_randomization_sha256", "initial_state_sha256")


def record(path: Path) -> dict:
    return {"path": str(path.resolve()), "sha256": sha256(path)}


def verified(entry: dict) -> Path:
    if set(entry) != {"path", "sha256"}:
        raise ValueError("artifact record must contain path and hash")
    path = Path(entry["path"]).resolve()
    if sha256(path) != entry["sha256"]:
        raise ValueError("artifact content changed")
    return path


def expectations(design: dict, training: dict, arm: str, seed: int, iteration: int) -> dict:
    """Build expectations from bound inputs and an authenticated training result.

    This helper does not establish the training result's authenticity; the caller
    must first run the appropriate complete training verifier for every arm/seed.
    """
    if training["status"] != "gate_training_pass" or training["admission"] != arm or training["seed"] != seed:
        raise ValueError("wrong authenticated training identity")
    links = [row for row in training["checkpoints"] if row["iteration"] == iteration]
    if len(links) != 1:
        raise ValueError("evaluated checkpoint absent from verified training")
    args = design["evaluator_arguments"]
    root = Path(design["gate_worktree"])
    conditions = json.loads(verified(record(Path(args["conditions"]))).read_text())
    clips = Path(args["clips"]).read_text().splitlines()
    references = {name: sha256(Path(args["bank"]) / f"{name}.npz") for name in clips}
    contract = json.loads(verified(design["gate_contract"]).read_text())
    sources = {}
    for name in RUNTIME_PATHS:
        source = (root / name).resolve()
        if str(source) not in contract["sources"] or sha256(source) != contract["sources"][str(source)]:
            raise ValueError("evaluator runtime is outside the bound training inventory")
        sources[name] = contract["sources"][str(source)]
    metadata = {
        "schema_version": "paired_eval_output/1", "task": "Climb-Tracking-Flat-Unitree-G1",
        "checkpoint_sha256": links[0]["checkpoint"]["sha256"], "device": args["device"],
        "clips_sha256": sha256(Path(args["clips"])), "conditions_sha256": sha256(Path(args["conditions"])),
        "selected_reference_sha256": references, "common_reference_sha256": references,
        "evaluator_sha256": contract["sources"][str((root / "tools/eval_paired_v2.py").resolve())],
        "source_sha256": sources, "software_versions": contract["software_versions"],
        "nominal": args["nominal"], "joint_noise": args["joint_noise"],
        "nconmax_per_world": args["nconmax"], "worlds": len(conditions["conditions"]),
        "full_window_worlds": sum(c["full_window"] for c in conditions["conditions"]),
    }
    identity = {k: training[k] for k in ("admission", "seed", "smoke", "num_envs", "contract_sha256", "configuration_sha256")}
    identity["iteration"] = iteration
    return {"identity": identity, "metadata": metadata,
            "checkpoint": links[0]["checkpoint"], "ledger": links[0]["ledger"],
            "paths": {"checkpoint": links[0]["checkpoint"]["path"], "conditions": args["conditions"],
                      "clips": args["clips"], "bank": args["bank"], "common_reference_bank": args["common_reference_bank"]}}


def verify_cell(cell: dict, expected: dict) -> dict:
    """Check exact training links, runtime/condition metadata and pairing hashes."""
    if set(cell) != {"csv", "metadata", "checkpoint", "ledger"}:
        raise ValueError("evaluation cell has missing or extra artifact records")
    for name in ("checkpoint", "ledger"):
        if cell[name] != expected[name]:
            raise ValueError("cell not linked to authenticated training checkpoint/ledger")
    paths = {name: verified(value) for name, value in cell.items()}
    ledger = json.loads(paths["ledger"].read_text())
    if any(ledger.get(k) != v for k, v in expected["identity"].items()):
        raise ValueError("training ledger identity/configuration mismatch")
    if ledger.get("checkpoint_sha256") != cell["checkpoint"]["sha256"]:
        raise ValueError("checkpoint hash does not match training ledger")
    for key in ("invalid_start_count", "invalid_reference_frame_count", "censored_resets"):
        if ledger["segment"].get(key) != 0:
            raise ValueError("invalid or censored training event")
    metadata = json.loads(paths["metadata"].read_text())
    if any(metadata.get(k) != v for k, v in expected["metadata"].items()):
        raise ValueError("evaluation provenance differs from bound expectations")
    expected_paths = dict(expected["paths"], output=str(paths["csv"]))
    for key, value in expected_paths.items():
        if not isinstance(metadata.get(key), str) or Path(metadata[key]).resolve() != Path(value).resolve():
            raise ValueError("evaluation input/output path mismatch")
    for name in PAIR_FIELDS:
        if not isinstance(metadata.get(name), str) or re.fullmatch(r"[0-9a-f]{64}", metadata[name]) is None:
            raise ValueError("missing or malformed paired initial-state identity")
    identity = expected["identity"]
    return {"arm": identity["admission"], "seed": identity["seed"], "iteration": identity["iteration"],
            "csv": str(paths["csv"]), "csv_sha256": cell["csv"]["sha256"],
            "metadata": str(paths["metadata"]), **{k: metadata[k] for k in PAIR_FIELDS}}


def verify_pairing(cells: list[dict], grid: set[tuple]) -> None:
    identities = [(c["arm"], c["seed"], c["iteration"]) for c in cells]
    if len(cells) != len(grid) or set(identities) != grid:
        raise ValueError("missing or duplicate evaluation grid cell")
    for path in ("csv", "metadata"):
        if len({c[path] for c in cells}) != len(cells):
            raise ValueError("evaluation artifacts reused between cells")
    for field in PAIR_FIELDS:
        if len({c[field] for c in cells}) != 1:
            raise ValueError("evaluation startup/initial states are not paired")


def development(run: Path) -> dict:
    """Exercise the verifier on the authenticated seed-81 CPU smoke only."""
    design_path = run / "design.json"
    design, training = verify_inputs(design_path, sha256(design_path))
    cells = []
    for arm in ("on", "off"):
        expected = expectations(design, training[arm], arm, 81, 19)
        cell = {"csv": record(run / arm / "evaluation.csv"),
                "metadata": record(run / arm / "evaluation.csv.meta.json"),
                "checkpoint": expected["checkpoint"], "ledger": expected["ledger"]}
        receipt = json.loads((run / arm / "receipt.json").read_text())
        for key in ("csv", "metadata"):
            if receipt["artifacts"][Path(cell[key]["path"]).name] != cell[key]["sha256"]:
                raise ValueError("development receipt content mismatch")
        cells.append(verify_cell(cell, expected))
    verify_pairing(cells, {(a, 81, 19) for a in ("on", "off")})
    return {"status": "h1_development_cell_provenance_pass", "classification": "measured CPU provenance checks only",
            "cells": cells, "full_training_enabled": False, "confirmation_endpoints_opened": False,
            "production_manifest_ingestion_enabled": False, "verifier_sha256": sha256(Path(__file__))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development-run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = development(args.development_run)
    with args.out.open("x") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "cells"}))
