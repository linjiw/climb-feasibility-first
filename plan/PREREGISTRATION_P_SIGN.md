# Pre-registration — P-SIGN: the motor-strength sign reversal as an infeasibility signature

**Sealed:** 2026-08-19, before any rollout of this design exists. Per D3 of the 2026-08-19
directive. **Runs only in genuine GPU gap capacity through the shared queue** (CPU-only rule until
2026-09-15 otherwise).

## Hypothesis

On references whose transitions are dynamically infeasible (airborne, unsupported), increasing
motor strength makes tracking *worse* inside the infeasible windows and not elsewhere — "a
stronger robot executes wrong actions harder." Observed twice on clip #44 (run0 and the seed-1
replication: standing ≈ 0 / airborne +15.0 and +16.0 mm; `plan/N5_RESULT.md`). This seal tests
generality on the family.

## Design

- Harness: `tools/g1_clip44_gate.py` machinery restricted to configs {base, motor−15 %, motor+15 %}
  plus a stock-mjlab arm (per-run floor), policy `uniform-mixed100-s1/model_3999.pt`
  (sha `6099a707…`), nominal robot, R = 8 replicate ICs, 10 s horizon truncated to clip length.
- Statistic: the calibrated N5 statistic — signed replicate-mean effect S = E_r[mean_t(φ⁺ − φ⁻)]
  on `body_pos_err`, windowed, with the identical-physics floor (Newton-base vs mjlab-base)
  computed **per run** and published alongside.
- Windows per clip from the full (non-brief) screen `tools/n1_knee_id.py` at gap 6 cm:
  *airborne* = frames with no contact candidate within 6 cm while |torque-limited unsupported
  wrench| > 0.5·weight, dilated ±0.1 s; *standing/supported* = frames with unsupported ≤ 0.1·weight,
  same dilation, non-overlapping with airborne. Windows are computed from the reference only —
  before and independently of any rollout.

## Clips (fixed now)

**Family (N1-flagged), the 12 highest `infeasible_frac` of the 20 flagged among the 40 atlas-nearest
neighbours of #44** (`reports/N3_candidate_feasibility.json`; the directive's "12 N1-flagged" is
honoured as this explicit list — note the correction recorded in `GLOBAL_EVAL_ADDENDUM.md`: 20 of
40 exceed the 10 % threshold, and the 12 sealed here are the strongest cases):

| clip | infeasible_frac |
|---|---:|
| BMLmovi_Subject_39_F_MoSh_Subject_39_F_8_poses_120_jpos | 0.367 |
| BMLmovi_Subject_41_F_MoSh_Subject_41_F_20_poses_120_jpos | 0.277 |
| CMU_111_111_03_poses_120_jpos | 0.258 |
| BMLmovi_Subject_72_F_MoSh_Subject_72_F_21_poses_120_jpos | 0.215 |
| CMU_22_23_Rory_22_03_poses_120_jpos | 0.213 |
| BMLmovi_Subject_8_F_MoSh_Subject_8_F_6_poses_120_jpos | 0.210 |
| BMLmovi_Subject_27_F_MoSh_Subject_27_F_5_poses_120_jpos | 0.208 |
| BMLmovi_Subject_48_F_MoSh_Subject_48_F_16_poses_120_jpos | 0.199 |
| BMLmovi_Subject_51_F_MoSh_Subject_51_F_12_poses_120_jpos | 0.196 |
| BMLmovi_Subject_11_F_MoSh_Subject_11_F_21_poses_120_jpos | 0.196 |
| BMLmovi_Subject_24_F_MoSh_Subject_24_F_11_poses_120_jpos | 0.191 |
| BMLmovi_Subject_45_F_MoSh_Subject_45_F_20_poses_120_jpos | 0.190 |

**Feasible matched controls, same (ground) category, `infeasible_frac ≤ 0.10`** — the first 12 of
`bank/tiers/aug_ground16.txt` (sealed `e489f1b8…`) in its atlas-proximity order.

Worlds: 24 clips × 8 ICs × 3 configs = 576 (arm A) + 24 × 8 (arm C floor) — one run, ~25 min.

## Sealed pass criteria (all three required to "pass")

(i) **Generality:** S(motor, airborne window) ≥ +5 mm with a 95 % paired-bootstrap CI excluding
zero on **≥ 8 of the 12** family clips.
(ii) **Specificity:** |S(motor, whole clip)| < 2 mm on ≥ 8 of the 12 feasible matched controls
(controls have no airborne windows by construction; whole-clip S is the comparable quantity).
(iii) **Localisation:** per family clip, |S(airborne)| ≥ 3 × |S(standing)| for the clips passing (i).

Pass → the paper gains a "rollout-only infeasibility detector" subsection (§9 slot) and the
signature becomes a candidate runtime guard (deployment: if tightening gains worsens tracking in a
segment, suspect the reference). Fail → the finding remains exactly one parked paragraph
(`plan/PARKING.md`), reported with its two supporting cases and this null.

Confounds pre-listed: family clips are all BMLmovi/CMU kneel-sit retargets — a pass generalises
within this family only (stated in any write-up); airborne windows correlate with high descent
speed, so the control comparison (same category, feasible) is the discriminator, not the standing
window alone.
