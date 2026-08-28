# Newton 1.5 no-training predictive gate — result

**Date:** 2026-08-28 EDT  
**Protocol:** `plan/PREREGISTRATION_NEWTON_PRED.md` (sealed `b1773fc5…`) + addendum 1
(`plan/PREREGISTRATION_NEWTON_PRED_addendum1.md`, sealed before any attempt-5 outcome).  
**Verdict:** **FAIL on valid data.** Newton remains an analysis instrument. **G3
(fragility-weighted sampling) never runs in this project.**

## Measurement validity (all sealed component checks pass)

Probe attempt 5 (`tools/newton15_pred_probe.py` SHA-256 `781f491e…`, 4-world child-process
batches, `env_spacing = 0`): deterministic-repeat max |Δ| = 0 for every policy, contact sets
equal across independent rebuilds, invalid starts = 0, invalid/escaped reference frames = 0,
cross-condition initial-state max |Δ| = 0, motor clamp realized on 12 / 14 / 13 of 42 units
(development / adaptive / grounded). Under addendum 1, units 9 and 46 (table indices 5, 23)
are excluded for paired-alive < 0.80; **40 units × 3 axes analyzed** (≥ 36 required).

## Sealed statistics (10,000 within-clip permutations, seed 20260826)

| target | partial Spearman ρ | one-sided p | LOCO ridge lift (aug − base) | lift p | rule |
|---|---:|---:|---:|---:|---|
| **adaptive (primary)** | **+0.141** | 0.158 | **−0.006** (0.561 → 0.555) | 0.640 | needs ρ ≥ +0.25, p ≤ 0.05, lift ≥ +0.05 → **fail** |
| grounded (directional) | +0.022 | 0.429 | −0.036 (0.588 → 0.552) | 0.898 | needs both > 0 → **fail** |

Descriptive per-axis raw Spearman (development S vs held-out S, 40 units): delay +0.42 / +0.53,
motor clamp +0.27 / −0.21, Newton-contact −0.03 / −0.08 (adaptive / grounded). The delay axis
carries whatever shared signal exists; the contact-generator axis carries none, and the
reference-only controls already reach ρ ≈ 0.56–0.59 on their own.

## Reading

A three-axis Newton fragility vector measured on one frozen policy does not predict another
policy's signed degradation beyond the feasibility screen and reference kinematics on this
panel. This is a clean, pre-registered null on valid data, not a harness failure. It closes G3
permanently (kill rule) and demotes Newton to a companion/appendix instrument (the recertified
dual-stack conformance, `plan/NEWTON15_RECERT_RESULT.md`, stands on its own).

## Artifacts

- effects: `reports/newton15_pred/probe/effects.csv` SHA-256 `d863abffb28893a52c870460acb6f4575edb1c78866e7910863e5507bfeff029`
- probe manifest: `reports/newton15_pred/probe/probe_manifest.json` SHA-256 `08ea88e9468bcd1c9ddd6f472be7f10a399852618c247b53956945a8236a24f9`
- result: `reports/newton15_pred/result.json` SHA-256 `ff7e5670658751f4b362ea8a531f51a6f79a2a5b381b3c59837504f268da3670`
- analyzer: `tools/analyze_newton_pred.py` SHA-256 `95479ebc…` (addendum 1)
- attempt 4 (not tested, never analyzed): `reports/newton15_pred/probe_attempt4_not_tested/`
- execution log: `autoresearch/autoresearch-260827-0040/research_log.md`
