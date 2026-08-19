# N2 — relational atlas v2: support features (2026-08-18)

**Tool:** `tools/analyze_atlas_support.py` → `reports/N2_atlas_support.json`,
`reports/support_features_mixed100.csv`, `reports/support_features_heldout100_wrt_mixed100.csv`,
`reports/support_features_tier_800.csv`.

**Support** of a clip relative to a training bank, in the atlas's 11-D z-scored intrinsic space
(A3's `FEATURES`): `knn_dist` (mean distance to the 5 nearest bank clips, self excluded),
`support_density` (duration-weighted Gaussian kernel mass of the bank around the clip, bandwidth
= median NN spacing of the bank, 1.16 z-units), `category_mass` (duration share of the clip's
rule-based category — ground / dynamic / quiet / locomotion; `flight_phase_frac` was dropped from
the rule because the bank's feet float ~3 cm above the plane and it fires on 80 % of clips — the
same offset N1 found).

Training bank tier_mixed100 by duration: locomotion 62 % (43 clips), quiet 23 % (31), dynamic 12 %
(24), **ground 3.2 % (2 clips)**. Clip #44: knn_dist 2.76 (8th lowest support of 100), density
0.012, category mass 0.032. tier_800 by duration: locomotion 51 %, quiet 44 %, dynamic 1.9 %,
**ground 0.65 % (9 clips)** — the 800 bank has *less* ground-contact share than the 100.

## T1 — do the intrinsic atlas's residuals concentrate on low-support clips? **Yes. Is #44 the extreme point? No.**

Training tier, uniform-s1 policy, LOO ridge on the 11 intrinsic features:

| eval protocol | LOO ρ intrinsic | ρ(|resid|, knn_dist) | ρ(|resid|, log density) | ρ(|resid|, cat mass) | #44 residual rank | #44 support rank |
|---|---:|---:|---:|---:|---:|---:|
| fixed frame-0 start | 0.471 | **+0.605** | **−0.578** | −0.246 | 43 / 100 | 8th lowest |
| random start | 0.508 | **+0.544** | **−0.561** | −0.350 | 14 / 100 | 8th lowest |

The atlas's misses are strongly the low-support clips (isolated "quiet" wipes/stomps, the one-leg
jumps, walk-with-box). #44 is *not* the extreme residual: the intrinsic model already rates it hard
(it lies far from the bank on the ground-contact axis, which is one of the fitted features), so its
difficulty is largely *explained*, and it is 8th (not 1st) in low support. Adding the support
features to the LOO fit does not improve within-policy prediction (0.471 → 0.449; 0.508 → 0.494):
with a single bank, support is a deterministic function of the same intrinsic coordinates.

## T2 — does intrinsic + support lift cross-policy transfer above 0.567? **Not detectably.**

Held-out 100 clips, per-arm difficulty (campaign it3999, seeds averaged), support relative to
tier_mixed100, A3 protocol (fit on one arm's labels, predict another's), with a 200-draw permutation
baseline of three random extra features:

| transfer | intrinsic | + support | random-3 mean (p95) | p |
|---|---:|---:|---:|---:|
| adaptive → uniform | 0.567 | 0.584 | 0.577 (0.601) | 0.24 |
| uniform → adaptive | 0.579 | 0.583 | 0.582 (0.610) | 0.46 |
| grounded → uniform | 0.544 | 0.575 | 0.553 (0.576) | 0.08 |
| uniform → grounded | 0.623 | 0.642 | 0.627 (0.650) | 0.13 |
| adaptive → grounded | 0.637 | 0.655 | 0.642 (0.664) | 0.13 |
| grounded → adaptive | 0.586 | 0.595 | 0.594 (0.622) | 0.37 |

Lifts of +0.00 to +0.03, none beyond what three noise features give. Yet support itself is
predictive of held-out difficulty: ρ(difficulty, knn_dist) = +0.34 / +0.37 / +0.41 for uniform /
adaptive / grounded, ρ(difficulty, log density) = −0.23 to −0.31. Support is real signal that the
intrinsic features already carry — because with one training bank the two are collinear.

## What this means, and the uncontaminated test for E3

Support cannot be separated from intrinsic difficulty using data from a single bank; it becomes a
distinct, testable object only when the bank changes. That is E3. Pre-registered here for E3
(policies trained on tier_800):

- **E3-S1.** For the held-out clips, support recomputed against tier_800 (`support_features_tier_800.csv`
  gives the bank; the held-out support is a one-line recomputation) differs from support against
  tier_mixed100. Prediction: per-clip Δdifficulty (800-policy − 100-policy) correlates negatively
  with Δlog-density (800 − 100): clips that *gain* support get easier. Criterion ρ ≤ −0.25.
- **E3-S2.** Fit intrinsic → difficulty on the 100-bank policies and predict the 800-bank
  policies: the residual of that transfer correlates with Δsupport (ρ ≥ +0.25 with Δknn_dist).
  Intrinsic + support fitted on the 100 bank should transfer to the 800 bank better than intrinsic
  alone by ≥ +0.05 in ρ, beyond a 200-draw noise-feature baseline.
- **E3-S3.** Ground-contact clips are the natural experiment inside this: the 800 bank has *less*
  ground share (0.65 %) than the 100 (3.2 %); prediction: held-out ground clips get *harder* under
  the 800 policy while locomotion clips get easier.
- Category composition of both banks is documented above and is an analysed variable in E3 (N4).
- Every difficulty label in these tests uses the stratified-start protocol (N4), not
  start-offset-averaged survival.

Honest bottom line: N2's directional claim ("misses concentrate on low-support clips") holds
strongly (ρ ≈ 0.55–0.60); the two sharper claims (#44 the extreme point; transfer lift from 0.567)
do not, and cannot on one bank. E3 is the first real test.
