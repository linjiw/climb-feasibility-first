# CLIMB: Feasibility-Gated Motion Tracking for Generalist Humanoid Controllers

**Manuscript status:** unsealed ICRA-sized prose companion, 2026-09-04. The canonical anonymous
two-column source is `paper/icra/root.tex`, its verified bibliography is
`paper/icra/references.bib`, and a passing build writes `paper/icra/ICRA_DRAFT.pdf`. Claims and
numbers remain governed by `paper/RESULTS_LOG.md` and the sealed records it cites.

## Abstract

Outcome-adaptive curricula treat persistent tracking error as learnable difficulty. This
assumption fails when a retargeted reference demands contact wrench or actuator effort that the
declared robot and scene cannot supply---a failure we call **reference--physics misalignment
(RPM)**. We formulate tracking difficulty as the staged product of reference feasibility,
bank-relative support, and intrinsic motion demand. We then introduce **CLIMB**, a closed-loop
data-to-policy framework with three interfaces: `refeas` screens final robot-space trajectories
using contact-free inverse dynamics and a torque-limited contact program; the Dynamic Feasibility
and Repair Pipeline (DFRP) projects qualified contacts and re-screens the result; and an
exact-support curriculum assigns zero probability to rejected intervals before capped
learning-progress allocation. In a three-seed Unitree G1 campaign, top-1 allocation peaked at
87--89%, and the same unsupported kneel-and-crawl reference became a recurrent attractor. On one
AMASS-to-G1 pipeline, `refeas` flags 2,442 of 10,705 clips; two implementations agree on 39 of 40
decisions in a stratified same-clip panel. DFRP qualifies 22 of 26 flagged candidates in a frozen
stratified panel while leaving 4 of 4 feasible controls byte-identical. Finally, adding
feasibility features raises cross-policy difficulty-transfer Spearman correlation from 0.567 to
0.609 over 100 held-out clips (`p = 0.010` against random features). These results establish a
concrete interface for separating reference admissibility from policy learning and compute
allocation.

## 1. Introduction

Large retargeted motion banks have made generalist humanoid tracking a practical training recipe:
map human motion to a robot, train a policy over the resulting references in massively parallel
simulation, and spend additional updates on motions the policy currently fails. Systems such as
PHC, MaskedMimic, H2O, ExBody, BeyondMimic, and SONIC demonstrate the scale and capability of this
recipe [1--6]. Adaptive motion allocation is a natural part of it. Failure, completion, or recent
learning progress appears to tell the trainer where another update is most useful [5,7,8].

That interpretation assumes every reference defines a solvable control problem. A retargeted
trajectory may instead have no admissible contact capable of supplying its demanded base wrench,
or may require joint effort beyond the modeled actuator range. We call this
**reference--physics misalignment (RPM)**. Under RPM, policy failure conflates three distinct
quantities:

`D(r; M, E, B) = F(r; M, E) x S(r; B) x I(r)`.

Here `F` is feasibility for robot `M` in scene `E`; `S` is scarcity relative to training bank
`B`; and `I` is intrinsic reference demand, including speed, contact switching, and friction.
This is a decision factorization, not an independence assumption: if `F = 0`, the reference is
routed rather than ranked as learnable difficulty; for admitted references, support and intrinsic
demand describe what the training distribution contains and what it asks the policy to learn.

We observed this ambiguity in a 100-motion Unitree G1 campaign. A BeyondMimic-style failure
sampler concentrated on the same kneel-and-crawl clip in all three seeds. Peak top-1 mass was
0.884, 0.870, and 0.893; those maxima describe whichever clip led at that instant and belonged to
another clip in two seeds. Clip-uniform sampling nevertheless achieved higher held-out survival in
all three paired seeds. The shared attractor passes ordinary kinematic checks. Yet, from 0.75 to 1.75 s,
its pelvis descends from 0.79 to 0.40 m while the nearest collision geometry remains 7--10 cm above
the floor. A median 329 N of support demand, approximately the 327 N model weight, has no modeled
source. The sampler therefore reads a persistent reference defect as persistent learning value.

