# Pre-registration — G1: the clip #44 gate (PhysFrag Phase 1)

**Written:** 2026-08-17 21:30 EDT, before any paired-counterfactual rollout exists.
**Plan:** `RESEARCH_PLAN_v4_PhysFrag.md` §Phase 1 / Gate G1, and the v4 closing
instruction: *"立刻跑 clip #44 gate：同一 policy、同一 initial state，只改变 delay、motor
strength、friction、contact model 和 torso CoM。"*
**Supersedes** the multi-solver framing of `PREREGISTRATION_S3_clip44.md`
(v3 §6). Multi-solver disagreement is demoted per v4; the contact-anatomy audit
and the (a)/(c) predictions in S3 remain in force and are re-used below.

## Pins

| item | value |
|---|---|
| policy | `logs/rsl_rl/g1_tracking/2026-08-15_20-29-21_uniform-mixed100-s1/model_3999.pt`, sha256 `6099a7072afdcfa4…` |
| physics | Newton `7bb6d02d` (1.6.0.dev0), mujoco_warp 3.11.0, mujoco 3.11.0, warp 1.16.0; mjlab worktree v1.6.0 |
| robot | mjlab `unitree_g1/xmls/g1.xml` sha256 `febdcbeffbbf8405…`, 34 collision geoms (14 foot capsules condim 3, μ 0.6, priority 1; 19 non-foot geoms **condim 1 = frictionless**; ground plane μ 1.0) |
| harness | `tools/s1_newton_conformance.py::NewtonPhysics` (MJWarp backend, `update_data_interval=0`, DR mirror + exact-geometry mirror), extended by `tools/g1_clip44_gate.py` |
| control | dt 0.02 s = 4 × 0.005 s substeps, mjlab obs/policy/actions/terminations unchanged |
| clips | `plan/G1_clips.txt` (drawn 2026-08-17 before this document) |

Every rollout in G1 runs on Newton/SolverMuJoCo. G0 must be closed *before* the
gate is run (see "G0 dependency" at the end); the same-solver residual measured
in that closure is the noise floor of everything below.

## Clips (fixed) — with the atlas row that motivated each

| role | clip | uniform-control survival | atlas signature (bank percentiles) |
|---|---|---:|---|
| **#44** | `BMLmovi_Subject_64_F_MoSh_Subject_64_F_9_poses_120_jpos` (9.98 s) | 0.31 | `nonfoot_ground_frac` 0.61 (**100%**), `support_margin_mean` −0.48 (5%), speed 51%, jerk 80% — kneel/crawl, floor contact 1.8–7.9 s |
| matched easy | `CMU_76_76_02_poses_120_jpos` (9.7 s) | 1.00 | speed 58%, jerk 84%, `nonfoot_ground_frac` 0, μ 80% — same duration & kinematic intensity, feet only |
| matched easy | `BMLhandball_S07_Expert_Trial_upper_left_right_037_poses_120_jpos` (13.3 s) | 1.00 | speed 29%, jerk 81%, upper-body dominant, feet only |
| ordinary hard | `DFaust_67_50027_50027_one_leg_jump_poses_60_jpos` (4.3 s) | 0.44 | `required_mu_p95` 94%, `vert_force_bw_max` 92%, single support |
| ordinary hard | `DFaust_67_50025_50025_one_leg_jump_poses_60_jpos` (5.4 s) | 0.31 | `required_mu_p95` 95%, `vert_force_bw_max` 96%, single support |
| high-dynamic, atlas-hard | `CMU_35_35_21_poses_120_jpos` (1.34 s) | — | speed **99%**, jerk 98%, μ 96% |

## Base configuration (the "nominal" robot)

- mjlab startup DR **disabled** for this gate (`base_com`, `foot_friction`,
  `encoder_bias`) so that every world shares one nominal robot and the
  observation pipeline is identical across the paired worlds. All three lie
  inside the training distribution, so nominal is in-distribution for the policy.
- No push events, no observation noise (as in S1).
- Terminations: mjlab's `anchor_pos`, `anchor_ori`, `ee_body_pos` (unchanged).

## Interventions (k = 1..6) and magnitudes δ_k — fixed now

Paired worlds τ^{+δ} and τ^{−δ} around the base value; F normalised by the
parameter distance (2δ), or by δ where the axis is one-sided.

| k | axis | base | −δ | +δ | mechanism / how applied |
|---|---|---|---|---|---|
| 1 | action delay | 0 ms (as trained) | (base) | **+20 ms** = one control step, one-sided | per-world ctrl FIFO in `substep_from_ctrl` (delayed PD targets) |
| 2 | motor strength | ×1.0 | ×0.85 | ×1.15 | scale `actuator_gainprm[0]`, `biasprm[1:3]`, `forcerange` (whole PD torque + clamp) |
| 3 | contact friction | foot μ 0.6 | 0.4 | 0.8 | `geom_friction[:,0]` of the 14 foot capsules (priority 1 ⇒ rules the pair) |
| 4a | contact stiffness | solref τ 0.020 s | 0.012 | 0.028 | `geom_solref[:,0]` of all robot geoms + ground (impedance timeconst) |
| 4b | contact **model** | non-foot geoms condim 1 | (base) | **condim 3, μ 0.6**, one-sided | knee/hand/torso contacts become frictional (`geom_condim`) — the sim2real-relevant model change for a kneel/crawl clip |
| 5 | torso CoM | nominal `body_ipos[torso_link]` | −2 cm x | +2 cm x | sagittal CoM shift; DR trains ±2.5 cm |

Ten worlds per (clip, initial condition): base, k1+, k2±, k3±, k4a±, k4b+, k5±.

## Initial conditions

