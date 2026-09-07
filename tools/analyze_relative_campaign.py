#!/usr/bin/env python3
"""Gate a complete prospective R3 campaign before parsing any policy outcomes."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re
import sys

import numpy as np
import torch

from analyze_relative_policy import aggregate_rows, analyze_scores, seed_summary
from analyze_relative_cost import execution_cost
from check_relative_progress_probe import sha256
from continue_relative_progress import verify_study
from relative_policy_provenance import ARMS, ITERATIONS, SEEDS, verified, verify_cell, verify_pairing
from relative_policy_secondaries import paired_secondary
from run_relative_failure_calibration import verify_calibration
from climb.relative_progress import RelativeProgressSampler
from climb.segment_runtime import SegmentSampler


class NotTested(ValueError):
    """A complete manipulation result fails a prospective scientific gate."""


def verify_training(run: dict, contract: dict, contract_hash: str, *, arm: str, seed: int) -> dict:
    """Replay all 41 sampler states, not only the four evaluated checkpoints."""
    log = verified(run["execution_log"], "training execution log").read_text()
    cost = execution_cost(log)
    if cost["status"] != "completed":
        raise ValueError("confirmation training has no successful execution terminal")
    prefix = "[INFO] Logging experiment in directory: "
    directories = [Path(line[len(prefix):]).resolve() for line in log.splitlines() if line.startswith(prefix)]
    seeds = re.findall(r"^\[INFO\] Training with: device=cuda:0, seed=(\d+), rank=0$", log, re.MULTILINE)
    parents = {Path(entry["checkpoint"]["path"]).resolve().parent for entry in run["snapshots"]}
    if len(directories) != 1 or set(directories) != parents or seeds != [str(seed)]:
        raise ValueError("execution log belongs to a different training run or seed")
    profiles = json.loads(verified(contract["profiles"], "profiles").read_text())
    selected = profiles["arms"][arm]
    manifest = verified(contract["unit_table"], "unit table")
    if json.loads(manifest.read_text())["unit_table_sha256"] != profiles["unit_table_sha256"]:
        raise ValueError("profile and campaign unit tables differ")
    cls = RelativeProgressSampler if arm == "R" else SegmentSampler
    extra = {"relative_factor": 2.0} if arm == "R" else {}
    sampler = cls(manifest, mode=selected["mode"], seed=seed, rank=selected["rank"],
                  exploration_ratio=selected["exploration_ratio"], difficulty_power=selected["difficulty_power"],
                  progress_window=10, progress_floor=selected["progress_floor"],
                  max_unit_probability=0.05, max_clip_probability=0.25, **extra)
    sources = {name: record["sha256"] for name, record in contract["training_sources"].items()}
    for name, record in contract["training_sources"].items():
        verified(record, name)
    snapshots = []
    checkpoint_links = {}
    for entry in run["snapshots"]:
        if set(entry) != {"ledger", "checkpoint", "sampler"}:
            raise ValueError("training snapshot must bind ledger, checkpoint and sampler")
        paths = {key: verified(record, key) for key, record in entry.items()}
        ledger = json.loads(paths["ledger"].read_text())
        iteration = ledger["iteration"]
        expected = {"relative_policy_arm": arm, "relative_policy_stage": "confirmation", "num_envs": 512,
                    "profile": selected, "profile_contract_sha256": contract["profiles"]["sha256"],
                    "campaign_contract_sha256": contract_hash, "source_hashes_at_launch": sources,
                    "training_entrypoint_sha256": contract["training_entrypoint"]["sha256"]}
        if contract.get("schema_version") == "relative_confirmation_contract/1":
            expected["configuration_sha256"] = contract["configuration_sha256"][arm][str(seed)]
        if any(ledger.get(key) != value for key, value in expected.items()):
            raise ValueError("training snapshot identity/source/frozen-contract mismatch")
        if (Path(ledger["checkpoint"]["path"]).resolve() != paths["checkpoint"]
                or ledger["checkpoint"]["sha256"] != entry["checkpoint"]["sha256"]):
            raise ValueError("training snapshot checkpoint cross-link mismatch")
        segment = ledger["segment"]
        expected_segment = {"training_seed": seed, "sampler_seed": seed, "horizon_steps": 50,
                            "unit_table_sha256": profiles["unit_table_sha256"],
                            **{key: selected[key] for key in ("mode", "rank", "exploration_ratio",
                                                              "difficulty_power", "progress_floor")},
                            **{key: profiles["common"][key] for key in ("progress_window",
                                              "max_unit_probability", "max_clip_probability")}}
        if any(segment.get(key) != value for key, value in expected_segment.items()):
            raise ValueError("training seed/support mismatch")
        if arm == "R" and (segment.get("relative_progress_factor") != 2.0
                           or segment.get("allocation_protocol") != "relative_progress_alp/1"):
            raise ValueError("relative allocator identity mismatch")
        state = torch.load(paths["sampler"], map_location="cpu", weights_only=True)
        if state["iteration"] != iteration:
            raise ValueError("sampler iteration mismatch")
        sampler.load_state_dict(state["sampler"])
        if not torch.equal(torch.tensor(segment["probabilities"], dtype=torch.float64), sampler.probabilities):
            raise ValueError("training probabilities do not replay")
        if any(segment[key] != 0 for key in ("invalid_start_count", "invalid_reference_frame_count", "censored_resets")):
            raise ValueError("training has invalid/censored events")
        if (segment["completed_trials"] != int(sampler.lifetime_attempts.sum())
                or segment["failed_trials"] != int(sampler.lifetime_failures.sum())):
            raise ValueError("training event accounting mismatch")
        concentration = sampler.concentration()
        snapshots.append({"iteration": iteration, "tv": sampler.adaptation_total_variation(),
                          "effective_units": concentration.entropy_effective_units,
                          "saturation": sampler.saturation_fraction(), "sampler_clock": sampler.clock,
                          "completed_trials": int(sampler.lifetime_attempts.sum())})
        if iteration in checkpoint_links:
            raise ValueError("duplicate training iteration")
        checkpoint_links[iteration] = entry
    snapshots.sort(key=lambda row: row["iteration"])
    if [row["iteration"] for row in snapshots] != [*range(0, 4000, 100), 3999]:
        raise ValueError("missing training snapshots")
    if any(current["sampler_clock"] <= previous["sampler_clock"]
           or current["completed_trials"] <= previous["completed_trials"]
           for previous, current in zip(snapshots, snapshots[1:])):
        raise ValueError("training clock/trials do not advance between checkpoints")
    post = snapshots[4:]
    mean_tv = float(np.mean([row["tv"] for row in post]))
    passed = min(row["effective_units"] for row in post) >= 12
    if arm == "U":
        passed &= max(row["tv"] for row in snapshots) <= 0.01
    elif arm == "R":
        passed &= 0.05 <= mean_tv <= 0.15 and post[-1]["saturation"] < 0.9
    elif arm == "D":
        passed &= mean_tv >= 0.05 and post[-1]["saturation"] < 0.9
    # A is the predeclared absolute-floor comparator: weak adaptation is a
    # descriptive outcome, not grounds to remove it or suppress the primary R-U.
    if not passed:
        raise NotTested(f"{arm} seed {seed}: complete manipulation gate failed")
    return {"mean_tv": mean_tv, "snapshots": snapshots, "checkpoint_links": checkpoint_links,
            "execution_cost": cost}


def preflight(manifest_path: Path) -> tuple[dict, dict, list[dict], dict]:
    """Validate every prerequisite, training run and evaluation cell before CSV parsing."""
    manifest = json.loads(manifest_path.read_text())
    if manifest["schema_version"] != "relative_campaign_manifest/1":
        raise ValueError("unsupported campaign manifest")
    contract_path = verified(manifest["contract"], "prospective contract")
    contract_hash = manifest["contract"]["sha256"]
    contract = json.loads(contract_path.read_text())
    if contract.get("status") != "frozen_before_confirmation":
        raise ValueError("campaign has no prospective confirmation freeze")
    if contract.get("schema_version") == "relative_confirmation_contract/1":
        from relative_confirmation_setup import verify_contract
        verify_contract(contract_path, contract_hash)
    profiles = json.loads(verified(contract["profiles"], "profiles").read_text())
    if profiles["confirmation"]["enabled"] is not True:
        raise ValueError("confirmation is disabled")
    analyzer_sources = contract["analysis_sources"]
    for name in ("analyze_relative_campaign.py", "analyze_relative_policy.py", "relative_policy_provenance.py",
                 "relative_policy_secondaries.py", "analyze_relative_cost.py"):
        path = verified(analyzer_sources[name], name)
        if path != Path(__file__).with_name(name).resolve():
            raise ValueError("contract binds another analyzer implementation")
    for seed in (11, 12):
        entry = contract["relative_replication"][str(seed)]
        decision = verified(entry["decision"], f"relative seed {seed}")
        if decision != (Path(entry["study_dir"]) / "long_result.json").resolve():
            raise ValueError("relative prerequisite decision cross-link mismatch")
        if verify_study(Path(entry["study_dir"]), seed)["status"] != "pass":
            raise NotTested("relative manipulation prerequisite failed")
    for seed in (31, 32):
        entry = contract["failure_calibration"][str(seed)]
        saved = json.loads(verified(entry["decision"], f"D seed {seed}").read_text())
        execution = json.loads(verified(entry["execution_design"], "D execution design").read_text())
        parents = {Path(name).parent for name in saved["bindings"]}
        if len(parents) != 1 or verify_calibration(parents.pop(), seed, execution["sources"]) != saved:
            raise ValueError("D calibration does not reproduce")
        if saved["status"] != "calibration_pass":
            raise NotTested("D calibration prerequisite failed")
    if set(manifest["arms"]) != ARMS:
        raise ValueError("campaign requires all four arms")
    cells = []
    manipulation = {}
    for arm in sorted(ARMS):
        if set(manifest["arms"][arm]) != {str(seed) for seed in SEEDS}:
            raise ValueError("campaign requires exactly the three fresh paired seeds")
        for seed in sorted(SEEDS):
            run = manifest["arms"][arm][str(seed)]
            checked = verify_training(run, contract, contract_hash, arm=arm, seed=seed)
            manipulation[f"{arm}:{seed}"] = {key: value for key, value in checked.items() if key != "checkpoint_links"}
            if set(run["evaluations"]) != {str(iteration) for iteration in ITERATIONS}:
                raise ValueError("missing or extra evaluation checkpoints")
            for iteration in sorted(ITERATIONS):
                cell = run["evaluations"][str(iteration)]
                for key in ("checkpoint", "ledger"):
                    if cell[key] != checked["checkpoint_links"][iteration][key]:
                        raise ValueError("evaluated cell is not linked to the verified training snapshot")
                cells.append(verify_cell(cell, contract, arm=arm, seed=seed, iteration=iteration))
    verify_pairing(cells)
    # Verify the reference-defined strata before opening any endpoint CSV.
    strata_path = verified(contract["strata"], "reference strata")
    with strata_path.open() as handle:
        strata = list(csv.DictReader(handle))
    panel = json.loads(verified(contract["panel"], "panel").read_text())
    if (len(strata) != 100 or len({row["clip"] for row in strata}) != 100
            or {row["clip"] for row in strata} != set(panel["motion_sha256"])
            or sum(row["stratum"] == "feasible_hard_reference" for row in strata) != 25
            or any(row["stratum"] not in ("feasible_hard_reference", "feasible_remainder") for row in strata)):
        raise ValueError("invalid reference-defined strata")
    return contract, {row["clip"]: row["stratum"] for row in strata}, cells, manipulation


def analyze(manifest_path: Path) -> dict:
    opened = False
    try:
        contract, strata, cells, manipulation = preflight(manifest_path)
        clips = sorted(strata)
        hard = np.array([index for index, clip in enumerate(clips) if strata[clip] == "feasible_hard_reference"])
        conditions = json.loads(verified(contract["conditions"], "conditions").read_text())["conditions"]
        iterations = sorted(ITERATIONS)
        scores = {iteration: {arm: np.zeros((3, 100)) for arm in ARMS} for iteration in iterations}
        survival = {iteration: {arm: np.zeros((3, 100)) for arm in ARMS} for iteration in iterations}
        final_rows = {}
        for cell in cells:
            path = Path(cell["csv"])
            if sha256(path) != cell["csv_sha256"]:
                raise ValueError("CSV changed after complete provenance preflight")
            opened = True
            with path.open() as handle:
                rows = list(csv.DictReader(handle))
            if cell["iteration"] == 3999:
                final_rows[(cell["arm"], cell["seed"])] = rows
            index = sorted(SEEDS).index(cell["seed"])
            scores[cell["iteration"]][cell["arm"]][index] = aggregate_rows(rows, conditions, clips)
            # Identical liveness weighting with zeroed precision errors gives
            # survived-horizon fraction while preserving every failed condition.
            alive_rows = [{**row, "common_root_relative_mpkpe_m_mean": 0.0,
                           "common_anchor_orientation_error_rad_mean": 0.0} for row in rows]
            survival[cell["iteration"]][cell["arm"]][index] = aggregate_rows(alive_rows, conditions, clips)
        primary = analyze_scores(scores[3999], hard, manipulation_pass=True, provenance_pass=True)
        secondaries = {}
        for comparator in ("U", "A", "D"):
            secondaries[f"R_minus_{comparator}"] = {
                str(seed): paired_secondary(final_rows[("R", seed)], final_rows[(comparator, seed)],
                                            conditions, clips) for seed in sorted(SEEDS)}
        curves = {str(iteration): {arm: {"feasible_hard_per_seed": scores[iteration][arm][:, hard].mean(axis=1).tolist(),
                                       "all_panel_per_seed": scores[iteration][arm].mean(axis=1).tolist(),
                                       "survival_all_panel_per_seed": survival[iteration][arm].mean(axis=1).tolist()}
                                  for arm in sorted(ARMS)} for iteration in iterations}
        time_weights = np.diff(iterations) / (iterations[-1] - iterations[0])
        aulc = {}
        for arm in ARMS:
            stack = np.stack([scores[iteration][arm][:, hard].mean(axis=1) for iteration in iterations])
            aulc[arm] = ((stack[:-1] + stack[1:]) * 0.5 * time_weights[:, None]).sum(axis=0)
        return {**primary, "classification": "prospective matched simulation policy comparison",
                "policy_endpoints_opened": True, "manifest_sha256": sha256(manifest_path),
                "manipulation": manipulation, "learning_curves_descriptive": curves,
                "AULC_R_minus_U_descriptive": seed_summary(aulc["R"] - aulc["U"]),
                "AULC_scope": "normalized trapezoidal area from iteration 1000 to 3999 only",
                "per_clip_final_R_minus_U": {clip: (scores[3999]["R"] - scores[3999]["U"])[:, index].tolist()
                                             for index, clip in enumerate(clips)},
                "quality_and_work_descriptive": secondaries,
                "training_cost_descriptive": {
                    "per_run": {label: row["execution_cost"] for label, row in manipulation.items()},
                    "total_elapsed_gpu_hours": sum(row["execution_cost"]["elapsed_gpu_hours"] for row in manipulation.values()),
                    "scope": "12 confirmation training runs only; excludes development, evaluation, queue time and engineering",
                    "limitation": "elapsed wall time on a shared GPU; not utilization-adjusted time, isolated memory or energy"}}
    except Exception as exc:
        return {"status": "not_tested" if isinstance(exc, NotTested) else "invalid", "reason": str(exc),
                "policy_endpoints_opened": opened}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.manifest)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({key: result[key] for key in ("status", "policy_endpoints_opened")}))
    if result["status"] in ("invalid", "not_tested"):
        sys.exit(1)
