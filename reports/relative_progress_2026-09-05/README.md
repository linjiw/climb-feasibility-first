# Relative-progress study: execution record

Classification: **exploratory simulation manipulation**. Policy benefit pending.
Design: `plan/RESEARCH_DESIGN_RELATIVE_PROGRESS_2026-09-05.md`.
Existing candidate specification: `plan/RELATIVE_ALP_PROBE_2026-09-05.md`.

## Completed R0 smoke

Seed 11, task `Climb-Tracking-Flat-Unitree-G1-RelativeALP-Probe`, 8 environments,
20 iterations. Started 2026-09-05 11:38:32 EDT, completed 11:38:49, rc=0.
Elapsed 17 seconds; baseline/peak total GPU memory 1,653/4,384 MiB (shared GPU,
so peak delta is not an isolated process-memory measurement).

Final ledger: 184 completed trials, zero censored resets, zero invalid starts,
zero invalid reference frames. Entropy-effective units 624.0341; maximum unit
probability 0.0164277, maximum clip mass 0.0171784. TV approximately zero because
the 10-tick history is not yet populated: this smoke tests lifecycle and binding,
not sustained adaptation. `smoke_result.json` records strict `smoke_pass` after
checking both iteration 0/19 ledgers, checkpoint hashes and sampler replay.

Exact launch from the repository root:

```bash
CLIMB_BANK=$PWD/bank/amass CLIMB_CLIPS=$PWD/bank/tiers/tier_800.txt \
CLIMB_SEGMENT_MANIFEST=$PWD/reports/g_segment/unit_table.json \
CLIMB_RELATIVE_SEED=11 WANDB_MODE=offline ATTEMPTS=1 \
tools/run_when_free.sh 14000 reports/relative_progress_2026-09-05/smoke_s11.log -- \
  mjlab-1.6.0/.venv/bin/python tools/train_relative_progress_probe.py \
  Climb-Tracking-Flat-Unitree-G1-RelativeALP-Probe \
  --env.scene.num-envs 8 --agent.max-iterations 20 --agent.logger tensorboard \
  --agent.run-name relative_smoke_s11 \
  --log-root reports/relative_progress_2026-09-05/smoke_s11

mjlab-1.6.0/.venv/bin/python tools/check_relative_progress_probe.py \
  --run-dir reports/relative_progress_2026-09-05/smoke_s11/g1_tracking/2026-09-05_11-38-35_relative_smoke_s11 \
  --seed 11 --stage smoke --out reports/relative_progress_2026-09-05/smoke_result.json
```

Outputs use exclusive creation; reproductions need a fresh destination.

## R1 long probe launched

Started 2026-09-05 11:45:22 EDT through the 14,000-MiB shared-GPU gate. Fresh
seed 11, 512 environments, 4,000 iterations, no checkpoint resume. Supervisor
PID at launch: 830991 (not a durable identity; use artifacts below).

```bash
mjlab-1.6.0/.venv/bin/python tools/run_relative_progress_study.py \
  --seed 11 --out-dir reports/relative_progress_2026-09-05/study_s11 \
  --smoke-result reports/relative_progress_2026-09-05/smoke_result.json
```

The supplied smoke was reproduced before the long launch. `launch.json` records
the detached supervisor argv/PID; `study_s11/design.json` binds the design and
checker before outcomes; `study_s11/long_command.json` is the exact training
argv. Track progress in `study_s11/long.log` and `study_s11_launcher.log`.
The supervisor writes `study_s11/long_result.json` and `terminal_status.json`
when finished or stopped. Absence of a terminal artifact is not completion.
The checker requires all 41 snapshots, with 37 post-warm-up snapshots entering
the fixed manipulation gate. No policy evaluator is invoked. Seed 12 and the
future matched policy benchmark remain separate conditional stages.

## Verification

```bash
mjlab-1.6.0/.venv/bin/python -m pytest \
  tests/test_relative_progress.py tests/test_relative_progress_probe.py -q
# 19 passed in 4.30s
mjlab-1.6.0/.venv/bin/python -m py_compile climb/relative_progress.py \
  tools/train_relative_progress_probe.py tools/check_relative_progress_probe.py \
  tools/run_relative_progress_study.py tests/test_relative_progress_probe.py
sha256sum -c plan/G_SEGMENT_FREEZE.sha256
git diff --check
```

All 41 existing Phase-G sealed files verified unchanged. Generated checkpoints,
event files and sampler-state binaries remain local/ignored under repository
rules; JSON ledgers and source-bound summaries preserve the measured record.

