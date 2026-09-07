# Results log — every paper-bound number and its artifact path (policy: RESEARCH_PLAN_v5)

## 2026-09-07 Fable submission manuscript and frozen H1

**Manuscript update, no scientific contract or completed numeric result changed.**
The ICRA source, generated Markdown and seven-page PDF now incorporate the
complete U/A/R/D result from
`reports/relative_confirmation_results_2026-09-06/summary.json`. Table II contains
all three paired final R−U differences on both panels and their mean/t intervals;
Figure 3 contains paired results and all learning curves. Primary hard mean
−0.0150684593, CI [−0.0943584262,+0.0642215077]; all-panel mean −0.0093155064,
CI [−0.1140463277,+0.0954153149]. Both registered criteria fail; disposition remains
**inconclusive**, not equivalence or demonstrated harm. The repair table uses the
existing one-policy result: raw 0.3925, repaired 0.3915, difference −0.0010,
clip-bootstrap CI [−0.0086,+0.0080], 26 clips and 656 paired conditions per arm.
Its qualification count remains 22/26 plus 4/4 byte-identical controls.

All 12 signed table values match the source at five decimals. Source summary
SHA-256 `5b1a5fdc537ab8e51405c443f29f34e2bb8f35887e295fc18342a108dd965429`.
Build/number/seal evidence: `reports/fable_submission_2026-09-07/` and
`paper/icra/BUILD_AUDIT_2026-09-07.md`. Claims, alternatives and unresolved limits
are reviewed in `paper/icra/REVIEW_2026-09-07.md`. E4 is explicitly `not_tested`;
normalization alone is not a novelty claim; no admission benefit enters the paper.

**H1: prospectively sealed, no policy result yet.** Fixed new paired seeds
1041–1045; two GPU smokes, ten training runs, forty held-out cells. Contract SHA-256
`fdc5354045bb848fb982822d5ebd6d9b40ca88cb14209acc6b880579eed4b474`.
Five-seed two-sided primary t decision, +0.02 descriptive, all-panel interval with
no pass/fail guard. Eight synthetic tests and two CPU smoke replays pass; these
are instrumentation evidence only. The durable scheduler is waiting for GPU
capacity. See `plan/H1_FABLE_FREEZE_2026-09-07.md` for exact commands, cutoffs and
artifact locations. This separate H1 design does not amend the completed R/U
contract or append seeds to that comparison.


## 2026-09-07 continuous natural-failure coverage and reference census

**Measured CPU development simulation:** the R41 checkpoint-19 policy produces
four natural failures on the same two admitted training references and four
conditions used in the prior continuous smoke. First failure steps are 49, 64,
40 and 37 (survival 0.98, 1.28, 0.80 and 0.74 seconds). The vector loop ends at
64 forwards, with 27 partially active steps, five retired-world environment
resets and five retired-world reference writes. Zero active resets/reference
writes; nine policy parameter tensors and four normalization buffers unchanged.
No allocator comparison or causal learning claim follows from these fixtures.

Independent replay also reproduces the earlier four successful attempts
(429 forwards, 123 partially active steps), with identical startup and initial-state
hashes across the two development runs. Fourteen new rejection tests pass.
Artifacts: `reports/continuous_failure_preparation_2026-09-07/replay.json`,
`smoke.log`, `tests.log`; full simulator receipt in the isolated ICRA worktree's
`reports/continuous_failure_development_2026-09-07/run/receipt.json`.

**Measured reference-only metadata:** all 100 held-out payload hashes match;
25 retain the existing feasible-hard reference label. Raw full-reference
transition durations are min 4.98 s, median 9.44 s, max 72.06 s, sum 1,403.22 s.
All exceed three seconds. These are not admitted durations or performance values.
No named corresponding frame screens/sidecars found in the declared report-tree
search; full continuous admission is pending. Artifact:
`reports/continuous_failure_preparation_2026-09-07/reference_readiness.json`
and `reference_candidates.csv`. Scope and reconstruction requirements:
`plan/CONTINUOUS_FAILURE_AND_REFERENCE_READINESS_2026-09-07.md`.

## 2026-09-06 completed frozen policy confirmation and continuous development

**Measured frozen simulation outcome:** all 12 trained policies and 48 held-out
cells complete; 492 training states replay. Three independent paired training
seeds (21/22/23); 49,152,000 transitions per policy; 100 test clips, 25 feasible-hard.

| Quantity | Paired-seed mean | Two-sided seed t 95% CI (df=2) | Class |
| --- | ---: | --- | --- |
| Final feasible-hard R−U | −0.015068459267959947 | [−0.09435842624903064, +0.06422150771311073] | registered primary; inconclusive |
| Final all-panel R−U | −0.009315506381973216 | [−0.11404632768409208, +0.09541531492014564] | registered guard; non-regression not established |
| Final hard R−D | −0.006745730159873853 | [−0.021893908519565127, +0.00840244819981742] | descriptive secondary |
| Final hard R−A | −0.006680740727722248 | [−0.07242863750148, +0.059067156046035504] | descriptive secondary |
| Normalized hard AULC R−U, checkpoints 1000–3999 | −0.028984641429545266 | [−0.057740602250632767, −0.0002286806084577618] | exploratory; not a confirmatory harm decision |

Primary seed deltas: −0.03399896411704021, −0.03298966480664032,
+0.021783251119800687. Supplementary primary paired hierarchical bootstrap CI
[−0.04416877706957367, +0.025321222754109297]; all-panel
[−0.04768233802225798, +0.033113661535246725]. No bootstrap rescue, equivalence,
confirmed harm, target-benefit exclusion or efficiency-accelerator claim follows.
AULC differences are negative in all three seeds. Preserve the registered result.

Artifacts: `reports/relative_confirmation_results_2026-09-06/` contains the
paired-result/learning-curve PNG/PDF, CSV, full-precision summary and descriptive
attainment export. Complete original analysis SHA-256
`2d1703da6d2d40fad9f9b17ffcf9d12036c4aaea917fb1054e81c91ed22bf3be`.
Exact serialized replay receipt:
`reports/continuous_execution_preparation_2026-09-06/serialized_confirmation_replay/verification.json`.
The original postprocessing failure is preserved: only tuple/list representation
of seed_order differed; no numeric value or scientific rule changed.

**Measured development only:** CPU continuous adapter, development R11 checkpoint
2000, two fully admitted training references, two replicates each: 4/4 complete
at 429/306 transitions (8.58/6.12 seconds), 429 vector forwards, zero active resets
or reference-state writes, 9 policy parameter tensors and 4 normalization buffers
unchanged. No method comparison. Runtime failure-path and CUDA coverage pending.
Receipt: `/home/linjiw/climb-icra-evidence-2026-09-06/reports/continuous_execution_development_2026-09-06/run/receipt.json`.
Thirteen continuity/support tests, five serialized-replay tests and seven optional-
sensor graph tests pass. Frozen-policy instrumentation pilot completed but no
stationarity/noise-floor result is established. Original GPU first-cell graph
assertion failed; corrected development queue remains distinct from full physical
sensitivity or hardware evidence. Scope and next study design:
`plan/USEFUL_PRACTICE_SUBMISSION_2026-09-06.md`.

The subsequent corrected CUDA queue ran all nine development cells, then failed
its aggregate original/unchanged exact CSV parity gate. Preserve that failure;
individual lifecycle replay does not establish aggregate conformance. Diagnostic:
`reports/continuous_execution_preparation_2026-09-06/gpu_followup_diagnosis.json`.
Full physical-sensitivity evaluation remains disabled.

## 2026-09-06 confirmation allocation and public research-story update

**Measured simulation training integrity and allocation:** at 22:17 EDT, ten of
12 confirmation training runs complete and independently replay over 410 saved
checkpoint states. All seeds 21/22 arms plus R23/D23 pass; U23 is running and A23
queued. No held-out endpoint has opened. Per-seed mean post-warm-up allocation TV:

| Arm | Seed 21 | Seed 22 | Seed 23 |
| --- | ---: | ---: | ---: |
| U | 0.0 | 0.0 | Pending |
| A | 0.029759170164293084 | 0.02933859420427059 | Pending |
| R | 0.08348494896009954 | 0.0824919974124211 | 0.08233284378057906 |
| D | 0.08391068947163956 | 0.08586509252074585 | 0.08398385293466296 |

Each complete run has 41 replayed states and zero invalid/censored events. The
TV mean uses 37 states from iteration 400 through 3999. Allocation histories are
correlated within runs and establish exposure contrast, not tracking improvement.
Public artifacts: `docs/assets/progress-2026-09-06/research_snapshot.json`,
`allocation_snapshots.csv` and `confirmation_allocation.png`/`.pdf` in that directory.
Original gate paths and SHA-256 identities are included in the JSON export.

**Measured development / pending outcomes:** the public development summary records
completed D31/D32 calibration, freeze prerequisites, H1 CPU evaluation/provenance
and CPU lifecycle checks. It does not establish full H1 benefit, forgetting recovery,
physical robustness or hardware transfer. Existing repair and E4 findings retain
separate exploratory/sealed labels. Scope, claim-to-evidence map, statistical
contract and next research decisions: `plan/PAGES_RESEARCH_STORY_2026-09-06.md`.

