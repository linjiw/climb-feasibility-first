# Autoresearch log — 2026-08-27 00:40 EDT — N-c probe launch, harness repairs, Phase-G seal draft

## Context

Phase N was sealed and probe-ready at commit `c4d1d6f`. This session launched the real 42-unit
Newton predictive probe (`tools/newton15_pred_probe.py`) and drafted the Phase-G seal on CPU.
No sealed file, manifest, or frozen analyzer was touched; all seal hashes re-verified `OK`
(`plan/PREREGISTRATION_NEWTON_PRED.md.sha256`, analyzer `1324aa6f…`, reference CSV `406ec407…`).

## Discarded integration artifacts (not measurements)

1. **First launch (00:43): int32 overflow at env build.** With the recert's global
   `warp.config.deterministic_max_records = 630`, Warp allocates `launch_dim × 630` deterministic
   scatter records for MJWarp's sparse-Hessian solver kernels (`module="unique"`; the bound is
   legitimately `nv(nv+1)/2 = 630` for G1). The buffer scales roughly quadratically with world
   count: 8.55 G records at 42 worlds (int32 overflow), ~1.6 GB keys at 8 worlds. Newton's own
   `SolverMuJoCo._scoped_deterministic_config` applies the same floor to its lazily-created
   kernels, so this is a property of the pinned stack, not of the probe. MJWarp/Newton are sealed
   pins and were not patched.
2. **`flatten_observation` iterated a `TensorDict` by batch row** (synthetic tests could not
   see this); fixed to iterate `.keys()`.
3. **In-process batching leaked device memory** (child of the same process held 9.4 GB after one
   4-world batch: Warp's mempool does not return closed-env allocations). Replaced by
   per-batch child processes; verified merge shape `(25, 6, 36)` and full release.
4. **OOM retry matcher** initially missed Warp's `Failed to allocate … bytes` message.

Measured batch costs (development policy, preflight axis, this GPU under ~100 % foreign
utilization): 4 worlds 54 s / ~5.6 GB; 6 worlds 63 s / ~8.1 GB; 8 worlds OOM with 10.4 GB free.
Foreign usage fluctuates 22.0–27.9 GB (two 10.5 GB jobs + spikes).

## Decision

Run at `--batch-worlds 4` in child processes with a 60 s × 240 OOM wait-retry per batch.
Conditions, starts, and N5 noise are keyed by `(table_index, replicate)` and therefore identical
to the unbatched contract; paired base/perturbed worlds always share a batch. Batch size is
recorded in the probe manifest (`batch_worlds`). Estimated wall time ≈ 1,575 batches × ~50 s ≈
22 h. The probe's final SHA is recorded in `reports/newton15_pred/probe/launch_env.txt` and is
written into the manifest (`probe_tool_sha256`).

Deterministic-repeat, cross-condition initial-state, invalid-start, and paired-alive checks are
unchanged and still fail closed in the frozen analyzer. Batching is disclosed as a harness
detail; if the two independent preflight rebuilds disagree the gate is **not tested**.

## Phase-G seal draft (CPU)

- `tools/build_g_eval_panel.py` → `reports/g_segment/panel/{panel.txt,panel_manifest.json}`:
  100 clips, 23.4 min, from 5,046 candidates in `clean.txt` (frames ≥ 250, infeasible ≤ 0.10,
  airborne ≤ 0.10; seed 20260827), disjoint by name and by motion-file SHA-256 from tier_800 /
  pruned / flagged99 / mixed100 / heldout100 / DFRP v1 / 42-unit mechanism panel (0 overlaps).
  `panel.txt` SHA `ec23b7b9…`.
- `plan/PREREGISTRATION_G_SEGMENT.md` (DRAFT, unsealed): G0/G1/G2, learning-progress rank
  (W = 10, λ = 0.01, `difficulty_power` 0), uncertainty fallback, warm-up 400 it, manipulation
  gate (TV ∈ [0.05, 0.15], ≥ 12 entropy-effective units, 0 invalid, saturation check), primary
  endpoint G2 − G1 survival with SESOI +0.05, drop order, pre-seal checklist S1–S7.
- Facts surfaced while drafting: neither LP nor uncertainty rank exists in `climb/` (only
  `conditional_failure_rate^power`); the DFRP v1 panel overlaps tier_800 by 2 clips;
  `run_when_free.sh` lives outside the repo; the 512-env footprint and per-arm GPU-hours are
  unmeasured.

## Keep / discard

Keep: probe harness fixes (unsealed implementation), launch record, panel builder + panel,
seal draft. Discard: every pre-fix launch as a Newton result. The gate verdict is not opened
until `reports/newton15_pred/probe/COMPLETED.json` exists and the frozen analyzer runs.

## 01:13 — probe stopped at preflight batch 6 (harness, not a measurement)

mjlab `auto_reset=False` raises when a terminated world is stepped again. World 3 of batch 6
(unit 23, replicate 0, development policy) fell inside the 25-step window. The sealed contract is
"no reset after termination; paired-alive frames only", so the probe now clears
`env._manual_reset_pending` every step: fallen worlds keep evolving physically, consume no RNG,
receive no new segment, and are masked by `alive`. Verified on the exact failing batch (62 s).
Relaunched 01:2x; new probe SHA in `launch_env.txt`. Batches 1–5 of the earlier run are
discarded (the manifest binds a single run).

## S1–S3 closed on CPU (details in `plan/PREREGISTRATION_G_SEGMENT.md`)

- S1 rank modes implemented and tested (59 tests pass; ruff clean).
- S2: 701 unflagged tier_800 clips screened in full mode (4 m 27 s wall, 8 nice'd workers,
  `n1_knee_id.py --gap 0.06`); 800 sidecars reduced at guard 0; the 99 legacy sidecars reproduce
  exactly; unit table 1,184 units / 368,951 legal starts. **140/701 unflagged clips contain a
  severe window** — the FGAS `assumeunflagged` eligibility set was inexact.
- S3: 2,800 evaluation conditions on the disjoint 100-clip panel.
