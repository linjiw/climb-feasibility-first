# Actuator-model sensitivity of the feasibility screen — design, declared before the outcome

**Status: prospective design, written before the tightened conditions were run.** 8 September 2026.
Unsealed. Changes no existing contract, threshold, arm, seed, endpoint or published result. CPU
only; no GPU job, no training, no policy, no held-out endpoint.

## Why this experiment, and why now

The manuscript and the public page both state that the reported flag counts are a **lower bound**
with respect to any tighter actuator model. That statement currently rests on an argument, not a
measurement: tightening a force range can only shrink the feasible set of the torque-limited
contact program, so the residual can only grow and the flagged fraction can only rise.

An adversarial verification pass on 7 September established two things that make this worth
measuring. First, `refeas/examples/g1_flat.xml` carries `forcerange="-139 139"` on both knees and
both hip rolls, the same limits as the training model, so the screen's actuator channel is
optimistic by construction. Second, the vendor knee maxima this project records (90 N·m and
120 N·m for two G1 revisions) appear only as a hand-entered block in
`reports/icra_evidence_2026-09-06/physics_audit.json`, with no archived source and no established
correspondence between those figures and the compiled limit. The comparison is therefore a
recorded discrepancy, and the honest way to use it is as a *sensitivity axis* rather than as a
claim about a physical motor.

This experiment converts the lower-bound argument into a measured quantity, costs no GPU time, and
is rung 2 of the deployment ladder in `fable.md` rev 5.

## Reproduction gate, verified before any tightened condition ran

All 900 clips in the local Phase-G bank appear in the published 10,705-clip screen
(`reports/feasibility_all/feasibility.csv`). Running the released screen at the baseline limit on
`ACCAD_Female1General_c3d_A5_-_pick_up_box_poses_120_jpos` reproduces its published row exactly:
frames 314, fps 50.0, `airborne_frac` 0.20382165605095542, `infeasible_frac` 0.20382165605095542,
`torque_infeasible_frac` 0.0.

**Gate:** the baseline condition must reproduce all 900 published rows to within 1e-12 on
`infeasible_frac`, `airborne_frac` and `torque_infeasible_frac`. If it does not, the run is
reported as `not_tested` and no sensitivity number is quoted. This gate is what licenses
attributing any measured change to the actuator limit alone.

## Design

| item | value |
|---|---|
| Clips | all 900 `.npz` in `bank/amass` (the Phase-G bank: 800 training plus the 100-clip held-out panel) |
| Conditions | knee and hip-roll `forcerange` at ±139 N·m (baseline, unchanged), ±120, ±90 |
| Held fixed | contact band `gap` 0.06 m; friction `mu` 0.6; whole clip; `--brief` clip-level features; all other actuator ranges unchanged |
| Instrument | `refeas/refeas/screen.py`, unmodified, pointed at three model files that differ only in those four `forcerange` attributes |
| Primary readout | flagged clip count under the manuscript's strict rule, `infeasible_frac > 0.10`, per condition |
| Secondary | mean and maximum `torque_infeasible_frac`; number of clips changing flag status; per-clip `infeasible_frac` deltas |

Only the four `forcerange` attributes change between conditions. Nothing else in the model, the
screen, the bank or the parameters is touched.

## Pre-declared prediction, and what would falsify it

**Prediction.** The flagged count is non-decreasing as the limit tightens, 139 → 120 → 90, and no
individual clip's `infeasible_frac` decreases by more than 1e-9 under tightening.

**Falsification.** Any clip whose `infeasible_frac` falls by more than 1e-9 when the limit is
tightened contradicts the monotonicity argument that the manuscript and the public page now rely
on. If that occurs, the lower-bound sentence must be withdrawn from both, and the cause diagnosed
before any replacement claim is made. A tolerance of 1e-9 is declared because the torque-limited
step is solved numerically.

**What a null looks like.** If the flagged count does not move at all, the honest reading is that
the screen's decisions on this bank are dominated by the unsupported-wrench residual rather than
by the actuator channel, and the lower bound is tight here. That is a useful result and will be
reported as such.

## Scope limits, declared in advance

- This measures the 900-clip Phase-G bank, **not** the 10,705-clip corpus behind the manuscript's
  22.8% headline. That corpus is not present locally. Any sensitivity reported here describes this
  bank and must not be transferred to the headline rate without re-running it there.
- The 120 and 90 N·m levels are the figures this repository records for two G1 revisions. They are
  used here as declared stress levels on an axis, not as calibrated hardware values, and this
  experiment establishes nothing about a physical motor.
- Tightening the knee and hip-roll ranges together follows the compiled model, in which both share
  the `7520-22` actuator group. A knee-only variant would require splitting that group and is not
  attempted here.
- The screen's other declared exclusions are unchanged: electrical, thermal, compliance, latency
  and structural limits remain outside the label.
