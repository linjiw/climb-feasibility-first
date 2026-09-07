# Relative-progress signal diagnosis and next experiment

Date: 2026-09-05. Classification: **measured exploratory diagnostic** and
**pending prospective implementation**. This is an unsealed addendum to
`RESEARCH_DESIGN_RELATIVE_PROGRESS_2026-09-05.md` and
`RELATIVE_PROGRESS_R1_RESULT_2026-09-05.md`; it changes no bound profile,
queued study, historical seal, or policy endpoint.

## Research finding

R1 showed sustained reallocation on seed 11, but allocation alone does not show
that the selected units are useful practice. We inspected the saved sampler
histories after reproducing the complete R1 decision, without parsing policy
outcomes or using the GPU.

For unit i at saved snapshot t, signed progress is the recent estimated success
rate minus its value ten sampler ticks earlier. Absolute progress is its
magnitude. Let p be the actual sampling distribution and b the deployment
prior. The diagnostic partitions **positive excess mass**, max(p_i-b_i, 0), by
positive, negative, or unchanged signed progress. It does not count the fraction
of all sampled trials that improve or decline.

| Quantity | Measured summary | Scope |
| --- | --- | --- |
| Positive excess mass assigned to declining success estimates | 0.4660473 | Unweighted mean of 37 post-warm-up snapshot fractions |
| Spearman correlation of adjacent absolute-progress rankings | 0.4223621 | Unweighted mean across 36 adjacent saved snapshot pairs |
| Absolute progress versus conditional failure rate | 0.2814350 | Mean of 37 within-snapshot Spearman correlations |
| Absolute progress versus recent attempt count | 0.4607236 | Mean of 37 within-snapshot correlations; exposure is endogenous |
| Fixed D weights applied to R's recorded histories: TV | 0.0859453 | Exploratory counterfactual snapshot mean; **not a D training result** |

Snapshots and units are correlated. No p-values, confidence intervals, or
independent-replication claim are attached to these descriptive summaries.
Declining estimates may reflect forgetting, stochastic estimation error, or
changes in policy behavior; this is not evidence of wasted practice. The
attempt-count association cannot identify whether exposure causes measured
progress. The counterfactual keeps R's histories fixed and cannot predict D's
live allocation or learning outcome.

Artifacts: `reports/relative_progress_2026-09-05/rank_signal_s11/result.json`,
`snapshots.csv`, and `rank_signal.{png,pdf}`. The result binds the diagnostic
source, original complete decision, and individual ledger/state identities.

Exact CPU command (a reproduction requires a fresh output directory):

```bash
mjlab-1.6.0/.venv/bin/python tools/analyze_relative_rank_signal.py \
  --result reports/relative_progress_2026-09-05/study_s11/long_result.json \
  --out-dir reports/relative_progress_2026-09-05/rank_signal_s11
```

## Decision and execution

Keep the fixed relative-ALP candidate. Do not tune it using this diagnostic.
The result supports retaining D as the already planned mechanism comparator:
does relative progress help beyond conditional failure ranking with a matched
pre-cap mixture coefficient? R versus D still differs in startup history and
cap-floor decomposition, so it is not a strictly rank-only ablation.

The dependency order remains:

1. Complete unchanged independent relative-ALP seed 12 and reproduce its gate.
2. Run U/A/R/D lifecycle smokes, each seed 41, 8 environments, 20 iterations.
3. Run the one fixed D candidate on fresh calibration seeds 31 and 32, each
   512 environments and 4,000 iterations. No outcome-driven candidate selection
   or parameter changes are permitted. Each seed needs all 41 checkpoint-linked
   snapshots, exact probability replay, valid accounting, zero invalid/censored
   events, mean post-warm-up TV >= 0.05, minimum effective units >= 12, final
   saturation < 0.9, and the fixed floor/caps. D has no 0.15 upper-TV restriction.
