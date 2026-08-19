# G1 gate — pre-registered statistics

## Clip-level fragility, raw mean |Δφ| over paired-alive frames (body_pos_err [m])

| axis | BMLmovi_Subject_64_F_MoSh_Subject_ | CMU_76_76_02_poses_120_jpos | BMLhandball_S07_Expert_Trial_upper | DFaust_67_50027_50027_one_leg_jump | DFaust_67_50025_50025_one_leg_jump | CMU_35_35_21_poses_120_jpos |
|---|---|---|---|---|---|---|
| delay | 0.0040 | 0.0058 | 0.0078 | 0.0153 | 0.0146 | 0.0096 |
| motor | 0.0198 | 0.0050 | 0.0053 | 0.0134 | 0.0034 | 0.0156 |
| fric | 0.0172 | 0.0043 | 0.0088 | 0.0050 | 0.0037 | 0.0332 |
| solref | 0.0060 | 0.0024 | 0.0062 | 0.0047 | 0.0047 | 0.0087 |
| com | 0.0141 | 0.0026 | 0.0034 | 0.0079 | 0.0044 | 0.0056 |
| condim | 0.0041 | 0.0043 | 0.0043 | 0.0131 | 0.0068 | 0.0134 |
| *same-solver floor (A base vs C base)* | 0.0037 | 0.0021 | 0.0086 | 0.0041 | 0.0047 | 0.0124 |

## Ratio to matched-easy mean (body_pos_err)

| axis | BMLmovi_Subject_64_F_MoSh_Subject_ | CMU_76_76_02_poses_120_jpos | BMLhandball_S07_Expert_Trial_upper | DFaust_67_50027_50027_one_leg_jump | DFaust_67_50025_50025_one_leg_jump | CMU_35_35_21_poses_120_jpos |
|---|---|---|---|---|---|---|
| delay | 0.59 | 0.85 | 1.15 | 2.25 | 2.15 | 1.41 |
| motor | 3.84 | 0.96 | 1.04 | 2.60 | 0.66 | 3.03 |
| fric | 2.61 | 0.66 | 1.34 | 0.76 | 0.56 | 5.04 |
| solref | 1.40 | 0.56 | 1.44 | 1.08 | 1.08 | 2.02 |
| com | 4.72 | 0.86 | 1.14 | 2.63 | 1.47 | 1.88 |
| condim | 0.95 | 1.00 | 1.00 | 3.08 | 1.58 | 3.14 |

## Termination fragility |P(alive+) − P(alive−)| at clip end

| axis | BMLmovi_Subject_64_F_MoSh_Subject_ | CMU_76_76_02_poses_120_jpos | BMLhandball_S07_Expert_Trial_upper | DFaust_67_50027_50027_one_leg_jump | DFaust_67_50025_50025_one_leg_jump | CMU_35_35_21_poses_120_jpos |
|---|---|---|---|---|---|---|
| delay | 0.00 (0.00/0.00) | 0.00 (1.00/1.00) | 0.00 (1.00/1.00) | 0.00 (0.00/0.00) | 0.00 (0.00/0.00) | 0.00 (1.00/1.00) |
| motor | 0.00 (0.00/0.00) | 0.00 (1.00/1.00) | 0.00 (1.00/1.00) | 0.00 (0.00/0.00) | 0.00 (0.00/0.00) | 0.00 (1.00/1.00) |
| fric | 0.00 (0.00/0.00) | 0.00 (1.00/1.00) | 0.00 (1.00/1.00) | 0.00 (0.00/0.00) | 0.00 (0.00/0.00) | 0.00 (1.00/1.00) |
| solref | 0.00 (0.00/0.00) | 0.00 (1.00/1.00) | 0.00 (1.00/1.00) | 0.00 (0.00/0.00) | 0.00 (0.00/0.00) | 0.00 (1.00/1.00) |
| com | 0.00 (0.00/0.00) | 0.00 (1.00/1.00) | 0.00 (1.00/1.00) | 0.00 (0.00/0.00) | 0.00 (0.00/0.00) | 0.00 (1.00/1.00) |
| condim | 0.00 (0.00/0.00) | 0.00 (1.00/1.00) | 0.00 (1.00/1.00) | 0.00 (0.00/0.00) | 0.00 (0.00/0.00) | 0.00 (1.00/1.00) |

## Peak localisation of F(t) (body_pos_err, 0.5 s smoothing)

| axis | BMLmovi_Subject_64_F_MoSh_Subject_ | CMU_76_76_02_poses_120_jpos | BMLhandball_S07_Expert_Trial_upper | DFaust_67_50027_50027_one_leg_jump | DFaust_67_50025_50025_one_leg_jump | CMU_35_35_21_poses_120_jpos |
|---|---|---|---|---|---|---|
| delay | t=0.2s pk/med=2.3 fail@2.4 | t=7.6s pk/med=3.9 fail@None | t=9.7s pk/med=3.1 fail@None | t=0.6s pk/med=1.1 fail@0.84 | t=0.5s pk/med=2.0 fail@0.9400000000000001 | t=1.0s pk/med=2.0 fail@None |
| motor | t=2.4s pk/med=2.0 fail@2.92 | t=4.5s pk/med=3.2 fail@None | t=3.1s pk/med=3.5 fail@None | t=0.5s pk/med=1.7 fail@0.8 | t=0.4s pk/med=1.5 fail@0.98 | t=0.7s pk/med=2.3 fail@None |
| fric | t=2.6s pk/med=17.7 fail@2.88 | t=7.5s pk/med=2.1 fail@None | t=9.7s pk/med=20.6 fail@None | t=0.5s pk/med=1.8 fail@0.8200000000000001 | t=0.7s pk/med=1.5 fail@0.92 | t=0.9s pk/med=1.5 fail@None |
| solref | t=2.7s pk/med=4.6 fail@2.94 | t=5.2s pk/med=2.7 fail@None | t=2.4s pk/med=3.4 fail@None | t=0.6s pk/med=1.5 fail@0.84 | t=0.7s pk/med=3.8 fail@0.96 | t=0.3s pk/med=2.2 fail@None |
| com | t=2.6s pk/med=23.9 fail@2.82 | t=9.4s pk/med=2.4 fail@None | t=0.9s pk/med=3.9 fail@None | t=0.5s pk/med=1.2 fail@0.8 | t=0.7s pk/med=1.7 fail@0.92 | t=0.3s pk/med=1.5 fail@None |
| condim | t=2.7s pk/med=3.9 fail@2.92 | t=7.5s pk/med=6.4 fail@None | t=9.7s pk/med=4.3 fail@None | t=0.5s pk/med=1.2 fail@0.8 | t=0.7s pk/med=2.7 fail@0.9400000000000001 | t=0.3s pk/med=1.4 fail@None |

