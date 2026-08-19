# Global evaluation addendum — feasibility-stratified endpoints (D1)

**Sealed:** 2026-08-19, per the advisor directive of 2026-08-19 (encoded in `RESEARCH_PLAN_v5.md`).
Applies uniformly to Exp-1/2 (retrospective), N3, E3, and every later experiment. Sealed **before**
the N3 chain relaunches and before any E3 number exists.

## Policy

29 of the 100 held-out clips (`bank/tiers/heldout100.txt`) exceed the 10 % dynamically-infeasible-
frame threshold; the evaluation set is contaminated and will **not** be swapped mid-project.
Henceforth, for every experiment:

1. **Primary endpoints** are computed on the **feasible-only stratum**: clips with
   `infeasible_frac ≤ 0.10` under the pinned screen (below).
2. **Secondary**: all-clips (the historically sealed aggregates continue to be reported).
3. **Descriptive only**: the infeasible-only stratum.

## Pinned screen version

| artifact | sha256 |
|---|---|
| `tools/n1_knee_id.py` (screen, `--brief`, gap 6 cm, torque-limited LP, real μ) | `94bc3f65509ddf8b…` |
| `tools/screen_feasibility.sh` (batch driver) | `bd6649c992b566ee…` |
| `reports/feasibility_e3/feasibility.csv` (mixed100 + heldout100 + tier_800, 979 clips) | `3c86119a4e996020…` |
| `reports/feasibility_all/feasibility.csv` (10,705 clips) | `587a2518a9a4b40a…` |

Flag = `infeasible_frac > 0.10`: fraction of frames whose torque-limited unsupported wrench exceeds
half the robot's weight (frames with no contact candidate within 6 cm count as fully unsupported).

## Threshold provenance (the 10 % predates this addendum)

The ≤ 10 % criterion first appears in `PREREGISTRATION_N3_coverage.md` (sealed `af1b7c9f…`,
2026-08-18: the ground16 inclusion screen "≤ 10 % of frames with unsupported wrench > 0.5·weight")
and in `PREREGISTRATION_E3_addendum.md` §4 (sealed `f7929136…`, same day: "clips above 10 % are
kept but flagged"). It was not chosen with knowledge of any stratified endpoint.

## Worked example — retrospective Exp-1/2 (numbers already computed, `plan/ATLAS_v21_RESULT.md` §2b, `reports/N_atlas_v21.json`)

Held-out survival at iteration 3999 (seed means); 71 feasible / 29 infeasible:

| arm | feasible-only (primary) | all (secondary, sealed record) | infeasible-only (descriptive) |
|---|---:|---:|---:|
| uniform | 0.834 | 0.810 | 0.750 |
| adaptive | 0.811 | 0.780 | 0.705 |
| grounded | 0.859 | 0.825 | 0.741 |

Ordering unchanged in all strata. Grounded's endpoint edge over uniform: +0.025 feasible,
−0.009 infeasible — the curriculum's benefit lives where a policy can succeed. The sealed
Exp-1/2 verdicts (Branch B; AULC primary) are unaffected: this addendum adds strata, it does not
re-adjudicate.

## Conflicts with sealed artifacts — flagged, not edited

1. **`PREREGISTRATION_N3_coverage.md` (sealed `af1b7c9f…`).** Its primary endpoint E1 is
   kneel/crawl-phase survival of clip **#44**, whose clip-level flag is *infeasible*
   (`infeasible_frac` = 0.130). No conflict in substance: E1 is a **phase-level** endpoint,
   deliberately restricted (post-N1 addendum) to the clip's *feasible* segment via stratified
   start offsets {2,3,4,6} s, with the infeasible descent reported separately. E1 stands as
   sealed. N3's E2 (heldout100 regression check, ±0.03) was sealed on all clips; it is kept as
   sealed and the feasible-only stratum is co-reported per this policy.
2. **`PREREGISTRATION_E3_addendum_v2.md` (sealed `2c38845b…`).** Its named-clip support
   predictions (P-A/P-B/P-C) span both strata — of the 22 P-A dynamic clips, 12 are
   feasibility-flagged; P-C losers 12/20 flagged; P-B gainers 3/20 flagged (counted now, before
   any E3 number exists). Those correlational predictions stand as sealed across all clips.
   The H2b **primary Δ(grounded−uniform) endpoint** at 800 follows this addendum: feasible-only
   primary, all-clips secondary. A feasibility×support interaction is *reported* (descriptively)
   because the strata overlap the support classes unevenly.
3. **`PREREGISTRATION_ATLAS_v21.md` (sealed `9b1a2c78…`)** — already run; its outcomes are
   recorded against its own criteria in `ATLAS_v21_RESULT.md` and are not restratified.
4. **Correction of record:** `N1_RESULT.md` says "12 of the 40" nearest family clips fail the
   screen; at the sealed 10 % threshold the count is **20 of 40**
   (`reports/N3_candidate_feasibility.json`). The 12 was an informal stricter cut. Recorded here;
   `N1_RESULT.md` is not edited (it is a result log, corrected by this addendum).

## Operational rules restated (from the directive)

Background jobs write a completion sentinel (exit code + UTC timestamp) into their report
directory (`tools/with_sentinel.sh`). Every paper-bound number carries an artifact path in
`paper/RESULTS_LOG.md`.
