# 10. Limitations and scope

**One robot, one embodiment.** Every number is Unitree G1. The screen's verdicts are
embodiment-relative by construction (a clip infeasible for the G1's leg fold may be feasible for a
robot with different limits); prevalence rates will differ per robot, though the 0.1–100 %
per-source spread suggests the pipeline-property conclusion is robust.

**One task configuration.** One reward set (BeyondMimic-style tracking terms), one termination
set, one PPO configuration, one action space (position targets at 50 Hz). The P-TAX null (§6)
shows the reward's reference-interpenetration tax does not confound difficulty *here*; other
reward configurations were not tested.

**Survival-centric endpoints.** Difficulty = 1 − survival throughout. Tracking-error endpoints
correlate but were not sealed as primaries. The stratified-start protocol removes the worst
survival artifact (start-offset averaging) but survival remains a coarse instrument.

**Horizon.** Exp-1/2 trained 4,000 iterations at 4,096 environments; the adaptive-vs-uniform gap
could in principle close at much longer horizons (an E4 cell is sealed but unscheduled). Branch B
("grounded ≈ uniform" at 100 clips) is a bounded claim at this scale, not an asymptotic one.

**Simulation only.** No hardware in this paper. The sign-reversal signature (§9) is proposed as a
deployment-time diagnostic but is untested off-simulator; the sealed P-SIGN test is itself
simulation. The LUCID-correlation — whether our simulated exposure audit predicts a companion
project's sim-to-real degradation — is the one bridge on the roadmap, and its N is small (few
policies, few motions); we state that caveat wherever it is cited.

**Causal slots pending.** N3 (composition) and E3 (support at scale) are sealed with pass criteria
and pre-listed null responses but not run at submission of this draft; §8 presents them as slots.
The decomposition's feasibility axis is causally closed only down to measurement (N1) and
prediction transfer (§7); the repair experiment (N7) that would close it interventionally is
sealed-after-N3 by design.

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

**Bank provenance.** One retargeting pipeline's output (whole_body_tracking → G1) was screened at
scale; the two-retargeter comparison on shared source clips is parked. Claims about *source* mocap
quality are explicitly out of scope: the screen certifies the retargeted output on the target
robot.