## EXPLORATORY (not pre-registered): signed effect, mean over replicates of time-mean (φ⁺−φ⁻), body_pos_err [m], 95% paired bootstrap CI

| axis | BMLmovi_Subject_64_F_MoSh_Subject_ | CMU_76_76_02_poses_120_jpos | BMLhandball_S07_Expert_Trial_upper | DFaust_67_50027_50027_one_leg_jump | DFaust_67_50025_50025_one_leg_jump | CMU_35_35_21_poses_120_jpos |
|---|---|---|---|---|---|---|
| delay | +0.0022 [+0.0022,+0.0022]* | -0.0025 [-0.0025,-0.0025]* | +0.0006 [+0.0006,+0.0006]* | -0.0045 [-0.0045,-0.0045]* | +0.0145 [+0.0145,+0.0145]* | -0.0037 [-0.0037,-0.0037]* |
| motor | +0.0149 [+0.0149,+0.0149]* | -0.0040 [-0.0040,-0.0040]* | +0.0000 [+0.0000,+0.0000]* | +0.0044 [+0.0044,+0.0044]* | -0.0024 [-0.0024,-0.0024]* | -0.0070 [-0.0070,-0.0070]* |
| fric | -0.0022 [-0.0022,-0.0022]* | -0.0021 [-0.0021,-0.0021]* | -0.0035 [-0.0035,-0.0035]* | +0.0049 [+0.0049,+0.0049]* | -0.0002 [-0.0002,-0.0002]* | -0.0326 [-0.0326,-0.0326]* |
| solref | -0.0014 [-0.0014,-0.0014]* | +0.0003 [+0.0003,+0.0003]* | -0.0043 [-0.0043,-0.0043]* | +0.0011 [+0.0011,+0.0011]* | -0.0024 [-0.0024,-0.0024]* | +0.0083 [+0.0083,+0.0083]* |
| com | -0.0018 [-0.0018,-0.0018]* | +0.0006 [+0.0006,+0.0006]* | -0.0003 [-0.0003,-0.0003]* | -0.0073 [-0.0073,-0.0073]* | +0.0025 [+0.0025,+0.0025]* | +0.0051 [+0.0051,+0.0051]* |
| condim | -0.0001 [-0.0001,-0.0001]* | -0.0031 [-0.0031,-0.0031]* | -0.0007 [-0.0007,-0.0007]* | +0.0131 [+0.0131,+0.0131]* | -0.0034 [-0.0034,-0.0034]* | -0.0128 [-0.0128,-0.0128]* |

(* = CI excludes zero; sign: + means the +δ world tracks worse)

## Survival at clip end, +δ / −δ (or +δ / base)

| axis | BMLmovi_Subject_64_F_MoSh_Subject_ | CMU_76_76_02_poses_120_jpos | BMLhandball_S07_Expert_Trial_upper | DFaust_67_50027_50027_one_leg_jump | DFaust_67_50025_50025_one_leg_jump | CMU_35_35_21_poses_120_jpos |
|---|---|---|---|---|---|---|
| delay | 0.00/0.00 | 1.00/1.00 | 1.00/1.00 | 0.00/0.00 | 0.00/0.00 | 1.00/1.00 |
| motor | 0.00/0.00 | 1.00/1.00 | 1.00/1.00 | 0.00/0.00 | 0.00/0.00 | 1.00/1.00 |
| fric | 0.00/0.00 | 1.00/1.00 | 1.00/1.00 | 0.00/0.00 | 0.00/0.00 | 1.00/1.00 |
| solref | 0.00/0.00 | 1.00/1.00 | 1.00/1.00 | 0.00/0.00 | 0.00/0.00 | 1.00/1.00 |
| com | 0.00/0.00 | 1.00/1.00 | 1.00/1.00 | 0.00/0.00 | 0.00/0.00 | 1.00/1.00 |
| condim | 0.00/0.00 | 1.00/1.00 | 1.00/1.00 | 0.00/0.00 | 0.00/0.00 | 1.00/1.00 |

## Same-solver survival (A base vs C base)

| clip | Newton | mjlab |
|---|---|---|
| BMLmovi_Subject_64_F_MoSh_Subject_64_F_9 | 0.00 | 0.00 |
| CMU_76_76_02_poses_120_jpos | 1.00 | 1.00 |
| BMLhandball_S07_Expert_Trial_upper_left_ | 1.00 | 1.00 |
| DFaust_67_50027_50027_one_leg_jump_poses | 0.00 | 0.00 |
| DFaust_67_50025_50025_one_leg_jump_poses | 0.00 | 0.00 |
| CMU_35_35_21_poses_120_jpos | 1.00 | 1.00 |