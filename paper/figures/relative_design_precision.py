#!/usr/bin/env python3
"""Prospective normal-model sensitivity for the fixed three-seed R3 decision.

No measured outcome or fitted variance is read. This figure script leaves the
training design unchanged and reports marginal gates, not joint campaign power.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import scipy
from scipy.integrate import quad
from scipy.stats import chi2, nct, norm, t

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from analyze_relative_policy import NONREGRESSION_MARGIN, SEEDS, SESOI

N = len(SEEDS)
DF = N - 1
CRITICAL = float(t.ppf(0.975, DF))


def validate(delta: float, sigma: float) -> None:
    if not np.isfinite([delta, sigma]).all() or sigma <= 0:
        raise ValueError("finite hypothetical mean and positive seed SD required")


def lower_bound_probability(delta: float, sigma: float, boundary: float) -> float:
    """Normal paired-seed model: probability the two-sided lower CI clears a bound."""
    validate(delta, sigma)
    if not np.isfinite(boundary):
        raise ValueError("finite boundary required")
    return float(nct.sf(CRITICAL, DF, (delta - boundary) * np.sqrt(N) / sigma))


def benefit_probability(delta: float, sigma: float) -> float:
    """P(sample mean >= SESOI and lower 95% t bound > 0), before the all-panel guard."""
    validate(delta, sigma)
    se = sigma / np.sqrt(N)
    cutoff = DF * (SESOI / (CRITICAL * se)) ** 2
    fixed = chi2.cdf(cutoff, DF) * norm.sf((SESOI - delta) / se)
    adaptive, error = quad(lambda q: norm.sf(CRITICAL * np.sqrt(q / DF) - delta / se)
                          * chi2.pdf(q, DF), cutoff, np.inf, epsabs=1e-10, epsrel=1e-10)
    if error > 1e-7:
        raise ArithmeticError("quadrature error exceeds tolerance")
    return float(fixed + adaptive)


def full_positive_bounds(hard_delta: float, hard_sigma: float,
                         panel_delta: float, panel_sigma: float) -> dict:
    """Frechet bounds avoid inventing dependence between hard and all-panel deltas."""
    benefit = benefit_probability(hard_delta, hard_sigma)
    guard = lower_bound_probability(panel_delta, panel_sigma, NONREGRESSION_MARGIN)
    return {"hard_delta": hard_delta, "hard_sigma": hard_sigma,
            "panel_delta": panel_delta, "panel_sigma": panel_sigma,
            "benefit_probability": benefit, "nonregression_probability": guard,
            "full_positive_lower_bound": max(0.0, benefit + guard - 1.0),
            "full_positive_upper_bound": min(benefit, guard)}


def generate(out: Path) -> dict:
    """Write hypothetical tables and an exportable figure; never read checkpoints."""
    out.mkdir(parents=True, exist_ok=False)
    sigmas = (0.005, 0.01, 0.02, 0.04)
    deltas = (0.0, 0.01, 0.02, 0.03, 0.04, 0.06)
    rows = [{"true_hard_delta": delta, "paired_seed_sd": sigma,
             "benefit_gate_probability": benefit_probability(delta, sigma),
             "lower_ci_above_zero_probability": lower_bound_probability(delta, sigma, 0.0),
             "negative_for_SESOI_probability": lower_bound_probability(SESOI - delta, sigma, 0.0)}
            for sigma in sigmas for delta in deltas]
    with (out / "hypothetical_primary.csv").open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    joint_bounds = [full_positive_bounds(delta, sigma, 0.0, sigma)
                    for sigma in sigmas for delta in (0.02, 0.04)]
    report = {"classification": "prospective hypothetical normal-model sensitivity; not measured policy evidence",
              "assumptions": ["Independent identically distributed normal paired training-seed deltas.",
                              "Means and SDs are illustrative choices, not fitted from any training or evaluation outcomes.",
                              "Normal approximation does not enforce bounded score differences.",
                              "Hard-panel and all-panel dependence is unspecified; only marginal and Frechet bounds are given.",
                              "All training/provenance gates are assumed passed; these probabilities exclude their failures."],
              "seed_count": N, "df": DF, "two_sided_95_t_critical": CRITICAL,
              "ci_half_width_per_sample_sd": CRITICAL / np.sqrt(N),
              "sesoi": SESOI, "nonregression_margin": NONREGRESSION_MARGIN,
              "max_sample_sd_for_positive_lower_ci_at_mean_SESOI": SESOI * np.sqrt(N) / CRITICAL,
              "max_sample_sd_for_nonregression_at_zero_mean": -NONREGRESSION_MARGIN * np.sqrt(N) / CRITICAL,
              "inequalities": "Sample SD must be strictly below these boundary values.",
              "primary_scenarios": rows, "hypothetical_zero_panel_mean_bounds": joint_bounds,
              "software": {"numpy": np.__version__, "scipy": scipy.__version__},
              "source_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                                (Path(__file__).resolve(), ROOT / "tools/analyze_relative_policy.py")},
              "references": ["https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.t.html",
                             "https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.nct.html"],
              "policy_endpoints_opened": False, "design_changed": False}
    with (out / "result.json").open("x") as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write("\n")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    grid = np.linspace(0, 0.06, 81)
    for sigma in sigmas:
        axes[0].plot(grid, [benefit_probability(delta, sigma) for delta in grid], label=f"Seed SD {sigma:g}")
        axes[1].plot(grid - 0.02, [lower_bound_probability(delta - 0.02, sigma, NONREGRESSION_MARGIN)
                                 for delta in grid], label=f"Seed SD {sigma:g}")
    axes[0].axvline(SESOI, color="gray", ls=":", lw=1)
    axes[1].axvline(NONREGRESSION_MARGIN, color="gray", ls=":", lw=1)
    axes[0].set(title="Hard-panel benefit gate", xlabel="Hypothetical true hard-panel R−U delta")
    axes[1].set(title="All-panel non-regression gate", xlabel="Hypothetical true all-panel R−U delta")
    for ax in axes:
        ax.set(ylim=(0, 1), ylabel="Probability of passing this gate")
        ax.grid(alpha=0.2)
    axes[0].legend(fontsize=8, loc="lower right")
    fig.suptitle("Three seeds: hypothetical normal-model sensitivity\nSeparate gates; neither curve is full campaign power", fontsize=11)
    fig.savefig(out / "design_precision.png", dpi=180)
    fig.savefig(out / "design_precision.pdf")
    plt.close(fig)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    result = generate(args.out_dir.resolve())
    print(json.dumps({key: result[key] for key in ("seed_count", "ci_half_width_per_sample_sd",
                      "max_sample_sd_for_positive_lower_ci_at_mean_SESOI", "design_changed")}, indent=2))
