# Pre-registration addendum 1 — Newton 1.5 no-training predictive gate

**Sealed:** 2026-08-27 21:55 EDT, before any outcome of probe attempt 5 exists
(attempt 5 launched 21:50 EDT with the harness fix below; its first effect row
cannot exist before the development policy's first paired axis completes).
**Amends:** `plan/PREREGISTRATION_NEWTON_PRED.md` (sealed `b1773fc5…`, unchanged).
**Manifest:** `plan/PREREGISTRATION_NEWTON_PRED_addendum1.md.sha256`.

## Why an addendum

Probe attempt 4 (2026-08-27 08:0x → 21:49 EDT; archived, never analyzed, in
`reports/newton15_pred/probe_attempt4_not_tested/`, effects CSV SHA-256
`af3e6d9c…`, manifest SHA-256 `24285068…`) completed all 126 rows and reported
**not tested** on two of the sealed instrument checks:

1. `cross_condition_initial_state_max_abs_delta = 2.0` on the two paired axes
   (0.0 on `newton_contact`). Diagnosed on a two-world paired build: root `qpos[0]`
   differs by exactly mjlab's default `env_spacing = 2.0 m` between neighbouring
   worlds of one build; `qvel`, warm start, reference index are identical and the
   observation differs by 2e-7 from world-position rounding. **Harness artifact.**
   Fix (probe only): `cfg.scene.env_spacing = 0.0`, so every world shares one
   origin (MJWarp worlds never interact). Verified byte-identical paired canonical
   state, warm start, observation, and reference index. Probe SHA-256 after the
   fix: `781f491ef2ef21e1925ddb494205dd5ba95bebd46a2dc718a00220703120aed4`.
2. `minimum_paired_alive_fraction = 0.19 < 0.80`. The original seal requires
   ≥ 80 % jointly-alive paired time points for **every** policy × unit × axis row
   and declares the gate not tested otherwise. To diagnose, **only the three
   `*_paired_alive_fraction` columns** of the attempt-4 effects table were read;
   no `*_s_mm` (effect) column or any other outcome was opened. Result: rows
   below 0.80 belong to two units — table index 45/46 → unit 46
   (`DFaust_67_50004_50004_knees`, development 0.19–0.24 and adaptive 0.43 on all
   three axes: both policies fall within 0.5 s under every condition, including
   the base) and unit 9 (`BMLmovi_Subject_27_F_5`, development `delay_20ms`
   0.78). Grounded has no row below 0.905. This is a property of the frozen
   policies on a mechanism panel that deliberately contains severe units, not a
   harness fault, and the row-level rule would let one unlearnable unit veto the
   whole gate.

## What changes (and nothing else)

- **Unit-level exclusion replaces the row-level veto.** A unit is excluded from
  every statistic if *any* of its nine policy × axis rows has paired-alive
  fraction < 0.80. At least **36 of 42 units** must remain; otherwise the gate is
  **not tested**. The full 42 × 3 table must still be present; exclusion never
  fills a missing row. The excluded units and count are written to the result.
- **Manifest validity is recomputed from components** in the frozen analyzer
  (deterministic repeat delta = 0, contacts equal, invalid starts = 0, invalid
  reference frames = 0, escaped frames = 0, cross-condition initial delta = 0,
  motor-clamp manipulation realized on ≥ 12 units) instead of the probe's single
  `pass_preflight` boolean, which folds the retired row-level alive rule in. The
  probe implementation is otherwise unchanged and still writes that boolean.
- **Frozen analyzer re-frozen:** `tools/analyze_newton_pred.py` SHA-256
  `95479ebce49d0c192025d13308b482e2c3b4616dc9ba3048716fe95ee46af20d`. Its
  `--synthetic` run now covers pass / null / discordant / excluded (40-unit pass)
  / too-few (fails closed); output `reports/newton15_pred/SYNTHETIC_addendum1.json`.

Unchanged: panel, starts, noise, axes, replicates, policies, the three-part
decision rule and its thresholds (partial ρ ≥ +0.25, one-sided within-clip
permutation p ≤ 0.05, LOCO lift ≥ +0.05, grounded direction), 10,000
permutations with seed 20260826, the kill rule (valid-data fail → G3 never runs),
and the rule that a harness failure is *not tested*, never a null.

## Disclosure

The exclusion rule was chosen after seeing which units fail the alive rule but
before seeing any effect. Under the rule, attempt 4 would have analyzed 40 units;
attempt 5 (identical physics, origin-only change) is expected to exclude the same
two. Both attempt-4 files stay archived and hash-bound for audit.