## Interim observation (not a gate decision)

At iteration 400, seed 11 reports TV 0.0631681, entropy-effective units
625.0428, maximum unit mass 0.0156207, and 152,890 completed trials, with
zero invalid starts/frames or censored resets. This is the first of the 37
required post-warm-up snapshots; no long-run pass is inferred. The immutable
source snapshot and digest are recorded in `interim_400.json`.

## Authorized continuation and analysis preparation

The follow-up instruction authorizes progress through the conditional seed-12
replication. `continuation_launch.json` records supervisor PID 866282 and its
exact command; `continuation/design.json` binds predecessor and continuation
source identities. This worker waits for R1's complete terminal decision, replays
its saved evidence, and only on a pass launches unchanged R2 seed-12 smoke/full
training. Follow `continuation_launcher.log`; subsequent seed-12 logs live under
`continuation/`. A scientific failure or invalid predecessor stops promotion.
The worker creates complete-result allocation figures with CSV/provenance and
writes `continuation/terminal_status.json`; it does not evaluate policy endpoints.

`plan/RELATIVE_PROGRESS_CONTINUATION_2026-09-05.md` documents the operational
contract, statistical assumptions and remaining R3 work. The prospective policy
kernel implements paired-seed t intervals, supplementary hierarchical intervals,
SESOI/non-regression decisions, and condition aggregation that retains failed
trials and rejects duplicates/missing observations. Its CLI only accepts
synthetic data; real evaluator provenance integration remains pending.
`r3_synthetic_with_aggregation.json` records six synthetic decision branches.

The full preflight verified all 900 input motion hashes, 2,800 evaluation
conditions and the 25/75 strata. Its overall result was **not launch-ready**
because this invocation omitted old G2 launch-environment variables; it does not
certify R3 readiness. Both the JSON and log are preserved as
`r3_input_preflight.{json,log}`. Its built-in simulator smoke briefly shared the
GPU with R1; future input-only audits should avoid the broad simulator preflight.

Final focused verification for this continuation: **42 tests passed in 5.07 s**;
changed tools compile; `git diff --check` passes; all 41 Phase-G sealed files
remain unchanged. Exact test command and source hashes are recorded in
`continuation_verification.json`. At the last live check, R1 had reached iteration
2400 with 21/37 required post-warm-up snapshots (partial mean TV 0.0724025),
and zero invalid or censored events. This remains an interim observation.


## R1 complete; recovery and R3 smokes queued

R1 completed 12:30:02 EDT: **manipulation pass**, mean TV 0.0832114 over all 37
post-warm-up snapshots, minimum effective units 616.2498, final saturation
0.737331, and zero invalid/censored events. Full verified PNG/PDF/CSV and source
binding are under `continuation_recovery/seed11_figure/`. This is one seed and
not a policy-benefit result.

The original `continuation/terminal_status.json` remains an execution stop: a
relative-path versus absolute-path dictionary mismatch in the smoke replay.
The failed source is preserved at `continuation/source_at_failed_launch.py`;
the regression-tested correction only preserves the original path spelling.
The original smoke and full results both reproduced exactly. Seed 12 was not
launched by that failed attempt.

The active replacement supervisor is `continuation_recovery_launcher.log`
(launch record `continuation_recovery_launch.json`, PID at launch 1035465).
It has verified R1 and waits for the shared-GPU availability gate. The separate
`policy_smokes_launcher.log` worker (launch PID 1039495) waits for both independent
manipulation passes before sequential 8-environment/20-iteration seed-41 smokes
of U/A/R/D. Simulator verification of those new profiles is pending. Their
CPU configuration and sampler-state tests pass.

The new D baseline uses fixed 0.80 exploration, chosen from R's algebraic
mixture coefficient before any D outcomes. Full rationale, tuning-cost limits,
calibration gates and exact launch commands are documented in
`plan/RELATIVE_PROGRESS_R1_RESULT_2026-09-05.md`. D calibration and all actual
policy evaluations remain pending.

The evaluator-provenance component is now implemented in
`tools/relative_policy_provenance.py`: it verifies checkpoint/ledger/CSV/source/
condition/reference links and checks the complete paired 48-cell design before
an outer loader may parse outcomes. Twelve artifact-corruption and pairing tests
pass. The complete campaign loader/manipulation gate remains pending, and the
development-only profiles still refuse confirmation. This does not open any
historical or new policy evaluation endpoint.

