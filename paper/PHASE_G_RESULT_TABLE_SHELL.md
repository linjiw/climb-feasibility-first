# Phase-G result tables — frozen topology, no results

**Status:** unsealed table shell, 2026-09-04. Every result cell is intentionally `pending`.
This file defines what will be reported; it is not evidence that a run occurred. Rows may not be
removed after results are known. Any additional analysis must be labelled exploratory.

## Table G-A — endpoint-blind ALP calibration

**Caption.** Sampler-only manipulation measurements for all 12 declared ALP configurations on
screen seed 20260903. TV is distance from G1's deployment-uniform distribution over 368,951
legal starts aggregated into 1,184 units. Values are read at PPO iterations 30/40/49. No reward,
survival, checkpoint evaluation, or tracking endpoint is available to the selector.

| candidate | exploration `rho` | ALP floor `lambda` | TV 30 | TV 40 | TV 49 | TV mean ± SD | min effective units | max top-1 | invalid/censored | final saturation | pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| rho005_floor0001 | 0.05 | 0.001 | pending | pending | pending | pending | pending | pending | pending | pending | pending |
| rho005_floor0010 | 0.05 | 0.010 | pending | pending | pending | pending | pending | pending | pending | pending | pending |
| rho005_floor0050 | 0.05 | 0.050 | pending | pending | pending | pending | pending | pending | pending | pending | pending |
| rho010_floor0001 | 0.10 | 0.001 | pending | pending | pending | pending | pending | pending | pending | pending | pending |
| rho010_floor0010 | 0.10 | 0.010 | pending | pending | pending | pending | pending | pending | pending | pending | pending |
| rho010_floor0050 | 0.10 | 0.050 | pending | pending | pending | pending | pending | pending | pending | pending | pending |
| rho020_floor0001 | 0.20 | 0.001 | pending | pending | pending | pending | pending | pending | pending | pending | pending |
| rho020_floor0010 | 0.20 | 0.010 | pending | pending | pending | pending | pending | pending | pending | pending | pending |
| rho020_floor0050 | 0.20 | 0.050 | pending | pending | pending | pending | pending | pending | pending | pending | pending |
| rho040_floor0001 | 0.40 | 0.001 | pending | pending | pending | pending | pending | pending | pending | pending | pending |
| rho040_floor0010 | 0.40 | 0.010 | pending | pending | pending | pending | pending | pending | pending | pending | pending |
| rho040_floor0050 | 0.40 | 0.050 | pending | pending | pending | pending | pending | pending | pending | pending | pending |

Selection is deterministic among passing rows: nearest mean TV to 0.10, then smallest TV SD,
then declared row order. A row passes only if mean TV is in `[0.05, 0.15]`, each TV is in
`[0.025, 0.20]`, effective units are at least 12, top-1 is at most 0.05, invalid/censored count
is zero, and final saturation is below 0.90.

## Table G-B — independent manipulation validation

**Caption.** The single selected configuration repeated on independent seed 20260904 using the
same sampler-only gates. A failed row returns Phase G to design and cannot be replaced by the
next-best screen row after inspecting policy endpoints.

| selected candidate | screen pass | validation TV 30/40/49 | validation TV mean ± SD | min effective units | max top-1 | invalid/censored | final saturation | validation pass |
|---|---|---|---:|---:|---:|---:|---:|---|
| pending | pending | pending | pending | pending | pending | pending | pending | pending |

## Table G-B2 — exploratory rank agreement

**Caption.** Sampler-only Spearman agreement at every post-warm-up G2 ledger among raw absolute
learning progress (before the floor, exploration mixture, and caps), conditional failure, and
the `p(1-p)` competence-frontier score. This table has no threshold and cannot select a setting,
open an endpoint, or alter the Phase-G verdict. `undefined` is printed when a score is constant.

| seed | iteration | units | rho(ALP, failure) | rho(ALP, p(1-p)) | rho(failure, p(1-p)) | status |
|---:|---:|---:|---:|---:|---:|---|
| 1 | pending | pending | pending | pending | pending | exploratory |
| 2 | pending | pending | pending | pending | pending | exploratory |
| 3 | pending | pending | pending | pending | pending | exploratory |

Additional checkpoint rows are printed rather than averaged away. If seed 3 is dropped under the
predeclared budget fallback, its row remains and is marked `not run`.

## Table G-C — confirmation manipulation gate

**Caption.** Post-warm-up sampler telemetry for G1 and G2. Each row names the actual PPO,
environment, and sampler seed. The provenance column requires all four declared evaluation
checkpoints to match their hash-bound training ledger, evaluator metadata, conditions, and
active/common references. Endpoint rows remain unparsed unless every available row passes.