4. Only after those passes, finish and test the confirmation runner and complete
   analysis contract, then freeze them before fresh confirmation training.

`tools/run_relative_failure_calibration.py` now implements step 3 and is queued
behind step 2. It replays the four smokes, checks bound sources, waits for at
least 14,000 MiB free GPU memory and at most 60% utilization, and runs the two D
seeds sequentially. A failed prerequisite or failed calibration stops promotion.
It launches no confirmation or policy evaluation.

Exact supervisor invocation already launched (do not duplicate):

```bash
mjlab-1.6.0/.venv/bin/python tools/run_relative_failure_calibration.py \
  --smoke-dir /home/linjiw/climb-feasibility-first/reports/relative_progress_2026-09-05/policy_smokes \
  --out-dir /home/linjiw/climb-feasibility-first/reports/relative_progress_2026-09-05/failure_calibration
```

Launch identity: `failure_calibration_launch.json`, PID at launch 1062984.
Immutable execution source bindings: `failure_calibration/design.json`.
Live log: `failure_calibration_launcher.log`. The eventual per-seed command
records will contain exact trainer argv/environment, task
`Climb-Tracking-Flat-Unitree-G1-Policy-D-Development`, and artifact locations.
At 17:03 EDT, replication, smoke and calibration supervisors were alive;
replication was waiting for GPU availability and its downstream stages had
not run. Absence of a terminal artifact is not a pass.

## Campaign analysis implementation and remaining work

`tools/analyze_relative_campaign.py` is a development prototype for the outer
real-artifact loader. Before parsing any endpoint CSV it checks prospective
contract identity, both relative replications, both D calibrations, all 41
training snapshots for every arm/seed, and the complete paired 48 evaluation
cells. It cross-links checkpoints to training ledgers, requires advancing
sampler clocks/trial totals, and checks the 100-clip reference-defined 25/75
strata. CSV hashes are checked again immediately before parsing. Aggregation
retains failed conditions and rejects missing or duplicate observations.

The prototype implements the proposed confirmation manipulation gates:
minimum post-warm-up effective units >= 12 for every arm; U maximum TV <= 0.01;
R mean TV in [0.05,0.15] and final saturation < 0.9; D mean TV >= 0.05 and final
saturation < 0.9. A's weak adaptation is a descriptive result and does not
suppress the primary R-U comparison. These rules require inclusion in the
future freeze; their presence in development code is not a preregistration.

After full preflight, the loader uses the existing paired-training-seed
statistical kernel for final-iteration R-U TrackingScore, SESOI +0.02, and
all-panel noninferiority margin -0.01. It adds descriptive learning curves,
survived-horizon fraction, per-clip paired deltas, and normalized trapezoidal
learning-curve area over iterations 1000 through 3999 only. Intermediate
checkpoints do not select the primary checkpoint.

Tests cover the aggregation and failure ordering, CLI failure output, real
sampler-state replay using synthetic trial histories, stale history rejection,
and invalid events between evaluation checkpoints. Aggregation tests stub the
complete preflight; the independent provenance component tests exercise the
cell verifier. **No complete real confirmation campaign or full end-to-end
campaign fixture has passed this loader.**

Remaining before confirmation: end-to-end campaign contract/fixture and source
closure audit; confirmation-enabled trainer with campaign digest in every
ledger; matched launch/evaluation scheduler; denominator-preserving quality and
work secondary reducers; actual lifecycle/calibration results; and a
prospective freeze with input/software/source hashes and execution-cost
accounting. Current bound development profiles keep confirmation disabled.
Independent replication and policy benefit both remain pending.

Verification record: `reports/relative_progress_2026-09-05/signal_and_calibration_verification.json`.
The integrated ten-file suite passed **90 tests in 23.62 s**, changed Python
files compile, whitespace checks pass, and all 41 existing Phase-G sealed
artifacts are unchanged. Synthetic test outcomes are not experimental evidence.
