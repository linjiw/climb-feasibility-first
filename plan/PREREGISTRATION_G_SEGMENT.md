# Pre-registration (DRAFT) — Phase G: one causal test of segment-native allocation

**Status:** DRAFT, **unsealed**. Written 2026-08-27 on CPU while the Newton N-c probe runs.
Target seal date **2026-09-10**; nothing in this document authorizes a training run until the
seal hash exists in `plan/G_SEGMENT_FREEZE.sha256` and every item in §9 is closed.
**Role:** the Phase-G seal called for in `fable.md` §3/§8.3. It covers a one-seed wiring
screen and a three-seed confirmation of three arms. G3 (Newton fragility-weighted sampling)
is **not** part of this document; it is eligible only if the sealed N-c gate
(`plan/PREREGISTRATION_NEWTON_PRED.md`) passes on valid data, and then only under a separate
seal.

## 1. Question and why it is the one worth GPU

Every prior intervention arm in this project either changed nothing the policy could convert
(E-HYG), failed its wiring gate (FGAS soft), moved the reference rather than the policy (N7), or
was uniform wearing an adaptive label (segment-v2 pilot, TV 0.014). No arm has yet tested
**whether adaptive allocation over an exact feasible support helps**, because no adaptive arm
has passed a manipulation check. This document tests exactly that, with the manipulation check
sealed *before* the endpoint and evaluated *before* the endpoint is opened.

Two contrasts, in priority order:

| contrast | meaning | status if positive | status if null with gate passed |
|---|---|---|---|
| **G2 − G1** (primary) | adaptive allocation over identical exact support | first positive intervention result | "allocation does not help once hygiene is exact" — publishable as a clean statement |
| G1 − G0 (secondary) | exact segment hygiene vs unmasked grounded starts | scale test of the segment-curation duration claim | consistent with E-HYG's sealed null; reported as such |

## 2. Arms

