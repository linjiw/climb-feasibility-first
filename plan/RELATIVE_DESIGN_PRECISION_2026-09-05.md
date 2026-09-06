# Prospective precision audit for the fixed R3 comparison

Date: 2026-09-05. Classification: **hypothetical design sensitivity; no measured policy outcomes**.
This addendum continues `RELATIVE_DEVELOPMENT_SMOKES_2026-09-05.md`. It does
not change the assigned seeds, methods, budget, primary endpoint, effect target
or non-regression margin. No evaluator CSV, checkpoint or training trajectory
was used to choose the hypothetical effects or variances below.

## What the current experiment can resolve

The most promising next scientific question remains whether relative-progress
allocation improves tracking over uniform allocation and conditional-failure
allocation at the same training budget. Two development seeds already support
sustained allocation contrast. The pending comparison has three independent
paired training seeds, not 2,800 independent policy replications. Its precision
therefore depends strongly on consistency across seeds.

The existing analyzer uses a two-sided 95% Student-t interval with two degrees
of freedom. Its half-width is **2.4841377 times the sample SD of the three paired
seed deltas**. This is calculated from the already implemented rule, not an
estimate of actual variability. For an observed hard-panel mean of +0.02,
positive lower confidence bound requires sample SD **strictly below 0.0080511**.
At an observed all-panel mean of zero, clearing the −0.01 non-regression margin
requires sample SD **strictly below 0.0040255**. Merely observing a positive mean
does not satisfy the declared benefit rule.

The quantile calculation uses SciPy's documented
[Student-t distribution](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.t.html).
The normal-model marginal calculations use the documented
[noncentral t representation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.nct.html)
and an independent quadrature calculation for the additional mean-effect gate.
The local report records installed package versions; no environment was upgraded.

## Hypothetical operating scenarios

Assume independent, identically distributed normal paired-seed deltas. Means
and population SDs in this table are **illustrative assumptions**, not fitted
values or predictions for these policies. The normal model does not enforce the
bounded support of score differences. Conditional on all manipulation/provenance
gates passing, the hard-panel benefit event is:

```
mean(seed deltas) >= 0.02
and mean(seed deltas) - t_0.975,2 * sample_sd / sqrt(3) > 0
```

| Hypothetical true hard-panel R−U mean | Hypothetical paired-seed population SD | Probability of hard-panel benefit gate |
| ---: | ---: | ---: |
| +0.02 | 0.01 | 30.8889% |
| +0.02 | 0.02 | 14.7528% |
| +0.04 | 0.01 | 90.8375% |
| +0.04 | 0.02 | 46.6744% |

These are probabilities for one necessary gate, **not full campaign power**.
The all-panel non-regression requirement can be more restrictive. For example,
assuming true all-panel mean zero and population SD 0.01, its probability of
passing is 17.8610%. Even if the hypothetical hard-panel mean is +0.04 with SD
0.01, full positive-decision probability cannot exceed 17.8610%. Without
specifying the dependence between panel summaries, the corresponding Frechet
bounds are [8.6985%, 17.8610%]. Do not multiply the two marginal probabilities
and call the result campaign power: the hard clips are part of the full panel.
The bounds also condition on passing all non-statistical gates.

For calculation, under the normal model the sample mean and sample variance
are independent. Let `q = df * sample_sd^2 / sigma^2`, distributed chi-square(df).
The benefit probability integrates the conditional normal tail above
`max(0.02, tcrit * sigma * sqrt(q/df) / sqrt(3))` over q. The non-regression
probability is the noncentral-t survival probability at tcrit with noncentrality
`(true_panel_mean + 0.01) * sqrt(3) / sigma`. Normal simulations independently
check the quadrature for four scenarios; they are mathematical checks only.

## Research decision

Keep the current three-seed comparison and thresholds fixed. Use it to report
effect sizes, all individual seed deltas, uncertainty and the declared decision.
A small or inconsistent benefit can remain inconclusive; that outcome does not
establish equivalence or show that progress contains no useful information.
Do not replace seed uncertainty with a clip-only bootstrap or use a favorable
secondary comparison to override the primary decision.

If the completed comparison is inconclusive, separate the next questions:

- A larger precision study would require a new prospective sample-size plan,
  fixed budget and independent seeds. Do not append seeds until the current
  result becomes positive or reinterpret this audit as authorization to do so.
- A progress-versus-noise study would require repeated fixed-policy trials or a
  shuffled-rank control. More confidence in an R−U mean alone cannot establish
  ranking informativeness, and the existing decline-share diagnostic does not
  distinguish forgetting from estimation noise.

The immediate execution sequence remains D calibration seeds 31/32, new-trainer
seed-51 lifecycle smokes, prospective confirmation freeze, then all 12 training
runs before any fixed-panel evaluation. D seed 31 is still running at this
addendum's preparation; only its complete predeclared calibration decision can
advance the downstream experiment.

## Reproducibility and artifacts

Figure script: `paper/figures/relative_design_precision.py`.

```bash
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 mjlab-1.6.0/.venv/bin/python paper/figures/relative_design_precision.py --out-dir reports/relative_progress_2026-09-05/design_precision
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 mjlab-1.6.0/.venv/bin/python -m pytest tests/test_relative_design_precision.py -q
```

Output directory: `reports/relative_progress_2026-09-05/design_precision/`.
`result.json` contains assumptions, exact numerical values, source hashes and
package versions. `hypothetical_primary.csv` contains all 24 illustrative
scenarios. `design_precision.png` and `.pdf` show separate gate probabilities
and are explicitly labeled hypothetical, not campaign power. The figure was
visually checked. Fourteen focused tests passed; exact combined verification
commands and outputs are recorded in `verification.json`.

No queued runtime source changed. The figure script lives with manuscript figure
sources, outside the runtime inventory. All results in this addendum are
prospective model calculations; none adds a measured tracking-performance claim.
