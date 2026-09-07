# Confirmation progress and inference immutability

2026-09-06, 12:10 EDT. **Unsealed progress addendum.** All confirmation settings
and sources remain governed by the existing immutable contract. This supersedes
the earlier U21 iteration-2000 status, preserving its historical records.

## Measured training progress

| Arm | Seed | Final iteration | Completed trials | Mean allocation TV | Training elapsed |
| --- | --- | --- | --- | --- | --- |
| U | 21 | 3999 | 1,086,702 | 0 | 2,014 s |
| A | 21 | 3999 | 1,084,430 | 0.029759170164293084 | 2,221 s |

Both ran exactly once, exited successfully and reported no OOM. Independent
`verify_training(training_record(job), ...)` replayed all 41 ledger/checkpoint/
sampler snapshots per arm and reproduced each scheduler gate exactly. This
includes source/configuration identity, event accounting, zero invalid starts,
zero invalid reference frames, zero censored resets and advancing sampler clocks.
A's absolute-floor comparison deliberately has no minimum-TV gate; its smaller
allocation change is a descriptive result, not grounds to alter or remove it.

Evidence: `reports/gpu_reentry_2026-09-06/completed_training_replay_1208.json` and
`reports/relative_progress_2026-09-05/confirmation_freeze/campaign_gpu_reentry_2026-09-06/`.
Exact training argv/task IDs are in `schedule.json`; execution times and return
codes are in `U_s21.log` and `A_s21.log`. Both use 512 environments and 4,000 PPO
iterations. U finished at 11:02:25 EDT; A at 12:02:42 EDT.

**Pending:** 10 training jobs and all 48 held-out evaluation cells. R21 is next.
At 12:10:49 EDT the GPU had 7,524 MiB free and 62% utilization, below the existing
14,000 MiB free / at-most-60% launch gate. Scheduler PID 2008052 remains alive and
will launch automatically when that gate passes. No duplicate scientific job was
launched and other users' jobs were not interrupted. The original pilot and
efficiency continuations remain alive. No endpoint-access record exists.

Primary policy benefit, efficiency gains, robustness and forgetting recovery are
still untested. Confirmation retains the preregistered two-sided 95% paired t
interval, mean feasible-hard R−U improvement at least 0.02, positive lower bound,
and all-panel lower-bound guard greater than −0.01. No confidence rule was changed
to match later strategic wording.

## Measured CPU inference audit

New code is isolated in `/home/linjiw/climb-icra-evidence-2026-09-06`:
`tools/audit_policy_immutability.py` and `tools/analyze_policy_immutability.py`.
The previously bound evaluator and intervention implementations remain unchanged.
The wrapper observes the registered inference policy, snapshots every named
parameter and buffer, checks evaluation mode at every forward call, then saves
before/after tensors. The analyzer authenticates receipts, independently replays
those checks and reruns the earlier physical-telemetry/parity verification.

Inputs are unchanged development R11/2000, the first two fixed training clips,
phases 0 and 0.5, one-second windows, four worlds, environment seed 26090651,
joint-noise seed 26090652, CPU and task `Climb-Tracking-Flat-Unitree-G1`.
The design was recorded and source-bound before execution with SHA-256
`d9169391b3688a123961bf8285c2acf6740ee2796c92e6e7fe7099daa3a3dfa8`.

All nine cells (original plus eight physical conditions) pass:

- All **9 actor parameter tensors and 4 observation-normalization buffers** are
  finite and exactly unchanged before/after each rollout, including normalization
  count. Initial tensors also match across all cells.
- All modules remain in evaluation mode across **50 forward calls per cell**,
  **450 vector inference calls total**.
- All nine CSVs match their previous counterparts byte for byte. Full startup,
  initial observation/action, realized delay, force and friction checks replay.
- These are the **same 36 development episode rows replayed**, not additional
  independent samples. No held-out panel or physical robot was evaluated.

Raw artifacts, source-bound design, per-cell exact launch argv, logs, CSVs,
metadata, before/after tensors and aggregate `verification.json` are in the
isolated worktree's `reports/policy_immutability_2026-09-06/`.

Nine tests pass, including changed weights, normalization moments/count, final
and interim training mode, missing forward calls/buffers and nonfinite tensors.
Verification commands and seal checks are recorded in the original repository's
`reports/gpu_reentry_2026-09-06/immutability_checks.json`.

## Next executable work

1. Let the existing confirmation scheduler take available GPU capacity for R21,
   D21 and the remaining seeds; preserve its single-attempt failure stops.
2. Exercise policy failure, world retirement and partial-reset handling on a
   separately recorded development fixture, then verify GPU execution/parity.
3. Run the already queued frozen-policy progress pilot after confirmation; it
   will inform the noise-versus-recovery mechanism study without changing the
   completed confirmation protocol.
4. Finish the matched feasibility-gate comparison audit and separately freeze
   any full physical-sensitivity study. Hardware transfer remains pending.
