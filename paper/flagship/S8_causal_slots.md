# 8. Causal tests (slots — structure fixed now, numbers fill on the Sept-15+ schedule)

Everything before this section is observational or mechanistic. Three sealed interventions close
the loop. Each slot states: what was sealed, what would confirm or refute it, when it fills.

## 8.1 N3 — composition causality (keystone) [SLOT]

**Sealed** 2026-08-19-era (`plan/PREREGISTRATION_N3_coverage.md`, `af1b7c9f…`; precondition
`plan/N3_PRECONDITION_env_admits.md`, `3c331e18…` — terminations verified not to fire on the
reference; naive PD-follow shown uninformative; contact-supported dynamics verified). Design:
tier_mixed100 + **ground16** (16 nearest *feasibility-screened* kneel/crawl neighbours) vs
+ **random16**; uniform ×2 seeds (keystone), adaptive ×1, random-control ×1; stratified-start
evaluation.

**Confirms coverage-causality iff** E1: attractor kneel/crawl-phase survival (offsets {2,3,4,6} s)
rises from 0.000 (baseline, `reports/N3_baseline_uniform-s1_strat.csv`) to ≥ 0.25 in both keystone
seeds, **and** E4: the random16 control stays < 0.10. E2 (no regression on easy/held-out), E3
(the adaptive sampler's top-1 mass releases below 0.5 as the family becomes learnable), E5
(training-set family improvement) are secondary. The descent offsets {0,1} s are predicted to
remain ≤ 0.25 — augmentation cannot fix an airborne reference; that is N7's job.

**Pre-listed null follow-ups (verbatim from the seal's precondition):** (1) exposure mass
insufficient — grounded targeting of the family, one seed; (2) within-family start-phase
curriculum — start training episodes inside the feasible phase, one seed; (3) reward tax on the
reference — checked via the oracle's per-term reward rates (`r_self_collisions`, `r_joint_limit`)
before touching any weight. None of these expands the bank.

**Fills:** first GPU block after Sept 15; resume-safety check (frozen config re-loaded,
hash-checked, seeds confirmed) before relaunch; realized GPU-hours recorded and used to re-plan
the remaining budget.

## 8.2 N7 — repair the impossible [SLOT, seal pending N3 readout]

Draft on file (`plan/N7_DRAFT_repair.md`): contact-restoring projection of the attractor family's
airborne transitions (lower the root, re-solve leg IK, time-warp within original vertical-velocity
bounds; verify with the screen to ≤ 5 % infeasible frames and no new interpenetration). Sealed
predictions will include: the repaired descent becomes learnable in the augmented bank; the §9
motor-strength sign reversal *vanishes* on the repaired clip; unrepaired family descents do not
improve in the same run. Converts "exclude the impossible" into "repair the impossible" and closes
the feasibility axis causally rather than by omission.

## 8.3 E3 — support moderation at scale [SLOT]

**Sealed** (`plan/PREREGISTRATION_E3_addendum.md` `f7929136…` + v2 `2c38845b…` + the D1 policy
`a93a87a0…`): uniform-800 ×3 vs grounded-800 ×3 (+ ≤1 adaptive demo, optional LP arm);
bank-invariant support (clean-bank z-space, fixed kernel h = 2.00); **bidirectional named
predictions** — the 22 dynamic held-out clips all lose support 100→800 and are predicted to get
*harder* (P-A, the risky half); the 20 largest support gainers get easier (P-B); grounded's
advantage concentrates on the losers (P-D, H2b-S: ρ(Δᴳ⁻ᵁ, Δlog-support) ≤ −0.25). Feasible-only
primary endpoints per D1; bank composition (ground 3.2 % → 0.65 %, dynamic 11.8 % → 1.9 %) is an
analysed variable; feasibility flags are a launch gate (already computed for all 900 clips,
`reports/feasibility_e3/feasibility.csv`, sentinel present).

**Fills:** after N3 in the Sept-15+ GPU order; results freeze Dec 1.
