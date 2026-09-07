# Matched gate runtime: implemented and exercised with PPO

Date: 2026-09-06. **Unsealed development addendum** to
`FROZEN_PROGRESS_PILOT_AND_GATE_AUDIT_2026-09-06.md`. This stage implements the
gate comparison's runtime and validates its lifecycle; practical gate benefit
remains pending. The original confirmation and queued frozen-policy pilot are
unchanged.

## Completed step

The two gate runtime views now share the audited candidate-start partition and
use the same conditional-failure D sampler. Gate-on retains the original 1,184
feasible units; gate-off admits all 1,649 candidate intervals. Both use the same
800 reference motions, exact H=50 non-wrapping semantics, rewards, controller,
randomization, PPO, 0.8 prior floor, 0.05 unit cap and 0.25 clip cap.

Worktree: `/home/linjiw/climb-gate-ablation-2026-09-06`, detached from `1552c99`
with copies of the original 130 current Python/shell sources, including the
untracked research code. No source in the original campaign or in the source-bound
frozen-policy pilot was edited. This third worktree allows further H1 work without
invalidating either queued study.

## Representation and runtime checks

`tools/prepare_gate_runtime.py` reconstructs the candidate start partition from
the source-bound sidecars and checks equality with the previous audit. Existing
feasible unit IDs, start intervals and deployment masses are preserved.
Rejected intervals receive new IDs above the original source-unit ID range.

For a rejected start interval `[a,b)`, the runtime reference span is represented
as `[a,b+H)`. Starts remain in `[a,b)`, so every trial satisfies `start+H < b+H`
and the source clip boundary. These spans can overlap in reference frames;
their start sets are disjoint. This preserves boundary-crossing rejected windows
that would be lost by constructing only fully rejected frame segments.

The two runtime manifests share the same `source_units` candidate table and
source bank. Their selected runtime rows differ only by the admission mask.
The runtime's historical field name `admissible_units` denotes allowed exact
starts in this development interface; gate-off rows are explicitly labelled
as dynamically rejected and must not be described as physically admissible.

`climb/gate_ablation.py` verifies the manifest hash, gate setting and exact mask,
then delegates sampling and trial execution to the original `SegmentSampler`
and `SegmentNativeMotionCommand`. It adds gate-specific rejected-probability and
completed-trial telemetry. Gate-on reproduces the original D sampler's ordered
unit IDs, legal-start intervals and startup probability tensor exactly.

Configuration comparison removes only admission, its manifest/path binding and
the administrative run name; every other environment and PPO field is equal.
Both commands use the same class. The unit tests also draw 20,000 exact starts
per arm, check terminal-frame/clip bounds, stress the prior floor and joint
caps with concentrated synthetic failure statistics, and reject an incomplete
candidate partition or tampered mask. These are implementation checks.

## Measured matched CPU PPO smokes

`tools/train_gate_smoke.py` permits only the fixed development lifecycle:
seed **71**, **8 environments**, **20 PPO iterations**, **24 steps per iteration**,
**3,840 transitions per arm**, checkpoints **0 and 19**. It does not expose the
full H1 budget or confirmation seeds. Both arms started with identical actor
tensors under the matched seed.

| Arm | Completed trials | Completed trials from rejected support | Final post-cap rejected probability | Elapsed CPU job seconds |
| --- | ---: | ---: | ---: | ---: |
| Gate-on D | 179 | 0 | 0 | 24.9197 |
| Gate-off D | 196 | 32 | 0.11434515 | 24.2224 |

Both completed with zero invalid starts, invalid reference frames or censored
resets. The saved sampler states, probabilities, completed/failure counters and
rejected-support telemetry replay exactly at both checkpoints. Gate-off thus
actually exercised restored support during PPO; gate-on excluded it. Differences
in trial counts or this short run's training rewards do not measure control
benefit. No held-out evaluation was performed. CPU elapsed times are not GPU
runtime estimates.

