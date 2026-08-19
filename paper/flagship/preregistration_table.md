# Exhibit: the sealed record (every pre-registration, hash, prediction, outcome)

All hashes sha256 (truncated); seal files in `plan/`, hash manifests in `plan/*.sha256`.
Outcomes: ✅ confirmed · ❌ refuted/null (as sealed) · ⚠ uninformative by registration defect ·
🕐 slot (sealed, not yet run) · ⬅ withdrawn.

| seal | hash | sealed | primary prediction | outcome | artifacts |
|---|---|---|---|---|---|
| A2 (Exp-2 grounded arm) | `37daa8a9` | 2026-08-16 | grounded beats/matches uniform on AULC; beats adaptive | ✅ grounded ≫ adaptive (AULC +0.055, 3/3 seeds); grounded ≈ uniform (Branch B, AULC −0.002) | `plan/BRANCH_DECISION.md`, `reports/campaign_summary_3arm.json` |
| A2 co-primary (iters-to-target) | 〃 | 〃 | grounded reaches uniform's endpoint sooner | ⚠ target was uniform's own rounded-up mean → uniform censored at its own bar; reported as uninformative, no compute-reduction claim | `plan/BRANCH_DECISION.md` |
| E10 (α/cap 2×2) | `dc207877` | 2026-08-17 | (frozen before running) | 🕐 frozen per v4/v5 | `plan/PREREGISTRATION_E10.md` |
| S1 conformance verdict | — (result, not seal) | 2026-08-17 | Newton ≡ mjlab to seed noise | ⬅ **initial "PASS with a contact-event fork that is itself a fragility measurement" withdrawn**: the fork was four integration errors (#8–11); after fixes 1.000/1.000 vs 1.000/1.000 | `plan/S1_RESULT.md` (revised in place with the withdrawal recorded), `reports/S1_*_absorb.json` |
| G1 clip-#44 gate | `41e4b20c` + addendum `2a9ceaca` | 2026-08-17 | contact-model & CoM fragility ≥ 2× matched-easy, ≥ 5× same-solver floor, pre-failure localisation | ❌ **gate fails as sealed**: 1.30–1.33× on predicted axes; nothing reaches 5× floor; termination fragility zero everywhere | `plan/G1_RESULT.md`, `reports/G1/run0/` |
| N2 support features | (in `plan/N2_RESULT.md`, pre-stated) | 2026-08-18 | residuals concentrate on low support ✚ transfer lifts above 0.567 | ✅ residuals (ρ +0.60/+0.54) / ❌ transfer (+0.00–0.03, inside noise baseline) — the honest split | `reports/N2_atlas_support.json` |
| N3 coverage causality | `af1b7c9f` (+ precondition `3c331e18`) | 2026-08-18 | attractor kneel/crawl-phase survival 0.000 → ≥ 0.25 in 2/2 keystone seeds; random16 control < 0.10 | 🕐 chain paused (CPU-only rule); first GPU block after Sept 15 | `reports/N3_baseline_uniform-s1_strat.csv` |
| E3 addendum (support moderation) | `f7929136` | 2026-08-18 | H2b → support-moderation; stratified starts; composition analysed | 🕐 post-Sept-15 | — |
| E3 addendum v2 (bidirectional, named) | `2c38845b` | 2026-08-18 | 22 named dynamic clips get *harder* at 800; 20 named gainers easier; ρ(Δᴳ⁻ᵁ, Δsupport) ≤ −0.25 | 🕐 post-Sept-15 | `reports/support_change_heldout100_100to800.csv` |
| Atlas v2.1 feasibility features | `9b1a2c78` | 2026-08-18 | F1 within-bank lift ≥ +0.05 / F2 transfer lift ≥ +0.03 at p < 0.05 / F3 residual anatomy | ❌ F1 / ✅ **F2 (0.567 → 0.609, p = 0.010; all six pairs positive)** / half F3 | `reports/N_atlas_v21.json`, `plan/ATLAS_v21_RESULT.md` |
| D1 evaluation policy | `a93a87a0` | 2026-08-19 | (policy, not prediction) feasible-only primary; threshold provenance cited | — sealed before N3 relaunch / any E3 number | `plan/GLOBAL_EVAL_ADDENDUM.md` |
| P-SIGN sign-reversal generality | `c7916e8c` | 2026-08-19 | ≥ 8/12 family clips ≥ +5 mm airborne (CI>0); ≥ 8/12 controls < 2 mm; ≥ 3× localisation | 🕐 GPU gap capacity | `plan/PREREGISTRATION_P_SIGN.md` |
| P-TAX reward-tax relevance | `7960057a` | 2026-08-19 | tax → difficulty partial CI > 0 on ≥ 2 heldout arms | ❌ **null as sealed** (0/3; significant CIs are *negative*) — hygiene finding only | `plan/P_TAX_RESULT.md`, `reports/P_TAX_result.json` |
| Research plan v5 | `4d490cf8` | 2026-08-19 | (directive encoding) | — | `plan/RESEARCH_PLAN_v5.md` |

Also on the record without seals (results that changed course): the atlas transfer criterion miss
(ρ 0.567 < 0.6 sealed bar, `reports/A3_atlas_transfer.json`); the H4→H4-r sign correction and the
A2 target defect (`plan/ADDENDUM_2026-08-16.md`); the "0.31 survival" start-offset artifact and
the 12→20 family-count correction (`plan/GLOBAL_EVAL_ADDENDUM.md`).
