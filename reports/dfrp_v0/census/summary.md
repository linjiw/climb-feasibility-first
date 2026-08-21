# DFRP v0 legacy-artifact routing census

**Status:** unsealed measured routing audit. This reclassifies existing root-only
artifacts; it is not an 8 cm root+IK recovery result or a policy-benefit result.

| route | clips | share of strict flagged set |
|---|---:|---:|
| primary candidate, `offset <= 0.08 m` | 644 | 26.4% |
| additional exploratory, `0.08 < offset <= 0.15 m` | 962 | 39.4% |
| recovered through 15 cm | 1606 | 65.8% |
| quarantine pending exact-segment/stronger-repair work | 836 | 34.2% |

The strict `infeasible_frac > 0.10` rule flags **2,442** of
10,705 clips. All 644 nominal primary candidates come from
the legacy root-only operator and therefore fail the new IK/contact
qualification; **zero legacy clips are promoted to DFRP training**. Exact
support sidecars are also absent bank-wide, so `training_eligible` is
0 by construction.

## Boundary/provenance discrepancy

The old repair directory is not exactly the new strict flagged set: strict
screening has 0 missing repair record(s), while the repair directory
has 1 out-of-scope record(s).

- missing: `none`
- out of scope: `CMU_76_76_02_poses_120_jpos`

This does not edit the published 2,443-row census. It explains why the strict
DFRP denominator is 2,442 and must be carried as an addendum rather than silently
replacing the historical artifact.

Manifest payload: `6b41fc24f31c9b5abc87d6683dbfd02c61059656eb45e1ea1339f61c3d332d34`.
