# DFRP v1 exact-repair panel result

**Status:** unsealed measured CPU result. **Gate: PASS.** No policy-benefit
or hardware claim is made.

The frozen panel produced **22/26**
(84.6%) exact-ready flagged clips and
**4/4** byte-identical
controls. The admitted panel exposes **10,561** legal
50-step starts. Median per-clip runtime was 2.57 s and p95 was
6.29 s.

## Frozen guards

- PASS: `flagged_ready_at_least_75pct`
- PASS: `controls_training_ready`
- PASS: `controls_byte_identical`
- PASS: `manifest_integrity_clean`
- PASS: `joint_limits_clean_among_admitted`
- PASS: `ik_residual_clean_among_admitted`

## Flagged clips not admitted

- `Transitions_mocap_mazen_c3d_punchboxing_walk_poses_120_jpos`: route `quarantine`; after=0.05172413793103448; reasons=['no_legal_raw_segment', 'residual_infeasibility']
- `CMU_20_21_rory1_20_10_poses_120_jpos`: route `quarantine`; after=0.08333333333333333; reasons=['no_legal_raw_segment', 'residual_infeasibility']
- `SFU_0005_0005_SideSkip001_poses_120_jpos`: route `repair_primary`; after=0.00663716814159292; reasons=['exact_training_support_not_ready', 'repair_qualification_incomplete']
- `BMLmovi_Subject_47_F_MoSh_Subject_47_F_15_poses_120_jpos`: route `repair_primary`; after=0.0; reasons=['exact_training_support_not_ready', 'repair_qualification_incomplete']

Selection payload: `900c2dbff2cfd709aefb9b308ac2980710efaa2a16c076206bda6fafe723a355`.
Manifest payload: `ca505482ccda7b6d1096f054c8535eff58063bc78af34ed0ace1235427eec175`.
Operator SHA-256: `40c367ad18894f6a7cf2ef83bc85d2765b68cbce9830dbe1d866417c32c597da`.
