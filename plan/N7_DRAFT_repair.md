# N7 — repair the impossible (DRAFT, to be sealed after N3 reads out; kept tiny)

Purpose: convert "exclude the infeasible" into "repair the infeasible" and close the feasibility
axis causally. Not to be run before N3's keystone is read.

Repair operator (contact-restoring projection, CPU): for each frame of a clip flagged airborne with
unsupported wrench > ½ weight, lower the root (and re-solve the leg IK against the joint limits) so
that at least the lowest foot/shin candidate touches the plane, with a time-warp of the transition so
the root's vertical velocity stays ≤ the original peak — i.e. keep the human's *intent* (kneel down),
change only where the retarget put the body relative to the floor. Verify with `n1_knee_id.py`:
target infeasible_frac ≤ 5 % and no new self-penetration.

Clips: #44 plus 2–3 family clips that failed the N1 screen (from the 12/40: BMLmovi_Subject_27_5,
_11_21, _60_6 — chosen for the same airborne-descent shape).

Arm: uniform on mixed100 + ground16 with the repaired #44-family clips added (1 seed) vs the N3
keystone (unrepaired). Evaluation: stratified starts as in N3.

Predictions (to be sealed with numbers from N3's readout):
- the descent phase of the *repaired* #44 (offsets 0–1 s) becomes learnable: stratified survival
  rises from ≤ 0.25 to ≥ 0.5;
- the motor-strength sign reversal vanishes on the repaired clip (paired motor±15 % signed effect in
  the former airborne window within ±2 mm of the floor; N5 instrument);
- unrepaired family clips do not improve on their descent phases in the same run (specificity).
Null follow-ups: repair too aggressive (kneel changes) → measure joint-space distance to original;
policy capacity → none claimed.
