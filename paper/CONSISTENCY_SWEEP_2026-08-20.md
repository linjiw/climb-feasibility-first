# TASK consistency-sweep — 2026-08-20

*Status labels used: measured, sealed ✓, exploratory. Artifact paths touched: listed per row.
UNVERIFIED: none remaining after fixes below.*

Cross-check of the preview page (`docs/index.html`), flagship sections, and companion draft
against `paper/RESULTS_LOG.md`. The four named discrepancies plus one found in the sweep.

| # | discrepancy | artifact truth | proposed (now applied) wording | files fixed |
|---|---|---|---|---|
| a | "positive on all six transfer pairs" (page §03) vs "4/6 pairs (p = .010–.045)" (page §04) | `reports/N_atlas_v21.json` F2: **direction +ve on 6/6 pairs; 4/6 clear the 200-draw random-3-feature permutation baseline** (p = 0.010 / 0.030 / 0.045 / 0.015); →grounded pairs +0.015/+0.018 n.s. (p = 0.235 / 0.160) | "direction positive on 6/6 transfer pairs; 4/6 significant beyond a random-feature permutation baseline (p = 0.010–0.045); the two →grounded pairs move +0.015/+0.018 but do not clear it" — the direction/significance split stated wherever either number appears | `docs/index.html` §03 callout; `paper/flagship/S7_transfer.md` (already split — sentence sharpened) |
| b | "d_z = 20" without per-seed values | per-seed it3999 endpoints (recomputed from `reports/campaign/*_it3999.csv`): uniform 0.8137/0.8125/0.8025, adaptive 0.7837/0.7850/0.7725 → **per-seed Δ(uniform−adaptive) = +0.0300/+0.0275/+0.0300** (mean +0.0292, sd 0.0014); `reports/campaign_summary_3arm.json` cohens_dz 20.207 | report the three per-seed deltas; footnote the d_z as an artefact of near-zero seed variance ("d_z = 20.2 reflects sd 0.0014 across 3 seeds; per-seed deltas are the meaningful statistic; sign test 3/3, permutation floor p = 0.125 at n = 3") | `paper/flagship/S3_collapse_nonfloor.md`; `docs/index.html` Act 1 |
| c | "two runs of the same physics engine" (page) vs "dual-engine" (page, S1 intro) — stack identity vague | S1/G0 compares **the same engine through two integration stacks**: mjlab v1.6.0 driving MuJoCo Warp 3.11.0 directly, vs Newton (repo commit `7bb6d02d`, pip version 1.6.0.dev0) driving MuJoCo Warp 3.11.0 through `SolverMuJoCo`; **classic MuJoCo 3.11.0 (C)** as third referee; warp-lang 1.16.0; pins recorded in `plan/PREREGISTRATION_G1_clip44.md` §Pins | standardise on **"dual-stack, same-engine conformance (third-engine referee)"**; name all three stacks + versions at first use; never "dual-engine" unqualified | `docs/index.html` (3 sites); `paper/flagship/S1_intro.md`; `S5_anatomy.md` §5.1 already names them — pins added |
| d | 327 N vs ~329 N phrasing drift | `reports/N1_clip44_knee_id.json`: descent-window (0.75–1.75 s) unconstrained unsupported force **median 328.6 N, p90 348.5 N**; robot weight **327.1 N** (33.3 kg) | canonical sentence: "median unsupported force 329 N (artifact: 328.6 N) against a robot weight of 327 N" — ~329 always paired with 327 at first use per document; standalone "~329 N" allowed only after the pairing | verified consistent in S1/S5/S6/companion/page (already paired); N1_RESULT unchanged (it is the artifact log) |
| e | (found in sweep) page §03 callout omitted the significance split while §04 card had it — same as (a) root cause: two authorship passes | as (a) | as (a) | `docs/index.html` |

Sweep also re-verified against `paper/RESULTS_LOG.md`: collapse numbers (0.884/0.870/0.893 top-1;
`reports/A5_coverage_dose.json`), grounded strata (+0.025/−0.009; `reports/N_atlas_v21.json`),
prevalence row set (`reports/feasibility_all/prevalence_report.txt`), N5 replication line
(r = 0.92, 6/6 > 5 mm — note this **6/6 is the instrument-replication statistic and is unrelated
to the 6/6 transfer-direction statistic in (a)**; both retained with explicit referents),
P-TAX row (`reports/P_TAX_result.json`). No further conflicts found.

**Result: table empty after the applied fixes** (all rows resolved in the same commit as this file).