Integrated verification: **71 tests pass**; changed Python tools compile;
`git diff --check` passes; all 41 Phase-G sealed files remain unchanged.
Exact command and current source hashes: `r1_recovery_and_profiles_verification.json`.

## New sampler-signal diagnostic and fixed-D execution queue

`rank_signal_s11/result.json` reproduces the complete R1 decision before
describing its histories. Across 37 post-warm-up snapshots, an unweighted mean
46.6047% of positive excess sampling mass goes to declining estimated success.
Adjacent progress-ranking Spearman correlation averages 0.422362 over 36 pairs.
These are exploratory, correlated history summaries: the denominator is extra
probability above the deployment prior, not all training draws. They establish
neither useful practice nor wasted practice. Source/state identities, full CSV,
and shareable PNG/PDF are in `rank_signal_s11/`.

Exact command:

```bash
mjlab-1.6.0/.venv/bin/python tools/analyze_relative_rank_signal.py \
  --result reports/relative_progress_2026-09-05/study_s11/long_result.json \
  --out-dir reports/relative_progress_2026-09-05/rank_signal_s11
```

The fixed D calibration supervisor is now queued after the four-arm smokes:
`failure_calibration_launch.json` (launch PID 1062984),
`failure_calibration/design.json` (source bindings), and
`failure_calibration_launcher.log`. It runs fresh seeds 31 and 32 sequentially,
each 512 environments / 4,000 iterations, with fixed pass/fail gates and no
candidate selection. This is a queued experiment, not completed simulator
validation. All three supervisor source sets still match their launch bindings;
R2 is waiting for GPU availability and downstream stages have not run.

The complete campaign loader is now a development prototype in
`tools/analyze_relative_campaign.py`. It combines prerequisite and all-training
snapshot checks with the existing 48-cell provenance verifier, then aggregates
final scores and descriptive learning curves. Its synthetic aggregation tests
stub the full preflight; additional tests exercise real sampler replay and
reject stale histories/invalid events. It has not passed a complete end-to-end
confirmation campaign fixture. Quality/work secondaries, confirmation execution
and the prospective freeze remain pending; current profiles still disable
confirmation. No policy outcomes were parsed in this work.

Full scientific interpretation, exact queue command, proposed campaign gates,
and remaining work: `plan/RELATIVE_SIGNAL_DIAGNOSIS_2026-09-05.md`.

Integrated verification: **90 tests passed in 23.62 s**; Python compilation and
`git diff --check` passed; all 41 Phase-G sealed artifacts are unchanged.
`signal_and_calibration_verification.json` records the exact ten-file test
command, check outputs, and source hashes. These tests verify development code;
they do not replace pending simulator runs or establish a policy result.

## Seed 12 launched; complete synthetic campaign validation

The previous queue ended in an operational stop at 17:36 EDT: the second GPU
availability poll missed the window, producing only `GAVE_UP polls=1` before
seed-12 training launched. All original terminal records remain preserved.
Fresh unchanged supervisors were launched at 18:29:57 EDT, recorded in
`continuation_gate_retry_launch.json`, `policy_smokes_gate_retry_launch.json`,
and `failure_calibration_gate_retry_launch.json`.

Seed-12 smoke passed: 8 environments, 20 iterations, 192 completed trials,
zero invalid/censored events, 17 seconds. The full 512-environment,
4,000-iteration replication launched 18:30:27 EDT and remains running.
Exact trainer commands, environment, evidence and logs are under
`continuation_gate_retry/study_s12/`. Follow its `long.log` and
`terminal_status.json`; full manipulation is pending until all required
snapshots and the complete result pass. The new downstream supervisors wait
for replication and lifecycle passes, respectively.

`tests/test_relative_campaign_integration.py` now passes a complete synthetic
campaign through the real prerequisite, training, evaluator-provenance and
aggregation functions, without replacing those gates. The fixture includes
both R prerequisites, both D calibrations, all 12 confirmation histories,
41 snapshots per confirmation run, and 48 paired evaluation cells. A final-cell
pairing mismatch blocks all endpoint aggregation. Dummy checkpoint bytes and
constructed histories are explicitly synthetic; no actual policy was evaluated.

