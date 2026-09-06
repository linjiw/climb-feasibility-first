# Relative-progress confirmation execution plan

Date: 2026-09-05. Classification: **prospective implementation; confirmation pending**.
This unsealed addendum extends `RESEARCH_DESIGN_RELATIVE_PROGRESS_2026-09-05.md`
and `RELATIVE_CONFIRMATION_READINESS_2026-09-05.md`. Existing sealed decisions,
source-bound development designs, profiles and measured results are unchanged.

## Research decision

Continue with scale-relative learning-progress allocation inside the exact
legal-start gate. Both planned development seeds sustain allocation contrast:
mean post-warm-up TV is 0.0832114 and 0.0827283. The necessary manipulation now
replicates, but useful learning has not been demonstrated. Nearly 47% of
positive excess mass goes to declining success estimates in each history;
forgetting and estimation noise remain competing explanations. The next
scientific test is the fixed four-arm policy comparison, with a conditional
failure-rate baseline to test whether progress offers value beyond difficulty.
The completed result and diagnostic limitations are recorded in
`RELATIVE_PROGRESS_REPLICATION_RESULT_2026-09-05.md`.

Keep the chosen relative rule and baseline settings fixed. Do not use the
diagnostics to add a noise threshold, change the relative factor, or select
favorable checkpoints. A later repeated-rollout noise study or shuffled-rank
control is a separate prospective study if the policy comparison warrants it.

## Fixed experiment

| Item | Contract |
| --- | --- |
| Arms | U deployment-uniform; A absolute-floor ALP; R relative ALP; D conditional failure rate |
| Training | Fresh seeds 21/22/23, 512 environments, 4,000 iterations per arm; identical non-sampler configuration |
| Support | Same 800 motions, exact legal starts, 50-transition trials, rewards, PPO and randomization |
| Evaluation | Same 100 held-out motions, 25 reference-defined feasible-hard motions and 2,800 paired conditions |
| Checkpoints | 1000, 2000, 3000, 3999; all 12 training histories must pass before any of the 48 evaluation cells launch |
| Primary | Final R−U hard-panel TrackingScore; training seed is the independent replication |
| Decision | Fixed SESOI +0.02, positive lower seed-level 95% bound, all-panel non-regression lower bound above −0.01 |
| Uncertainty | Three paired seeds, t interval with 2 degrees of freedom; paired hierarchical bootstrap is supplementary |
| Secondaries | R−A/R−D, learning curves, common-success pose with coverage, work with failed conditions and exposure, scoped training cost |

The full decision logic remains in the existing design and analysis code.
Three seeds give limited precision. R−D is not a pure ranking-only intervention:
startup behavior and cap/floor composition also differ. Neither a TV pass nor a
synthetic analyzer test establishes policy benefit, energy efficiency, hardware
transfer, or a new general learning-progress principle.

## Implemented execution path

`tools/train_relative_confirmation.py` builds fixed configurations through the
same environment factory as development. Its CLI accepts an arm, an assigned
seed, a contract identity and an output directory. It starts fresh and binds
each checkpoint ledger to the campaign, configuration, profile, sources and
actual sampler state. The ledger verifier reproduces sampler probabilities and
checks event accounting. New-schema campaign analysis now also invokes the
strict launch-contract verifier before outcome aggregation.

`tools/relative_confirmation_setup.py` records canonical configuration hashes,
source identities, runtime Python sources, G1 assets, installed package versions
and GPU/driver identity. The prepared inventory contains **375 files**, including
**36 G1 assets**. Compiled third-party libraries and driver binaries are recorded
by version rather than content; callable configuration identities depend on
the separately hashed source. This is not a bitwise simulator determinism claim.

`tools/run_relative_confirmation.py` constructs a deterministic 60-job schedule.
Training order rotates across seeds: 21 uses U/A/R/D, 22 uses A/R/D/U, and 23
uses R/D/U/A. Three seeds do not fully balance four execution positions. All
12 training jobs precede evaluation. Every job checks source and prerequisite
bindings, waits for at least 14,000 MiB free and at most 60% utilization, validates
again, and rechecks GPU availability before starting. This shared-device check
is not an atomic resource reservation. Per-job wait defaults to two hours.