CLIMB closes this reference--policy interface in three stages (Fig. 1). First, `refeas` evaluates
the final robot-space trajectory against the target model, scene, contacts, friction, and actuator
ranges. Second, DFRP admits supported intervals, restores qualified contact geometry, and
quarantines residual or over-distorted repairs. Third, the exact-support curriculum constructs
non-wrapping legal starts and applies adaptive learning progress (ALP) only inside the hard
feasibility gate. Policy outcomes close the loop by updating allocation, but never override
reference admission.

The resulting evidence covers all three interfaces. The screen flags 2,442/10,705 clips in one
AMASS-to-`whole_body_tracking`-to-G1 pipeline and 7/4,950 in a separately filtered
BONES-SEED-to-G1 production pairing. The counts are intentionally not pooled: feasibility is a
corpus--pipeline property. Two implementations agree on 39/40 strict decisions in a stratified
same-clip panel. DFRP qualifies 22/26 flagged panel candidates under residual, displacement,
joint-limit, contact-IK, and exact-support gates, while 4/4 feasible controls remain unchanged.
Across 100 held-out clips, feasibility features also improve difficulty ranking across policies
trained with different curricula from `rho = 0.567` to `0.609` (`p = 0.010`).

This paper makes three contributions:

1. **RPM factorization and `refeas`.** A final-trajectory screen tested at bank scale and across
   two implementations.
2. **DFRP.** A fail-closed contact projection that qualifies 22/26 stratified candidates while
   leaving 4/4 feasible controls unchanged.
3. **Exact-support ALP.** A hash-bound support with 1,184 units and 368,951 starts, zero rejected
   mass, and bounded unit/clip allocation.

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

## 3. CLIMB: data-to-policy framework

### 3.1 Model-relative feasibility

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

### 3.2 `refeas`: contact-capacity screen

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
fraction for which joint-torque feasibility itself fails. A clip crosses the primary screen rule
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

### 3.3 DFRP: contact-manifold repair

The Dynamic Feasibility and Repair Pipeline (DFRP) targets clips that cross the strict screen rule
because collision geometry floats above its intended support surface. Let `h_t` be the nearest
candidate support geometry, `d(h_t, E; q_t)` its signed distance to the scene, and `c = 3 mm` the
target clearance. DFRP defines the contact-manifold projection

```text
min_{delta_z, Delta_theta} sum_{t in T} [
    w_z delta_z_t^2 + w_q ||Delta_theta_t||_2^2
    + w_s (delta_z_{t+1} - delta_z_t)^2]

subject to
    qtilde_t = q_t - delta_z_t e_z + S_t Delta_theta_t
    d(h_t, E; qtilde_t) - c <= 0
    0 <= delta_z_t <= d(h_t, E; q_t) - c
    q_min <= q_t + S_t Delta_theta_t <= q_max.
```

Here `T` contains frames with no collision geometry inside the 6 cm screen band and `S_t` selects
the six hip, knee, and ankle coordinates of the supporting leg. The objective minimizes root and
joint deviation while restoring a legal contact without penetrating the plane.

DFRP v1 implements a deterministic two-stage approximation. It first lowers the root by the
minimum clearance correction, Gaussian-smooths that timeline over 0.24 s, and clips the result so
it never raises the root or pushes the selected geometry through the plane. If the selected leg
still misses the contact target, at most 15 damped least-squares iterations apply

`Delta_theta_t = clip(-e_t J_z,t^T / (J_z,t J_z,t^T + 1e-5), -0.05, 0.05)`,

