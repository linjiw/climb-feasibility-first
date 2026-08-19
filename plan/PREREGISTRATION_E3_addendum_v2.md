# Pre-registration addendum v2 — E3 (800-clip bank): bidirectional support-moderation, named in advance

Written 2026-08-18, before E3 launches; supersedes §1 of `PREREGISTRATION_E3_addendum.md`
(kept for the record; sealed `f7929136…`). Method fix first: support must be computed in a
**bank-invariant** way to compare 100 → 800 — z-scaling on the clean bank (8,520 clips) and a fixed
kernel bandwidth h = 2.00 (mixed100's NN spacing in that space) — so the density is a duration
*fraction* of the bank near the clip (`tools/analyze_atlas_support.support_features(..., ref_clips, h)`;
`reports/support_change_heldout100_100to800.csv`). Under the earlier bank-relative scaling all Δ were
negative by construction; that table is void.

## What actually changes 100 → 800 for the held-out clips (bank-invariant support)

| held-out category | n | mean Δlog-support | share of clips gaining support | category mass 100 → 800 |
|---|---:|---:|---:|---:|
| locomotion | 54 | −0.01 | 63 % | 62.3 % → 52.7 % |
| quiet | 23 | −0.47 | 61 % | 22.7 % → 44.7 % |
| **dynamic** | **22** | **−1.99** | **0 %** | 11.8 % → 1.9 % |
| ground | 1 | +0.78 | 100 % | 3.2 % → 0.7 % |

Overall 49 % of held-out clips gain support, median Δ −0.10. The 800 bank is a *quieter* bank: every
dynamic held-out clip loses support (Δ −0.5 to −3.5), most quiet clips gain neighbours even though
their category's share doubles only in mass, and the single ground clip gains because the 800 bank's
nine ground clips are closer to it than mixed100's two.

## The bidirectional, risky predictions (named clips)

Let d_c(bank, arm) be per-clip difficulty under the stratified-start protocol (N4 §3), and
Δ⁸⁰⁰⁻¹⁰⁰_c = d_c(uniform-800) − d_c(uniform-100) (positive = harder at scale).

**P-A (harm, primary):** the 22 dynamic held-out clips — all of which lose support — get **harder**
under uniform-800: mean Δ⁸⁰⁰⁻¹⁰⁰ over the 22 > 0, and ρ(Δ⁸⁰⁰⁻¹⁰⁰_c, Δlog-support_c) ≤ −0.25 over all
100 held-out clips. Named members (dynamic, all losing support):
  - `Eyes_Japan_Dataset_kaiwa_jump-04-horizontal-kaiwa_poses_120_jpos` (dynamic, Δlog-support -0.15)
  - `CMU_35_35_24_poses_120_jpos` (dynamic, Δlog-support -3.32)
  - `SFU_0015_0015_Kirikaeshi001_poses_120_jpos` (dynamic, Δlog-support -1.23)
  - `CMU_127_127_13_poses_120_jpos` (dynamic, Δlog-support -2.83)
  - `CMU_35_35_20_poses_120_jpos` (dynamic, Δlog-support -3.10)
  - `CMU_16_16_35_poses_120_jpos` (dynamic, Δlog-support -2.18)
  - `ACCAD_Male2Walking_c3d_B17_-__Walk_to_hop_to_walk_a_poses_120_jpos` (dynamic, Δlog-support -2.26)
  - `CMU_20_21_rory1_20_10_poses_120_jpos` (dynamic, Δlog-support -2.05)
  - `ACCAD_Female1General_c3d_A15_-_skip_to_stand_poses_120_jpos` (dynamic, Δlog-support -2.71)
  - `Eyes_Japan_Dataset_yamaoka_tennis-18-catch_netball-yamaoka_poses_120_jpos` (dynamic, Δlog-support -2.36)
  - `ACCAD_Male2Walking_c3d_B17_-__Walk_to_hop_to_walk_poses_120_jpos` (dynamic, Δlog-support -2.25)
  - `BMLmovi_Subject_27_F_MoSh_Subject_27_F_11_poses_120_jpos` (dynamic, Δlog-support -0.95)
  - `CMU_35_35_18_poses_120_jpos` (dynamic, Δlog-support -2.85)
  - `CMU_35_35_26_poses_120_jpos` (dynamic, Δlog-support -3.25)
  - `CMU_108_108_18_poses_120_jpos` (dynamic, Δlog-support -2.08)
  - `Eyes_Japan_Dataset_ichige_soccer-29-heel_lift-ichige_poses_120_jpos` (dynamic, Δlog-support -0.98)
  - `CMU_91_91_04_poses_120_jpos` (dynamic, Δlog-support -0.65)
  - `Eyes_Japan_Dataset_hamada_jump-02-leap-hamada_poses_120_jpos` (dynamic, Δlog-support -0.41)
  - `CMU_106_106_04_poses_60_jpos` (dynamic, Δlog-support -1.46)
  - `ACCAD_s007_QkWalk1_poses_120_jpos` (dynamic, Δlog-support -2.92)
  - `CMU_108_108_16_poses_120_jpos` (dynamic, Δlog-support -3.52)
  - `CMU_139_139_11_poses_60_jpos` (dynamic, Δlog-support -0.27)

**P-B (gain):** the 20 largest support gainers get easier (mean Δ⁸⁰⁰⁻¹⁰⁰ < 0):
  - `CMU_137_137_36_poses_120_jpos` (locomotion, Δlog-support +0.86)
  - `CMU_122_122_55_poses_120_jpos` (locomotion, Δlog-support +0.85)
  - `KIT_3_kneel_down_with_right_hand03_poses_100_jpos` (ground, Δlog-support +0.78)
  - `KIT_675_walk_with_table_left04_poses_100_jpos` (locomotion, Δlog-support +0.77)
  - `KIT_291_shake_hand05_poses_100_jpos` (quiet, Δlog-support +0.76)
  - `KIT_1229_hand_through_hair_right_arm_02_poses_100_jpos` (quiet, Δlog-support +0.76)
  - `CMU_144_144_04_poses_120_jpos` (locomotion, Δlog-support +0.76)
  - `KIT_10_WalkInClockwiseCircle08_poses_100_jpos` (locomotion, Δlog-support +0.73)
  - `CMU_106_106_13_poses_60_jpos` (quiet, Δlog-support +0.73)
  - `KIT_969_Trial_30_poses_100_jpos` (quiet, Δlog-support +0.73)
  - `Eyes_Japan_Dataset_kanno_gesture_etc-50-syuriken-kanno_poses_120_jpos` (quiet, Δlog-support +0.72)
  - `KIT_572_wipe_circular_left07_poses_100_jpos` (quiet, Δlog-support +0.72)
  - `Eyes_Japan_Dataset_kanno_pose-19-funny-kanno_poses_120_jpos` (quiet, Δlog-support +0.72)
  - `Eyes_Japan_Dataset_hamada_accident-06-damage_left_leg-hamada_poses_120_jpos` (locomotion, Δlog-support +0.72)
  - `KIT_424_seesaw04_poses_100_jpos` (locomotion, Δlog-support +0.71)
  - `GRAB_s1_toothpaste_pick_all` (quiet, Δlog-support +0.71)
  - `KIT_425_bend_left06_poses_100_jpos` (locomotion, Δlog-support +0.71)
  - `KIT_424_walking_fast08_poses_100_jpos` (locomotion, Δlog-support +0.70)
  - `BMLhandball_S07_Expert_Trial_upper_right_180_poses_120_jpos` (locomotion, Δlog-support +0.70)
  - `GRAB_s5_spherelarge_pick_all` (quiet, Δlog-support +0.70)

**P-C (the 20 largest losers, across categories) get harder** — this list overlaps P-A but adds the
quiet/locomotion clips whose neighbourhoods empty out at 800:
  - `BMLmovi_Subject_32_F_MoSh_Subject_32_F_7_poses_120_jpos` (quiet, Δlog-support -3.74)
  - `CMU_108_108_16_poses_120_jpos` (dynamic, Δlog-support -3.52)
  - `Eyes_Japan_Dataset_takiguchi_jump-05-rope_normal_run-takiguchi_poses_120_jpos` (quiet, Δlog-support -3.39)
  - `CMU_35_35_24_poses_120_jpos` (dynamic, Δlog-support -3.32)
  - `CMU_35_35_26_poses_120_jpos` (dynamic, Δlog-support -3.25)
  - `CMU_35_35_20_poses_120_jpos` (dynamic, Δlog-support -3.10)
  - `BMLmovi_Subject_24_F_MoSh_Subject_24_F_2_poses_120_jpos` (quiet, Δlog-support -3.06)
  - `Eyes_Japan_Dataset_hamada_jump-09-rope_cross-hamada_poses_120_jpos` (locomotion, Δlog-support -2.96)
  - `ACCAD_s007_QkWalk1_poses_120_jpos` (dynamic, Δlog-support -2.92)
  - `CMU_35_35_18_poses_120_jpos` (dynamic, Δlog-support -2.85)
  - `CMU_127_127_13_poses_120_jpos` (dynamic, Δlog-support -2.83)
  - `BMLmovi_Subject_45_F_MoSh_Subject_45_F_19_poses_120_jpos` (quiet, Δlog-support -2.80)
  - `ACCAD_Female1General_c3d_A15_-_skip_to_stand_poses_120_jpos` (dynamic, Δlog-support -2.71)
  - `BMLmovi_Subject_70_F_MoSh_Subject_70_F_3_poses_120_jpos` (quiet, Δlog-support -2.36)
  - `Eyes_Japan_Dataset_yamaoka_tennis-18-catch_netball-yamaoka_poses_120_jpos` (dynamic, Δlog-support -2.36)
  - `ACCAD_Male2Walking_c3d_B17_-__Walk_to_hop_to_walk_a_poses_120_jpos` (dynamic, Δlog-support -2.26)
  - `ACCAD_Male2Walking_c3d_B17_-__Walk_to_hop_to_walk_poses_120_jpos` (dynamic, Δlog-support -2.25)
  - `CMU_16_16_35_poses_120_jpos` (dynamic, Δlog-support -2.18)
  - `CMU_108_108_18_poses_120_jpos` (dynamic, Δlog-support -2.08)
  - `CMU_20_21_rory1_20_10_poses_120_jpos` (dynamic, Δlog-support -2.05)

**P-D (H2b-S, the curriculum interaction):** grounded-800's advantage over uniform-800,
Δᴳ⁻ᵁ_c = d_c(uniform-800) − d_c(grounded-800), is larger on the losers than on the gainers:
mean Δᴳ⁻ᵁ over the P-C list > mean over the P-B list, and ρ(Δᴳ⁻ᵁ_c, Δlog-support_c) ≤ −0.25.

Predicted *harms* (P-A, P-C) are the sharp test: a "diversity helps" story predicts the opposite sign
for the dynamic clips; a "support" story predicts them getting worse while the bank grows eightfold.
If P-A fails (dynamic clips do not get harder) the support account is wrong or the intrinsic
difficulty of dynamic clips saturates the measure — either way reported as a miss.

Everything else in `PREREGISTRATION_E3_addendum.md` (composition as analysed variable, stratified
starts, feasibility flag as launch gate, optional LP arm, non-claims) stands.