## 2026-09-06 eight completed confirmation training gates and H1 provenance

**Measured training allocation/integrity, not policy utility:** all four arms for
seeds 21 and 22 complete 4,000 iterations and independently replay across 328
saved states. Mean allocation TV for seed 21 / seed 22: U 0 / 0;
A 0.029759170164293084 / 0.02933859420427059;
R 0.08348494896009954 / 0.0824919974124211;
D 0.08391068947163956 / 0.08586509252074585.
No held-out endpoint has opened. Artifact:
`reports/h1_provenance_preparation_2026-09-06/confirmation_replay.json`.

**Measured development provenance and synthetic rejection checks:** both existing
seed-81 CPU evaluation cells pass exact checkpoint/ledger/runtime/condition links
and paired-state identity; 19 tests pass. The synthetic 24-cell grid is a protocol
fixture, not completed H1 evaluation. Full H1 remains disabled. Scope, commands
and remaining work: `plan/H1_PROVENANCE_PREPARATION_2026-09-06.md`.

## 2026-09-06 R21 interim checkpoint and synthetic H1 analysis preparation

**Measured interim training integrity:** R21 checkpoint 2100, verified at
14:44:23 EDT, has 596,494 completed trials including 197,689 failures, zero
invalid/censored events, 76 finite checkpoint tensors and exact sampler-probability
replay. Point allocation TV is 0.0882566243200943. Full R21 gate and policy benefit
remain pending; no held-out cell has been evaluated. Artifact:
`reports/h1_analysis_preparation_2026-09-06/r21_snapshot.json`.

**Synthetic/prospective only:** H1 paired seed-level statistical and ordering
kernel passes 16 tests. It preserves the draft +0.02 improvement target, two-sided
95% t interval with df=2 and −0.01 guards; preservation is a separate margin-based
noninferiority result. Proposed supplementary bootstrap uses 10,000 draws and
seed 20260906, pending the H1 freeze. Tests establish six verifier calls before
24 outcome reads and zero outcome reads after any training-gate failure; they use
synthetic callbacks, not completed H1 runs. Artifact:
`/home/linjiw/climb-icra-evidence-2026-09-06/reports/h1_analysis_preparation_2026-09-06/synthetic.json`.
Scope and remaining production requirements:
`plan/H1_ANALYSIS_PREPARATION_2026-09-06.md`.

## 2026-09-06 H1 entrypoint and paired development evaluator

**Measured training integrity:** existing H1 seed-81 entrypoint smokes replay
exactly (8 environments, 20 PPO iterations, 3,840 transitions per arm). Gate-on:
183 completed trials, zero rejected-support trials. Gate-off: 173 completed trials,
25 rejected-support trials; final rejected probability 0.11375725722182886. Both
start from the same actor hash and have zero invalid/censored events. Artifacts:
`/home/linjiw/climb-gate-ablation-2026-09-06/reports/gate_entrypoint_2026-09-06/`.
These are distinct from the earlier seed-71 runtime smokes.

**Measured development evaluation integrity:** two checkpoint-19 policies produce
eight episode rows on two training clips with paired startup/initial state,
exact checkpoint-to-loaded-policy equality, unchanged normalization/parameters,
and valid nonzero clip scores. This is an undertrained, single-seed pipeline
smoke, not a gate-benefit estimate. A first metadata-write failure from a missing
environment path is preserved; the fresh rerun after adding the pinned-environment
link passes. Nine targeted tests pass. Evidence:
`/home/linjiw/climb-icra-evidence-2026-09-06/reports/gate_evaluator_environment_fixed_2026-09-06/verification.json`.
Full scope, failed artifact and exact commands:
`plan/H1_EVALUATOR_DEVELOPMENT_2026-09-06.md`. Full H1 remains disabled.

## 2026-09-06 device entrypoint CPU parity and pending GPU conformance

**Measured development entrypoint check:** original, unchanged and 20 ms delay
produce 21 CPU episode rows identical to their prior natural-lifecycle CSVs.
Policy immutability, physical/reset/score replay and correct absence of CUDA
graphs on CPU pass. These are repeated development cases, not independent policy
effect samples. Evidence in the isolated ICRA worktree:
`reports/device_lifecycle_cpu_2026-09-06/verification.json`.

**Pending:** nine GPU development cells are source-bound and queued behind the
complete confirmation campaign and frozen-policy pilot. Zero GPU cells have
started at the 12:47 EDT snapshot. Actual graph-launch counts, GPU parity and
GPU reset conformance are not yet measured. Eleven tests pass, including synthetic
graph-receipt rejection; these do not substitute for GPU execution.
Full design, acceptance criteria and queue records:
`plan/GPU_DEVICE_VALIDATION_QUEUE_2026-09-06.md`.

## 2026-09-06 natural-failure and early-retirement CPU lifecycle

**Measured development lifecycle:** original plus eight physical conditions on
five training clips, selected by reference duration/joint-speed RMS and fixed-list
order before execution, produce 63 episode rows: 21 natural failures and 10 early
successful retirements. There are 29 environment reset calls and 101 entity-reset
calls, including 37 motion-resample calls. Nested reset calls are not episodes;
the shared development checkpoint and paired rows are not independent efficacy
replications. No confirmation clips are included.

Baseline has natural `ee_body_pos` failures at steps 32/104, an early successful
clip at step 56 (1.12 s), and four continuing worlds at 150 steps. The 20 ms delay
condition retires all worlds by step 131. These establish validation-path coverage,
not a broad robustness, sample-efficiency, transfer or recovery estimate.

An initial environment-only reset trace missed command-driven robot resets and
is preserved with `incomplete_audit.json`. The expanded entity recorder leaves
all nine CSVs unchanged. Original/unchanged parity, native score accounting,
world-specific reset/delay replay, physical checks and policy immutability pass;
11 regression tests pass. Complete evidence:
`/home/linjiw/climb-icra-evidence-2026-09-06/reports/natural_entity_lifecycle_2026-09-06/verification.json`.
Design and exact execution: `plan/NATURAL_POLICY_LIFECYCLE_2026-09-06.md`.
GPU conformance and the separate full physical-study freeze remain pending.

## 2026-09-06 injected reset lifecycle defect and correction

**Measured CPU software conformance, not natural policy failure evidence.** A
prospectively specified injected-termination fixture fails reset isolation for
5/10/20 ms delay, while six non-delay conditions pass. The first reset changes
per-world command-delay counts [40,40,40,40] to [1,41,41,41], advancing unselected
histories without a physics step. Failed artifacts are preserved in the isolated
ICRA worktree's `reports/injected_reset_fixture_2026-09-06/failed_audit.json`.

A separately source-bound development correction passes all nine cells: 36
injected-fixture rows, 27 partial resets, 80 native metric values replayed per
cell and 800 world-physics control records replayed per cell. Policy tensors are
unchanged; failed/retired worlds stop contributing to metrics, and failure at
the final horizon is scored as failure. Complete fixed evidence is in
`/home/linjiw/climb-icra-evidence-2026-09-06/reports/injected_reset_fixed_2026-09-06/verification.json`.

The unaffected world 2 CSV row matches its earlier no-injection reference for
all nine conditions before and after the correction. No tracking improvement
is claimed. Thirteen regression tests pass. Original confirmation sources and
sealed decisions remain unchanged; natural failure and GPU coverage are pending.
Details: `plan/PHYSICS_RESET_LIFECYCLE_2026-09-06.md`.

## 2026-09-06 complete U21/A21 training and development inference immutability

**Measured training integrity:** U21 and A21 finished 4,000 iterations, with
1,086,702 and 1,084,430 completed trials respectively. Mean allocation TV is
0 and 0.029759170164293084; elapsed training is 2,014 and 2,221 seconds. Both
41-snapshot gates independently replay exactly, with zero invalid/censored events.
A has no frozen minimum-TV requirement. Artifact:
`reports/gpu_reentry_2026-09-06/completed_training_replay_1208.json`.
These measurements establish neither tracking benefit nor sample efficiency;
10 training jobs and all 48 held-out cells remain pending at this snapshot.

**Measured development inference integrity:** original evaluator plus eight
physical conditions preserve all 9 actor parameter tensors and 4 normalization
buffers exactly, with evaluation mode throughout 450 vector forward calls.
All nine CSVs equal their previous development counterparts byte for byte.
This is a replay of the same 36 short training-clip rows, not new independent
policy efficacy evidence. Source-bound design, traces and aggregate verification:
`/home/linjiw/climb-icra-evidence-2026-09-06/reports/policy_immutability_2026-09-06/`.
Failure/reset and GPU coverage remain pending. Full execution and limitations:
`plan/CONFIRMATION_PROGRESS_AND_IMMUTABILITY_2026-09-06.md`.

## 2026-09-06 development policy evaluator integration

All artifacts in this table are in the isolated ICRA worktree
`/home/linjiw/climb-icra-evidence-2026-09-06/reports/physics_evaluator_development_2026-09-06/`.
Original confirmation is now training U21 in its new operational directory, but
has no complete arm comparison or opened held-out endpoint. Its statistics and
all historical sealed decisions remain unchanged.

