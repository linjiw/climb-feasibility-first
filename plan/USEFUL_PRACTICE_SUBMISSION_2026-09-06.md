# Useful practice: submission plan and continuous-execution study

Date: 6 September 2026. Unsealed addendum responding to the latest strategic
review. No frozen confirmation source, threshold, arm, seed or endpoint changes.

## Central question and bounded contribution

Given a fixed training budget, how should a humanoid practice model-admissible
motion segments so that additional experience becomes transferable tracking skill?

Working title: **CLIMB: Exact-Support Curriculum Learning for Humanoid Motion
Tracking**. Admission determines which windows the declared model/screen accepts;
allocation determines where experience goes; independent evaluation determines
what the policy learned. CLIMB does not currently identify all causes of failure.
A coverage floor cannot create missing motions, and apparent progress does not
identify intrinsic difficulty or forgetting.

The intended contributions are an exact temporal-support interface, a four-arm
three-seed policy comparison at fixed support and budget, and behavioral tests
of admission value and continuous execution. Signal intervention and physical
transfer claims require their own evidence. Debugging history remains provenance
and motivation rather than the manuscript's organizing structure.

With training budget B and fixed test distribution, the conceptual objective is
max E[J_test(pi_B)] over the sequence of admissible allocation distributions p_t,
subject to support, exposure-floor/cap and resource constraints. The marginal
value of practice is the expected difference between equal-budget targeted and
prior-distributed continuation from the same policy/optimizer state. Current
relative progress is a proposed inexpensive proxy; it does not estimate this
causal value directly.

For support interval A_u, legal starts obey s + K(H,L) contained in A_u, where K
includes every initial, intermediate and terminal reference access and observation
lookahead L. Current pinned MotionCommand reference properties use time_steps,
with no future-frame observation in the current configuration. The new support
helper handles explicit lookahead and erodes both ends as needed; the development
runtime enables only the audited zero-lookahead case. Exactness is relative to
screen membership and runtime semantics, not a physical feasibility certificate.

For complete history and positive mu = sum b_u g_u, the current pre-cap mixture is
p_u = 0.8 b_u + 0.2 b_u g_u / mu. Positive common scaling of g leaves p unchanged;
pre-cap TV(p,b) = 0.2 TV(bg/mu,b) <= 0.2. Fallback and active caps remain as
implemented. Neither property proves useful task ranking; zero true change plus
noisy estimated change can still produce positive absolute progress.

## Submission schedule verified against the official call

