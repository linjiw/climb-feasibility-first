#!/usr/bin/env python3
"""Prospective H1 statistics/order kernel; CLI accepts synthetic data only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

import numpy as np
from scipy.stats import t

ARMS = ("on", "off")
SEEDS = (61, 62, 63)
CHECKPOINTS = (1000, 2000, 3000, 3999)
TARGET = 0.02
MARGIN = -0.01
BOOTSTRAP_SEED = 20260906
BOOTSTRAP_DRAWS = 10000


def schedule() -> list[dict]:
    """Describe six training jobs followed by 24 evaluations; no launch argv."""
    jobs = []
    for index, seed in enumerate(SEEDS):
        for arm in ARMS if index % 2 == 0 else ARMS[::-1]:
            jobs.append({"stage": "train", "arm": arm, "seed": seed})
    for seed in SEEDS:
        for arm in ARMS:
            for checkpoint in CHECKPOINTS:
                jobs.append({"stage": "evaluate", "arm": arm, "seed": seed, "checkpoint": checkpoint})
    return jobs


def load_after_training(
    training_records: dict, verify_training: Callable, load_outcome: Callable,
) -> dict:
    """Order authenticated callbacks; this does not itself authenticate files.

    Future production callers must bind the contract, source inventory and these
    callbacks. Synthetic callbacks below test ordering only and cannot authorize
    an experiment. No outcome callback runs until all six verifiers return.
    """
    expected = {(arm, seed) for arm in ARMS for seed in SEEDS}
    if set(training_records) != expected:
        raise ValueError("requires exactly six paired training records")
    for job in schedule()[:6]:
        key = (job["arm"], job["seed"])
        result = verify_training(training_records[key], arm=key[0], seed=key[1])
        if (result.get("status") != "gate_training_pass" or result.get("admission") != key[0]
                or result.get("seed") != key[1] or result.get("smoke") is not False
                or result.get("device") != "cuda:0" or result.get("transitions") != 49152000
                or [r["iteration"] for r in result.get("checkpoints", [])] != [*range(0, 4000, 100), 3999]):
            raise ValueError("full-budget training verification incomplete")
    result = {}
    for job in schedule()[6:]:
        key = (job["arm"], job["seed"], job["checkpoint"])
        result[key] = load_outcome(*key)
    return result


def seed_interval(delta: np.ndarray) -> dict:
    if delta.shape != (3,) or not np.isfinite(delta).all():
        raise ValueError("requires three finite paired seed means")
    mean, sd = float(delta.mean()), float(delta.std(ddof=1))
    half = float(t.ppf(.975, 2) * sd / np.sqrt(3))
    return {"paired_seed_deltas": dict(zip(map(str, SEEDS), delta.tolist())),
            "mean": mean, "sd_across_seeds": sd, "seed_t_95ci": [mean - half, mean + half],
            "independent_units": 3, "df": 2}


def paired_bootstrap(delta: np.ndarray) -> list[float]:
    """Resample seed and shared clip identities, preserving each on/off pair."""
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    seeds = rng.integers(0, 3, size=(BOOTSTRAP_DRAWS, 3))
    clips = rng.integers(0, delta.shape[1], size=(BOOTSTRAP_DRAWS, delta.shape[1]))
    values = delta[seeds[:, :, None], clips[:, None, :]].mean(axis=(1, 2))
    return np.quantile(values, [.025, .975]).tolist()


def analyze_scores(scores: dict, hard_indices: np.ndarray, *, training_pass: bool, provenance_pass: bool) -> dict:
    """Pure final-checkpoint decision kernel; input authentication is external."""
    if not provenance_pass:
        return {"status": "invalid", "decision_available": False}
    if not training_pass:
        return {"status": "not_tested", "decision_available": False}
    if set(scores) != set(ARMS):
        raise ValueError("requires gate-on and gate-off only")
    for value in scores.values():
        if (not isinstance(value, np.ndarray) or value.shape != (3, 100)
                or not np.isfinite(value).all() or ((value < 0) | (value > 1)).any()):
            raise ValueError("expected finite 3-by-100 clip scores in [0,1]")
    hard = np.asarray(hard_indices)
    if (hard.shape != (25,) or not np.issubdtype(hard.dtype, np.integer)
            or len(np.unique(hard)) != 25 or ((hard < 0) | (hard >= 100)).any()):
        raise ValueError("requires 25 unique reference-defined hard indices")
    delta = scores["on"] - scores["off"]
    primary, guard = seed_interval(delta[:, hard].mean(axis=1)), seed_interval(delta.mean(axis=1))
    benefit = primary["mean"] >= TARGET and primary["seed_t_95ci"][0] > 0
    nonregression = guard["seed_t_95ci"][0] > MARGIN
    preservation = primary["seed_t_95ci"][0] > MARGIN and nonregression
    improvement = benefit and nonregression
    status = "improvement" if improvement else "preservation_only" if preservation else "inconclusive_or_harm"
    primary["paired_seed_clip_bootstrap_95ci_supplementary"] = paired_bootstrap(delta[:, hard])
    guard["paired_seed_clip_bootstrap_95ci_supplementary"] = paired_bootstrap(delta)
    return {"status": status, "decision_available": True, "primary_on_minus_off": primary,
            "all_panel_on_minus_off": guard, "improvement_pass": improvement,
            "primary_effect_pass": benefit, "all_panel_nonregression_pass": nonregression,
            "preservation_pass": preservation,
            "analysis": {"seed_order": list(SEEDS), "checkpoint": 3999, "target": TARGET,
                         "nonregression_margin": MARGIN, "bootstrap_seed": BOOTSTRAP_SEED,
                         "bootstrap_draws": BOOTSTRAP_DRAWS, "independent_unit": "paired training seed"},
            "limitations": ["Preservation is noninferiority within margins, not equivalence or improvement.",
                            "Bootstrap intervals cannot override the seed-level t decision.",
                            "Prospective development kernel; production provenance and freeze remain required."]}


def synthetic() -> dict:
    results = {}
    for name, shifts in {"improvement": [.04, .041, .039], "preservation_only": [0, .001, -.001],
                         "inconclusive_or_harm": [.06, -.02, .04]}.items():
        scores = {arm: np.full((3, 100), .5) for arm in ARMS}
        scores["on"] += np.array(shifts)[:, None]
        result = analyze_scores(scores, np.arange(25), training_pass=True, provenance_pass=True)
        if result["status"] != name:
            raise ValueError("synthetic H1 decision failed")
        results[name] = result
    return {"classification": "SYNTHETIC H1 validation only; no measured policy outcomes",
            "full_training_enabled": False, "schedule": schedule(), "cases": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", action="store_true", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = synthetic()
    with args.out.open("x") as handle:
        handle.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print("Synthetic H1 decisions and 30-job ordering prepared; no experiment launched")
