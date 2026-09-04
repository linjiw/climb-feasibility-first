# Feasibility-Gated Humanoid Motion Tracking: Separating Reference Physics from Curriculum Difficulty

**Manuscript status:** unsealed ICRA-sized prose draft, 2026-09-04. The anonymous two-column source
is `paper/icra/root.tex`, its verified bibliography is `paper/icra/references.bib`, and a passing
build writes `paper/icra/ICRA_DRAFT.pdf`. Phase G remains in endpoint-blind calibration. Claims
and numbers remain governed by `paper/RESULTS_LOG.md` and the sealed records it cites.

## Abstract

Adaptive curricula improve humanoid tracking by concentrating updates on difficult motion
segments, but persistent policy error can also arise when a retargeted reference demands
unsupported or over-limit dynamics. We call this **reference--physics misalignment (RPM)**: the
curriculum interprets an inadmissible reference as learnable difficulty. In a three-seed Unitree
G1 campaign, peak top-1 allocation reached 87--89%, and the same kneel-and-crawl reference became
a dominant attractor in every seed; during its descent, 86% of frames have no collision geometry
within 6 cm of the floor, while median unsupported force is approximately one body weight. We
introduce **CLIMB**, a feasibility-gated tracking pipeline that screens final robot-space
trajectories with contact-free inverse dynamics and a torque-limited contact program, then
converts admissible intervals into exact non-wrapping training units. Learning progress
reallocates samples only inside this gate, which yields 1,184 hash-bound units and 368,951 legal
fixed-horizon starts. On one AMASS-to-G1 pipeline, the screen flags 2,442 of 10,705 clips above a
fixed 10%-of-frames threshold; on a separate filtered 4,950-clip production pairing, an independent
implementation flags 7, and the implementations agree on 39 of 40 strict decisions in a
stratified same-clip panel. **Phase-G status: endpoint-blind calibration in progress.** Its matched
ALP-versus-uniform outcome will determine whether adaptive allocation adds value after reference
feasibility is fixed.

## 1. Introduction

Large retargeted motion banks have made generalist humanoid tracking a practical training recipe:
map human motion to a robot, train a policy over the resulting references in massively parallel
simulation, and spend additional updates on motions the policy currently fails. Systems such as
PHC, MaskedMimic, H2O, ExBody, BeyondMimic, and SONIC demonstrate the scale and capability of this
recipe [1--6]. Adaptive motion allocation is a natural part of it. Failure, completion, or recent
learning progress appears to tell the trainer where another update is most useful [5,7,8].

That interpretation assumes that policy error measures a solvable control problem. A retargeted
trajectory can violate the assumption before the policy acts: the robot may have no admissible
contact capable of supplying the demanded base wrench, or the required joint effort may exceed the
modeled actuator range. We call this **reference--physics misalignment (RPM)**. Under RPM, the same
persistent error can describe an unlearned feasible skill or a reference that does not define one
for this embodiment and scene. A policy-only curriculum cannot distinguish the two from failure
alone.

We observed this ambiguity in a 100-motion Unitree G1 campaign. A BeyondMimic-style failure
sampler concentrated on the same kneel-and-crawl clip in all three seeds. Peak top-1 mass was
0.884, 0.870, and 0.893; those maxima describe whichever clip led at that instant and belonged to
another clip in two seeds. Clip-uniform sampling nevertheless achieved higher held-out survival in
all three paired seeds. The shared attractor passes ordinary kinematic checks. Yet, from 0.75 to 1.75 s,
its pelvis descends from 0.79 to 0.40 m while the nearest collision geometry remains 7--10 cm above
the floor. A median 329 N of support demand, approximately the 327 N model weight, has no modeled
source. The sampler therefore reads a persistent reference defect as persistent learning value.

CLIMB closes this reference--policy interface in three stages. First, a robot-space feasibility
screen evaluates the final retargeted trajectory using the target MuJoCo model, modeled contacts,
friction, and actuator ranges. Second, cause-aware routing admits supported intervals, sends
scene-mismatch or repair candidates to separate paths, and quarantines residual failures. Third,
an exact-support curriculum turns admitted intervals into non-wrapping fixed-horizon starts and
applies outcome-based allocation only within that support. This design separates reference
admissibility from learning progress while holding embodiment, reward, PPO, legal-start prior,
caps, compute, seeds, and evaluator fixed.

