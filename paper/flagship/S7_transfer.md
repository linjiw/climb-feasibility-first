# 7. Difficulty that transfers (complete except the E3 slot)

**The question.** A difficulty atlas is useful only if it describes the *motion*, not one training
run. Two policies rank held-out difficulty at ρ = 0.832 (`reports/A3_atlas_transfer.json`); a
reference-kinematics/dynamics atlas fit on one policy predicted the other at ρ = 0.567–0.579 —
below the pre-registered 0.6 bar (sealed criterion; outcome recorded as a miss). What closes the
gap?

**Support alone does not (sealed prediction, null).** Bank-relative support features (kNN distance
and duration-weighted density in atlas space, category mass) were pre-registered
(`plan/N2_RESULT.md`) with two claims: atlas residuals concentrate on low-support clips — **holds**,
ρ(|resid|, kNN) = +0.60 / +0.54 (exploratory-confirmed on both start protocols) — and transfer
lifts above 0.567 — **null**: +0.00 to +0.03, inside a 200-draw random-feature baseline
(`reports/N2_atlas_support.json`). Diagnosis, stated in advance of E3: with a single training
bank, support is collinear with the intrinsic coordinates; it becomes a distinct object only when
the bank changes. That is E3's sealed test (slot, §8).

**Feasibility does (sealed prediction, met).** Atlas v2.1 added three screen features
(`infeasible_frac`, `airborne_frac`, unsupported impulse per weight), pre-registered
(`plan/PREREGISTRATION_ATLAS_v21.md`, `9b1a2c78…`) with predicted transfer lift ≥ +0.03 at
permutation p < 0.05. Result (`reports/N_atlas_v21.json`, `plan/ATLAS_v21_RESULT.md`):

| transfer (A3 protocol) | intrinsic | + feasibility | random-3 p95 | perm p |
|---|---:|---:|---:|---:|
| adaptive → uniform | 0.567 | **0.609** | 0.602 | **0.010** |
| uniform → adaptive | 0.579 | 0.616 | 0.607 | 0.030 |
| grounded → uniform | 0.544 | 0.580 | 0.577 | 0.045 |
| grounded → adaptive | 0.586 | 0.633 | 0.626 | 0.015 |
| → grounded (2 pairs) | 0.623 / 0.637 | 0.638 / 0.655 | n.s. | 0.24 / 0.16 |

All six pairs move in the predicted direction; four clear the permutation baseline —
**feasibility is the first feature family that transfers across policies**, because it is a
property of the reference on the robot, not of any training run. Direct correlations:
ρ(held-out difficulty, `infeasible_frac`) = +0.37 / +0.48 / +0.50 per arm. The two companion
predictions were **not** met and are reported as sealed misses: within-bank LOO fit did not
improve (F1 — at 100 clips the screen features are collinear with the atlas's contact proxies,
which were their shadows all along), and the residual's correlation with infeasibility did not
vanish under a linear model (F3, half-met: support keeps explaining the misses).

**Where this leaves the decomposition.** Intrinsic features predict within-policy difficulty
(LOO ρ 0.47–0.51 training tier, 0.70+ on the original RQ1 protocol); feasibility adds the
cross-policy component; support is measured, predictive in the raw (ρ up to +0.41), and awaiting
its uncontaminated test. **[E3 SLOT — sealed predictions `2c38845b…`: per-clip Δdifficulty
(800−100) vs Δlog-support ρ ≤ −0.25; all 22 named dynamic held-out clips lose support and are
predicted to get harder; H2b-S support-moderation of the grounded−uniform gap; fills after the
Sept-15+ E3 run.]**
