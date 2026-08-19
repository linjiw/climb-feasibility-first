# Atlas v2.1 — feasibility features: result against `PREREGISTRATION_ATLAS_v21.md` (2026-08-18)

Feasibility screen (`tools/screen_feasibility.sh`, brief mode of `n1_knee_id.py`, gap 6 cm) over
tier_mixed100 + heldout100 + tier_800 = 979 clips, ~1 s per clip → `reports/feasibility_e3/feasibility.csv`.
Analysis `tools/analyze_atlas_v21.py` → `reports/N_atlas_v21.json`.

| pre-registered test | prediction | result | verdict |
|---|---|---|---|
| F1 within-bank LOO fit (training tier, uniform-s1) | +feasibility lifts LOO ρ ≥ +0.05; #44 residual rank > 60 | fixed-start 0.471 → 0.449, random-start 0.508 → 0.515 (random-3 baseline p95 0.507 / 0.525); #44 rank 43 → 30, 14 → 19 | **not met** — yet `infeasible_frac` alone correlates with training-tier difficulty at ρ +0.50 / +0.54; on 100 clips it is collinear with the intrinsic set (support margin, clearance) |
| F2 cross-policy transfer (held-out, A3 protocol) | adaptive→uniform 0.567 → ≥ 0.597 with permutation p < 0.05, same direction on the other pairs | **adaptive→uniform 0.567 → 0.609 (p = 0.010)**; uniform→adaptive 0.579 → 0.616 (p = 0.030); grounded→uniform 0.544 → 0.580 (p = 0.045); grounded→adaptive 0.586 → 0.633 (p = 0.015); →grounded pairs +0.015/+0.018 (n.s.); all six positive | **met** — the first feature addition that lifts transfer beyond a noise-feature baseline; direct ρ(held-out difficulty, infeasible_frac) = +0.37 / +0.48 / +0.50 (uniform / adaptive / grounded) |
| F3 residual anatomy | ρ(|resid|, infeasible) → ~0; ρ(|resid|, kNN) stays ≥ 0.45 | ρ(|resid|, infeasible) 0.30 → 0.28 / 0.34 → 0.34; ρ(|resid|, kNN) 0.61 → 0.60 / 0.54 → 0.50 | **half met** — support keeps explaining the misses; feasibility residual does not vanish (the linear model does not absorb it) |

Reading: feasibility is real, transferable signal — it survives the change of policy where support
(N2) could not — but at 100 training clips it does not add to a within-bank ridge that already has
support-margin and clearance features. The honest summary: *feasibility × support × intrinsic* is the
right decomposition; feasibility is now measured; its within-bank redundancy with the atlas's contact
proxies is expected (they were its shadows), and the transfer lift is the evidence that it is the
underlying variable.

## Step 2b — campaign endpoints on feasible-only clips (robustness companion; sealed numbers stand)

29 of the 100 held-out clips carry > 10 % infeasible frames. Held-out survival at 4000 iterations
(seed means):

| arm | all 100 (sealed) | feasible-only (71) | infeasible-only (29) |
|---|---:|---:|---:|
| uniform | 0.810 | 0.834 | 0.750 |
| adaptive | 0.780 | 0.811 | 0.705 |
| grounded | 0.825 | 0.859 | 0.741 |

Ordering unchanged (grounded ≥ uniform > adaptive). Grounded's endpoint edge over uniform is +0.025 on
feasible clips and −0.009 on infeasible ones: the curriculum's benefit lives where a policy *can*
succeed; nothing helps a clip that asks the robot to hover. The "0.810 ceiling" is 0.834 on feasible
clips. Caveat carried from the pre-registration: `infeasible_frac` also flags genuine take-off frames of
jumps/skips (feet > 6 cm up while decelerating) — the full-bank prevalence (running, `reports/feasibility_all/`)
reports the share per category so that this ambiguity is quantified rather than assumed away.

## Full-bank prevalence (advisor 2c) — 10,705 clips, `reports/feasibility_all/prevalence_report.txt`

| category | n | > 10 % infeasible frames | > 25 % | duration share flagged |
|---|---:|---:|---:|---:|
| dynamic | 804 | 58.6 % | 32.6 % | 54.5 % |
| ground | 175 | 39.4 % | 18.3 % | 44.1 % |
| locomotion | 5591 | 24.5 % | 17.4 % | 31.2 % |
| quiet | 4135 | 12.9 % | 7.5 % | 19.8 % |
| **all** | **10705** | **22.8 %** | 14.8 % | 27.4 % |

By source: CNRS 100 %, Transitions 90 %, HUMAN4D 55 %, ACCAD 42 %, CMU 40 %, BMLhandball 27 %,
Eyes_Japan 23 %, BMLmovi 22 %, KIT 17 %, DFaust 19 %, GRAB 0.1 %, TCD 1.6 %. **Roughly a fifth to a
quarter of a standard large-scale retargeted bank asks the robot for support that no available
contact can provide for more than a tenth of the clip** — with the caveat, pre-registered, that
genuine flight (jumps, running with real aerial phases) contributes to the dynamic category's rate;
the ground category's 39 % cannot be explained that way and is the #44 family writ large. The
per-source spread (0.1 %–100 %) says this is a property of the retargeting/source pipeline, not of
motion difficulty. This is dramatic enough to justify the released-tool + upstream-note path
(same pattern as mjlab #1153 / whole_body_tracking #73): the screen is one CPU-second per clip and
catches what kinematic QC cannot.