Feasibility is a corpus--pipeline property. The screen flags 2,442/10,705 clips in the primary
AMASS-to-`whole_body_tracking`-to-G1 pipeline and 7/4,950 in the separately filtered
BONES-SEED-to-G1 production pairing used by SONIC. The two implementations agree on 39/40 strict
decisions in a stratified same-clip panel. Source corpus, release filtering, robot file, and
implementation all change between the bank-scale measurements, so they motivate measuring each
pairing rather than comparing retargeters from unmatched denominators.

This paper makes three contributions:

1. **RPM diagnosis.** A three-seed curriculum attractor localized to a robot-space interval whose
   demanded wrench has no admissible modeled support source.
2. **The CLIMB method.** A policy-independent contact/torque screen, cause-aware routing, and a
   hard feasibility gate yielding 1,184 units and 368,951 legal starts.
3. **Claim-isolating evaluation.** Bank-scale and cross-implementation screen tests plus a matched
   ALP-versus-uniform allocation ablation on identical feasible support.

The allocation ablation is in endpoint-blind calibration; its exhaustive result status is
positive, null, inconclusive, or `not_tested` under the predeclared manipulation and provenance
gates.

## 2. Related work

### Motion filtering and dynamic retargeting

Policy-based curation already removes poorly tracked references. H2O retains AMASS motions that a
privileged imitator can follow, and ExBody2 uses an initial policy's sequence errors to select a
feasible and diverse subset [3,9]. These are effective system designs, but their score requires a
trained policy and combines reference quality with that policy's capability. KungfuBot instead
uses a human-space center-of-mass/center-of-pressure stability heuristic before robot retargeting
[10]. LIMMT combines target-robot motion heuristics, diversity, and complexity, with physical-score
weights calibrated through repeated policy training [11]. PHUMA filters source artifacts and
retargets with joint-limit, ground-contact, and anti-skating losses [12]. CLIMB builds on this line
but changes the training interface: the final robot-space screen determines the support on which
an adaptive allocator is permitted to act.

Optimization-based retargeters address a complementary problem. Kinodynamic Motion Retargeting
uses rigid-body and contact constraints to construct viable locomotion, while Direct Dynamic
Retargeting uses simulator-in-the-loop optimization without requiring an infeasible geometric
intermediate [13,14]. AMO and SPIDER likewise generate viable references through trajectory
optimization or physics-based sampling with contact guidance [15,16]. GMR and *Retargeting
Matters* further show that retargeting artifacts affect downstream tracking robustness [17]. An
earlier analytic study estimates velocity, acceleration, and torque requirements for 40 upper-body
motions, but does not test whole-body environmental support [18]. Repair can therefore be
preferable to exclusion. Our narrower question is diagnostic and routing-oriented: after
retargeting, can the demanded robot-space wrench be supplied by admissible contacts within the
modeled actuator limits? The screen can route a reference toward exclusion, repair, or a
scene/contact-model correction; it does not decide that exclusion is best.

### Adaptive allocation

Prioritized experience replay and prioritized level replay formalize the benefit and bias of
nonuniform training distributions, including explicit replay/exploration mixing [19,20]. In
humanoid tracking, BeyondMimic popularized a failure-EMA bin sampler, while GMT and EGM reweight
motions or motion segments using tracking outcomes [5,7,8]. Those systems combine allocation with
curation, staged training, clipping, or architectural changes. Empirical failure, completion, and
tracking error identify hard examples, but do not by themselves determine whether a reference is
dynamically admissible. CLIMB inserts that test before outcome-based allocation; its matched
comparison then changes only the allocation distribution over a shared set of legal trials.

### Evaluation on fixed support

Robot-learning comparisons are sensitive to seed count, aggregation, and interval construction
[21]. Tracking adds another conditioning problem: kinematic error among survivors can improve when
a method terminates earlier. HumanTracker responds to related limitations by adding contact-aware
and preference-aligned trajectory diagnostics [22]. We use a liveness-weighted tracking score as
the primary Phase-G endpoint and report common-survivor quality only beside survival. The current
contact-timing proxy remains exploratory unless it passes an independent blinded-label gate.

## 3. CLIMB: feasibility-gated tracking

### 3.1 Problem and assumptions

