# 5. Anatomy of an attractor: from "hardest clip" to "impossible reference"

The clip every adaptive run collapsed onto (§3) looked, at first, like the most interesting object
in the bank: a kneel-down-to-crawl motion at the 99.7th percentile of non-foot ground contact,
failing at 0.31 survival while the bank averaged 0.89. Three successive instruments each destroyed
one hypothesis about it. We present them in order because the *order* is the method: physics
claims were not permitted until the harness was proven, and data claims were not permitted until
physics was excluded.

## 5.1 First, prove the instrument: same-solver conformance (G0)

To ask physics questions we coupled a second implementation — Newton's SolverMuJoCo — to the
training environment so that the environment kept observations, the frozen policy, actions and
terminations while the second engine integrated the dynamics. Both sides run the *same*
MuJoCo-Warp version, so the sealed prediction was agreement to seed noise. Instead: survival
0.44–0.72 vs 1.00 on a mastered clip, with identical mean tracking error, across six runs.

Under the standing rule that **any same-solver discrepancy is integration error until proven
otherwise**, a four-stage elimination (full model diff; static/spinning bias forces from identical
states; per-substep paired stepping through the forking window with MuJoCo-C as a third referee; a
*shadow* solver stepping the other engine's own trajectory) located four silent integration errors
— none of them physics, all of them instructive, and one of them (the initially reported
"contact-event fork at step 298") a previously *published-internally* finding that we hereby state
as **withdrawn**: it was the 6.0-second clip's wrap-around teleport, visible only to the engine
that was allowed to overwrite it. The four errors and the protocol are Appendix A1; after the
fixes the two implementations agree at 1.000/1.000 vs 1.000/1.000 survival, Δerror ≤ 1 mm,
per-substep |Δq̇| ≤ 3 × 10⁻⁵ rad/s (`plan/S1_RESULT.md`, `reports/S1_*_absorb.json`). Everything
downstream inherits this floor.

## 5.2 Then ask physics: the pre-registered fragility gate (G1) — negative

Sealed before the run (`plan/PREREGISTRATION_G1_clip44.md`, `41e4b20c…` + addendum `2a9ceaca…`):
if the attractor's difficulty is a physics-parameter sensitivity, paired ±δ counterfactual worlds
— action delay +20 ms, motor strength ±15 %, foot friction 0.4/0.8, contact stiffness 12/28 ms,
torso CoM ±2 cm, and non-foot contacts made frictional — should show elevated fragility on the
contact axes relative to matched-easy controls, localised before failure. 480 + 480 + 480 worlds
(intervention arm, contact-model arm, same-solver floor arm), 6 clips, 8 replicate ICs.

**The gate fails on its sealed criteria** (`plan/G1_RESULT.md`, `reports/G1/run0/`): the predicted
axes reach 1.30–1.33× the matched-easy fragility (needed ≥ 2×); no (clip, axis) reaches the sealed
5× same-solver floor; and **termination fragility is zero everywhere** — the clip dies 8/8 in all
ten configurations, at every start offset inside its ground segment, with 0.0–0.2 % actuator
saturation until the fall. Physics-parameter sensitivity cannot explain a failure that no physics
parameter modulates. (The gate also surfaced one exploratory anomaly — a sign reversal on the
motor axis unique to this clip — which §9 develops with the calibrated instrument.)

## 5.3 Then ask the data: contact-feasibility of the reference (N1) — verdict

Per-frame inverse dynamics with contacts disabled gives the base wrench the environment must
supply; a torque-limited LP over friction cones at the contacts actually available (within 6 cm of
the plane) gives the smallest unsupported remainder (`tools/n1_knee_id.py`,
`reports/N1_clip44_knee_id.json`). The verdict is unambiguous: in the descent, 0.75–1.75 s, **no
collision geom is within 6 cm of the floor** — the retargeted feet float 7–10 cm up while the
pelvis falls 0.79 → 0.40 m — leaving ~329 N ≈ the robot's full weight (327 N) unsupported in 86 %
of those frames; the rise repeats it at 8.0–8.5 s. The kneel/crawl *between* is fully supportable
within actuator limits, even under the simulator's own frictionless-knee contact model. The
matched-easy control is supported at every frame. Kinematically the clip is ordinary — zero
joint-limit violations, ≤ 5.6 rad/s — which is exactly why kinematic QC and the kinematic half of
our atlas could not see it. Mechanism: the human sits back onto the heels; the robot's leg cannot
fold that far; the retarget resolves the conflict by lifting the legs instead of lowering the root.

**Resolution.** The attractor decomposes into (i) a physically impossible transition — a data
defect, family-wide: 20 of its 40 nearest kneel/crawl neighbours exceed the 10 %-infeasible-frame
threshold (`reports/N3_candidate_feasibility.json`; the "12/40" first reported in
`plan/N1_RESULT.md` was an informal stricter cut, corrected in `plan/GLOBAL_EVAL_ADDENDUM.md`) —
and (ii) a feasible skill (kneeling, crawling) occupying 3.2 % of the training bank's duration, on
which the policy was never trained. The failure-weighted sampler cannot distinguish "impossible"
from "hard" from "unseen"; it poured 87–89 % of its exposure into the one clip where those three
coincide. The earlier "0.31 survival" was itself an artifact of start-offset averaging — episodes
beginning after the ground segment survived — which is why every difficulty label from here on
uses the stratified-start protocol (§6). Whether adding *feasible* members of this family to the
bank makes the feasible phase trackable is the sealed N3 keystone (§8); whether *repairing* the
impossible transition makes the descent trackable is N7, to be sealed after N3 reads out.
