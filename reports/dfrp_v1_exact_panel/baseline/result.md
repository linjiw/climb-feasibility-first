# DFRP v1 exact-repair panel result

**Status:** unsealed measured CPU result. **Gate: FAIL.** No policy-benefit
or hardware claim is made.

The frozen panel produced **22/26**
(84.6%) exact-ready flagged clips and
**1/4** byte-identical
controls. The admitted panel exposes **11,372** legal
50-step starts. Median per-clip runtime was 2.56 s and p95 was
6.35 s.

## Frozen guards

- PASS: `flagged_ready_at_least_75pct`
- PASS: `controls_training_ready`
- FAIL: `controls_byte_identical`
- PASS: `manifest_integrity_clean`
- PASS: `joint_limits_clean`
- FAIL: `ik_residual_clean`

## Flagged clips not admitted

- `Transitions_mocap_mazen_c3d_punchboxing_walk_poses_120_jpos`: route `segment_only`; after=0.05172413793103448; reasons=['residual_infeasibility']
- `CMU_20_21_rory1_20_10_poses_120_jpos`: route `segment_only`; after=0.08333333333333333; reasons=['residual_infeasibility']
- `SFU_0005_0005_SideSkip001_poses_120_jpos`: route `repair_primary`; after=0.00663716814159292; reasons=['exact_training_support_not_ready', 'repair_qualification_incomplete']
- `BMLmovi_Subject_47_F_MoSh_Subject_47_F_15_poses_120_jpos`: route `repair_primary`; after=0.0; reasons=['exact_training_support_not_ready', 'repair_qualification_incomplete']

Selection payload: `900c2dbff2cfd709aefb9b308ac2980710efaa2a16c076206bda6fafe723a355`.
Manifest payload: `6896a5806b15ba3977d2c31cd054e5bf7e6fb604382db744aadefcd2db7c6542`.
Operator SHA-256: `8ddd69873b73e65e04f32a30f911c1efa3900253f35b1bb3284678a3f7c8c7f7`.