with joint-limit projection after every step. Body poses and velocities are recomputed by forward
kinematics and finite differences. The approximation is fail-closed rather than assumed to solve
the target program: the full trajectory is re-screened, and admission requires residual
infeasibility at most 5%, root displacement at most 8 cm, valid joint limits, maximum contact-IK
residual at most 10 mm, and at least one hash-bound legal 50-step start. Scene-mismatch cases,
including references that require an absent box, bypass projection and are routed to context
completion or quarantine.

### 3.4 Exact-support gated allocation

Clip classification is too coarse because one reference can contain both supportable and
unsupported intervals. We reduce per-frame screens to ordered feasible runs, retain only 50-step
windows wholly inside a run, and bind each motion and sidecar by SHA-256. Across 800 training clips,
1,841 source runs yield 1,184 admissible units and 368,951 legal starts after 657 short runs are
discarded. A unit is an attribution stratum; the deployment prior is uniform over legal starts,
not units or clips.

Let `U` contain candidate units, `F_u in {0,1}` denote admission under the declared screen, and
`n_u` count legal starts. The duration-correct base mass is `b_u = n_u / sum_v n_v`. For absolute
learning progress `LP_u(k)` at sampler clock `k`, CLIMB forms

`q_u(k) = F_u b_u [LP_u(k) + lambda] / sum_v F_v b_v [LP_v(k) + lambda]`,

then applies `p(k) = Cap_(c_unit,c_clip)(bbar, q(k); rho)`, where `bbar` is `b` normalized over
admitted units. Without an active concentration limit, the operator returns
`rho bbar + (1-rho) q`; otherwise it reallocates only the focused mass under the fixed unit and
clip ceilings while preserving `p_u >= rho bbar_u`. A rejected interval therefore receives zero
mass under the declared model, while `rho` preserves deployment-prior exploration inside the gate.
The binary `F_u` keeps admissibility and allocation separately testable; a smooth residual-based
gate would be a different intervention.

Admissible runs and DFRP-qualified repairs enter exact support; missing-context and residual
failures do not. The runtime samples only legal starts, emits explicit truncation at a segment
boundary, never wraps into a rejected frame, and serializes its deterministic generator and
sufficient statistics. Per-unit and per-clip caps bound concentration. Missing sidecars, changed
motion hashes, invalid starts, invalid frames, or censored resets fail the contract.

The paired evaluator freezes `(motion, start, replicate, environment noise, dynamics noise)` and
replays it across policies. It assigns the reference before the first observation, disables
auto-reset until terminal channels are captured, rejects invalid offsets, and records checkpoint,
task, condition, reference, evaluator, and output hashes. The 100-clip panel is name- and
hash-disjoint from training and contains 2,800 paired conditions.

![The CLIMB closed-loop data-to-policy framework.](../figures/f1_feasibility_first.png)

**Fig. 1. The CLIMB closed-loop data-to-policy framework.** Difficulty is separated into
model-relative feasibility, bank-relative support, and intrinsic demand before policy outcomes
affect allocation. `refeas` screens, DFRP repairs and re-qualifies eligible contacts, and
exact-support ALP allocates only over legal non-wrapping starts. The 22/26 callout is a frozen
stratified repair panel; the 1,184 units and 368,951 starts are properties of the hash-bound
800-motion support, not policy-performance claims.

## 4. Experimental design

### E1: Does RPM create the motivating attractor?

We analyze the previously sealed 100-motion campaign: 4,096 environments, 4,000 PPO iterations,
three seeds per arm, and 100 disjoint evaluation motions with eight episodes per clip. The
comparison includes failure-adaptive, clip-uniform, and a normalized grounded sampler. We report
the adaptive top-1 exposure, the identity of its attractor, held-out survival, and the attractor's
modeled contact-capacity residual. This campaign establishes the motivating failure case; E4
separately isolates the exact-support allocator.

### E2: Does the screen scale, agree, and transfer across policies?

