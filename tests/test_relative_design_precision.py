"""Check prospective sensitivity math against normal simulation and the fixed kernel."""

from pathlib import Path
import sys

import numpy as np
import pytest
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "paper/figures"))
import relative_design_precision as design
from analyze_relative_policy import seed_summary


def test_critical_value_matches_fixed_seed_interval():
    result = seed_summary(np.array([0.01, 0.02, 0.03]))
    assert result["seed_t_95ci"][1] - result["mean"] == pytest.approx(design.CRITICAL * 0.01 / np.sqrt(3))
    assert design.DF == 2 and design.N == 3


@pytest.mark.parametrize("sigma", (0.005, 0.01, 0.02, 0.04))
def test_null_ci_type_one_probability(sigma):
    assert design.lower_bound_probability(0.0, sigma, 0.0) == pytest.approx(0.025)


@pytest.mark.parametrize("delta,sigma", [(0.0, 0.01), (0.02, 0.01), (0.04, 0.02), (0.06, 0.04)])
def test_integral_matches_independent_normal_simulation(delta, sigma):
    values = np.random.default_rng(20260906).normal(delta, sigma, size=(200_000, 3))
    mean, sd = values.mean(axis=1), values.std(axis=1, ddof=1)
    passed = (mean >= design.SESOI) & (mean - design.CRITICAL * sd / np.sqrt(3) > 0)
    probability = design.benefit_probability(delta, sigma)
    tolerance = 6 * np.sqrt(max(probability * (1-probability), 1e-6) / len(mean))
    assert abs(passed.mean() - probability) < tolerance
    assert probability <= design.lower_bound_probability(delta, sigma, 0.0) + 1e-10
    assert probability <= norm.sf((design.SESOI-delta)/(sigma/np.sqrt(3))) + 1e-10


def test_joint_bounds_contain_independent_gate_product():
    result = design.full_positive_bounds(0.04, 0.02, 0.0, 0.01)
    independent = result["benefit_probability"] * result["nonregression_probability"]
    assert 0 <= result["full_positive_lower_bound"] <= independent <= result["full_positive_upper_bound"] <= 1


@pytest.mark.parametrize("delta,sigma", [(0.0, 0.0), (0.0, -1.0), (float("nan"), 0.01), (0.0, float("inf"))])
def test_invalid_hypothetical_parameters_rejected(delta, sigma):
    with pytest.raises(ValueError):
        design.benefit_probability(delta, sigma)
