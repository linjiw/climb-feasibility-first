#!/usr/bin/env python3
"""Describe fixed-grid efficiency only after the original campaign verifies."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

ITERATIONS = (1000, 2000, 3000, 3999)
SEEDS = (21, 22, 23)
ARMS = ("U", "A", "R", "D")
TRANSITIONS = (np.array(ITERATIONS) + 1) * 512 * 24


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def attainment(values: np.ndarray, target: float) -> dict:
    """Require attainment at this and every later observed checkpoint."""
    eligible = [i for i in range(4) if np.all(values[i:] >= target)]
    if not eligible:
        return {"status": "not_attained_on_observed_grid", "transitions": None,
                "budget_fraction": None}
    index = eligible[0]
    return {"status": "attained_at_first_observation" if index == 0 else "attained_on_observed_grid",
            "iteration": ITERATIONS[index], "transitions": int(TRANSITIONS[index]),
            "budget_fraction": float(TRANSITIONS[index] / TRANSITIONS[-1])}


def summarize(result: dict) -> dict:
    """Consume complete validated summaries; never change the primary decision."""
    if (result.get("status") not in ("positive", "negative_for_prespecified_effect", "inconclusive")
            or result.get("policy_endpoints_opened") is not True):
        raise ValueError("requires a valid completed original analysis")
    curves = result["learning_curves_descriptive"]
    if set(curves) != {str(i) for i in ITERATIONS}:
        raise ValueError("requires the four fixed checkpoints")
    for checkpoint in curves.values():
        if set(checkpoint) != set(ARMS):
            raise ValueError("requires all four arms")
    panels = {}
    for panel in ("feasible_hard", "all_panel"):
        values = {arm: np.asarray([curves[str(i)][arm][f"{panel}_per_seed"]
                                   for i in ITERATIONS], dtype=float) for arm in ARMS}
        if any(v.shape != (4, 3) or not np.isfinite(v).all()
               or ((v < 0) | (v > 1)).any() for v in values.values()):
            raise ValueError("requires finite four-checkpoint, three-seed scores in [0,1]")
        weights = np.diff(TRANSITIONS) / (TRANSITIONS[-1] - TRANSITIONS[0])
        areas = {arm: ((v[:-1] + v[1:]) * 0.5 * weights[:, None]).sum(axis=0)
                 for arm, v in values.items()}
        targets = values["U"][-1]
        panels[panel] = {
            "normalized_AULC_per_seed": {a: v.tolist() for a, v in areas.items()},
            "AULC_R_minus_U_per_seed": (areas["R"] - areas["U"]).tolist(),
            "paired_U_final_target": {
                str(seed): {"target": float(targets[j]),
                            "arms": {a: attainment(v[:, j], targets[j]) for a, v in values.items()}}
                for j, seed in enumerate(SEEDS)},
            "checkpoint_R_minus_U_per_seed": (values["R"] - values["U"]).tolist(),
        }
    original_area = result.get("AULC_R_minus_U_descriptive")
    if original_area is not None:
        expected = [original_area["paired_seed_deltas"][str(s)] for s in SEEDS]
        if not np.allclose(panels["feasible_hard"]["AULC_R_minus_U_per_seed"],
                           expected, atol=1e-12, rtol=0):
            raise ValueError("original and derived AULC disagree")
    return {"schema_version": "icra_efficiency_descriptive/1", "status": "complete",
            "classification": "exploratory secondary; no new confirmation decision",
            "original_primary_status": result["status"], "seed_order": list(SEEDS),
            "checkpoint_iterations": list(ITERATIONS), "training_transitions": TRANSITIONS.tolist(),
            "panels": panels,
            "limitations": [
                "Targets are each paired U seed's observed final score, not externally fixed thresholds.",
                "Attainment is sustained only at observed checkpoints; no interpolation or monotonicity assumption.",
                "First-observation attainment does not locate an earlier crossing; non-attainment has no finite ratio.",
                "AULC covers iterations 1000 through 3999 only; early training is unobserved.",
                "Checkpoints are saved after zero-indexed PPO updates; budget uses (iteration + 1) * 512 * 24.",
                "Three trained policies per arm remain the independent units; no efficiency significance claim.",
                "Bootstrap, target attainment and AULC cannot rescue the frozen primary decision."]}


def analyze_campaign(root: Path, contract_hash: str) -> dict:
    """Gate access, then reproduce the source-bound original analysis in place."""
    freeze = root / "reports/relative_progress_2026-09-05/confirmation_freeze"
    contract_path = freeze / "contract.json"
    if sha256(contract_path) != contract_hash:
        raise ValueError("contract hash differs")
    contract = json.loads(contract_path.read_text())
    if contract.get("status") != "frozen_before_confirmation":
        raise ValueError("requires frozen confirmation")
    campaign = freeze / "campaign"
    terminal_path = campaign / "terminal_status.json"
    if not terminal_path.exists():
        return {"status": "pending", "policy_endpoints_opened": False,
                "reason": "original campaign has no terminal result", "contract_sha256": contract_hash}
    terminal = json.loads(terminal_path.read_text())
    if terminal.get("status") != "completed":
        return {"status": "unavailable", "policy_endpoints_opened": False,
                "original_terminal": terminal, "contract_sha256": contract_hash}
    # Check all bound source bytes before importing the original verifier.
    inventory = contract["runtime_inventory"]
    inventory_path = Path(inventory["path"])
    if sha256(inventory_path) != inventory["sha256"]:
        raise ValueError("inventory changed")
    for name, digest in json.loads(inventory_path.read_text())["files"].items():
        if sha256(Path(name)) != digest:
            raise ValueError(f"bound runtime source changed: {name}")
    source = contract["analysis_sources"]["analyze_relative_campaign.py"]
    if Path(source["path"]).resolve() != root / "tools/analyze_relative_campaign.py":
        raise ValueError("contract binds another analyzer")
    sys.path[:0] = [str(root / "tools"), str(root)]
    from analyze_relative_campaign import analyze
    manifest = campaign / "campaign_manifest.json"
    if json.loads(manifest.read_text())["contract"] != {"path": str(contract_path), "sha256": contract_hash}:
        raise ValueError("campaign contract cross-link differs")
    reproduced = analyze(manifest)
    saved_path = campaign / "analysis.json"
    if reproduced != json.loads(saved_path.read_text()):
        raise ValueError("original campaign analysis does not reproduce")
    if "AULC_R_minus_U_descriptive" not in reproduced:
        raise ValueError("original campaign omits the fixed AULC summary")
    return {**summarize(reproduced), "policy_endpoints_opened": True,
            "contract_sha256": contract_hash, "original_analysis_sha256": sha256(saved_path),
            "manifest_sha256": sha256(manifest), "tool_sha256": sha256(Path(__file__))}


def synthetic() -> dict:
    curves = {str(i): {a: {f"{p}_per_seed": [v] * 3 for p in ("feasible_hard", "all_panel")}
                       for a, v in (("U", u), ("A", u), ("R", r), ("D", u))}
              for i, u, r in zip(ITERATIONS, (0.2, 0.4, 0.5, 0.6), (0.4, 0.6, 0.65, 0.7))}
    return summarize({"status": "inconclusive", "policy_endpoints_opened": True,
                      "learning_curves_descriptive": curves})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--campaign-root", type=Path)
    parser.add_argument("--contract-sha256")
    parser.add_argument("--wait-seconds", type=int, default=0,
                        help="wait for original terminal result; never launch or retry scientific jobs")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.wait_seconds < 0 or (args.synthetic and args.wait_seconds):
        parser.error("wait must be nonnegative and applies only to a real campaign")
    if args.out.exists():
        parser.error("output already exists")
    if args.synthetic:
        result = {**synthetic(), "classification": "synthetic validation only",
                  "policy_endpoints_opened": False}
    else:
        if args.campaign_root is None or args.contract_sha256 is None:
            parser.error("real analysis requires --campaign-root and --contract-sha256")
        source_hash = sha256(Path(__file__))
        terminal = args.campaign_root / "reports/relative_progress_2026-09-05/confirmation_freeze/campaign/terminal_status.json"
        deadline = time.monotonic() + args.wait_seconds
        if args.wait_seconds and not terminal.exists():
            print("Waiting for original campaign terminal; no policy endpoints opened", flush=True)
        while not terminal.exists() and time.monotonic() < deadline:
            time.sleep(min(30, max(0, deadline - time.monotonic())))
        if sha256(Path(__file__)) != source_hash:
            raise ValueError("postprocessor source changed while queued")
        result = analyze_campaign(args.campaign_root.resolve(), args.contract_sha256)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({k: result[k] for k in ("status", "policy_endpoints_opened")}))


if __name__ == "__main__":
    main()