The final-checkpoint descriptive reducer in `tools/relative_policy_secondaries.py`
reports R-U/R-A/R-D common-success pose with all coverage counts, plus
all-condition work and exposure. Empty pose cells stay null. Early-failure
work is retained and cannot establish energy efficiency. The actual development
profiles keep confirmation disabled. Remaining source/input audit, confirmation
execution, training-cost accounting and freeze are listed in
`plan/RELATIVE_CONFIRMATION_READINESS_2026-09-05.md`.

Verification for this update: **101 tests passed in 116.90 s**, Python
compilation and whitespace checks pass, all 41 sealed Phase-G artifacts remain
unchanged. Exact commands, test environment and source hashes:
`campaign_readiness_verification.json`. The initial 24-file static import
inventory is `confirmation_source_inventory.json`; external/runtime dependency
and input auditing remains pending.

## Both planned manipulation seeds pass

Seed 12 completed at 19:26:40 EDT. Its complete gate passes: mean TV
0.0827283432 over 37 post-warm-up snapshots, minimum effective units 618.611481,
final saturation 0.7331081, 1,086,192 completed trials and zero invalid/censored
events. Both studies were reproduced again in `replication_review.json`.
The verified two-seed allocation figure is under
`continuation_gate_retry/replication_figure/`. This is an exploratory allocation
replication; no policy-benefit result is available.

The unchanged diagnostic on seed 12 gives declining-estimate excess-mass share
0.4680896 and adjacent rank correlation 0.4029245. Use
`rank_signal_s12_corrected/` for the figure and source-bound diagnostic, and
`replicated_rank_diagnostic.csv` for the two-seed comparison. The initial
seed-12 figure's hardcoded “Seed 11” caption is preserved and corrected in an
addendum; all numerical fields and CSV bytes match. Attempt-count correlations
for both seeds use 36 valid adjacent-snapshot intervals, correcting the earlier
37-observation wording without changing means.

`replication_reference_audit.json` verifies all 900 motion identities and
reconstructs all 2,800 evaluation conditions from current headers on CPU.
`replication_execution_cost.json` accounts for 6,053 s / 1.681389 elapsed
GPU-hours across the two full probes, plus the unlaunched gate miss, with
explicit exclusions. The campaign loader now binds successful cost logs to
their run directory/seed and includes scoped training-cost summaries.

Full scientific interpretation, corrections, exact commands and remaining
confirmation work: `plan/RELATIVE_PROGRESS_REPLICATION_RESULT_2026-09-05.md`.
The existing `policy_smokes_gate_retry` and `failure_calibration_gate_retry`
workers retain their fixed profiles and wait for the GPU/prerequisite gates.

Integrated verification: **121 tests pass in 107.28 s**, Python compilation and
whitespace checks pass, and all 41 sealed Phase-G artifacts are unchanged.
`replication_audit_and_cost_verification.json` records exact commands and source
identities. Synthetic validation is not policy evidence.


## Confirmation execution prepared; simulator validation queued

The fixed trainer, ledger and 60-job scheduler are implemented. Under
`confirmation_preparation/`, the draft binds 12 configurations, 12 training
commands, 48 evaluation commands and an inventory of 375 files including
36 G1 assets. `cpu_preflight_result.json` reproduces the actual reference audit,
runtime inventory and configuration identities; confirmation correctly rejects
this draft. The profile remains disabled and no confirmation endpoint was opened.

`confirmation_entrypoint_smokes_launch.json` records the detached seed-51
supervisor and exact command. It waits for the existing fixed D calibration,
then tests the new trainer for U/A/R/D with eight environments and 20 iterations.
The existing seed-41 smokes and D seeds 31/32 remain earlier dependencies.
The supervisor never enables or launches confirmation.

**152 tests passed in 109.93 s**; compilation and whitespace checks pass and
all 41 sealed Phase-G artifacts remain unchanged. Exact commands and source
hashes: `confirmation_execution_verification.json`. New controller tests stub
job execution/verifiers; new ledger tests replay synthetic completed trials.
The earlier full synthetic campaign exercises its legacy contract schema.
Positive complete new frozen-contract execution and simulator/evaluator
validation remain pending. Technical validation supplies no policy-benefit result.

The full execution plan and evidence limits are in
`plan/RELATIVE_CONFIRMATION_EXECUTION_2026-09-05.md`.


## Evaluator compatibility addendum

Use `confirmation_preparation_adapter/` for current draft commands and runtime
identities. The former draft is preserved but superseded. Actual CLI testing
found that the sealed evaluator rejects the sealed condition file's two extra
provenance fields; every shared field and all 2,800 conditions agree. A separate
strict adapter validates the untouched sealed payload and provenance, then
reuses the evaluator. Its identity is required in new-schema evaluation metadata.