Each scientific job launches once. Failures stop execution and preserve logs
and a partial manifest; no automatic training restart, checkpoint substitution,
optional extra seeds or outcome-driven retry is implemented. A later restart
requires a documented review of what actually launched. Failed evaluator launches
conservatively mark endpoint access. Negative and inconclusive valid analyses
remain completed results. The cost ledger reports elapsed job time and shared
device memory, with its existing scope limits.

## Prepared artifacts and CPU evidence

Artifact root: `reports/relative_progress_2026-09-05/confirmation_preparation/`.

- `draft_contract.json`: configuration and input bindings; status **draft**.
- `runtime_inventory.json`: content hashes and version records.
- `schedule_preview.json`: exact commands for 12 training and 48 evaluation jobs.
- `entrypoint_smoke_preview.json`: exact seed-51 U/A/R/D lifecycle commands.
- `preparation_result.json`: prepared counts and remaining requirements.
- `cpu_preflight_result.json`: actual-bank preflight pass and launch rejection.

The actual draft reproduces the 900-motion/2,800-condition reference audit,
the runtime inventory and all 12 configuration hashes without constructing a
simulator. A confirmation launch correctly rejects this draft. The original
profile contract retains `confirmation.enabled=false`; preparation launched no
training or evaluation jobs. Preview confirmation commands intentionally cannot
execute until a new prospective frozen contract is prepared.

Tests cover configuration parity with development, non-sampler equality across
arms, seed restrictions, changed rewards/profile rejection, fixed scheduling,
prelaunch GPU changes, single-launch failures, endpoint-access accounting, and
the actual new ledger writer/replay for all four arms using synthetic trials.
Controller tests stub child execution and evidence checks; their scope is
explicit. The earlier full synthetic campaign exercises real scientific and
provenance gates but uses its legacy contract schema. A positive complete run
through the new frozen-contract branch and actual simulator/evaluator remain
pending. Synthetic checkpoint bytes and histories are not policy evidence.
Integrated verification: **152 tests passed in 109.93 s**; Python compilation
and whitespace checks pass; all 41 sealed Phase-G artifacts are unchanged.
Exact verification commands and source hashes are recorded in
`reports/relative_progress_2026-09-05/confirmation_execution_verification.json`.

## GPU sequence and remaining decisions

1. Existing seed-41 U/A/R/D lifecycle worker completes after GPU availability.
2. Existing fixed D calibration completes seeds 31 and 32. Both must pass their
   predeclared complete-history gates; no upper TV bound of 0.15 is imposed on D.
3. `tools/run_relative_entrypoint_smokes.py` waits for both actual D passes and
   then runs the new trainer on U/A/R/D using seed 51, eight environments and
   20 iterations. Exact task IDs are
   `Climb-Tracking-Flat-Unitree-G1-Policy-{U,A,R,D}-ConfirmationSmoke`.
   Each requires checkpoints 0/19, completed trials, zero invalid/censored
   events, source/configuration identity and exact sampler replay.
4. Audit the complete new frozen-contract/evaluator integration, bind the
   completed calibration and entrypoint-smoke artifacts, and create a new
   prospective confirmation contract before using seeds 21–23.
5. Execute the fixed comparison, report every assigned seed and the declared
   decision, then decide whether further progress-signal diagnostics are justified.

The entrypoint supervisor has a six-hour prerequisite wait and a six-hour
availability wait for each smoke. It never launches confirmation automatically.
Its launch record, PID and exact argv belong in
`reports/relative_progress_2026-09-05/confirmation_entrypoint_smokes_launch.json`;
results belong in `confirmation_entrypoint_smokes/{U,A,R,D}_result.json`.
Source changes after preparation invalidate the bound draft, including changes
or additions under `tools/`; preserve that draft and use a fresh documented
preparation if implementation changes become necessary. Existing source-bound
workers and sealed manifests remain untouched.
