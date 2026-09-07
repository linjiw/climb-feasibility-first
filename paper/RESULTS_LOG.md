# Results log — every paper-bound number and its artifact path (policy: RESEARCH_PLAN_v5)

## 2026-09-06 confirmation allocation and public research-story update

**Measured simulation training integrity and allocation:** at 22:17 EDT, ten of
12 confirmation training runs complete and independently replay over 410 saved
checkpoint states. All seeds 21/22 arms plus R23/D23 pass; U23 is running and A23
queued. No held-out endpoint has opened. Per-seed mean post-warm-up allocation TV:

| Arm | Seed 21 | Seed 22 | Seed 23 |
| --- | ---: | ---: | ---: |
| U | 0.0 | 0.0 | Pending |
| A | 0.029759170164293084 | 0.02933859420427059 | Pending |
| R | 0.08348494896009954 | 0.0824919974124211 | 0.08233284378057906 |
| D | 0.08391068947163956 | 0.08586509252074585 | 0.08398385293466296 |

Each complete run has 41 replayed states and zero invalid/censored events. The
TV mean uses 37 states from iteration 400 through 3999. Allocation histories are
correlated within runs and establish exposure contrast, not tracking improvement.
Public artifacts: `docs/assets/progress-2026-09-06/research_snapshot.json`,
`allocation_snapshots.csv` and `confirmation_allocation.png`/`.pdf` in that directory.
Original gate paths and SHA-256 identities are included in the JSON export.

**Measured development / pending outcomes:** the public development summary records
completed D31/D32 calibration, freeze prerequisites, H1 CPU evaluation/provenance
and CPU lifecycle checks. It does not establish full H1 benefit, forgetting recovery,
physical robustness or hardware transfer. Existing repair and E4 findings retain
separate exploratory/sealed labels. Scope, claim-to-evidence map, statistical
contract and next research decisions: `plan/PAGES_RESEARCH_STORY_2026-09-06.md`.

**2026-09-05 manuscript usage update:** E4 calibration now appears in Results §5.4;
its values remain measured 50-iteration calibration, not confirmation endpoints.
E3 now reports the existing all-26-candidate p95-of-per-clip-p95 root-velocity
deviation 1.210 m/s and root-acceleration deviation 34.91 m/s² from
`reports/dfrp_v1_exact_panel/iter1/result.json` → `fidelity` (measured reference
distortion; not tracking error or a qualification threshold).
The earlier one-seed exact-support pilot's 22,321 common-survivor frames have
adaptive-minus-uniform body-position error −4.20 mm (95% unit-bootstrap interval
[−6.63,−1.90] mm) and anchor-orientation error −0.02795 rad
([−0.03966,−0.01628] rad), from `reports/segment_v2_pilot/result.json` and
`tools/analyze_segment_pilot.py`; exploratory, insufficient allocation separation
(TV 0.014), no ALP attribution or survival-equivalence claim.

> **Corrections 2026-08-19:** three numbers in this log were wrong and are fixed in place —
> the exposure attribution (C1), the saturation-at-fall replicate count and mean (C2), and
> the per-actuator identity, now withdrawn (C3). Evidence, ground truth and reproduce
> commands: [`paper/CORRECTIONS_2026-08-19.md`](CORRECTIONS_2026-08-19.md). The two
> artifacts involved now have generators (`tools/analyze_wasted_exposure.py`,
> `tools/analyze_sat_at_fall.py`); both were hand-computed before.

