# H1 checkpoint-to-evaluation development validation

2026-09-06. **Unsealed development addendum.** This advances the matched
feasibility-admission comparison without changing the live U/A/R/D confirmation
or enabling the full H1 study.

## Existing full-entrypoint work independently replayed

The gate worktree already contains `tools/train_gate_study.py`, configuration/
contract helpers, support manifests and the complete 41-checkpoint provenance
verifier. Its existing seed-81 CPU entrypoint smokes were independently replayed
this turn. Their draft contract remains:
`/home/linjiw/climb-gate-ablation-2026-09-06/reports/gate_entrypoint_2026-09-06/preparation/draft_contract.json`,
SHA-256 `57f36c6c20cb0cfbf09e08a479dc215164527e91487101056ac23444ae2f6ea2`.
All 386 bound runtime files still match and full training is disabled.

| Entry smoke | Environments | PPO iterations | Transitions | Completed trials | Rejected-support completed trials |
| --- | --- | --- | --- | --- | --- |
| Gate-on, seed 81 | 8 | 20 | 3,840 | 183 | 0 |
| Gate-off, seed 81 | 8 | 20 | 3,840 | 173 | 25 |

Both checkpoint schedules (0/19), sampler state, source/configuration identity,
event accounting and admission-specific probability bounds replay exactly.
Invalid starts, invalid reference frames and censored resets are zero. Initial
actor hashes are identical. Final gate-off rejected probability is
0.11375725722182886; gate-on is zero. These are training-integrity and support-
exposure checks, not policy-benefit evidence. They are separate from the earlier
seed-71 runtime smoke documented in `MATCHED_GATE_RUNTIME_2026-09-06.md`.

## New paired development evaluator

New code lives in the isolated ICRA worktree, preserving the gate draft's complete
source inventory: `tools/eval_gate_development.py` and
`tools/analyze_gate_development.py`. The launch adapter verifies the gate contract
and replays **both** training smokes before opening a development evaluation.
It checks matched training initial actors and rejects held-out clip overlap.

The original paired evaluator from the gate worktree loads each arm's checkpoint
19, using its unchanged 13 actor/normalization state tensors. The new recorder
authenticates exact equality to the saved checkpoint, counts actual environment
steps and verifies inference immutability. The analyzer checks output hashes,
training/checkpoint links, source/software identity, common-reference hashes,
paired startup/initial state and the unchanged TrackingScore aggregator.

Inputs were fixed before execution: first two training-list clips, phases 0/0.5,
four worlds per arm, one-second windows, CPU, evaluation seed **26090671**,
joint-noise seed **26090672**, task **Climb-Tracking-Flat-Unitree-G1**. Training
seed remains **81**; evaluation seeds are not additional independent training
replicates. All eight rows are retained, including failed episodes. Clip scores
are finite, positive and at most one. No on/off efficacy contrast or confidence
interval is interpreted from this smoke.

## Preserved environment-path failure and rerun

The first gate-on policy rollout wrote its CSV, then failed while writing source
metadata because the gate worktree lacked the `mjlab-1.6.0` directory expected
by the original evaluator. Its log, partial CSV and `execution_stopped.json` are
preserved in the ICRA worktree's `reports/gate_evaluator_development_2026-09-06/`.
This incomplete output is not a passing evaluation.

A local symlink now maps
`/home/linjiw/climb-gate-ablation-2026-09-06/mjlab-1.6.0` to the original pinned
environment `/home/linjiw/climb-feasibility-first/mjlab-1.6.0`. No simulator or
gate source was changed. Both arms were run into the fresh directory
`reports/gate_evaluator_environment_fixed_2026-09-06/` in the ICRA worktree.
Its separately recorded design hash is
`1efa563866b3765651132066ac0cd0ae3653d9382d6ced97c19f1b77d1028070`.
This was a documented development environment repair; no frozen scientific
job was retried.

Both arms now pass. Exact launch argv, seeds/task, raw logs, CSVs, metadata,
policy tensors, receipts and `verification.json` are retained beside the design.
The evaluation adapter cannot enable full H1 evaluation.

## Tests and next gates

Nine tests pass: complete measured replay; rejection of altered pairing,
checkpoint/condition metadata, swapped actors, changed normalization counts,
CSV corruption and arm identity; and rejection of full evaluation through the
development adapter. Compilation, both original seals, all 376 original runtime
hashes and all 386 gate runtime hashes pass. Existing pilot and GPU-validation
dependency bindings also remain unchanged.

Exact verification commands, artifact/source hashes and queue snapshot are in
the original repository's `reports/gate_evaluator_development_2026-09-06/`.
A preliminary search found no training-start log markers for candidate seeds
61/62/63 in the inspected local CLIMB report/run/log directories. It is recorded
as `candidate_seed_scan.json`, **not** as a complete fresh-seed audit and cannot
authorize H1. A complete audit must be refreshed before the future freeze.

Remaining H1 prerequisites: resolve and record original confirmation; complete
fresh-seed audit; validate both full entrypoints on GPU; finish the full paired
evaluation/analysis adapter and all-training-before-evaluation scheduler; freeze
the independent H1 contract before full training. The draft proposes six training
jobs and 24 evaluation cells. This development result does not enable them.

At 13:21:21 EDT, original confirmation remains 2/12 training jobs complete and
0/48 cells evaluated. R21 waits for shared GPU capacity (4,287 MiB free, 97%
utilization). Confirmation, pilot, efficiency and GPU-conformance supervisors
remain alive; no GPU-validation cell has started. Full H1 remains unscheduled.