| Measurement | Use and limitation | Artifact | Class |
| --- | --- | --- | --- |
| Original evaluator + 8 adapter conditions × 4 episode rows = 36; R11/2000; first two training clips; phases 0/0.5; one-second horizons; environment seed 26090651 / joint-noise seed 26090652; all 36 survive and clip scores are nonzero | Small CPU lifecycle only; training clips, one development policy, no confirmation or transfer inference | `design.json`, per-condition CSVs/metadata/receipts, exact `*_launch.json`, `verification.json` | measured development policy rollout |
| Original vs unchanged adapter CSV byte-identical; all 8 variants match startup RNG/physical state, initial qpos/qvel, first observations/actions; 200 recorded physics substeps × 4 worlds per adapter cell | Tests actual evaluator integration and pairing on these short conditions; no policy-triggered reset coverage or GPU graph verification | per-condition `instrumentation.pt`, `verification.json` | measured CPU evaluator conformance |
| Unchanged maximum absolute knee force 86.40794 N·m; knee-only 120/90 N·m clamps never activate and their CSVs match unchanged | Does not establish insensitivity to reduced actuation on difficult motions | `unchanged`, `knee_120nm`, `knee_90nm` traces/CSVs; `verification.json` | measured development telemetry; limited stress coverage |
| 20 ms delay reaches 139 N·m; 11/1,600 knee force samples are at least 98% of the limit | Substeps/joints/worlds are correlated observations, not independent replications; no broad robustness or safety conclusion | `delay_20ms/instrumentation.pt`, `verification.json` | measured development response to perturbation |

The full physical-sensitivity grid remains disabled pending further lifecycle
checks and its own prospective freeze. See
`plan/GPU_REENTRY_AND_EVALUATOR_PROGRESS_2026-09-06.md` for scope and execution.

## 2026-09-06 measured physical-intervention instrumentation

Artifacts below are in `/home/linjiw/climb-icra-evidence-2026-09-06`, under
`reports/physics_sensitivity_2026-09-06/`. No original policy endpoint or claim
changes. The S1 physical-sensitivity preparation remains unsealed and disabled
for full evaluation; it is distinct from historical S1 conformance experiments.

| Measurement | Use and limitation | Artifact | Class |
| --- | --- | --- | --- |
| Eight conditions, two worlds, 12 physics steps each plus one unchanged repeat: 216 integrated world physics steps; seed 26090641; 1.65554 s fixture exercise time | Named CPU G1 actuator fixture; timing excludes original contract verification/imports and does not estimate policy/GPU cost; force/reset probes are additional nonintegrated operations | `cpu_smoke/design.json`, `cpu_smoke/result.json`; exact argv/task in original repo `reports/physics_sensitivity_stage_2026-09-06/execution.json` | measured development instrumentation |
| Command delay 0/1/2/4 physics steps = 0/5/10/20 ms, exact saved control traces | Built-in command-buffer behavior only; not motor lag, observation delay or policy robustness | `cpu_smoke/traces.pt`, `trace_verification.json` | measured CPU command traces |
| Knee clamp probes reach both ±120/±90 N·m in respective conditions; hip roll remains ±139 N·m; all 29 actuator signed clamps checked | Forced nonintegrated saturation probes; no trained-policy torque use or hardware calibration | same traces/verification; `intervention_checks.png` and `.pdf` | measured CPU force probes |
| Foot sliding-friction targets 0.3/1.2 on exactly 14 foot geoms; untargeted coefficients preserved; common fixture initial states and repeated baseline exact | Model-field and deterministic reproduction checks; not measured contact response, evaluator startup pairing or independent statistical repetitions | same traces/verification | measured CPU instrumentation |

Next evidence remains actual evaluator integration and policy-rollout validation.
No tracking, efficiency, forgetting recovery, physical robustness or transfer gain
is inferred from these fixture measurements.

## 2026-09-06 ICRA physical-assumption audit and efficiency scope

No confirmation policy number changes. New code is isolated in
`/home/linjiw/climb-icra-evidence-2026-09-06`; original profiles and sources remain
unchanged. Full scope: `plan/ICRA_EVIDENCE_ROADMAP_2026-09-06.md`.

