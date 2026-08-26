# Appendix A3. Screen validation detail

*Artifacts: `reports/N1_clip44_knee_id.json`, `reports/N1_CMU76_knee_id.json`,
`reports/N1_gap_sensitivity.json`, `reports/upstream_drafts/CNRS_AUDIT.md`,
`reports/repair_census/summary.json`. Labels as marked.*

**Internal controls [measured].** Within the attractor clip itself the screen's phases align with
mechanics: standing and kneeling phases report 0 N torque-limited residual (the kneel even under
the simulator's frictionless-knee contact model); only the transitions flag. The matched-easy
control is supported at every frame (τ/limit p95 = 0.66). The synthetic hover demo (a standing
pose translated upward) flags at exactly its constructed 45 %.

**Parameter sensitivity [measured; found by adversarial review, reported as found].** The contact
gap is a real choice with two failure modes: at 3 cm the feasible control itself flags 42 %
(the bank carries a ~3 cm systematic stance-clearance offset from retarget ground alignment); at
10 cm the screen degenerates (airborne geometry is granted as contact and the attractor's descent
reads 0 %). 6 cm sits between the failure modes — above the bank's clearance offset, below
bridgeable distance. The ½-weight bound is insensitive (flag mass 15.1/13.1/12.5 % at
0.25/0.5/0.75× weight) because unsupported force concentrates near 1× weight. Flight is exempt by
construction (free fall demands no support), verified on a jump clip whose ballistic phases do
not flag while its floating preparation frames do.

**External validation [measured].** (i) A deterministic severity-stratified 5+5 hand-check of the
extreme sources reproduces the clearance verdict from raw NPZ poses: CNRS is 5/5 ingest defects
on ordinary walks (median lowest-geometry clearance 5.1–9.7 cm); Transitions is mixed, 3/5 ingest
and 2/5 acrobatic content, with no scene-mismatch verdict in the ten-clip panel
(`reports/feasibility_extremes/`). (ii) The rollout-only sign-reversal localises to screen-flagged windows in two
independent seed sets without the rollouts ever seeing the screen. (iii) The repair census closes
the loop constructively: lowering the root exactly where the screen says support is missing
removes the flag in 1,606 of the strict 2,442 flagged clips (65.8%, residual ≤ 5 %; C4), is a no-op on feasible controls, and
is correctly *refused* by the over-repair budget on genuine ballistics — a screen that flagged
noise would not respond to a targeted geometric fix this way.

**Cross-implementation validation [measured; §6].** The strongest external check is a second,
independently written implementation of the same method (different codebase, different G1 MJCF,
μ 0.7 rather than 0.6) applied to a different production bank. It returns 0.14 % of 4,950 clips
above the 10 %-infeasible threshold — a screen carrying a systematic bug, or one that conflated
flight with infeasibility, would not return near-zero on a bank that contains 111 clips above
10 % airborne frames and 7 `kneeling_loop_*` clips at airborne fraction 1.000 with infeasible
fraction 0.000. The same run is a discrimination test the method passes in the other direction:
those kneeling loops carry their weight on the knees and are supportable at every frame.

We then applied *both* implementations to each clip in a deterministic stratified 20+20 panel
[measured; `reports/feasibility_xcheck/`; selection seed 260826]. The adapters preserve the exact
29-joint name/order/axis layout; the implementations retain their production MJCF and μ settings.
Across all 40 clips, `infeasible_frac` ranks agree at Spearman ρ = **0.984** and `airborne_frac`
at ρ = **0.997**. At the strict `infeasible_frac > 0.10` rule, 39/40 verdicts agree (97.5 %,
κ = 0.948): 16 both flag, 23 neither, one SONIC-only, zero CLIMB-only. AMASS agrees 20/20;
BONES-SEED agrees 19/20. The sole threshold disagreement is `burpee_002__A362_M` (CLIMB 0.019,
SONIC 0.136). Because selection is stratified on the native verdict, this table validates
implementation agreement; it is not a prevalence estimator and does not remove the corpus/release-
filter confound in the 160× cross-bank contrast.

| bank | stratum | clip | CLIMB infeasible / airborne | SONIC infeasible / airborne | >.10 flag |
|---|---|---|---:|---:|:---:|
| BONES-SEED | flagged | `burpee_002__A362_M` | 0.019 / 0.004 | 0.136 / 0.177 | disagree |
| BONES-SEED | flagged | `high_jump_R_003__A367_M` | 0.124 / 0.219 | 0.138 / 0.219 | agree |
| BONES-SEED | flagged | `jump_off_50cm_R_001__A415_M` | 0.358 / 0.418 | 0.366 / 0.425 | agree |
| BONES-SEED | flagged | `jump_off_front_50cm_001__A416_M` | 0.324 / 0.486 | 0.353 / 0.493 | agree |
| BONES-SEED | flagged | `jump_off_front_50cm_R_002__A416_M` | 0.379 / 0.426 | 0.379 / 0.426 | agree |
| BONES-SEED | flagged | `jump_on_50cm_002__A415` | 0.636 / 0.721 | 0.658 / 0.721 | agree |
| BONES-SEED | flagged | `kick_back_001__A495_M` | 0.472 / 0.079 | 0.472 / 0.082 | agree |
| BONES-SEED | feasible | `door_knob_right_side_open_R_001__A509_M` | 0.000 / 0.000 | 0.000 / 0.000 | agree |
| BONES-SEED | feasible | `greetings_hat_R_003__A261` | 0.000 / 0.000 | 0.000 / 0.000 | agree |
| BONES-SEED | feasible | `injured_R_leg_idle_right_R_002__A326` | 0.000 / 0.000 | 0.000 / 0.000 | agree |
| BONES-SEED | feasible | `jog_avoid_bump_270_R_002__A167` | 0.000 / 0.013 | 0.000 / 0.013 | agree |
| BONES-SEED | feasible | `jog_ff_stop_360_R_002__A237_M` | 0.011 / 0.000 | 0.000 / 0.000 | agree |
| BONES-SEED | feasible | `jump_ff_360_R_003__A295` | 0.000 / 0.000 | 0.000 / 0.000 | agree |
| BONES-SEED | feasible | `medium_big_heavy_one_hand_walk_ff_start_270_R_003__A505_M` | 0.000 / 0.000 | 0.000 / 0.000 | agree |
| BONES-SEED | feasible | `praying_001__A185_M` | 0.000 / 0.000 | 0.000 / 0.000 | agree |
| BONES-SEED | feasible | `reach_jump_R_003__A223` | 0.000 / 0.086 | 0.000 / 0.086 | agree |
| BONES-SEED | feasible | `turn_jump_270_003__A058` | 0.000 / 0.000 | 0.000 / 0.000 | agree |
| BONES-SEED | feasible | `walk_backward_stop_002__A037_M` | 0.000 / 0.000 | 0.000 / 0.000 | agree |
| BONES-SEED | feasible | `walk_sideway_135_start_001__A024` | 0.000 / 0.000 | 0.000 / 0.000 | agree |
| BONES-SEED | feasible | `warm_welcome_R_001__A432_M` | 0.000 / 0.000 | 0.000 / 0.000 | agree |
| AMASS-wbt-G1 | flagged | `BMLmovi_Subject_53_F_MoSh_Subject_53_F_17_poses_120_jpos` | 0.607 / 0.607 | 0.603 / 0.603 | agree |
| AMASS-wbt-G1 | flagged | `BMLmovi_Subject_64_F_MoSh_Subject_64_F_9_poses_120_jpos` | 0.130 / 0.124 | 0.134 / 0.228 | agree |
| AMASS-wbt-G1 | flagged | `CMU_02_02_02_poses_120_jpos` | 0.427 / 0.411 | 0.460 / 0.444 | agree |
| AMASS-wbt-G1 | flagged | `CMU_102_102_28_poses_120_jpos` | 0.669 / 0.795 | 0.669 / 0.792 | agree |
| AMASS-wbt-G1 | flagged | `CMU_91_91_41_poses_120_jpos` | 0.195 / 0.286 | 0.200 / 0.286 | agree |
| AMASS-wbt-G1 | flagged | `CNRS_288_-12_L_1` | 0.648 / 0.629 | 0.634 / 0.618 | agree |
| AMASS-wbt-G1 | flagged | `KIT_3_downstairs03_poses_100_jpos` | 0.730 / 0.730 | 0.730 / 0.730 | agree |
| AMASS-wbt-G1 | flagged | `KIT_3_kneel_up_hold03_poses_100_jpos` | 0.319 / 0.319 | 0.319 / 0.319 | agree |
| AMASS-wbt-G1 | flagged | `KIT_572_squat02_poses_100_jpos` | 0.185 / 0.185 | 0.185 / 0.185 | agree |
| AMASS-wbt-G1 | flagged | `KIT_675_walk_with_handrail_beam_right06_poses_100_jpos` | 0.475 / 0.475 | 0.471 / 0.471 | agree |
| AMASS-wbt-G1 | feasible | `BMLmovi_Subject_22_F_MoSh_Subject_22_F_2_poses_120_jpos` | 0.000 / 0.000 | 0.000 / 0.000 | agree |
| AMASS-wbt-G1 | feasible | `CMU_28_28_15_poses_120_jpos` | 0.000 / 0.000 | 0.000 / 0.000 | agree |
| AMASS-wbt-G1 | feasible | `Eyes_Japan_Dataset_hamada_throw_toss-05-both_hands_over_heavy-hamada_poses_120_jpos` | 0.000 / 0.000 | 0.000 / 0.000 | agree |
| AMASS-wbt-G1 | feasible | `Eyes_Japan_Dataset_shiono_gesture_etc-35-west_side-shiono_poses_120_jpos` | 0.002 / 0.002 | 0.001 / 0.001 | agree |
| AMASS-wbt-G1 | feasible | `GRAB_s8_gamecontroller_pick_all` | 0.000 / 0.000 | 0.000 / 0.000 | agree |
| AMASS-wbt-G1 | feasible | `KIT_291_push_recovery_stand_back03_poses_100_jpos` | 0.000 / 0.000 | 0.000 / 0.000 | agree |
| AMASS-wbt-G1 | feasible | `KIT_424_bend_left07_poses_100_jpos` | 0.000 / 0.000 | 0.000 / 0.000 | agree |
| AMASS-wbt-G1 | feasible | `KIT_4_WalkInCounterClockwiseCircle02_poses_100_jpos` | 0.000 / 0.000 | 0.000 / 0.000 | agree |
| AMASS-wbt-G1 | feasible | `KIT_7_RightTurn03_poses_100_jpos` | 0.000 / 0.000 | 0.000 / 0.000 | agree |
| AMASS-wbt-G1 | feasible | `KIT_9_bend_left08_poses_100_jpos` | 0.000 / 0.000 | 0.000 / 0.000 | agree |

**Known limits.** Plane-only terrain — and the second bank makes the cost concrete: its flagged
box jumps (four of its seven flagged clips) are unsupportable only because the 50 cm box they use is
absent from the screened scene
(a scene/reference mismatch, not a retarget defect, and not repairable by root projection).
Embodiment-relative verdicts; q̈ from smoothed central
differences (5-frame) — velocity-spike artifacts (one observed 40 rad/s glitch) are a separate QC
class the screen does not target.
