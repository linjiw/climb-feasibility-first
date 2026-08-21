# 10. Limitations and scope

**One robot, one embodiment.** Every number is Unitree G1. The screen's verdicts are
embodiment-relative by construction (a clip infeasible for the G1's leg fold may be feasible for a
robot with different limits); prevalence rates will differ per robot, though the 0.1–100 %
per-source spread suggests the pipeline-property conclusion is robust.

**One task configuration.** One reward set (BeyondMimic-style tracking terms), one termination
set, one PPO configuration, one action space (position targets at 50 Hz). The P-TAX null (§6)
shows the reward's reference-interpenetration tax does not confound difficulty *here*; other
reward configurations were not tested.

**Survival-centric endpoints and evaluation audit.** Difficulty = 1 − survival throughout.
Tracking-error endpoints correlate but were not sealed as primaries. Post-outcome review found that
the evaluators did not pair startup randomization, fixed-second offsets were clipped and duplicated
on short motions while missing late phases of long motions, and terminal error/effort reads followed
auto-reset. `climb_eval.py` also acts once on a stale pre-assignment observation. Survival remains a
measured endpoint under the sealed harness, but terminal motion-quality claims and fully paired
method deltas require the v2 evaluator (`plan/SEGMENT_NATIVE_FOLLOWUP_2026-08-20.md`).

**Horizon.** Exp-1/2 trained 4,000 iterations at 4,096 environments; the adaptive-vs-uniform gap
could in principle close at much longer horizons (an E4 cell is sealed but unscheduled). Branch B
("grounded ≈ uniform" at 100 clips) is a bounded claim at this scale, not an asymptotic one.

**Simulation only.** No hardware in this paper. The sign-reversal signature (§9) failed its
sealed simulation generality/specificity test and is not proposed as a deployment-time diagnostic.
The LUCID-correlation — whether our simulated exposure audit predicts a companion
project's sim-to-real degradation — is the one bridge on the roadmap, and its N is small (few
policies, few motions); we state that caveat wherever it is cited.

**Causal work remains incomplete.** N3's composition endpoints pass but its preflight stop fires;
E-HYG's pruning arm is a sealed null; soft FGAS fails its implementation gate; N7 has a positive
deployment contrast but fails its benefit and coverage rules; E3 (support at scale) remains sealed
and pending (§8). The decomposition's feasibility axis is causally closed through measurement
(N1), prediction transfer (§7), and a bounded repair intervention, but no completed intervention
yet improves policy skill on unchanged references under all of its registered guards.

**Descoped: the solver-ensemble program.** This project began with the hypothesis that
disagreement across physics engines could serve as an uncertainty oracle for sim-to-real. We
descoped it for three reasons, in order of discovery: (i) same-solver conformance consumed the
error budget — four silent integration errors produced larger effects than any cross-solver
difference we intended to measure, and until a harness passes per-substep conformance,
cross-solver disagreement measures the harness; (ii) the fragility gate showed single-trajectory
divergence is chaos-dominated at exactly the scales an ensemble would integrate over; (iii) the
attractor that motivated the program dissolved into a data defect. The second engine earned a
different role — referee (conformance), measurement backend (the batched inverse-dynamics/LP
screen), and instrument floor (N5) — and we report that plainly rather than as the program
originally imagined.

**Bank provenance, and what the second bank does and does not settle.** The bank-scale prevalence
numbers are one retargeting pipeline's output (whole_body_tracking → G1). A second production bank
— the 4,950-clip BONES-SEED corpus as consumed by SONIC — has since been screened by an
independent re-implementation and comes in at 0.14 % (§6); that is what licenses the per-corpus
framing and forecloses reading 22.8 % as a rate for retargeted banks generally. It is not the
controlled comparison: different source corpus, different robot model file, different friction
coefficient (μ 0.7 vs 0.6), and a release filter on one side only, so corpus content and the filter
are confounded with the retargeter. The controlled version — two retargeters over the *same* source
clips, one screen — remains parked, and until it is run the honest statement is that prevalence
varies by orders of magnitude across pipelines, not that any named pipeline causes it. Claims about
*source* mocap quality stay out of scope: the screen certifies the retargeted output on the target
robot.

**Plane-only terrain, made concrete.** The screen assumes a flat floor, and the second bank shows
what that costs: five of its seven flagged clips are jumps, four of them named for a 50 cm box
that is not in the screened scene. Their references are unsupportable *as screened* and, if trained on a flat floor,
unsupportable in fact — but the defect is a scene/reference mismatch whose fix is terrain or
exclusion, and the repair operator (root projection) is the wrong tool for it. On terrain-bearing
corpora the screen must be given the terrain, or its verdicts must be read as "unsupportable on a
plane".
