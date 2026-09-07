# Frozen-policy instrumentation and the matched gate candidate universe

Date: 2026-09-06. **Unsealed development addendum** to
`USEFUL_PRACTICE_NEXT_STEPS_2026-09-06.md`. Original confirmation sources,
scientific parameters, sealed files and manifests are unchanged.

## Confirmation advanced

All four seed-51 entrypoint smokes passed. The existing freezer reproduced every
prerequisite and configuration and created the prospective contract with SHA-256
`8f2192a9b937060a9ba6aa4fbd1b4a6aed8a7da183abf1c64fa9db557a5af013`.
The unchanged 60-job scheduler is active. At the 01:21 EDT snapshot it had created
the schedule and was waiting for shared-GPU capacity before the first training
job; no confirmation endpoint had opened. Freeze and schedule artifacts are in
`reports/relative_progress_2026-09-05/confirmation_freeze/`.

The four-arm comparison remains the immediate policy-result deliverable.
The separate diagnostic queue described below cannot use the GPU until the
confirmation scheduler reports completion. A failed/stopped confirmation stops
that diagnostic queue for review; it does not trigger a competing continuation.

## Implemented development collector

All new code and diagnostic outputs reside in
`/home/linjiw/climb-signal-quality-2026-09-06`.

`tools/frozen_progress_pilot.py` loads the prospectively selected R development
seed 11 checkpoint at iteration 2000, with its exact bank and unit table. It
uses the training environment configuration, including observation corruption,
physical randomization, stochastic policy actions and the original exact-start
sampler. Actor loading goes through PPO's strict actor loader; it deliberately
does not restore the saved runner environment clock into the new environment.
There are no PPO updates. The actor is in evaluation mode with gradients disabled;
actor and normalization tensors must remain exactly equal before and after.

Three separate seeds define environment randomness (26090601), exact-start
sampling (26090602), and action sampling (26090603). The actor samples through
the real stochastic forward path. A separate saved RNG stream prevents action
sampling from consuming the environment's Torch random stream. Tests verify
identical action sequences for repeated seeds, different samples for independent
seeds, preservation of the ambient RNG and unchanged actual checkpoint tensors.
These are CPU implementation checks, not independent simulator replications.

The active sampler starts with a fresh Beta prior and empty history. A diagnostic
shadow inherits the development sampler's discounted masses and rate history,
but clears pending and lifetime event counters and resets its clock to zero.
The shadow receives the same new completed outcomes and never controls exposure.
It intentionally retains historical contamination to measure initialization
dependence; its progress is not stationary-policy evidence.

The observer wraps the existing completed-event accumulator and 50-step clock
without changing their outputs. Each saved tick includes attempts, failures,
last-exposure steps, signed change, pre-cap probabilities, complete sampler state,
post-cap TV and shadow state. Replaying the completed counts through the actual
sampler must reproduce discounted masses, history, probabilities, trial totals
and TV at every tick. Missing ticks, altered event counts and changed
probabilities fail verification. Trials still active at the fixed collection
boundary remain ongoing; they are not invented successes or failures.

`tools/analyze_frozen_progress_pilot.py` produces per-unit and per-tick CSVs and
a coverage/initialization summary. It checks saved input hashes and reruns event
replay. The output explicitly refuses to establish stationarity or fit calibrated
noise thresholds from a short instrumentation run.

## Measured simulator smoke

Task: `Climb-Tracking-Flat-Unitree-G1-FrozenProgress-Instrumentation`.
Development checkpoint: R11, iteration 2000. Seeds: environment 26090601,
sampler 26090602, action 26090603. CPU, 8 environments, 12 estimator ticks,
600 environment steps, **4,800 transitions**.

The actual simulator smoke passed: **98 completed trials**, 11 failures,
zero invalid starts/reference frames and zero censored resets. All 12 active
sampler and shadow ticks replay exactly. Actor and observation-normalizer
tensor hashes are unchanged. Eight ongoing trials remain at the stopping boundary.
Measured rollout time was **16.8273 seconds**; total construction/collection/check
time was **22.1210 seconds**. These CPU smoke times do not estimate GPU pilot or
confirmation runtime.

Only **90 of 1,184 units** received a completed attempt, covering **18.4743%** of
the legal-start prior mass. At tick 12, the inherited share of the shadow's
discounted attempt mass is **0.9980838** when averaged with prior weights;
the cold-versus-shadow absolute success-rate difference averages **0.4017312**
with those same weights. These describe startup under a very small exposure
budget. They establish neither noise magnitude nor the burn-in required by the
512-environment pilot.

Artifacts in the separate worktree:

