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

## 07:48 — attempt 3 stopped on the `newton_contact` axis (harness, not a measurement)

Development preflight, `delay_20ms`, and `motor_clamp_85pct` completed (~6 h, 4-world batches,
zero OOM retries needed). The first `use_mujoco_contacts=False` batch raised
`'NoneType' object has no attribute 'rigid_contact_max'`: with MJWarp collision off, Newton's
`SolverMuJoCo.step` needs a `Contacts` buffer from Newton's own `CollisionPipeline`, and the
pinned S1 wrapper passes `None` because every earlier run (S1, G0, N-b) used MuJoCo-native
contacts. This axis had never executed. Fix (probe only; S1 baseline untouched):
`attach_newton_collision` wraps `solver.step` to run `CollisionPipeline(model,
rigid_contact_max ≥ naconmax, broad_phase="explicit").collide(state_in, buffer)` every substep.
Verified on 4 worlds: all alive under both generators; `error_body_pos` differs by ≤ 0.5 mm at
step 25; contact sets differ (expected). Also added per-(policy, axis) stage caching keyed by
the probe's SHA so a late failure keeps finished stages; the earlier stages were *not* reused
(different probe SHA). Relaunched 08:0x as attempt 4 (`probe_run_attempt3_contact_axis_fail.log`
kept). Two `B023` lint notes on immediately-invoked lambdas are deferred until the run ends.

## 21:50 — attempt 4 completed as NOT TESTED; addendum 1 sealed; attempt 5 launched

Attempt 4 ran all 126 rows (13 h 45 min; zero OOM retries; deterministic repeats and contact
sets exactly equal; motor clamp realized on 12/14/13 units). Two sealed checks failed:
`cross_condition_initial_state_max_abs_delta = 2.0` (mjlab `env_spacing` offsetting paired
worlds' root x — harness; fixed with `env_spacing = 0`, verified byte-identical) and
`minimum_paired_alive_fraction = 0.19` (unit 46 unlearnable for development/adaptive within
0.5 s; unit 9 at 0.78 on one row). Only the alive columns of attempt 4 were read; effects were
not opened; files archived under `probe_attempt4_not_tested/`. Addendum 1
(`plan/PREREGISTRATION_NEWTON_PRED_addendum1.md`) replaces the row-level veto with unit-level
exclusion (≥ 36 units must remain) and re-freezes the analyzer (`95479ebc…`), synthetic
five-branch pass. Attempt 5 launched 21:50 with the spacing fix (probe `781f491e…`).

## 09:43 Aug 28 — attempt 5 complete; sealed verdict FAIL on valid data

Attempt 5 ran uninterrupted 21:50 → 09:43 (13.9 h). A 02:18 note from another session
(`INTERRUPTED.json`, now `INTERRUPTED_stale_external_note.json`) claimed the PIDs were absent;
the monitor stream, log writes, manifest, and `COMPLETED.json` show the run never stopped, and the
narrative edits that note produced in `fable.md`/`STATUS.md`/this log were restored from HEAD.
Component checks: repeat Δ 0, contacts equal, invalid/escaped 0, cross-condition Δ 0 (spacing fix
confirmed), clamp realized 12/14/13. Addendum-1 analyzer (`95479ebc…`, hash verified) excluded
units 9 and 46 as predicted (40 analyzed) and returned **gate FAIL**: adaptive partial ρ +0.141
(p 0.158), LOCO lift −0.006 (p 0.640); grounded ρ +0.022, lift −0.036. Recorded in
`plan/NEWTON_PRED_RESULT.md`, `STATUS.md`, `RESULTS_LOG.md`, `PARKING.md` (G3 killed), fable §9/§10.
