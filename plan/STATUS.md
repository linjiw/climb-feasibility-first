# CLIMB / feasibility-first — status against Research Plan v5

Updated 2026-08-19. **v5 (`RESEARCH_PLAN_v5.md`, sealed `4d490cf8…`) is authoritative**: D1
evaluation policy, D2 spin-out, D3 new seals, D4 writing-first window to Sept 15. v4's freeze
discipline continues underneath. Seals manifest: `plan/SEALS_2026-08-19.sha256`.

## Payoff directive (2026-08-21, Linji): approvals and launches

| item | state |
|---|---|
| **E-HYG approved** ("完全批准") → **sealed** `a5494b7c…` + frozen analysis `5f8eb56e…` (4-branch synthetic dry-run passes, incl. the VOLUME branch that catches "just fewer clips") | `plan/PREREGISTRATION_E_HYG.md`, `tools/analyze_ehyg.py`, `plan/E_HYG_FREEZE.sha256` |
| Banks/lists sealed by hash: tier_800_pruned (701 clips; tier_800 is 12.4 % flagged — a *lower bound* vs raw 22.8 %), zs_ground_feasible (60), zs_dynamic_feasible (60) | `bank/tiers/` |
| **N3 + E-HYG chain launched** per "立刻", reconciled with the GPU rule via the gap-gated shared queue (waits ≥ 14 GB, nice priority, never preempts LUCID). Hash-verified resume-safety step PASSED (aug lists, frozen analyses, composed tiers, s2/s3 checkpoints). Order: s2/s3 stratified baselines → N3 keystone → N3 evals → E-HYG. Sentinels throughout. | `tools/n3_ehyg_chain.sh`, `logs/campaign/n3_verify.log` |
| Repair census: 2,442 flagged clips, running (~1.3k done); **2×2 aggregator armed** (severity × auto-recoverable) → fills the main table + companion §8 on sentinel | `tools/aggregate_repair_census.py`, `reports/repair_census/` |
| Narrative: efficiency cliff (3 CPU-h vs 10³–10⁴ GPU-h) + exposure ledger (adaptive mean 48.8 % of draws on the impossible clip) into S1 contributions & companion §8; **three deliverables** named (refeas · contact-projection repair · eval/monitoring protocols) in S1, companion §8, README | commit `f124d71` |
| N7 draft extended: repair (R1) vs prune (R2) arms; seals post-N3 with readout numbers; sign-reversal falsifier carried in | `plan/N7_DRAFT_repair.md` |

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
| psign-prep (P2) | **done** — analysis frozen (sha `db538a9b…`), 3-branch synthetic dry-run passes, mechanism hypothesis + N7 falsifier written; verified no P-SIGN outcomes exist; gap watcher still waiting (GPU ~89 %) | `plan/P_SIGN_PREP.md` |
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
| P-SIGN harness | **built** (`tools/p_sign_gate.py` + sealed analysis `tools/analyze_p_sign.py`); gap watcher armed; GPU currently saturated (30.4/32.6 GB, 89 %, LUCID jobs) so not run |
| Companion note | figure refs wired; prose v0.1 stands; submit-ready pass next |

## Next scheduled

Aug 23–Sept 5: companion figures + submit-ready; flagship §1–2, §7 polish, §10; P-SIGN iff GPU gap.
Sept 5–12: assembly + red-team pass. Sept 15+: N3 relaunch (resume-safety check first: frozen
config re-load, hash check, seeds vs seal) → N7 seal/run → E3 → E10 → E4; GPU-hours measured on N3
re-plan the budget. Dec 1 results freeze.

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
| N3 coverage causality | **pre-registered, training chain launched** (`PREREGISTRATION_N3_coverage.md`, sha `af1b7c9f…`) | ground16 = 16 nearest *feasible* kneel/crawl neighbours (N1 screen); random16 control; arms uniform×2, adaptive×1, random×1; endpoints on **stratified-start** survival (E1: #44 kneel/crawl phase 0.000 → ≥ 0.25 both seeds). Baseline measured. Chain waits for ≥ 14 GB GPU headroom (`logs/campaign/n3_chain.log`). | `tools/eval_stratified.py`, `tools/run_campaign_n3.sh`, `bank/tiers/aug_*16.txt` |
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
| 2c full-bank prevalence | **done** — 22.8 % of 10,705 clips have >10 % infeasible frames (ground 39 %, dynamic 59 %; per-source 0.1–100 %) → released-tool + upstream-note path justified | `reports/feasibility_all/prevalence_report.txt`, `ATLAS_v21_RESULT.md` |
| 3 E3 addendum v2 | sealed `2c38845b…` | bank-invariant support; all 22 dynamic held-out clips lose support 100→800 → predicted *harder*; named gainers/losers |
| 4 N7 repair | drafted, unsealed until N3 reads out | `N7_DRAFT_repair.md` |
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
| S4 | SONIC ONNX conformance | later (v4 keeps SONIC as evaluation target, not training) |
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
