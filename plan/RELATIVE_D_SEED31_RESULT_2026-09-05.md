# Fixed D baseline: first complete calibration result

Date: 2026-09-05. Classification: **measured exploratory calibration; second seed pending**.
This unsealed addendum continues the fixed four-arm research plan. No profile,
threshold, assigned seed, runtime source or sealed artifact changes.

## Complete result

Conditional-failure baseline D seed 31 completed all 4,000 iterations with 512
environments at 22:21:40 EDT. The complete saved decision reproduces through
`verify_calibration`, including all 41 checkpoint/ledger/sampler bindings,
source identities, exact probabilities, trial accounting, exploration floor
and unit/clip caps. Every recorded invalid-start, invalid-reference and
censored-reset counter is zero.

| Quantity | Complete seed-31 result |
| --- | ---: |
| Mean post-warm-up TV | 0.0849553389 |
| Post-warm-up TV range | [0.0083016899, 0.1182816177] |
| Minimum post-warm-up entropy-effective units | 625.061738 |
| Maximum post-warm-up unit mass | 0.0172129278 |
| Maximum post-warm-up clip mass | 0.0172129278 |
| Final saturation | 0.727195946 |
| Completed trials | 1,113,773 |
| Post-warm-up snapshots / all snapshots | 37 / 41 |
| Full calibration decision | calibration_pass |

The fixed gate constrains the mean TV, not every individual snapshot; early
post-warm-up values below 0.05 do not fail it. D has no 0.15 upper-TV gate.
Effective-unit minimum and probability extrema above use iterations at least
400; invalid/censored counters are checked throughout.

One full training attempt ran for 2,229 seconds, or 0.619167 elapsed GPU-hours.
The execution log reports shared-device baseline memory 388 MiB and peak total
memory 9,519 MiB. These are scoped job-time/memory records, not isolated GPU
usage, energy or evidence that D trains faster than R. The full job command,
environment and task ID are in
`reports/relative_progress_2026-09-05/failure_calibration_gate_retry/seed31_launch.json`:
`Climb-Tracking-Flat-Unitree-G1-Policy-D-Development`, seed 31, 512 environments,
4,000 iterations. Original result, execution design and log remain preserved.

## What the comparison establishes

The two completed R probes have mean TV 0.0832114 and 0.0827283; D seed 31 has
mean TV 0.0849553. The mean magnitudes are close descriptively, but these are
unequal development replications with different seeds. They are not a paired
method comparison, a significance test or evidence of similar policy quality.

The complete histories expose a temporal difference: D's TV is 0.0083017 at
iteration 400 and reaches 0.1182816 at the final checkpoint, whereas R already
has substantial allocation contrast early in training. Similar averages do not
mean matched sampling distributions or identical exposure schedules. Preserve
the existing qualification that R−D is not a strictly rank-only ablation because
startup and floor/cap composition differ. Do not tune either method to force
its curve to resemble the other after seeing these histories.

The next scientific question remains policy utility: does relative progress
improve held-out feasible-hard tracking over U at the fixed budget, while
satisfying the all-panel guard, and how do the descriptive R−A/R−D contrasts
inform the mechanism? One D calibration pass makes this baseline more credible
as an actual nonuniform intervention. Its planned second seed is still required.
No policy outcome was evaluated in this review.

## Figure and evidence

`paper/figures/relative_calibration_comparison.py` accepts only complete results
that reproduce through the existing R or D verifiers. It preserves each seed
separately, rejects duplicates and records exact result/design/log identities.
The exportable figure was visually checked. The dashed TV line marks the
minimum post-warm-up **mean**, and the saturation limit applies at the final
snapshot. No upper-TV band for D is drawn.

Artifact directory: `reports/relative_progress_2026-09-05/failure_seed31_review/`.

- `result.json`: three verified complete histories and scoped costs.
- `snapshots.csv`: all 123 snapshots, labeled by method and seed.
- `allocation_comparison.png` and `.pdf`: allocation, support and saturation.
- `freeze_readiness.json`: unchanged draft preflight and exact remaining evidence.
- `verification.json`: targeted test, compilation, whitespace and seal checks.

Exact reproduction command:

```bash
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 mjlab-1.6.0/.venv/bin/python paper/figures/relative_calibration_comparison.py --relative-results reports/relative_progress_2026-09-05/study_s11/long_result.json reports/relative_progress_2026-09-05/continuation_gate_retry/study_s12/long_result.json --failure-results reports/relative_progress_2026-09-05/failure_calibration_gate_retry/seed31_result.json --failure-design reports/relative_progress_2026-09-05/failure_calibration_gate_retry/design.json --out-dir reports/relative_progress_2026-09-05/failure_seed31_review
```

Output directories are exclusive; use a fresh directory when reproducing.
Tests check actual D replay, rejection of a rehashed changed summary, missing
execution design and duplicated replication. Existing calibration tests cover
scientific and bookkeeping failures.

## Next execution and freeze plan

Seed 32 launched at 22:24:12 EDT under the unchanged supervisor and is running.
The new-trainer smoke supervisor still waits for both fixed D passes. Its
U/A/R/D seed-51 lifecycle runs require eight environments, 20 iterations and
both checkpoint ledgers. No additional training is launched by this review.

After all remaining prerequisites pass:

1. Replay complete D seed-32 and all four seed-51 results; do not rely on terminal
   status strings alone. Verify their design/source and checkpoint bindings.
2. Preserve the current draft. Create a new profile copy with only
   `confirmation.enabled` changed to true, bind all completed prerequisite
   records, and reproduce the twelve unchanged configuration hashes.
3. Verify the actual bank/reference inputs, runtime inventory, adapter and
   analysis identities. Record the prospective contract and a new seal before
   any seed 21–23 training. Never amend the Phase-G seal.
4. Run the strict full contract verifier, then launch the existing fixed schedule
   once: 12 training runs, all manipulation gates, then 48 paired evaluations.
   Keep all startup-pairing and provenance checks before outcome aggregation.

If the second D calibration or a lifecycle check fails, preserve the failure
and follow its declared stop rule; a new baseline or scientific retry requires
a new prospective design. The precision audit's hypothetical scenarios do not
justify optional seed additions or weaker decision thresholds. Confirmation
remains disabled in the current draft, and tracking benefit remains pending.


Verification: **11 targeted tests passed in 12.51 s**; compilation, whitespace
and all 41 sealed Phase-G identity checks pass. Queued runtime sources remain
unchanged. The prior integrated suite result remains a separate verification.
