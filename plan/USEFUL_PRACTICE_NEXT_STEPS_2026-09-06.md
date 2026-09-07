# When does changing practice improve robot learning?

Date: 2026-09-06. **Unsealed research-plan addendum.** Confirmation remains
governed by its existing design, prerequisite decisions and prospective freeze.
This document changes the follow-on research priorities, not the current method
or primary endpoint. No hardware experiment is proposed.

## Research question and contribution to earn

For simulated G1 tracking in the declared scene, does selecting robot-admissible
practice using credible policy change improve held-out control at equal training
transitions? Separate three propositions: model admission, reliable measurement
of change, and causal value of extra practice. The existing allocation passes
establish intervention strength; they do not establish the latter two propositions.

The proposed paper contribution has three parts, with status carried forward:

1. An exact-support interface separating admissible reference windows from policy
   success, retaining the declared 50-transition non-wrapping trials (**implemented**;
   practical gate benefit **pending**).
2. A controlled four-arm comparison on three paired training seeds inside that
   interface (**pending**), with useful control as the outcome and allocation
   telemetry as the explanation of exposure.
3. A development measurement protocol distinguishing apparent progress from
   stationary-policy variability, followed conditionally by equal-budget practice
   branches (**proposed**; no noise, forgetting-recovery or practice-value finding).

