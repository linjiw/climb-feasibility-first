# Relative-progress confirmation readiness

Date: 2026-09-05. **Exploratory development; confirmation pending.**
This addendum preserves all sealed files and the source-bound R1/R2 and D
profiles. It extends `RELATIVE_SIGNAL_DIAGNOSIS_2026-09-05.md`.

## Direction and scientific question

Keep the relative-progress candidate as the next experiment. R1 supports its
ability to sustain nonuniform allocation as progress amplitude decreases. The
new history diagnostic leaves the value of those rankings unresolved. The next
decisive question is whether that reallocation improves held-out tracking over
uniform allocation, and whether it adds value over conditional failure ranking.

The intended contributions remain bounded:

1. A scale-relative progress allocator on the existing exact admissible support,
   with unchanged 50-step training horizons and probability caps.
2. A reproducible manipulation check over 41 checkpoint-linked snapshots per
   training run, including independent replication before policy comparison.
3. A four-arm, three-training-seed simulation comparison with 100 held-out clips
   and 2,800 paired evaluation conditions, conditional on the development gates.

Item 1 has implementation evidence and one complete exploratory manipulation
pass. Independent replication and item 3 remain pending. This is not a novelty
claim or a physical-robot result. Training uses the existing outcome history;
no additional deployment-time sensor or policy input is introduced.

## Execution correction and restart

The earlier replacement continuation stopped at 17:36 EDT. Its underlying
seed-12 smoke log contains only `GAVE_UP polls=1`; no `LAUNCH` sentinel or smoke/
long training directory exists. The outer error mentioned a missing smoke
result because it tried to verify a study that never launched. The downstream
smoke and D-calibration workers then stopped on their prerequisite rules.
This is an execution failure, not a failed manipulation experiment.

The original design, logs and terminal artifacts remain in
`reports/relative_progress_2026-09-05/continuation_recovery/`, `policy_smokes/`,
and `failure_calibration/`. At 18:29:57 EDT, the unchanged supervisors were
restarted with exclusive fresh output directories:

| Stage | New artifact directory | Supervisor PID at launch |
| --- | --- | --- |
| R1 replay, then R2 smoke/full training | `continuation_gate_retry/` | 1091691 |
| U/A/R/D smokes after replicated manipulation | `policy_smokes_gate_retry/` | 1091692 |
| Fixed D seeds 31 and 32 after smokes | `failure_calibration_gate_retry/` | 1091693 |

Each corresponding `*_launch.json` records the exact supervisor argv, time,
reason and PID; `*_launcher.log` and each `design.json` preserve execution and
source bindings. No scientific parameter, seed, threshold or retry-after-OOM
rule changed. The new execution is justified by proof that the previous
seed-12 attempt launched no training.

**Measured lifecycle result:** seed 12 smoke, task
`Climb-Tracking-Flat-Unitree-G1-RelativeALP-Probe`, 8 environments, 20 iterations,
started 18:30:10 and completed 18:30:27 EDT, rc=0. Strict checker: `smoke_pass`,
192 completed trials, zero invalid/censored events. Its full 512-environment,
4,000-iteration run launched at 18:30:27 EDT and is running. No full-run gate
decision is inferred from this smoke or intermediate telemetry.

Exact trainer argv are in
`continuation_gate_retry/study_s12/{smoke,long}_command.json`; the environment,
seed and source identities are in that study's `design.json`. The log records
the unchanged 14,000-MiB / 60%-utilization GPU gate. Existing launcher polling
can still miss a short availability window; a future operational fix would need
new versioned wrappers while preserving these source-bound studies.

## Pose and work analysis specification

`tools/relative_policy_secondaries.py` implements the planned descriptive
secondary reducer, used by the developing campaign loader only after complete
preflight. These definitions must enter the eventual confirmation freeze.

- Compare R with U, A and D separately for each training seed at iteration 3999.
- Pair pose measurements only on identical conditions where **both** arms have
  `success=1`. Reaching the last timestep with a failure flag does not count.
  Use common-reference root-relative position error in metres and anchor
  orientation error in radians.
- Retain every panel clip and its total condition count, each arm's success
  count and the common-success count. Empty common-success cells have null pose
  estimates. Covered-clip pose averages name their coverage and are not
  interpreted as all-panel effects. Different pairs/seeds can select different
  subsets; these are descriptive outcomes, not causal effects of allocation.
- Work includes **every** evaluation condition, including early failures. Record
  total absolute mechanical work per actuator, observed exposure seconds,
  per-condition means, and work divided by observed exposure. The scalar
  all-panel work contrast averages per-clip means, retaining the fixed panel.
- Lower work may mean earlier failure. Report it with exposure and primary
  survival; neither the work integral nor its exposure ratio is battery energy
  or a demonstrated efficiency gain. No value is imputed for zero exposure.
- Reject missing/duplicate conditions, inconsistent success flags, negative or
  nonfinite work, and nonzero work without observed exposure.

These summaries do not change the final R-U TrackingScore primary endpoint,
SESOI +0.02, all-panel margin -0.01, or the seed-level inference. Secondary
quality and work do not select checkpoints or override the primary decision.

## Validation scope and next promotion

The new synthetic campaign fixture constructs both relative prerequisites,
both D calibrations, all 12 confirmation training histories (41 snapshots each),
and all 48 evaluation cells (2,800 conditions each). It uses the real prerequisite,
sampler, provenance and aggregation functions; its constructed histories and
dummy checkpoint bytes are explicitly synthetic and prove no learning result.
It also tests whether a rehashed mismatch in the last evaluation cell stops
analysis before any endpoint aggregation.

Confirmation remains disabled in the actual bound development profiles.
Remaining work before confirmation is a complete source/dependency and input
audit, the campaign-bound confirmation trainer and scheduler, training-cost
accounting, completed R2/smoke/D gates, and the prospective freeze. Preserve the
fixed four arms and seeds 21/22/23. A failed scientific gate stops promotion;
there is no outcome-driven candidate search or extra-seed collection.

Integrated verification completed: **101 tests passed in 116.90 s**, including
the complete campaign fixture and failure-denominator cases. Changed Python
files compile, whitespace checks pass, and all 41 sealed Phase-G artifacts are
unchanged. Exact commands, test environment and source hashes:
`reports/relative_progress_2026-09-05/campaign_readiness_verification.json`.

The initial static source inventory finds 24 local Python files reachable from
the analyzer, development trainer and evaluator through explicit imports:
`reports/relative_progress_2026-09-05/confirmation_source_inventory.json`.
It records file hashes and dependency edges, but does not certify external
packages, plugin discovery, subprocess programs or indirect data reads. Those
remain part of the complete source/input audit before the prospective freeze.
