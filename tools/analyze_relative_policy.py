#!/usr/bin/env python3
"""Prospective R3 statistical kernel; CLI accepts synthetic fixtures only.

Real endpoint ingestion remains unavailable until the independent manipulation
replication, comparator calibration, and evaluator provenance manifest are ready.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.stats import t

SEEDS = (21, 22, 23)
ARMS = ("U", "A", "R", "D")
SESOI = 0.02
NONREGRESSION_MARGIN = -0.01
BOOTSTRAP_SEED = 20260905
BOOTSTRAP_DRAWS = 10_000


def aggregate_rows(rows: list[dict], conditions: list[dict], clip_order: list[str], *,
                   window_s: float = 3.0) -> np.ndarray:
    """Keep failed trials in clip means; reject duplicate or unpaired conditions.

    This pure adapter consumes already verified rows. It does not authenticate
    CSVs, checkpoints, or evaluator metadata; that external gate is still needed.
    """
    expected = {row["condition_id"]: row for row in conditions}
    if len(expected) != len(conditions) or not conditions:
        raise ValueError("condition manifest is empty or has duplicate identities")
    actual = {row["condition_id"]: row for row in rows}
    if len(actual) != len(rows) or set(actual) != set(expected):
        raise ValueError("missing, extra, or duplicate evaluator condition")
    if (len(set(clip_order)) != len(clip_order)
            or {row["clip"] for row in conditions} != set(clip_order)):
        raise ValueError("clip panel mismatch")
    grouped = {clip: [] for clip in clip_order}
    for identity, condition in expected.items():
        row = actual[identity]
        if row["clip"] != condition["clip"]:
            raise ValueError("condition-to-clip attribution mismatch")
        for field in ("start_frame", "replicate", "horizon_steps"):
            if str(row[field]) != str(condition[field]):
                raise ValueError(f"condition {field} mismatch")
        if condition["full_window"] is not True or str(row["full_window"]).lower() not in ("true", "1"):
            raise ValueError("short or incomplete condition window")
        survival, actual_window, position, orientation = (
            float(row[key]) for key in ("survival_s", "actual_window_s",
                                       "common_root_relative_mpkpe_m_mean",
                                       "common_anchor_orientation_error_rad_mean")
        )
        if (not np.isfinite([survival, actual_window, position, orientation]).all()
                or actual_window <= 0 or abs(actual_window - window_s) > 1e-6
                or survival < 0 or survival > actual_window + 1e-6
                or position < 0 or orientation < 0):
            raise ValueError("invalid tracking measurement")
        score = min(survival / actual_window, 1.0) * np.exp(-position / 0.30 - orientation / 0.40)
        grouped[condition["clip"]].append(float(score))
    return np.array([np.mean(grouped[clip]) for clip in clip_order])


def seed_summary(values: np.ndarray) -> dict:
    """Two-sided Student-t interval over independent paired training-seed deltas."""
    mean = float(values.mean())
    sd = float(values.std(ddof=1))
    half_width = float(t.ppf(0.975, len(values) - 1) * sd / np.sqrt(len(values)))
    return {"paired_seed_deltas": dict(zip(map(str, SEEDS), values.tolist())),
            "mean": mean, "sd_across_seeds": sd,
            "seed_t_95ci": [mean - half_width, mean + half_width],
            "independent_units": len(values), "df": len(values) - 1}


def hierarchical_interval(delta: np.ndarray, *, draws: int = BOOTSTRAP_DRAWS) -> list[float]:
    """Resample paired seed and clip identities, preserving the arm contrast."""
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    seed_index = rng.integers(0, delta.shape[0], size=(draws, delta.shape[0]))
    clip_index = rng.integers(0, delta.shape[1], size=(draws, delta.shape[1]))
    sampled = delta[seed_index[:, :, None], clip_index[:, None, :]].mean(axis=(1, 2))
    return np.quantile(sampled, [0.025, 0.975]).tolist()


def analyze_scores(scores: dict[str, np.ndarray], hard_indices: np.ndarray, *,
                   manipulation_pass: bool, provenance_pass: bool) -> dict:
    """Analyze complete per-clip final scores; caller must establish provenance.

    Arrays have three rows in seed order 21/22/23 and 100 columns in fixed panel
    order. These booleans are integration hooks, not a replacement for verifying
    source-bound raw evaluator artifacts in a future input adapter.
    """
    if not provenance_pass:
        return {"status": "invalid", "reason": "provenance gate failed"}
    if not manipulation_pass:
        return {"status": "not_tested", "reason": "manipulation gate failed"}
    if set(scores) != set(ARMS):
        raise ValueError("all four matched arms are required")
    for arm, values in scores.items():
        if (not isinstance(values, np.ndarray) or values.shape != (3, 100)
                or not np.isfinite(values).all() or ((values < 0) | (values > 1)).any()):
            raise ValueError(f"{arm}: expected finite 3-by-100 scores in [0,1]")
    hard = np.asarray(hard_indices)
    if (hard.shape != (25,) or not np.issubdtype(hard.dtype, np.integer)
            or len(np.unique(hard)) != 25 or ((hard < 0) | (hard >= 100)).any()):
        raise ValueError("expected 25 unique reference-defined feasible-hard indices")
    delta = scores["R"] - scores["U"]
    primary = seed_summary(delta[:, hard].mean(axis=1))
    guard = seed_summary(delta.mean(axis=1))
    primary["hierarchical_paired_95ci_supplementary"] = hierarchical_interval(delta[:, hard])
    guard["hierarchical_paired_95ci_supplementary"] = hierarchical_interval(delta)
    benefit = primary["mean"] >= SESOI and primary["seed_t_95ci"][0] > 0
    nonregression = guard["seed_t_95ci"][0] > NONREGRESSION_MARGIN
    if benefit and nonregression:
        status = "positive"
    elif primary["seed_t_95ci"][1] < SESOI:
        status = "negative_for_prespecified_effect"
    else:
        status = "inconclusive"
    secondary = {
        f"R_minus_{arm}": {
            "feasible_hard": seed_summary((scores["R"] - scores[arm])[:, hard].mean(axis=1)),
            "all_panel": seed_summary((scores["R"] - scores[arm]).mean(axis=1)),
        } for arm in ("A", "D")
    }
    return {"schema_version": "relative_policy_statistics/1", "status": status,
            "primary_R_minus_U": primary, "all_panel_nonregression": guard,
            "primary_effect_requirement_pass": benefit, "nonregression_pass": nonregression,
            "secondary_descriptive": secondary,
            "analysis": {"seed_order": SEEDS, "primary_clips": 25, "panel_clips": 100,
                         "sesoi": SESOI, "nonregression_margin": NONREGRESSION_MARGIN,
                         "bootstrap_seed": BOOTSTRAP_SEED, "bootstrap_draws": BOOTSTRAP_DRAWS},
            "limitations": ["Three training seeds give imprecise seed-level inference.",
                            "Hierarchical intervals and secondary contrasts do not override the primary decision.",
                            "A negative SESOI decision is not an equivalence claim."]}


def synthetic() -> dict:
    output = {}
    cases = {
        "positive": [0.04, 0.041, 0.039],
        "negative_for_prespecified_effect": [0.0, 0.001, -0.001],
        "inconclusive": [0.06, -0.02, 0.04],
    }
    hard = np.arange(25)
    for expected, shifts in cases.items():
        scores = {arm: np.full((3, 100), 0.5) for arm in ARMS}
        scores["R"] += np.array(shifts)[:, None]
        result = analyze_scores(scores, hard, manipulation_pass=True, provenance_pass=True)
        if result["status"] != expected:
            raise AssertionError(f"{expected} fixture returned {result['status']}")
        output[expected] = result
    scores = {arm: np.full((3, 100), 0.5) for arm in ARMS}
    scores["R"][:, :25] += 0.04
    scores["R"][:, 25:] -= 0.08
    guard = analyze_scores(scores, hard, manipulation_pass=True, provenance_pass=True)
    if guard["status"] == "positive" or guard["nonregression_pass"]:
        raise AssertionError("all-panel regression did not block promotion")
    output["nonregression_failure"] = guard
    for status, manipulation, provenance in (("not_tested", False, True), ("invalid", True, False)):
        result = analyze_scores({}, hard, manipulation_pass=manipulation, provenance_pass=provenance)
        if result["status"] != status:
            raise AssertionError("gate ordering failed")
        output[status] = result
    return {"classification": "synthetic validation only; no measured policy outcomes",
            "branches": output}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", action="store_true", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = synthetic()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print("Passed six synthetic decision branches; no policy endpoints opened")


if __name__ == "__main__":
    main()
