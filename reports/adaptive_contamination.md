# Adaptive-sampling contamination: does infeasible reference reach the optimizer?

Bank `bank/tiers/tier_mixed100.txt`: 100 clips, 25 flagged at infeasible_frac > 0.1 (25 %). Mean infeasible_frac over all clips 0.0606.

## 0. Bottom line

- **MEASURED, no model.** A failure-adaptive clip sampler puts demonstrably more mass on screen-flagged references than a uniform one: the adaptive arm's top-1 clip ALONE carries more flagged mass than the uniform arm's entire curriculum (25 % exactly). Same for the floor-repaired arm, by a smaller margin.
- **MEASURED, no model.** The collapse is not diffuse: it lands on ONE clip, the same one in all six runs, in both non-uniform arms -- and that clip is flagged.
- **MODELLED: FAILED.** The sampler fixed point cannot reproduce the logged top-1 mass and entropy from any available per-clip failure-rate source under either weight model. No total is reported. See section 3.
- **The instrumentation, not the analysis, is the bottleneck.** One extra logged scalar (`sum_{c in F} p_c` next to `commands.py:117`) would replace the whole modelling layer with a measurement.

## 1. Measured (no model)

Ambiguity policy for the headline column: `round`. `LB` = time-averaged top-1 mass counted only when the top-1 clip is flagged; a strict lower bound on the total.

| run | mean top-1 mass | mean norm. entropy | eff. clips exp(H) | P(top-1 flagged) | LB flagged mass | LB infeasible-frame share | distinct top-1 clips |
|---|---|---|---|---|---|---|---|
| adaptive-s1 | 0.4980 | 0.3770 | 7.2 | 78.4 % | 38.98 % | 7.00 % | 22 (12 flagged) |
| adaptive-s2 | 0.4882 | 0.3921 | 9.7 | 70.4 % | 39.91 % | 6.49 % | 21 (9 flagged) |
| adaptive-s3 | 0.4793 | 0.4016 | 9.9 | 71.3 % | 36.87 % | 6.72 % | 15 (7 flagged) |
| grounded-s1 | 0.3391 | 0.6137 | 22.5 | 81.5 % | 28.81 % | 4.88 % | 24 (8 flagged) |
| grounded-s2 | 0.3284 | 0.6200 | 23.2 | 72.8 % | 27.32 % | 4.32 % | 30 (15 flagged) |
| grounded-s3 | 0.3599 | 0.5956 | 21.8 | 72.7 % | 27.67 % | 4.39 % | 32 (13 flagged) |
| uniform-s1 | (sentinel 1/n) | (sentinel 1.0) | (sentinel) | (sentinel) | (sentinel) | (sentinel) | (sentinel) |
| uniform-s2 | (sentinel 1/n) | (sentinel 1.0) | (sentinel) | (sentinel) | (sentinel) | (sentinel) | (sentinel) |
| uniform-s3 | (sentinel 1/n) | (sentinel 1.0) | (sentinel) | (sentinel) | (sentinel) | (sentinel) | (sentinel) |
| uniform (ANALYTIC) | 0.0100 | 1.0000 | 100.0 | 25.0 % | 25.00 % (exact total) | 6.06 % (exact total) | n/a |

The uniform arm's logged sampling metrics are hardcoded sentinels (`climb/commands.py:137-141`); its `sampling_top1_bin = 0.5` points at clip index 50, which in this bank IS flagged (`Eyes_Japan_Dataset_kawaguchi_gesture_etc-39-giant_baba-kawaguchi_poses_120_jpos`), so a naive lower bound on the uniform logs returns a spurious 1/n. The uniform row above is analytic, not measured.

### Ambiguity sensitivity (LB flagged mass, %)

| run | round | drop | zero | ambiguous iters |
|---|---|---|---|---|
| adaptive-s1 | 38.98 | 39.34 | 38.79 | 56 |
| adaptive-s2 | 39.91 | 40.48 | 39.78 | 69 |
| adaptive-s3 | 36.87 | 37.25 | 36.78 | 50 |
| grounded-s1 | 28.81 | 29.63 | 28.74 | 120 |
| grounded-s2 | 27.32 | 28.68 | 27.20 | 206 |
| grounded-s3 | 27.67 | 29.08 | 27.50 | 217 |

## 1b. WHICH clips the collapse lands on (measured)

`mass_share` = time-averaged top-1 mass attributable to that clip. Pooled over seeds within an arm.

