# CLIMB flagship — structure of record (updated 2026-08-19 per RESEARCH_PLAN_v5 / D4)

Supersedes `00_outline_2026-08-18.md`. Format: RSS 2027 (CoRL 2027 fallback). Every table row
labelled **sealed-confirmatory** or **exploratory**. Withdrawn claims stated as withdrawn. No
claim without an artifact path (`paper/RESULTS_LOG.md`).

## Working titles (proposed, NOT committed — for review)

1. *Feasibility First: Why Humanoid Motion-Tracking Curricula Collapse, and What Difficulty Is Made Of*
2. *The Impossible Clip: Feasibility, Support, and Intrinsic Difficulty in Humanoid Motion Tracking*
3. *Not Hard, Impossible: Auditing What Failure-Adaptive Curricula Actually Learn From*
4. *Where Tracking Difficulty Comes From: A Feasibility × Support × Intrinsic Decomposition for Humanoid Motion Banks*
5. *Chasing a Hovering Reference: Sampler Collapse, Infeasible Retargets, and Coverage Repair in Humanoid Motion Tracking*

## Spine (one figure, F1 drafted)

Difficulty = **feasibility × support × intrinsic**; each axis has its own measurement (contact LP ·
kNN support · atlas features) and its own fix (repair/exclude · composition · curriculum/robustness).
The chain: sampler collapse → the non-floor → the infeasible-and-unsupported attractor → grounded
repair → composition causality (N3 slot) → support moderation at scale (E3 slot).

## Sections

| § | title | state | file |
|---|---|---|---|
| 1 | Introduction — the chain and the decomposition | **complete** | `flagship/S1_intro.md` |
| 2 | Related work — adaptive sampling/prioritisation (PER, PLR, BeyondMimic sampler, mjlab), generalist humanoid tracking (SONIC-era), retargeting & physical plausibility (contact-aware retargeting, physics-filtered mocap), exposure-auditing (LUCID companion). **12 citations verified live 2026-08-20; ○-marked standards queued for final bib pass; LUCID flagged as internal.** | **complete (draft)** | `flagship/S2_related.md` |
| 3 | Sampler collapse and the non-floor (Exp-1; #1153/#73 reach) | **complete** | `flagship/S3_collapse_nonfloor.md` |
| 4 | Grounded repair (Exp-2 + D1 stratified re-analysis) | **complete** | `flagship/S4_grounded_repair.md` |
| 5 | Anatomy of an attractor (G0 elimination → G1 negative → N1 verdict; errors #8–11 → Appendix A1) | **complete** | `flagship/S5_anatomy.md`, `flagship/A1_g0_appendix.md` |
| 6 | The feasibility screen at scale (prevalence, eval contamination, label hygiene incl. the P-TAX null; compressed, cites companion note) | **complete** | `flagship/S6_screen_at_scale.md` |
| 7 | Difficulty that transfers (N2; atlas v2.1 0.567→0.609 perm p=0.01; support-moderation pending E3) | complete + slot | `flagship/S7_transfer.md` |
| 8 | Causal tests — N3 keystone slot (null follow-ups verbatim from seal); N7 slot (seal after N3); E3 slot (bidirectional predictions, named gainers/losers) | slots | `flagship/S8_causal_slots.md` |
| 9 | The calibrated instrument (N5; r = 0.92 replication; Lyapunov-horizon finding) + P-SIGN slot | complete + slot | `flagship/S9_instrument.md` |
| 10 | Limitations and scope | **complete** | `flagship/S10_limitations.md` |
| — | **Pre-registration table** (first-class exhibit): every seal — hash, date, prediction, outcome, artifact — incl. the failed G1 gate, the withdrawn S1 verdict, the N2 within-bank null, the P-TAX null | **complete** | `flagship/preregistration_table.md` |
| A1 | G0 conformance detail (errors #8–11, protocol) | complete | `flagship/A1_g0_appendix.md` |
| A2 | N5 instrument calibration detail | Aug 23–Sept 5 | from `plan/N5_RESULT.md` |
| A3 | Screen validation detail | Aug 23–Sept 5 | from `plan/N1_RESULT.md` + companion |

## Figures (script + data path recorded; regenerate-only after Dec 1 freeze)

| fig | content | script | data |
|---|---|---|---|
| F1 | decomposition spine | `paper/figures/decomposition.svg` (hand-drawn SVG) | — |
| F2 | collapse mechanism timeline: entropy/top-1 vs held-out gap | **done** `paper/figures/f2_collapse.py` | `reports/A5_coverage_dose.json`, `reports/campaign_summary_3arm.json` |
| F3 | clip #44 anatomy: airborne window, unsupported force, start-offset deaths, F(t) | `paper/figures/f3_anatomy.py` (adapt the upstream repro figure) | `reports/N1_clip44_knee_id.json`, `reports/N3_baseline_uniform-s1_strat.csv`, `reports/G1/run0/g1_summary.json` |
| F4 | prevalence by category × source | **done** `paper/figures/f4_prevalence.py` | `reports/feasibility_all/feasibility.csv` |
| F5 | transfer lift (intrinsic vs +support vs +feasibility, perm baselines) | **done** `paper/figures/f5_transfer.py` | `reports/N2_atlas_support.json`, `reports/N_atlas_v21.json` |
| F6 | N3 slot (stratified-start survival, keystone) | after N3 | `reports/N3_*` |
| F7 | E3 slot (support-moderation, named strata) | after E3 | — |

## Companion note (`paper/companion/`) — submittable Sept 5

*Auditing dynamic feasibility of retargeted humanoid motion data* (4–6 pp, arXiv + workshop).
Method → validation on #44 (+N5 sign-reversal corroboration) → prevalence tables → eval-set
contamination (29/100) → recommendations → tool (refeas v0.1.0). Flagship cites it, keeps §6
compressed.

## Red-team pass (Sept 5–12) → `paper/RED_TEAM.md`

For every claim: "what exposure, harness, or data artifact could explain this instead?" + the
specific check that closes it. The project's own history (transfer gap = observation bug; adaptive
deficit = sampler bug; hardest clip = data bug) is the reason this pass is mandatory.