The [official ICRA 2027 call](https://2027.ieee-icra.org/contribute/call-for-icra-2027-papers-now-accepting-submissions/)
was checked on 6 September: paper deadline September 15, 2026; complete paper
limited to eight pages including references; reviewers need not inspect external
URLs. The page lists accompanying-video windows ending September 9 and reopening
September 17–22. Plan around the official windows, not a December research freeze.

Adopted internal milestones: September 10 claim selection; September 12 reported-
evidence cutoff; September 13–15 integration, figures and consistency checks.
These are planning gates, not promises of favorable or completed experiments.
Any older December project milestone is outside this submission schedule.

Eight-page target: introduction/problem 0.9, related work 0.6, method 1.5,
main results and learning curves 1.7, admission 0.6, mechanism 0.5, continuous or
physical execution 0.7, limitations/conclusion 0.4, references 1.1. Total eight.
If a secondary study remains incomplete, narrow the claim and reallocate its space;
do not replace essential evidence with an external link. Five intended exhibits:
exact support/method, paired primary/learning curves, admission, signal/practice
mechanism, and continuous or physical execution. No placeholder is a result.

## Current confirmation remains first

All twelve 4,000-iteration training jobs and all 48 held-out cells are complete.
The full frozen analysis reproduces exactly in its JSON representation. Each full run uses 49,152,000 simulator transitions;
completed-trial counts are exposure/accounting, not the training-budget axis.
The current held-out evaluator already scores uninterrupted windows up to three
seconds. The training trials are 50 steps; the continuous follow-up must extend
beyond those evaluation windows, not mislabel existing evaluation as 50-step.

Retain final feasible-hard R−U mean >= +0.02, positive lower two-sided 95% paired
seed t bound (df=2), and all-panel lower bound > −0.01. A pass means the point
estimate reaches the target and there is evidence for a positive effect; it does
not mean the true effect is established to exceed +0.02. Show all three paired
seed differences. Bootstrap and exploratory attainment/AULC cannot change the
frozen disposition. Retain non-attainment and sparse-checkpoint uncertainty.

The completed result is **inconclusive**: final hard R−U −0.0150684593,
two-sided seed t 95% CI [−0.0943584262, +0.0642215077]. The all-panel guard also
fails to establish non-regression. Exploratory hard AULC R−U is negative in every
seed (mean −0.0289846414), so an efficiency-accelerator claim is unsupported.
Do not add seeds or revise the current method to rescue this decision.
Full evidence: `reports/relative_confirmation_results_2026-09-06/README.md`.

## C1: continuous execution, separate prospective study

Question: do learned differences survive execution of longer genuinely continuous
admitted references? Proposed comparison: U/D/R final checkpoints, all three
training seeds, identical reference-defined sequences and paired initial states.

Before policy scoring, audit candidate support from unchanged references. Select
eligible sequences using reference kinematics and contiguous screen support only.
Distinguish complete source clips from continuous subintervals; never concatenate
across rejected transitions. Publish inclusion/exclusion counts, duration and
motion-family coverage. Do not choose sequences because one method succeeds.
A full held-out selection manifest and its hashes are still pending.

One initialization per attempt. The initial reference state is shared, disclosed
and is not a learned entry controller. No intermediate state injection, wraparound,
resampling or concatenation in a scored attempt. Retire a world at first physical
failure or declared sequence end. Vector resets after retirement do not restart
scoring. A common entry/exit controller, if later added, needs its own shared
protocol and measurement; interior tracking does not establish transitions into it.

Report full-sequence completion, sequence-length-normalized liveness-weighted
TrackingScore, physical failure causes and reference-frame failure locations.
Keep every attempted reference/repeat and all failures. Separate duration and
motion-family descriptions from the primary seed-level contrast; no frame-level
pseudoreplication. This remains an exploratory follow-up on a transparently reused
held-out panel unless a separate prospective statistical contract is frozen.

Development completed this turn: a separately bound CPU adapter runs both entire
training references selected as the first two fully admitted clips with at least
301 frames in unit-table order. They have 429/306 transitions (8.58/6.12 seconds),
two paired-condition replicates each, one fixed development R11 checkpoint 2000.
All four attempts complete, with zero active resets/reference-state writes and
429 vector inference calls; nine parameter tensors and four normalization buffers
remain identical to the loaded checkpoint. This is a pipeline smoke, not an
allocator comparison, long-sequence generalization claim or hardware result.
Thirteen pure support/continuity tests pass. Failure-path runtime coverage and
CUDA validation, complete C1 selection/analysis, then a separate freeze remain.

Sources/artifacts: new tools in `/home/linjiw/climb-icra-evidence-2026-09-06/tools/`
(`continuous_execution_support.py`, `eval_continuous_development.py`); bound design
and raw CSV/meta/policy/continuity trace in that worktree's
`reports/continuous_execution_development_2026-09-06/`; operational records under
`reports/continuous_execution_preparation_2026-09-06/` in the original workspace.
The first launcher selected the base interpreter by resolving the venv symlink;
that import failure happened before simulation. Its command/log are preserved.
Using the literal pinned venv executable succeeded without changing the design.

## Priorities after the existing queued prerequisites

1. Completed: independently reproduce the original campaign and efficiency
   analysis. Preserve the inconclusive disposition; do not claim demonstrated
   curriculum benefit or efficiency acceleration. The remaining studies ask
   about usable execution, admission and practice value on their own terms.
2. Finish continuous-execution validation and H1 admission value. H1 D-on/off
   isolates admission under D, with common candidate boundaries and normalization
   disclosed; it cannot establish an admission-by-relative-progress interaction.
3. The frozen-policy instrumentation pilot is complete. Now design independent
   repeated scoring at matched sample-count regimes. A frozen policy's apparent
   progress estimates the noise alternative only under that declared scoring design.
4. Proposed causal practice test: three development seeds × two checkpoints ×
   targeted/control branches = twelve short continuations. Clone policy, optimizer,
   normalizers and relevant RNG/state; predefine independent group-selection data,
   matched additional transitions and evaluation on targeted plus related unpracticed
   motions. Freeze budget and analysis before outcomes. These branches are not
   launched or treated as an already validated measure of forgetting recovery.
5. Only if a demonstrated signal weakness warrants it, test a new reliability-
   calibrated score [abs(delta_hat) − c sigma_hat]_+. Validate uncertainty under
   correlated histories; do not use naive IID variance or modify current R.
6. Prepare a common actor export/observation/action-interface audit before any
   physical comparison. Hardware access is unconfirmed. Proposed nominal scope:
   turning/crouching/dynamic stepping, two references per family, U/D/R and paired
   attempts. The ideal 162-attempt grid is a proposal, not an execution requirement.
   Any distillation, adaptation, deployment randomization or safety procedure must
   be common across arms. Another tracker's successful hardware demo is not
   CLIMB transfer. No physical robot run is authorized or launched by this addendum.

## Verified closest-work positioning

- [LIMMT](https://arxiv.org/html/2606.06953v1), Sections 1 and 3: motion curation
  explicitly combines physics feasibility, diversity and complexity. CLIMB cannot
  claim that recognizing data quality or filtering infeasibility is itself new.
- [GMT](https://arxiv.org/html/2506.14770v1), Section 3.1: randomized subclip
  construction and tracking-performance-based sampling. Describe its segment-aware
  design accurately rather than contrasting CLIMB with uniform whole-clip sampling.
- [EGM](https://arxiv.org/html/2512.19043v1), Section 3.2: global motion bins and
  EMA composite tracking-error probabilities. A future common-learner score adapter
  would be a component comparison, not a reproduction of its full MoE/student stack.
- [ALP-GMM](https://arxiv.org/abs/1910.07224) establishes absolute-learning-progress
  curriculum precedent. The abstract was checked; no new quantitative claim is drawn.
- [Syllabus learning-progress implementation](https://raw.githubusercontent.com/RyanNavillus/Syllabus/main/syllabus/curricula/learning_progress.py)
  uses fast/slow success estimates, their absolute difference, then z-score/sigmoid
  and probability normalization. It is related signal processing, not the identical
  CLIMB prior-weighted mixture. The linked OpenReview PDF hit a browser challenge;
  implementation claims here come from the project's source, not that unread PDF.

Defensible distinction to test: exact model-admissible temporal support plus a
controlled study of learner-dependent practice allocation and its held-out control
value. The current D comparison is between allocator designs, not a pure ranking-
only ablation. A later matched tracking-error or shuffled-score component can refine
signal attribution after the present disposition. Release reconstruction and
support/evaluation metadata where permitted, without redistributing licensed motions.

## Subsequent GPU development disposition

After the original optional-sensor graph assertion failure, all nine separately
bound corrected development cells completed. The aggregate original/unchanged
CSV equality gate failed on numerical differences. Preserve the failure and
diagnose repeatability versus instrumentation before selecting any prospective
parity criterion. No full sensitivity study is enabled and no robustness benefit
is established. See `reports/continuous_execution_preparation_2026-09-06/gpu_followup_diagnosis.json`.
