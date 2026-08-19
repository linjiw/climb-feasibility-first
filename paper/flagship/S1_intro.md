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
0.1 % to 100 % across source datasets under a single retargeting pipeline — a pipeline property,
not a difficulty gradient — and contaminating 29 of our own 100 evaluation clips (§6). Adding
feasibility features to a reference-difficulty model produces the first cross-policy transfer gain
that survives a permutation baseline (Spearman 0.567 → 0.609, p = 0.01): feasibility is the
component of difficulty that belongs to the clip rather than to any particular training run (§7).

The audit itself required two methodological instruments that we release with the paper. First, a
dual-engine conformance protocol: before any physics claim, a second implementation of the *same*
simulator was coupled to the training harness and driven to per-substep agreement (|Δq̇| ≤ 3×10⁻⁵)
— which surfaced four silent integration errors whose combined effect, a 40-point survival fork,
we had initially misread as a finding and here explicitly withdraw (§5.1, Appendix A1). Second, a
calibrated sensitivity statistic: paired-trajectory differences are chaos-dominated at the
millimetre scale within seconds, and only signed replicate-mean effects measured against a
published identical-physics floor resolve mechanism effects (6–14 mm, replicated across seeds at
r = 0.92; §9).

Because this project's history is a catalogue of plausible findings that dissolved under audit —
a transfer gap that was an observation bug, a curriculum deficit that was a sampler bug, a
"hardest clip" that was a data bug — every interpretive claim in this paper was hash-sealed before
its numbers existed, and the full ledger, including the failed gate, the withdrawn verdict, and
three nulls, is a first-class exhibit. Two causal confirmations are sealed and scheduled rather
than done, and are presented as slots with their pass criteria and pre-listed null responses:
composition causality (does adding 16 screened kneel/crawl clips make the feasible phase
trackable?) and support moderation at scale (an 800-clip bank with *named clips predicted to get
worse*). We believe the decomposition, the screen, the repair, and the audit discipline are useful
to the community now, independent of how those slots resolve — and the paper is written so that
either outcome is reportable without revision of any earlier claim.

**Contributions.** (1) A mechanism-level diagnosis of failure-adaptive curriculum collapse in
humanoid tracking, including the non-floor derivation, with upstream fixes filed. (2) A
coverage-grounded repair that provably floors exposure and rescues failure-weighted sampling.
(3) The feasibility × support × intrinsic decomposition of tracking difficulty, with a released
~1 CPU-s/clip dynamic-feasibility screen, bank-scale prevalence, and the demonstration that
feasibility is the transferable component of difficulty. (4) An audit methodology for
simulation-based robot learning — dual-engine conformance, stratified-start evaluation, calibrated
paired-rollout sensitivity, and a sealed prediction ledger — released as tools and protocols.
