# Red-team audit — "what exposure, harness, or data artifact could explain this instead?"

Pass scheduled Sept 5–12 (RESEARCH_PLAN_v5). Skeleton opened 2026-08-19 so checks can be logged as
they are done rather than reconstructed. Format: claim → alternative artifact explanations →
closing check (specific, with artifact path) → status.

Prior escapes that motivate this pass: the transfer gap was an observation bug (stale first obs);
the adaptive deficit was a sampler bug (non-floor); the hardest clip was a data bug (airborne
retarget); the "contact-event fork" was four harness bugs (#8–11); the "0.31 survival" was a
protocol bug (start-offset averaging).

| # | claim (§) | alternative explanations to attack | closing check | status |
|---|---|---|---|---|
| 1 | Adaptive collapses onto one clip (§3) | logging artifact in telemetry; per-seed coincidence; resample-time confound | raw sampler telemetry across 3 seeds shows same clip (`A7`); clip identity stable across arms; entropy series continuous | ✅ closed (A7, A5) |
| 2 | Uniform beats adaptive (§3) | eval-set composition favouring uniform; horizon truncation; auto-reset bias | 3/3 seeds, paired; strata (D1) preserve ordering; wrap-freeze protocol in `climb_eval.py` documented | ✅ (strata re-checked 08-18) |
| 3 | Non-floor derivation (§3) | misread upstream code; version drift | derivation + minimal repro in filed issues #1153/#73; upstream acknowledged? → **check issue thread state before submission** | ⏳ |
| 4 | Grounded ≫ adaptive (§4) | ρ=0.1 floor acts as different *exploration*, not coverage; extra uniform data volume | entropy/top-1 telemetry shows floor binds only at collapse; exposure ledger… **ledger frozen — state as limitation, not check** | ⏳ needs wording |
| 5 | Conformance closure (§5.1) | agreement by coincidence of seeds; absorbed-writes hiding real divergence | per-substep |Δq̇| ≤ 3e-5 at every substep (not endpoints); MuJoCo-C referee; two repeats; absorbed-write count logged (57–59) | ✅ (`S1_RESULT.md`) |
| 6 | G1 negative (§5.2) | δ too small; φ too coarse; floor rule too strict | N5 recalibration finds real 6–14 mm effects with the *same data* — instrument, not δ, was the limit; negative stands under both statistics | ✅ (`g1_v2_summary.json`) |
| 7 | N1 airborne verdict (§5.3) | ground-alignment offset placed the whole clip too high; gap 6 cm arbitrary; qdd differentiation noise | gap sensitivity 3/6/10 cm run 08-17 (`n1_*_0.06/0.10.json`); control clip supported at every frame under same pipeline; standing phase of #44 itself is supported (internal control) | ✅ |
| 8 | Prevalence 22.8 % (§6) | flight conflated with infeasibility; screen bug on specific sources | category caveat sealed in atlas-v2.1 prereg *before* prevalence read; per-source spread argues pipeline; **to do: manually inspect 5 flagged CNRS + 5 Transitions clips** | ⏳ |
| 9 | Feasibility transfer lift (§7) | three extra features lift any ridge; leakage via screen fit to difficulty | 200-draw random-feature permutation (p = 0.010–0.045); screen never sees difficulty labels | ✅ (`N_atlas_v21.json`) |
| 10 | Sign reversal (§9) | window definition post-hoc; two seeds share the harness | windows from reference-only contact flags (N1), defined before windowed analysis; P-SIGN sealed with controls — **wait for P-SIGN before promoting** | 🕐 sealed |
| 11 | Support-residual correlation (§7) | kNN distance ≈ outlier-ness ≈ intrinsic hardness (circularity) | stated as diagnosis in N2; only E3's bank-change breaks the circle — **write as pending, not closed** | ⏳ wording |
| 12 | P-TAX null (§6) | tax measure too coarse (binary >1 cm); population too small | bootstrap CIs are wide but sign is consistently negative; sealed rule respected; stated as null with CI | ✅ |
| 13 | Oracle precondition (§8.1) | playback bypasses physics → terminations trivially pass? | playback *teleports then steps* — terminations evaluated on post-physics state; PD-follow failure on easy clips shows the oracle's limitation is balance, not terminations | ✅ (`N3_PRECONDITION`) |

Open items to close during the pass: #3 (issue threads), #4 (limitation wording), #8 (manual
inspection of extreme-source clips), #11 (pending-tense wording), plus a fresh sweep of any new
text written after this date.

| 14 | Related-work positioning (§2) | misattributed sampler lineage; invented refs | 12 citations live-verified 2026-08-20 (arXiv/DOI listed in RESULTS_LOG); ○-marked standards flagged for final bib pass; LUCID explicitly flagged internal | ⏳ final bib pass |
| 15 | "Screen catches what kinematic QC cannot" (§2, §6) | GMR/Retargeting-Matters criteria might already catch it | their criteria are clearance/sliding/self-intersection — the airborne descent has *good* clearance by construction; state as: complementary, dynamic vs kinematic | ✅ wording in S2 |
