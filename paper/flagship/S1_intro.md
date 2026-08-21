# 1. Introduction

Generalist humanoid motion tracking has converged on a recipe: retarget a large mocap corpus to
the robot, train a tracking policy over the whole bank in massively parallel simulation, and steer
training with a curriculum that samples harder motions more often. The recipe scales — trackers now
follow tens of thousands of clips — and each of its stages trusts the one before it: the curriculum
trusts that failure means *hard*, the trainer trusts that the references are *achievable*, and the
benchmark trusts that averaged survival measures *skill*. This paper is an end-to-end audit of that
chain on a Unitree G1, and its central finding is that the chain's core quantity — per-clip
difficulty — conflates three different things that no stage of the standard pipeline can tell
apart:

**difficulty = feasibility × support × intrinsic.**

A clip can fail because no controller could track it on this robot (*feasibility*: the retargeted
reference demands forces that no available contact can supply); because the training bank contains
nothing like it (*support*); or because it is genuinely demanding (*intrinsic*: speed, contact
switching, friction). Each factor has its own measurement — a per-frame contact-feasibility screen,
a bank-relative density, a reference atlas — and its own fix: repair or exclusion, bank
composition, and curriculum or robustness training. A failure-weighted sampler that cannot
distinguish them collapses onto the corner where all three coincide.

We found that corner empirically. A failure-adaptive sampler of the family used by current
open-source trackers concentrated 87–89 % of its exposure on a single kneel-and-crawl clip in
three of three seeds — the same clip every time — and *lost* to uniform sampling on held-out
survival (0.780 vs 0.810, 3/3 seeds). Part of the cause is a bug with reach: the sampler's
advertised uniform-mixing floor is added to *counts*, so the true floor is ε/(Σq+ε) < 1 % and
shrinks with environment count; we derive this, file it upstream, and repair it with a one-line
normalise-then-mix that provably floors exposure (§3–4). But the deeper cause took three
instruments to find. A pre-registered physics-fragility gate — 1,440 paired counterfactual worlds
across action delay, motor strength, friction, contact stiffness, contact model, and center of
mass — failed its own sealed criteria: *nothing* moved the clip's survival (§5). What finally
explained it was a per-frame feasibility test of the reference itself: for a full second of the
retargeted descent, no part of the robot is within 6 cm of the floor while the pelvis drops
0.35 m — roughly the robot's entire weight (~329 N) has nothing to push on. The clip is
impossible, its feasible kneeling core is absent from the bank (3.2 % of training duration), and
the sampler weighted it precisely because failure was guaranteed.

Screening the full 10,705-clip bank (~1 CPU-second per clip) shows this is not an anecdote:
**22.8 % of clips are dynamically infeasible for more than 10 % of their frames**, ranging from
0.1 % to 100 % across source datasets under a single retargeting pipeline — a corpus-and-pipeline property,
not a difficulty gradient — and contaminating 29 of our own 100 evaluation clips (§6). The
complement matters as much as the number, and we state it before anyone infers a rate for
retargeted banks in general: an independently re-implemented screen over the 4,950-clip BONES-SEED
bank that trains SONIC returns **0.14 %**, 160× lower, on a pre-registered test whose pre-committed
consequence (descoping a planned training ablation there) was taken [measured; §6]. Prevalence is a
property of a particular corpus-and-pipeline pairing; it has to be measured per corpus, and at
≤ 1 CPU-second per clip it can be, as a standing release gate. Adding feasibility features to a
reference-difficulty model produces the first cross-policy transfer gain
that survives a permutation baseline (Spearman 0.567 → 0.609, p = 0.01): feasibility is the
component of difficulty that belongs to the clip rather than to any particular training run (§7).

The audit itself required two methodological instruments that we release with the paper. First, a
dual-stack conformance protocol: before any physics claim, the *same* engine (MuJoCo Warp 3.11.0)
was reached through a second integration stack — Newton (commit `7bb6d02d`) via its SolverMuJoCo
path, against mjlab v1.6.0 driving it directly, with classic MuJoCo 3.11.0 (C) as a third referee —
and driven to per-substep agreement (|Δq̇| ≤ 3×10⁻⁵)
— which surfaced four silent integration errors whose combined effect, a 40-point survival fork,
we had initially misread as a finding and here explicitly withdraw (§5.1, Appendix A1). Second, a
calibrated sensitivity statistic: paired-trajectory differences are chaos-dominated at the
millimetre scale within seconds, and only signed replicate-mean effects measured against a
published identical-physics floor resolve mechanism effects (6–14 mm, replicated across seeds at
r = 0.92; §9).

Because this project's history is a catalogue of plausible findings that dissolved under audit —
a transfer gap that was an observation bug, a curriculum deficit that was a sampler bug, a
"hardest clip" that was a data bug — every interpretive claim in this paper was hash-sealed before
its numbers existed, and the full ledger, including failed gates, a withdrawn verdict, and nulls,
is a first-class exhibit. N3 now supplies a mixed intervention result — its targeted-composition
endpoints pass, but an adaptive-arm regression triggers the frozen interpretation stop — while
E-HYG finds no benefit from blunt clip pruning. Support moderation at scale remains sealed and
pending, with named clips predicted to get worse. We retain all of these outcomes without
reframing; the decomposition, screen, repair, and audit discipline do not depend on every
intervention being positive.

**Contributions.** (1) A mechanism-level diagnosis of failure-adaptive curriculum collapse in
humanoid tracking, including the non-floor derivation, with upstream fixes filed — and the
exposure accounting that quantifies the cost: the shipped sampler concentrates a mean 48.8 % of
all clip draws on whichever single clip is currently winning (peak 87–89 %), and at least 21.9 %
of them on the impossible clip specifically [measured;
`reports/wasted_exposure_accounting.json`]. (2) A coverage-grounded repair that provably floors
exposure and rescues failure-weighted sampling. (3) The feasibility × support × intrinsic
decomposition of tracking difficulty, with bank-scale prevalence measured on two independently
built production banks (22.8 % vs 0.14 %) — which makes prevalence a per-corpus measurement and the
screen a release gate — and the demonstration that feasibility is the transferable component of
difficulty. (4) An audit methodology for
simulation-based robot learning — dual-stack conformance, stratified-start evaluation, calibrated
paired-rollout sensitivity, and a sealed prediction ledger. The data-engineering economics frame
all four: screening the entire 10,705-clip bank costs ~3 CPU-hours and repairing a recoverable
clip ~3 CPU-seconds, against the 10³–10⁴ GPU-hours of the training runs they protect — four to
five orders of magnitude between the audit and the asset it defends.

**Released deliverables (three, distinct in where they sit in the pipeline):**
(i) **refeas** — the offline pre-training screen (contact-free inverse dynamics + torque-limited
contact LP, ~1 CPU-s/clip); (ii) **contact-projection repair** — the lightweight geometric fix
for the recoverable fraction of flagged clips (root projection onto the contact manifold, with an
over-repair budget that refuses genuine ballistics); (iii) **evaluation & monitoring protocols**
— stratified-start evaluation, feasibility-stratified endpoints, and the dual-stack conformance
checklist. A proposed rollout-only sign-reversal detector failed its sealed generality and
specificity test and is retained as a negative result, not a runtime guard.