Task IDs:
`Climb-Tracking-Flat-Unitree-G1-Gate-On-Development` and
`Climb-Tracking-Flat-Unitree-G1-Gate-Off-Development`.
Exact argv, CPU environment overrides and seed are in
`reports/gate_runtime_2026-09-06/cpu_{on,off}_launch.json` in the new worktree.
Raw logs, execution durations, checkpoints and ledgers are retained there.
`tools/analyze_gate_smokes.py` reproduces both complete smoke decisions and checks
configuration and initial-actor equality. Its paired result is
`reports/gate_runtime_2026-09-06/paired_smoke_result.json`.

Eleven targeted tests pass, and the four new Python runtime/builder/trainer/
analyzer files compile. Verification scope remains development implementation;
the full comparison has not run.

## A gate-specific allocation check

The rejected share of the full legal-start prior is
`r = 48,121 / 417,072 = 0.11537816012582959`. At startup the actual gate-off cap
operator retains exactly that rejected probability. For the fixed D rule, the
existing operator preserves the per-unit floor `p_u >= 0.8 b_u`. Summing over
rejected units gives the deterministic lower bound

    P(rejected | gate-off) >= 0.8 r = 0.09230252810066368.

Applying the corresponding floor to the complementary admitted set gives

    P(rejected | gate-off) <= 0.8 r + 0.2 = 0.2923025281006637.

These bounds assume the same fixed support/prior and successful floor/cap
constraints, which must be verified at runtime. Gate-on rejected probability
is exactly zero by construction. Tests cover failure rankings concentrated on
rejected units, on admitted units, and uninformative all-success statistics.

This gives H1 an admission-specific manipulation check without requiring a
progress-ranking TV threshold: verify the bounds at every saved sampler snapshot
and verify actual exposure accounting throughout. The bound concerns sampling
probability, not the share of consumed PPO transitions. Early failures affect
trial duration, and rejected probability is not a measured waste or benefit.

## Prospective full-study draft and next implementation step

`reports/gate_runtime_2026-09-06/h1_study_draft.json` records the proposed two-arm
study: seeds 61/62/63 (fresh-seed audit still pending), 512 environments,
4,000 PPO iterations, checkpoints 1000/2000/3000/3999, **294,912,000 training
transitions** across six arms. This is a non-executable draft with
`full_training_enabled=false`, not an already frozen experiment.

The primary estimand is final feasible-hard clip-weighted TrackingScore,
gate-on minus gate-off, with training seed as the independent unit and a two-sided
95% paired t interval with two degrees of freedom. The proposed improvement
decision retains mean gain at least +0.02, positive lower bound, and the all-panel
lower bound above −0.01. A separately labelled preservation result requires
hard-panel and all-panel lower bounds above −0.01; this is noninferiority within
those margins, not equivalence or improvement. All numerical rules must be fixed
in the future prospective freeze before full training.

The existing reference-defined 100-clip panel, including 25 feasible-hard clips,
would be reused; report that reuse rather than claiming a new held-out population.
All six training/provenance gates must pass before any of the 24 checkpoint
evaluation cells. The original four-arm study's endpoint definition and decision
are not amended.

Next code work is the full-budget entrypoint, complete checkpoint/provenance
verifier, scheduler and analysis integration, followed by GPU lifecycle validation
and fresh-seed audit. Resolve the current U/A/R/D confirmation before scheduling
this next full comparison. A new prospective contract must bind all production
sources and inputs; these development manifests cannot simply be relabelled as
confirmation-enabled.

Both arms share screen-derived candidate interval boundaries. The comparison
therefore isolates exclusion under that common representation, not the removal
of every use of feasibility information. A physics-blind partition or matched
reference-blind exclusion arm remains a later control.

## Current execution priority

At this stage's operational check, the original confirmation scheduler was still
waiting for shared-GPU capacity before its first training arm. The frozen-policy
pilot queue was waiting behind completed confirmation. Keep those sequences
unchanged. Their eventual policy result and valid noise measurement, followed by
the matched gate comparison, remain the path to learning which admissible
practice improves control.
