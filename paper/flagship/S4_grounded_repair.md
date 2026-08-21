# 4. Grounded repair: normalise-then-mix restores coverage without giving up prioritisation

**Claim class: sealed-confirmatory** (pre-registration A2, sha `37daa8a9…`, sealed 2026-08-16
before the grounded arm's final evaluation existed; adjudication `plan/BRANCH_DECISION.md`).
Strata per `plan/GLOBAL_EVAL_ADDENDUM.md` (sealed `a93a87a0…`): feasible-only primary, all-clips
secondary, infeasible-only descriptive.

**The repair.** The upstream sampler adds its uniform term into *counts*: p ∝ q + ε/N, so the
uniform share is ε/(Σq + ε) — vanishing exactly when failures are plentiful (§3). Grounded
sampling normalises first and mixes on the simplex: p = (1 − ρ)·softmax(failure weights) + ρ·u,
ρ = 0.10 — a true, scale-invariant floor. One line of code; the same failure signal.

**Effect on exposure (the mechanism variable).** Over 3 seeds × 4,000 iterations
(`reports/A5_coverage_dose.json`): mean sampling entropy 0.60–0.62 vs adaptive's 0.38–0.40; top-1
clip mass max 0.57–0.70 vs 0.87–0.89. The attractor is the same clip in all six adaptive/grounded
runs (`reports/A7_attractor.json`) — grounding does not change *what* the sampler wants, it bounds
what it can *spend*.

**Effect on performance.** Held-out survival at iteration 3999 (3 seeds, seed-mean ± sd where
sealed; `reports/campaign_summary_3arm.json`, `reports/N_atlas_v21.json`):

| arm | feasible-only (primary, 71 clips) | all 100 (secondary, sealed record) | infeasible-only (descriptive, 29) |
|---|---:|---:|---:|
| adaptive | 0.811 | 0.780 ± 0.006 | 0.705 |
| uniform | 0.834 | 0.810 ± 0.005 | 0.750 |
| grounded | **0.859** | **0.825 ± 0.009** | 0.741 |

Sealed adjudication (all-clips, as registered): grounded ≫ adaptive (AULC +0.055, endpoint +0.044,
3/3 seeds) — **coverage-grounding rescues failure-weighted adaptivity from collapse**. Against
uniform, the sealed primary (AULC) is a match (0.6956 vs 0.6979, −0.3 % relative); the endpoint
favours grounded (+0.015, 3/3 seeds) but is secondary, and the sealed verdict is **Branch B:
grounded ≈ uniform** at 100 clips. The registered co-primary (iterations-to-0.810) is reported as
**uninformative by construction**: the target was uniform's own rounded-up endpoint mean, which
censors uniform at its own bar — a registration defect we document rather than exploit
(`plan/BRANCH_DECISION.md`).

**The stratified re-analysis sharpens the mechanism** (exploratory; strata computed 2026-08-18,
`plan/ATLAS_v21_RESULT.md` §2b): grounded's endpoint edge over uniform is **+0.025 on feasible
clips and −0.009 on infeasible ones**. A curriculum can only help where success is possible; no
sampler can teach a policy to track a reference that asks the robot to hover (§5–6). This is also
the honest frame for the sealed Branch B: at 100 clips, 29 % of the *evaluation* mass sat in a
stratum where the compared samplers cannot differ except by noise.

**What remains open, and what has read out.** Whether prioritisation beats uniform when the bank is
diverse enough for coverage to bind is E3's question (800 clips), sealed with bidirectional
support-moderation predictions including named clips that should get *worse*
(`plan/PREREGISTRATION_E3_addendum_v2.md`, `2c38845b…`). Whether *composition* — not sampling —
is the causal fix for the attractor's family was N3's question: its targeted endpoints pass, but
an adaptive-arm regression triggers the preflight stop and prevents unqualified closure
(`plan/N3_RESULT.md`). E3 remains a slot in §8.