Let a retargeted reference provide generalized position and velocity
`(q_t, qdot_t)` for the Unitree G1 at frame `t`. We apply a centered five-frame moving average to
velocity, differentiate at the reference frame rate, and smooth the resulting acceleration with
the same window. Feasibility is defined relative to a robot model, scene, collision geometry,
friction model, actuator force ranges, and reference trajectory. The present instantiation uses
the G1 and a flat plane; electrical, thermal, compliance, latency, and structural limits remain
outside this model-relative label.

We use the compiled G1 MuJoCo model that underlies the tracking environment. Contact-free inverse
dynamics returns the generalized force needed to realize the prescribed acceleration. The six
free-joint coordinates define the base wrench `W_t` that the environment must supply; the remaining
coordinates define contact-free joint torque `tau_free,t`. A collision geometry becomes a
candidate contact when its exact distance to the plane is at most `g = 0.06 m`.

The 6 cm band is a declared engineering tolerance. At 3 cm a known feasible control is flagged on
42% of frames because the bank carries an approximately 3 cm ground-alignment offset. At 10 cm,
the attractor's 7--10 cm floating descent is incorrectly granted a contact candidate and reads as
feasible. The 6 cm setting lies between those observed failure modes; it is not presented as a
universal physical constant.

### 3.2 Contact-capacity screen

For each candidate contact point we construct a four-edge pyramidal friction cone with coefficient
0.6 in the primary model; a simulator-matched secondary view makes non-foot contacts frictionless.
Mapping a
nonnegative vector of generator magnitudes `f_t` through the contact Jacobian gives both a base
wrench matrix `A_t f_t` and a joint-torque contribution `J_t f_t`. We first solve a weighted
nonnegative least-squares problem to expose the unconstrained residual, weighting angular-wrench
rows by two so forces and moments are comparable at an approximately 0.5 m lever arm. We then solve a linear
program that minimizes the L1 wrench slack while enforcing

`-tau_max <= tau_free,t - J_t f_t <= tau_max,   f_t >= 0`.

The translational component of the resulting weighted residual defines unsupported force under
these modeled contacts and actuator limits. With no candidate contact, the residual is the
contact-free demand.
We report four clip-level quantities: the fraction of frames with no contact candidate
(`airborne_frac`), the fraction whose torque-limited unsupported force exceeds half the robot
weight (`infeasible_frac`), the time integral of unsupported force normalized by weight, and the
fraction for which joint-torque feasibility itself fails. A clip crosses the primary audit rule
only when `infeasible_frac > 0.10` (strict inequality).

Airborne and infeasible are intentionally separate. A ballistic flight phase with acceleration
near gravity has little external support demand and is not flagged merely because no geometry is
near the floor. Conversely, nonballistic hovering or descending without an admissible support
source is flagged. In the second production bank, seven kneeling loops are airborne on every frame
yet have zero infeasible fraction because the modeled knees can supply support. Collapsing the two
axes would delete precisely the non-foot-contact behavior a rare-skill bank should preserve.

The screen takes approximately one CPU-second per clip in the primary implementation. A separate
implementation screens the 4,950-clip production bank at 0.145 CPU-s per clip (0.84 ms per screened
frame). The screen therefore runs as an offline bank-ingestion stage rather than in the policy
control loop.

### 3.3 Routing and exact-support curriculum

Clip classification alone is too coarse for a controlled allocation experiment. A clip can
contain both supportable and unsupported intervals. We therefore reduce full per-frame screens to
ordered feasible runs, retain only 50-step windows that lie wholly inside a run, and bind each
motion and sidecar by SHA-256. The table spans 800 training clips and contains 1,841 source units.
After discarding 657 runs shorter than the fixed horizon, 1,184 admissible units and 368,951 legal
starts remain. A unit is an attribution stratum; the deployment prior is uniform over legal starts,
not uniform over units or clips.

Let `U` contain candidate units, `F_u in {0,1}` denote admission under the declared screen, and
`n_u` count legal starts. The duration-correct base mass is `b_u = n_u / sum_v n_v`. For absolute
learning progress `LP_u(k)` at sampler clock `k`, CLIMB forms

`q_u(k) = F_u b_u [LP_u(k) + lambda] / sum_v F_v b_v [LP_v(k) + lambda]`,

