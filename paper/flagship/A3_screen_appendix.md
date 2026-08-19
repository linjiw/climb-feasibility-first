# Appendix A3. Screen validation detail

*Artifacts: `reports/N1_clip44_knee_id.json`, `reports/N1_CMU76_knee_id.json`,
`reports/N1_gap_sensitivity.json`, `reports/upstream_drafts/CNRS_AUDIT.md`,
`reports/repair_census/summary.json`. Labels as marked.*

**Internal controls [measured].** Within the attractor clip itself the screen's phases align with
mechanics: standing and kneeling phases report 0 N torque-limited residual (the kneel even under
the simulator's frictionless-knee contact model); only the transitions flag. The matched-easy
control is supported at every frame (τ/limit p95 = 0.66). The synthetic hover demo (a standing
pose translated upward) flags at exactly its constructed 45 %.

**Parameter sensitivity [measured; found by adversarial review, reported as found].** The contact
gap is a real choice with two failure modes: at 3 cm the feasible control itself flags 42 %
(the bank carries a ~3 cm systematic stance-clearance offset from retarget ground alignment); at
10 cm the screen degenerates (airborne geometry is granted as contact and the attractor's descent
reads 0 %). 6 cm sits between the failure modes — above the bank's clearance offset, below
bridgeable distance. The ½-weight bound is insensitive (flag mass 15.1/13.1/12.5 % at
0.25/0.5/0.75× weight) because unsupported force concentrates near 1× weight. Flight is exempt by
construction (free fall demands no support), verified on a jump clip whose ballistic phases do
not flag while its floating preparation frames do.

**External validation [measured].** (i) Hand-checks of the extreme sources: the 100 %-flagged
subset is ordinary walking whose output floats 6–8 cm — screen verdict reproduced end-to-end from
raw npz. (ii) The rollout-only sign-reversal localises to screen-flagged windows in two
independent seed sets without the rollouts ever seeing the screen. (iii) The repair census closes
the loop constructively: lowering the root exactly where the screen says support is missing
removes the flag in 65.8 % of 2,443 clips (residual ≤ 5 %), is a no-op on feasible controls, and
is correctly *refused* by the over-repair budget on genuine ballistics — a screen that flagged
noise would not respond to a targeted geometric fix this way.

**Known limits.** Plane-only terrain; embodiment-relative verdicts; q̈ from smoothed central
differences (5-frame) — velocity-spike artifacts (one observed 40 rad/s glitch) are a separate QC
class the screen does not target.
