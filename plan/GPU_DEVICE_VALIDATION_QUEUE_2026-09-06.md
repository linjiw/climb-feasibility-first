# Device validation entrypoint and queued GPU conformance

2026-09-06. **Unsealed operational/development addendum.** The full confirmation
contract, statistical decisions and original runtime files remain unchanged.
New code and per-cell artifacts are in
`/home/linjiw/climb-icra-evidence-2026-09-06`.

## Measured CPU prerequisite

`tools/eval_device_lifecycle.py` runs the existing paired evaluator on the device
specified by a source-bound development design. It composes the validated
physical operators, partial-reset correction, entity-reset recorder and policy
immutability observer. A scoped Warp launch observer records actual launches of
the simulator's step, forward, reset and sensing CUDA graphs. Original imports
are restored when the context exits.

Before any GPU queue was activated, the new entrypoint ran **original, unchanged
and 20 ms delay** on CPU. It reused the fixed natural-lifecycle batch: development
R11/2000, five training clips, seven worlds, horizons
[56,143,115,150,150,150,150], environment seed 26090661, joint-noise seed 26090662,
task `Climb-Tracking-Flat-Unitree-G1`. The prior reference-only clip selection and
held-out disjointness checks remain applicable.

All **21 CPU episode rows** reproduce the prior CSVs byte for byte. The device
receipt correctly reports CPU with no CUDA graphs or launches. Native scoring,
natural failure and early-success coverage, reset isolation, realized delay,
physical checks and policy immutability replay successfully. These are repeated
development cases, not new independent policy-effect replications.

Raw design, per-cell exact argv/logs, CSVs, metadata, graph receipts and tensor
traces are in `reports/device_lifecycle_cpu_2026-09-06/`. Its pre-execution design
SHA-256 is `d9993fd8413cf483f8688b8f33fd4d95a0add149ae9d1d7cbad33baa1ca213f5`.
Aggregate verification uses `tools/analyze_device_lifecycle.py` and is saved as
`verification.json` in that directory.

## Bound GPU acceptance checks

The GPU design uses the same seven-world training-only batch across original
plus all eight physical conditions. Device is `cuda:0`; full evaluation remains
disabled. CPU/GPU outcome equality is not required: acceptance compares original
and unchanged outputs **within the same device**. No cross-device tolerance is
tuned after observing GPU output.

The fixed GPU checks require:

- Exact original/unchanged CSV parity, paired initial physical inputs/actions,
  matching source/condition/receipt identities and complete raw traces.
- Actual CUDA graph use: all four graph objects present, exactly one recorded
  step-graph launch per physics step, and observed forward/reset/sense launches.
  A device label alone does not pass this check.
- Finite, exactly unchanged actor/normalization tensors; inference-call counts
  equal actual vector-loop length, including early completion.
- Exact unselected-world reset-state preservation, cleared selected delayed
  histories and per-world delay replay across environment and command resets.
- Native metric replay at rtol 1e-6 / atol 1e-7 and actuator force bounds with
  1e-4 N·m tolerance, matching the preceding development verifiers.
- At least one natural failure, early successful retirement and environment
  reset in each condition. Missing coverage remains incomplete; it does not
  trigger changes to the batch or acceptance thresholds.

These checks are prospective; **GPU results are pending**. CPU execution and
synthetic graph-receipt tests do not establish CUDA graph conformance.

## Queue activated with confirmation and pilot priority

GPU design:
`reports/device_lifecycle_gpu_2026-09-06/design.json` in the isolated worktree.
SHA-256: `6d445e068966dae661e10679d4e9d44ffac8a6e0321351f22e1df7ed6ed40b46`.
It binds the new sources, transitive development/runtime inputs, CPU verification,
confirmation schedule and pilot queue identity. Acceptance checks and job order
are fixed before any GPU result.

`tools/queue_device_lifecycle.py` was launched at 12:46:32 EDT as **PID 2286869**.
It first requires successful terminals from:

1. `confirmation_freeze/campaign_gpu_reentry_2026-09-06/terminal_status.json`,
   with the completed-job list exactly matching the bound 60-job schedule.
2. The frozen-policy pilot's
   `reports/frozen_progress_pilot_2026-09-06/queue_gpu_reentry_2026-09-06/terminal_status.json`
   in the signal-quality worktree, with its expected development completion status.

A stopped/invalid/not-tested prerequisite stops this queue. It cannot bypass or
restart either prerequisite. Once both complete, each GPU cell requires at least
14,000 MiB free and utilization at most 60%, with source checks repeated before
launch. Operational waits are 172,800 seconds for prerequisites and 86,400 seconds
for each GPU availability gate. Each cell gets one attempt; no automatic retries.
The final CPU analyzer must pass before the queue reports GPU development success.

The scheduler has been verified alive and waiting for both prerequisites, with
all nine cell output directories absent. Queue artifacts are under
`reports/device_lifecycle_gpu_2026-09-06/queue/` in the isolated worktree. Exact
supervisor argv/PID, log and snapshot are in the original repository's
`reports/device_lifecycle_queue_2026-09-06/`.

## Verification and remaining work

Eleven tests pass: measured CPU entrypoint replay, five malformed GPU graph
receipts, both-prerequisite enforcement, stopped prerequisite cases and changed
source/CPU-gate rejection. Compilation passes. Both checked seals and all 376
original runtime hashes match. Exact commands and source hashes:
`reports/device_lifecycle_queue_2026-09-06/verification.json` in the original repo.

At 12:47:17 EDT confirmation remains **2/12 trained, 0/48 evaluated**, with R21
next; GPU validation is **0/9 started**. The GPU has 4,327 MiB free at 68%
utilization. Confirmation, pilot, efficiency and GPU-validation supervisors are
alive. The current queue owns no GPU process.

After measured GPU conformance, integrate the validated operators and reset
handling into the separately bound general physical-study evaluator and complete
its prospective freeze before full evaluation. The matched feasibility-gate
training study and policy-noise attribution remain separate research questions.
No robustness benefit, sample-efficiency gain, recovery mechanism or hardware
transfer is established by this queue preparation.
