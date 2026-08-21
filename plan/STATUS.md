# CLIMB / feasibility-first — status against Research Plan v5

Updated 2026-08-21. **v5 (`RESEARCH_PLAN_v5.md`, sealed `4d490cf8…`) is authoritative**: D1
evaluation policy, D2 spin-out, D3 new seals, D4 writing-first window to Sept 15. v4's freeze
discipline continues underneath. Seals manifest: `plan/SEALS_2026-08-19.sha256`.

## State as of 2026-08-21 (writing-side snapshot — what a reader needs to know first)

| item | state | where |
|---|---|---|
| **N3 completed and unblinded** | Frozen arithmetic gate E1∧E4 passes (ground16 0.750/0.750; random16 0.000), but the adaptive arm violates E2 (heldout Δ −0.0346; easy 0.857), triggering the frozen preflight stop. E3 fails (late max top-1 0.784); descent prediction misses (1.000/0.688). Report as a **mixed sealed outcome**, not unqualified causal closure. | `reports/N3_result.json`, `plan/N3_RESULT.md` |
| **E-HYG completed and unblinded** | **Sealed null:** feasible heldout Δ −0.0101, p=0.951; P1 and P2 fail; ZS-ground Δ −0.0354 remains inside its bracket. Clip pruning at this prevalence/seed does not improve training. | `reports/E_HYG_result.json`, `plan/E_HYG_RESULT.md` |
| **P-SIGN completed** | **Sealed fail:** family 7/12, clean controls 4/12, localised 2/7. The two #44 cases remain exploratory; the runtime-detector claim is rejected. | `reports/P_SIGN/run0/p_sign_summary.json`, `plan/P_SIGN_RESULT.md` |
| **SONIC feasibility-hygiene training ablation** | **DESCOPED**, on its own pre-registered rule. The full BONES-SEED bank (4,950 clips) was screened by an independently written implementation of the screen: **7 clips (0.14 %) exceed `infeasible_frac > 0.10`, against 22.8 % on the AMASS/whole_body_tracking bank** — a factor of 160; 111 (2.24 %) exceed `airborne_frac > 0.10`; flagged duration 0.09 %. P10 registered the prediction (< 10 %) *and* pre-committed the consequence (a low rate descopes the ablation), so arms B/C would differ from A by seven clips and no training run resolves that. Five of the seven are jumps (four named for the 50 cm box they use, which is absent from the flat scene) — a scene mismatch, not a retarget defect, and not repairable by root projection. Kept from the run: seven `kneeling_loop_*` clips at airborne 1.000 / infeasible 0.000 (the evidence that airborne and infeasible must stay separate axes), and a cost of **0.145 CPU-s per clip = 0.84 ms per screened frame** that makes the screen a standing release gate (the drafts previously quoted 0.21, the wall × workers equivalent; reconciled 2026-08-19). | `GR00T-WholeBodyControl/docs/prediction_register.md` (P10), `docs/plan_feasibility_hygiene_v1.md`; screen `gear_sonic/research/hygiene/screen.py` |
| **What that means for the papers** | The AMASS 22.8 % is a measurement of *one corpus-and-pipeline pairing*, not a rate for retargeted banks in general — a second production stack screens 160× lower. Folded into flagship §1/§2/§6/§10/A3, companion abstract/§4/§7/§8, `RESULTS_LOG`, `RED_TEAM` (rows 8, 17, 20, 21). **Two sweeps, both closed:** the first found and fixed the sites where 22.8 % read as generic; the second (same day) tightened "property of *the retargeting pipeline*" → "of a particular corpus-and-pipeline pairing" (corpus content and the `robot_filtered` release filter are confounded with the retargeter, as §10 already said), removed "SONIC's bank is clean" from §2, added the release-filter confound to §6's caveat, scoped the companion's repair split from "for the community" to "on this bank", and reconciled the screen-cost figure against the P10 register. Full site lists: `paper/CONSISTENCY_SWEEP_2026-08-20.md`, both addenda. | `paper/` |
| **FGAS completed — soft formulation fails its implementation gate** | All three MJLab seeds reached 3999/4000 and every frozen evaluation completed. Feasible-hard20 survival is 0.7586→0.7390 (Δ **−0.0196**, 95% CI [−0.0497,+0.0134]); feasible-heldout Δ −0.0123 passes the no-regression bound. Late rejected-start mass is 0.199, failing the `<0.15` wiring gate, while top-1 remains flagged 0.861 of the time. Post-outcome reconstruction matches telemetry within 0.0022: failure weighting overwhelms the clip-mean soft multiplier. Report this as **soft FGAS not validated**, not a broad rejection of segment-native FGAS. | `reports/FGAS_result.json`, `reports/FGAS_diagnosis.json`, `plan/FGAS_RESULT.md` |
| **Segment- vs clip-level curation measured** | On `tier_800`'s 99 flagged clips (20.2 min of 152.4 min): guard 0 s recovers 12.5 min (61.7 %), 584/1,259 bins, 3/99 clips lost; guard 1.0 s recovers 5.8 min (28.9 %), 305/1,259 bins, 26/99 lost. Bank-level: pruning discards 13.3 % of duration, curation returns 8.2 % / 3.8 %. Generalisable claim carried into the drafts: **the value of segment-level curation falls as the policy's reference lookahead grows** — the guard band is a property of the framework, not the data. Carried as a **duration** claim only — no training arm has consumed curated segments — with `--min-seg-s 1.0` and strict bin eligibility labelled as choices, not measurements (`RED_TEAM` row 21, open by construction). Landed in flagship §6, companion §8, `RESULTS_LOG`; figure F9 is a written candidate, not drawn. | `reports/segments_tier800/`, `tools/screen_segments.py`, `plan/FGAS_DIRECTIVE_2026-08-19.md` |
| **Contamination / hygiene measurement** | Bank prevalence **done** (22.8 % of 10,705). Legacy repair recovers 1,606/2,442 strict-flagged clips through 15 cm (65.8 %); C4 corrects the historical 2,443-row directory's extra feasible control. Tier-level pruning **done** (`tier_800_pruned`, 701 clips). | `reports/feasibility_all/`, `reports/dfrp_v0/census/`, `paper/CORRECTIONS_2026-08-21_DFRP.md` |
| **DFRP v0 CPU gate** | Artifact contract, root/contact-IK operator, exact-unit integration, two-clip training-ready view, and strict full-bank legacy routing audit complete. 644/2,442 (26.4 %) fit the 8 cm displacement tier, but all bank-wide legacy repairs remain qualification-incomplete and zero are promoted to training. | `plan/DFRP_V0_RESULT_2026-08-21.md`, `reports/dfrp_v0/` |
| **DFRP v1 exact panel passes** | Unsealed frozen CPU panel: 22/26 flagged repairs are exact-ready and all 4 controls are byte-identical/ready. The curated view contains 26 clips, 36 units, and 10,561 legal 50-step starts. Two residual-infeasibility and two IK-qualification failures remain excluded. This validates the implementation gate only—not a bank-wide recovery rate or policy benefit. | `plan/DFRP_V1_EXACT_PANEL_RESULT_2026-08-21.md`, `reports/dfrp_v1_exact_panel/` |
| **Corrections applied** | C1 exposure attribution (the impossible clip's share bracketed [21.9 %, 48.8 %]; the JSON key was copied), C2 saturation-at-fall (≥ 4/29 in 8/8, exactly 5/29 in 7/8, mean 16.8 %), C3 per-actuator identity **withdrawn** (not recoverable from the artifact). All three fixed in place across `RESULTS_LOG`, flagship, companion, payoff plan, `RED_TEAM` row 18. | `paper/CORRECTIONS_2026-08-19.md` |
| **Open artifact-hygiene item** | The second bank's 4,950-row per-clip screen CSV was not found in accessible `/tmp` paths; the durable record is still only the P10 register entry. It needs a durable path + sentinel before submission. The public-site prose and rendered drafts are now synchronized with the 2026-08-20 outcomes and per-corpus prevalence framing. | flagged in `paper/CONSISTENCY_SWEEP_2026-08-20.md` |

## Payoff directive (2026-08-21, Linji): approvals and launches

| item | state |
|---|---|
| **E-HYG approved** ("完全批准") → **sealed** `a5494b7c…` + frozen analysis `5f8eb56e…` (4-branch synthetic dry-run passes, incl. the VOLUME branch that catches "just fewer clips") | `plan/PREREGISTRATION_E_HYG.md`, `tools/analyze_ehyg.py`, `plan/E_HYG_FREEZE.sha256` |
| Banks/lists sealed by hash: tier_800_pruned (701 clips; tier_800 is 12.4 % flagged by clip count and 13.3 % by duration — a *lower bound* vs the raw bank's 22.8 %, and itself an over-estimate of what must be lost: segment curation recovers 61.7 % of the flagged duration at guard 0 s), zs_ground_feasible (60), zs_dynamic_feasible (60) | `bank/tiers/`, `reports/segments_tier800/` |
| **N3 + E-HYG chain completed** through the gap-gated shared queue. Resume safety passed; all training/evaluation sentinels and the final chain sentinel exist; frozen analyses read out as N3 mixed and E-HYG null. | `tools/n3_ehyg_chain.sh`, `logs/campaign/n3_ehyg_chain.log`, `plan/N3_RESULT.md`, `plan/E_HYG_RESULT.md` |
| Repair census: **complete** — historical directory 1,607/2,443; strict-set correction 1,606/2,442, both 65.8 % rounded. DFRP split: 644 within 8 cm, 962 additional through 15 cm. | `reports/repair_census/summary.{json,md}`, `reports/dfrp_v0/census/summary.{json,md}` |
| Narrative: efficiency cliff (3 CPU-h vs 10³–10⁴ GPU-h) + exposure ledger (adaptive mean 48.8 % of draws on the impossible clip) into S1 contributions & companion §8; **three deliverables** named (refeas · contact-projection repair · eval/monitoring protocols) in S1, companion §8, README | commit `f124d71` |
| **N7 completed — positive deployment contrast, sealed joint fail:** R/repaired − K/raw is +0.0397 (motion-bootstrap CI [+0.0153,+0.0658]) but misses the +0.05 SESOI; R/raw − K/raw is −0.0036, so no policy-only transfer is visible. Heldout point non-regression passes; the ZS-ground coverage rule fails. Post-outcome audit finds eight tier800 overlaps in `heldout100` and concentrates most deployment benefit in 11 over-budget repairs. | `reports/N7_result.json`, `reports/N7_posthoc_audit.json`, `plan/N7_RESULT.md` |
| **Core/evaluation review + paired-v2 pilot completed** | Three independent reviews found raw failure-flux feedback, nonterminal clip-wrap teleports, start-only masking, unpaired evaluation DR, clipped duplicate offsets, stale first observations, and reset-contaminated terminal metrics. Sealed results stay unchanged. Separate v2 primitives now use stable segment IDs, fixed-clock conditional statistics, dedicated RNG, hard support, unit/clip caps, exact frame sidecars, a fail-closed unit table, and sampler-equivalent resume (37 focused tests pass; cap re-review passed 4,000 randomized certificates). The paired evaluator completed a strict 3,296-trial repair pilot: R/repaired − K/raw success +0.1355 [0.0505,0.2365], but R/raw − K/raw only +0.0234 [−0.0123,0.0825]. A 672-trial disjoint clean/raw control shows no clear regression. This is exploratory routing evidence, not a replacement for sealed N7 or a training claim. | `plan/SEGMENT_NATIVE_FOLLOWUP_2026-08-20.md`, `reports/eval_v2_pilot/result.json`, `reports/segment_v2_smoke/unit_table.json`, `autoresearch/evals-260820-1734/review_log.md` |

## Publication state (2026-08-20, on Linji's instruction)

Both repos **public**: github.com/linjiw/climb-feasibility-first (project, page, drafts, sealed
record) and github.com/linjiw/refeas (tool, v0.1.0). GitHub Pages live:
**https://linjiw.github.io/climb-feasibility-first/** (source `docs/`, branch master). Root
README rewritten as the public front door with a reviewer guide (RESULTS_LOG → prereg table →
companion+review → RED_TEAM → STATUS); the old operational README preserved as `WORKSPACE.md`.
Flagship sections assembled into `paper/flagship/DRAFT_full.md` (section files remain the source
of truth). An external reviewing agent is expected; its guidance lands as a future directive.
Upstream note drafts remain **NOT FILED** (visible in-repo as drafts) pending Linji's approval.
Both drafts now **render as typeset pages on the site** (2026-08-21): `docs/companion.html` and
`docs/flagship.html`, generated from the markdown sources by `tools/render_paper_html.py`
(figures injected at content anchors; print stylesheet = PDF via browser print). The HTML is
generated output — edit the markdown, re-run the renderer, commit both. index.html hero/footer
link to them (commit `7c5caa2`).

## v6 directive (2026-08-20, `ADVISOR_DIRECTIVE_2026-08-20_v6.md` `98b78d9c…`) — task ledger

| task | state | output |
|---|---|---|
| consistency-sweep | **done, table empty** — (a) 6/6 direction vs 4/6 significance split stated everywhere; (b) d_z=20 replaced by per-seed Δ +0.030/+0.028/+0.030; (c) "dual-engine" → dual-stack same-engine with pins named; (d) 329/327 pairing verified vs artifact (median 328.6 N) | `paper/CONSISTENCY_SWEEP_2026-08-20.md` |
| coupling-taxonomy | **done** — 9 error classes × (symptom, detector, S1 instance); ships as companion Appendix A + refeas docs | `paper/companion/appendix_coupling_taxonomy.md`, `refeas/docs/COUPLING_TAXONOMY.md` |
| cnrs-audit | **done — verdict: CNRS = ingest (ordinary walks floating 6–8 cm; subset-wide root-height convention); Transitions = mixed (acrobatic content, flagged frames are non-ballistic floating, severity 22 % vs 57–66 %)**; advisory reworded; upstream drafts remain NOT FILED pending approval | `reports/upstream_drafts/CNRS_AUDIT.md` |
| n3-preflight (P1) | **done** — frozen `tools/analyze_n3.py` (sha `b118b2d3…`), 4-branch synthetic dry-run passes, all 16 neighbours confirmed ≤ 0.10 infeasible with support metrics, decision tree written; s2/s3 stratified baselines flagged as pre-unblinding requirement | `plan/N3_PREFLIGHT.md`, `reports/N3_ground16_preflight.csv` |
| psign-prep (P2) | **done, experiment read out** — analysis frozen (sha `db538a9b…`); sealed experiment fails 7/12 family, 4/12 controls, 2/7 localised | `plan/P_SIGN_PREP.md`, `plan/P_SIGN_RESULT.md` |
| threshold-audit | **spec only (as directed)** — λ-injection design, TOST bounds ±1/32 on the sealed primary, negative framing: bugs #6/#8/#9 sit 1.3–110,000× above the threshold; #11 shows why a q̇ threshold can't replace bidirectionality checks | `plan/SPEC_threshold_audit.md` |
| newton-1.0-recert | **spec only (as directed)** — version-note flagged (GA line vs checkout metadata; commit hash is the pin), 6-step protocol identical to S1, float32-geometry class marked predicted-sensitive | `plan/SPEC_newton_recert.md` |
| companion-review (P0) | **done — 2 majors found and fixed same day** (ephemeral gap-sensitivity artifact → durable `reports/N1_gap_sensitivity.json`, and the "6–11 points" error → 6.0–8.4/8.4–11.8 corrected in 4 documents); 5 minors fixed; **zero unresolved majors** | `paper/companion/REVIEW_2026-08-20.md` |
| companion note (P0) | **v0.2 submit-candidate**: full prose, every claim labelled, every number pathed, pins in header, taxonomy appendix, gap/bound sensitivity honestly stated | `paper/companion/companion_note_draft.md` |
| upstream-drafts (P3) | unblocked by cnrs-audit; drafts updated; **awaiting Linji approval to file** | `reports/upstream_drafts/` |

P0 DoD check: numbers pathed ✓ · labels ✓ · taxonomy appendix ✓ · versions pinned ✓ ·
sweep table empty ✓ · review zero majors ✓ → **companion is submit-ready pending Linji's
author/scope pass and figure typesetting.**

## v5 Aug 19–22 tranche — status

| item | state | where |
|---|---|---|
| D1 GLOBAL_EVAL_ADDENDUM | **sealed** `a93a87a0…` (threshold provenance cited; worked example recorded; conflicts with N3/E3 seals flagged §Conflicts; 12→20 family-count correction recorded) | `plan/GLOBAL_EVAL_ADDENDUM.md` |
| P-SIGN pre-registration | **sealed** `c7916e8c…`; harness built (`tools/p_sign_gate.py`, `tools/analyze_p_sign.py`, clip lists in plan/); gap watcher armed (≥7 GB free + util<60% ×3 checks) | `plan/PREREGISTRATION_P_SIGN.md` |
| P-TAX pre-registration + run | **sealed `7960057a…` and run — NULL as sealed** (0/3 heldout arms positive; significant CIs negative). Hygiene finding only | `plan/P_TAX_RESULT.md`, `reports/P_TAX_result.json` |
| D2a tool repo | **done**: `refeas/` v0.1.0, Apache-2.0, G1 worked example (synthetic hover flags 45 %), schema documented, git tag | `refeas/` (commit 865e93a) |
| D2c upstream drafts | **drafted, NOT filed — await Linji's approval**: wbt/BeyondMimic retarget note + dataset advisory (CNRS/Transitions); repro figure + screen JSON attached | `reports/upstream_drafts/` |
| D2b companion note | draft v0.1 (structure + abstract + all section content; figures F1/F2 to generate) — submittable target Sept 5 | `paper/companion/companion_note_draft.md` |
| D4 flagship §3–§6 | **prose complete** (§3 collapse/non-floor, §4 grounded repair with D1 strata, §5 anatomy with the withdrawal narrated, §6 screen at scale incl. P-TAX null); §7 and §9 also complete-with-slots; §8 slots structured; pre-registration table built | `paper/flagship/`, `paper/00_outline.md` |
| Results log / red team / parking | opened: `paper/RESULTS_LOG.md` (every paper number → artifact), `paper/RED_TEAM.md` (13 rows, 4 open items for the Sept pass), `plan/PARKING.md` (6 parked ideas) | |
| Sentinels | `tools/with_sentinel.sh`; retroactive sentinels on both screen runs | `reports/feasibility_*/COMPLETED` |

## Aug 23–Sept 5 tranche — progress (updated 2026-08-20)

| item | state |
|---|---|
| Flagship §1 Introduction | **complete** (`paper/flagship/S1_intro.md`) — chain + decomposition + contributions |
| Flagship §2 Related work | **complete (draft)** — 12 citations live-verified (BeyondMimic 2508.08241, mjlab 2601.22074, SONIC 2511.07820/SciRobotics, PLR 2010.03934, PHC, MaskedMimic, PhysCap, ASAP, PolySim, GMR, Retargeting Matters 2510.02252, contact-aware retargeting 2109.07431); ○-standards queued for bib pass; LUCID flagged internal |
| Flagship §10 Limitations | **complete** — incl. the solver-ensemble descope rationale |
| Figures F2/F4/F5 | **generated** with recorded scripts + data paths (`paper/figures/`) |
| P-SIGN harness | **run; sealed fail** (`tools/p_sign_gate.py` + sealed analysis `tools/analyze_p_sign.py`): 7/12 family, 4/12 controls, 2/7 localised |
| Companion note | figure refs wired; prose v0.1 stands; submit-ready pass next |

## Next scheduled

Next: integrate exact segment units into the command runtime, implement explicit
segment-boundary truncation with time-limit bootstrap, and simulator-trace every
reference frame before the 512-env smoke. Then separately seal a common-mechanics
MJLab segment-native comparison. Add common-reference contact timing before any
motion-quality claim. E3 → E10 → E4 remain later in the queue. Dec 1 results freeze.

## The three v4 actions

| action | state | where |
|---|---|---|
| 1. Freeze E3/E4/E10, ledger, full SONIC training, S2 solvers | **frozen** | tasks #11 (frozen), #13 (demoted) |
| 2. G0 same-solver conformance | **CLOSED 2026-08-17 22:20** — four integration errors (DR never mirrored; float32 geometry rounding → knife-edge foot contact; stale first obs; one-directional coupling missed mjlab-side state writes such as the clip-wrap teleport). KIT_1226 n=32: Newton 1.000/1.000 vs mjlab 1.000/1.000, Δerr −0.0005; clip #44 0.000 vs 0.000, Δerr +0.001. | `plan/S1_RESULT.md`, `reports/S1_*_absorb.json` |
| 3. G1 clip #44 gate | **RUN 2026-08-17 23:05, does NOT pass** (`G1_RESULT.md`). 480 worlds, 6 clips × 8 ICs × 10 configs + condim arm + mjlab floor. Contact-model 1.33×, CoM 1.30× vs easy (P1 needed ≥ 2×); motor 2.16× but no axis reaches the 5× same-solver floor; #44 dies 8/8 in every configuration, at every start offset, with ~0 actuator saturation until the fall → policy representation/coverage failure, not physics fragility. Exploratory: +15% motor uniquely *hurts* #44 (sign reversed vs all other clips). Methodological: single-trajectory paired |Δφ| is chaos-dominated (same-solver floor ≈ effect sizes) → F must use signed replicate means / distributions. | `reports/G1/run0/`, `tools/g1_clip44_gate.py`, `tools/analyze_g1.py` |

## Advisor next steps N1–N6 (2026-08-18, `ADVISOR_NEXT_STEPS_2026-08-18.md`)

| step | state | result | where |
|---|---|---|---|
| N1 knee-contact inverse dynamics | **done** | #44's reference is dynamically **infeasible in the descent** (0.75–1.75 s: feet 7–10 cm airborne, ~1 g unsupported) and the rise (8.0–8.5 s); the kneel/crawl phase itself is feasible within torque limits. 12 of the 40 nearest ground clips share the airborne artefact (BMLmovi sit/kneel family). Control CMU_76 fully supported. | `N1_RESULT.md`, `tools/n1_knee_id.py`, `reports/N1_*.json` |
| N2 relational atlas v2 | **done** | Atlas misses concentrate on low-support clips (ρ(|resid|, kNN) +0.60 / +0.54) — but #44 is not the extreme point (residual rank 43/14, support rank 8), and support does not lift cross-policy transfer on one bank (0.567 → 0.584, within a noise-feature baseline) because support is collinear with intrinsic features until the bank changes. Uncontaminated version pre-registered for E3. | `N2_RESULT.md`, `tools/analyze_atlas_support.py`, `reports/support_features_*.csv` |
| N3 coverage causality | **run; mixed sealed outcome** (`af1b7c9f…`) | E1/E4 pass (0.750/0.750; random 0.000), but adaptive E2 regression triggers the preflight stop; E3 and descent predictions miss. | `reports/N3_result.json`, `plan/N3_RESULT.md` |
| N4 E3 addendum | **done, sealed** (`PREREGISTRATION_E3_addendum.md`, sha `f7929136…`) | H2b → support-moderation (ρ(Δ_c, ΔS_c) ≤ −0.25, low-support quartile named in advance); 800-bank composition documented (ground 0.65 %, dynamic 1.9 %, quiet 43 %); stratified-start protocol mandated for every label; feasibility flag as label hygiene; optional LP arm. | |
| N5 F redefined | **done on run0; seed-1 replication queued** | Signed replicate-mean S resolves 6–14 mm effects above a ≈ 0 ± 1 mm identical-physics floor (motor ‡ on 5/6 clips incl. the #44 sign reversal; delay ‡ on the dynamic clips); W1-minus-floor and timing channels agree; contact onsets never move. Instrument calibration only. | `N5_RESULT.md`, `tools/analyze_g1_v2.py`, `reports/G1/run0/g1_v2_*` |
| N6 PhysFrag reprioritised | **done** | Off the critical path; LUCID-correlation is its one surviving test (small N); Featherstone/XPBD, SONIC, differentiable contacts frozen; conformance harness is the durable asset. Motor-strength sign reversal parked as one hypothesis paragraph. | this file, `G1_RESULT.md`, `N5_RESULT.md` |

**The argument now (paper spine):** collapse → the non-floor (ε/(Σq+ε)) → the unsupported attractor
(#44: an airborne retarget in a family the bank barely contains) → grounded repair → composition as
the causal fix (N3) → support-moderation at scale (E3). No bank expansion to "confirm"; N3's
sixteen clips are the confirmation, E3 the scale test.


## Second guidance round (2026-08-18b, `ADVISOR_GUIDANCE_2026-08-18b.md`) — done today

| step | state | result |
|---|---|---|
| 1 env-admits-the-skill | done, sealed as N3 precondition | playback: terminations never fire on the reference; contact LP: kneel supportable in the sim contact model; naive PD-follow falls on *every* clip (no balance feedback) and survives only kneeling offsets — precondition met. Self-collision penalty is charged on reference poses bank-wide (retarget hand–hip interpenetration), not kneel-specific. Null follow-ups pre-listed. `N3_PRECONDITION_env_admits.md` |
| 2a feasibility screen, E3 banks | done | 979 clips (mixed100 + heldout100 + 800), `reports/feasibility_e3/feasibility.csv`; 29/100 held-out clips > 10 % infeasible |
| 2b endpoints feasible-only | done | ordering unchanged; grounded's edge lives on feasible clips (+0.025), ceiling 0.834 |
| 2c full-bank prevalence | **done** — 22.8 % of 10,705 clips have >10 % infeasible frames (ground 39 %, dynamic 59 %; per-source 0.1–100 %) → released-tool + upstream-note path justified. **2026-08-19: this is a one-pipeline number** — a second production bank (BONES-SEED/SONIC, 4,950 clips) screens at 0.14 %, so prevalence is per-corpus and the drafts say so | `reports/feasibility_all/prevalence_report.txt`, `ATLAS_v21_RESULT.md`, `GR00T-WholeBodyControl/docs/prediction_register.md` (P10) |
| 3 E3 addendum v2 | sealed `2c38845b…` | bank-invariant support; all 22 dynamic held-out clips lose support 100→800 → predicted *harder*; named gainers/losers |
| 4 N7 repair | completed; deployment +0.0397 but sealed benefit and coverage gates fail | `N7_RESULT.md`, `reports/N7_result.json` |
| 5 atlas v2.1 | pre-registered `9b1a2c78…`, run | F2 met (transfer 0.567 → 0.609, p = 0.01), F1 not met, F3 half — `ATLAS_v21_RESULT.md` |
| 6 sign-reversal signature | exploratory on run0 | +0.3 mm standing / +15 mm airborne / +27 mm aftermath; generality test filed for the next GPU gap |
| 7 writing | started | `paper/00_outline.md`, four evidence-complete sections, `paper/figures/decomposition.svg` |
| CPU-only rule | **N3 training chain paused**; N5 seed-1 replication landed in a gap window — instrument replicates (r = 0.92; 6/6 sign agreement on |S|>5 mm; #44 motor reversal +12.8 mm, airborne-localised in both seeds) | `N5_RESULT.md` |

## G0 lessons that change how the harness works (all silent, none raised)

1. mjlab's per-env startup DR lives only in `env.sim.wp_model`; anything built
   from the spec is the nominal robot. Mirror expanded fields, then `set_const`.
2. Newton's float32 import path is 1e-7 off mjlab's geometry; MuJoCo's contact
   inclusion is a hard `dist < 0` test, so identical physics ≠ identical
   contacts at rest. Mirror exact geometry for same-solver work.
3. `assign_clips` teleports after `reset()`'s observation; recompute obs.
4. Protocol (forward per substep) is *not* a factor: mjlab_fwdsub = 1.000.

## v3 spikes — status under v4

| # | Spike | State |
|---|---|---|
| S1/G0 | conformance | see above; verdict revised — earlier "contact-event fork = fragility" withdrawn |
| S2 / S2b | Featherstone/XPBD, within/between decomposition | **demoted** (v4: multi-solver disagreement is confounded); after Phase 1, needs solver-neutral joint_f actuation |
| S3 → G1 | clip #44 | re-registered as PhysFrag G1 (paired ±δ counterfactuals, five mechanisms + contact-model axis); S3's contact-anatomy audit carried over |
| S4 | SONIC ONNX conformance | later (v4 keeps SONIC as evaluation target, not training). **2026-08-19: the SONIC feasibility-hygiene training ablation is separately descoped** — its bank screens at 0.14 %, see the state table at the top |
| S5 | wp.Tape | **demoted** (FD paired rollouts primary) |

## Infrastructure

| Item | State |
|---|---|
| Bridge env `bridge/.venv` | done — mjlab + Newton + torch cu128 |
| Harness architecture | mjlab owns obs/policy/terminations; Newton owns physics; MuJoCo state ↔ MuJoCo state via `solver.mjw_data` (`update_data_interval=0`); DR + exact-geometry mirrors; `ctrl_for_substep` hook for the delay axis |
| GPU | shared box; runs go through `run_when_free.sh` (retries on OOM) |

## Application track (v2 queue) — frozen per v4

E2 complete (Branch B); E10 pre-registered, **frozen**; E3/E4 post-Sept-15;
A1–A7 complete; A4 filed upstream (mjlab#1153, whole_body_tracking#73).

## Corrections to the record

1. Clip #44 is not atlas-benign (99.7th pct `nonfoot_ground_frac`; kneel/crawl).
2. v3 E4 telemetry came from a 512-env smoke; campaign-scale numbers in `BRANCH_DECISION.md`.
3. S1's "contact-event fork" was integration error (fixes 8–10 in `S1_RESULT.md`).

## Upstream notes for Newton (not filed)

- `SolverMuJoCo.get_max_contact_count()` → `NotImplementedError` on MuJoCo-C.
- `builder.rigid_gap` defaults to 0.1 m and applies to imported MJCF shapes and the ground plane.
- MJCF import rounds geometry through float32 `wp.transform`; for bit-conformance against a MuJoCo reference the compiled MJWarp model needs the source spec's float64 values.
