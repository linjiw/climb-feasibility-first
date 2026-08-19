# G1 gate — pre-registered statistics

## Clip-level fragility, raw mean |Δφ| over paired-alive frames (body_pos_err [m])

| axis | BMLmovi_Subject_64_F_MoSh_Subject_ | CMU_76_76_02_poses_120_jpos | BMLhandball_S07_Expert_Trial_upper | DFaust_67_50027_50027_one_leg_jump | DFaust_67_50025_50025_one_leg_jump | CMU_35_35_21_poses_120_jpos |
|---|---|---|---|---|---|---|
| delay | 0.0090 | 0.0041 | 0.0085 | 0.0134 | 0.0108 | 0.0156 |
| motor | 0.0184 | 0.0053 | 0.0117 | 0.0116 | 0.0056 | 0.0189 |
| fric | 0.0089 | 0.0035 | 0.0074 | 0.0070 | 0.0053 | 0.0125 |
| solref | 0.0053 | 0.0029 | 0.0087 | 0.0064 | 0.0044 | 0.0050 |
| com | 0.0092 | 0.0039 | 0.0103 | 0.0060 | 0.0056 | 0.0078 |
| condim | 0.0070 | 0.0026 | 0.0079 | 0.0069 | 0.0054 | 0.0049 |
| *same-solver floor (A base vs C base)* | 0.0061 | 0.0025 | 0.0084 | 0.0054 | 0.0054 | 0.0059 |

## Ratio to matched-easy mean (body_pos_err)

| axis | BMLmovi_Subject_64_F_MoSh_Subject_ | CMU_76_76_02_poses_120_jpos | BMLhandball_S07_Expert_Trial_upper | DFaust_67_50027_50027_one_leg_jump | DFaust_67_50025_50025_one_leg_jump | CMU_35_35_21_poses_120_jpos |
|---|---|---|---|---|---|---|
| delay | 1.43 | 0.64 | 1.36 | 2.12 | 1.72 | 2.48 |
| motor | 2.16 | 0.62 | 1.38 | 1.36 | 0.66 | 2.21 |
| fric | 1.63 | 0.64 | 1.36 | 1.28 | 0.98 | 2.29 |
| solref | 0.91 | 0.50 | 1.50 | 1.10 | 0.75 | 0.85 |
| com | 1.30 | 0.55 | 1.45 | 0.84 | 0.78 | 1.10 |
| condim | 1.33 | 0.50 | 1.50 | 1.31 | 1.04 | 0.92 |

## Termination fragility |P(alive+) − P(alive−)| at clip end

| axis | BMLmovi_Subject_64_F_MoSh_Subject_ | CMU_76_76_02_poses_120_jpos | BMLhandball_S07_Expert_Trial_upper | DFaust_67_50027_50027_one_leg_jump | DFaust_67_50025_50025_one_leg_jump | CMU_35_35_21_poses_120_jpos |
|---|---|---|---|---|---|---|
| delay | 0.00 (0.00/0.00) | 0.00 (1.00/1.00) | 0.00 (1.00/1.00) | 0.00 (0.00/0.00) | 0.00 (0.00/0.00) | 0.00 (1.00/1.00) |
| motor | 0.00 (0.00/0.00) | 0.00 (1.00/1.00) | 0.25 (1.00/0.75) | 0.00 (0.00/0.00) | 0.00 (0.00/0.00) | 0.00 (1.00/1.00) |
| fric | 0.00 (0.00/0.00) | 0.00 (1.00/1.00) | 0.00 (1.00/1.00) | 0.00 (0.00/0.00) | 0.00 (0.00/0.00) | 0.00 (1.00/1.00) |
| solref | 0.00 (0.00/0.00) | 0.00 (1.00/1.00) | 0.00 (1.00/1.00) | 0.00 (0.00/0.00) | 0.00 (0.00/0.00) | 0.00 (1.00/1.00) |
| com | 0.00 (0.00/0.00) | 0.00 (1.00/1.00) | 0.00 (1.00/1.00) | 0.00 (0.00/0.00) | 0.00 (0.00/0.00) | 0.00 (1.00/1.00) |
| condim | 0.00 (0.00/0.00) | 0.00 (1.00/1.00) | 0.00 (1.00/1.00) | 0.00 (0.00/0.00) | 0.00 (0.00/0.00) | 0.00 (1.00/1.00) |

## Peak localisation of F(t) (body_pos_err, 0.5 s smoothing)