then applies `p(k) = Cap_(c_unit,c_clip)(bbar, q(k); rho)`, where `bbar` is the base mass normalized
over admitted units. Without an active concentration limit, the operator returns
`rho bbar + (1-rho) q`; otherwise it reallocates only the focused mass under the fixed unit and
clip ceilings while preserving the exact lower bound `p_u >= rho bbar_u`. Thus a rejected interval
receives zero mass under the declared model, while `rho` preserves deployment-prior exploration
inside the gate. The present method uses binary `F_u` so admissibility and allocation remain
separately testable; a smooth residual-based gate is a different intervention.

Intervals do not all receive the same remedy. Admissible runs enter the exact support. References
whose required contact object is absent from the scene are paired with that context or withheld. A
lightweight root-translation plus contact-IK path projects eligible repair candidates before the
same screen and qualification checks are rerun; residual infeasibility, excess displacement,
joint-limit failure, or contact-IK residual sends the result to quarantine.

The runtime samples only legal starts, emits an explicit truncation at a segment boundary, and
attributes attempts and outcomes to the sampled unit. It never wraps into a rejected frame or
continues learning across a reference teleport. The sampler owns a deterministic CPU generator and
serializes its state and sufficient statistics for equivalent resume. Per-unit and per-clip caps
bound concentration. A missing sidecar, changed motion hash, invalid start, invalid reference
frame, or censored reset fails the contract.

The paired evaluator freezes `(motion, start, replicate, environment noise, dynamics noise)` and
replays it across policies. It assigns the reference before computing the first observation,
disables auto-reset until terminal channels are captured, rejects rather than clips invalid
offsets, and records checkpoint, task, conditions, reference, evaluator, and output hashes. The
100-clip panel is name- and hash-disjoint from the 800 training clips and contains 2,800 paired
conditions.

## 4. Experimental design

### E1: Does RPM create the motivating attractor?

We analyze the previously sealed 100-motion campaign: 4,096 environments, 4,000 PPO iterations,
three seeds per arm, and 100 disjoint evaluation motions with eight episodes per clip. The
comparison includes failure-adaptive, clip-uniform, and a normalized grounded sampler. We report
the adaptive top-1 exposure, the identity of its attractor, held-out survival, and the attractor's
modeled contact-capacity residual. This campaign establishes the motivating failure case; E4
separately isolates the exact-support allocator.

### E2: Does the screen scale and agree across implementations?

The primary corpus contains 10,705 AMASS-derived references retargeted through
`whole_body_tracking` to the G1 model. We report raw flagged counts under the strict fixed rule,
category and source breakdowns, and contamination in the historical 100-clip evaluator. A separate
experiment covers all 4,950 references in the filtered BONES-SEED production pairing. We never pool
their prevalence estimates. A deterministic 40-clip stratified panel (20 from each bank) is passed
through both implementations to measure score and decision agreement; because the panel is
enriched for flags, it is not a prevalence sample.

### E3: Which intervals should be filtered, repaired, or quarantined?

We first test whether simpler routing choices already establish training benefit. E-HYG prunes 99
flagged motions from an 800-motion training
bank but yields a held-out feasible-motion effect of -0.0101 under its predeclared test. The soft
FGAS segment formulation estimates a primary effect of -0.0196 with a 95% hierarchical-bootstrap
interval `[-0.0497, +0.0134]`, but its rejected-start-mass manipulation gate fails. The exploratory
segment-native pilot is mechanically clean yet reaches only 0.014 total variation from its
control. These observations motivate an exact-support, manipulation-first test; none is evidence
that the final allocator helps.

A source- and severity-stratified CPU panel also exercises the repair route. It applies root
translation plus contact IK, reruns the screen, and requires residual infeasibility at most 5%,
root displacement at most 8 cm, joint-limit compliance, and contact-IK residual at most 10 mm. It
admits 22/26 flagged candidates and keeps 4/4 feasible controls byte-identical, producing 36 units
and 10,561 legal starts. A separate sealed repair-all policy study is a boundary because it misses
its benefit and coverage gates.

### E4: Does learning-progress allocation help on identical feasible support?

Phase G compares two 512-environment, 4,000-iteration arms with confirmation seeds 1, 2, and 3.
G1 samples uniformly over all legal starts. G2 estimates the Beta-smoothed conditional success
rate `s_u(k)` for each unit and ranks absolute learning progress
`LP_u(k) = |s_u(k) - s_u(k-10)|`. Its focus distribution is proportional to the legal-start prior
times `LP_u + lambda`; exploration `rho` mixes the G1 prior back in before the fixed unit and clip
caps.

