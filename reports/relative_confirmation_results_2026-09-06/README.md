# Complete frozen confirmation: inconclusive

Measured simulation result, independently reproduced 6 September 2026 at 23:47
EDT. This supersedes the dated 22:17 pending snapshot, without revising its record
or the scientific contract. All 12 U/A/R/D training runs and all 48 held-out cells
are complete. Each trained policy receives 49,152,000 simulator transitions;
training gates reproduce across 492 saved states. Replication is three paired
training seeds, not the number of clips, conditions or saved checkpoints.

## Primary decision and secondary context

| Final feasible-hard R−U | TrackingScore difference |
| --- | ---: |
| Seed 21 | −0.0339989641 |
| Seed 22 | −0.0329896648 |
| Seed 23 | +0.0217832511 |
| Mean | −0.0150684593 |
| Two-sided paired seed t 95% CI, df=2 | [−0.0943584262, +0.0642215077] |

The frozen mean target (+0.02) and positive lower confidence bound do not pass.
The all-panel mean is −0.0093155064, with 95% t interval
[−0.1140463277, +0.0954153149]; its lower-bound guard (>−0.01) also does not pass.
**Registered disposition: inconclusive.** These wide intervals establish neither
benefit nor harm nor equivalence, and do not rule out the target-sized benefit.
Failure to establish non-regression is not proof of regression.

The supplementary paired hierarchical bootstrap gives primary interval
[−0.0441687771, +0.0253212228] and all-panel interval
[−0.0476823380, +0.0331136615]. It cannot override the registered decision.
Descriptive final hard R−D is −0.0067457302, interval
[−0.0218939085, +0.0084024482]; all three seed differences are negative.
R−A is −0.0066807407, interval [−0.0724286375, +0.0590671560]. These compare
allocator designs, not solely the quality of their rankings.

Exploratory normalized feasible-hard learning-curve area over checkpoints
1000–3999 gives R−U differences −0.0397784738, −0.0304155926 and −0.0167598578.
Mean −0.0289846414, descriptive 95% t interval
[−0.0577406023, −0.0002286806]. This is an exploratory secondary, with no
multiplicity-adjusted confirmatory harm claim. The campaign does not support an
efficiency-accelerator narrative. Two R seeds never attain their paired U final
score on the observed grid. Four checkpoints do not identify a precise crossover;
retain every non-attainment in `efficiency_descriptive.json`.

The figure `paired_results_and_learning_curves.pdf` / `.png` shows both primary
panels and all four learning curves. Points in the first panels are seed pairs;
the diamond and bar are their mean and two-sided t interval. Dashed lines mark
the hard point-estimate target and all-panel lower-bound margin. Thin learning
curves are individual seeds; thick curves are means. The x axis counts simulator
transitions, including the zero-indexed checkpoint convention. No pre-1000 area
or interpolated attainment result is inferred.

## Exact replay and preserved postprocessing failure

Campaign: `reports/relative_progress_2026-09-05/confirmation_freeze/campaign_gpu_reentry_2026-09-06/`.
Original complete `analysis.json` SHA-256:
`2d1703da6d2d40fad9f9b17ffcf9d12036c4aaea917fb1054e81c91ed22bf3be`.
Campaign manifest SHA-256:
`80c3ed6f26e9026ae8b12793cb63cdc4ea43ff8fc8ee131893bed7b0df0ef401`.
Frozen contract SHA-256:
`8f2192a9b937060a9ba6aa4fbd1b4a6aed8a7da183abf1c64fa9db557a5af013`.

The queued efficiency worker reported `postprocessing_failed` because its raw
Python comparison treated the analyzer's `seed_order` tuple as unequal to the
saved JSON list. The isolated `replay_serialized_confirmation.py` compares the
full analyzer output in its exact JSON representation. Every numeric value
matches, with no tolerance relaxation. The sole representation difference is
`$.analysis.seed_order`. Five targeted tests cover representation equivalence,
numeric changes, nonfinite values and incomplete-campaign rejection.

The original worker, source bindings and failed terminal record are unchanged.
Successful replay and complete supplementary output:
`reports/continuous_execution_preparation_2026-09-06/serialized_confirmation_replay/verification.json`.
This receipt, `summary.json`, `learning_curves.csv`, and
`efficiency_descriptive.json` are the sources for the current interpretation.

## What this changes

The allocation manipulation worked, but the registered policy benefit is not
established. Preserve this disposition; do not append seeds, change R or use a
secondary endpoint to relabel it. Before another full allocator campaign,
diagnose whether apparent progress predicts useful additional practice.

The separate continuous-execution CPU development adapter now completes four
attempts on two fully admitted training references (8.58 and 6.12 seconds), with
no active resets or reference-state rewrites. It uses one development policy,
R11 checkpoint 2000, and establishes pipeline continuity only. The existing
held-out evaluator already ran three-second windows; this follow-up genuinely
extends the duration. Failure-path runtime coverage, CUDA conformance, fixed
held-out continuous-reference selection and the U/D/R comparison remain pending.

The frozen-policy instrumentation pilot completed; stationarity/noise-floor
estimation remains unestablished. Original CUDA lifecycle validation failed an
assertion requiring a camera/raycast sense graph absent from this contact-only
task. A separately bound optional-sensor correction passes seven targeted tests.
Its first reentry launched no cell because the unchanged GPU capacity gate failed;
a bounded wait queue preserved both stopped attempts and retried no cell.
That queue subsequently completed all nine development cells, then failed the
aggregate original/unchanged exact CSV parity check. Individual cell lifecycle
replay and per-field control differences are recorded in
`reports/continuous_execution_preparation_2026-09-06/gpu_followup_diagnosis.json`.
No numeric parity tolerance changed. Full physical-sensitivity evaluation stays
disabled, and the cause of the numerical control differences remains unresolved.

Next priorities are continuous-execution validation and H1 admission value, then
independent signal scoring and a prospectively fixed practice intervention. The
September 10 claim selection and September 12 evidence cutoff are recorded in
`plan/USEFUL_PRACTICE_SUBMISSION_2026-09-06.md`. Hardware access and transfer remain
unconfirmed. This result currently supports a bounded study of practice allocation,
not the proposed positive curriculum-benefit conclusion.