- `reports/frozen_progress_pilot_2026-09-06/cpu_smoke_launch.json`: exact argv
  and environment overrides, including hidden CUDA and two CPU threads.
- `cpu_smoke.log`, `cpu_smoke/{design.json,result.json,ticks.pt}` under that root.
- `cpu_smoke_analysis/{summary.json,units.csv,ticks.csv}` under that root.

The new 17-test suite passes: actual checkpoint stochasticity/freeze, sampler
observer/replay, gate support boundary cases, diagnostic queue rejection, and
the existing operational handoff checks. This is scoped implementation evidence;
the GPU pilot has not run.

## Queued next diagnostic step

A source-bound queue now waits behind completed confirmation. Its first job is
an 8-environment, 12-tick GPU smoke using the same development inputs. Only an
instrumentation pass allows the fixed **512-environment, 100-tick pilot**:
5,000 environment steps, **2,560,000 transitions**. The analyzer runs after each
successful job. All are development-bank observations; no confirmation policy
or held-out condition is a diagnostic input.

`reports/frozen_progress_pilot_2026-09-06/queue_design.json` binds 520 source,
runtime, asset and evidence paths. Its SHA-256 is
`a70dfef2e6bb2553f56cf972e8107f5b35fd1b59d81ae7cbca4585132828676a`.
`queue_launch.json` records PID 1809891 and exact argv. The queue has a 24-hour
confirmation wait and two-hour per-job GPU wait, preserves confirmation's
14,000-MiB-free/60%-utilization availability rule, and makes one attempt per job.
It stops on changed bindings, failed prerequisites or execution errors.

Do not edit bound development sources while this queue is pending. If a change
becomes necessary, preserve this attempted design and record a separate revision.
The next decision after the pilot is to specify settling tolerance, maximum
burn-in, adequate-exposure strata and independent scored-block lengths for the
four frozen-policy cells. This pilot is not one of those scored repetitions.

## H1 support audit: correct the candidate-universe construction

The existing builder iterates over `feasible_segments_frames` before creating
`source_units`. Thus `source_units` already excludes dynamically rejected frame
intervals; its difference from `admissible_units` is the short-horizon filter.
Simply restoring dropped `source_units` would not implement gate removal.

`tools/audit_gate_candidate_support.py` instead partitions the full legal-start
axis `[0, frames−50)` for each candidate clip. An accepted interval corresponding
to feasible frame run `[a,b)` is `[a,b−50)`, with strict `start+50 < b` matching
the current evaluator/reference indexing contract. Its complement includes
starts whose windows cross rejected frames, even when the starting frame itself
is feasible. The audit checks all 800 sidecar hashes, exhaustive disjoint
feasible/excluded frame partitions, and exact equality with existing feasible
start intervals and unit identities. Exhaustive small-timeline tests cover the
H versus H+1 boundary and windows crossing excluded intervals.

**Measured reference-only support audit:**

| Quantity | Count |
| --- | ---: |
| Candidate clips | 800 |
| All legal non-wrapping 50-step starts | 417,072 |
| Existing gate-admitted starts | 368,951 |
| Rejected starts restored by removing admission | 48,121 |
| Preserved feasible units | 1,184 |
| Additional rejected-start intervals | 465 |
| Total candidate intervals | 1,649 |
| Clips containing rejected starts | 239 |
| Clips without any admitted starts | 3 |

Rejected start count is **11.5378%** of the uncapped legal-start-uniform prior.
It is neither post-cap sampling mass nor wasted PPO transitions. Dynamic
screening settings are inherited from the source-bound sidecars; this audit
does not validate those physical assumptions or demonstrate practical gate value.

Artifacts: separate worktree
`reports/gate_candidate_audit_2026-09-06/{result.json,candidate_start_intervals.json,clips.json}`.
The candidate schema is deliberately not a runtime training manifest and has
`training_enabled=false`. No gate-off policy has trained.

The next H1 implementation must bind this shared candidate partition, preserve
canonical feasible-unit identities, and implement gate-on/off masks with D held
fixed. Report both prior renormalization and the actual capped distributions.
Both arms would share screen-derived interval boundaries: the ablation isolates
the admission mask conditional on that representation, not the removal of all
feasibility information. A physics-blind partition/exclusion comparison is a
different, later control. Exact starts and reference horizons must pass matched
smokes before any H1 prospective freeze or fresh-seed training.

## Scientific priority remains unchanged

Finish U/A/R/D and report its declared seed-level decision. Use the pilot to
design valid noise measurement; do not infer forgetting from absolute change.
Make the matched gate comparison the next full training study. Practice-value
branches remain conditional; reliability calibration, positive-only progress,
stronger mixtures, repair expansion and simulator migration do not enter the
current confirmation.