Before sealing, a 12-row grid crosses `rho in {0.05, 0.10, 0.20, 0.40}` and
`lambda in {0.001, 0.01, 0.05}`. Every row runs for 50 iterations on seed 20260903. Only sampler
ledgers at iterations 30, 40, and 49 enter selection. A row passes when mean allocation total
variation is in `[0.05, 0.15]`, each checkpoint lies in `[0.025, 0.20]`, entropy-effective units
remain at least 12, top-1 probability remains at most 0.05, invalid/censored counts are zero, and
final rank saturation is below 0.90. The passing row nearest TV 0.10 is selected, with TV variance
and declared order as ties, then repeated once on seed 20260904. Failure returns the study to
design without opening a policy endpoint.

The confirmation gate applies the same separation, concentration, validity, parameter, seed, and
provenance checks after a 400-iteration warm-up. Only a passed gate unlocks the primary endpoint:
liveness-weighted TrackingScore on the 25 reference-defined feasible-hard evaluation clips,
`h exp(-MPKPE/0.30 m - anchor_error/0.40 rad)`, where `h` is survived-horizon fraction. The
independent unit is clip within training seed, with a seed-then-clip hierarchical bootstrap of
10,000 draws. Survival, all-panel TrackingScore, AULC, and common-survivor non-harm are declared
secondaries. Exactly one status is printed: `positive`, `null`, `inconclusive`, or `not_tested`.

## 5. Results

### 5.1 RPM creates a curriculum attractor

The adaptive sampler's peak top-1 mass is 0.884/0.870/0.893 across the three campaign seeds, and
the same BMLmovi kneel-and-crawl clip repeatedly becomes the dominant attractor in all three.
The maximum top-1 mass belongs to another clip in two seeds, so we do not attribute all three
maxima to the shared attractor. Uniform sampling achieves
higher held-out endpoint survival in every paired seed: differences `(uniform - adaptive)` are
+0.0300, +0.0275, and +0.0300. With only three seeds, the sign pattern is the useful description;
the minimum attainable paired permutation p-value is 0.125, so we do not headline a significance
claim.

The reference is kinematically ordinary: it has no joint-limit violation and peak joint speed is
at most 5.6 rad/s. The dynamic screen localizes a different failure. From 0.75--1.75 s, 86% of
frames have no candidate contact and median unsupported force is 329 N; the G1 model weighs 327 N.
The kneeling/crawling interval from 1.75--7.25 s is supportable through its non-foot contacts, and
the 8.0--8.5 s rise again becomes unsupported. Every trained policy has zero survival from frame
0, while the tested late 8 s offset survives. This explains why random-offset averaging had
previously made an untrackable prefix look partially learnable.

![The feasibility-first trial interface.](../figures/f1_feasibility_first.png)

**Fig. 1. The CLIMB feasibility-gated tracking interface.** (a) In the motivating closed-loop simulation
campaign, the same attractor recurs in 3/3 adaptive seeds; 0.87--0.89 is the campaign maximum
top-1 mass and does not belong to that clip in every seed. (b) A reference-only robot-space screen
localizes the attractor's unsupported interval. This pipeline-specific temporal and modeled-wrench
diagnosis isolates this failure case rather than every cause of adaptive concentration. (c) The preregistered G1/G2
comparison keeps the 1,184 units, 368,951 legal starts, hashes, PPO implementation, and compute
fixed while changing allocation; its policy outcome is pending.

### 5.2 The gate is pipeline-conditioned and reproducible

Under the strict `infeasible_frac > 0.10` rule, 2,442 of 10,705 primary-pipeline clips are flagged
(22.8%). Category rates range from 12.9% for quiet motion to 58.6% for dynamic motion, and source
rates range from 0.1% for GRAB to 100% for CNRS. Severity-stratified inspection shows why category
labels are insufficient: the five inspected CNRS cases are ordinary fast walks with extended
floating intervals, whereas the Transitions sample mixes ingest defects with acrobatic content.
The 22.8% is therefore a property of this corpus and pipeline, not a generic rate for retargeted
motion or an intrinsic-difficulty gradient.

