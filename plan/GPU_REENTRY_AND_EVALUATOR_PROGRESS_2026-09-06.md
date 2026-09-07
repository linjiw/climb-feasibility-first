# GPU execution reentry and development evaluator integration

Date: 2026-09-06. **Unsealed execution addendum.** The user explicitly requested
experiment execution after GPU capacity became available. Contract
`8f2192a9b937060a9ba6aa4fbd1b4a6aed8a7da183abf1c64fa9db557a5af013`
continues to govern confirmation. No scientific parameter or sealed source changes.

## Original stop and authorized reentry

The overnight scheduler stopped at 03:03 with `GPU availability deadline; job
not launched`. The complete original terminal records zero completed jobs and no
endpoint access; the partial manifest has empty U/A/R/D arms. Its directory has
only the schedule, partial manifest and terminal. The downstream pilot stopped
while waiting for confirmation; the efficiency worker recorded `unavailable`.
All these records remain unchanged. There was no partial scientific run to retry.

After the user's instruction and verification of those artifacts, the unchanged
scheduler was relaunched into
`reports/relative_progress_2026-09-05/confirmation_freeze/campaign_gpu_reentry_2026-09-06/`.
The only operational changes are the output directory and the per-job GPU wait
allowance, increased from 7,200 to 86,400 seconds. The original 14,000 MiB free
memory / utilization ≤60% gate is unchanged. Every scientific job still has a
single attempt. An exact recursive comparison confirms all 60 jobs match the old
schedule after substituting the campaign output path alone.

U seed 21 launched on the GPU. At the 10:41:51 EDT verified snapshot its latest
complete checkpoint was iteration **1700 of final 3999**, with **498,543 completed
trials**, **193,875 failed trials**, and zero invalid starts, invalid reference
frames or censored resets. These are **interim training telemetry**. The complete
training/manipulation gate and policy benefit remain pending. No confirmation
endpoint-access record exists. Snapshot:
`reports/gpu_reentry_2026-09-06/execution_snapshot.json`.

Its task ID is `Climb-Tracking-Flat-Unitree-G1-Policy-U-Confirmation`; the
trainer's exact command is in the new campaign schedule and U21 log.

At 10:46:32 EDT, checkpoint 2000 also passed content-hash verification and all
76 saved tensors were finite. Its cumulative 575,886 trials include 201,403
failures and zero invalid/censored events. This later **interim** record is
`reports/gpu_reentry_2026-09-06/execution_snapshot_2000.json`; the earlier snapshot
remains preserved. It is not the full 4,000-iteration gate or a policy result.

The existing rotation/order, U/A/R/D × seeds 21/22/23, 512 environments, 4,000 PPO
iterations, and all 12 training gates before the 48 evaluation cells remain fixed.
Do not interpret a running queue or an intermediate checkpoint as a completed arm.

## Downstream continuation restored

A new pilot queue design points to the reentry campaign's terminal, retains the
exact original two scientific jobs and all 520 original dependency bindings, and
uses a fresh operational queue directory. Its scientific output directories were
verified absent before launch. The old stopped queue and its design are retained.
The two jobs are still the GPU instrumentation smoke followed by the fixed
512-environment / 100-tick frozen-policy pilot; neither is a stationary-noise study.

The new `tools/follow_confirmation_reentry.py` in the isolated ICRA worktree waits
for the named campaign's terminal. On completion it invokes the unchanged full
campaign verifier/analyzer, requires exact reproduction of the saved analysis,
then calls the already tested descriptive efficiency kernel. A stopped/invalid
campaign remains unavailable. It cannot launch or retry scientific jobs. This
avoids rewriting the old efficiency worker's hard-coded campaign or source hashes.

Exact argv/PIDs, input hashes, logs and schedule comparison:
`reports/gpu_reentry_2026-09-06/{launch.json,followups_launch.json,schedule_equivalence.json}`.
The pilot and efficiency wait allowances are operational limits, not changed
statistical thresholds. Queues remain subject to their existing failure stops.

## Completed independent CPU work: actual paired-evaluator integration

The new `tools/eval_physics_development.py` wraps the original paired evaluator in
an isolated process. Scoped environment/entity/wrapper instrumentation installs
the already verified S1 operators, records startup and first-policy inputs, and
captures desired targets, realized controls and forces at every physics substep.
Original modules are restored on context exit; original source files are untouched.

Development inputs were fixed before these runs: R11 at iteration 2000 from the
existing hash-bound checkpoint inventory; the first two clips in the fixed
800-clip training list; phases 0 and 0.5; one replicate per start; one-second
windows; CPU; environment seed **26090651** and joint-noise seed **26090652**.
The clips are explicitly checked disjoint from the 100-clip held-out panel.
This is a small development lifecycle, not a new evaluation population.
The evaluator task ID is `Climb-Tracking-Flat-Unitree-G1`; the adapter condition
is recorded separately in each cell's receipt and tensor trace.

The unmodified original evaluator and all eight adapter conditions completed:
**9 cells × 4 episode rows = 36 rows**, each with the full 50-step horizon and
nonzero clip-level tracking. All 36 rows survived their one-second horizon.
The unchanged adapter CSV matches the original evaluator **byte for byte**.

All eight adapter conditions have identical pre-intervention startup randomization
and CPU RNG state, initial qpos/qvel, first observations and first actions. Each
records **200 physics substeps × 4 worlds**; the command delays exactly replay
the requested 0/1/2/4-step lag. Every recorded force stays within the corresponding
actuator clamp. Named knee limits, foot coefficients and untargeted values are
independently checked; startup/initial-state telemetry agrees with the original
evaluator's own metadata hashes. No confirmation outcome was opened.

These positive development rows are an instrumentation check, not a filter for
future efficacy data: a zero score or failure must remain in the full study's
declared denominator. The original scorer is reused with the development window
explicitly set to one second; confirmation's three-second scoring is unchanged.

## What these traces do and do not establish

In the unchanged run, the largest absolute knee force was **86.40794 N·m**.
The knee-only 120/90 N·m conditions never bound the policy torque and their output
CSVs match the unchanged run. They therefore do not demonstrate that reduced
actuation has no effect on difficult motions. Their force-limit implementation
was exercised by the earlier deliberate saturation fixture.

The 20 ms delay run reached **139 N·m**, with **11 of 1,600 knee force samples**
at or above 98% of the configured limit. This is a measured telemetry response
on one development policy and two selected training clips, not an independent
statistical finding or a robustness/safety claim. Do not extrapolate from the
36/36 short-window survival result to physical transfer.

Remaining gates: explicit actor/normalizer tensor immutability receipts; policy
trajectories that exercise failure/retirement/reset handling; GPU graph and
same-input zero-intervention checks; and a separate prospective freeze before
the full physical-sensitivity policy grid. No S1 GPU job displaces confirmation.
The matched gate study remains the next full training comparison; the fixed
noise pilot retains its place immediately after confirmation.

## Artifacts and verification

New code is in `/home/linjiw/climb-icra-evidence-2026-09-06`; all development
designs, exact per-cell argv, raw logs, CSVs, metadata and tensor traces are in
its `reports/physics_evaluator_development_2026-09-06/`. The complete independent
result is `verification.json`, generated by `tools/analyze_physics_development.py`.

Fifteen tests pass: actual schedule equivalence, stopped-campaign access controls,
dependency/contract rejection, complete measured evaluator verification and
eight corrupted policy-telemetry cases. Compilation and whitespace checks pass;
all 376 original runtime file hashes and both checked seals remain unchanged.
Original-repository operational evidence and exact verification commands are in
`reports/gpu_reentry_2026-09-06/verification.json` and its README.
