# Research design: feasibility-gated tracking with scale-relative progress

Date: 2026-09-05. Status: **exploratory design and authorized simulation execution**.
This is an addendum to the research program, not an amendment of any sealed study.
The user requested a progress review, full design/research plan, implementation,
and initial experiments. This document selects the next direction using completed
artifacts. The existing untracked relative-progress prototype predates this turn;
the new work is its execution contract, verifier, lifecycle validation, and study.

## 1. Decision and current evidence

Prioritize **a reliable adaptive allocator inside the existing exact feasibility
gate**, followed by a matched gate ablation. The immediate hypothesis is that
normalizing progress by its deployment-weighted mean prevents a fixed additive
floor from erasing allocation contrast late in training. Sustained contrast is a
necessary manipulation check; it is not evidence of useful learning by itself.

| Evidence | Label and result | Consequence |
| --- | --- | --- |
| E4 seed 1, two 4,000-iteration arms | **sealed decision: not_tested**; mean post-warm-up TV 0.0296587 fails the 0.05 minimum; policy evaluation endpoints remain closed | Do not call E4 a policy null or continue seeds 2–3 under its failed gate |
| Exact sampler replay, eight E4 ALP snapshots | **measured replay**; the absolute floor contributes 64.3% to 93.6% of the focus normalizer from iteration 500 to 3999; probability caps did not explain these snapshots | A specific scale failure is testable without policy outcome access |
| Relative factor 2 on the same eight histories | **exploratory counterfactual**; TV 0.0560–0.1087, mean 0.0854 | Motivates one fixed candidate; endogenous histories require fresh training |
| DFRP fixed-policy panel | **measured exploratory simulation**; 26 clips, 656 conditions per arm, clip-weighted TrackingScore 0.392505 raw vs 0.391502 repaired, delta −0.001003, clip-bootstrap 95% CI [−0.008588,+0.008020] | No aggregate improvement demonstrated; repeatability and repair-specific analysis precede more repair training |
| E-HYG and soft FGAS | **sealed null / failed implementation gate**, respectively | Clip deletion and soft multipliers are insufficient evidence for the active method |
| Newton predictive gate | **sealed fail** | Retain Newton as an instrument; do not revive G3 |
| Exact gate implementation | **measured artifact contract**; 1,184 units and 368,951 legal 50-step starts from 800 motions | Preserve this interface; distinguish model admissibility from closed-loop feasibility |

Evidence paths:
`reports/g_segment/confirmation/seed1/manipulation_result.json`,
`reports/g_segment/confirmation/allocation_diagnosis.json`,
`reports/dfrp_policy_validation_2026-09-05/result.json`,
`plan/E_HYG_RESULT.md`, `plan/FGAS_RESULT.md`, `plan/NEWTON_PRED_RESULT.md`,
`reports/g_segment/unit_table.json`.
The repair uncertainty resamples clips for one fixed policy; it is not training-seed
uncertainty. Small unchanged-control differences require numerical-repeatability
accounting. The historical fixed-policy repeat remains a separate study.

## 2. Research question and intended contribution

Deployment setting: a Unitree G1 controller trained in pinned mjlab 1.6.0 on a
flat scene, consuming final robot-space retargeted reference windows. The scarce
resource is policy-training exposure on a shared GPU. A difficult reference may
be informative, unsupported by the scene/model, or an estimation-noise outlier.

Question: after exact admission and horizon semantics are held fixed, can
scale-relative learning-progress allocation sustain a useful curriculum and
improve feasible held-out motion tracking at equal simulator steps?

Provisional contributions, conditional on their evidence:

1. A reproducible diagnosis of how absolute ranking floors suppress an intended
   curriculum intervention as progress amplitudes decay.
2. A scale-relative allocation rule composed with exact legal-start support,
   duration exposure, exploration floors, and joint unit/clip caps.
3. A matched simulation evaluation separating manipulation, progress informativeness,
   policy utility, and gate efficacy, with failed gates and nulls reported.

