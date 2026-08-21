# Corrections — 2026-08-21 DFRP routing audit

This addendum records one membership error exposed by the fail-closed DFRP v0
manifest. Historical census artifacts remain unchanged.

## C4 — the 2,443-row repair directory is not the strict flagged set

**Previously stated:** “65.8% of 2,443 flagged clips are auto-recoverable.”

**Corrected:** the pinned strict rule `infeasible_frac > 0.10` flags **2,442**
clips. Of those, the legacy root-only operator recovers **1,606 (65.8%)** under
the old `offset <= 0.15 m` / residual `<= 0.05` budget. The historical repair
directory has 2,443 JSON records and 1,607 successes because it additionally
contains the feasible no-op control `CMU_76_76_02_poses_120_jpos`
(`infeasible_frac = 0.0`); it is not the exact strict flagged set.

The exact-boundary clip
`BMLmovi_Subject_62_F_MoSh_Subject_62_F_3_poses_120_jpos`
(`infeasible_frac = 0.10`) is correctly outside the strict set and was not
repaired. The prior “noted, not changed” paragraph in
`paper/CORRECTIONS_2026-08-19.md` correctly distinguished 2,442 (`>`) from
2,443 (`>=`) but incorrectly inferred that the 2,443-row repair directory was
the `>=` set.

**Effect:** the aggregate recovery percentage remains 65.8% at one decimal.
Category/source tables in the historical 2,443-row summary are retained as
historical directory-census outputs; only claims that all 2,443 were flagged
are withdrawn. DFRP's new 8 cm split is **644/2,442 (26.4%)** primary-budget
legacy candidates plus **962/2,442 (39.4%)** additional 8–15 cm exploratory
candidates. All are legacy root-only artifacts and none is promoted to DFRP
training without new qualification and exact support.

**Evidence:** `reports/dfrp_v0/census/manifest.json`,
`reports/dfrp_v0/census/summary.{json,md}`, payload
`6b41fc24f31c9b5abc87d6683dbfd02c61059656eb45e1ea1339f61c3d332d34`;
generator `tools/analyze_dfrp_manifest.py`.
