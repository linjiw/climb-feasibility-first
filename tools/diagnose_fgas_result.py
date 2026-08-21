#!/usr/bin/env python3
"""Post-outcome diagnostics for the completed soft-FGAS campaign.

This script does not alter the frozen analyzer or its decision. It reconstructs
the final sampler from exposure ledgers, decomposes hard-rejected start mass by
clip, and evaluates counterfactual eligibility strengths using the recovered
relative failure signal.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEEDS = (1, 2, 3)
EPSILON = 0.1
FLAG_THRESHOLD = 0.10
MASS_RE = re.compile(r"sampling_ineligible_mass:\s*([-\d.eE+]+)")


def _clip_names(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]


def _feasibility(path: Path) -> dict[str, float]:
    with path.open() as handle:
        return {
            row["clip"]: float(row["infeasible_frac"]) for row in csv.DictReader(handle)
        }


def _expand(record: dict[str, Any], field: str) -> list[float]:
    values = [float(value) for value in record[field]]
    repeated = [value for value in values for _ in range(int(record["bin_frames"]))]
    return repeated[: int(record["frames"])]


def _sidecar_stats(path: Path) -> dict[str, float]:
    record = json.loads(path.read_text())
    hard = _expand(record, "bin_eligible")
    soft = _expand(record, "bin_score")
    if len(hard) != len(soft) or not hard:
        raise ValueError(f"{path}: invalid expanded sidecar")
    soft_mass = sum(soft)
    soft_power_2 = [value**2 for value in soft]
    soft_power_2_mass = sum(soft_power_2)
    return {
        "hard_fraction": sum(hard) / len(hard),
        "soft_mean": soft_mass / len(soft),
        "soft_rejected_conditional": (
            sum(weight * (1.0 - keep) for weight, keep in zip(soft, hard, strict=True))
            / soft_mass
            if soft_mass > 0.0
            else 1.0 - sum(hard) / len(hard)
        ),
        "soft_power_2_rejected_conditional": (
            sum(
                weight * (1.0 - keep)
                for weight, keep in zip(soft_power_2, hard, strict=True)
            )
            / soft_power_2_mass
            if soft_power_2_mass > 0.0
            else 1.0 - sum(hard) / len(hard)
        ),
    }


def _mixture(failure: list[float], eligibility: list[float]) -> list[float]:
    eligible_sum = sum(eligibility)
    if eligible_sum <= 0.0:
        raise ValueError("counterfactual removes every clip")
    base = [value / eligible_sum for value in eligibility]
    focused = [
        max(value, 0.0) * weight
        for value, weight in zip(failure, eligibility, strict=True)
    ]
    focused_sum = sum(focused)
    focus = [value / focused_sum for value in focused] if focused_sum > 0.0 else base
    return [
        (1.0 - EPSILON) * adaptive + EPSILON * prior
        for adaptive, prior in zip(focus, base, strict=True)
    ]


def _recover_failure(probability: list[float], eligibility: list[float]) -> list[float]:
    eligible_sum = sum(eligibility)
    base = [value / eligible_sum for value in eligibility]
    focus = [
        max((prob - EPSILON * prior) / (1.0 - EPSILON), 0.0)
        for prob, prior in zip(probability, base, strict=True)
    ]
    failure = [
        focused / weight if weight > 0.0 else 0.0
        for focused, weight in zip(focus, eligibility, strict=True)
    ]
    scale = max(failure, default=0.0)
    return [value / scale for value in failure] if scale > 0.0 else failure


def _last_logged_mass(path: Path) -> float:
    values = [
        float(match.group(1))
        for line in path.read_text(errors="replace").splitlines()
        if (match := MASS_RE.search(line))
    ]
    if not values:
        raise ValueError(f"{path}: no ineligible-mass metric")
    return values[-1]


def _counterfactual(
    names: list[str],
    failure: list[float],
    eligibility: list[float],
    rejected: list[float],
    infeasible: dict[str, float],
) -> dict[str, Any]:
    probability = _mixture(failure, eligibility)
    top = max(range(len(names)), key=lambda index: probability[index])
    return {
        "hard_rejected_start_mass": sum(
            prob * bad for prob, bad in zip(probability, rejected, strict=True)
        ),
        "clip_level_flagged_mass": sum(
            prob
            for name, prob in zip(names, probability, strict=True)
            if infeasible[name] > FLAG_THRESHOLD
        ),
        "top_clip": names[top],
        "top_clip_mass": probability[top],
        "top_clip_flagged": infeasible[names[top]] > FLAG_THRESHOLD,
    }


def diagnose(root: Path) -> dict[str, Any]:
    names = _clip_names(root / "bank/tiers/tier_mixed100.txt")
    infeasible = _feasibility(root / "reports/feasibility_e3/feasibility.csv")
    sidecars = [
        _sidecar_stats(
            root / "reports/eligibility/tier_mixed100_guard0_bin50" / f"{name}.json"
        )
        for name in names
    ]
    soft = [row["soft_mean"] for row in sidecars]
    rejected = [row["soft_rejected_conditional"] for row in sidecars]
    hard = [row["hard_fraction"] for row in sidecars]
    output: list[dict[str, Any]] = []
    baseline_preflight: list[dict[str, Any]] = []

    for seed in SEEDS:
        baseline_matches = sorted(
            root.glob(
                f"logs/rsl_rl/g1_tracking/*grounded-mixed100-s{seed}/model_3999_exposure.json"
            )
        )
        if len(baseline_matches) == 1:
            baseline_ledger = json.loads(baseline_matches[0].read_text())
            if baseline_ledger["clip"] != names:
                raise ValueError(
                    f"baseline seed {seed}: ledger clip order differs from frozen bank"
                )
            baseline_failure = _recover_failure(
                [float(value) for value in baseline_ledger["sampling_weight"]],
                [1.0] * len(names),
            )
            baseline_preflight.append(
                {
                    "seed": seed,
                    "available": True,
                    "soft_counterfactual": _counterfactual(
                        names, baseline_failure, soft, rejected, infeasible
                    ),
                    "hard_counterfactual": _counterfactual(
                        names, baseline_failure, hard, [0.0] * len(names), infeasible
                    ),
                }
            )
        else:
            baseline_preflight.append(
                {
                    "seed": seed,
                    "available": False,
                    "reason": "grounded baseline predates per-checkpoint exposure ledgers",
                }
            )

        matches = sorted(
            root.glob(
                f"logs/rsl_rl/g1_tracking/*fgas-soft-mixed100-s{seed}/model_3999_exposure.json"
            )
        )
        if len(matches) != 1:
            raise ValueError(f"seed {seed}: expected one final ledger, found {matches}")
        ledger = json.loads(matches[0].read_text())
        if ledger["clip"] != names:
            raise ValueError(f"seed {seed}: ledger clip order differs from frozen bank")
        probability = [float(value) for value in ledger["sampling_weight"]]
        failure = _recover_failure(probability, soft)
        reconstructed = sum(
            prob * bad for prob, bad in zip(probability, rejected, strict=True)
        )
        logged = _last_logged_mass(
            root / f"logs/campaign/fgas-soft-mixed100-s{seed}.log"
        )
        contributions = sorted(
            (
                {
                    "clip": name,
                    "contribution": prob * bad,
                    "sampling_mass": prob,
                    "conditional_rejected": bad,
                    "infeasible_frac": infeasible[name],
                    "soft_mean": weight,
                }
                for name, prob, bad, weight in zip(
                    names, probability, rejected, soft, strict=True
                )
            ),
            key=lambda row: row["contribution"],
            reverse=True,
        )
        counterfactuals = {
            "soft_power_1_observed": _counterfactual(
                names, failure, soft, rejected, infeasible
            ),
            "soft_power_2": _counterfactual(
                names,
                failure,
                [value**2 for value in soft],
                [row["soft_power_2_rejected_conditional"] for row in sidecars],
                infeasible,
            ),
            "hard_bin_start": _counterfactual(
                names, failure, hard, [0.0] * len(names), infeasible
            ),
            "clip_flag_gate": _counterfactual(
                names,
                failure,
                [
                    weight if infeasible[name] <= FLAG_THRESHOLD else 0.0
                    for name, weight in zip(names, soft, strict=True)
                ],
                rejected,
                infeasible,
            ),
        }
        output.append(
            {
                "seed": seed,
                "final_logged_mass": logged,
                "final_reconstructed_mass": reconstructed,
                "absolute_error": abs(logged - reconstructed),
                "top_contributors": contributions[:5],
                "counterfactuals": counterfactuals,
            }
        )

    flat = _counterfactual(names, [0.0] * len(names), soft, rejected, infeasible)
    max_reconstruction_error = max(row["absolute_error"] for row in output)
    if max_reconstruction_error >= 0.005:
        raise AssertionError(
            f"sampler reconstruction differs from telemetry by {max_reconstruction_error}"
        )
    return {
        "diagnosis": "soft-mask accounting reconstruction",
        "flat_projection": flat,
        "preexisting_grounded_failure_preflight": baseline_preflight,
        "max_final_reconstruction_error": max_reconstruction_error,
        "seeds": output,
        "conclusion": (
            "Telemetry matches the frozen sampler: this is not a stalled run or an accounting "
            "fault. Failure adaptation overwhelms a clip-mean soft multiplier and shifts mass "
            "toward partially eligible clips, so the flat projection is not a late-run bound. "
            "A hard-bin start mask makes rejected-start mass zero, but can legitimately retain "
            "clip-level flagged leaders because it preserves their feasible segments."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = diagnose(args.root)
    rendered = json.dumps(result, indent=1)
    print(rendered)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n")


if __name__ == "__main__":
    main()