The primary corpus contains 10,705 AMASS-derived references retargeted through
`whole_body_tracking` to the G1 model. We report raw flagged counts under the strict fixed rule,
category and source breakdowns, and contamination in the historical 100-clip evaluator. A separate
experiment covers all 4,950 references in the filtered BONES-SEED production pairing. We never pool
their prevalence estimates. A deterministic 40-clip stratified panel (20 from each bank) is passed
through both implementations to measure score and decision agreement; because the panel is
enriched for flags, it is not a prevalence sample. Separately, a ridge model fits 11 intrinsic
reference features to per-clip difficulty under one curriculum and ranks difficulty under another
on the same 100 held-out clips. We compare intrinsic features with and without the three `refeas`
features against 200 random three-feature additions. This is cross-policy transfer, not
cross-architecture transfer.

### E3: Does DFRP qualify repairs without changing feasible controls?

We freeze a source- and severity-stratified CPU panel before repair: 26 strict-flagged candidates
span three root-displacement bands and two initial-infeasibility bands, and four source-matched
feasible clips serve as no-op controls. The primary outcome is exact-ready flagged count under the
5% residual, 8 cm root, joint-limit, 10 mm contact-IK, source-hash, and legal-start gates. The gate
requires at least 20/26 candidates, 4/4 byte-identical ready controls, zero integrity or
qualification failures among admitted clips, and a reproducible manifest payload. Runtime and
root, joint, body, velocity, and acceleration deviations are secondary diagnostics.

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

The endpoint-blind calibration selected `rho = 0.40`, `lambda = 0.05`. Its screen TVs are
0.1310/0.1063/0.0865 (mean 0.1079); the independent-seed TVs are
0.1292/0.1045/0.0831 (mean 0.1056). The latter retains at least 700.1 entropy-effective units,
at most 0.0134 top-1 mass, zero invalid or censored events, and 0.2365 final saturation. This is
a passed manipulation calibration, not an ALP policy-performance result; the G2--G1 endpoint
remains sealed and unread.

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

### 5.2 `refeas` is pipeline-conditioned and reproducible

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

The difficulty decomposition is also visible across policies trained with different curriculum
allocations. On the same 100 held-out clips, an 11-feature intrinsic atlas fit to adaptive-policy
difficulty ranks uniform-policy difficulty at `rho = 0.567`. Adding `infeasible_frac`,
`airborne_frac`, and normalized unsupported impulse raises the rank correlation to `0.609`, above
198 of 200 random three-feature additions (one-sided `p = 0.010`). All six directed policy pairs
move in the same direction and four have `p < 0.05`; the two pairs targeting the grounded policy
do not. This is transfer across policies sharing an architecture, not evidence of cross-architecture
or cross-robot transfer.

![Bank-scale screen with separate corpus/pipeline prevalence bars and a same-clip
implementation-agreement scatter plot](../figures/f2_bank_scale.png)