| number(s) | where used | artifact path | class |
|---|---|---|---|
| top-1 mass 0.884/0.870/0.893; mean entropy 0.38–0.40 (adaptive); 0.60–0.62, top-1 0.57–0.70 (grounded) | §3, §4, F2 | `reports/A5_coverage_dose.json` | sealed-confirmatory |
| same attractor clip 3/3 seeds ×2 arms; share of concentrated iters 0.28–0.53 | §3 | `reports/A7_attractor.json` | sealed-confirmatory |
| endpoint 0.780/0.810/0.825 ± sd; AULC 0.640/0.698/0.696; paired deltas, d_z | §3, §4 | `reports/campaign_summary_3arm.json` | sealed-confirmatory |
| feasible-only strata 0.811/0.834/0.859; infeasible 0.705/0.750/0.741; grounded edge +0.025/−0.009 | §4, §6 | `reports/N_atlas_v21.json` (endpoints_2b), `plan/ATLAS_v21_RESULT.md` | exploratory → D1 primary going forward |
| non-floor derivation ε/(Σq+ε); upstream filings | §3 | `plan/RESEARCH_PLAN_v2.md` E3 row; mjlab#1153; whole_body_tracking#73; `reports/A4_upstream_issue.md` | sealed-confirmatory |
| conformance after fixes: 1.000/1.000 vs 1.000/1.000, Δerr −0.5/−0.8 mm; #44 0.000 vs 0.000 (+1.0 mm); |Δq̇| ≤ 3e-5 | §5.1, A1 | `reports/S1_KIT1226_n32_absorb.json`, `reports/S1_clip44_n32_absorb.json`, `plan/S1_RESULT.md` | confirmatory (post-fix) |
| Newton 1.5 exact-unit recertification: one easy + one contact-rich hash-bound DFRP v1 unit; placement/first-observation/first-action deltas 0; 48 resynchronized substeps `|Δq|=|Δq̇|=0`; exact contact/termination timing; two independent repeats with zero dispersion. Seven live-model import residuals precede the exact mirror. | future companion appendix / Phase N gate | `reports/newton15_recert/{UNIT_SELECTION.json,result.json,trajectories.npz,COMPLETED.json}`, `plan/NEWTON15_RECERT_RESULT.md` | unsealed measured conformance; not a policy-benefit or predictive result |
| Newton no-training predictive gate (sealed, addendum 1): three-axis fragility vector from the uniform policy does **not** predict held-out degradation beyond `infeasible_frac` + six reference-kinematic controls — adaptive partial ρ +0.141 (one-sided within-clip permutation p 0.158; threshold +0.25 / 0.05), LOCO ridge lift −0.006 (threshold +0.05); grounded ρ +0.022, lift −0.036; 40 of 42 units (units 9, 46 excluded for paired-alive < 0.80); per-axis raw ρ delay +0.42, clamp +0.27, contact −0.03 (adaptive). All instrument checks pass (zero dispersion, cross-condition Δ 0, clamp realized 12/14/13 units). | companion appendix / flagship §8 one sentence: G3 closed | `reports/newton15_pred/result.json` (`ff7e5670…`), `probe/effects.csv` (`d863abff…`), `plan/NEWTON_PRED_RESULT.md` | sealed measured null on valid data; G3 never runs |
| pre-fix forks 0.656/0.594/0.500/0.594/0.500 | A1 | `reports/S1_KIT1226_n32*.json` | withdrawn-context |
| G1 ratios (1.30–2.16×), floor ratios (≤3.2×), termination fragility 0 everywhere, failure-time agreement ≤ 0.1 s | §5.2 | `reports/G1/run0/g1_summary.json`, `plan/G1_RESULT.md` | sealed-confirmatory (negative) |
| N1: descent 0.75–1.75 s airborne, ~329 N ≈ weight (327 N) unsupported in 86 % of frames; rise 8.0–8.5 s; kneel supportable (0 N residual, both contact models); control supported every frame | §5.3, §6, F3 | `reports/N1_clip44_knee_id.json`, `reports/N1_CMU76_knee_id.json`, `plan/N1_RESULT.md` | confirmatory (measurement) |
| family: 20/40 neighbours > 10 % infeasible (12 was an informal cut, corrected) | §5.3 | `reports/N3_candidate_feasibility.json`, `plan/GLOBAL_EVAL_ADDENDUM.md` | measurement + correction |
| stratified-start baseline: #44 0/0/0/0 at 1–6 s offsets, 1.00 at 8 s; family fails in ground segments | §5.3, §8.1, F3 | `reports/N3_baseline_uniform-s1_strat.csv` | measurement |
| prevalence 22.8 % (>10 % frames); ground 39 %, dynamic 59 %, locomotion 25 %, quiet 13 %; sources 0.1–100 % | §6, F4, companion | `reports/feasibility_all/prevalence_report.txt` (+ sentinel `COMPLETED`) | measurement — **one pipeline only** (AMASS → whole_body_tracking → G1); never state it as a rate for retargeted banks generally, see the cross-bank row below |
| eval contamination 29/100 | §6, D1 seal | `reports/feasibility_e3/feasibility.csv` | measurement |
| P-TAX: median tax 0.126; 53 % > 0.1; heldout partial ρ −0.039/−0.151/−0.089; 0/3 sealed rule | §6 | `reports/P_TAX_tax_fractions.csv`, `reports/P_TAX_result.json`, `plan/P_TAX_RESULT.md` | sealed null |
| policy-consensus ρ 0.832; intrinsic transfer 0.567/0.579; +support +0.00–0.03 (n.s.); +feasibility 0.609/0.616/0.580/0.633, perm p 0.010/0.030/0.045/0.015; direct ρ(difficulty, infeas) +0.37/+0.48/+0.50 | §7, F5 | `reports/A3_atlas_transfer.json`, `reports/N2_atlas_support.json`, `reports/N_atlas_v21.json` | sealed splits per table |
| support-residual ρ +0.605/+0.544 (kNN), −0.578/−0.561 (density) | §7 | `reports/N2_atlas_support.json` | confirmed half of N2 |
| bank-invariant support change 100→800: all 22 dynamic clips lose; category table; named lists | §8.3 | `reports/support_change_heldout100_100to800.csv`, `plan/PREREGISTRATION_E3_addendum_v2.md` | sealed predictions |
| N5: floor ≈ 0 ± 1 mm; motor +11.5/−2.6/−4.6/−10.9/−0.8/−14.2 mm (run0); delay +11.9 CMU_35; termination shift −0.51 ± 0.14 s (delay, #44); contact-onset ≤ 0.03 s | §9, A2 | `reports/G1/run0/g1_v2_summary.json`, `plan/N5_RESULT.md` | calibration (exploratory label) |
| N5 replication: r = 0.92; 6/6 sign agreement > 5 mm; #44 motor +12.8 [+11.2,+14.2]; windows +0.3/+15.0/+26.8 (s0), −1.4/+16.0/+20.4 (s1) | §9 | `reports/G1/run1_seed1/g1_v2_summary.json`, `plan/N5_RESULT.md` | replication (exploratory label) |
| oracle precondition: playback survives all (err 4–13 mm); PD-follow dies on all incl. easy; kneel offsets its only survivals | §8.1 | `reports/N3_env_admits_*.csv`, `plan/N3_PRECONDITION_env_admits.md` | precondition |
| refeas demo: hover clip flags 45 % airborne/infeasible, 1.77 s free-fall-equivalent | companion | `refeas/examples/demo_hover_brief.json` (repo tag v0.1.0) | tool validation |
| ICRA F1 (CLIMB screen → DFRP route/repair → exact-support ALP system pipeline, with feasibility × support × intrinsic factorization) | ICRA §1/§3, F1 | `paper/figures/f1_feasibility_first.py` → `.png/.pdf`; exact-support counts from `reports/g_segment/unit_table.json`; DFRP qualification counts from `reports/dfrp_v1_exact_panel/iter1/result.json` | method schematic + measured artifact callouts; 22/26 is a stratified-panel qualification rate and 1,184/368,951 are support-table counts; **no ALP policy-benefit claim** |
| ICRA F2 (separate bank-scale rates + same-clip implementation agreement) | ICRA §5.2, F2 | `paper/figures/f2_bank_scale.py` → `.png/.pdf`; data `reports/feasibility_all/feasibility.csv`, `reports/feasibility_sonic/hygiene_screen.csv`, `reports/feasibility_xcheck/agreement.csv` | measured figure; full-bank bars have separate denominators and confounded pipelines; 40-clip panel is flag-enriched, not prevalence; **no causal retargeter claim** |
| F2 figure (collapse timeline + concentration bars) | §3, F2 | `paper/figures/f2_collapse.py` → `.png/.pdf`; data `reports/campaign/*.csv`, `reports/A5_coverage_dose.json` | figure |
| F4 figure (prevalence category × source) | §6, companion Fig 2 | `paper/figures/f4_prevalence.py` → `.png/.pdf`; data `reports/feasibility_all/feasibility.csv` | figure |
| F5 figure (transfer lift with perm baselines) | §7 | `paper/figures/f5_transfer.py` → `.png/.pdf`; data `reports/N2_atlas_support.json`, `reports/N_atlas_v21.json` | figure |
| citation verification (20/20 external refs live-checked 2026-08-26; LUCID internal and flagged) | §2 | `paper/CITATION_CHECK_2026-08-26.md` | verification |
| eval depression: flagged clips 6.0/7.5/8.4 pts below all-clips aggregate (8.4/10.6/11.8 below feasible stratum) per arm — supersedes the erroneous "6–11" | §6 companion §5 | `reports/N_atlas_v21.json` endpoints_2b; correction logged `paper/companion/REVIEW_2026-08-20.md` MAJOR-2 | measured (corrected) |
| gap sensitivity: 3 cm flags control 42 % (bank clearance offset); 10 cm degenerates (#44 descent reads 0); ½-weight bound stable 15.1/13.1/12.5 % at 0.25/0.5/0.75×W | companion §2 | `reports/N1_gap_sensitivity.json` | measured |
| Extreme-source 5+5 hand-check, selected at strict-flag severity quantiles 0/25/50/75/100: CNRS **5/5 ingest** ordinary walks, median lowest-geometry clearance 5.1/6.1/7.4/8.4/9.7 cm and longest >6 cm runs 1.34–3.76 s; Transitions **3/5 ingest + 2/5 content + 0/5 scene-mismatch**, with ordinary sideways running/run-backwards and standing punch among the ingest cases. | companion §4, A3, advisory | `reports/feasibility_extremes/{clips.csv,clearance_trace.csv,extreme_source_panel.png,COMPLETED.json}`; narrative `reports/upstream_drafts/CNRS_AUDIT.md`; script `tools/audit_extreme_sources.py` | measured reviewer check; severity-stratified inspection, not a source-prevalence estimator |
| per-seed Δ(uniform−adaptive) +0.0300/+0.0275/+0.0300 (endpoints 0.8137/0.8125/0.8025 vs 0.7837/0.7850/0.7725) | §3 | recomputed from `reports/campaign/*_it3999.csv`; sweep row (b) `paper/CONSISTENCY_SWEEP_2026-08-20.md` | sealed ✓ (per-seed restatement) |
| wasted exposure: adaptive mean **top-1 clip mass** 48.8 % (peak 87–89 %) — of which the impossible clip accounts for ≥ 21.9 %; it is top-1 in 34 % of logged iterations and in 2 of 3 seeds the peak belongs to another clip; clip-uniform 25 % draws / 6.1 % frames to flagged (mixed100); bank 22.8 % clips / 27.4 % duration / 9.8 % mean frames | payoff plan §0, flagship §6 (candidate) | `reports/wasted_exposure_accounting.json`; regenerated by `tools/analyze_wasted_exposure.py` | measured — **corrected 2026-08-19**: the shipped JSON's `exposure_to_impossible_clip_mean` is byte-identical to `mean_top1_mass`, i.e. a copied key, not an independent measurement. The share on the impossible clip is bracketed [21.9 %, 48.8 %]. |
| effort saturation: 0/29 actuators in the supported phase; ≥ 4/29 at ≥98 % force within 0.6 s of losing foot support in 8/8 replicates, exactly 5/29 (17.2 %) in 7/8 (world 7 is 4/29 = 13.8 %); mean 16.8 % | companion §5b, flagship §6 | `reports/effort_sat_at_fall.json` (from `reports/G1/run0/armA.npz`); regenerated by `tools/analyze_sat_at_fall.py` | measured — **corrected 2026-08-19**: was "5/29 (17.2 %) … 8/8"; 17.2 % is a per-world value, the mean is 16.8 %. Per-actuator identity is **not** recoverable from the artifact — `tools/g1_clip44_gate.py:242` collapses the actuator axis before storage. |
| repair operator validation: #44 0.13→0.00 (8.2 cm); family 27_5 0.21→0.00; worst 39_8 0.37→0.20 (needs stronger op); CNRS walk 0.66→0.01 (13.9 cm); Transitions jump correctly refused; feasible control no-op | payoff plan §2, N7 draft | `tools/repair_contact_projection.py`; per-clip `/tmp/repval_reports` → durable copies in `reports/repair_census/json/` as census covers them | measured |
| tier_800 contamination 12.4 % (99/800) → pruned bank 701 clips | E-HYG seal, §8 slot | `bank/tiers/tier_800_pruned.txt` (sha 4cfb5aea); flags `reports/feasibility_e3/feasibility.csv` | measured |
| N3: #44 feasible-phase survival base s1/s2/s3 0.000/0.031/0.188 → ground16 s1/s2 **0.750/0.750**; random16 0.000; analyzer E1∧E4 true, but adaptive E2 regression (heldout Δ −0.0346; easy control 0.857) triggers the preflight stop; E3 max top-1 after 2000 = 0.784 (fail); descent 1.000/0.688 (prediction miss) | §8, F6 | `reports/N3_result.json`, `reports/N3_*_strat.csv`, `reports/N3_adaptive-mixed100g16-s1_telemetry.csv`, `plan/N3_RESULT.md` | sealed mixed outcome — arithmetic gate passes; unqualified causal interpretation stopped by E2 |
| E-HYG: feasible heldout 0.918→0.907, Δ **−0.0101**, one-sided permutation p=0.951; all-heldout Δ −0.0132; worst decile/best half −0.0153/−0.0035; ZS-ground Δ −0.0354 inside bracket; decision P1∧P2 false | §8, companion §8 | `reports/E_HYG_result.json`, six `reports/E_HYG_uniform-amass800{,p}-s1_*_strat.csv`, `plan/E_HYG_RESULT.md` | sealed null |
| P-SIGN: family generality 7/12 (need 8), clean controls 4/12 (need 8), airborne localisation 2/7; joint rule false | §3 companion, §6, §9 | `reports/P_SIGN/run0/p_sign_summary.json`, `reports/P_SIGN/run0/analysis.log`, `plan/P_SIGN_RESULT.md` | sealed fail — runtime-detector claim rejected |
| repair operator validation placeholder (see the corrected census and DFRP rows below) | — | superseded by `reports/dfrp_v0/census/summary.{json,md}` and `reports/dfrp_v1_exact_panel/iter1/result.json` | superseded; no claim |
| repair census: legacy operator recovers 1,606/2,442 strict-flagged clips (65.8 %) through 15 cm; historical directory summary is 1,607/2,443 because it includes one feasible no-op control (C4). Historical-directory strata: 10–25 % 73.1 %, >25 % 61.7 %, ground 68.1 %, quiet 80.9 %, dynamic 51.2 % | companion §8, payoff plan §2, flagship §6/§8 candidates | strict set `reports/dfrp_v0/census/summary.{md,json}`; historical directory `reports/repair_census/summary.{md,json}`; correction `paper/CORRECTIONS_2026-08-21_DFRP.md` | measured, corrected |
| **cross-bank prevalence**: BONES-SEED (SONIC) 4,950 clips — 7 (0.14 %) > 10 % infeasible, 111 (2.24 %) > 10 % airborne, 5 (0.10 %) > 20 % infeasible; flagged duration 0.09 %; 7 `kneeling_loop_*` at airborne 1.000 / infeasible 0.000; cost **0.145 CPU-s/clip = 0.84 ms per screened frame** (the register's measured figure; the durable 2026-08-26 reproduction took 179.8 s wall on 8 workers). Threshold sensitivity: at `> 0.05` it is 29 (0.59 %) infeasible / 225 (4.55 %) airborne; at `> 0.20`, 5 / 32. The seven flagged, with `infeasible_frac`: `jump_on_50cm_002` 0.658, `kick_back_001` 0.472, `jump_off_front_50cm_R_002` 0.379, `jump_off_50cm_R_001` 0.366, `jump_off_front_50cm_001` 0.353, `high_jump_R_003` 0.138, `burpee_002` 0.136. Against this bank's 22.8 % / 23.5 % / 27.4 % (10,705 clips) | §1, §2, §6, §10, A3, companion §4 + abstract | prediction + result: `GR00T-WholeBodyControl/docs/prediction_register.md` (P10, registered before the original run, consequence pre-committed); durable 4,950-row screen `reports/feasibility_sonic/hygiene_screen.csv` (sha `c28fccb…`) + `reports/feasibility_sonic/COMPLETED.json` (0 failures; μ 0.7, gap 0.06, ½-weight, MJCF `g1_29dof_rev_1_0.xml` sha `15a330f1…`); screen `gear_sonic/research/hygiene/screen.py` | measured (pre-registered, **confirmed**); durable reproduction matches every registered threshold count and the flagged-duration headline |
| Cross-implementation same-clip check: deterministic stratified 20 BONES-SEED (7 native-flagged + 13 sampled feasible) + 20 AMASS (10 native-flagged including #44 + 10 sampled feasible), selection seed 260826. Across all 40, CLIMB vs SONIC `infeasible_frac` Spearman ρ **0.9836** (p 7.16e−30), `airborne_frac` ρ **0.9974** (p 4.13e−45); strict `infeasible_frac > 0.10` agreement **39/40 = 97.5 %**, κ **0.9485** (both 16, neither 23, SONIC-only 1, CLIMB-only 0). By bank: AMASS 20/20, ρ 1.000 infeasible / 0.998 airborne; BONES 19/20, ρ 0.962 / 0.989. The sole threshold disagreement is `burpee_002__A362_M` (CLIMB 0.019 vs SONIC 0.136). | ICRA abstract / E2 / result §2; A3; companion §4 | `reports/feasibility_xcheck/{selection.csv,agreement.csv,summary.json,COMPLETED.json}`; adapter/aggregator `tools/feasibility_xcheck.py`; model and implementation hashes in sentinels | measured reviewer check (not pre-registered); stratified agreement panel, not a prevalence estimator or retargeter-causal comparison |
| segment- vs clip-level curation on `tier_800`'s 99 flagged clips (20.2 min of 152.4 min): guard 0 s → 12.5 min (61.7 %), 584/1,259 bins, 3/99 clips lost; guard 1.0 s → 5.8 min (28.9 %), 305/1,259 bins, 26/99 lost. Bank-level: prune discards 13.3 % of duration, curation returns 8.2 % / 3.8 %. Cost 99 clips in 45 s wall on 6 CPU workers | §6, companion §8 | `reports/segments_tier800/segments_guard0.csv`, `reports/segments_tier800/segments_guard1.0.csv`, per-clip `reports/segments_tier800/full/`; reducer `tools/screen_segments.py`; derivation `plan/FGAS_DIRECTIVE_2026-08-19.md` | measured — duration claim only (no training arm has consumed curated segments); `--min-seg-s 1.0` and strict bin eligibility are choices, not measurements |
| FGAS CPU projection on mixed100 guard-0 sidecars: joint hard-rejected start mass 0.28984 measure-only, 0 hard, 0.10269 soft under a flat clip distribution | apparatus / §8 | `climb/eligibility.py`; `tests/test_fgas_sampling.py`; `plan/PREREGISTRATION_FGAS.md` | measured apparatus; the completed adaptive run shows this flat projection is not a late-run bound |
| FGAS soft guard-0, 3 matched seeds: feasible-hard20 0.7586→0.7390, Δ **−0.0196**, hierarchical bootstrap CI [−0.0497,+0.0134]; feasible-heldout Δ −0.0123; late top-1 flagged 0.861, top-1 mass 0.501, hard-rejected start mass **0.199** (gate `<0.15` fails). Final telemetry reconstructs within 0.0022; one 0.702-eligible clip contributes 0.194/0.118/0.070 rejected mass across seeds | §8 FGAS | `reports/FGAS_result.json`, `reports/FGAS_diagnosis.json`, `plan/FGAS_RESULT.md`; frozen bundle `reports/FGAS/_frozen/20260820T152154Z/` | sealed primary **not confirmed; implementation gate fails** — this clip-mean soft formulation is not validated; no broad segment-FGAS claim |
| N7 repaired800 composition: raw 3.923% → repair-all 0.903% duration-weighted infeasibility at fixed N=800; 10 residual and 12 over-offset clips remain labelled | §8 N7 | `reports/repaired800/manifest.json`; `plan/REPAIRED800_COMPOSITION.md`; `plan/N7_DRAFT_repair.md` | measured bank composition |
| N7 one-seed 2×2: deployment R/repaired − K/raw **+0.0397**, motion-bootstrap CI [+0.0153,+0.0658] (misses +0.05 SESOI); R/raw − K/raw −0.0036; K/repaired − K/raw +0.0233; interaction +0.0200. Heldout100 −0.0104 (point guard passes); ZS-ground R−K −0.0199 and R−P +0.0155 (coverage fails); overall false | ICRA E3 / result §3; flagship §8.2 | `reports/N7_result.json`, six `reports/N7/*.csv`, `plan/N7_RESULT.md` | sealed joint fail; motion bootstrap is not seed uncertainty |
| N7 post-outcome integrity: `heldout100` contains 8 tier800 training motions; disjoint92 delta −0.0122, CI [−0.0316,+0.0012], feasible-disjoint68 −0.0137, CI [−0.0391,+0.0024]. Deployment delta by repair stratum: certified78 +0.0160, over-budget11 +0.2305, residual10 +0.0143 | §8.2 limitation / v2 design | `reports/N7_posthoc_audit.json`, `tools/diagnose_n7_result.py`, `plan/N7_RESULT.md` | exploratory post-outcome; frozen decision unchanged |
| DFRP v0 legacy routing: 644/2,442 (26.4 %) strict-flagged clips fit the 8 cm primary displacement budget; 962 (39.4 %) additional clips fit 8–15 cm; all are legacy root-only and qualification-incomplete, so zero are training-eligible. Two-clip root+IK development view: 1 feasible byte-identical no-op + 1 repair 0.1010→0.0303 infeasible, 39.8 mm root, 0.992 mm contact residual, 76 legal starts total | DFRP direction / future §8 method | `reports/dfrp_v0/{census,dev_panel}/`, `plan/DFRP_V0_RESULT_2026-08-21.md` | unsealed measured implementation; no policy outcome |
| DFRP v1 frozen exact panel: 22/26 flagged candidates (84.6 %) pass residual ≤5 %, root ≤8 cm, joint-limit, IK-residual ≤10 mm, hash-bound exact-support, and legal-start gates; 4/4 feasible controls are byte-identical/ready. Curated view: 26 clips, 36 units, 10,561 legal 50-step starts; median/p95 CPU runtime 2.57/6.29 s per clip. Two residual-infeasibility and two IK-qualification failures are excluded. | ICRA E3 / result §3; DFRP direction / flagship future §8 method | `reports/dfrp_v1_exact_panel/iter1/{result.json,curated_manifest.json,unit_table.json}`, `plan/DFRP_V1_EXACT_PANEL_RESULT_2026-08-21.md` | unsealed measured implementation on a stratified panel; not a bank-wide recovery rate or policy outcome |
| Phase-G endpoint-blind G2 manipulation calibration: 2/12 screen candidates pass; deterministic selection rho 0.40 / lambda 0.05 has screen TV 0.1310/0.1063/0.0865 (mean 0.1079), then independent-seed TV 0.1292/0.1045/0.0831 (mean 0.1056), minimum 700.1 effective units, maximum top-1 0.0134, zero invalid/censored events, and saturation 0.2365 | Phase-G preregistration / future ICRA experiment | `reports/g_segment/calibration/result.json`, 39 hash-bound ledgers, `plan/G2_CALIBRATION_RESULT_2026-09-04.md` | unsealed measured manipulation only; no evaluator or policy-performance endpoint read; no policy-benefit claim |


## 2026-09-05 execution addendum: E4 disposition and next candidate

These entries supersede earlier pending labels for the named experiments only.
No sealed artifact, endpoint definition, or prior outcome has been amended.

| Number or disposition | Use and limitation | Artifact | Class |
| --- | --- | --- | --- |
| E4 seed-1 mean post-warm-up TV 0.0296587 < 0.05; both 4,000-iteration arms complete; `not_tested` | Future E4 results wording; policy endpoints unopened, seeds 2–3 stopped. This is not a policy null. | `reports/g_segment/confirmation/seed1/manipulation_result.json` | sealed manipulation decision |
| Absolute-floor focus-normalizer share 64.3% at iteration 500 → 93.6% at 3999; relative κ=2 replay mean TV 0.0854, range 0.0560–0.1087, eight snapshots | Motivation for separate candidate; fixed recorded histories cannot establish live allocation or learning benefit. | `reports/g_segment/confirmation/allocation_diagnosis.json` | measured replay plus exploratory counterfactual |
| DFRP one-policy, 26 clips, 656 paired conditions per arm: clip-weighted TrackingScore raw 0.392505 → repaired 0.391502, Δ −0.001003, clip-bootstrap 95% CI [−0.008588,+0.008020]; raw/repaired trial successes 409/656 and 397/656 | Future repair follow-up; no aggregate gain established. Clip-weighted score and trial-level success denominators differ. Short windows, two training-overlap clips, unchanged-control numerical differences, and one policy limit scope. | `reports/dfrp_policy_validation_2026-09-05/result.json`, `strata.all.all_conditions` | measured exploratory fixed-policy deployment comparison |
| Relative-progress R0: seed 11, 8 environments, 20 iterations, 184 completed trials, 0 invalid/censored events, 17 s; strict smoke pass | Implementation evidence only; incomplete history gives approximately zero TV. R1 launched with 512 environments / 4,000 iterations; sustained manipulation and policy benefit remain pending. | `reports/relative_progress_2026-09-05/smoke_result.json`, `smoke_s11.log`, `study_s11/design.json` | measured exploratory lifecycle smoke; long-run result pending |


## 2026-09-05 R1 completed manipulation result

| Number / disposition | Scope and limitation | Artifact | Class |
| --- | --- | --- | --- |
| Relative ALP seed 11: full 4,000 iterations / 512 environments; 41 checkpoints, 37 post-warm-up snapshots; mean TV 0.0832114, individual range [0.0489606,0.1082347]; min effective units 616.2498; max post-warm-up unit/clip mass 0.0177383/0.0184985; final saturation 0.737331; 1,087,814 completed trials, zero invalid/censored events; manipulation pass | Replaces pending R1 label only. One exploratory seed; no tracking or rank-informativeness claim. TV band applies to the run mean, not every snapshot. The earlier E4 uses a different seed and is not a paired performance comparator. | `reports/relative_progress_2026-09-05/study_s11/long_result.json`, `seed11_recovery_verification.json`, `continuation_recovery/seed11_figure/` | measured exploratory manipulation |
| R1 elapsed training 2,680 s (0.744444 GPU-hours elapsed); shared-GPU baseline/peak total 1,382/12,841 MiB | Shared GPU, including other processes; not isolated allocator overhead, process memory or throughput benchmark | `reports/relative_progress_2026-09-05/study_s11/long.log` | measured execution cost |

The first continuation stopped before seed 12 because it resolved relative smoke
ledger keys to absolute paths. Both original smoke/long results replay exactly
when path spelling is preserved; the corrected wrapper changes no scientific
threshold or checker. Failed source/design/log are retained. Seed 12 remains
queued, with independent replication and policy benefit pending; see
`plan/RELATIVE_PROGRESS_R1_RESULT_2026-09-05.md`.

## 2026-09-05 R1 sampler-signal diagnostic

These descriptive numbers are recorded for possible future paper use; they do
not change a sealed result or establish policy benefit.

| Number / disposition | Scope and limitation | Artifact | Class |
| --- | --- | --- | --- |
| Declining estimated success receives 0.4660473 of positive excess sampling mass | Unweighted mean of 37 post-warm-up snapshot fractions in R1 seed 11; denominator is positive probability mass above deployment prior, not all trials. Forgetting and estimation noise are unresolved alternatives. | `reports/relative_progress_2026-09-05/rank_signal_s11/result.json` | measured exploratory sampler diagnostic |
| Adjacent absolute-progress ranking Spearman correlation 0.4223621; progress/failure 0.2814350; progress/recent-attempt count 0.4607236 | Means over 36 adjacent snapshot pairs or 37 within-snapshot correlations, respectively. Correlated observations, endogenous exposure, no inferential or independent-replication claim. | `reports/relative_progress_2026-09-05/rank_signal_s11/result.json`, `snapshots.csv` | measured exploratory correlations |
| Fixed D allocation on R histories has mean TV 0.0859453 | Holds R histories fixed; not a D training result and not used for profile selection. Actual D seeds 31/32 remain pending. | `reports/relative_progress_2026-09-05/rank_signal_s11/result.json` | exploratory counterfactual replay |

Definitions, execution queue and remaining confirmation requirements:
`plan/RELATIVE_SIGNAL_DIAGNOSIS_2026-09-05.md`. No diagnostic changes the
queued independent replication, baseline profile, or policy endpoint rules.

## 2026-09-05 R2 lifecycle and execution addendum

| Number / disposition | Scope and limitation | Artifact | Class |
| --- | --- | --- | --- |
| Relative ALP seed-12 smoke: 8 environments, 20 iterations, 192 completed trials, zero invalid/censored events, 17 s, strict `smoke_pass` | Lifecycle evidence only. Full 512-environment / 4,000-iteration replication launched 18:30:27 EDT; complete manipulation and policy benefit remain pending. | `reports/relative_progress_2026-09-05/continuation_gate_retry/study_s12/smoke_result.json`, `smoke.log`, `long_command.json` | measured exploratory simulator smoke |

The preceding `continuation_recovery` attempt stopped at a GPU poll miss before
seed-12 training launched. It is an operational stop, not a manipulation failure
or discarded seed. Original logs/design/terminal records remain preserved.
`plan/RELATIVE_CONFIRMATION_READINESS_2026-09-05.md` documents the unchanged
restart and developing secondary-analysis definitions. Synthetic campaign test
results do not supply any new paper-bound policy-performance number.

## 2026-09-05 completed relative-ALP replication and input audit

| Number / disposition | Scope and limitation | Artifact | Class |
| --- | --- | --- | --- |
| Seed 12: 4,000 iterations / 512 environments; 41 snapshots, 37 post-warm-up; mean TV 0.0827283432, range [0.0507759,0.1013988], minimum effective units 618.611481, maximum unit/clip mass 0.0223513/0.0223513, final saturation 0.7331081, 1,086,192 completed trials, zero invalid/censored events; manipulation pass | Both planned development seeds now pass and reproduce. Sustained allocation only; policy utility, ranking utility and transfer remain pending. Probability extrema/effective-unit minimum are post-warm-up. | `reports/relative_progress_2026-09-05/replication_review.json`, `continuation_gate_retry/study_s12/long_result.json` | measured exploratory simulation replication |
| Seed-12 declining-estimate share of positive excess mass 0.4680896; adjacent rank correlation 0.4029245; progress/failure correlation 0.2747052; progress/new-attempt correlation 0.4469226; D fixed-history TV 0.0849016 | Unweighted correlated-snapshot summaries: 37 excess/failure/TV snapshots, 36 adjacent-rank/attempt intervals. Positive excess mass is not all training draws; D replay is not D training. | `reports/relative_progress_2026-09-05/rank_signal_s12_corrected/result.json`, `replicated_rank_diagnostic.csv` | measured exploratory diagnostics and counterfactual |
| Full R1/R2 elapsed training: 2,680 + 3,373 = 6,053 s, 1.681389 elapsed GPU-hours | Two full probes only; excludes smokes, waiting, engineering, evaluations and prior studies. Shared device, not GPU-active time, isolated overhead, or energy. The intervening gate miss launched no training. | `reports/relative_progress_2026-09-05/replication_execution_cost.json` | measured scoped execution cost |
| 900 motion identities verified; 800 training / 100 evaluation, zero content overlap; 2,800 conditions reconstructed from current headers | CPU reference-input audit only; does not certify confirmation execution or policy performance. | `reports/relative_progress_2026-09-05/replication_reference_audit.json` | measured input verification |

**Corrections without changed measurements:** the earlier seed-11 attempt-count
correlation 0.4607236 averages **36** valid adjacent-snapshot intervals, not 37;
the first post-warm-up snapshot has no predecessor. The seed-12 diagnostic's
initial figure title incorrectly said “Seed 11”; its JSON already said seed 12.
The original figure/source are preserved, with an equality-checked caption
correction in `rank_signal_s12/caption_correction.json`. Use the corrected
seed-12 figure. No scientific gate, rank statistic, or sealed result changed.


## 2026-09-05 confirmation implementation disposition

The fixed confirmation trainer, checkpoint ledger and scheduler are implemented;
the actual draft passes CPU source/configuration/reference preflight. The draft
keeps confirmation disabled. New seed-51 entrypoint smokes are queued after
fixed D calibration; simulator validation, the complete new frozen-contract
integration audit, prospective freeze and policy utility remain **pending**.
No paper-bound policy-performance number changes in this update. Synthetic
tests and configuration audits are implementation evidence only. See
`plan/RELATIVE_CONFIRMATION_EXECUTION_2026-09-05.md` and
`reports/relative_progress_2026-09-05/confirmation_execution_verification.json`.


## 2026-09-05 evaluator compatibility correction

**Measured implementation defect:** the sealed evaluator rejects the sealed
Phase-G condition file because it contains two additional provenance fields;
all shared fields and all 2,800 conditions match exactly. The prior reference
input audit did not certify the evaluator CLI. A separate adapter validates
the unchanged sealed file, complete payload and provenance, then reuses the
sealed rollout implementation. New evaluation metadata binds the adapter.
No scientific condition, sealed source, sealed manifest or paper-bound policy
number changes. Strict-contract synthetic integration is implementation evidence;
actual benchmark execution and policy utility remain **pending**. The previous
seed-51 queue was superseded before any smoke launched. Details and preserved
identities: `plan/RELATIVE_EVALUATOR_ADAPTER_2026-09-05.md`.


## 2026-09-05 completed four-arm development lifecycle

| Number / disposition | Scope and limitation | Artifact | Class |
| --- | --- | --- | --- |
| U/A/R/D seed-41 smokes: 191/183/177/198 completed trials; eight environments, 20 iterations each; all four smoke passes with zero invalid/censored events | Complete source-bound sampler/checkpoint replay reproduces. Short-run counts are lifecycle counters, not policy comparisons. | `reports/relative_progress_2026-09-05/development_smoke_review/result.json` | measured development simulation |
| U/A/R/D elapsed smoke job time: 20/21/18/16 seconds; total 75 seconds, 0.020833 elapsed GPU-hours | These four jobs only, shared device; excludes queue time, CPU checks and all other studies. Not GPU-active time or energy. | Same review, original four smoke logs | measured scoped execution cost |
| All four actual development checkpoints pass strict CPU actor-only loading, including exact normalization restoration | Fixed zero observation stub; no simulator, policy forward call or rollout. Runtime tracking and policy utility remain pending. | `reports/relative_progress_2026-09-05/development_smoke_review/checkpoint_loading.json` | measured CPU lifecycle verification |

D seed-31 calibration is now running; its interim snapshots are not a complete
scientific pass. Assigned seeds, profiles and held-out endpoint rules remain
unchanged. No paper-bound policy-performance number changes. Next research
plan: `plan/RELATIVE_DEVELOPMENT_SMOKES_2026-09-05.md`.


## 2026-09-05 prospective three-seed precision sensitivity

| Quantity | Scope and limitation | Artifact | Class |
| --- | --- | --- | --- |
| Fixed three-seed 95% t-interval half-width = 2.4841377 × sample SD; observed mean +0.02 requires sample SD <0.0080511 for positive lower bound; observed panel mean zero requires SD <0.0040255 for the −0.01 guard | Algebra of the existing decision rule; not an estimate of actual training-seed variability. | `reports/relative_progress_2026-09-05/design_precision/result.json` | prospective design calculation |
| Hypothetical hard-panel benefit probabilities at (true mean, population SD): (+0.02,0.01) 30.8889%; (+0.02,0.02) 14.7528%; (+0.04,0.01) 90.8375%; (+0.04,0.02) 46.6744% | IID normal paired-seed model, illustrative unfitted parameters; one necessary gate only, conditional on all manipulation/provenance gates. Not measured policy evidence or full campaign power. | Same result; `hypothetical_primary.csv` | hypothetical operating scenarios |
| With hypothetical all-panel mean zero and SD 0.01, guard pass probability 17.8610%; combining hard mean +0.04/SD 0.01 gives full-positive Frechet bounds [8.6985%,17.8610%] | Does not assume independence of hard/full-panel summaries; normal approximation and no fitted variances. | Same result; `design_precision.pdf` | hypothetical bounds |

No method, assigned seed, budget, condition, threshold or queued source changes.
No benchmark policy outcomes are read. The sensitivity informs interpretation of
an inconclusive result and does not authorize optional seed additions. Exact
assumptions, derivation and next-study distinctions:
`plan/RELATIVE_DESIGN_PRECISION_2026-09-05.md`.


## 2026-09-05 fixed D seed-31 complete calibration

| Number / disposition | Scope and limitation | Artifact | Class |
| --- | --- | --- | --- |
| D seed 31: 4,000 iterations, 512 environments; mean TV 0.0849553389 over 37 post-warm-up snapshots, range [0.0083017,0.1182816]; minimum effective units 625.061738; maximum unit/clip mass 0.0172129/0.0172129; final saturation 0.727195946; 1,113,773 completed trials; zero invalid/censored events; calibration_pass | All 41 checkpoint/sampler histories reproduce. One fixed-baseline development seed only; planned seed 32 remains pending. Mean gate does not constrain each snapshot, and D has no upper 0.15 gate. | `reports/relative_progress_2026-09-05/failure_seed31_review/result.json`, original `failure_calibration_gate_retry/seed31_result.json` | measured exploratory calibration |
| D seed-31 elapsed training: 2,229 s / 0.619167 GPU-hours; one launch, successful terminal | Shared device; baseline/peak total memory 388/9,519 MiB. Excludes smokes, queue, evaluation and CPU engineering; not speed, energy or isolated GPU-active-time evidence. | Same review, original `seed31.log` | measured scoped execution cost |

The complete R11/R12/D31 allocation figure keeps unequal replications separate.
Similar mean TV does not establish identical allocation, comparable startup
exposure, progress-ranking utility or policy quality. No benchmark policy
endpoint was opened. Result and next freeze requirements:
`plan/RELATIVE_D_SEED31_RESULT_2026-09-05.md`.


## 2026-09-05 prospective freeze command implementation

The finalization command is implemented and tested. It refuses incomplete
actual prerequisites without writing enabled profiles, and verifies/seals a
complete explicitly synthetic contract without launching jobs. This supplies
implementation evidence only. Actual D replication, new-trainer lifecycle,
confirmation freeze and held-out policy utility remain **pending**. No
paper-bound performance number or scientific design changes. Details:
`plan/RELATIVE_CONFIRMATION_FREEZER_2026-09-05.md`.

## 2026-09-05 public relative-progress research checkpoint

The GitHub Pages update exports the already recorded R11/R12/D31 allocation
histories, E4 `not_tested` disposition and fixed-policy DFRP result with their
claim boundaries. No measured performance value changes. Public source identities
and the 23:10 EDT pending-state snapshot are in
`docs/assets/relative-progress/research_snapshot.json`; explanation and fixed
next-study design are in `docs/relative-progress.html`. Partial D32 progress is
operational status only and is excluded from the completed-run figure and table.
