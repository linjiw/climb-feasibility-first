# S1 / G0 — Newton ↔ mjlab same-solver conformance

**Date:** 2026-08-17 (revised 2026-08-17 late under Plan v4 G0 discipline).
**Verdict (revised): the step-298 "contact-event fork" was integration error,
not physics.** Three further silent mismatches were located and fixed; the
per-substep physics now agrees to |Δqvel| ≤ 3e-5 across the impact and to zero
contact-set mismatches over 300 steps × 8 worlds. The closed-loop survival
re-run under the fixed harness is the G0 close-out (see "G0 close-out" below).

The earlier verdict "PASS with a localised contact-event discrepancy that is
itself a fragility measurement" is withdrawn: v4 says any same-solver
discrepancy is to be treated as integration error, and it was.

## Result

Frozen policy `uniform-mixed100-s1/model_3999`, mjlab owns obs/policy/
terminations, Newton owns physics. Same compiled MjSpec, same runtime solver
options, no obs noise, no pushes.

| clip | arm | survival | mean steps | body-pos err | Δerr vs mjlab |
|---|---|---:|---:|---:|---:|
| KIT_1226 (mastered), n=32 | mjlab | 1.000 | 500 | 0.0369 | — |
| | Newton MJWarp | 0.719 | 446 | 0.0375 | +0.0006 |
| KIT_1226, n=1 | mjlab | 1.000 | 500 | 0.0364 | — |
| | Newton MJWarp | 1.000 | 500 | 0.0348 | −0.0016 |
| | Newton MuJoCo-C | 1.000 | 500 | 0.0347 | −0.0017 |
| clip #44 (frontier), n=32 | mjlab | 0.000 | 139 | 0.1261 | — |
| | Newton MJWarp | 0.000 | 148 | 0.1326 | +0.0065 |

Peak body-position error over the episode (32 eps, KIT_1226): mjlab p90 0.275 /
max 0.364; Newton p90 0.148 / max 0.187. **Newton tracks slightly better than
mjlab on the mean.**

## The residual: a contact-event fork at step 298–299

The 0.719 survival on the mastered clip is not drift. Steps 280–297 are
identical to three decimals; at step 298 *both* engines see the reference jump
(end-effector error 0.076 → 0.150 in both) — a hard instant in the clip. One
substep later mjlab's worst env sits at 0.149 while Newton's worst is at
**0.381**, above the 0.25 `ee_body_pos` threshold. By step 310 Newton is back to
0.175: it did not fall, it briefly overshot at the moment of impact.

