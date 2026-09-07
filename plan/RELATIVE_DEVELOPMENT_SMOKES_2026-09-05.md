# Four-arm lifecycle results and next research gate

Date: 2026-09-05. Classification: **measured development simulation and CPU lifecycle verification**.
This unsealed addendum continues `RELATIVE_EVALUATOR_ADAPTER_2026-09-05.md`.
No method setting, queued runtime source, sealed file or manifest changes.

## Completed evidence

All four planned seed-41 development smokes completed and their complete saved
results reproduce under the original source-bound verifier. Each ran eight
parallel environments for 20 PPO iterations, retained checkpoints 0 and 19,
completed trials, and had zero invalid starts, invalid reference frames or
censored resets. Checkpoint/state identities and exact sampler replay pass.

| Arm | Completed trials at iteration 19 | Elapsed job seconds | Decision |
| --- | ---: | ---: | --- |
| U deployment-uniform | 191 | 20 | smoke_pass |
| A absolute-floor ALP | 183 | 21 | smoke_pass |
| R relative ALP | 177 | 18 | smoke_pass |
| D conditional failure rate | 198 | 16 | smoke_pass |

Trial counts are lifecycle counters; unequal counts in this very short run are
not a method comparison. Low short-smoke TV does not trigger tuning. Total
elapsed job time is 75 seconds (0.020833 elapsed GPU-hours), across these four
smokes only. It excludes waiting, previous studies, full D calibration and CPU
engineering. The shared-device time is not isolated GPU-active time or energy.
Exact commands, task IDs, source bindings, checkpoints and cost logs are retained
in `reports/relative_progress_2026-09-05/development_smoke_review/result.json` and
the original `policy_smokes_gate_retry/{U,A,R,D}_launch.json` files. Task IDs are
`Climb-Tracking-Flat-Unitree-G1-Policy-{U,A,R,D}-Development`, seed 41.

The actual iteration-19 checkpoints from all four smokes also load on CPU
through the same registered runner and exact strict actor-only call used by the
sealed evaluator. Every actor tensor, including observation normalization, is
restored exactly. Critic parameters remain unchanged; the training iteration is
not restored, while the existing runner restores its environment step counter.
The returned actor is in evaluation mode. No policy forward call or rollout is
performed. The environment supplies only fixed zero tensors with the observed
checkpoint dimensions: actor 160, critic 286, actions 29. This is serialization
and loading evidence, not a runtime observation or physical-behavior check.

`tests/test_relative_checkpoint_loading.py` implements the audit and verifies
that missing normalization and incompatible actor input dimensions fail strict
loading. `development_smoke_review/checkpoint_loading.json` binds the actual
checkpoint and audit/runtime sources. Targeted verification plus the existing
evaluator adapter/interface checks: **27 tests passed in 3.31 s**. Python
compilation, whitespace and all 41 sealed Phase-G checks pass. Exact commands
and outputs are in `development_smoke_review/verification.json`. The prior
175-test integrated run is a separate completed verification, not rerun here.

## Current experiment

D calibration seed 31 started through the existing supervisor and is training
with the unchanged conditional-failure profile, 512 environments and 4,000
iterations. At 21:57:36 EDT, its latest complete saved snapshot was iteration
2100, with 607,883 completed trials and zero invalid/censored events. This is
an **interim operational snapshot**, not a complete calibration pass.
`development_smoke_review/execution_snapshot.json` binds that ledger and verifies
that both the running calibration sources and prepared runtime inventory are
unchanged. Seed 32 and the new trainer's seed-51 smokes remain downstream.

Do not interpret interim allocation statistics or training rewards as a policy
result. The existing supervisor makes the complete seed-31 decision, then runs
seed 32 only on a pass. Both full histories must pass the fixed minimum mean TV,
effective-support and final-saturation gates. Neither this progress review nor
checkpoint-loading success changes those gates.

## Next research decision

The most promising immediate test remains the fixed U/A/R/D comparison at equal
training steps. Two relative-progress development seeds already establish
sustained allocation contrast; policy value and progress-ranking utility still
need the held-out comparison. Keep the exact gate, relative rule, failure
baseline, estimator and assigned seeds fixed.

| Next evidence | Decision |
| --- | --- |
| Either fixed D calibration fails its complete scientific gate | Stop this four-arm candidate campaign. Record failure; do not tune D or relabel a weak baseline after seeing its trajectory. Any revised baseline requires a new prospective study. |
| Both D calibrations and all new seed-51 trainer smokes pass | Bind actual prerequisite decisions, preserve the current runtime, and create a new prospective frozen confirmation contract before using seeds 21–23. |
| Confirmation training or provenance gate fails | Preserve the not-tested/invalid disposition and keep aggregation closed; do not substitute a checkpoint or add seeds. |
| Valid final R−U comparison | Apply the already declared +0.02 benefit target and −0.01 all-panel non-regression rule with training-seed uncertainty; report each seed, including negative or inconclusive results. |
| R does not improve over D, or any apparent benefit remains ambiguous | A separate prospective repeated-rollout noise study or shuffled-rank control can examine whether progress adds information beyond difficulty. Current diagnostics alone cannot distinguish forgetting from noise. |

The fixed benchmark evaluator runs only after all 12 training gates pass; all
48 paired startup identities must agree before aggregation. CPU actor loading
does not authorize early held-out scoring. The remaining runtime dependency is
new-trainer simulator validation; actual benchmark rollout and policy utility
remain pending. The active downstream worker remains
`confirmation_entrypoint_smokes_adapter`, PID 1541297 at this snapshot, waiting
for the original fixed-D supervisor. Confirmation remains disabled in the draft.