| arm | clip idx | clip | infeasible_frac | flagged | occupancy | mass share |
|---|---|---|---|---|---|---|
| adaptive | 44 | `BMLmovi_Subject_64_F_MoSh_Subject_64_F_9_poses_120_jpos` | 0.130 | YES | 34.1 % | 21.92 % |
| adaptive | 65 | `CMU_135_135_02_poses_120_jpos` | 0.288 | YES | 14.7 % | 6.97 % |
| adaptive | 66 | `DFaust_67_50025_50025_one_leg_jump_poses_60_jpos` | 0.000 | no | 6.8 % | 4.15 % |
| adaptive | 95 | `Eyes_Japan_Dataset_hamada_jump-07-rope_double-hamada_poses_120_jpos` | 0.180 | YES | 8.4 % | 3.83 % |
| adaptive | 86 | `Eyes_Japan_Dataset_kawaguchi_turn-05-turn-kawaguchi_poses_120_jpos` | 0.238 | YES | 6.6 % | 3.02 % |
| adaptive | 5 | `KIT_950_Wipe_Head_Horizontal_01_poses_100_jpos` | 0.000 | no | 3.6 % | 2.09 % |
| grounded | 44 | `BMLmovi_Subject_64_F_MoSh_Subject_64_F_9_poses_120_jpos` | 0.130 | YES | 37.1 % | 17.72 % |
| grounded | 95 | `Eyes_Japan_Dataset_hamada_jump-07-rope_double-hamada_poses_120_jpos` | 0.180 | YES | 12.4 % | 4.79 % |
| grounded | 65 | `CMU_135_135_02_poses_120_jpos` | 0.288 | YES | 11.3 % | 3.13 % |
| grounded | 66 | `DFaust_67_50025_50025_one_leg_jump_poses_60_jpos` | 0.000 | no | 7.5 % | 2.99 % |
| grounded | 5 | `KIT_950_Wipe_Head_Horizontal_01_poses_100_jpos` | 0.000 | no | 6.2 % | 1.91 % |
| grounded | 86 | `Eyes_Japan_Dataset_kawaguchi_turn-05-turn-kawaguchi_poses_120_jpos` | 0.238 | YES | 3.5 % | 1.02 % |

- **adaptive**: dominant top-1 clip is index 44 (`BMLmovi_Subject_64_F_MoSh_Subject_64_F_9_poses_120_jpos`, flagged=True); 79.2 % of all top-1 mass sits on flagged clips; per-seed modal clip: {'44': [1, 2, 3]}.
- **grounded**: dominant top-1 clip is index 44 (`BMLmovi_Subject_64_F_MoSh_Subject_64_F_9_poses_120_jpos`, flagged=True); 82.2 % of all top-1 mass sits on flagged clips; per-seed modal clip: {'44': [1, 2, 3]}.

## 1c. Sensitivity: extrapolating the top-1 term to a total (ASSUMED, not measured)

Two named assumptions about the composition of the `1 - top1` residual. Neither is a result; they are here so a reader can see how far the answer can move without a behavioural model.

| run | LB (measured) | +base-rate residual | +self-similar residual |
|---|---|---|---|
| adaptive-s1 | 38.98 % | 51.53 % | 78.37 % |
| adaptive-s2 | 39.91 % | 52.71 % | 81.89 % |
| adaptive-s3 | 36.87 % | 49.89 % | 77.06 % |
| grounded-s1 | 28.81 % | 45.33 % | 85.40 % |
| grounded-s2 | 27.32 % | 44.11 % | 83.72 % |
| grounded-s3 | 27.67 % | 43.67 % | 77.22 % |

**Read this before quoting either column.** The arm ordering is NOT robust to the residual assumption. Measured lower bound: adaptive 38.6 % > grounded 27.9 %. Base-rate residual keeps that ordering (51.4 % vs 44.4 %). Self-similar residual REVERSES it (79.1 % vs 82.1 %), because the grounded arm spreads more mass outside its argmax and its argmax process is, if anything, slightly MORE flagged-selective (P(top-1 flagged) is comparable in both arms). So 'adaptive contaminates more than grounded' is defensible as a statement about CONCENTRATION and about the lower bound; it is NOT established for the total.

## 2. Distribution-free bracket on the TOTAL (still no behavioural model)

Interval of total flagged mass consistent with the logged (top-1 mass, entropy, argmax identity) and the count of flagged clips. Valid for any distribution. Width is the point.

| run | flagged mass lo | hi | infeasible-frame share lo | hi |
|---|---|---|---|---|
| adaptive-s1 | 39.34 % | 88.69 % | 7.07 % | 22.14 % |
| adaptive-s2 | 40.48 % | 89.66 % | 6.59 % | 21.33 % |
| adaptive-s3 | 37.26 % | 87.30 % | 6.81 % | 21.93 % |
| grounded-s1 | 30.15 % | 89.12 % | 5.20 % | 20.03 % |
| grounded-s2 | 29.20 % | 88.89 % | 4.70 % | 19.73 % |
| grounded-s3 | 29.59 % | 85.46 % | 4.77 % | 18.94 % |

## 3. Modelled total, and its validation gate

*Failure-rate source audit*: campaign per-checkpoint eval CSVs are on a DISJOINT held-out bank; they cannot supply per-clip failure rates for the training clips (0 of 100 clips shared with the training bank, across 81 campaign CSVs).

Gate: |sim-logged|/logged <= 0.15 on mean top-1 mass AND |sim-logged| <= 0.05 on mean normalised entropy, for BOTH arms on the SAME failure-rate source.