Both engines run mujoco_warp 3.11.0. So this is a genuine solver-configuration
sensitivity at a contact event — Newton and mjlab configure the MJWarp contact
pipeline differently (contact capacity, CCD defaults, `mjDSBL_MULTICCD` set on
Newton's side) and at a hard impact those choices fork the outcome for ~30% of
episodes. That is exactly the object T1 is meant to measure, showing up in the
conformance test. It is recorded, not patched away: characterising it belongs to
S2b's within/between-config decomposition, and the KIT_1226 step-298 event is a
ready-made probe point.

## Six bugs found on the way — every one a silent convention mismatch

Each produced a plausible, wrong result; none raised. Listed because they are
exactly the failures a Newton evaluation harness for *any* mjlab policy will hit.

| # | symptom | cause | fix |
|---|---|---|---|
| 1 | reference arm itself died at 0.2 s | wrong test clip — a LAFAN1 clip the policy never trained on | use a clip from the policy's own bank |
| 2 | 29 joints "fell" under a pure hold | Newton built **58 actuators**: 29 imported from the spec + 29 synthesised from `joint_target_ke/kd`. The imported ones got no ctrl and pulled toward zero. | do not set target gains; the imported actuators already carry mjlab's kp/kd/forcerange |
| 3 | still fell after fix 2 | imported `<position>` actuators are `CTRL_DIRECT`: they read `control.mujoco.ctrl`, not `joint_target_q`. `mjw_data.ctrl` was all zeros. | write `control.mujoco.ctrl` (same MJCF actuator order as mjlab's `ctrl`) |
| 4 | 180° pelvis error every substep, joint velocities already agreeing to 0.02 rad/s | quaternion writeback used the *forward* permutation instead of its inverse (xyzw→wxyz is (3,4,5,6)←(6,3,4,5), not (4,5,6,3)) | — superseded by fix 6 |
| 5 | robot bounced on the ground (z 0.76–0.81 vs flat 0.772) | `builder.rigid_gap` defaults to **0.1 m** and is applied to every shape incl. the ground plane; mjlab uses gap 0 | `rigid_gap = 0`, `default_shape_cfg.gap = 0`, ground plane with mjlab's params |
| 6 | 0.64 rad/s disagreement on base angular-x at **substep 0**, before any dynamics | Newton's free-joint `joint_qd` is world-frame ω and COM-referenced v; MuJoCo's is body-frame ω and joint-origin v | stop round-tripping through Newton's joint state: sync mjlab `qpos/qvel` **directly into `solver.mjw_data`** with `update_data_interval=0`. Same layout, same conventions, no conversion at all |
| 7 | 5/16 envs died at exactly step 299 with *lower* tracking error than mjlab | calling `forward()` after writeback made derived quantities one substep *fresher* than stock mjlab, whose terminations are calibrated to the stale read | mirror Newton's derived arrays instead of recomputing |

Fixes 6 and 7 are the architecture: **MuJoCo state ↔ MuJoCo state, and mjlab
sees exactly what its own step would produce.** Newton's Newton-side
representation is bypassed entirely for the sync, which is both simpler and
correct.

Also established along the way, all verified equal between the two MjModels:
joint order, actuator→joint map, kp/kd/forcerange, masses, inertias, joint axes
and positions, contact friction/solref/solimp/condim, 34 collision geoms, 141
collidable body pairs, integrator, solver, iterations. Newton's importer is
faithful; the mismatches were all at the *interface*.

## Two things Newton should know about (not filed yet)

- `SolverMuJoCo.get_max_contact_count()` raises `NotImplementedError` on the
  MuJoCo-C backend. Trivial to work around; worth a one-line implementation or a
  clearer error.
- The `robot_policy` example sets `builder.rigid_gap = 0.0` without comment. A
  0.1 m default gap silently changes contact behaviour for any imported MJCF
  robot; the importer could either inherit the MJCF's `gap` (0 by default) or
  warn.

## What S1 unlocks

- **S2** can proceed: same harness, `SolverFeatherstone` / `SolverXPBD` in
  place of `SolverMuJoCo`. The bank/policy/obs path is proven.
- **S2b** has a probe point already: KIT_1226 step 298 is a measured contact
  event where two configurations of the *same* solver fork. The
  within/between-config decomposition can be validated on it before touching
  clip #44.
- **The CPU rung is real**: MuJoCo-C agrees with MJWarp to 0.0001, so
  "MJWarp → CPU MuJoCo" is a working ladder step inside one process.
- The bridge environment (`/data/robotixx/climb/bridge/.venv`) holds mjlab +
  Newton + torch cu128 in one interpreter and is the runtime for everything
  eval-side from here.

## G0 close-out (2026-08-17, after v4)

Under v4 the 0.44–0.72 vs 1.00 survival split on KIT_1226 could not stand as a
"fragility measurement". Systematic elimination — model diff, static and
spinning bias forces, per-substep paired stepping across the impact, contact-set
diffs, and MuJoCo-C as a third referee — found three more integration errors:

| # | symptom | cause | evidence | fix |
|---|---|---|---|---|
| 8 | 3.3 N·m residual in `qfrc_bias` on the free-joint angular dofs from *identical* (q, qd), even at qvel = 0 | mjlab's **startup domain randomisation** (`base_com` ±2.5/5/5 cm on torso `body_ipos`, `foot_friction` 0.3–1.2, `encoder_bias`) is applied to `env.sim.wp_model` after compile, per env, and never reaches the spec that Newton was built from. Newton integrated the nominal G1; mjlab the randomised one. My earlier "all inertials equal" check compared the pristine CPU `mj_model` and so could not see it. | exported XML loaded straight into MuJoCo reproduces *Newton's* torque `[0.03, −6.65, 0]`, mjlab's live model gives `[−2.79, −8.24, 0]` — a ~1 cm whole-body CoM shift | mirror every mjlab-expanded field (`body_ipos`, `geom_friction`, `body_subtreemass`, `*_invweight0`, `actuator_acc0`) into Newton's MJWarp model through name-based index maps, then `mjw.set_const` (`NewtonPhysics._mirror_mjlab_model_fields`). Static bias residual → 2.9e-6 |
| 9 | Newton-driven rollouts still forked (0.41–0.59 survival) although per-substep stepping from mjlab's states agreed to 2e-5 | **float32 geometry rounding**: Newton's import path (MJCF → `wp.transform` → MjSpec → MJWarp) leaves `geom_quat` 4e-7, `body_pos` 3e-7, `geom_size` 4e-8, `dof_armature` 2e-8 off mjlab's float64-exact values. Physically nothing — but a lightly loaded foot capsule rests at contact distance ≈ 0 and MuJoCo includes a contact iff dist < 0, so the offset decides whether a **frictional** foot contact exists. | at every disagreeing substep Newton carried exactly one extra `ground_plane`–`right_foot*` contact with dist −0.0 at the capsule endpoint; MuJoCo-C from the same pre-state agreed with mjlab to 1e-3 and disagreed with Newton by 0.05–3.3 rad/s | copy mjlab's exact float32 `geom_pos/quat/size/rbound/aabb`, `body_pos/quat/ipos/iquat/inertia/mass`, `jnt_pos/axis`, `dof_armature` into Newton's MJWarp model, `set_const` (`_mirror_exact_geometry`). Shadow test: **0 mismatches** over 300 steps × 8 worlds |
| 10 | first action of every episode was a random kick, different per arm and per run | `assign_clips(at_start=True)` teleports the robot to frame 0 *after* `reset()` computed its observation; the stale obs described a random clip time ± noise (joint_pos differed by up to 1.15 rad between two resets) | `|Δobs0|` = 3.4–4.5 between arms with `|Δq0|` = 0 | recompute the observation after the teleport (`env.sim.forward(); wrapped.get_observations()`) |

Also verified equal along the way (so they are *not* the cause): all `opt.*`
fields at runtime, contact pair-filter matrix (469 robot–robot + 33 ground
pairs), joint limits/armature/damping, actuator gains and clamps, forward-only
contacts at identical states, and — decisively — one substep from identical
(q, qd, ctrl, warmstart) at *every* substep of the impact window 290–312:
|Δqvel| ≤ 3e-5, |Δqfrc_constraint| ≤ 0.026 of 836 N, identical `nefc`/`nacon`.
The mjlab arm is also insensitive to calling `forward()` after every substep
(`mjlab_fwdsub` arm: 1.000), so protocol staleness is not a factor.

Fix 7 in the table above is thereby reinterpreted: the "stale vs fresh" story
was a red herring; the survival split it seemed to explain was fixes 8–9.

| 11 | after fixes 8–10 the survival split persisted (0.50–0.59) although a MuJoCo-Warp *shadow* stepping from Newton's own states matched Newton at 1279 of 1280 substeps | **the coupling was one-directional.** KIT_1226 is a **6.0 s clip**; step 299 = 5.98 s is the clip **wrap**, where `MultiClipMotionCommand._update_command` → `_resample_command` *teleports* the robot onto a freshly sampled reference frame by writing `qpos/qvel` into mjlab's sim. mjlab's arm gets teleported; Newton's arm had that write overwritten by its own physics one substep later and then had to chase a reference that had jumped → 40–60% exceeded `ee_body_pos`. Auto-reset of terminated envs and `push_robot` write state the same way. There never was a contact-event fork. | body_pos_err jumps 0.034 → 0.16 (median 0.09) for *all* Newton worlds at step 299, deaths only there; the shadow test proves per-substep physics identical | at the start of every substep, any env whose mjlab `qpos/qvel` differs from what Newton last wrote back is copied into Newton (warm start cleared) — `_absorb_external_state_writes`. 57–59 such writes per 32-env KIT_1226 rollout, 35 on clip #44 (auto-resets) |

## G0 close-out result (2026-08-17 22:20 EDT)

| clip | arm | survival | mean steps | body-pos err | Δ vs mjlab | verdict |
|---|---|---:|---:|---:|---:|---|
| KIT_1226 (mastered, 6.0 s clip, 10 s horizon), n=32 | mjlab | 1.000 | 500 | 0.0376 | — | |
| | Newton MJWarp | **1.000** | 500 | 0.0371 | −0.0005 | CONFORMS |
| | mjlab (repeat) | 1.000 | 500 | 0.0371 | — | |
| | Newton MJWarp (repeat) | **1.000** | 500 | 0.0368 | −0.0008 | CONFORMS |
| clip #44 (frontier), n=32 | mjlab | 0.000 | 140.4 | 0.1274 | — | |
| | Newton MJWarp | 0.000 | 143.0 | 0.1284 | +0.0010 | CONFORMS |

Per-substep: |Δqvel| ≤ 3e-5 across the whole 290–312 window from identical
states; forward-only contacts identical; MuJoCo-C as third referee agrees with
both. **G0 is closed.** The same-solver residual for G1's noise floor is the
arm-C-vs-arm-A comparison inside the gate run itself.

`reports/S1_KIT1226_n32_absorb.json`, `reports/S1_clip44_n32_absorb.json`.

Artifacts: `tools/s1_newton_conformance.py`, `reports/S1_KIT1226_n32*.json`,
`reports/S1_clip44_n32.json`, scratch diagnostics `g0_*.py` (job tmp).
