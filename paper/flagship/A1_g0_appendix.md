# Appendix A1. Same-solver conformance: the elimination protocol and four silent integration errors

We coupled Newton's SolverMuJoCo (MuJoCo-Warp 3.11.0) to mjlab's environment so that mjlab keeps
observations, the frozen policy, actions and terminations while Newton integrates the physics —
MuJoCo state ↔ MuJoCo state through `solver.mjw_data`, one Newton substep per mjlab `sim.step()`.
Both sides run the same MuJoCo-Warp version, so the pre-registered prediction was agreement to seed
noise. Instead the mastered clip KIT_1226 read survival 0.44–0.72 on Newton against 1.00 on mjlab in
six runs, with the same mean tracking error (Δ ≤ 1 mm) and a fork at control step ~298.

**Protocol.** (i) A complete model diff of the two compiled MJWarp models — every `opt.*` field, the
contact pair-filter matrix (469 robot–robot + 33 ground pairs), joints, actuators, geometry.
(ii) Static and spinning bias-force comparison from identical (q, q̇). (iii) Per-substep paired
stepping: from identical (q, q̇, ctrl, warm-start) at every substep of the forking window, one step
in each engine, comparing q̈, constraint forces, contact counts. (iv) Contact-set diffs with
**MuJoCo-C as a third referee** stepping the same pre-state. (v) A **shadow** solver: mjlab's engine
stepping *Newton's own trajectory* substep by substep during a Newton-driven rollout.

**Findings.** Four integration errors, all silent, none physics:
1. mjlab's startup domain randomisation (torso CoM ±2.5/5/5 cm, foot μ 0.3–1.2) is written into
   `env.sim.wp_model` after compile and never reaches the spec; Newton was integrating the nominal
   robot — a 3.3 N·m base gravity-torque residual, visible only as a ~1 cm whole-body CoM shift.
   Fix: mirror the DR-expanded fields by name and recompute derived constants (residual → 3e-6).
2. Newton's MJCF import rounds geometry through float32 transforms (geom quaternions 4e-7 off,
   body positions 3e-7). MuJoCo includes a contact iff dist < 0, and a lightly loaded foot capsule
   rests at dist ≈ 0: the offset decides whether a *frictional* contact exists. At every disagreeing
   substep Newton carried exactly one extra ground–foot contact at dist −0.0; MuJoCo-C agreed with
   mjlab to 1e-3 and with Newton not at all (0.05–3.3 rad/s). Fix: copy the reference's exact float32
   geometry into Newton's model (0 mismatches over 300 steps × 8 worlds).
3. The motion command teleports the robot after `reset()` computed its observation; the first
   action was a random kick.
4. The coupling was one-directional. KIT_1226 is a 6.0 s clip; step 299 is its *wrap*, where the
   motion command teleports the robot onto a fresh reference by writing qpos/qvel into mjlab's sim.
   mjlab's arm got teleported; Newton's arm had the write overwritten by its own physics one substep
   later and chased a reference that had jumped. Auto-resets and push events write state the same
   way. Fix: absorb any environment-side state write into the solver at the start of each substep.

After the fixes: KIT_1226 1.000/1.000 vs 1.000/1.000 (Δerr −0.5 mm), clip #44 0.000 vs 0.000
(Δerr +1 mm), per-substep |Δq̇| ≤ 3e-5 across the whole window, contact counts identical. The
same-solver residual is what makes the fragility instrument of §5 (N5) interpretable, and the
protocol is reusable: any second physics implementation coupled to an RL harness should be held to
per-substep paired stepping with an independent referee, not to end-of-episode metrics, which
matched throughout.