| f source | w model | arm | sim top-1 | logged top-1 | sim H | logged H | d top-1 (rel) | d H (abs) | argmax match | modelled flagged mass | pass |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A7_trainbank_uniform_s1 | rate | grounded | 0.8479 | 0.3425 | 0.2337 | 0.6098 | +1.476 | -0.3761 | no (sim 65 vs logged 44) | 90.6 % | FAIL |
| A7_trainbank_uniform_s1 | rate | adaptive | 0.4630 | 0.4885 | 0.6506 | 0.3902 | -0.052 | +0.2603 | no (sim 65 vs logged 44) | 66.3 % | FAIL |
| A7_trainbank_uniform_s1 | flux | grounded | 0.8491 | 0.3425 | 0.2193 | 0.6098 | +1.479 | -0.3905 | no (sim 78 vs logged 44) | 3.0 % | FAIL |
| A7_trainbank_uniform_s1 | flux | adaptive | 0.5008 | 0.4885 | 0.5862 | 0.3902 | +0.025 | +0.1960 | no (sim 78 vs logged 44) | 10.4 % | FAIL |
| eval_mixed100_uniform_s1 | rate | grounded | 0.7281 | 0.3425 | 0.3831 | 0.6098 | +1.126 | -0.2267 | no (sim 28 vs logged 44) | 4.9 % | FAIL |
| eval_mixed100_uniform_s1 | rate | adaptive | 0.4769 | 0.4885 | 0.6436 | 0.3902 | -0.024 | +0.2533 | no (sim 28 vs logged 44) | 9.5 % | FAIL |
| eval_mixed100_uniform_s1 | flux | grounded | 0.6379 | 0.3425 | 0.4421 | 0.6098 | +0.863 | -0.1677 | no (sim 16 vs logged 44) | 4.7 % | FAIL |
| eval_mixed100_uniform_s1 | flux | adaptive | 0.4951 | 0.4885 | 0.5728 | 0.3902 | +0.014 | +0.1826 | no (sim 16 vs logged 44) | 6.7 % | FAIL |
| eval_tier_mixed100_fixed | rate | grounded | 0.0300 | 0.3425 | 0.8199 | 0.6098 | -0.912 | +0.2101 | no (sim 5 vs logged 44) | 47.3 % | FAIL |
| eval_tier_mixed100_fixed | rate | adaptive | 0.0333 | 0.4885 | 0.7386 | 0.3902 | -0.932 | +0.3484 | no (sim 5 vs logged 44) | 50.0 % | FAIL |
| eval_tier_mixed100_fixed | flux | grounded | 0.8675 | 0.3425 | 0.2117 | 0.6098 | +1.533 | -0.3981 | no (sim 85 vs logged 44) | 90.7 % | FAIL |
| eval_tier_mixed100_fixed | flux | adaptive | 0.5006 | 0.4885 | 0.6292 | 0.3902 | +0.025 | +0.2389 | no (sim 85 vs logged 44) | 64.9 % | FAIL |
| eval_tier_mixed100_rand | rate | grounded | 0.2661 | 0.3425 | 0.4825 | 0.6098 | -0.223 | -0.1273 | no (sim 5 vs logged 44) | 60.5 % | FAIL |
| eval_tier_mixed100_rand | rate | adaptive | 0.3333 | 0.4885 | 0.2386 | 0.3902 | -0.318 | -0.1516 | no (sim 5 vs logged 44) | 66.7 % | FAIL |
| eval_tier_mixed100_rand | flux | grounded | 0.8792 | 0.3425 | 0.1981 | 0.6098 | +1.567 | -0.4117 | no (sim 72 vs logged 44) | 3.2 % | FAIL |
| eval_tier_mixed100_rand | flux | adaptive | 0.4759 | 0.4885 | 0.6632 | 0.3902 | -0.026 | +0.2729 | no (sim 72 vs logged 44) | 14.0 % | FAIL |

Cells: 8 = (failure source) x (weight model); 0 pass. The MODELLED adaptive flagged mass spans a factor 9.9 across cells -- the modelled total is not identified by the data available, whatever the gate says.

The grounded arm has **zero** free parameters (the EMA scale `k` cancels at `commands.py:97`), so its row is a pure prediction with nothing to tune. The adaptive arm has one (`k`), fitted to the logged top-1 mass, leaving entropy as the out-of-sample test.

**Gate verdict: FAIL.** SIMULATION FAILED -- no modelled total is reported; only the measured lower bound, the analytic uniform arm and the distribution-free bracket stand as results

## 4. How much of grounded's reduction is mechanical?

Both arms are `p = lam*u + (1-lam)/n`; grounded pins `lam = 0.9`, adaptive gets `lam = S/(S+eps)` with S the failure-count EMA sum. Holding `u` fixed at the adaptive arm's value predicts grounded's top-1 mass from shrinkage alone.

| lam(adaptive) | u_max implied | grounded top-1 predicted | observed | mechanical share of the reduction |
|---|---|---|---|---|
| 1.000 | 0.4885 | 0.4406 | 0.3425 | 32.8 % |
| 0.999 | 0.4890 | 0.4411 | 0.3425 | 32.5 % |
| 0.990 | 0.4933 | 0.4450 | 0.3425 | 29.8 % |
| 0.980 | 0.4982 | 0.4494 | 0.3425 | 26.7 % |