| arm | seed | calibrated parameters match | PPO/env/sampler seed match | mean TV | min effective units | max top-1 | invalid frames | censored resets | final saturation | evaluation provenance | gate |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|---|
| G1 deployment-uniform | 1 | pending | pending | pending | pending | pending | pending | pending | pending | pending | pending |
| G2 ALP | 1 | pending | pending | pending | pending | pending | pending | pending | pending | pending | pending |
| G1 deployment-uniform | 2 | pending | pending | pending | pending | pending | pending | pending | pending | pending | pending |
| G2 ALP | 2 | pending | pending | pending | pending | pending | pending | pending | pending | pending | pending |
| G1 deployment-uniform | 3 | pending | pending | pending | pending | pending | pending | pending | pending | pending | pending |
| G2 ALP | 3 | pending | pending | pending | pending | pending | pending | pending | pending | pending | pending |

## Table G-D — primary and declared secondary contrasts

**Caption.** Paired closed-loop simulation contrasts over the hash-bound 100-clip panel and
three training seeds. The primary estimate uses the 25 reference-defined feasible-hard clips;
the independent unit is the clip within training seed, resampled by a seed-then-clip hierarchical
bootstrap with 10,000 draws. TrackingScore is
`h * exp(-MPKPE/0.30 m - anchor_angle/0.40 rad)`, including failures through survived-horizon
fraction `h`. Values are G2 minus G1 unless the comparator column says otherwise.

| priority | population | metric | comparator | estimate | 95% CI | SESOI/margin | decision |
|---|---|---|---|---:|---:|---:|---|
| primary | feasible-hard 25 | TrackingScore at iteration 3999 | G2 − G1 | pending | pending | +0.02 | pending |
| key secondary | feasible-hard 25 | survival | G2 − G1 | pending | pending | +0.05 | pending |
| key secondary | all 100 | TrackingScore at iteration 3999 | G2 − G1 | pending | pending | descriptive | pending |
| key secondary | all 100 | survival | G2 − G1 | pending | pending | descriptive | pending |
| key secondary | feasible-hard 25 | TrackingScore AULC, iterations 1000/2000/3000/3999 | G2 − G1 | pending | pending | descriptive | pending |

## Table G-E — common-survivor non-harm

**Caption.** Relative G2-minus-G1 differences on feasible-hard conditions survived by both arms.
Lower is better. The number of common-survivor clips is printed because these metrics are
conditioned on survival. Non-harm requires the 95% CI upper bound below +10% for every row.

| metric | common-survivor clips / 25 | relative estimate | 95% CI | +10% margin passed |
|---|---:|---:|---:|---|
| root-relative body MPKPE | pending | pending | pending | pending |
| anchor orientation error | pending | pending | pending | pending |
| absolute mechanical work per actuator | pending | pending | pending | pending |

## Table G-F — contact-timing instrument and exploratory contrast

**Caption.** Contact timing is reported only through the fixed source-hash-bound kinematic proxy
and the blinded held-out validation in `plan/G_CONTACT_TIMING_VALIDATION.md`. Events are matched
one-to-one at ±2 frames (40 ms), separately by foot and touchdown/liftoff. Empty/empty windows do
not receive perfect F1. Until the instrument row says `validated`, every policy row is
exploratory and cannot affect the Phase-G verdict.

| stage / population | comparison | reference events / minimum subgroup | micro-F1 | minimum subgroup F1 | median timing error | status / 95% CI |
|---|---|---:|---:|---:|---:|---|
| held-out instrument panel | rater A vs rater B | pending | pending | pending | pending | pending |
| held-out instrument panel | fixed proxy vs consensus | pending | pending | pending | pending | pending |
| feasible-hard common survivors | G2 − G1 contact-event F1 | pending | pending | pending | pending | pending |
| all-panel common survivors | G2 − G1 contact-event F1 | pending | pending | pending | pending | pending |

## Exhaustive status line

Exactly one Phase-G status is reported: `positive`, `null`, `inconclusive`, or `not_tested`.
`Not tested` includes low treatment separation, concentration/cap failure, rank saturation,
invalid or censored trials, calibration-file mismatch, parameter mismatch, seed mismatch, or
evaluation-provenance mismatch. G0 was removed before sealing because its uniform-over-clips
sampler and G1's uniform-over-legal-starts sampler confound support hygiene with clip-duration
exposure; no G1−G0 result may be added to this table after readout.
Contact timing remains exploratory unless its source-hash-bound reference labels are validated
before the seal.
