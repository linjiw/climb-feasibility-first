# Relative-progress manipulation replicated

Date: 2026-09-05. **Measured exploratory simulation result. Policy benefit pending.**
This addendum updates `RELATIVE_CONFIRMATION_READINESS_2026-09-05.md` and the
original relative-progress design without changing their bound sources or any
sealed artifact.

## Result and bounded claim

Both planned development seeds pass the complete manipulation gate. Under the
fixed exact-support G1 training setup, relative ALP sustains capped nonuniform
allocation in two independent seed runs. This supports moving to the fixed
baseline-calibration stage. It does not establish better tracking, informative
progress rankings, transfer to another bank, or physical-robot performance.

| Full-run quantity | Seed 11 | Seed 12 |
| --- | --- | --- |
| Post-warm-up mean TV | 0.0832113932 | 0.0827283432 |
| Snapshot TV range | 0.0489606–0.1082347 | 0.0507759–0.1013988 |
| Minimum entropy-effective units | 616.249846 | 618.611481 |
| Maximum unit probability | 0.0177383 | 0.0223513 |
| Maximum clip probability | 0.0184985 | 0.0223513 |
| Final saturation fraction | 0.7373311 | 0.7331081 |
| Completed trials | 1,087,814 | 1,086,192 |
| Invalid starts / invalid frames / censored resets | 0 / 0 / 0 | 0 / 0 / 0 |
| Checkpoint snapshots / post-warm-up snapshots | 41 / 37 | 41 / 37 |
| Complete decision | manipulation pass | manipulation pass |

Probability maxima and minimum effective units are over the 37 post-warm-up
snapshots. The TV interval gate applies to the run mean, not every snapshot.
Each full run uses 512 environments and 4,000 iterations. Seed 12 completed at
19:26:40 EDT, rc=0. Both original smoke/long results were reproduced again
before this review was recorded in `reports/relative_progress_2026-09-05/replication_review.json`.
The existing replication figure, with PNG/PDF/CSV and provenance, is under
`continuation_gate_retry/replication_figure/`.

## Ranking diagnostic across both seeds

Apply the same descriptive computation to seed 12 without changing any
candidate or baseline setting. Values are unweighted means of correlated
snapshot statistics; no p-values or population-level inference are attached.

| Diagnostic | Seed 11 | Seed 12 | Valid observations per seed |
| --- | --- | --- | --- |
| Declining-success share of positive excess probability mass | 0.4660473 | 0.4680896 | 37 snapshots |
| Adjacent absolute-progress ranking Spearman correlation | 0.4223621 | 0.4029245 | 36 snapshot pairs |
| Absolute progress versus conditional failure rate | 0.2814350 | 0.2747052 | 37 snapshots |
| Absolute progress versus newly completed attempts since prior saved snapshot | 0.4607236 | 0.4469226 | 36 snapshot pairs |
| Fixed D allocation on recorded R histories: mean TV | 0.0859453 | 0.0849016 | 37 snapshots; counterfactual only |

The first row's denominator is probability mass above the deployment prior,
not all training draws. Negative success-rate change can reflect forgetting,
estimation noise, or other policy changes. Attempt-count correlation includes
endogenous sampling exposure. The D calculation fixes R's histories and is not
a D training result. These patterns justify keeping the strong failure-rate
comparison; they do not show that selected practice helps or is wasted.

Comparison table: `replicated_rank_diagnostic.csv`. Seed-12 artifacts:
`rank_signal_s12_corrected/{result.json,snapshots.csv,rank_signal.png,rank_signal.pdf}`.
The initial seed-12 figure had a hardcoded “Seed 11” title, although its JSON
correctly identified seed 12. The original image/source and a correction record
are preserved under `rank_signal_s12/`; corrected numerical fields and CSV bytes
are identical. Use the corrected figure for presentation.

**Denominator correction to the earlier diagnostic addendum:** the
attempt-count correlation uses 36 adjacent-snapshot intervals per seed,
not 37 observations. The first saved snapshot has no previous attempt count.
The earlier numeric mean is unchanged. Progress-versus-failure and excess-mass
summaries do use 37 snapshots. This corrects wording in
`RELATIVE_SIGNAL_DIAGNOSIS_2026-09-05.md` and its corresponding results-log row.

