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

The unit table used by G1/G2 will be built once, before sealing, and bound here by file and
payload SHA-256 (§9). The eight-clip N7 overlap must not recur: the evaluation panel of §5 is
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

**Implementation status:** neither rank exists in `climb/` today (only
`conditional_failure_rate^difficulty_power`). Both must be implemented, unit-tested (including
the pilot's sampler-equivalent resume property), and hash-bound here **before** sealing (§9).

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
  same for every arm and seed.
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
| S1 | LP rank + uncertainty fallback implemented in `climb/segment_curriculum.py` / `segment_runtime.py`, with `W`, `λ`, and resume equivalence tested | tests pass; SHAs recorded here |
| S2 | `tier_800` guard-0 unit table built; file + payload SHA recorded; admissible unit count and legal-start count recorded | `reports/g_segment/unit_table.json` |
| S3 | condition manifest for the 100-clip panel built with `eval_paired_v2.build_conditions`; SHA recorded | `reports/g_segment/eval_conditions.json` |
| S4 | frozen analyzer `tools/analyze_g_segment.py` with `--synthetic` branches: positive / null / inconclusive / gate-fail (must fail closed without the ledger) | SHA recorded; `reports/g_segment/SYNTHETIC.json` |
| S5 | `run_when_free.sh` moved into `tools/` (today it lives only in a job scratch directory) and the memory need set from a measured 512-env footprint | script SHA recorded |
| S6 | seeds fixed; drop order copied verbatim into `plan/STATUS.md` | — |
| S7 | G3 pointer: `PARKING.md` entry updated with the N-c verdict when it lands | — |

Seal: `sha256sum plan/PREREGISTRATION_G_SEGMENT.md tools/analyze_g_segment.py
tools/build_g_eval_panel.py reports/g_segment/panel/panel.txt reports/g_segment/unit_table.json
reports/g_segment/eval_conditions.json climb/segment_curriculum.py climb/segment_runtime.py
> plan/G_SEGMENT_FREEZE.sha256`, then append the document hash to `plan/SEALS_2026-08-19.sha256`.