**Figure 2. Bank-scale screen and implementation agreement.** (a) Bars are normalized within two
separate corpus/pipeline denominators and apply the strict `infeasible_frac > 0.10` rule:
2,442/10,705 for AMASS → `whole_body_tracking` → G1 and 7/4,950 for filtered BONES-SEED →
G1. Corpus, filtering, robot file, friction, and implementation differ, so this is not a causal
retargeter comparison. (b) On a flag-enriched, deterministic 20+20 same-clip panel, strict
decisions agree for 39/40 clips (Spearman ρ = 0.9836, Cohen's κ = 0.9485). That panel checks
implementation agreement; its stratified selection is not a prevalence sample.

### 5.3 DFRP restores exact support on a stratified panel

DFRP qualifies 22/26 flagged candidates (84.6%) and all four feasible controls pass as
byte-identical no-ops. The resulting 26-clip curated view contains 36 admissible units and 10,561
legal 50-step starts. Median and 95th-percentile CPU runtime are 2.57 and 6.29 s per clip. Two
candidates remain above the 5% residual-infeasibility ceiling, and two more reach that ceiling but
violate the 10 mm contact-IK bound; all four are quarantined. Thus 84.6% is a qualification rate
on the frozen panel, not a bank-wide recovery rate or a policy-benefit estimate.

### 5.4 Alternative routing and allocation controls

The historical evaluator contains 29 flagged clips among 100. Across three policies, flagged
clips score 6.0--8.4 survival points below the all-clip aggregate and 8.4--11.8 below the feasible
stratum. The grounded-minus-uniform endpoint contrast is +0.025 on feasible clips and -0.009 on
flagged clips. These data justify stratified evaluation, but changing the evaluation subset cannot
establish training benefit.

Whole-clip E-HYG pruning removes all 99 flagged motions even though exact segmentation retains
12.5 of their 20.2 minutes and loses only 3/99 clips at zero guard; feasible-held-out survival
changes from 0.918 to 0.907 (`Delta = -0.0101`, one-sided permutation `p = 0.951`). The tested soft
segment weighting changes feasible-hard survival by `-0.0196` with 95% hierarchical-bootstrap
interval `[-0.0497,+0.0134]` and leaves 0.199 mass on hard-rejected starts, failing its
predeclared manipulation gate. These outcomes do not establish a universal failure of pruning or
soft weighting; they show that neither tested substitute implements exact admission.

An earlier exact-support pilot provides a bounded fidelity signal rather than an allocation win.
Across 22,321 paired common-survivor frames, adaptive-minus-uniform body-position error is
`-4.20 mm` (95% unit-bootstrap interval `[-6.63,-1.90] mm`) and anchor-orientation error is
`-0.02795 rad` (`[-0.03966,-0.01628] rad`). The allocation changes by only 0.014 TV, however, so
survival and success remain inconclusive and the pilot cannot attribute those improvements to
ALP. Similarly, an earlier repair-all policy study estimates a `+0.0397` deployment change but
misses its `+0.05` smallest effect of interest and its coverage gate. These controls separate
detection, admission, repair qualification, and policy allocation instead of treating them as one
intervention.

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

The exact-support ALP sampler and its matched multi-seed protocol are implemented, but this
manuscript does not report a passed ALP-versus-uniform endpoint. Zero rejected mass and the unit
and clip caps are therefore mechanism properties, not evidence of policy superiority. The repair
route likewise needs a same-policy, distortion-aware comparison of certified repair against exact
feasible intervals and quarantine. The observation that would settle this is joint movement of
tracking, survival, reference fidelity, contact timing, and mechanical work under one paired trial
contract.

## 7. Conclusion

Reference--physics misalignment turns persistent tracking error into a misleading curriculum
signal. In the diagnosed three-seed campaign, one such reference repeatedly becomes a dominant
attractor; `refeas` localizes its unsupported wrench demand before policy training. CLIMB turns
that diagnosis into an active interface: DFRP restores qualified contacts, exact-support sampling
excludes rejected frames, and policy outcomes allocate compute only inside that gate. On the
tested artifacts, DFRP qualifies 22/26 stratified repair candidates, the hard support exposes
368,951 legal starts, and feasibility features improve difficulty transfer across policies from
`rho = 0.567` to `0.609`. Feasibility, data support, intrinsic demand, and learning progress are
therefore separate quantities that a humanoid tracking system can measure and change without
asking one noisy failure signal to represent all four.

## Reproducibility and AI disclosure

The screening and training stack uses mjlab v1.6.0 at commit `0fb8a681136b`, MuJoCo 3.11.0,
NumPy 2.5.1, and SciPy 1.16.2. Motion, sidecar, unit-table, task, checkpoint, evaluator, condition,
and output identities are SHA-256 bound. Released code and aggregate artifacts will be supplied
through an anonymous review repository; licensed AMASS-derived motion files cannot be
redistributed. OpenAI Codex assisted with code, figure composition, and language editing. The
authors verified scientific claims and artifact provenance.

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