`evaluator_adapter_correction/` preserves the pre-change unsealed sources, queue
supersession, original rejection, successful CPU preflight and integrated
verification. The old seed-51 supervisor was stopped before launching a smoke.
`confirmation_entrypoint_smokes_adapter_launch.json` records its replacement;
`confirmation_entrypoint_smokes_adapter/` contains the replacement lifecycle
queue. Earlier development-smoke and fixed-D workers remain unchanged.

New integration tests exercise the strict production contract and real verifiers
on synthetic histories/outcomes. Actual CLI/configuration tests stop at simulator
construction and check interface parity for all four arms. No benchmark policy
outcomes were opened. Detailed scope and remaining GPU validation:
`plan/RELATIVE_EVALUATOR_ADAPTER_2026-09-05.md`.


Integrated verification: **175 tests passed in 292.93 s**. Python compilation,
whitespace checks and all 41 sealed Phase-G identity checks pass.
The replacement seed-51 supervisor is queued after fixed D calibration;
its launch identity is recorded in `confirmation_entrypoint_smokes_adapter_launch.json`.


## Four-arm development smokes completed

`development_smoke_review/result.json` replays all four actual seed-41 smoke
results and records their exact launch commands and scoped costs. Completed
trials U/A/R/D are 191/183/177/198, with zero invalid/censored events; total
elapsed time is 75 seconds. These counts are lifecycle evidence, not a method
ranking. `checkpoint_loading.json` verifies strict CPU actor-only loading and
normalization restoration from the actual four iteration-19 checkpoints without
simulator construction or policy forward calls.

D seed 31 is now running (iteration 2100 at the 21:57:36 EDT snapshot); complete
calibration remains pending. Source/runtime bindings remain intact. The active
new-trainer smoke worker still waits for both fixed D calibration passes.
`verification.json` records 27 targeted tests passing in 3.31 s, compilation,
whitespace and all 41 sealed artifacts. The prior integrated 175-test result
remains separate. Full evidence and remaining decision rules:
`plan/RELATIVE_DEVELOPMENT_SMOKES_2026-09-05.md`.


## Prospective design precision

`design_precision/` contains a CSV, JSON and exportable PNG/PDF for the unchanged
three-seed decision rule. These are hypothetical normal-model calculations with
unfitted effect/variance scenarios; no policy outputs are read. The separate
benefit and non-regression curves are not full campaign power. The fixed
interval half-width is 2.4841377 times sample SD. Full assumptions, illustrative
probabilities and interpretation rules are in
`plan/RELATIVE_DESIGN_PRECISION_2026-09-05.md`. Fourteen new mathematical tests
plus the existing analysis tests pass: 29 tests in 0.32 s. Compilation,
whitespace and all 41 sealed identity checks pass; see `verification.json`.


## Fixed D seed 31 completes and reproduces

`failure_seed31_review/` contains a replay-verified comparison of R11/R12/D31,
all 123 snapshots, PNG/PDF figure and scoped training costs. D seed 31 passes
with mean TV 0.0849553, minimum effective units 625.0617, final saturation
0.727196 and 1,113,773 completed trials; invalid/censored counters are zero.
The figure is descriptive across unequal development replications, not policy
evidence. Seed 32 is training under the unchanged supervisor.

`freeze_readiness.json` records the current draft preflight and exact remaining
D32/seed51 prerequisite paths. `verification.json` records 11 targeted tests
passing in 12.51 s, compilation, whitespace and all 41 sealed identity checks.
`execution_snapshot.json` binds the interim seed-32 state and unchanged runtime.
Full result and next research/execution steps:
`plan/RELATIVE_D_SEED31_RESULT_2026-09-05.md`.


## Final freeze command validated

`freeze_command_validation/` records the actual prerequisite refusal, exact
verification commands, source hashes and operational snapshot.
`tools/freeze_relative_confirmation.sh` resolves only the predeclared evidence
paths, runs complete production checks, and creates a new exclusive contract
and seal when ready. It does not launch jobs. Four transition tests and the
existing complete strict-contract integration test pass, using synthetic
positive evidence; shell/Python syntax, whitespace and all 41 sealed artifacts
also pass. The current actual draft remains disabled and creates no freeze.
See `plan/RELATIVE_CONFIRMATION_FREEZER_2026-09-05.md`.