The second production pairing supplies the strongest boundary. Only 7 of 4,950 clips (0.14%) cross
the same nominal strict rule, while 111 (2.24%) are airborne on more than 10% of frames. Five of the
seven flags are jumps, including four whose names refer to a 50 cm box absent from the flat audit
scene. Their verdict is “unsupported on this plane,” which routes them toward the missing terrain
or exclusion rather than geometric root projection.

Across the 40-clip same-input implementation panel, `infeasible_frac` ranks correlate at 0.9836,
`airborne_frac` at 0.9974, and strict decisions agree for 39/40 clips (Cohen's kappa 0.9485). The
single disagreement is `burpee_002__A362_M` (0.019 versus 0.136). This closes an implementation-
agreement question on the enriched panel; it does not remove the corpus, filter, robot-file, or
friction confounds between the two full-bank prevalence estimates.

![Bank-scale screen with separate corpus/pipeline prevalence bars and a same-clip
implementation-agreement scatter plot](../figures/f2_bank_scale.png)

**Figure 2. Bank-scale screen and implementation agreement.** (a) Bars are normalized within two
separate corpus/pipeline denominators and apply the strict `infeasible_frac > 0.10` rule:
2,442/10,705 for AMASS → `whole_body_tracking` → G1 and 7/4,950 for filtered BONES-SEED →
G1. Corpus, filtering, robot file, friction, and implementation differ, so this is not a causal
retargeter comparison. (b) On a flag-enriched, deterministic 20+20 same-clip panel, strict
decisions agree for 39/40 clips (Spearman ρ = 0.9836, Cohen's κ = 0.9485). That panel checks
implementation agreement; its stratified selection is not a prevalence sample.

### 5.3 Routing changes support, but policy benefit is conditional

The historical evaluator contains 29 flagged clips among 100. Across three policies, flagged
clips score 6.0--8.4 survival points below the all-clip aggregate and 8.4--11.8 below the feasible
stratum. Moreover, the grounded-minus-uniform endpoint contrast is +0.025 on feasible clips and
-0.009 on flagged clips. These data justify feasibility-stratified evaluation, but changing the
evaluation subset cannot establish a training benefit.

The routing controls separate operator validity from policy value. E-HYG's pruning contrast is a
sealed null, soft FGAS does not satisfy its own allocation gate, and the prior segment-native
treatment is only 0.014 TV from control. Together they distinguish three statements often
collapsed in discussion: a reference defect can be measured; screening can change the admissible
training support; and an adaptive allocation rule can improve policy performance on that support.
The first is established here, the second is an apparatus property, and Phase G directly tests the
third.

The repair panel demonstrates that the routing operator can recover exact-support candidates:
22/26 flagged cases pass every residual, displacement, joint-limit, contact-IK, and hash gate,
while 4/4 feasible controls remain byte-identical. The panel is stratified rather than a
prevalence sample. In the earlier repair-all policy study, repaired-reference deployment changes
by +0.0397 with a motion-bootstrap 95% interval `[+0.0153,+0.0658]`, below its +0.05 smallest
effect of interest; unchanged-reference policy transfer is -0.0036, and the coverage gate fails.
Repair is therefore an implemented route whose downstream value requires a matched,
distortion-aware comparison, not the explanation for the present policy claim.

### 5.4 Feasibility-gated allocation on exact support

**Status at this draft: pending calibration; no reward, survival, or tracking endpoint has been
opened.** The exact 900-motion local payload passes every committed identity. The 12-candidate
screen is queued behind a 14,000 MiB shared-GPU availability gate. Populate this subsection only
from the frozen Phase-G result table.

**[Table 3: all 12 calibration rows and the independent-validation row.]**

**[Table 4: confirmation manipulation/provenance gate, primary feasible-hard TrackingScore
contrast, survival, AULC, and common-survivor non-harm.]**

Use exactly one of the following result forms:

- **Positive:** “With every manipulation and provenance gate passed, G2 changed feasible-hard
  TrackingScore by `[estimate]` (95% CI `[lo, hi]`) relative to G1 across `[n]` training seeds;
  survival changed by `[estimate, CI]`, and all common-survivor non-harm margins `[passed/failed]`.”
- **Null:** “With every gate passed, the feasible-hard TrackingScore interval `[lo, hi]` did not
  clear the +0.02 smallest effect of interest; within this task and budget, calibrated ALP did not
  materially improve on deployment-uniform allocation.”
- **Inconclusive:** state the interval and the exact decision rule that remains unresolved.
- **Not tested:** name the failed manipulation or provenance gate and do not print an endpoint
  estimate.

## 6. Limitations

CLIMB's admission label is model-relative. The current screen instantiates one G1 model and a flat
scene with collision contacts, friction, and actuator force limits. Hardware deployment would add
electrical, thermal, compliance, latency, and structural constraints and then require closed-loop
validation. Terrain-bearing references likewise require their terrain in the scene; the four
box-jump flags in the production bank are routed to missing context rather than declared bad
motion.

Finite differences, the 6 cm contact band, and the half-weight residual threshold introduce
modeling choices. Local sensitivity checks bound the two thresholds on this bank, but a new robot
or retargeter must recalibrate them. The 22.8% and 0.14% rates therefore remain separate
corpus--pipeline measurements. A smooth feasibility weight derived from residual slack could
retain borderline cases, but would couple admissibility and allocation; it requires its own
matched ablation against the current binary gate.

Phase G has three training seeds, or two under the predeclared budget fallback, so uncertainty is
seed- and clip-structured. Its result applies to the calibrated ALP rule, support, task, and
budget. The repair route likewise needs a same-policy, distortion-aware comparison of certified
repair against exact feasible intervals and quarantine. The observation that would settle this is
joint movement of tracking, survival, reference fidelity, contact timing, and mechanical work
under one paired trial contract.

## 7. Conclusion

Reference--physics misalignment turns persistent tracking error into a misleading curriculum
signal. In the diagnosed three-seed campaign, one such reference repeatedly becomes a dominant
attractor; the screen localizes its unsupported wrench demand before policy training. CLIMB turns
that diagnosis into an active interface: it screens and routes final robot-space trajectories,
constructs exact legal-start support, and assigns zero training mass to rejected intervals under
the declared model. The pending matched allocation ablation will determine whether ALP adds value
inside that gate. In either outcome, feasibility and learning progress are separate quantities
that can be measured, changed, and evaluated independently.

## References — numbered mirror

Canonical verified metadata now lives in `paper/icra/references.bib`; this compact list preserves
the prose draft's numeric citation mapping. Source checks are recorded in
`paper/CITATION_CHECK_2026-08-26.md` and `paper/CITATION_CHECK_2026-09-04.md`.

1. Luo et al., “PHC,” ICCV 2023.
2. Tessler et al., “MaskedMimic,” SIGGRAPH Asia 2024.
3. He et al., “H2O,” arXiv:2403.04436.
4. Cheng et al., “ExBody,” RSS 2024, arXiv:2402.16796.
5. Liao et al., “BeyondMimic,” arXiv:2508.08241.
6. NVIDIA GEAR, “SONIC,” arXiv:2511.07820 / Science Robotics 2026.
7. Chen et al., “GMT,” arXiv:2506.14770.
8. Yang et al., “EGM,” arXiv:2512.19043.
9. “ExBody2,” arXiv:2412.13196.
10. Xie et al., “KungfuBot / PBHC,” NeurIPS 2025.
11. “LIMMT,” arXiv:2606.06953.
12. Lee et al., “PHUMA,” arXiv:2510.26236.
13. “Kinodynamic Motion Retargeting,” arXiv:2603.09956.
14. “Direct Dynamic Retargeting,” arXiv:2605.23762.
15. Li et al., “AMO,” RSS 2025.
16. Pan et al., “SPIDER,” arXiv:2511.09484.
17. “Retargeting Matters / GMR,” arXiv:2510.02252.
18. Klas et al., “On the Actuator Requirements for Human-Like Execution of Retargeted Human
    Motion on Humanoid Robots,” Humanoids 2023.
19. Schaul et al., “Prioritized Experience Replay,” ICLR 2016, arXiv:1511.05952.
20. Jiang, Grefenstette, and Rocktaschel, “Prioritized Level Replay,” ICML 2021,
    arXiv:2010.03934.
21. Agarwal et al., “Deep Reinforcement Learning at the Edge of the Statistical Precipice,”
    NeurIPS 2021, arXiv:2108.13264.
22. “HumanTracker,” arXiv:2608.13555.
