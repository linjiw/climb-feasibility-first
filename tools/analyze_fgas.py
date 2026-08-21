#!/usr/bin/env python3
"""Frozen FGAS analysis: performance, attractor movement, and contamination.

The primary comparison is soft FGAS versus the already-completed grounded
(mixture-floor) baseline at matched seeds and 4,000 iterations.  Performance is
measured on the sealed feasible-hard20 list; heldout100 feasible motions are the
no-regression population.  Training logs supply the pre-registered FGAS-2
attractor and implementation checks.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SEEDS = (1, 2, 3)
FLAG_THRESHOLD = 0.10
BOOTSTRAP_DRAWS = 20_000
BOOTSTRAP_SEED = 20260820

_METRIC_RE = re.compile(
    r"Metrics/motion/(sampling_top1_bin|sampling_top1_prob|"
    r"sampling_clip_entropy|sampling_ineligible_mass):\s*([-\d.eE+]+)"
)


def _read_eval(path: Path) -> dict[str, float]:
    with path.open() as handle:
        return {
            row["clip"]: float(row["survival_rate"]) for row in csv.DictReader(handle)
        }


def _read_strat(path: Path) -> dict[str, float]:
    grouped: dict[str, list[float]] = {}
    with path.open() as handle:
        for row in csv.DictReader(handle):
            if row["offset_s"] == "mean":
                continue
            grouped.setdefault(row["clip"], []).append(float(row["survival"]))
    return {clip: float(np.mean(values)) for clip, values in grouped.items()}


def _read_feasibility(path: Path) -> dict[str, float]:
    with path.open() as handle:
        return {
            row["clip"]: float(row["infeasible_frac"]) for row in csv.DictReader(handle)
        }


def _read_list(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]


def parse_training_log(path: Path) -> list[dict[str, float]]:
    """Read one scalar value per learning iteration from the console log."""
    values: dict[str, list[float]] = {}
    with path.open(errors="replace") as handle:
        for line in handle:
            match = _METRIC_RE.search(line)
            if match:
                values.setdefault(match.group(1), []).append(float(match.group(2)))
    required = (
        "sampling_top1_bin",
        "sampling_top1_prob",
        "sampling_clip_entropy",
        "sampling_ineligible_mass",
    )
    missing = [name for name in required if name not in values]
    if missing:
        raise ValueError(f"{path}: missing training metrics {missing}")
    count = min(len(values[name]) for name in required)
    return [{name: values[name][index] for name in required} for index in range(count)]


def hierarchical_bootstrap(delta: np.ndarray) -> tuple[float, float]:
    """Seed-by-motion bootstrap CI for a paired survival delta."""
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    n_seed, n_motion = delta.shape
    draws = np.empty(BOOTSTRAP_DRAWS)
    for index in range(BOOTSTRAP_DRAWS):
        seed_ids = rng.integers(0, n_seed, n_seed)
        motion_ids = rng.integers(0, n_motion, n_motion)
        draws[index] = delta[np.ix_(seed_ids, motion_ids)].mean()
    quantiles = np.quantile(draws, (0.025, 0.975))
    return float(quantiles[0]), float(quantiles[1])


def outcome_summary(
    baseline: list[dict[str, float]],
    fgas: list[dict[str, float]],
    population: list[str],
) -> dict[str, Any]:
    missing = [
        clip for clip in population if any(clip not in arm for arm in baseline + fgas)
    ]
    if missing:
        raise ValueError(
            f"outcome population missing {len(missing)} clips, e.g. {missing[:3]}"
        )
    base = np.array([[arm[clip] for clip in population] for arm in baseline])
    method = np.array([[arm[clip] for clip in population] for arm in fgas])
    delta = method - base
    ci_low, ci_high = hierarchical_bootstrap(delta)
    return {
        "motions": len(population),
        "baseline_seed_means": base.mean(axis=1).tolist(),
        "fgas_seed_means": method.mean(axis=1).tolist(),
        "baseline_mean": float(base.mean()),
        "fgas_mean": float(method.mean()),
        "paired_delta": float(delta.mean()),
        "bootstrap_95ci": [ci_low, ci_high],
    }


def telemetry_summary(
    records: list[dict[str, float]],
    training_clips: list[str],
    feasibility: dict[str, float],
) -> dict[str, Any]:
    late = records[len(records) // 2 :]
    flagged = np.array(
        [feasibility.get(clip, math.inf) > FLAG_THRESHOLD for clip in training_clips]
    )
    selected = []
    ambiguous = 0
    for record in late:
        raw_index = record["sampling_top1_bin"] * len(training_clips)
        if abs(raw_index - round(raw_index)) > 1e-6:
            ambiguous += 1
            continue
        selected.append(bool(flagged[round(raw_index) % len(training_clips)]))
    return {
        "iterations": len(records),
        "late_iterations": len(late),
        "late_ambiguous_argmax": ambiguous,
        "p_top1_flagged": float(np.mean(selected)) if selected else float("nan"),
        "mean_top1_mass": float(np.mean([r["sampling_top1_prob"] for r in late])),
        "mean_clip_entropy": float(np.mean([r["sampling_clip_entropy"] for r in late])),
        "mean_ineligible_mass": float(
            np.mean([r["sampling_ineligible_mass"] for r in late])
        ),
    }


def verdict(
    hard_outcome: dict[str, Any],
    feasible_outcome: dict[str, Any],
    telemetry: list[dict[str, Any]],
) -> dict[str, Any]:
    hard_delta = float(hard_outcome["paired_delta"])
    hard_ci_low = float(hard_outcome["bootstrap_95ci"][0])
    feasible_delta = float(feasible_outcome["paired_delta"])
    mean_flagged = float(np.mean([row["p_top1_flagged"] for row in telemetry]))
    mean_top1 = float(np.mean([row["mean_top1_mass"] for row in telemetry]))
    mean_contamination = float(
        np.mean([row["mean_ineligible_mass"] for row in telemetry])
    )

    performance = hard_delta >= 0.05 and hard_ci_low > 0.0
    no_regression = feasible_delta >= -0.03
    attractor = mean_flagged < 0.40 and 0.30 <= mean_top1 <= 0.38
    implementation = mean_contamination < 0.15
    if performance and no_regression and implementation:
        reading = "performance_benefit"
    elif implementation and no_regression:
        reading = "hygiene_only_or_performance_null"
    else:
        reading = "failed_or_harmful"
    return {
        "performance_benefit": performance,
        "no_feasible_regression": no_regression,
        "attractor_moves": attractor,
        "soft_contamination_gate": implementation,
        "mean_p_top1_flagged": mean_flagged,
        "mean_top1_mass": mean_top1,
        "mean_ineligible_mass": mean_contamination,
        "reading": reading,
        "rules": {
            "performance": "feasible-hard20 delta >= 0.05 and bootstrap CI low > 0",
            "no_regression": "heldout feasible delta >= -0.03",
            "attractor": "P(top1 flagged) < 0.40 and mean top1 mass in [0.30, 0.38]",
            "soft_implementation": "late joint hard-rejected mass < 0.15",
        },
    }


def analyze(root: Path) -> dict[str, Any]:
    feasibility = _read_feasibility(root / "reports/feasibility_e3/feasibility.csv")
    training_clips = _read_list(root / "bank/tiers/tier_mixed100.txt")
    hard_clips = _read_list(root / "bank/tiers/fgas_feasible_hard20.txt")
    feasible_clips = [
        clip
        for clip in _read_list(root / "bank/tiers/heldout100.txt")
        if feasibility[clip] <= FLAG_THRESHOLD
    ]
    baseline_eval = [
        _read_eval(root / f"reports/campaign/grounded-mixed100-s{seed}_it3999.csv")
        for seed in SEEDS
    ]
    fgas_eval = [
        _read_eval(root / f"reports/campaign/fgas-soft-mixed100-s{seed}_it3999.csv")
        for seed in SEEDS
    ]
    baseline_strat = [
        _read_strat(root / f"reports/FGAS/grounded-mixed100-s{seed}_hard20_strat.csv")
        for seed in SEEDS
    ]
    fgas_strat = [
        _read_strat(root / f"reports/FGAS/fgas-soft-mixed100-s{seed}_hard20_strat.csv")
        for seed in SEEDS
    ]
    telemetry = [
        telemetry_summary(
            parse_training_log(root / f"logs/campaign/fgas-soft-mixed100-s{seed}.log"),
            training_clips,
            feasibility,
        )
        for seed in SEEDS
    ]
    hard = outcome_summary(baseline_strat, fgas_strat, hard_clips)
    feasible = outcome_summary(baseline_eval, fgas_eval, feasible_clips)
    return {
        "analysis": "FGAS soft guard0 versus grounded mixture baseline",
        "seeds": list(SEEDS),
        "feasible_hard20": hard,
        "heldout_feasible": feasible,
        "telemetry": telemetry,
        "decision": verdict(hard, feasible, telemetry),
    }


def synthetic() -> None:
    base = [{"a": 0.4, "b": 0.5}, {"a": 0.5, "b": 0.4}, {"a": 0.45, "b": 0.45}]
    better = [{"a": 0.6, "b": 0.6}, {"a": 0.6, "b": 0.55}, {"a": 0.55, "b": 0.6}]
    hard = outcome_summary(base, better, ["a", "b"])
    feasible = outcome_summary(base, better, ["a", "b"])
    moved = [
        {
            "p_top1_flagged": 0.3,
            "mean_top1_mass": 0.34,
            "mean_ineligible_mass": 0.10,
        }
    ] * 3
    result = verdict(hard, feasible, moved)
    assert result["performance_benefit"] and result["attractor_moves"]
    assert result["reading"] == "performance_benefit"

    null = [dict(row, p_top1_flagged=0.74) for row in moved]
    result = verdict(hard, feasible, null)
    assert not result["attractor_moves"] and result["performance_benefit"]

    contaminated = [dict(row, mean_ineligible_mass=0.3) for row in moved]
    result = verdict(hard, feasible, contaminated)
    assert not result["soft_contamination_gate"]
    assert result["reading"] == "failed_or_harmful"
    print(
        "FGAS synthetic analysis: benefit, attractor-null, and wiring-fail branches pass"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    if args.synthetic:
        synthetic()
        return
    result = analyze(args.root)
    rendered = json.dumps(result, indent=1)
    print(rendered)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n")


if __name__ == "__main__":
    main()