The algebraic normalization alone is a small engineering change. A methods claim
requires evidence for the composition and policy value, beyond increased TV.

## 3. Literature boundary, checked 2026-09-05

[ALP-GMM](https://arxiv.org/abs/1910.07224) already uses absolute learning progress
to build curricula and studies learnable/unlearnable environments. We do not
claim to invent learning-progress sampling. Its continuous task-generation model
differs from this fixed exact-start motion bank.
[BeyondMimic, §III-F](https://arxiv.org/html/2508.08241v1) uses empirical failure
information for adaptive motion sampling; a failure-based allocator is therefore
a relevant matched baseline, while our test does not reproduce its entire system.
[Athena-WBC](https://arxiv.org/abs/2607.04837) and
[LooperMuscle](https://arxiv.org/abs/2608.00820) are recent whole-body-control
alternatives involving experts/training recipes. Their abstracts were checked;
a full algorithm/code comparison is pending before any priority or state-of-the-art
claim. They change more components than the immediate sampler ablation.

This targeted primary-source scan is not an exhaustive novelty review. No current
best-performance claim or hardware transfer claim is proposed.

## 4. Method and implementation contract

Let U be admitted units, F the frozen admission decision, and b the normalized
deployment mass over U. Each sample chooses a unit and then an exact legal start;
its H=50 transitions cannot wrap a clip or leave the admitted interval. The screen
uses declared robot/scene constraints offline and is independent of policy error.

The existing fixed-clock estimator computes absolute changes in smoothed
conditional success rate across a 10-tick history: g_u ≥ 0. Keep its event
attribution, priors, decay, and clock unchanged. Define μ = Σ b_u g_u.

```
if history incomplete or μ = 0: p = existing deployment-prior/cap operator
otherwise:
    w_u = g_u / μ + κ                     κ = 2
    p = existing capped mixture(b, w, ρ)   ρ = 0.40
```

Before active caps, q_u = b_u(g_u/μ + κ)/(1+κ), p_u = ρb_u+(1−ρ)q_u.
Thus this candidate also equals an unregularized progress distribution mixed
with the base at effective exploration 0.80; this equivalent parameterization
must be disclosed. It is not a new information source. Its TV is
`(1−ρ) E_b|g−μ| / [2 μ (1+κ)]`, invariant to common positive rescaling of g
in exact arithmetic. The existing joint cap operator retains the scale invariance
because its input distributions are identical. Floating-point extremes still need
finite-input checks. Positive but noisy g remains an unresolved failure mode.

Fixed: robot, observation/action spaces, PPO, rewards (failure penalty −10),
800-motion identity, legal starts, estimator, 0.05 unit cap, 0.25 clip cap,
50-step trial clock, seed assignment, and bank hash verification. New weights
live in `climb/relative_progress.py`; the isolated task is
`Climb-Tracking-Flat-Unitree-G1-RelativeALP-Probe`.
No new deployment-time sensors, network, or physics oracle is required.

`tools/train_relative_progress_probe.py` writes checkpoint-linked telemetry and
sampler state every 100 iterations. Launch-time source identities, sampler/training
seeds, environment count, table hash, rank configuration, actual probabilities,
completed/censored/invalid events, and saturation are recorded.
`tools/check_relative_progress_probe.py` requires the complete cadence, reproduces
sampler probabilities from checkpoint state, checks exact support identity, floor,
both caps, finite diagnostics, source/checkpoint bindings, and event accounting.
It never loads policy-evaluation CSVs. Sampler replay is not a bitwise claim for
resuming an entire simulator rollout; interrupted training is a recorded attempt.

## 5. Staged experiments and decision rules

### R0: implementation and lifecycle smoke — immediate

Pure tests cover positive scale invariance, zero-progress fallback, invalid inputs,
exact legal starts, sampler resume, and incompatible relative factors. Verifier
tests must reject incomplete telemetry and corrupted provenance/state.
Then run seed 11, 8 environments, 20 PPO iterations. Require iteration 0 and 19
checkpoints/ledgers/states, correct task configuration, completed trials, zero
invalid/censored events, both caps and floor respected, exact replay, and valid
source bindings. Low TV in this short smoke is not a reason to tune κ.

### R1: sustained manipulation — start after R0

Fresh seed 11, 512 environments, 4,000 iterations, save every 100 plus final 3999.
Exactly 41 snapshots; 37 at iterations ≥400 enter the mean. Fixed gates from the
pre-existing probe plan: mean TV ∈[0.05,0.15], all post-warm-up entropy-effective
unit counts ≥12, unit mass ≤0.05, zero invalid/censored events throughout, and
final rank saturation <0.90. Also enforce the existing clip cap and exploration
floor. No endpoint evaluation. One run is one training replication.

Pass → independent R2. Fail → stop this candidate and report the failed condition;
do not select a favorable checkpoint or retune κ on this trajectory. Malformed or
missing artifacts → invalid/incomplete, not a scientific fail or a pass.

### R2: independent manipulation replication — conditional

Repeat R0/R1 with seed 12 and unchanged settings only if seed 11 passes. Both full
runs must pass. No pooled mean can hide one failed seed. These are exploratory
development seeds and cannot later become confirmatory training replications.
If both pass, prepare a new pre-outcome benchmark manifest and analyzer.

### R3: progress meaning and policy utility — future confirmation

Four exact-gated arms: deployment-uniform U, absolute-floor ALP A (λ=0.05),
relative ALP R (κ=2), and conditional failure-rate allocation D. This separates
useful ALP from any nonuniform exposure and from the previous absolute floor.
All arms receive the same 512 environments, 4,000 iterations, PPO/DR/reward,
support and seeds 21/22/23. No existing E4 checkpoint substitutes for a fresh arm.
The D configuration must be fixed using separate training-only calibration seeds
and a written equal tuning budget before these seeds run; benchmark launch is
pending that manifest. Historical failure-flux sampling is not relabeled D.

Reuse the existing hash- and name-disjoint 100-motion evaluation panel and its
reference-defined 25 feasible-hard clips; verify the fixed 2,800-condition
manifest again. Evaluate iterations 1000/2000/3000/3999, using identical starts,
noise identities, horizon and raw references across arms. Failed episodes remain
in the denominator. One primary contrast: final R−U clip-averaged liveness-weighted
TrackingScore on feasible-hard clips. Proposed SESOI +0.02 absolute score and
all-panel non-regression margin −0.01 are design choices, not measured effects.
Freeze them and the numerical analyzer in a new study before any benchmark run.

Training seeds are the independent policy replications; report each paired seed
delta, mean, SD and a seed-level interval. Three seeds imply low precision and
cannot support a strong small-effect significance claim. Hierarchical paired
seed/clip bootstrap (10,000 draws, analysis seed 20260905) is supplementary,
with all replicate deltas visible. No optional extra seeds after outcomes; an
expanded sample requires a new prospective study.

Positive requires the predeclared primary mean ≥+0.02, a positive lower seed-level
95% bound, and the predeclared non-regression lower bound above −0.01. Negative
evidence means the upper bound excludes +0.02; other cases are inconclusive.
A failed manipulation/provenance gate is not_tested/invalid respectively. A null
does not establish equivalence. Secondary R−A and R−D contrasts, AULC, survival,
per-clip losses, common-survivor pose errors (with retained denominators), work
and training cost are descriptive; stronger multiple-comparison claims require
an explicitly frozen multiplicity policy.

An R-versus-U win alone establishes allocation utility, not accurate progress
ranking. A separate shuffled-rank control and fixed-policy repeated-rollout noise
panel are the next diagnostic if R does not beat D or if ranks are unstable.
Record temporal rank stability and attempt counts as diagnostics; these do not
serve as substitute policy endpoints. Do not silently add uncertainty shrinkage
or a noise threshold to the current relative candidate.

### H1: isolate gate efficacy — after allocator direction is resolved

Compare the same conditional-failure allocator with/without dynamic admission
on the same contaminated 800-motion candidate set. Both retain exact non-wrapping
H=50 horizons; construct candidate units from source intervals before admission.
Gate removal must be the only changed mechanism. Preserve duration accounting
and feasible support identities, and record changed normalization explicitly.
Use three fresh matched seeds and equal training/evaluation contracts. Freeze
contamination strata from reference-only scores, rejected probability mass,
unit and clip concentration, and feasible-hard TrackingScore before launching.
The cap bounds possible concentration in both arms; historical 88% clip peaks
are not an appropriate target under a 25% clip cap. Zero rejected mass follows
from the gate by construction; only preserved/improved learning establishes
practical value. A collapse-prevention headline needs this matched comparison.

### Repair and smooth weights — deferred branches

Keep DFRP repeatability/control accounting separate. Certified repair merits a
new training arm only after its fidelity and repeatability limits are resolved;
larger edits or excluded qualification failures cannot supply its headline gain.
Smooth feasibility weighting and learned feasibility are deferred until hard-gate
utility and boundary errors are measured. Hardware remains outside this study.

## 6. Compute, artifacts, and execution

Each full arm consumes 4,000 × 512 × 24 = 49,152,000 simulator transitions.
The historical local G1 arm took 1,912 seconds (0.53 GPU-hours elapsed allocation);
R1/R2 budget approximately 1–2 GPU-hours total, allowing setup and contention.
The future four-arm/three-seed benchmark is 12 training arms (about 6.4 hours at
that historical rate, budget 8–12 plus separately measured evaluation costs).
These are estimates, not new measured throughput. Log peak total/baseline VRAM,
elapsed time, failures, and queue delay. Use the shared 14,000-MiB memory gate;
do not interrupt other jobs. Automatic OOM retries are disabled for this study
so a failed attempt cannot disappear behind a successful rerun.

Immediate command (a fresh output directory is mandatory):

```bash
mjlab-1.6.0/.venv/bin/python tools/run_relative_progress_study.py \
  --seed 11 --out-dir reports/relative_progress_2026-09-05/study_s11
```

The runner executes smoke → strict validation → fresh full training → full
validation, preserving argv, source/design hashes, training logs, result JSONs,
and terminal status. `--smoke-result` can reuse a completed same-seed smoke only
if the checker exactly reproduces its result and all current source hashes match.
It does not execute R2/R3/H1 automatically. No publication or messages are part
of this authorization. No sealed file or seal manifest is changed.

## 7. Claim–evidence map and deliverables

| Claim | Mechanism/test | Comparator and independent unit | Evidence needed / limitation |
| --- | --- | --- | --- |
| Fixed floor diluted E4 contrast | exact probability replay | eight snapshots of one seed | already measured; histories are correlated |
| Candidate is amplitude invariant | algebra + rescaling test | same rank vector under common scaling | finite nonnegative inputs; no claim about rank quality |
| Candidate sustains allocation | R1 and R2 complete ledgers | two new training seeds | pending; TV is a manipulation measure |
| Candidate improves learning | R3 paired policy outcomes | R vs U/A/D; three fresh paired seeds | pending; low seed count limits uncertainty |
| Gate protects useful learning | H1 | same allocator, gate toggled; fresh paired seeds | pending; one corpus/pipeline/scene |
| Repair improves tracking | independent DFRP follow-up | same policy raw/repaired | current aggregate gain unsupported |

Required outputs: design and execution binding; complete machine-readable result
including stop reason; a TV-versus-iteration figure with the accepted band and
all snapshots; seed-level learning curves and per-clip loss tables only after R3;
updated status and paper results log with exact source paths. The strongest
currently defensible statement is that the scale failure has an identified
replay mechanism and a testable isolated repair. Policy benefit remains pending.