| Number or disposition | Use and limitation | Artifact | Class |
| --- | --- | --- | --- |
| All 12 frozen configuration hashes reproduced; 29 actuators CPU-compiled; both knee actuator force ranges [−139,+139] N·m with force limiting and unit gear | Configured clamp verification, not measured torque use, hardware fidelity or transfer | `reports/icra_evidence_2026-09-06/physics_audit.json` | measured configuration / CPU model compilation |
| Six actuator groups have command delay min/max 0/0 physics steps; physics timestep 0.005 s; control timestep 0.02 s | No configured command delay; does not measure motor lag or sensor latency | same audit | measured configuration |
| Training startup foot-friction range [0.3,1.2], nominal foot friction 0.6; plane terrain; sealed evaluation `nominal=false` retains startup COM/friction/encoder perturbations but removes pushes and observation corruption | Configuration and source evidence only; no robustness outcome or independent contact calibration | same audit; original `tools/eval_paired_v2.py` | measured configuration / source audit |
| Unitree public maximum knee torque 90 N·m for G1, 120 N·m for G1 EDU, versus model 139 N·m | Public-spec discrepancy; not calibration of a robot revision or a full torque-speed/thermal model | [Unitree G1 specification](https://www.unitree.com/g1/), checked 2026-09-06; URL and values in physics audit | externally reported specification |
| Checkpoint 2000 represents 2001/4000 = 50.025% of 49,152,000 training transitions | Zero-indexed post-update checkpoint arithmetic; no measured efficiency gain | isolated `tools/analyze_icra_efficiency.py`; original RSL-RL runner; `efficiency_synthetic.json` in report directory | calculated budget / synthetic validation |

Actual efficiency status is **pending**, with no endpoints opened. The queued
postprocessor preserves the original primary decision. Proposed S1's 96 evaluation
cells / 268,800 condition instances are prospective budget arithmetic only, not
executed evidence. Simulator sensitivity does not establish physical Sim2Real.

## 2026-09-06 matched gate runtime lifecycle

Artifacts in this section are in the separate worktree
`/home/linjiw/climb-gate-ablation-2026-09-06`. Full H1 training remains disabled;
the current U/A/R/D confirmation and frozen-policy diagnostic are unchanged.

| Number or disposition | Use and limitation | Artifact in H1 worktree | Class |
| --- | --- | --- | --- |
| Gate-on/off CPU PPO smokes: seed 71, 8 environments, 20 iterations, 3,840 transitions per arm; identical initial actor tensors; on 179 completed/0 rejected-support trials, off 196 completed/32 rejected-support trials; both zero invalid/censored events and exact checkpoint sampler replay | Validates matched runtime and restored-support exercise; not policy improvement, difficulty ranking or sample efficiency. No held-out evaluation. | `reports/gate_runtime_2026-09-06/paired_smoke_result.json`; `cpu_{on,off}/run/` checkpoints and ledgers; exact argv in `cpu_{on,off}_launch.json` | measured development PPO lifecycle |
| Final post-cap rejected sampling probability on 0, off 0.1143451525; elapsed CPU job times 24.9197 / 24.2224 s | Short-smoke allocation and scoped elapsed time only; not a full-history allocation estimate or GPU runtime forecast | same paired result and `cpu_{on,off}_execution.json` | measured development telemetry |
| Fixed gate-off rejected probability bounds [0.0923025281, 0.2923025281] from rejected prior share 48,121/417,072 and per-unit floor 0.8 b; startup actual post-cap share 0.1153781601 | Conditional on the fixed support and valid floor/cap constraints; probability bound, not PPO transition share, wasted exposure or practical gate benefit | `reports/gate_runtime_2026-09-06/h1_study_draft.json`, `manifests/result.json`; `plan/MATCHED_GATE_RUNTIME_2026-09-06.md` | analytical bound and measured runtime construction |

## 2026-09-06 frozen-policy instrumentation and H1 support audit

All artifacts below are in the separate worktree
`/home/linjiw/climb-signal-quality-2026-09-06`. Original confirmation outcomes
remain pending and its scientific configuration is unchanged.

| Number or disposition | Use and limitation | Artifact in separate worktree | Class |
| --- | --- | --- | --- |
| R11/2000 CPU smoke: 8 environments, 12 estimator ticks, 4,800 transitions; 98 completed trials, 11 failures; zero invalid/censored events; 8 ongoing trials at stop; exact actor/normalizer hashes and tick replay | Frozen collector lifecycle only; no PPO, stationary-null or policy-benefit inference. Seeds environment 26090601 / sampler 26090602 / actions 26090603 | `reports/frozen_progress_pilot_2026-09-06/cpu_smoke/{result.json,design.json,ticks.pt}`, exact argv `cpu_smoke_launch.json` in parent | measured development simulation |
| CPU rollout 16.8273 s, total 22.1210 s; 90/1,184 units attempted, prior mass coverage 0.1847426894; inherited shadow attempt-mass fraction 0.9980838151 and cold/shadow absolute rate gap 0.4017311523, both prior-weighted at tick 12 | Tiny instrumentation exposure budget; neither stationary noise magnitude nor GPU runtime/burn-in estimate | `reports/frozen_progress_pilot_2026-09-06/cpu_smoke_analysis/summary.json` | measured instrumentation coverage and initialization dependence |
| H1 candidate universe: 800 clips, 417,072 full legal H=50 starts, 368,951 admitted, 48,121 rejected (0.1153781601 of uncapped legal-start prior); 1,184 feasible + 465 rejected-start intervals = 1,649; 239 clips with rejected starts, 3 without admitted starts | Sidecar-derived support accounting, preserving existing feasible units; not post-cap mass, wasted training or gate benefit; no H1 policy trained | `reports/gate_candidate_audit_2026-09-06/{result.json,candidate_start_intervals.json,clips.json}` | measured reference-only audit; training disabled |

The 512-environment/100-tick pilot remains queued behind completed confirmation.
Its 2,560,000 transitions are a prospective instrumentation budget, not a scored
noise-study repetition or an executed GPU result.

## 2026-09-06 development calibration and research-plan addendum

These entries support future manuscript use; no confirmation endpoint or prior
sealed decision changes. Confirmation control benefit remains **pending**.

| Number or disposition | Use and limitation | Artifact | Class |
| --- | --- | --- | --- |
| D seed 32: mean post-warm-up TV 0.0859387133; minimum post-warm-up effective units 624.2887989; final saturation 0.7381756757; 1,118,388 completed trials; zero invalid/censored events; full calibration pass | Second fixed-D allocation replication, not control benefit; both seeds 31/32 independently replayed | `reports/research_next_2026-09-06/calibration_verification.json`; original `reports/relative_progress_2026-09-05/failure_calibration_gate_retry/seed32_result.json` | measured exploratory development |
| Gaussian stationary-noise large-unit pre-cap TV 0.0604879731; new 2,000 × 1,184-unit run, seed 260906, mean 0.0604042781, Monte Carlo SE 0.0000271173 | Illustrates that allocation contrast can exceed 0.05 without learning; equal prior, independent equal-variance Gaussian changes and inactive caps. Never subtract from actual R TV. Not the user's attached simulation. | `/home/linjiw/climb-signal-quality-2026-09-06/reports/research_next_2026-09-06/noise_only_tv.json`; generator in that worktree `tools/reproduce_noise_only_tv.py` | synthetic illustration and analytical calculation |
| 24 proposed short branches consume 29,491,200 transitions, 5% of fixed confirmation's 589,824,000; six proposed H1 arms consume 294,912,000 | Training arithmetic only; excludes evaluation, setup and noise-study settling; no runtime estimate and no branches/H1 launched | `plan/USEFUL_PRACTICE_NEXT_STEPS_2026-09-06.md`; synthetic result above records branch arithmetic | calculated prospective budgets |
| Actual estimator: decay 0.99 per 50-step tick; progress window 10 ticks; 688 ticks reduce inherited mass multiplier below 0.001 | Frozen-policy burn-in planning; multiplier is not a rate-bias bound or stationarity certificate. At 512 environments this is 17,612,800 transitions. | `reports/research_next_2026-09-06/development_inputs.json`; `climb/segment_runtime.py`, `climb/segment_command.py` | source audit plus calculation |

The unchanged comparison is queued behind seed-51 lifecycle validation and GPU
availability. The noise study, causal practice-value study, practical gate
ablation and reliability-aware redesign remain **pending/proposed**.

**2026-09-05 manuscript usage update:** E4 calibration now appears in Results §5.4;
its values remain measured 50-iteration calibration, not confirmation endpoints.
E3 now reports the existing all-26-candidate p95-of-per-clip-p95 root-velocity
deviation 1.210 m/s and root-acceleration deviation 34.91 m/s² from
`reports/dfrp_v1_exact_panel/iter1/result.json` → `fidelity` (measured reference
distortion; not tracking error or a qualification threshold).
The earlier one-seed exact-support pilot's 22,321 common-survivor frames have
adaptive-minus-uniform body-position error −4.20 mm (95% unit-bootstrap interval
[−6.63,−1.90] mm) and anchor-orientation error −0.02795 rad
([−0.03966,−0.01628] rad), from `reports/segment_v2_pilot/result.json` and
`tools/analyze_segment_pilot.py`; exploratory, insufficient allocation separation
(TV 0.014), no ALP attribution or survival-equivalence claim.

> **Corrections 2026-08-19:** three numbers in this log were wrong and are fixed in place —
> the exposure attribution (C1), the saturation-at-fall replicate count and mean (C2), and
> the per-actuator identity, now withdrawn (C3). Evidence, ground truth and reproduce
> commands: [`paper/CORRECTIONS_2026-08-19.md`](CORRECTIONS_2026-08-19.md). The two
> artifacts involved now have generators (`tools/analyze_wasted_exposure.py`,
> `tools/analyze_sat_at_fall.py`); both were hand-computed before.

| number(s) | where used | artifact path | class |
|---|---|---|---|
| top-1 mass 0.884/0.870/0.893; mean entropy 0.38–0.40 (adaptive); 0.60–0.62, top-1 0.57–0.70 (grounded) | §3, §4, F2 | `reports/A5_coverage_dose.json` | sealed-confirmatory |
| same attractor clip 3/3 seeds ×2 arms; share of concentrated iters 0.28–0.53 | §3 | `reports/A7_attractor.json` | sealed-confirmatory |
| endpoint 0.780/0.810/0.825 ± sd; AULC 0.640/0.698/0.696; paired deltas, d_z | §3, §4 | `reports/campaign_summary_3arm.json` | sealed-confirmatory |
| feasible-only strata 0.811/0.834/0.859; infeasible 0.705/0.750/0.741; grounded edge +0.025/−0.009 | §4, §6 | `reports/N_atlas_v21.json` (endpoints_2b), `plan/ATLAS_v21_RESULT.md` | exploratory → D1 primary going forward |
| non-floor derivation ε/(Σq+ε); upstream filings | §3 | `plan/RESEARCH_PLAN_v2.md` E3 row; mjlab#1153; whole_body_tracking#73; `reports/A4_upstream_issue.md` | sealed-confirmatory |
| conformance after fixes: 1.000/1.000 vs 1.000/1.000, Δerr −0.5/−0.8 mm; #44 0.000 vs 0.000 (+1.0 mm); |Δq̇| ≤ 3e-5 | §5.1, A1 | `reports/S1_KIT1226_n32_absorb.json`, `reports/S1_clip44_n32_absorb.json`, `plan/S1_RESULT.md` | confirmatory (post-fix) |
| Newton 1.5 exact-unit recertification: one easy + one contact-rich hash-bound DFRP v1 unit; placement/first-observation/first-action deltas 0; 48 resynchronized substeps `|Δq|=|Δq̇|=0`; exact contact/termination timing; two independent repeats with zero dispersion. Seven live-model import residuals precede the exact mirror. | future companion appendix / Phase N gate | `reports/newton15_recert/{UNIT_SELECTION.json,result.json,trajectories.npz,COMPLETED.json}`, `plan/NEWTON15_RECERT_RESULT.md` | unsealed measured conformance; not a policy-benefit or predictive result |
| Newton no-training predictive gate (sealed, addendum 1): three-axis fragility vector from the uniform policy does **not** predict held-out degradation beyond `infeasible_frac` + six reference-kinematic controls — adaptive partial ρ +0.141 (one-sided within-clip permutation p 0.158; threshold +0.25 / 0.05), LOCO ridge lift −0.006 (threshold +0.05); grounded ρ +0.022, lift −0.036; 40 of 42 units (units 9, 46 excluded for paired-alive < 0.80); per-axis raw ρ delay +0.42, clamp +0.27, contact −0.03 (adaptive). All instrument checks pass (zero dispersion, cross-condition Δ 0, clamp realized 12/14/13 units). | companion appendix / flagship §8 one sentence: G3 closed | `reports/newton15_pred/result.json` (`ff7e5670…`), `probe/effects.csv` (`d863abff…`), `plan/NEWTON_PRED_RESULT.md` | sealed measured null on valid data; G3 never runs |
| pre-fix forks 0.656/0.594/0.500/0.594/0.500 | A1 | `reports/S1_KIT1226_n32*.json` | withdrawn-context |
| G1 ratios (1.30–2.16×), floor ratios (≤3.2×), termination fragility 0 everywhere, failure-time agreement ≤ 0.1 s | §5.2 | `reports/G1/run0/g1_summary.json`, `plan/G1_RESULT.md` | sealed-confirmatory (negative) |
| N1: descent 0.75–1.75 s airborne, ~329 N ≈ weight (327 N) unsupported in 86 % of frames; rise 8.0–8.5 s; kneel supportable (0 N residual, both contact models); control supported every frame | §5.3, §6, F3 | `reports/N1_clip44_knee_id.json`, `reports/N1_CMU76_knee_id.json`, `plan/N1_RESULT.md` | confirmatory (measurement) |
| family: 20/40 neighbours > 10 % infeasible (12 was an informal cut, corrected) | §5.3 | `reports/N3_candidate_feasibility.json`, `plan/GLOBAL_EVAL_ADDENDUM.md` | measurement + correction |
| stratified-start baseline: #44 0/0/0/0 at 1–6 s offsets, 1.00 at 8 s; family fails in ground segments | §5.3, §8.1, F3 | `reports/N3_baseline_uniform-s1_strat.csv` | measurement |
| prevalence 22.8 % (>10 % frames); ground 39 %, dynamic 59 %, locomotion 25 %, quiet 13 %; sources 0.1–100 % | §6, F4, companion | `reports/feasibility_all/prevalence_report.txt` (+ sentinel `COMPLETED`) | measurement — **one pipeline only** (AMASS → whole_body_tracking → G1); never state it as a rate for retargeted banks generally, see the cross-bank row below |
| eval contamination 29/100 | §6, D1 seal | `reports/feasibility_e3/feasibility.csv` | measurement |
| P-TAX: median tax 0.126; 53 % > 0.1; heldout partial ρ −0.039/−0.151/−0.089; 0/3 sealed rule | §6 | `reports/P_TAX_tax_fractions.csv`, `reports/P_TAX_result.json`, `plan/P_TAX_RESULT.md` | sealed null |
| policy-consensus ρ 0.832; intrinsic transfer 0.567/0.579; +support +0.00–0.03 (n.s.); +feasibility 0.609/0.616/0.580/0.633, perm p 0.010/0.030/0.045/0.015; direct ρ(difficulty, infeas) +0.37/+0.48/+0.50 | §7, F5 | `reports/A3_atlas_transfer.json`, `reports/N2_atlas_support.json`, `reports/N_atlas_v21.json` | sealed splits per table |
| support-residual ρ +0.605/+0.544 (kNN), −0.578/−0.561 (density) | §7 | `reports/N2_atlas_support.json` | confirmed half of N2 |
| bank-invariant support change 100→800: all 22 dynamic clips lose; category table; named lists | §8.3 | `reports/support_change_heldout100_100to800.csv`, `plan/PREREGISTRATION_E3_addendum_v2.md` | sealed predictions |
| N5: floor ≈ 0 ± 1 mm; motor +11.5/−2.6/−4.6/−10.9/−0.8/−14.2 mm (run0); delay +11.9 CMU_35; termination shift −0.51 ± 0.14 s (delay, #44); contact-onset ≤ 0.03 s | §9, A2 | `reports/G1/run0/g1_v2_summary.json`, `plan/N5_RESULT.md` | calibration (exploratory label) |
| N5 replication: r = 0.92; 6/6 sign agreement > 5 mm; #44 motor +12.8 [+11.2,+14.2]; windows +0.3/+15.0/+26.8 (s0), −1.4/+16.0/+20.4 (s1) | §9 | `reports/G1/run1_seed1/g1_v2_summary.json`, `plan/N5_RESULT.md` | replication (exploratory label) |
| oracle precondition: playback survives all (err 4–13 mm); PD-follow dies on all incl. easy; kneel offsets its only survivals | §8.1 | `reports/N3_env_admits_*.csv`, `plan/N3_PRECONDITION_env_admits.md` | precondition |
| refeas demo: hover clip flags 45 % airborne/infeasible, 1.77 s free-fall-equivalent | companion | `refeas/examples/demo_hover_brief.json` (repo tag v0.1.0) | tool validation |
| ICRA F1 (CLIMB screen → DFRP route/repair → exact-support ALP system pipeline, with feasibility × support × intrinsic factorization) | ICRA §1/§3, F1 | `paper/figures/f1_feasibility_first.py` → `.png/.pdf`; exact-support counts from `reports/g_segment/unit_table.json`; DFRP qualification counts from `reports/dfrp_v1_exact_panel/iter1/result.json` | method schematic + measured artifact callouts; 22/26 is a stratified-panel qualification rate and 1,184/368,951 are support-table counts; **no ALP policy-benefit claim** |
| ICRA F2 (separate bank-scale rates + same-clip implementation agreement) | ICRA §5.2, F2 | `paper/figures/f2_bank_scale.py` → `.png/.pdf`; data `reports/feasibility_all/feasibility.csv`, `reports/feasibility_sonic/hygiene_screen.csv`, `reports/feasibility_xcheck/agreement.csv` | measured figure; full-bank bars have separate denominators and confounded pipelines; 40-clip panel is flag-enriched, not prevalence; **no causal retargeter claim** |
| F2 figure (collapse timeline + concentration bars) | §3, F2 | `paper/figures/f2_collapse.py` → `.png/.pdf`; data `reports/campaign/*.csv`, `reports/A5_coverage_dose.json` | figure |
| F4 figure (prevalence category × source) | §6, companion Fig 2 | `paper/figures/f4_prevalence.py` → `.png/.pdf`; data `reports/feasibility_all/feasibility.csv` | figure |
| F5 figure (transfer lift with perm baselines) | §7 | `paper/figures/f5_transfer.py` → `.png/.pdf`; data `reports/N2_atlas_support.json`, `reports/N_atlas_v21.json` | figure |
| citation verification (20/20 external refs live-checked 2026-08-26; LUCID internal and flagged) | §2 | `paper/CITATION_CHECK_2026-08-26.md` | verification |
| eval depression: flagged clips 6.0/7.5/8.4 pts below all-clips aggregate (8.4/10.6/11.8 below feasible stratum) per arm — supersedes the erroneous "6–11" | §6 companion §5 | `reports/N_atlas_v21.json` endpoints_2b; correction logged `paper/companion/REVIEW_2026-08-20.md` MAJOR-2 | measured (corrected) |
| gap sensitivity: 3 cm flags control 42 % (bank clearance offset); 10 cm degenerates (#44 descent reads 0); ½-weight bound stable 15.1/13.1/12.5 % at 0.25/0.5/0.75×W | companion §2 | `reports/N1_gap_sensitivity.json` | measured |
| Extreme-source 5+5 hand-check, selected at strict-flag severity quantiles 0/25/50/75/100: CNRS **5/5 ingest** ordinary walks, median lowest-geometry clearance 5.1/6.1/7.4/8.4/9.7 cm and longest >6 cm runs 1.34–3.76 s; Transitions **3/5 ingest + 2/5 content + 0/5 scene-mismatch**, with ordinary sideways running/run-backwards and standing punch among the ingest cases. | companion §4, A3, advisory | `reports/feasibility_extremes/{clips.csv,clearance_trace.csv,extreme_source_panel.png,COMPLETED.json}`; narrative `reports/upstream_drafts/CNRS_AUDIT.md`; script `tools/audit_extreme_sources.py` | measured reviewer check; severity-stratified inspection, not a source-prevalence estimator |
| per-seed Δ(uniform−adaptive) +0.0300/+0.0275/+0.0300 (endpoints 0.8137/0.8125/0.8025 vs 0.7837/0.7850/0.7725) | §3 | recomputed from `reports/campaign/*_it3999.csv`; sweep row (b) `paper/CONSISTENCY_SWEEP_2026-08-20.md` | sealed ✓ (per-seed restatement) |
| wasted exposure: adaptive mean **top-1 clip mass** 48.8 % (peak 87–89 %) — of which the impossible clip accounts for ≥ 21.9 %; it is top-1 in 34 % of logged iterations and in 2 of 3 seeds the peak belongs to another clip; clip-uniform 25 % draws / 6.1 % frames to flagged (mixed100); bank 22.8 % clips / 27.4 % duration / 9.8 % mean frames | payoff plan §0, flagship §6 (candidate) | `reports/wasted_exposure_accounting.json`; regenerated by `tools/analyze_wasted_exposure.py` | measured — **corrected 2026-08-19**: the shipped JSON's `exposure_to_impossible_clip_mean` is byte-identical to `mean_top1_mass`, i.e. a copied key, not an independent measurement. The share on the impossible clip is bracketed [21.9 %, 48.8 %]. |
| effort saturation: 0/29 actuators in the supported phase; ≥ 4/29 at ≥98 % force within 0.6 s of losing foot support in 8/8 replicates, exactly 5/29 (17.2 %) in 7/8 (world 7 is 4/29 = 13.8 %); mean 16.8 % | companion §5b, flagship §6 | `reports/effort_sat_at_fall.json` (from `reports/G1/run0/armA.npz`); regenerated by `tools/analyze_sat_at_fall.py` | measured — **corrected 2026-08-19**: was "5/29 (17.2 %) … 8/8"; 17.2 % is a per-world value, the mean is 16.8 %. Per-actuator identity is **not** recoverable from the artifact — `tools/g1_clip44_gate.py:242` collapses the actuator axis before storage. |
| repair operator validation: #44 0.13→0.00 (8.2 cm); family 27_5 0.21→0.00; worst 39_8 0.37→0.20 (needs stronger op); CNRS walk 0.66→0.01 (13.9 cm); Transitions jump correctly refused; feasible control no-op | payoff plan §2, N7 draft | `tools/repair_contact_projection.py`; per-clip `/tmp/repval_reports` → durable copies in `reports/repair_census/json/` as census covers them | measured |
| tier_800 contamination 12.4 % (99/800) → pruned bank 701 clips | E-HYG seal, §8 slot | `bank/tiers/tier_800_pruned.txt` (sha 4cfb5aea); flags `reports/feasibility_e3/feasibility.csv` | measured |
| N3: #44 feasible-phase survival base s1/s2/s3 0.000/0.031/0.188 → ground16 s1/s2 **0.750/0.750**; random16 0.000; analyzer E1∧E4 true, but adaptive E2 regression (heldout Δ −0.0346; easy control 0.857) triggers the preflight stop; E3 max top-1 after 2000 = 0.784 (fail); descent 1.000/0.688 (prediction miss) | §8, F6 | `reports/N3_result.json`, `reports/N3_*_strat.csv`, `reports/N3_adaptive-mixed100g16-s1_telemetry.csv`, `plan/N3_RESULT.md` | sealed mixed outcome — arithmetic gate passes; unqualified causal interpretation stopped by E2 |
| E-HYG: feasible heldout 0.918→0.907, Δ **−0.0101**, one-sided permutation p=0.951; all-heldout Δ −0.0132; worst decile/best half −0.0153/−0.0035; ZS-ground Δ −0.0354 inside bracket; decision P1∧P2 false | §8, companion §8 | `reports/E_HYG_result.json`, six `reports/E_HYG_uniform-amass800{,p}-s1_*_strat.csv`, `plan/E_HYG_RESULT.md` | sealed null |
| P-SIGN: family generality 7/12 (need 8), clean controls 4/12 (need 8), airborne localisation 2/7; joint rule false | §3 companion, §6, §9 | `reports/P_SIGN/run0/p_sign_summary.json`, `reports/P_SIGN/run0/analysis.log`, `plan/P_SIGN_RESULT.md` | sealed fail — runtime-detector claim rejected |
| repair operator validation placeholder (see the corrected census and DFRP rows below) | — | superseded by `reports/dfrp_v0/census/summary.{json,md}` and `reports/dfrp_v1_exact_panel/iter1/result.json` | superseded; no claim |
| repair census: legacy operator recovers 1,606/2,442 strict-flagged clips (65.8 %) through 15 cm; historical directory summary is 1,607/2,443 because it includes one feasible no-op control (C4). Historical-directory strata: 10–25 % 73.1 %, >25 % 61.7 %, ground 68.1 %, quiet 80.9 %, dynamic 51.2 % | companion §8, payoff plan §2, flagship §6/§8 candidates | strict set `reports/dfrp_v0/census/summary.{md,json}`; historical directory `reports/repair_census/summary.{md,json}`; correction `paper/CORRECTIONS_2026-08-21_DFRP.md` | measured, corrected |
| **cross-bank prevalence**: BONES-SEED (SONIC) 4,950 clips — 7 (0.14 %) > 10 % infeasible, 111 (2.24 %) > 10 % airborne, 5 (0.10 %) > 20 % infeasible; flagged duration 0.09 %; 7 `kneeling_loop_*` at airborne 1.000 / infeasible 0.000; cost **0.145 CPU-s/clip = 0.84 ms per screened frame** (the register's measured figure; the durable 2026-08-26 reproduction took 179.8 s wall on 8 workers). Threshold sensitivity: at `> 0.05` it is 29 (0.59 %) infeasible / 225 (4.55 %) airborne; at `> 0.20`, 5 / 32. The seven flagged, with `infeasible_frac`: `jump_on_50cm_002` 0.658, `kick_back_001` 0.472, `jump_off_front_50cm_R_002` 0.379, `jump_off_50cm_R_001` 0.366, `jump_off_front_50cm_001` 0.353, `high_jump_R_003` 0.138, `burpee_002` 0.136. Against this bank's 22.8 % / 23.5 % / 27.4 % (10,705 clips) | §1, §2, §6, §10, A3, companion §4 + abstract | prediction + result: `GR00T-WholeBodyControl/docs/prediction_register.md` (P10, registered before the original run, consequence pre-committed); durable 4,950-row screen `reports/feasibility_sonic/hygiene_screen.csv` (sha `c28fccb…`) + `reports/feasibility_sonic/COMPLETED.json` (0 failures; μ 0.7, gap 0.06, ½-weight, MJCF `g1_29dof_rev_1_0.xml` sha `15a330f1…`); screen `gear_sonic/research/hygiene/screen.py` | measured (pre-registered, **confirmed**); durable reproduction matches every registered threshold count and the flagged-duration headline |
| Cross-implementation same-clip check: deterministic stratified 20 BONES-SEED (7 native-flagged + 13 sampled feasible) + 20 AMASS (10 native-flagged including #44 + 10 sampled feasible), selection seed 260826. Across all 40, CLIMB vs SONIC `infeasible_frac` Spearman ρ **0.9836** (p 7.16e−30), `airborne_frac` ρ **0.9974** (p 4.13e−45); strict `infeasible_frac > 0.10` agreement **39/40 = 97.5 %**, κ **0.9485** (both 16, neither 23, SONIC-only 1, CLIMB-only 0). By bank: AMASS 20/20, ρ 1.000 infeasible / 0.998 airborne; BONES 19/20, ρ 0.962 / 0.989. The sole threshold disagreement is `burpee_002__A362_M` (CLIMB 0.019 vs SONIC 0.136). | ICRA abstract / E2 / result §2; A3; companion §4 | `reports/feasibility_xcheck/{selection.csv,agreement.csv,summary.json,COMPLETED.json}`; adapter/aggregator `tools/feasibility_xcheck.py`; model and implementation hashes in sentinels | measured reviewer check (not pre-registered); stratified agreement panel, not a prevalence estimator or retargeter-causal comparison |
| segment- vs clip-level curation on `tier_800`'s 99 flagged clips (20.2 min of 152.4 min): guard 0 s → 12.5 min (61.7 %), 584/1,259 bins, 3/99 clips lost; guard 1.0 s → 5.8 min (28.9 %), 305/1,259 bins, 26/99 lost. Bank-level: prune discards 13.3 % of duration, curation returns 8.2 % / 3.8 %. Cost 99 clips in 45 s wall on 6 CPU workers | §6, companion §8 | `reports/segments_tier800/segments_guard0.csv`, `reports/segments_tier800/segments_guard1.0.csv`, per-clip `reports/segments_tier800/full/`; reducer `tools/screen_segments.py`; derivation `plan/FGAS_DIRECTIVE_2026-08-19.md` | measured — duration claim only (no training arm has consumed curated segments); `--min-seg-s 1.0` and strict bin eligibility are choices, not measurements |
| FGAS CPU projection on mixed100 guard-0 sidecars: joint hard-rejected start mass 0.28984 measure-only, 0 hard, 0.10269 soft under a flat clip distribution | apparatus / §8 | `climb/eligibility.py`; `tests/test_fgas_sampling.py`; `plan/PREREGISTRATION_FGAS.md` | measured apparatus; the completed adaptive run shows this flat projection is not a late-run bound |
| FGAS soft guard-0, 3 matched seeds: feasible-hard20 0.7586→0.7390, Δ **−0.0196**, hierarchical bootstrap CI [−0.0497,+0.0134]; feasible-heldout Δ −0.0123; late top-1 flagged 0.861, top-1 mass 0.501, hard-rejected start mass **0.199** (gate `<0.15` fails). Final telemetry reconstructs within 0.0022; one 0.702-eligible clip contributes 0.194/0.118/0.070 rejected mass across seeds | §8 FGAS | `reports/FGAS_result.json`, `reports/FGAS_diagnosis.json`, `plan/FGAS_RESULT.md`; frozen bundle `reports/FGAS/_frozen/20260820T152154Z/` | sealed primary **not confirmed; implementation gate fails** — this clip-mean soft formulation is not validated; no broad segment-FGAS claim |
| N7 repaired800 composition: raw 3.923% → repair-all 0.903% duration-weighted infeasibility at fixed N=800; 10 residual and 12 over-offset clips remain labelled | §8 N7 | `reports/repaired800/manifest.json`; `plan/REPAIRED800_COMPOSITION.md`; `plan/N7_DRAFT_repair.md` | measured bank composition |
| N7 one-seed 2×2: deployment R/repaired − K/raw **+0.0397**, motion-bootstrap CI [+0.0153,+0.0658] (misses +0.05 SESOI); R/raw − K/raw −0.0036; K/repaired − K/raw +0.0233; interaction +0.0200. Heldout100 −0.0104 (point guard passes); ZS-ground R−K −0.0199 and R−P +0.0155 (coverage fails); overall false | ICRA E3 / result §3; flagship §8.2 | `reports/N7_result.json`, six `reports/N7/*.csv`, `plan/N7_RESULT.md` | sealed joint fail; motion bootstrap is not seed uncertainty |
| N7 post-outcome integrity: `heldout100` contains 8 tier800 training motions; disjoint92 delta −0.0122, CI [−0.0316,+0.0012], feasible-disjoint68 −0.0137, CI [−0.0391,+0.0024]. Deployment delta by repair stratum: certified78 +0.0160, over-budget11 +0.2305, residual10 +0.0143 | §8.2 limitation / v2 design | `reports/N7_posthoc_audit.json`, `tools/diagnose_n7_result.py`, `plan/N7_RESULT.md` | exploratory post-outcome; frozen decision unchanged |
| DFRP v0 legacy routing: 644/2,442 (26.4 %) strict-flagged clips fit the 8 cm primary displacement budget; 962 (39.4 %) additional clips fit 8–15 cm; all are legacy root-only and qualification-incomplete, so zero are training-eligible. Two-clip root+IK development view: 1 feasible byte-identical no-op + 1 repair 0.1010→0.0303 infeasible, 39.8 mm root, 0.992 mm contact residual, 76 legal starts total | DFRP direction / future §8 method | `reports/dfrp_v0/{census,dev_panel}/`, `plan/DFRP_V0_RESULT_2026-08-21.md` | unsealed measured implementation; no policy outcome |
| DFRP v1 frozen exact panel: 22/26 flagged candidates (84.6 %) pass residual ≤5 %, root ≤8 cm, joint-limit, IK-residual ≤10 mm, hash-bound exact-support, and legal-start gates; 4/4 feasible controls are byte-identical/ready. Curated view: 26 clips, 36 units, 10,561 legal 50-step starts; median/p95 CPU runtime 2.57/6.29 s per clip. Two residual-infeasibility and two IK-qualification failures are excluded. | ICRA E3 / result §3; DFRP direction / flagship future §8 method | `reports/dfrp_v1_exact_panel/iter1/{result.json,curated_manifest.json,unit_table.json}`, `plan/DFRP_V1_EXACT_PANEL_RESULT_2026-08-21.md` | unsealed measured implementation on a stratified panel; not a bank-wide recovery rate or policy outcome |
| Phase-G endpoint-blind G2 manipulation calibration: 2/12 screen candidates pass; deterministic selection rho 0.40 / lambda 0.05 has screen TV 0.1310/0.1063/0.0865 (mean 0.1079), then independent-seed TV 0.1292/0.1045/0.0831 (mean 0.1056), minimum 700.1 effective units, maximum top-1 0.0134, zero invalid/censored events, and saturation 0.2365 | Phase-G preregistration / future ICRA experiment | `reports/g_segment/calibration/result.json`, 39 hash-bound ledgers, `plan/G2_CALIBRATION_RESULT_2026-09-04.md` | unsealed measured manipulation only; no evaluator or policy-performance endpoint read; no policy-benefit claim |


## 2026-09-05 execution addendum: E4 disposition and next candidate

These entries supersede earlier pending labels for the named experiments only.
No sealed artifact, endpoint definition, or prior outcome has been amended.

| Number or disposition | Use and limitation | Artifact | Class |
| --- | --- | --- | --- |
| E4 seed-1 mean post-warm-up TV 0.0296587 < 0.05; both 4,000-iteration arms complete; `not_tested` | Future E4 results wording; policy endpoints unopened, seeds 2–3 stopped. This is not a policy null. | `reports/g_segment/confirmation/seed1/manipulation_result.json` | sealed manipulation decision |
| Absolute-floor focus-normalizer share 64.3% at iteration 500 → 93.6% at 3999; relative κ=2 replay mean TV 0.0854, range 0.0560–0.1087, eight snapshots | Motivation for separate candidate; fixed recorded histories cannot establish live allocation or learning benefit. | `reports/g_segment/confirmation/allocation_diagnosis.json` | measured replay plus exploratory counterfactual |
| DFRP one-policy, 26 clips, 656 paired conditions per arm: clip-weighted TrackingScore raw 0.392505 → repaired 0.391502, Δ −0.001003, clip-bootstrap 95% CI [−0.008588,+0.008020]; raw/repaired trial successes 409/656 and 397/656 | Future repair follow-up; no aggregate gain established. Clip-weighted score and trial-level success denominators differ. Short windows, two training-overlap clips, unchanged-control numerical differences, and one policy limit scope. | `reports/dfrp_policy_validation_2026-09-05/result.json`, `strata.all.all_conditions` | measured exploratory fixed-policy deployment comparison |
| Relative-progress R0: seed 11, 8 environments, 20 iterations, 184 completed trials, 0 invalid/censored events, 17 s; strict smoke pass | Implementation evidence only; incomplete history gives approximately zero TV. R1 launched with 512 environments / 4,000 iterations; sustained manipulation and policy benefit remain pending. | `reports/relative_progress_2026-09-05/smoke_result.json`, `smoke_s11.log`, `study_s11/design.json` | measured exploratory lifecycle smoke; long-run result pending |


## 2026-09-05 R1 completed manipulation result

| Number / disposition | Scope and limitation | Artifact | Class |
| --- | --- | --- | --- |
| Relative ALP seed 11: full 4,000 iterations / 512 environments; 41 checkpoints, 37 post-warm-up snapshots; mean TV 0.0832114, individual range [0.0489606,0.1082347]; min effective units 616.2498; max post-warm-up unit/clip mass 0.0177383/0.0184985; final saturation 0.737331; 1,087,814 completed trials, zero invalid/censored events; manipulation pass | Replaces pending R1 label only. One exploratory seed; no tracking or rank-informativeness claim. TV band applies to the run mean, not every snapshot. The earlier E4 uses a different seed and is not a paired performance comparator. | `reports/relative_progress_2026-09-05/study_s11/long_result.json`, `seed11_recovery_verification.json`, `continuation_recovery/seed11_figure/` | measured exploratory manipulation |
| R1 elapsed training 2,680 s (0.744444 GPU-hours elapsed); shared-GPU baseline/peak total 1,382/12,841 MiB | Shared GPU, including other processes; not isolated allocator overhead, process memory or throughput benchmark | `reports/relative_progress_2026-09-05/study_s11/long.log` | measured execution cost |

The first continuation stopped before seed 12 because it resolved relative smoke
ledger keys to absolute paths. Both original smoke/long results replay exactly
when path spelling is preserved; the corrected wrapper changes no scientific
threshold or checker. Failed source/design/log are retained. Seed 12 remains
queued, with independent replication and policy benefit pending; see
`plan/RELATIVE_PROGRESS_R1_RESULT_2026-09-05.md`.

## 2026-09-05 R1 sampler-signal diagnostic

These descriptive numbers are recorded for possible future paper use; they do
not change a sealed result or establish policy benefit.

| Number / disposition | Scope and limitation | Artifact | Class |
| --- | --- | --- | --- |
| Declining estimated success receives 0.4660473 of positive excess sampling mass | Unweighted mean of 37 post-warm-up snapshot fractions in R1 seed 11; denominator is positive probability mass above deployment prior, not all trials. Forgetting and estimation noise are unresolved alternatives. | `reports/relative_progress_2026-09-05/rank_signal_s11/result.json` | measured exploratory sampler diagnostic |
| Adjacent absolute-progress ranking Spearman correlation 0.4223621; progress/failure 0.2814350; progress/recent-attempt count 0.4607236 | Means over 36 adjacent snapshot pairs or 37 within-snapshot correlations, respectively. Correlated observations, endogenous exposure, no inferential or independent-replication claim. | `reports/relative_progress_2026-09-05/rank_signal_s11/result.json`, `snapshots.csv` | measured exploratory correlations |
| Fixed D allocation on R histories has mean TV 0.0859453 | Holds R histories fixed; not a D training result and not used for profile selection. Actual D seeds 31/32 remain pending. | `reports/relative_progress_2026-09-05/rank_signal_s11/result.json` | exploratory counterfactual replay |

Definitions, execution queue and remaining confirmation requirements:
`plan/RELATIVE_SIGNAL_DIAGNOSIS_2026-09-05.md`. No diagnostic changes the
queued independent replication, baseline profile, or policy endpoint rules.

## 2026-09-05 R2 lifecycle and execution addendum

| Number / disposition | Scope and limitation | Artifact | Class |
| --- | --- | --- | --- |
| Relative ALP seed-12 smoke: 8 environments, 20 iterations, 192 completed trials, zero invalid/censored events, 17 s, strict `smoke_pass` | Lifecycle evidence only. Full 512-environment / 4,000-iteration replication launched 18:30:27 EDT; complete manipulation and policy benefit remain pending. | `reports/relative_progress_2026-09-05/continuation_gate_retry/study_s12/smoke_result.json`, `smoke.log`, `long_command.json` | measured exploratory simulator smoke |

The preceding `continuation_recovery` attempt stopped at a GPU poll miss before
seed-12 training launched. It is an operational stop, not a manipulation failure
or discarded seed. Original logs/design/terminal records remain preserved.
`plan/RELATIVE_CONFIRMATION_READINESS_2026-09-05.md` documents the unchanged
restart and developing secondary-analysis definitions. Synthetic campaign test
results do not supply any new paper-bound policy-performance number.

## 2026-09-05 completed relative-ALP replication and input audit

| Number / disposition | Scope and limitation | Artifact | Class |
| --- | --- | --- | --- |
| Seed 12: 4,000 iterations / 512 environments; 41 snapshots, 37 post-warm-up; mean TV 0.0827283432, range [0.0507759,0.1013988], minimum effective units 618.611481, maximum unit/clip mass 0.0223513/0.0223513, final saturation 0.7331081, 1,086,192 completed trials, zero invalid/censored events; manipulation pass | Both planned development seeds now pass and reproduce. Sustained allocation only; policy utility, ranking utility and transfer remain pending. Probability extrema/effective-unit minimum are post-warm-up. | `reports/relative_progress_2026-09-05/replication_review.json`, `continuation_gate_retry/study_s12/long_result.json` | measured exploratory simulation replication |
| Seed-12 declining-estimate share of positive excess mass 0.4680896; adjacent rank correlation 0.4029245; progress/failure correlation 0.2747052; progress/new-attempt correlation 0.4469226; D fixed-history TV 0.0849016 | Unweighted correlated-snapshot summaries: 37 excess/failure/TV snapshots, 36 adjacent-rank/attempt intervals. Positive excess mass is not all training draws; D replay is not D training. | `reports/relative_progress_2026-09-05/rank_signal_s12_corrected/result.json`, `replicated_rank_diagnostic.csv` | measured exploratory diagnostics and counterfactual |
| Full R1/R2 elapsed training: 2,680 + 3,373 = 6,053 s, 1.681389 elapsed GPU-hours | Two full probes only; excludes smokes, waiting, engineering, evaluations and prior studies. Shared device, not GPU-active time, isolated overhead, or energy. The intervening gate miss launched no training. | `reports/relative_progress_2026-09-05/replication_execution_cost.json` | measured scoped execution cost |
| 900 motion identities verified; 800 training / 100 evaluation, zero content overlap; 2,800 conditions reconstructed from current headers | CPU reference-input audit only; does not certify confirmation execution or policy performance. | `reports/relative_progress_2026-09-05/replication_reference_audit.json` | measured input verification |

**Corrections without changed measurements:** the earlier seed-11 attempt-count
correlation 0.4607236 averages **36** valid adjacent-snapshot intervals, not 37;
the first post-warm-up snapshot has no predecessor. The seed-12 diagnostic's
initial figure title incorrectly said “Seed 11”; its JSON already said seed 12.
The original figure/source are preserved, with an equality-checked caption
correction in `rank_signal_s12/caption_correction.json`. Use the corrected
seed-12 figure. No scientific gate, rank statistic, or sealed result changed.


## 2026-09-05 confirmation implementation disposition

The fixed confirmation trainer, checkpoint ledger and scheduler are implemented;
the actual draft passes CPU source/configuration/reference preflight. The draft
keeps confirmation disabled. New seed-51 entrypoint smokes are queued after
fixed D calibration; simulator validation, the complete new frozen-contract
integration audit, prospective freeze and policy utility remain **pending**.
No paper-bound policy-performance number changes in this update. Synthetic
tests and configuration audits are implementation evidence only. See
`plan/RELATIVE_CONFIRMATION_EXECUTION_2026-09-05.md` and
`reports/relative_progress_2026-09-05/confirmation_execution_verification.json`.


## 2026-09-05 evaluator compatibility correction

**Measured implementation defect:** the sealed evaluator rejects the sealed
Phase-G condition file because it contains two additional provenance fields;
all shared fields and all 2,800 conditions match exactly. The prior reference
input audit did not certify the evaluator CLI. A separate adapter validates
the unchanged sealed file, complete payload and provenance, then reuses the
sealed rollout implementation. New evaluation metadata binds the adapter.
No scientific condition, sealed source, sealed manifest or paper-bound policy
number changes. Strict-contract synthetic integration is implementation evidence;
actual benchmark execution and policy utility remain **pending**. The previous
seed-51 queue was superseded before any smoke launched. Details and preserved
identities: `plan/RELATIVE_EVALUATOR_ADAPTER_2026-09-05.md`.


## 2026-09-05 completed four-arm development lifecycle

| Number / disposition | Scope and limitation | Artifact | Class |
| --- | --- | --- | --- |
| U/A/R/D seed-41 smokes: 191/183/177/198 completed trials; eight environments, 20 iterations each; all four smoke passes with zero invalid/censored events | Complete source-bound sampler/checkpoint replay reproduces. Short-run counts are lifecycle counters, not policy comparisons. | `reports/relative_progress_2026-09-05/development_smoke_review/result.json` | measured development simulation |
| U/A/R/D elapsed smoke job time: 20/21/18/16 seconds; total 75 seconds, 0.020833 elapsed GPU-hours | These four jobs only, shared device; excludes queue time, CPU checks and all other studies. Not GPU-active time or energy. | Same review, original four smoke logs | measured scoped execution cost |
| All four actual development checkpoints pass strict CPU actor-only loading, including exact normalization restoration | Fixed zero observation stub; no simulator, policy forward call or rollout. Runtime tracking and policy utility remain pending. | `reports/relative_progress_2026-09-05/development_smoke_review/checkpoint_loading.json` | measured CPU lifecycle verification |

D seed-31 calibration is now running; its interim snapshots are not a complete
scientific pass. Assigned seeds, profiles and held-out endpoint rules remain
unchanged. No paper-bound policy-performance number changes. Next research
plan: `plan/RELATIVE_DEVELOPMENT_SMOKES_2026-09-05.md`.


## 2026-09-05 prospective three-seed precision sensitivity

| Quantity | Scope and limitation | Artifact | Class |
| --- | --- | --- | --- |
| Fixed three-seed 95% t-interval half-width = 2.4841377 × sample SD; observed mean +0.02 requires sample SD <0.0080511 for positive lower bound; observed panel mean zero requires SD <0.0040255 for the −0.01 guard | Algebra of the existing decision rule; not an estimate of actual training-seed variability. | `reports/relative_progress_2026-09-05/design_precision/result.json` | prospective design calculation |
| Hypothetical hard-panel benefit probabilities at (true mean, population SD): (+0.02,0.01) 30.8889%; (+0.02,0.02) 14.7528%; (+0.04,0.01) 90.8375%; (+0.04,0.02) 46.6744% | IID normal paired-seed model, illustrative unfitted parameters; one necessary gate only, conditional on all manipulation/provenance gates. Not measured policy evidence or full campaign power. | Same result; `hypothetical_primary.csv` | hypothetical operating scenarios |
| With hypothetical all-panel mean zero and SD 0.01, guard pass probability 17.8610%; combining hard mean +0.04/SD 0.01 gives full-positive Frechet bounds [8.6985%,17.8610%] | Does not assume independence of hard/full-panel summaries; normal approximation and no fitted variances. | Same result; `design_precision.pdf` | hypothetical bounds |

No method, assigned seed, budget, condition, threshold or queued source changes.
No benchmark policy outcomes are read. The sensitivity informs interpretation of
an inconclusive result and does not authorize optional seed additions. Exact
assumptions, derivation and next-study distinctions:
`plan/RELATIVE_DESIGN_PRECISION_2026-09-05.md`.


## 2026-09-05 fixed D seed-31 complete calibration

| Number / disposition | Scope and limitation | Artifact | Class |
| --- | --- | --- | --- |
| D seed 31: 4,000 iterations, 512 environments; mean TV 0.0849553389 over 37 post-warm-up snapshots, range [0.0083017,0.1182816]; minimum effective units 625.061738; maximum unit/clip mass 0.0172129/0.0172129; final saturation 0.727195946; 1,113,773 completed trials; zero invalid/censored events; calibration_pass | All 41 checkpoint/sampler histories reproduce. One fixed-baseline development seed only; planned seed 32 remains pending. Mean gate does not constrain each snapshot, and D has no upper 0.15 gate. | `reports/relative_progress_2026-09-05/failure_seed31_review/result.json`, original `failure_calibration_gate_retry/seed31_result.json` | measured exploratory calibration |
| D seed-31 elapsed training: 2,229 s / 0.619167 GPU-hours; one launch, successful terminal | Shared device; baseline/peak total memory 388/9,519 MiB. Excludes smokes, queue, evaluation and CPU engineering; not speed, energy or isolated GPU-active-time evidence. | Same review, original `seed31.log` | measured scoped execution cost |

The complete R11/R12/D31 allocation figure keeps unequal replications separate.
Similar mean TV does not establish identical allocation, comparable startup
exposure, progress-ranking utility or policy quality. No benchmark policy
endpoint was opened. Result and next freeze requirements:
`plan/RELATIVE_D_SEED31_RESULT_2026-09-05.md`.


## 2026-09-05 prospective freeze command implementation

The finalization command is implemented and tested. It refuses incomplete
actual prerequisites without writing enabled profiles, and verifies/seals a
complete explicitly synthetic contract without launching jobs. This supplies
implementation evidence only. Actual D replication, new-trainer lifecycle,
confirmation freeze and held-out policy utility remain **pending**. No
paper-bound performance number or scientific design changes. Details:
`plan/RELATIVE_CONFIRMATION_FREEZER_2026-09-05.md`.

## 2026-09-05 public relative-progress research checkpoint

The GitHub Pages update exports the already recorded R11/R12/D31 allocation
histories, E4 `not_tested` disposition and fixed-policy DFRP result with their
claim boundaries. No measured performance value changes. Public source identities
and the 23:10 EDT pending-state snapshot are in
`docs/assets/relative-progress/research_snapshot.json`; explanation and fixed
next-study design are in `docs/relative-progress.html`. Partial D32 progress is
operational status only and is excluded from the completed-run figure and table.
