#!/usr/bin/env python3
"""Prepare and execute the preselected DFRP fixed-policy validation.

GPU work waits for an E4 terminal decision and the continuation lock. Historical
reference identities must be recovered exactly before either cell is evaluated.
An E4 manipulation failure ends E4, but does not invalidate this independent E3
exploratory reference comparison requested by the user.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import sys
import time
from pathlib import Path

from analyze_dfrp_policy_validation import analyze
from eval_paired_v2 import DEFAULT_PHASES, build_conditions, sha256_file
from restore_dfrp_validation_payload import MANIFEST, require_hash
from run_e4_confirmation import OUT as E4_OUT
from run_e4_confirmation import PYTHON, ROOT, gated, run_dir, verify_seal, write_once

OUT = ROOT / "reports/dfrp_policy_validation_2026-09-05"
RECOVERY = ROOT / "bank/dfrp_validation_recovery"


def artifact(path: Path) -> dict:
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}


def prepare() -> Path:
    verify_seal()
    manifest = json.loads(MANIFEST.read_text())
    clips = manifest["clips"]
    if len(clips) != 26 or sum(r["flagged"] for r in clips) != 22:
        raise ValueError("historical DFRP panel differs from 22 repairs + 4 controls")
    training = ROOT / "bank/tiers/tier_800.txt"
    training_names = {s.strip() for s in training.read_text().splitlines()
                      if s.strip() and not s.startswith("#")}
    metadata = [{"clip": r["name"], "frames": r["original"]["frames"],
                 "fps": r["original"]["fps"]} for r in clips]
    conditions = build_conditions(
        metadata, [float(s) for s in DEFAULT_PHASES.split(",")], 4, 3.0,
        20260905, 20260906, 0.05, False, 70,
    )
    conditions_path = OUT / "conditions.json"
    write_once(conditions_path, conditions)
    list_path = OUT / "clips.txt"
    content = "".join(f"{r['name']}\n" for r in clips)
    if list_path.exists() and list_path.read_text() != content:
        raise ValueError("refusing changed clip list")
    if not list_path.exists():
        list_path.write_text(content)
    design = {
        "schema_version": "dfrp_policy_validation_design/1",
        "classification": "exploratory design written before policy endpoints",
        "checkpoint_selection": "Exact Uniform seed 1, final iteration 3999",
        "conditions": artifact(conditions_path), "clip_list": artifact(list_path),
        "curated_manifest": artifact(MANIFEST), "training_clips": artifact(training),
        "evaluator_sha256": sha256_file(ROOT / "tools/eval_paired_v2.py"),
        "analyzer_sha256": sha256_file(ROOT / "tools/analyze_dfrp_policy_validation.py"),
        "bootstrap": {"unit": "clip", "replicates": 10000, "seed": 20260905},
        "common_fidelity_reference": "raw historical bank in both cells",
        "claims": "Windowed fixed-policy reference effect; not full-clip or training benefit.",
        "clips": [{"clip": r["name"], "qualified_repair": r["flagged"],
                   "training_overlap": r["name"] in training_names,
                   "raw_sha256": r["original"]["sha256"],
                   "repaired_sha256": r["training_motion"]["sha256"],
                   "reference_distortion": r["repair"]["fidelity"] if r["flagged"] else None}
                  for r in clips],
    }
    path = OUT / "design.json"
    write_once(path, design)
    return path


def terminal_e4() -> str | None:
    seed1 = E4_OUT / "seed1/manipulation_result.json"
    if not seed1.exists():
        return None
    record = json.loads(seed1.read_text())
    if record["status"] == "not_tested":
        return "seed1_manipulation_not_tested"
    all_seeds = E4_OUT / "manipulation_all_seeds.json"
    if all_seeds.exists() and json.loads(all_seeds.read_text())["status"] == "not_tested":
        return "all_seed_manipulation_not_tested"
    if (E4_OUT / "result.json").exists():
        return "confirmation_analysis_complete"
    return None


def verify_payload(design: dict) -> tuple[Path, Path]:
    receipt = json.loads((RECOVERY / "recovery_result.json").read_text())
    if (receipt.get("pass") is not True or receipt.get("raw_verified") != 26
            or receipt.get("repaired_verified") != 26
            or receipt.get("manifest_sha256") != design["curated_manifest"]["sha256"]):
        raise ValueError("DFRP historical payload recovery did not pass")
    raw, repaired = Path(receipt["raw_bank"]), Path(receipt["repaired_bank"])
    for row in design["clips"]:
        require_hash(raw / f"{row['clip']}.npz", row["raw_sha256"])
        require_hash(repaired / f"{row['clip']}.npz", row["repaired_sha256"])
    return raw, repaired


def evaluate_cells(design_path: Path, checkpoint: Path, raw: Path, repaired: Path) -> None:
    design = json.loads(design_path.read_text())
    write_once(OUT / "execution_binding.json", {
        "design_sha256": sha256_file(design_path),
        "checkpoint": str(checkpoint), "checkpoint_sha256": sha256_file(checkpoint),
        "raw_bank": str(raw), "repaired_bank": str(repaired),
        "classification": "pre-evaluation identity binding; no policy results",
    })
    for arm, bank in (("raw", raw), ("repaired", repaired)):
        output = OUT / f"{arm}.csv"
        if output.exists() or Path(f"{output}.meta.json").exists():
            raise ValueError(f"existing evaluation; inspect before retry: {output}")
        gated([
            str(PYTHON), "tools/eval_paired_v2.py", "--checkpoint", str(checkpoint),
            "--clips", design["clip_list"]["path"], "--bank", str(bank),
            "--common-reference-bank", str(raw),
            "--conditions", design["conditions"]["path"], "--episodes", "4",
            "--window", "3", "--seed", "20260905", "--joint-noise-seed", "20260906",
            "--joint-noise", "0.05", "--nconmax", "70", "--out", str(output),
        ], OUT / f"{arm}.log", 1)
    result = analyze(design_path, OUT / "raw.csv", OUT / "repaired.csv")
    write_once(OUT / "result.json", result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--wait-e4", action="store_true")
    parser.add_argument("--source-repo", type=Path)
    args = parser.parse_args()
    design_path = prepare()
    if args.prepare_only:
        print(f"Prepared {design_path}; no simulator started", flush=True)
        return 0
    if args.source_repo is None:
        parser.error("--source-repo is required for payload recovery")
    lock = (OUT / ".validation.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    while (status := terminal_e4()) is None:
        if not args.wait_e4:
            raise ValueError("E4 still active; refusing competing GPU work")
        print("WAIT E4 terminal decision before independent DFRP evaluation", flush=True)
        time.sleep(30)
    # Keep the E4 lock until this workflow ends, preventing overlapping restarts.
    e4_lock = (E4_OUT / ".continuation.lock").open("a")
    while True:
        try:
            fcntl.flock(e4_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if not args.wait_e4:
                raise
            time.sleep(30)
    write_once(OUT / "e4_terminal_status.json", {"status": status})
    if not (RECOVERY / "recovery_result.json").exists():
        gated([
            str(PYTHON), "tools/restore_dfrp_validation_payload.py",
            "--source-repo", str(args.source_repo.resolve()),
            "--out", str(RECOVERY), "--device", "cuda:0",
        ], OUT / "cuda_recovery.log", 1)
    raw, repaired = verify_payload(json.loads(design_path.read_text()))
    checkpoint = run_dir(1, "G1") / "model_3999.pt"
    evaluate_cells(design_path, checkpoint, raw, repaired)
    print("DONE exploratory DFRP fixed-policy comparison", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
