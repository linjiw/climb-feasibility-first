# Results log — every paper-bound number and its artifact path (policy: RESEARCH_PLAN_v5)

| number(s) | where used | artifact path | class |
|---|---|---|---|
| top-1 mass 0.884/0.870/0.893; mean entropy 0.38–0.40 (adaptive); 0.60–0.62, top-1 0.57–0.70 (grounded) | §3, §4, F2 | `reports/A5_coverage_dose.json` | sealed-confirmatory |
| same attractor clip 3/3 seeds ×2 arms; share of concentrated iters 0.28–0.53 | §3 | `reports/A7_attractor.json` | sealed-confirmatory |
| endpoint 0.780/0.810/0.825 ± sd; AULC 0.640/0.698/0.696; paired deltas, d_z | §3, §4 | `reports/campaign_summary_3arm.json` | sealed-confirmatory |
| feasible-only strata 0.811/0.834/0.859; infeasible 0.705/0.750/0.741; grounded edge +0.025/−0.009 | §4, §6 | `reports/N_atlas_v21.json` (endpoints_2b), `plan/ATLAS_v21_RESULT.md` | exploratory → D1 primary going forward |
| non-floor derivation ε/(Σq+ε); upstream filings | §3 | `plan/RESEARCH_PLAN_v2.md` E3 row; mjlab#1153; whole_body_tracking#73; `reports/A4_upstream_issue.md` | sealed-confirmatory |
| conformance after fixes: 1.000/1.000 vs 1.000/1.000, Δerr −0.5/−0.8 mm; #44 0.000 vs 0.000 (+1.0 mm); |Δq̇| ≤ 3e-5 | §5.1, A1 | `reports/S1_KIT1226_n32_absorb.json`, `reports/S1_clip44_n32_absorb.json`, `plan/S1_RESULT.md` | confirmatory (post-fix) |
| pre-fix forks 0.656/0.594/0.500/0.594/0.500 | A1 | `reports/S1_KIT1226_n32*.json` | withdrawn-context |
| G1 ratios (1.30–2.16×), floor ratios (≤3.2×), termination fragility 0 everywhere, failure-time agreement ≤ 0.1 s | §5.2 | `reports/G1/run0/g1_summary.json`, `plan/G1_RESULT.md` | sealed-confirmatory (negative) |
| N1: descent 0.75–1.75 s airborne, ~329 N ≈ weight (327 N) unsupported in 86 % of frames; rise 8.0–8.5 s; kneel supportable (0 N residual, both contact models); control supported every frame | §5.3, §6, F3 | `reports/N1_clip44_knee_id.json`, `reports/N1_CMU76_knee_id.json`, `plan/N1_RESULT.md` | confirmatory (measurement) |
| family: 20/40 neighbours > 10 % infeasible (12 was an informal cut, corrected) | §5.3 | `reports/N3_candidate_feasibility.json`, `plan/GLOBAL_EVAL_ADDENDUM.md` | measurement + correction |
| stratified-start baseline: #44 0/0/0/0 at 1–6 s offsets, 1.00 at 8 s; family fails in ground segments | §5.3, §8.1, F3 | `reports/N3_baseline_uniform-s1_strat.csv` | measurement |
| prevalence 22.8 % (>10 % frames); ground 39 %, dynamic 59 %, locomotion 25 %, quiet 13 %; sources 0.1–100 % | §6, F4, companion | `reports/feasibility_all/prevalence_report.txt` (+ sentinel `COMPLETED`) | measurement |
| eval contamination 29/100 | §6, D1 seal | `reports/feasibility_e3/feasibility.csv` | measurement |
| P-TAX: median tax 0.126; 53 % > 0.1; heldout partial ρ −0.039/−0.151/−0.089; 0/3 sealed rule | §6 | `reports/P_TAX_tax_fractions.csv`, `reports/P_TAX_result.json`, `plan/P_TAX_RESULT.md` | sealed null |
| policy-consensus ρ 0.832; intrinsic transfer 0.567/0.579; +support +0.00–0.03 (n.s.); +feasibility 0.609/0.616/0.580/0.633, perm p 0.010/0.030/0.045/0.015; direct ρ(difficulty, infeas) +0.37/+0.48/+0.50 | §7, F5 | `reports/A3_atlas_transfer.json`, `reports/N2_atlas_support.json`, `reports/N_atlas_v21.json` | sealed splits per table |
| support-residual ρ +0.605/+0.544 (kNN), −0.578/−0.561 (density) | §7 | `reports/N2_atlas_support.json` | confirmed half of N2 |
| bank-invariant support change 100→800: all 22 dynamic clips lose; category table; named lists | §8.3 | `reports/support_change_heldout100_100to800.csv`, `plan/PREREGISTRATION_E3_addendum_v2.md` | sealed predictions |
| N5: floor ≈ 0 ± 1 mm; motor +11.5/−2.6/−4.6/−10.9/−0.8/−14.2 mm (run0); delay +11.9 CMU_35; termination shift −0.51 ± 0.14 s (delay, #44); contact-onset ≤ 0.03 s | §9, A2 | `reports/G1/run0/g1_v2_summary.json`, `plan/N5_RESULT.md` | calibration (exploratory label) |
| N5 replication: r = 0.92; 6/6 sign agreement > 5 mm; #44 motor +12.8 [+11.2,+14.2]; windows +0.3/+15.0/+26.8 (s0), −1.4/+16.0/+20.4 (s1) | §9 | `reports/G1/run1_seed1/g1_v2_summary.json`, `plan/N5_RESULT.md` | replication (exploratory label) |
| oracle precondition: playback survives all (err 4–13 mm); PD-follow dies on all incl. easy; kneel offsets its only survivals | §8.1 | `reports/N3_env_admits_*.csv`, `plan/N3_PRECONDITION_env_admits.md` | precondition |
| refeas demo: hover clip flags 45 % airborne/infeasible, 1.77 s free-fall-equivalent | companion | `refeas/examples/demo_hover_brief.json` (repo tag v0.1.0) | tool validation |