## Input and execution-cost work completed

`tools/check_relative_inputs.py` passed a CPU-only reference audit: all 900
motion hashes match (800 training, 100 evaluation), name/content overlap is
zero, and all 2,800 conditions reconstruct exactly from the current 100
evaluation motion headers. The 100-clip panel and reference-defined 25/75
strata retain their identities. The audit constructs no simulator and opens no
policy endpoint. Its measured report is `replication_reference_audit.json`;
`confirmation_ready` remains false.

`tools/analyze_relative_cost.py` now accounts for completed, failed, OOM, and
never-launched attempts without silently dropping consumed compute. Across the
two named full relative probes, elapsed training time is 2,680 + 3,373 = 6,053 s,
or 1.681389 elapsed GPU-hours. The intervening prelaunch GPU poll miss launched
no training and contributes zero training time. Scope excludes smokes, waiting,
engineering, evaluation and historical development studies. Shared-GPU elapsed
time is not utilization-adjusted compute or energy; memory values are for the
whole shared device, not isolated allocator overhead. There is no speedup claim.
Report: `replication_execution_cost.json`.

The developing campaign analyzer now requires successful execution logs linked
to each run's checkpoint directory and training seed, and reports per-run costs
and the total for the 12 confirmation runs. Its source contract must bind the
cost analyzer. Corrupt time/memory arithmetic, repeated/incomplete launches,
failed training terminals and substituted run logs are rejected before policy
aggregation. Synthetic integration fixtures exercise the new contract.

## Next experimental step

At 20:25 EDT, the existing four-arm smoke worker (launch PID 1091692) and D
calibration worker (1091693) were alive with unchanged source bindings. Smokes
wait for the shared-GPU gate; D calibration waits for all four smokes. Continue
with the one fixed D profile on seeds 31 and 32, each 512 environments / 4,000
iterations. No candidate search or setting change follows these diagnostics.

If those stages pass, finish the campaign-bound confirmation trainer/scheduler,
audit its runtime dependencies and robot assets, and freeze the complete
protocol before seeds 21/22/23 train. The primary comparison remains final
R-U TrackingScore on reference-feasible-hard clips; R-D is the planned
descriptive test of value beyond conditional failure ranking. An R-U win alone
does not identify accurate progress ranking. The shuffled-rank/noise follow-up
remains a separate prospective study if that mechanism question remains open.

No confirmation training or policy evaluator has launched. E4's sealed
`not_tested` disposition and unopened policy endpoints remain unchanged.

## Verification and reproduction

**121 tests passed in 107.28 s**, including the complete synthetic campaign,
cost-log substitution/failure cases and exact condition reconstruction. Python
compilation, whitespace checks and all 41 existing Phase-G sealed identities
pass. Exact commands, test environment and source hashes:
`reports/relative_progress_2026-09-05/replication_audit_and_cost_verification.json`.

CPU commands executed (reproduction needs fresh output destinations):

```bash
mjlab-1.6.0/.venv/bin/python tools/check_relative_inputs.py \
  --out reports/relative_progress_2026-09-05/replication_reference_audit.json

OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 mjlab-1.6.0/.venv/bin/python \
  tools/analyze_relative_rank_signal.py \
  --result reports/relative_progress_2026-09-05/continuation_gate_retry/study_s12/long_result.json \
  --out-dir reports/relative_progress_2026-09-05/rank_signal_s12_corrected

mjlab-1.6.0/.venv/bin/python tools/analyze_relative_cost.py \
  --log R1_long=reports/relative_progress_2026-09-05/study_s11/long.log \
  --log R2_prelaunch_stop=reports/relative_progress_2026-09-05/continuation_recovery/study_s12/smoke.log \
  --log R2_long=reports/relative_progress_2026-09-05/continuation_gate_retry/study_s12/long.log \
  --scope 'Two full relative-ALP probes and the intervening unlaunched R2 gate miss; excludes smokes, queue time, engineering, and historical studies' \
  --out reports/relative_progress_2026-09-05/replication_execution_cost.json
```