| axis | BMLmovi_Subject_64_F_MoSh_Subject_ | CMU_76_76_02_poses_120_jpos | BMLhandball_S07_Expert_Trial_upper | DFaust_67_50027_50027_one_leg_jump | DFaust_67_50025_50025_one_leg_jump | CMU_35_35_21_poses_120_jpos |
|---|---|---|---|---|---|---|
| delay | t=2.5s pk/med=9.0 fail@2.38 | t=0.3s pk/med=2.0 fail@None | t=9.7s pk/med=2.6 fail@None | t=0.6s pk/med=1.4 fail@0.8 | t=0.7s pk/med=2.1 fail@0.62 | t=0.9s pk/med=2.0 fail@None |
| motor | t=2.7s pk/med=1.9 fail@2.2600000000000002 | t=5.0s pk/med=2.3 fail@None | t=5.9s pk/med=3.4 fail@6.0 | t=0.6s pk/med=1.4 fail@0.8 | t=0.7s pk/med=1.3 fail@0.9 | t=0.7s pk/med=1.4 fail@None |
| fric | t=2.6s pk/med=11.5 fail@2.74 | t=7.5s pk/med=2.6 fail@None | t=9.7s pk/med=3.1 fail@None | t=0.6s pk/med=2.0 fail@0.76 | t=0.7s pk/med=2.5 fail@0.88 | t=1.0s pk/med=1.2 fail@None |
| solref | t=2.6s pk/med=5.2 fail@2.74 | t=7.5s pk/med=2.4 fail@None | t=9.7s pk/med=4.7 fail@None | t=0.6s pk/med=1.9 fail@0.78 | t=0.7s pk/med=2.3 fail@0.92 | t=0.4s pk/med=1.5 fail@None |
| com | t=2.7s pk/med=7.8 fail@2.8000000000000003 | t=7.5s pk/med=2.0 fail@None | t=9.7s pk/med=5.3 fail@None | t=0.6s pk/med=1.7 fail@0.78 | t=0.7s pk/med=1.6 fail@0.92 | t=0.3s pk/med=1.2 fail@None |
| condim | t=2.7s pk/med=6.4 fail@2.9 | t=7.5s pk/med=3.2 fail@None | t=9.7s pk/med=5.0 fail@None | t=0.6s pk/med=1.5 fail@0.8 | t=0.7s pk/med=2.0 fail@0.92 | t=0.3s pk/med=1.8 fail@None |

## EXPLORATORY (not pre-registered): signed effect, mean over replicates of time-mean (φ⁺−φ⁻), body_pos_err [m], 95% paired bootstrap CI

| axis | BMLmovi_Subject_64_F_MoSh_Subject_ | CMU_76_76_02_poses_120_jpos | BMLhandball_S07_Expert_Trial_upper | DFaust_67_50027_50027_one_leg_jump | DFaust_67_50025_50025_one_leg_jump | CMU_35_35_21_poses_120_jpos |
|---|---|---|---|---|---|---|
| delay | +0.0017 [-0.0017,+0.0048] | +0.0011 [-0.0000,+0.0024] | +0.0024 [+0.0008,+0.0038]* | +0.0032 [-0.0053,+0.0113] | +0.0063 [+0.0026,+0.0103]* | +0.0119 [+0.0085,+0.0162]* |
| motor | +0.0115 [+0.0092,+0.0138]* | -0.0026 [-0.0036,-0.0015]* | -0.0046 [-0.0095,-0.0004]* | -0.0109 [-0.0143,-0.0080]* | -0.0008 [-0.0034,+0.0021] | -0.0142 [-0.0174,-0.0121]* |
| fric | +0.0004 [-0.0021,+0.0030] | -0.0007 [-0.0016,+0.0003] | +0.0002 [-0.0014,+0.0022] | -0.0048 [-0.0072,-0.0025]* | -0.0028 [-0.0046,-0.0006]* | -0.0091 [-0.0186,-0.0017]* |
| solref | -0.0019 [-0.0036,-0.0004]* | +0.0005 [-0.0005,+0.0014] | -0.0024 [-0.0048,+0.0002] | +0.0031 [-0.0006,+0.0064] | -0.0023 [-0.0042,-0.0005]* | +0.0018 [+0.0007,+0.0030]* |
| com | -0.0023 [-0.0040,-0.0005]* | -0.0006 [-0.0017,+0.0005] | -0.0034 [-0.0055,-0.0010]* | +0.0006 [-0.0030,+0.0045] | -0.0002 [-0.0030,+0.0023] | -0.0011 [-0.0080,+0.0042] |
| condim | +0.0001 [-0.0010,+0.0012] | +0.0006 [-0.0004,+0.0018] | -0.0004 [-0.0024,+0.0013] | +0.0029 [-0.0011,+0.0065] | +0.0020 [-0.0012,+0.0049] | -0.0012 [-0.0046,+0.0019] |

(* = CI excludes zero; sign: + means the +δ world tracks worse)

## Survival at clip end, +δ / −δ (or +δ / base)

| axis | BMLmovi_Subject_64_F_MoSh_Subject_ | CMU_76_76_02_poses_120_jpos | BMLhandball_S07_Expert_Trial_upper | DFaust_67_50027_50027_one_leg_jump | DFaust_67_50025_50025_one_leg_jump | CMU_35_35_21_poses_120_jpos |
|---|---|---|---|---|---|---|
| delay | 0.00/0.00 | 1.00/1.00 | 1.00/1.00 | 0.00/0.00 | 0.00/0.00 | 1.00/1.00 |
| motor | 0.00/0.00 | 1.00/1.00 | 1.00/0.75 | 0.00/0.00 | 0.00/0.00 | 1.00/1.00 |
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