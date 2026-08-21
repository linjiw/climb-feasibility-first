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
removes the flag in 1,606 of the strict 2,442 flagged clips (65.8%, residual ≤ 5 %; C4), is a no-op on feasible controls, and
is correctly *refused* by the over-repair budget on genuine ballistics — a screen that flagged
noise would not respond to a targeted geometric fix this way.

**Cross-implementation validation [measured; §6].** The strongest external check is a second,
independently written implementation of the same method (different codebase, different G1 MJCF,
μ 0.7 rather than 0.6) applied to a different production bank. It returns 0.14 % of 4,950 clips
above the 10 %-infeasible threshold — a screen carrying a systematic bug, or one that conflated
flight with infeasibility, would not return near-zero on a bank that contains 111 clips above
10 % airborne frames and 7 `kneeling_loop_*` clips at airborne fraction 1.000 with infeasible
fraction 0.000. The same run is a discrimination test the method passes in the other direction:
those kneeling loops carry their weight on the knees and are supportable at every frame.

**Known limits.** Plane-only terrain — and the second bank makes the cost concrete: its flagged
box jumps (four of its seven flagged clips) are unsupportable only because the 50 cm box they use is
absent from the screened scene
(a scene/reference mismatch, not a retarget defect, and not repairable by root projection).
Embodiment-relative verdicts; q̈ from smoothed central
differences (5-frame) — velocity-spike artifacts (one observed 40 rad/s glitch) are a separate QC
class the screen does not target.