Progress-driven curricula already exist in
[Graves et al.](https://proceedings.mlr.press/v70/graves17a.html) and
[ALP-GMM](https://arxiv.org/abs/1910.07224). These primary sources were checked
2026-09-06. The contribution to test is the value of the robot-specific
composition, not invention of progress sampling. Other literature in the supplied
guidance has not been independently audited in this addendum.

## Immediate execution: finish the fixed comparison

Both fixed D calibrations now pass and were independently replayed in full:

| Seed | Mean post-warm-up TV | Minimum post-warm-up effective units | Final saturation | Completed trials |
| --- | ---: | ---: | ---: | ---: |
| 31 | 0.08495534 | 625.06174 | 0.72719595 | 1,113,773 |
| 32 | 0.08593871 | 624.28880 | 0.73817568 | 1,118,388 |

Classification: **measured exploratory allocation**, with zero invalid/censored
events verified by the existing full-history checker. Evidence:
`reports/research_next_2026-09-06/calibration_verification.json` and the original
`failure_calibration_gate_retry/seed{31,32}_result.json` records. No policy-benefit
number is inferred from these histories.

At the 00:39 EDT handoff, the existing seed-51 worker (PID 1541297) had prepared
U's launch record but had not launched its trainer; the shared GPU was occupied.
The actual freeze check reproduced the draft and identified only the four
seed-51 smoke results as missing. An external operational supervisor (launch PID
1722327) now waits for this worker's terminal pass, runs the existing freezer,
checks its receipt and seal, and executes its exact structured scheduler argv.
It refuses failures, changed bindings, existing freeze output, and retries.
It does not launch the proposed diagnostics or H1 experiment.

The unchanged confirmation is U/A/R/D × seeds 21–23, 512 environments,
4,000 PPO iterations, checkpoints 1000/2000/3000/3999. All 12 training gates
must pass before the 48 paired held-out evaluation cells. Final feasible-hard
R−U TrackingScore remains primary: mean improvement at least +0.02, positive
lower seed-level 95% bound, and all-panel lower bound above −0.01 under the
existing decision implementation. Do not add a mechanism, replace a checkpoint,
increase mixture strength, revise the horizon, or add seeds to rescue an outcome.

Durable operational records:

- `reports/research_next_2026-09-06/handoff_launch.json`: exact argv and PID.
- `reports/research_next_2026-09-06/handoff/`: wait design, eventual freeze and
  scheduler logs, and terminal disposition.
- `reports/relative_progress_2026-09-05/confirmation_freeze/campaign/`: eventual
  seed-level training/evaluation artifacts and `analysis.json`; absent until the
  prerequisites and freeze succeed.

GPU availability remains an external dependency. A queued supervisor is not a
completed comparison. A timeout or failed smoke must retain its actual disposition;
the handoff will not silently restart it.

| Fixed-study outcome | Research decision |
| --- | --- |
| Declared final R−U benefit and non-regression pass | Report bounded policy benefit; prioritize matched H1. |
| R helps but R−D is unresolved | Adaptive allocation may help; retain D and make no progress-specific superiority or equivalence claim. |
| Only intermediate learning curves favor R | Exploratory efficiency lead; a new fixed efficiency endpoint requires a separate prospective study. |
| Valid uncertainty rules out +0.02 benefit | Preserve the negative conclusion for this configuration; diagnose signal quality/practice utility before another full allocator campaign. |
| Intervals remain wide | Inconclusive at three training seeds; additional conditions are not additional trained policies. |
| Training/provenance gate fails | Preserve not-tested/invalid status and existing endpoint-access rules. |

## Separate development workspace and completed analytical check

Workspace: `/home/linjiw/climb-signal-quality-2026-09-06`, detached from commit
`1552c99`, with copies of all 130 current Python/shell sources under `climb/` and
`tools/`. The copy includes the current untracked research sources; checking out
HEAD alone would omit them. Identities are recorded in
`reports/research_next_2026-09-06/source_snapshot.json`. New diagnostics live
only there; their output root is that worktree's
`reports/research_next_2026-09-06/`. Original `tools/`, `climb/`, profiles, sealed
files and manifests remain unchanged. Runtime inventory verification still uses
the original campaign root. Development policies are accessed read-only by exact
path/hash; confirmation endpoints are not diagnostic inputs.

For positive mean progress μ and inactive caps, the current rule gives

    TV(p,b) = 0.1 E_b |g/μ − 1|.

For g = σ|Z|, positive σ, equal prior and independent standard-normal Z, let
m = sqrt(2/π). The large-unit limit is

    0.2 [erf(m/sqrt(2)) − 1 + exp(−m²/2)] = 0.06048797312237089.

`tools/reproduce_noise_only_tv.py` in the separate worktree independently checks
the closed form against quadrature, direct probability TV and scale invariance.
The new run uses RNG seed 260906, 2,000 repetitions and 1,184 units: mean TV
0.0604042781, Monte Carlo standard error 0.0000271173; all draws exceed 0.05.
This is a new **synthetic** reproduction, not the supplied attachment or the
user's particular random draws. Finite-unit simulation need not equal the
large-unit limit. Artifact: worktree `reports/research_next_2026-09-06/noise_only_tv.json`.

This example omits the actual nonuniform prior, history, unequal exposure and
joint cap operator. Do not subtract its value from observed TV. At exactly zero
progress, the implementation falls back to the prior; the positive-noise limit
does not imply a nonzero TV for an exactly zero vector.

## Development study N: measure stationary-policy apparent progress

**Hypothesis:** online absolute progress includes a material measurement component;
the amount and selected units must be measured, not assumed. The main deliverable
is observed change against its empirical frozen-policy distribution, with
post-cap TV as a secondary readout.

Use R seeds 11 and 12 at iterations 2000 and 3999, four cells chosen without
confirmation outcomes. Twelve development checkpoints and their sampler/ledger
files have been hash-bound in `reports/research_next_2026-09-06/development_inputs.json`.
That inventory also binds the auxiliary change pairs and branch checkpoints.

Run the actual training environment, exact unit/start sampler and completed-trial
attribution, but disable PPO updates and freeze actor parameters and observation
normalization. Retain sampled actions and the training randomization relevant to
outcomes. Hash actor/normalizer tensors before and after each block. Seed policy
sampling, environment perturbations and exact-start RNG separately for independent
repetitions; log their identities. Identical deterministic rollouts do not count
as independent uncertainty measurements.

The source audit finds an estimator update every **50 environment steps**, decay
**0.99 per tick**, and progress over **10 ticks (500 environment steps)**. Replay
must preserve this clock, pending outcomes, rates, unit attribution and caps.
PPO iterations use 24 steps and cannot substitute for estimator ticks. Saved
100-iteration checkpoint spacing is about 48 ticks, so existing checkpoint pairs
cannot independently reconstruct the exact 10-tick online policy-change signal.

Before scored blocks, reset estimator history and settle under the frozen policy.
Never label inherited learning history as stationary noise. Instrument per-tick,
per-unit attempts/failures, discounted attempt mass, last-exposure age, prior mass,
signed and absolute changes, pre-/post-cap probabilities, and invalid/censored
events. Trial failures stay in denominators. Units with inadequate measurement
remain explicitly uncalibrated; do not remove them from the whole-distribution TV.

**Next implementation step:** build a 100-tick instrumentation/cost pilot on
seed 11 at iteration 2000, 512 environments, in the separate worktree after the
confirmation has GPU priority. Budget: 2,560,000 transitions, excluding setup;
this pilot is not a stationary-null result. Verify policy immutability, event
replay, clock cadence and independent randomness before scientific measurement.
Record sample counts and throughput to specify burn-in and scored-block lengths
prospectively for the four-cell study. No new GPU diagnostic has launched.

Burn-in is a real resource issue: 688 ticks reduce an inherited discounted-mass
multiplier below 0.001, requiring 17,612,800 transitions at 512 environments,
before a scored block. This multiplier is neither a rate-bias bound nor proof of
stationarity. Use coupled estimators with different initial histories on the
same pilot event stream to diagnose initialization dependence, and examine
exposure-poor units separately. Fix a settling tolerance and maximum burn-in from
the pilot before the independent scored runs. A stream that does not settle
within its prospective budget is calibration-incomplete, not a favorable null.
Do not promise a small full study by ignoring burn-in or count replayed blocks
as fresh rollout repetitions.

For the scored study, use at least two independent rollout streams per cell,
with the exact repeat count and scored length fixed after the instrumentation
pilot. Report cell-level distributions and sampling uncertainty conditional on
each frozen policy; four cells are only two development training seeds.
Compare apparent progress/excess mass by attempt count, baseline success,
history age and prior mass. Fit any empirical noise thresholds on calibration
blocks and evaluate them on separate blocks. Thresholds remain empirical
quantiles, not automatically simultaneous confidence bounds.

To check independent change rankings with available checkpoints, compare
1900→2000 and 3900→3999 using separate rollout blocks for each endpoint and each
replicate. Publish sign agreement, rank correlation and excess-mass overlap
with explicit common-unit coverage and tie handling. These are longer-interval
change measurements, not a validation of exact 10-tick online rankings. Testing
that exact interval requires separately saved development checkpoint pairs.

## Next full comparison H1: practical value of admission

**Pending separate prospective freeze.** Keep the existing H1 proposal: the same
conditional-failure allocator D on the same contaminated 800-motion candidate
bank, dynamic admission on versus off, three fresh paired seeds and equal
training transitions. Construct candidate units from source intervals before
admission. Gate-off retains exact legal H=50 starts and never wraps or reads past
a reference; dynamic rejection and horizon legality are different conditions.

Keep controller, rewards, PPO, randomization, unit/clip caps and evaluator fixed.
Bind the candidate universe, common feasible-unit identities, reference-only
contamination strata, duration/legal-start counts and changed support
normalization before launch. Proposed training budget is six 4,000-iteration
arms at 512 × 24 steps, 294,912,000 transitions; runtime remains unmeasured.
Choose and audit fresh seeds in the new H1 contract, without reusing confirmation
outcomes as calibration data.

Primary estimand: paired-seed final feasible-hard TrackingScore, gate-on minus
gate-off. Report all feasible-panel outcomes and seed-level intervals. Freeze
the practical benefit/non-regression margins before training; retaining +0.02
and −0.01 is the starting proposal, not an already sealed H1 decision.
Rejected exposure is a mechanism measure; zero under hard admission follows
from construction. The historical approximately 88% clip concentration is not
a target under the current 25% clip cap.

An inconclusive allocator result does not by itself invalidate testing D with
and without the gate. A positive R result raises H1's submission priority. A
reference-blind size/duration-matched exclusion arm would isolate the value of
physics-informed selection beyond data removal, but is deferred from the minimum
two-arm study. Longer legal tracking intervals are a separate evaluation with
recomputed starts, never an amendment to the current primary endpoint.

## Conditional study P: the value of extra practice

Branch R development seeds 11/12 at checkpoints 1000/2000/3000 into U/R/D and
shuffled-score exposure for 100 additional PPO iterations each. Equal budgets
give 24 branches × 100 × 512 × 24 = **29,491,200 transitions**, exactly **5%** of
confirmation's 589,824,000 training transitions. Probe evaluation, restoration,
burn-in and diagnostic costs are additional; this ratio is not a runtime estimate.

Checkpoint structure audit confirms actor, critic, both observation normalizers
and optimizer state are present in all 12 inventoried checkpoints. Evidence:
`reports/research_next_2026-09-06/branch_state_inventory.json`. Full restoration
behavior is still untested. Restore the optimizer moments and current learning
rate, iteration/schedule, normalizers and sampler history; verify equal initial
tensors and optimizer state across arms. Existing actor-only evaluation loading
is insufficient. Define a common reset-boundary environment initialization and
paired future RNG streams; do not claim exact training continuation unless
simulator/RNG state restoration is also verified. After branching, normalizers
may update identically by algorithm, while their values can diverge with exposure.

Use one fixed development probe panel of training-bank units/conditions, excluded
from PPO updates in every branch, with hashes and exact legal starts fixed before
branching. This measures local transfer within development data, not fresh
confirmation generalization. Declare the resulting common training support and
renormalized priors. Baseline J(theta_t) and final J(theta_{t+100}) use the same
probe condition distribution, independent of ranking/calibration blocks.

Primary contrast is [J_R(after)−J(before)]−[J_U(after)−J(before)]. Report each
seed/checkpoint cell and seed summaries; checkpoints within a seed are correlated.
R−D and R−shuffled are secondary local mechanism comparisons. Use the same history
to initialize D and R where the contract permits, rather than giving one arm an
arbitrary cold start. This is a local intervention on R-trained policy states;
it does not establish equal value for policies reached by every curriculum.

Shuffle within prior/exposure strata fixed from development data, apply the
existing cap operator, and report resulting TV, entropy/effective support and
clip concentration. Do not use favorable outcome selection to tune a shuffle.
Without prospectively demonstrated distribution-strength matching, call it a
shuffled-score control, not a ranking-only ablation. Preserve all unsuccessful
probe conditions in the declared score. A forgetting-recovery claim additionally
needs independently verified declining units randomized to targeted exposure
versus matched exposure; improvement following selection alone is insufficient.

## Conditional method: calibrate priorities and adaptation strength

Only after N supports useful calibration and P or confirmation identifies a
reason to act on it, propose h_u = max(g_u−nu_u,0), G = sum(b*g), H = sum(b*h),
and alpha = 0.2 H/G for G>0, otherwise zero. Use the same cap/support operator on
(1−alpha)b + alpha b*h/H when H>0; use the prior/cap fallback otherwise.

For nonnegative thresholds, 0≤H≤G, so alpha≤0.2 and pre-cap prior weight≥0.8.
With zero thresholds this reduces to current R; with no retained signal it
returns to the prior. A useful equivalent pre-cap expression for G>0 is
(1−0.2H/G)b + 0.2 b*h/G, avoiding division by H. H/G is a retained-signal proxy,
not a probability of genuine learning. Outlier scores must not automatically
receive a full 20% budget after most scores are removed.

Keep credible declines initially. Future prospective ablation: current R,
noise-shrunk scores with fixed strength, and noise-shrunk scores with adaptive
strength. No such change belongs in the bound campaign. Repair expansion,
smooth weights, simulator migration and architecture changes remain deferred.

## Claim–evidence map and paper priorities

| Claim | Evidence / comparator | Independent unit and present limit |
| --- | --- | --- |
| R changes exposure | R11/R12 complete allocation histories | Two development seeds; no control benefit established. |
| R improves held-out control | Fixed final R−U, declared all-panel guard | Three paired training seeds; pending. |
| Selected change exceeds measurement variability | N, frozen policies with independent rollout streams | Conditional on four checkpoint cells from two seeds; pending. |
| Acting on priorities buys learning | P, equal-budget branches from identical checkpoints | Two development seeds; local effect, pending. |
| Admission protects useful learning | H1, same D with gate on/off | Three fresh paired seeds; pending. |

Lead the results figure with held-out TrackingScore versus training transitions,
show individual training seeds, and place allocation curves alongside as exposure
evidence. Add mechanism figures only when measured. Define video motion families
and success/failure selection rules before inspecting clips. The official
[ICRA 2027 call](https://2027.ieee-icra.org/announcements/call-for-technical-papers/)
still lists **September 15, 2026** for contributed papers (checked 2026-09-06).
Protect time for the fixed comparison and the strongest feasible H1 evidence;
the reliability-aware redesign must not displace them. Any incomplete component
remains pending in the manuscript, even at the deadline.
