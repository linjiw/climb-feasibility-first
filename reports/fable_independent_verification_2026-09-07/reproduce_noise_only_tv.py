#!/usr/bin/env python3
"""Reproduce the illustrative stationary Gaussian null; no robot rollouts."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.integrate import quad


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=260906)
    parser.add_argument("--repetitions", type=int, default=2000)
    parser.add_argument("--units", type=int, default=1184)
    args = parser.parse_args()
    if args.repetitions < 2 or args.units < 2:
        parser.error("at least two repetitions and units required")
    mean = math.sqrt(2 / math.pi)
    analytical = 0.2 * (math.erf(mean / math.sqrt(2)) - 1 + math.exp(-mean**2 / 2))
    integrand = lambda x: abs(x / mean - 1) * mean * math.exp(-x*x / 2)
    numerical = 0.1 * (quad(integrand, 0, mean)[0] + quad(integrand, mean, np.inf)[0])
    np.testing.assert_allclose(analytical, numerical, atol=1e-12, rtol=0)
    samples = abs(np.random.default_rng(args.seed).standard_normal((args.repetitions, args.units)))
    relative = samples / samples.mean(axis=1, keepdims=True)
    tv = 0.1 * abs(relative - 1).mean(axis=1)
    scaled = samples * 1e-9
    np.testing.assert_allclose(relative, scaled / scaled.mean(axis=1, keepdims=True), atol=1e-14)
    # Direct probabilities independently verify the TV coefficient.
    p = (0.8 + 0.2 * relative) / args.units
    np.testing.assert_allclose(tv, 0.5 * abs(p - 1 / args.units).sum(axis=1), atol=1e-14)
    result = {
        "classification": "synthetic illustration; not frozen-policy robot evidence",
        "assumptions": ["independent equal-variance Gaussian signed changes",
                        "equal prior mass", "inactive caps", "positive noise amplitude"],
        "seed": args.seed, "repetitions": args.repetitions, "units": args.units,
        "analytical_large_unit_tv": analytical, "quadrature_tv": numerical,
        "finite_unit_mean_tv": float(tv.mean()),
        "finite_unit_sd_tv": float(tv.std(ddof=1)),
        "monte_carlo_standard_error": float(tv.std(ddof=1) / math.sqrt(args.repetitions)),
        "replicate_tv_quantiles_025_50_975": np.quantile(tv, [0.025, 0.5, 0.975]).tolist(),
        "fraction_above_005": float((tv > 0.05).mean()),
        "limitations": "No actual prior, estimator history, event process, caps, or policy learning; do not subtract this null from observed TV.",
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "numpy_version": np.__version__,
        "confirmation_transitions": 4 * 3 * 4000 * 512 * 24,
        "proposed_branch_transitions": 2 * 3 * 4 * 100 * 512 * 24,
        "branch_to_confirmation_fraction": (2 * 3 * 4 * 100) / (4 * 3 * 4000),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
