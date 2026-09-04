#!/usr/bin/env python3
"""Draft Phase-G analysis: manipulation and provenance gates, then G2 - G1.

Inputs are a hash-complete run manifest (per arm and seed: evaluator CSVs,
metadata, policy checkpoints, and sampler ledgers), the endpoint-blind
calibration design/result, and the sealed evaluation contract. The gates verify
the sampler manipulation and exact evaluation provenance before any endpoint
row is parsed. The tool fails closed when an input is missing. ``--synthetic``
exercises positive, null, inconclusive, and multiple not-tested branches.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

TRACKING_SCORE_SESOI = 0.02
SURVIVAL_SESOI = 0.05
TRACKING_SIGMA_P_M = 0.30
TRACKING_SIGMA_THETA_RAD = 0.40
TV_BAND = (0.05, 0.15)
MIN_ENTROPY_EFFECTIVE_UNITS = 12.0
MAX_SATURATION_FRACTION = 0.90
MAX_TOP1_PROBABILITY = 0.05
G1_MAX_TV = 0.01
UNIT_TABLE_SHA256 = "a52a668e5570c24e01a1af821164cbd19a38a3cd9007f245f78494ce11af9606"
WARMUP_ITERATION = 400
FINAL_ITERATION = 3999
AULC_ITERATIONS = (1000, 2000, 3000, 3999)
NONINFERIORITY_MARGIN = 0.10
QUALITY_METRICS = (
    "common_root_relative_mpkpe_m_mean",
    "common_anchor_orientation_error_rad_mean",
    "absolute_mechanical_work_per_actuator_j",
)
BOOTSTRAP_SEED = 20260910
BOOTSTRAP_DRAWS = 10_000
ARMS = ("G1", "G2")
RUN_MANIFEST_SCHEMA = "g_segment_run_manifest/1"
EVAL_OUTPUT_SCHEMA = "paired_eval_output/1"
EVALUATOR_PATH = Path(__file__).resolve().with_name("eval_paired_v2.py")
TRAINING_ENTRYPOINT_PATH = Path(__file__).resolve().with_name(
    "climb_segment_train.py"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verified_artifact(record: Any, label: str) -> Path:
    """Resolve and hash-check one ``{path, sha256}`` manifest record."""
    if not isinstance(record, dict) or set(record) != {"path", "sha256"}:
        raise ValueError(f"{label}: expected exact path/sha256 artifact record")
    path = Path(record["path"]).resolve()
    if not path.is_file():
        raise ValueError(f"{label}: missing artifact {path}")
    actual = sha256_file(path)
    if actual != record["sha256"]:
        raise ValueError(
            f"{label}: SHA-256 mismatch {actual} != {record['sha256']}"
        )
    return path


def verified_ledgers(run: dict[str, Any], label: str) -> list[dict[str, Any]]:
    """Read hash-bound sampler ledgers without touching evaluator endpoints."""
    records = run.get("ledgers")
    if not isinstance(records, list) or not records:
        raise ValueError(f"{label}: no hash-bound sampler ledgers")
    return [
        json.loads(verified_artifact(record, f"{label} ledger {index}").read_text())
        for index, record in enumerate(records)
    ]


def _average_ranks(values: np.ndarray) -> np.ndarray:
    """Return deterministic average-tie ranks for finite one-dimensional data."""
    if values.ndim != 1 or not bool(np.isfinite(values).all()):
        raise ValueError("rank input must be a finite one-dimensional array")
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(values.size, dtype=np.float64)
    start = 0
    while start < values.size:
        stop = start + 1
        while stop < values.size and values[order[stop]] == values[order[start]]:
            stop += 1
        ranks[order[start:stop]] = 0.5 * (start + stop - 1)
        start = stop
    return ranks


def _spearman_rho(left: np.ndarray, right: np.ndarray) -> float | None:
    """Return Spearman rho, or ``None`` when either ranking is constant."""
    if left.shape != right.shape or left.ndim != 1 or left.size < 3:
        raise ValueError("Spearman inputs must be same-length vectors with at least 3 rows")
    left_rank = _average_ranks(left)
    right_rank = _average_ranks(right)
    if np.ptp(left_rank) == 0.0 or np.ptp(right_rank) == 0.0:
        return None
    return float(np.corrcoef(left_rank, right_rank)[0, 1])


def exploratory_rank_agreement(manifest: dict[str, Any]) -> dict[str, Any]:
    """Compare ALP with failure and competence-frontier scores, without a gate.

    This diagnostic reads sampler telemetry only. It has no threshold and cannot
    alter the Phase-G verdict.
    """
    rows: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for seed, run in manifest["arms"]["G2"]["seeds"].items():
        ledgers = verified_ledgers(run, f"G2 seed {seed}")
        for ledger in sorted(ledgers, key=lambda item: int(item["iteration"])):
            iteration = int(ledger["iteration"])
            if iteration < WARMUP_ITERATION:
                continue
            segment = ledger["segment"]
            rates_raw = segment.get("conditional_success_rates")
            progress_raw = segment.get("learning_progress")
            if not isinstance(rates_raw, list) or not isinstance(progress_raw, list):
                missing.append({"seed": seed, "iteration": iteration})
                continue
            rates = np.asarray(rates_raw, dtype=np.float64)
            progress = np.asarray(progress_raw, dtype=np.float64)
            if (
                rates.shape != progress.shape
                or rates.ndim != 1
                or rates.size < 3
                or not bool(np.isfinite(rates).all())
                or not bool(np.isfinite(progress).all())
                or bool(((rates < 0.0) | (rates > 1.0)).any())
                or bool((progress < 0.0).any())
            ):
                raise ValueError(
                    f"G2 seed {seed} iteration {iteration}: malformed rank telemetry"
                )
            failure = 1.0 - rates
            competence_frontier = rates * (1.0 - rates)
            rows.append(
                {
                    "seed": seed,
                    "iteration": iteration,
                    "units": int(rates.size),
                    "rho_alp_failure": _spearman_rho(progress, failure),
                    "rho_alp_competence_frontier": _spearman_rho(
                        progress, competence_frontier
                    ),
                    "rho_failure_competence_frontier": _spearman_rho(
                        failure, competence_frontier
                    ),
                }
            )
    return {
        "classification": "exploratory sampler-only; no decision role",
        "status": "available" if rows and not missing else "incomplete",
        "rows": rows,
        "missing": missing,
    }


def _path_value_matches(value: Any, expected: Path) -> bool:
    """Compare a metadata path without raising on malformed JSON types."""
    return isinstance(value, str) and Path(value).resolve() == expected


def _artifact_digest(record: Any, name: str) -> Any:
    """Read a nested digest for reporting without trusting record types."""
    if not isinstance(record, dict):
        return None
    artifact = record.get(name)
    return artifact.get("sha256") if isinstance(artifact, dict) else None


def read_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open() as handle:
        rows = {row["condition_id"]: row for row in csv.DictReader(handle)}
    if not rows:
        raise ValueError(f"{path}: empty evaluator output")
    return rows


def validate_rows(rows: dict[str, dict[str, str]], conditions: dict[str, Any], label: str) -> None:
    expected = {row["condition_id"] for row in conditions["conditions"]}
    if set(rows) != expected:
        raise ValueError(f"{label}: condition set differs from the sealed manifest")
    if any(row["full_window"] not in ("True", "1", "true") for row in rows.values()):
        raise ValueError(f"{label}: a condition is not full-window")


def tracking_score(row: dict[str, str]) -> float:
    """Bound precision by observed horizon so early failure cannot look precise."""
    survival_fraction = min(
        max(float(row["survival_s"]) / float(row["actual_window_s"]), 0.0),
        1.0,
    )
    position = float(row["common_root_relative_mpkpe_m_mean"])
    orientation = float(row["common_anchor_orientation_error_rad_mean"])
    return survival_fraction * np.exp(
        -position / TRACKING_SIGMA_P_M
        -orientation / TRACKING_SIGMA_THETA_RAD
    )


def per_clip(
    rows: dict[str, dict[str, str]], clips: list[str], column: str
) -> np.ndarray:
    sums = {clip: [] for clip in clips}
    for row in rows.values():
        if row["clip"] in sums:
            value = (
                tracking_score(row)
                if column == "tracking_score"
                else float(row[column])
            )
            sums[row["clip"]].append(value)
    if any(not values for values in sums.values()):
        raise ValueError(f"column {column}: a requested clip has no conditions")
    return np.array([np.mean(sums[clip]) for clip in clips])


def hierarchical_bootstrap(
    matrix: np.ndarray, rng: np.random.Generator, draws: int
) -> dict[str, float]:
    """Seed-then-clip resampling of a seeds x clips effect matrix."""
    seeds, clips = matrix.shape
    stats = np.empty(draws)
    for index in range(draws):
        seed_index = rng.integers(0, seeds, size=seeds)
        clip_index = rng.integers(0, clips, size=clips)
        stats[index] = matrix[np.ix_(seed_index, clip_index)].mean()
    return {
        "point": float(matrix.mean()),
        "ci_low": float(np.percentile(stats, 2.5)),
        "ci_high": float(np.percentile(stats, 97.5)),
        "seeds": int(seeds),
        "clips": int(clips),
        "draws": int(draws),
    }


def load_calibration_contract(
    manifest: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    """Verify the endpoint-blind design/result files bound by the run manifest."""
    link = manifest.get("calibration")
    if not isinstance(link, dict) or set(link) != {
        "design_path", "design_sha256", "result_path", "result_sha256"
    }:
        raise ValueError("run manifest has no exact calibration file binding")
    design_path = Path(link["design_path"])
    result_path = Path(link["result_path"])
    if sha256_file(design_path) != link["design_sha256"]:
        raise ValueError("calibration design hash mismatch")
    if sha256_file(result_path) != link["result_sha256"]:
        raise ValueError("calibration result hash mismatch")
    design = json.loads(design_path.read_text())
    result = json.loads(result_path.read_text())
    if design.get("schema_version") != "g2_calibration_design/1":
        raise ValueError("unsupported calibration design")
    if (
        result.get("schema_version") != "g2_calibration_result/1"
        or result.get("status") != "ready_to_freeze"
        or result.get("design_sha256") != link["design_sha256"]
    ):
        raise ValueError("calibration result is not ready or bound to the design")
    selected = result.get("selected")
    candidates = design.get("candidates", [])
    if not isinstance(selected, dict) or selected not in candidates:
        raise ValueError("calibration result selected an undeclared candidate")
    hashes = {
        "design_sha256": link["design_sha256"],
        "result_sha256": link["result_sha256"],
    }
    return design, selected, hashes


def _contract_mismatches(
    segment: dict[str, Any], expected: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """Return exact telemetry mismatches without reading policy endpoints."""
    mismatches: dict[str, dict[str, Any]] = {}
    for key, wanted in expected.items():
        actual = segment.get(key)
        if isinstance(wanted, float):
            try:
                matches = actual is not None and np.isclose(
                    float(actual), wanted, rtol=0.0, atol=1.0e-12
                )
            except (TypeError, ValueError):
                matches = False
        else:
            matches = actual == wanted
        if not matches:
            mismatches[key] = {"actual": actual, "expected": wanted}
    return mismatches


def manipulation_gate(manifest: dict[str, Any]) -> dict[str, Any]:
    """Read every post-warm-up ledger before any endpoint is opened."""
    design, selected, calibration_hashes = load_calibration_contract(manifest)
    report: dict[str, Any] = {
        "calibration": {**calibration_hashes, "selected": selected},
        "G2": {},
        "G1": {},
    }
    for arm in ("G2", "G1"):
        for seed, run in manifest["arms"][arm]["seeds"].items():
            ledgers = verified_ledgers(run, f"{arm} seed {seed}")
            post = [l for l in ledgers if int(l["iteration"]) >= WARMUP_ITERATION]
            if not post:
                raise ValueError(
                    f"{arm} seed {seed}: no sampler ledger after warm-up "
                    "(fail closed)"
                )
            seg = [l["segment"] for l in post]
            tv = [float(s["adaptation_total_variation"]) for s in seg]
            entropy = [float(s["entropy_effective_units"]) for s in seg]
            top1 = [float(s["top1_probability"]) for s in seg]
            invalid = sum(
                int(s["invalid_start_count"])
                + int(s["invalid_reference_frame_count"])
                for s in seg
            )
            censored = sum(int(s.get("censored_resets", 0)) for s in seg)
            final = max(post, key=lambda l: int(l["iteration"]))["segment"]
            saturation = float(final.get("rank_saturation_fraction", float("nan")))
            expected = {
                "mode": "adaptive" if arm == "G2" else "uniform",
                "unit_table_sha256": UNIT_TABLE_SHA256,
                "sampler_seed": int(seed),
                "training_seed": int(seed),
                "rank": design["rank"],
                "progress_window": int(design["progress_window"]),
                "difficulty_power": float(design["difficulty_power"]),
                "exploration_ratio": float(selected["exploration_ratio"]),
                "progress_floor": float(selected["progress_floor"]),
                "max_unit_probability": float(design["max_unit_probability"]),
                "max_clip_probability": float(design["max_clip_probability"]),
            }
            mismatches: dict[str, dict[str, Any]] = {}
            for row in seg:
                for key, mismatch in _contract_mismatches(row, expected).items():
                    mismatches.setdefault(key, mismatch)
            entry = {
                "ledgers_after_warmup": len(post),
                "mean_tv": float(np.mean(tv)),
                "min_entropy_effective_units": float(min(entropy)),
                "max_top1_probability": float(max(top1)),
                "invalid_frames": invalid,
                "censored_resets": censored,
                "final_saturation_fraction": saturation,
                "contract_mismatches": mismatches,
            }
            if arm == "G2":
                entry["pass"] = bool(
                    TV_BAND[0] <= entry["mean_tv"] <= TV_BAND[1]
                    and entry["min_entropy_effective_units"]
                    >= MIN_ENTROPY_EFFECTIVE_UNITS
                    and entry["max_top1_probability"]
                    <= MAX_TOP1_PROBABILITY + 1.0e-8
                    and invalid == 0
                    and censored == 0
                    and np.isfinite(saturation)
                    and saturation < MAX_SATURATION_FRACTION
                    and not mismatches
                )
            else:
                entry["pass"] = bool(
                    entry["mean_tv"] < G1_MAX_TV
                    and invalid == 0
                    and censored == 0
                    and not mismatches
                )
            report[arm][seed] = entry
    report["pass"] = all(
        entry["pass"]
        for arm in ("G2", "G1")
        for entry in report[arm].values()
    )
    return report


def evaluation_provenance_gate(
    manifest: dict[str, Any],
    conditions: dict[str, Any],
    seeds: list[str],
) -> dict[str, Any]:
    """Verify every evaluation cell before parsing a single endpoint row."""
    expected_evaluator_hash = sha256_file(EVALUATOR_PATH)
    expected_training_hash = sha256_file(TRAINING_ENTRYPOINT_PATH)
    report: dict[str, Any] = {
        "pass": True,
        "evaluator_sha256": expected_evaluator_hash,
        "training_entrypoint_sha256": expected_training_hash,
        "cells": {},
    }
    top_mismatches = {}
    for key, expected in (
        ("schema_version", RUN_MANIFEST_SCHEMA),
        ("evaluator_sha256", expected_evaluator_hash),
        ("training_entrypoint_sha256", expected_training_hash),
    ):
        if manifest.get(key) != expected:
            top_mismatches[key] = {
                "actual": manifest.get(key),
                "expected": expected,
            }
    reference_hashes: dict[str, str] = {}
    try:
        panel_path = verified_artifact(
            manifest.get("panel_manifest"), "evaluation panel manifest"
        )
        panel = json.loads(panel_path.read_text())
        if panel.get("schema_version") != "g_segment_eval_panel/1":
            raise ValueError("unsupported evaluation panel manifest")
        reference_hashes = panel["motion_sha256"]
        if set(reference_hashes) != {
            row["clip"] for row in conditions["conditions"]
        }:
            raise ValueError("panel motion hashes do not match condition clips")
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        top_mismatches["panel_manifest"] = {
            "actual": str(exc),
            "expected": "hash-bound g_segment_eval_panel/1 over all condition clips",
        }
    report["top_level_mismatches"] = top_mismatches
    report["pass"] &= not top_mismatches
    expected_worlds = len(conditions["conditions"])

    for arm in ARMS:
        report["cells"][arm] = {}
        for seed in seeds:
            run = manifest["arms"][arm]["seeds"][seed]
            ledgers = verified_ledgers(run, f"{arm} seed {seed}")
            by_iteration: dict[int, list[dict[str, Any]]] = {}
            for ledger in ledgers:
                by_iteration.setdefault(int(ledger["iteration"]), []).append(ledger)
            evaluations = run.get("evaluations")
            if not isinstance(evaluations, dict):
                evaluations = {}
            report["cells"][arm][seed] = {}
            for iteration in AULC_ITERATIONS:
                label = f"{arm} seed {seed} iteration {iteration}"
                mismatches: list[str] = []
                record = evaluations.get(str(iteration))
                paths: dict[str, Path] = {}
                if not isinstance(record, dict) or set(record) != {
                    "csv", "metadata", "checkpoint"
                }:
                    mismatches.append("missing or malformed evaluation record")
                else:
                    for artifact in ("csv", "metadata", "checkpoint"):
                        try:
                            paths[artifact] = verified_artifact(
                                record[artifact], f"{label} {artifact}"
                            )
                        except (OSError, ValueError) as exc:
                            mismatches.append(str(exc))

                meta: dict[str, Any] = {}
                if "metadata" in paths:
                    try:
                        meta = json.loads(paths["metadata"].read_text())
                    except (OSError, json.JSONDecodeError) as exc:
                        mismatches.append(f"metadata is unreadable: {exc}")
                if meta:
                    exact_meta = {
                        "schema_version": EVAL_OUTPUT_SCHEMA,
                        "task": "Climb-Tracking-Flat-Unitree-G1",
                        "conditions_sha256": conditions["_sha256"],
                        "evaluator_sha256": expected_evaluator_hash,
                        "worlds": expected_worlds,
                        "full_window_worlds": expected_worlds,
                        "joint_noise": conditions["joint_noise"],
                        "nominal": conditions["nominal"],
                        "nconmax_per_world": conditions["nconmax_per_world"],
                    }
                    for key, expected in exact_meta.items():
                        if meta.get(key) != expected:
                            mismatches.append(
                                f"metadata {key}={meta.get(key)!r}, expected {expected!r}"
                            )
                    if "csv" in paths and not _path_value_matches(
                        meta.get("output"), paths["csv"]
                    ):
                        mismatches.append("metadata output path does not name the CSV")
                    if "checkpoint" in paths:
                        if not _path_value_matches(
                            meta.get("checkpoint"), paths["checkpoint"]
                        ):
                            mismatches.append(
                                "metadata checkpoint path does not name the policy artifact"
                            )
                        if meta.get("checkpoint_sha256") != record["checkpoint"]["sha256"]:
                            mismatches.append(
                                "metadata checkpoint hash differs from the run manifest"
                            )
                    if meta.get("selected_reference_sha256") != reference_hashes:
                        mismatches.append(
                            "active-reference hashes differ from the panel manifest"
                        )
                    if meta.get("common_reference_sha256") != reference_hashes:
                        mismatches.append(
                            "common-reference hashes differ from the panel manifest"
                        )

                linked = by_iteration.get(iteration, [])
                if len(linked) != 1:
                    mismatches.append(
                        f"expected one sampler ledger at iteration {iteration}, got {len(linked)}"
                    )
                elif isinstance(record, dict):
                    ledger = linked[0]
                    checkpoint_link = ledger.get("checkpoint")
                    if checkpoint_link != record.get("checkpoint"):
                        mismatches.append(
                            "sampler ledger does not bind the evaluated checkpoint"
                        )
                    if ledger.get("training_entrypoint_sha256") != expected_training_hash:
                        mismatches.append(
                            "sampler ledger training-entrypoint hash mismatch"
                        )

                cell = {
                    "pass": not mismatches,
                    "mismatches": mismatches,
                    "checkpoint_sha256": (
                        _artifact_digest(record, "checkpoint")
                    ),
                    "csv_sha256": _artifact_digest(record, "csv"),
                }
                report["cells"][arm][seed][str(iteration)] = cell
                report["pass"] &= cell["pass"]
    report["pass"] = bool(report["pass"])
    return report


def analyze(
    manifest: dict[str, Any],
    conditions: dict[str, Any],
    strata: dict[str, str],
    *,
    seed: int,
    draws: int,
) -> dict[str, Any]:
    if set(manifest.get("arms", {})) != set(ARMS):
        raise ValueError("run manifest must contain exactly the G1 and G2 arms")
    if manifest.get("conditions_sha256") != conditions.get("_sha256"):
        raise ValueError("run manifest does not bind the sealed condition manifest")
    if manifest.get("strata_sha256") != conditions.get("_strata_sha256"):
        raise ValueError("run manifest does not bind the sealed evaluation strata")
    clips = sorted({row["clip"] for row in conditions["conditions"]})
    if set(strata) != set(clips):
        raise ValueError("strata do not match the evaluation panel")
    hard_clips = sorted(
        clip for clip, label in strata.items() if label == "feasible_hard_reference"
    )
    if not hard_clips:
        raise ValueError("feasible-hard reference stratum is empty")
    seeds = sorted(manifest["arms"]["G2"]["seeds"])
    if sorted(manifest["arms"]["G1"]["seeds"]) != seeds:
        raise ValueError("G1 and G2 must share the same seeds")
    if seeds not in (["1", "2"], ["1", "2", "3"]):
        raise ValueError("confirmation must contain declared seeds 1-2 or 1-3")
    gate = manipulation_gate(manifest)
    rng = np.random.default_rng(seed)

    result: dict[str, Any] = {
        "gate": gate,
        "exploratory_rank_agreement": exploratory_rank_agreement(manifest),
        "seeds": seeds,
        "clips": len(clips),
        "feasible_hard_reference_clips": len(hard_clips),
        "tracking_score": {
            "definition": (
                "survival_fraction * exp(-MPKPE/0.30m "
                "- anchor_orientation_error/0.40rad)"
            ),
            "sesoi": TRACKING_SCORE_SESOI,
        },
    }
    if not gate["pass"]:
        result["verdict"] = "not_tested"
        result["reason"] = "manipulation gate failed; endpoints not opened"
        return result

    provenance = evaluation_provenance_gate(manifest, conditions, seeds)
    result["evaluation_provenance_gate"] = provenance
    if not provenance["pass"]:
        result["verdict"] = "not_tested"
        result["reason"] = (
            "evaluation provenance gate failed; endpoint rows not parsed"
        )
        return result

    row_cache: dict[tuple[str, str, int], dict[str, dict[str, str]]] = {}

    def rows_for(
        arm: str, seed_name: str, iteration: int
    ) -> dict[str, dict[str, str]]:
        key = (arm, seed_name, iteration)
        if key not in row_cache:
            record = manifest["arms"][arm]["seeds"][seed_name]["evaluations"][
                str(iteration)
            ]
            rows = read_rows(Path(record["csv"]["path"]))
            validate_rows(
                rows,
                conditions,
                f"{arm} seed {seed_name} it {iteration}",
            )
            row_cache[key] = rows
        return row_cache[key]

    def table(
        arm: str,
        iteration: int,
        column: str = "success",
        selected_clips: list[str] | None = None,
    ) -> np.ndarray:
        selected_clips = clips if selected_clips is None else selected_clips
        matrix = []
        for s in seeds:
            matrix.append(
                per_clip(rows_for(arm, s, iteration), selected_clips, column)
            )
        return np.array(matrix)

    g2_score = table("G2", FINAL_ITERATION, "tracking_score", hard_clips)
    g1_score = table("G1", FINAL_ITERATION, "tracking_score", hard_clips)
    primary = hierarchical_bootstrap(g2_score - g1_score, rng, draws)
    result["primary_G2_minus_G1_tracking_score_feasible_hard"] = primary
    g2_survival = table("G2", FINAL_ITERATION, "success", hard_clips)
    g1_survival = table("G1", FINAL_ITERATION, "success", hard_clips)
    hard_survival = hierarchical_bootstrap(g2_survival - g1_survival, rng, draws)
    result["secondary_G2_minus_G1_survival_feasible_hard"] = hard_survival
    all_score = hierarchical_bootstrap(
        table("G2", FINAL_ITERATION, "tracking_score", clips)
        - table("G1", FINAL_ITERATION, "tracking_score", clips),
        rng,
        draws,
    )
    result["secondary_G2_minus_G1_tracking_score_all"] = all_score
    all_survival = hierarchical_bootstrap(
        table("G2", FINAL_ITERATION, "success", clips)
        - table("G1", FINAL_ITERATION, "success", clips),
        rng,
        draws,
    )
    result["secondary_G2_minus_G1_survival_all"] = all_survival
    aulc = {
        arm: np.mean(
            [table(arm, it, "tracking_score", hard_clips) for it in AULC_ITERATIONS],
            axis=0,
        )
        for arm in ("G1", "G2")
    }
    result["secondary_G2_minus_G1_tracking_score_aulc"] = hierarchical_bootstrap(
        aulc["G2"] - aulc["G1"], rng, draws
    )
    # Common-survivor quality noninferiority, relative to G1, lower is better.
    quality = {}
    noninferior = True
    for metric in QUALITY_METRICS:
        matrix = []
        for s in seeds:
            r2 = rows_for("G2", s, FINAL_ITERATION)
            r1 = rows_for("G1", s, FINAL_ITERATION)
            per = []
            for clip in hard_clips:
                pairs = [
                    (float(r2[c][metric]), float(r1[c][metric]))
                    for c in r2
                    if r2[c]["clip"] == clip
                    and r2[c]["success"] == "1"
                    and r1[c]["success"] == "1"
                ]
                if pairs:
                    a = np.mean([pair[0] for pair in pairs])
                    b = np.mean([pair[1] for pair in pairs])
                    per.append((a - b) / max(abs(b), 1e-9))
                else:
                    per.append(np.nan)
            matrix.append(per)
        matrix = np.array(matrix)
        keep = ~np.isnan(matrix).any(axis=0)
        if not bool(keep.any()):
            raise ValueError(f"{metric}: no clip has common survivors in every seed")
        boot = hierarchical_bootstrap(matrix[:, keep], rng, draws)
        boot["pass"] = bool(boot["ci_high"] < NONINFERIORITY_MARGIN)
        noninferior &= boot["pass"]
        quality[metric] = boot
    result["noninferiority_relative"] = quality

    if (
        primary["point"] >= TRACKING_SCORE_SESOI
        and primary["ci_low"] > 0.0
        and noninferior
    ):
        verdict = "positive"
    elif (
        primary["ci_high"] < TRACKING_SCORE_SESOI
        and hard_survival["ci_high"] < SURVIVAL_SESOI
    ):
        verdict = "null"
    else:
        verdict = "inconclusive"
    result["verdict"] = verdict
    return result


def _synthetic_case(
    root: Path,
    conditions: dict[str, Any],
    *,
    delta: float,
    noise: float,
    tv: float,
    rng: np.random.Generator,
) -> dict[str, Any]:
    clips = sorted({row["clip"] for row in conditions["conditions"]})
    base = {clip: rng.uniform(0.3, 0.9) for clip in clips}
    selected = {
        "id": "synthetic_selected",
        "exploration_ratio": 0.1,
        "progress_floor": 0.01,
    }
    design = {
        "schema_version": "g2_calibration_design/1",
        "rank": "learning_progress",
        "progress_window": 10,
        "difficulty_power": 0.0,
        "max_unit_probability": 0.05,
        "max_clip_probability": 0.25,
        "candidates": [selected],
    }
    design_path = root / "calibration_design.json"
    design_path.write_text(json.dumps(design))
    design_hash = sha256_file(design_path)
    calibration_result = {
        "schema_version": "g2_calibration_result/1",
        "status": "ready_to_freeze",
        "design_sha256": design_hash,
        "selected": selected,
    }
    calibration_path = root / "calibration_result.json"
    calibration_path.write_text(json.dumps(calibration_result))
    fake_reference_hashes = {clip: "a" * 64 for clip in clips}
    panel_path = root / "panel_manifest.json"
    panel_path.write_text(json.dumps({
        "schema_version": "g_segment_eval_panel/1",
        "motion_sha256": fake_reference_hashes,
    }))
    manifest: dict[str, Any] = {
        "schema_version": RUN_MANIFEST_SCHEMA,
        "evaluator_sha256": sha256_file(EVALUATOR_PATH),
        "training_entrypoint_sha256": sha256_file(TRAINING_ENTRYPOINT_PATH),
        "conditions_sha256": conditions["_sha256"],
        "strata_sha256": conditions["_strata_sha256"],
        "panel_manifest": {
            "path": str(panel_path.resolve()),
            "sha256": sha256_file(panel_path),
        },
        "calibration": {
            "design_path": str(design_path),
            "design_sha256": design_hash,
            "result_path": str(calibration_path),
            "result_sha256": sha256_file(calibration_path),
        },
        "arms": {},
    }
    for arm, shift in (("G1", 0.0), ("G2", delta)):
        manifest["arms"][arm] = {"seeds": {}}
        for s in ("1", "2", "3"):
            entry: dict[str, Any] = {"evaluations": {}, "ledgers": []}
            checkpoints = {}
            for it in (0, WARMUP_ITERATION, *AULC_ITERATIONS):
                checkpoint = root / f"{arm}_s{s}_model_{it}.pt"
                checkpoint.write_bytes(f"{arm}:{s}:{it}".encode())
                checkpoints[it] = {
                    "path": str(checkpoint.resolve()),
                    "sha256": sha256_file(checkpoint),
                }

                if it in AULC_ITERATIONS:
                    csv_path = root / f"{arm}_s{s}_{it}.csv"
                    with csv_path.open("w", newline="") as handle:
                        fields = [
                            "condition_id", "clip", "full_window", "success",
                            "survival_s", "actual_window_s", *QUALITY_METRICS,
                        ]
                        writer = csv.DictWriter(handle, fieldnames=fields)
                        writer.writeheader()
                        for row in conditions["conditions"]:
                            p = np.clip(
                                base[row["clip"]]
                                + shift * it / FINAL_ITERATION
                                + rng.normal(0, noise),
                                0,
                                1,
                            )
                            success = int(rng.random() < p)
                            writer.writerow({
                                "condition_id": row["condition_id"],
                                "clip": row["clip"],
                                "full_window": "True",
                                "success": success,
                                "survival_s": 3.0 if success else 1.5,
                                "actual_window_s": 3.0,
                                "common_root_relative_mpkpe_m_mean": max(
                                    0.001, 0.10 - shift * it / FINAL_ITERATION
                                ),
                                "common_anchor_orientation_error_rad_mean": max(
                                    0.001, 0.20 - shift * it / FINAL_ITERATION
                                ),
                                "absolute_mechanical_work_per_actuator_j": 0.1 * (
                                    1 + rng.normal(0, 0.02)
                                ),
                            })
                    meta_path = Path(f"{csv_path}.meta.json")
                    meta_path.write_text(json.dumps({
                        "schema_version": EVAL_OUTPUT_SCHEMA,
                        "task": "Climb-Tracking-Flat-Unitree-G1",
                        "checkpoint": str(checkpoint.resolve()),
                        "checkpoint_sha256": checkpoints[it]["sha256"],
                        "selected_reference_sha256": fake_reference_hashes,
                        "common_reference_sha256": fake_reference_hashes,
                        "conditions_sha256": conditions["_sha256"],
                        "evaluator_sha256": sha256_file(EVALUATOR_PATH),
                        "nominal": conditions["nominal"],
                        "joint_noise": conditions["joint_noise"],
                        "nconmax_per_world": conditions["nconmax_per_world"],
                        "worlds": len(conditions["conditions"]),
                        "full_window_worlds": len(conditions["conditions"]),
                        "output": str(csv_path.resolve()),
                    }))
                    entry["evaluations"][str(it)] = {
                        "csv": {
                            "path": str(csv_path.resolve()),
                            "sha256": sha256_file(csv_path),
                        },
                        "metadata": {
                            "path": str(meta_path.resolve()),
                            "sha256": sha256_file(meta_path),
                        },
                        "checkpoint": checkpoints[it],
                    }

                ledger_path = root / f"{arm}_s{s}_{it}_segment.json"
                ledger_path.write_text(json.dumps({
                    "iteration": it,
                    "checkpoint": checkpoints[it],
                    "training_entrypoint_sha256": sha256_file(
                        TRAINING_ENTRYPOINT_PATH
                    ),
                    "segment": {
                        "mode": "adaptive" if arm == "G2" else "uniform",
                        "unit_table_sha256": UNIT_TABLE_SHA256,
                        "sampler_seed": int(s),
                        "training_seed": int(s),
                        "rank": "learning_progress",
                        "progress_window": 10,
                        "difficulty_power": 0.0,
                        "exploration_ratio": selected["exploration_ratio"],
                        "progress_floor": selected["progress_floor"],
                        "max_unit_probability": 0.05,
                        "max_clip_probability": 0.25,
                        "adaptation_total_variation": tv if arm == "G2" else 0.0,
                        "entropy_effective_units": 40.0,
                        "top1_probability": 0.04,
                        "invalid_start_count": 0,
                        "invalid_reference_frame_count": 0,
                        "censored_resets": 0,
                        "rank_saturation_fraction": 0.3,
                        "conditional_success_rates": np.linspace(
                            0.05, 0.95, 40
                        ).tolist(),
                        "learning_progress": (
                            0.02
                            + 0.01
                            * np.sin(np.linspace(0.0, 4.0 * np.pi, 40))
                        ).tolist(),
                    },
                }))
                entry["ledgers"].append({
                    "path": str(ledger_path.resolve()),
                    "sha256": sha256_file(ledger_path),
                })
            manifest["arms"][arm]["seeds"][s] = entry
    return manifest


def synthetic(conditions: dict[str, Any], strata: dict[str, str], out: Path) -> int:
    cases = {
        "positive": {"delta": 0.12, "noise": 0.02, "tv": 0.08, "rng_seed": 1},
        "null": {"delta": -0.10, "noise": 0.02, "tv": 0.08, "rng_seed": 2},
        "inconclusive": {"delta": 0.005, "noise": 0.25, "tv": 0.08, "rng_seed": 6},
        "gate_fail": {"delta": 0.12, "noise": 0.02, "tv": 0.01, "rng_seed": 5},
        "seed_mismatch": {"delta": 0.12, "noise": 0.02, "tv": 0.08, "rng_seed": 7},
        "provenance_mismatch": {
            "delta": 0.12, "noise": 0.02, "tv": 0.08, "rng_seed": 8
        },
    }
    verdicts = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name, kw in cases.items():
            case_dir = Path(tmp) / name
            case_dir.mkdir()
            parameters = dict(kw)
            rng_seed = parameters.pop("rng_seed")
            manifest = _synthetic_case(
                case_dir,
                conditions,
                rng=np.random.default_rng(rng_seed),
                **parameters,
            )
            if name == "seed_mismatch":
                ledger_record = (
                    manifest["arms"]["G2"]["seeds"]["1"]["ledgers"][1]
                )
                ledger_path = Path(ledger_record["path"])
                ledger = json.loads(ledger_path.read_text())
                ledger["segment"]["training_seed"] = 42
                ledger_path.write_text(json.dumps(ledger))
                ledger_record["sha256"] = sha256_file(ledger_path)
            elif name == "provenance_mismatch":
                meta_record = manifest["arms"]["G2"]["seeds"]["1"][
                    "evaluations"
                ][str(FINAL_ITERATION)]["metadata"]
                meta_path = Path(meta_record["path"])
                metadata = json.loads(meta_path.read_text())
                metadata["checkpoint_sha256"] = "0" * 64
                meta_path.write_text(json.dumps(metadata))
                meta_record["sha256"] = sha256_file(meta_path)
            result = analyze(
                manifest, conditions, strata, seed=BOOTSTRAP_SEED, draws=500
            )
            verdicts[name] = result["verdict"]
    expected = {
        "positive": "positive",
        "null": "null",
        "inconclusive": "inconclusive",
        "gate_fail": "not_tested",
        "seed_mismatch": "not_tested",
        "provenance_mismatch": "not_tested",
    }
    passed = verdicts == expected
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "synthetic": True,
        "pass": passed,
        "verdicts": verdicts,
        "expected": expected,
        "analyzer_sha256": sha256_file(Path(__file__).resolve()),
    }
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(f"Phase-G analyzer synthetic: {'PASS' if passed else 'FAIL'} {verdicts}")
    return 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--conditions",
        type=Path,
        default=Path("reports/g_segment/eval_conditions.json"),
    )
    parser.add_argument(
        "--strata", type=Path, default=Path("reports/g_segment/panel/strata.csv")
    )
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=BOOTSTRAP_SEED)
    parser.add_argument("--draws", type=int, default=BOOTSTRAP_DRAWS)
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    conditions = json.loads(args.conditions.read_text())
    conditions["_sha256"] = sha256_file(args.conditions)
    with args.strata.open() as handle:
        strata = {row["clip"]: row["stratum"] for row in csv.DictReader(handle)}
    conditions["_strata_sha256"] = sha256_file(args.strata)
    if args.synthetic:
        return synthetic(conditions, strata, args.out)
    if args.manifest is None:
        parser.error("--manifest is required without --synthetic")
    manifest = json.loads(args.manifest.read_text())
    result = analyze(manifest, conditions, strata, seed=args.seed, draws=args.draws)
    result["inputs"] = {
        "conditions_sha256": conditions["_sha256"],
        "strata_sha256": conditions["_strata_sha256"],
        "manifest_sha256": sha256_file(args.manifest),
        "analyzer_sha256": sha256_file(Path(__file__).resolve()),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: result[k] for k in ("verdict",) if k in result}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
