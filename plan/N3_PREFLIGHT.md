# N3 pre-flight (TASK n3-preflight, v6 P1) — frozen 2026-08-20, before any N3 outcome exists

*Status labels used: measured (tables), sealed 🕐 (all N3 outcomes). Artifact paths touched:
`tools/analyze_n3.py`, `reports/N3_ground16_preflight.csv`. UNVERIFIED: none.*

## 1. Frozen analysis script

`tools/analyze_n3.py` — sha256 **`b118b2d3357745aded59be0ccf5c46ca54b42f10ba41982fd03bc3dea37a39d0`**.
Implements the sealed criteria verbatim (seal `af1b7c9f`, D1 strata `a93a87a0`): E1 keystone
(#44 kneel/crawl-phase = offsets {2,3,4,6} s, ≥ 0.25 in *both* aug-uniform seeds), E4 specificity
(random16 arm < 0.10), E2 no-regression (easy ≥ 0.95; heldout ±0.03 all-clips, feasible-only
co-reported), E3 interaction (adaptive-on-augmented top-1 < 0.5 after iter 2000), E5 reported,
descent offsets {0,1} s reported separately with the ≤ 0.25 prediction flag. Decision =
E1 ∧ E4 only. **This file must not change after the N3 chain starts; any change requires a dated
addendum here and a re-hash.**

## 2. Synthetic dry-run (run 2026-08-20; no real outcome files exist or were touched)

Four fabricated branches, all deciding as sealed:

| branch | aug s1/s2 kneel | rand16 | verdict |
|---|---|---|---|
| A confirm | 0.40 / 0.35 | 0.05 | causal = **True** ✓ |
| B dose-null | 0.10 / 0.05 | 0.05 | False ✓ |
| C one-seed | 0.40 / 0.15 | 0.05 | False (both seeds required) ✓ |
| D non-specific | 0.40 / 0.35 | 0.30 | False (E4 fails) ✓ |

## 3. refeas + support confirmation for all 16 neighbour clips (`reports/N3_ground16_preflight.csv`)

All 16 pass the sealed inclusion screen (full-mode `infeasible_frac` ≤ 0.10; range 0.034–0.097;
source `reports/N3_candidate_feasibility.json`). Support vs tier_mixed100: kNN distance 2.06–2.88
z-units (bank median NN spacing 1.16 — every neighbour sits in genuinely thin support),
duration-weighted density 0.008–0.024, total added duration 197 s (≈ 13.6 % of the 1,260 s bank).

## 4. Missing baselines to measure BEFORE unblinding (flagged in the seal)

The stratified-start baseline exists only for uniform-mixed100-**s1**
(`reports/N3_baseline_uniform-s1_strat.csv`: #44 kneel-phase 0.000). Seeds s2/s3 must be measured
with the identical protocol *before* any augmented arm is analysed (two ~10-min GPU evals; queue
them at the head of the Sept-15 block, before the training chain's own evals are read).

## 5. Decision tree for the pre-listed null follow-ups (verbatim classes from the seal's precondition)

```
run analyze_n3.py (frozen) on the completed arms
│
├─ E1 ∧ E4          → coverage causal for the feasible phase.
│                      Report; seal N7 (repair) with numbers from this readout; no bank expansion.
│
├─ ¬E1 ∧ E5 holds   → family learnable in-training but not generalising to #44 at this dose.
│   (ground16 members improve)   → Null follow-up 1: EXPOSURE MASS — grounded sampler with the
│                                  family's floor raised (targeted mixing), one seed, same eval.
│                                  Prediction: E1 recovers iff dose was the issue.
│
├─ ¬E1 ∧ ¬E5        → family not learnable at 4k iters for this policy class.
│                      → Null follow-up 2: START-PHASE CURRICULUM — train with episode starts
│                        stratified inside the feasible phase of family clips, one seed.
│                      → If that also fails: Null follow-up 3: REWARD TAX audit on the ground16
│                        set via the oracle's per-term rates (r_self_collisions, r_joint_limit;
│                        already logged in reports/N3_env_admits_playback_g1.0.csv) BEFORE
│                        touching any weight. Note P-TAX already found no difficulty-level tax
│                        effect; this branch examines the *learning*-level effect only.
│
├─ E1 ∧ ¬E4         → effect is not composition-specific (any 16 clips help).
│                      Report as such; the coverage story weakens to "data volume";
│                      no rescue analysis is authorised.
│
└─ E2 fails anywhere → STOP before interpreting E1/E4: augmentation regressed the base
                       distribution; check the frozen config hash first (resume-safety class).
```

Nothing analytic is decided after outcomes exist: the script, thresholds, strata, baselines list,
and this tree are all fixed now.