| arm | support | sampler | invariants |
|---|---|---|---|
| G0 | `tier_800` (800 clips, sealed `87cbeb8e…`), unmasked grounded starts, normalise-then-mix (ε-fix, mjlab #1153) | deployment prior (uniform over clip duration) | **fresh** training run; the old grounded checkpoint is not reused |
| G1 | exact feasible 50-step units built from `tier_800` guard-0 sidecars (`reports/segments_v2_tier800_guard0/`) with `tools/build_segment_unit_table.py` | `segment_sampling_mode="uniform"` over the unit table's deployment mass | exact support mask; explicit truncation; zero invalid starts |
| G2 | identical unit table to G1 (same file hash) | `segment_sampling_mode="adaptive"` with the **learning-progress rank** of §3 | exploration floor ρ = 0.10; unit cap 0.05; clip cap 0.25; stable unit attribution |

All arms: 4,000 iterations, 512 envs, identical PPO configuration, identical environment seed
per training seed, failure penalty as in the segment-v2 pilot (−10). Seeds for confirmation:
three, fixed at seal time. The wiring screen is seed 1 only.

The unit table used by G1/G2 is built: `reports/g_segment/unit_table.json` — 800 clips,
1,841 source units, **1,184 admissible 50-step units, 368,951 legal starts** (657 short units
discarded); file SHA-256 `a98c48541fbc4aa4627d9b24c5a08e9e67f0d6bc9bb94103da57313b94766739`, payload SHA-256
`a52a668e5570c24e01a1af821164cbd19a38a3cd9007f245f78494ce11af9606`. Its sidecars
(`reports/g_segment/sidecars_guard0/`, 800 files) were reduced by `tools/screen_segments.py`
(SHA-256 `993c448af3185f955bea7f7718c1849837b7d9957366bbf3d8fcd618f208915b`) at guard 0 s / symmetric / min-seg 0 / bin 50 / severe / real model from
full-mode per-frame screens: the 99 flagged clips' existing screens
(`reports/segments_tier800/full/`) and **701 new full-mode screens of the unflagged clips**
(`reports/g_segment/screen_full/`, `n1_knee_id.py --gap 0.06`, μ 0.6). The 99 legacy sidecars
reproduce with zero field mismatches. **Finding:** 140 of the 701 unflagged clips contain at
least one severe window at guard 0 — the FGAS-era `tier_800_assumeunflagged_guard0_bin50`
eligibility (which treated unflagged clips as fully feasible) was not exact. G1/G2 use the exact
table; this is disclosed here so the G1 − G0 contrast is read as *exact* hygiene. The eight-clip N7 overlap must not recur: the evaluation panel of §5 is
already hash-verified disjoint from `tier_800` and every other list an arm can see.

## 3. The G2 rank (must be named exactly, because this is what sank every earlier arm)

**Retired:** conditional failure rate as the sole rank. It saturates near 1 on an exact support
(pilot: 0.014 TV from uniform) and rewards unlearnable units.

**Primary rank — learning progress (LP).** The sampler already maintains a fixed-clock,
Beta-smoothed conditional success estimate per unit, `s_u(k)`, at sampler clock `k`
(`climb/segment_curriculum.py::conditional_failure_rate`, prior 0.5 / strength 2). Define, with
window `W = 10` sampler clock ticks,

    LP_u(k) = | s_u(k) − s_u(k − W) |            (absolute learning progress, Matiisen et al. 2017 / ALP-GMM form)

and the focus term `focus_u ∝ base_u · (LP_u + λ)` with `λ = 0.01` so that a unit with zero
measured progress keeps a nonzero focus share. `difficulty_power` is **0** in G2 (the failure
rate enters only through `s_u`, never as a multiplicative rank). Exploration ρ = 0.10 mixes the
deployment prior back in; the unit/clip caps are enforced exactly as in
`_apply_probability_caps`. During the first `W` ticks `LP_u` is undefined and the sampler is
uniform over the exact support (this is the warm-up of §4).

**Pre-declared fallback rank — conditional uncertainty.** If, and only if, the wiring screen
fails the manipulation gate with the LP rank, the screen is repeated once with
`focus_u ∝ base_u · s_u (1 − s_u)` (Bernoulli variance of the conditional success estimate),
same floor and caps. A second gate failure ends Phase G's adaptive arm as **not tested** and
the confirmation runs G0/G1 only.

No other rank, power, window, floor, or cap is admissible after outcomes exist.

**Implementation status (2026-08-27):** both ranks are implemented as
`SegmentSampler(rank="learning_progress" | "uncertainty", progress_window=10, progress_floor=0.01)`
in `climb/segment_runtime.py` (SHA-256 `2b2631e2fffdebb70eac8d885daca4689283e52c0674ddfcd79d29dc0591e50f`), plumbed through
`SegmentNativeMotionCommandCfg.segment_rank / segment_progress_window / segment_progress_floor`
in `climb/segment_command.py` (SHA-256 `89b56c009fdd86d2a327e9ce69d99101f960291453b8bf70c42ee3fae6dbcfeb`). `difficulty_power ≠ 0` with a non-failure rank
is a launch error. The success-rate ring buffer round-trips through `state_dict` and the
sampler-equivalent resume test covers it (`tests/test_segment_runtime.py`, 10 tests; full
suite 59). The ledger now also records `rank` and `rank_saturation_fraction` (gate item 4).
The default rank remains `failure`, so the pilot's behaviour is unchanged.

## 4. Manipulation gate — sealed with the endpoint, evaluated before it

Warm-up = the first 400 of 4,000 iterations (10 %; ≥ `W` sampler ticks under the pilot's
update cadence). Over every sampler ledger checkpoint (`model_N_segment.json`) after warm-up, the
G2 arm must satisfy **all** of:

1. mean `sampling_adaptation_total_variation` (TV between G2's realized unit distribution and
   the G1 uniform-over-support distribution) **∈ [0.05, 0.15]**;
2. entropy-effective unit count **≥ 12** at every post-warm-up checkpoint, and top-1 unit
   probability ≤ 0.05 by construction (a cap violation is a launch error, not a soft fail);
3. realized invalid frames **= 0** and late rejected-start mass **= 0** (exact support makes
   both trivially checkable; a nonzero value is a wiring bug);
4. conditional-rate saturation check: fewer than 90 % of admissible units have `s_u` outside
   (0.05, 0.95) at the final checkpoint — otherwise the rank had nothing to rank and the arm is
   reported as not tested, exactly like the pilot.

Gate failure on the wiring screen → **stop; do not launch seeds 2–3**; apply the §3 fallback
once; re-screen. Gate failure is reported as **not tested**, never as a null.

G1 and G0 have their own trivial checks: G1 TV from its declared uniform distribution < 0.01;
G0 realized clip exposure matches the deployment prior within 0.02 TV.

## 5. Evaluation

- Evaluator: `tools/eval_paired_v2.py` (paired v2; frozen condition manifest; auto-reset off
  for terminal reads; joint-noise seed fixed). The condition manifest is built once before
  sealing from the panel below and bound by hash; `eval_paired_v2` validates it byte-exactly.
- Panel: `reports/g_segment/panel/panel.txt` — 100 clips, 23.4 min, drawn outcome-blind from
  `bank/tiers/clean.txt` with `frames ≥ 250`, `infeasible_frac ≤ 0.10`, `airborne_frac ≤ 0.10`
  (NumPy seed 20260827); verified disjoint **by name and by motion-file SHA-256** from
  `tier_800`, `tier_800_pruned`, `tier_800_flagged99`, `tier_mixed100`, `heldout100`, the DFRP
  v1 panel, and the 42-unit mechanism panel (0 overlaps on every list).
  `panel.txt` SHA-256 `ec23b7b959dbb6bd05015f5821c99ac9d5a70dd966ef5448443d060b4a3127fe`;
  manifest `reports/g_segment/panel/panel_manifest.json`; builder
  `tools/build_g_eval_panel.py` SHA-256
  `dd36fedcdfbb125f6396cf01d29d3b1ecf381d1aa9d0351d87d928549c603627`.
- Conditions: 7 phases × 4 replicates × 3.0 s windows per clip (the eval-v2 pilot design),
  same for every arm and seed. Built: `reports/g_segment/eval_conditions.json` — **2,800
  conditions, all full-window**, environment seed 20260910, joint-noise seed 20260911, joint
  noise 0.05, nconmax 70; SHA-256 `74b723d42c4050eea9f4ea7ff87d22771e8e32c5155b56829900bf4cb3744a4e`.
- **Primary endpoint:** feasible-disjoint survival (fraction of conditions surviving the full
  window) at iteration 3,999, contrast G2 − G1, three seeds, seed × clip hierarchical
  bootstrap (10,000 draws, NumPy seed 20260910), 95 % percentile interval.
- **Secondary:** AULC of survival over checkpoints {1000, 2000, 3000, 3999}; G1 − G0 survival.
- **Common-survivor quality noninferiority** (G2 vs G1 on conditions both survive): MPKPE,
  anchor-orientation error, mechanical work; margin 10 % relative; the **CI lower bound**, not
  the point, must clear the margin.
- Any repaired-reference contrast (G-2 later, not here) reports the N7 2×2 decomposition
  (policy / reference / interaction) plus fidelity diagnostics.

## 6. Sealed decision rule (to be frozen verbatim at seal time)

SESOI = **+0.05** survival (the project's standing SESOI).

- **Positive:** G2 − G1 point ≥ +0.05 **and** CI lower bound > 0 **and** noninferiority holds.
- **Sealed null:** CI upper bound < +0.05 with the manipulation gate passed. Reported as
  "allocation does not help once hygiene is exact", which closes G3's motivation regardless of
  N-c.
- **Inconclusive:** anything else with the gate passed; reported with the interval, no
  re-analysis.
- **Not tested:** gate failed on both ranks; G0/G1 results still reported.

No threshold is softened after inspection.

## 7. Budget and drop order (decided now)

The segment-v2 pilot measured ~10k env-steps/s; a 512 × 4,000 arm is ~2.05 M steps × 512 envs
= ~1.05 G env-steps ≈ 29 GPU-h at that rate — **unmeasured for a full arm**. The wiring screen
records realized GPU-hours and peak memory in its sentinel. If three seeds × three arms do not
fit before the Dec 1 freeze, drop in this order: (1) G0 entirely (E-HYG already bounds the
hygiene contrast), (2) seed 3, (3) never the manipulation gate or the panel.

## 8. Non-claims

Not a claim about repaired references (that is G-2), not about Newton (that is N-c/G3), not
about bank-wide curation, not about SONIC. A positive G2 − G1 is a claim about *this* rank on
*this* support; the fallback rank, if used, is named as such.

## 9. Pre-seal checklist (all must be closed before `G_SEGMENT_FREEZE.sha256` is written)

| # | item | done when |
|---|---|---|
| S1 ✅ | LP rank + uncertainty fallback implemented in `climb/segment_runtime.py`, plumbed in `segment_command.py`; `W`, `λ`, and resume equivalence tested (59 tests) | SHAs in §3 |
| S2 ✅ | `tier_800` guard-0 exact unit table built from full-mode screens of all 800 clips | `reports/g_segment/unit_table.json`, SHAs in §2 |
| S3 ✅ | condition manifest for the 100-clip panel built with `eval_paired_v2.build_conditions` | `reports/g_segment/eval_conditions.json`, SHA in §5 |
| S4 ✅ (draft) | frozen analyzer `tools/analyze_g_segment.py`: gate first (TV band, entropy, invalid/censored = 0, saturation < 0.90; G1 TV < 0.01), seed×clip hierarchical bootstrap for G2 − G1 survival / AULC / G1 − G0, common-survivor relative noninferiority (MPKPE, anchor orientation, work; CI upper < +10 %), §6 verdict; `--synthetic` passes positive / null / inconclusive / gate-fail; fails closed without a post-warm-up ledger or on a condition-set mismatch. SHA-256 `a9c2c5466bf3d8992882ce04ead016695d4df0c47d2ff2d991a62b2e60314016` (re-hash at seal; the G0 exposure check is reported, not gated, because G0 uses the clip-level command) | `reports/g_segment/SYNTHETIC.json` |
| S5 | `run_when_free.sh` moved into `tools/` (today it lives only in a job scratch directory) and the memory need set from a measured 512-env footprint | script SHA recorded |
| S6 | seeds fixed; drop order copied verbatim into `plan/STATUS.md` | — |
| S7 | G3 pointer: `PARKING.md` entry updated with the N-c verdict when it lands | — |

Seal: `sha256sum plan/PREREGISTRATION_G_SEGMENT.md tools/analyze_g_segment.py
tools/build_g_eval_panel.py reports/g_segment/panel/panel.txt reports/g_segment/unit_table.json
reports/g_segment/eval_conditions.json climb/segment_curriculum.py climb/segment_runtime.py
> plan/G_SEGMENT_FREEZE.sha256`, then append the document hash to `plan/SEALS_2026-08-19.sha256`.