R = 8 replicate initial conditions per clip: frame-0 teleport (as in S1) plus
per-replicate noise drawn once and applied identically to that replicate's ten
worlds: joint position U(−0.05, 0.05) rad, root linear velocity U(−0.1, 0.1) m/s,
root angular velocity U(−0.2, 0.2) rad/s. The first observation is recomputed
after the teleport (S1 lesson). Seed 0. Total 6 × 8 × 10 = 480 worlds, one run.

## φ — the interpretable metric vector, per control step, per world

| j | metric | source |
|---|---|---|
| root_pos_err [m] | `error_anchor_pos` | mjlab command metrics |
| root_ori_err [rad] | `error_anchor_rot` | " |
| body_pos_err [m] | `error_body_pos` (mean over tracked bodies) | " |
| joint_pos_err [rad] | `error_joint_pos` | " |
| foot_contact (L,R) | any foot capsule at dist < 0 (Newton contact list) | Newton `mjw_data.contact` |
| foot_slip [m/s] | planar ankle-roll body speed while that foot is in contact | body xpos differences |
| target_gap [rad] | mean |ctrl − q| over actuated joints | mjlab ctrl, qpos |
| effort_sat | fraction of actuators with |force| ≥ 0.98·forcerange | Newton `actuator_force` |
| alive | not terminated | mjlab termination manager |

Distances: absolute difference for continuous metrics; Hamming (0/1 per foot)
for contact state; termination fragility = |P(alive⁺) − P(alive⁻)| over replicates.

## Statistics — decided now

1. **F_{m,t,k,j}** = mean over replicates c of |φ_j(τ⁺) − φ_j(τ⁻)| / (2δ_k), on
   control steps where *both* paired worlds are alive (paired-alive frames).
2. **Clip-level fragility** F̄_{m,k,j} = time-mean of F over paired-alive frames.
   Reported in raw units *and* as a ratio to the mean of the two matched-easy
   clips (same k, j).
3. **Localisation**: the time of the F peak (0.5 s smoothing) relative to (i)
   the first termination among the ±δ worlds and (ii) the S3 audit windows.
4. **Noise floor**: F_resid = same quantity computed between the *baseline*
   world of the Newton arm and the *baseline* world of a stock-mjlab arm from
   the identical (obs, state) — the G0 same-solver residual on these clips. A
   signal is reported only if F̄ ≥ 5 × F_resid for that (k, j).

## Predictions (H2 of v4) — recorded before the run

- **P1 (mechanism, primary):** clip #44's clip-level fragility on the *contact
  model* axis (k4b) and the *torso CoM* axis (k5) is ≥ 2× the matched-easy mean
  for at least one of {root_ori_err, body_pos_err, alive}. Its delay (k1) and
  motor (k2) fragility are *not* elevated (< 1.5×) relative to the easy pair.
- **P2 (localisation, primary):** the #44 fragility peak lies in the ground-
  support transitions [1.4, 2.4] s ∪ [7.4, 8.4] s or in the knee-loaded interval
  and *precedes* the first termination.
- **P3 (distinct signature):** the two `one_leg_jump` clips are most fragile to
  motor strength (k2) and delay (k1); `CMU_35_35_21` to delay/motor; neither is
  elevated on k4b. So #44's profile is distinguishable from ordinary-hard.
- **P4 (S3 carried over):** if #44 shows *no* between-configuration spread on any
  axis while failing in all worlds, the reference itself is the problem
  (impossible reference / retarget artefact), per S3's (a).

## Decision rule for the gate

**G1 passes** iff P1 and P2 hold and P3 gives a profile for #44 that differs
from both ordinary-hard clips on at least one axis by ≥ 2×.

**G1 fails** if #44's mechanism profile is < 1.5× the easy pair on every axis, or
if it is elevated but not localised (flat in time). Then, per v4, before any
expansion to 200/800/10,822 clips: check tracking-reward/termination artefacts,
reference corruption (the S3 penetration audit is 98th percentile but under the
screen), initialisation, impossible reference, and policy representation
failure. The plan explicitly forbids widening the clip set to rescue the gate.

## G0 dependency and residual budget

The gate is meaningful only under the v4 discipline that any Newton-vs-mjlab
discrepancy under the *same solver* is integration error. G0 status at sealing
time: three integration errors found and fixed today (mjlab's per-env DR was
never mirrored into Newton — 3.3 N·m base gravity-torque residual; float32
geometry rounding decided a knife-edge frictional foot contact — 0.06–3.3 rad/s
substep forks; first observation was stale w.r.t. the frame-0 teleport). Per-
substep paired physics now agrees to |Δqvel| ≤ 3e-5 across the KIT_1226 impact
and to zero contact-count mismatches over 300 steps × 8 worlds. The closed-loop
survival re-run is in progress; **G1 does not run until it conforms**, and the
residual it reports becomes F_resid's expected order of magnitude.

## Frozen while G1 runs (v4)

E3/E4, E10, the sampling ledger, SONIC training, S2 (Featherstone/XPBD), any
differentiable-contact spike. Nothing here touches training.

## Addendum 2026-08-17 22:25 EDT (before the gate run) — G0 closed

G0 closed after a fourth integration error (one-directional coupling missed
mjlab-side state writes such as the clip-wrap teleport; see `S1_RESULT.md`
fix 11). KIT_1226 n=32: Newton 1.000/1.000 vs mjlab 1.000/1.000 (Δerr −0.0005);
clip #44 0.000 vs 0.000 (Δerr +0.001). The G1 harness therefore runs with the
absorb mechanism on; the pre-registered noise floor (arm C vs arm A base worlds)
is unchanged. Horizon: 10 s; each clip is analysed only up to its own length
(clip lengths recorded in `meta.json`); the CMU_35_35_21 clip is 1.34 s, so its
statistics rest on 67 control steps. Nothing else changes.
