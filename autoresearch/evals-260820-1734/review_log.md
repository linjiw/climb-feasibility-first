# V2 review session and paired-checkpoint iteration

Started: 2026-08-20 17:34 EDT. Classification: exploratory apparatus review;
no sealed result, implementation, registration, or manifest may be changed.

## Inputs

- Frozen outcomes: `reports/FGAS_result.json`, `reports/N7_result.json`.
- Post-outcome audit: `reports/N7_posthoc_audit.json`.
- V2 core: `climb/segment_curriculum.py` and focused tests.
- V2 evaluator: `tools/eval_paired_v2.py` and `reports/eval_v2_smoke/`.
- Design contract: `plan/SEGMENT_NATIVE_FOLLOWUP_2026-08-20.md`.

## Review agenda

1. Core: conditional-rate state, hard support, transition-safe horizons,
   segment-boundary lifecycle, and exact checkpoint/resume.
2. Evaluation: condition pairing, initial-state/DR identity, terminal reads,
   contact and motion-quality semantics, vector retirement, and provenance.
3. Strategy: whether a bounded existing-checkpoint K/R pilot is the next
   highest-information action before implementing a new training runtime.

## Baseline gates

- Ruff and ty clean; 16 focused tests pass.
- Paired synthetic, repeated-success, and forced-failure GPU smokes pass.
- Repeated cells have identical startup-randomization and initial-state hashes;
  success and survival match. Continuous GPU metrics differ only slightly.
- FGAS and N7 manifests validate; no CLIMB process is active.

## Iteration rule

Keep a change only if it resolves a concrete review finding and preserves all
baseline gates. The K/R pilot is wiring/exploratory evidence only: it cannot
replace the frozen N7 decision or establish training-seed uncertainty.

## Independent review — round 2

All three reviewers recommend a bounded K/R evaluation before new training,
but only after the following apparatus gates:

- **Core P0:** filtering short segments currently loses their canonical source
  IDs; rate/outcome credit could shift to the wrong unit.
- **Core P0:** the event EMA is batch-partition dependent (`{failure, success}`
  can produce 0.48, 0.50, or 0.52 from the same initial state).
- **Core P0:** a 0.1 deployment floor still permits top-1 probability 0.901 and
  entropy ESS 2.18 for one persistent hard unit among 100. Unit and clip caps,
  or at minimum frozen concentration gates, are required.
- **Lifecycle:** the H+1 frame rule depends on mjlab's current `dt=0` reset
  increment. The runtime smoke must trace placed, first-observation, reward,
  truncation, and post-reset frame IDs exactly.
- **Evaluation P0:** quality aggregates use each policy's own survival prefix.
  Immediate analyses must restrict quality to jointly successful condition IDs;
  a fuller evaluator must expose common-prefix or per-step statistics.
- **Evaluation high:** add a multi-world staggered-retirement smoke, stronger
  source/bank/config provenance, precise contact/work/action labels, and a
  strict condition-ID paired analyzer.
- **Scientific P0:** active-target errors cannot distinguish better motion from
  an easier repaired target. Add common raw-reference fidelity and reference
  distortion before interpreting repair quality.

Decision: keep the pilot exploratory and policy-independent, but pause its four
GPU cells until the P0 apparatus fixes and a multi-world smoke pass.

## Apparatus changes kept

- Segment units now retain immutable canonical IDs when short intervals are
  filtered. Starts use a dedicated replayable Torch generator.
- Replaced event-order EMA updates with fixed-clock discounted failure/attempt
  sufficient statistics. A clock aggregates all trial outcomes before one
  update, making within-clock ordering irrelevant.
- Added concentration diagnostics and deterministic unit/clip probability caps.
  Caps preserve the exact exploration floor, keep hard-ineligible units at zero,
  and fail before training when their total capacity is infeasible.
- The evaluator now hashes selected active/common NPZs and relevant source files,
  freezes environment and joint-noise seeds, labels work/action/contact channels
  precisely, and evaluates robot motion against a common raw reference.
- The analyzer rejects any condition, seed, DR, initial-state, software, source,
  or reference mismatch. Survival uses every full-window condition; quality uses
  only four-way or pairwise jointly successful conditions.
- A three-world failure/short/success smoke exercised staggered retirement and
  reproduced startup and initial-state hashes plus all discrete outcomes. Raw
  active-to-common distortion was exactly zero. During the first 824-world pilot
  attempt, the common-reference guard correctly exposed retired worlds advancing
  past their clips. The guard now validates active trials only and clamps unused
  retired-world lookups; the rerun completed.

Verification after the pilot apparatus changes: Ruff pass, ty pass, and
evaluator/analyzer synthetics pass. No sealed file was modified.

## Exploratory paired K/R pilot

Protocol: one training seed per policy, common raw-reference bank, environment
seed 20260822, joint-noise seed 20260823, 3 s windows, seven horizon-safe phases,
four replicates, and `nconmax=70`. The 32-motion repair panel produced 824 worlds
per cell (812 full-window); all four cells completed. The disjoint 12-motion
clean/raw control produced 336 worlds per policy, all full-window. Exact inputs,
condition manifests, CSVs, metadata, and analysis are under
`reports/eval_v2_pilot/`.

Motion-equal repair-panel results on the 29 full-window motions:

- R/repaired minus K/raw success: **+0.1355**, motion-bootstrap 95% interval
  **[+0.0505,+0.2365]**; survival: **+0.2626 s**
  **[+0.1208,+0.4238]**.
- R/raw minus K/raw success: **+0.0234** **[-0.0123,+0.0825]**; survival:
  **+0.0547 s** **[-0.0161,+0.1496]**. Policy-only transfer is unresolved.
- K/repaired minus K/raw success: **+0.0961** **[+0.0320,+0.1773]**. The large
  deployment contrast is primarily a reference effect, not controller evidence.
- Deployment success by stratum: over-budget **+0.2630**, certified **+0.0844**,
  residual **+0.0153**. Over-budget repairs are the clear routing target.
- Clean/raw control R minus K: success **+0.0208** **[0,+0.0625]**; survival
  **+0.0149 s** **[-0.0454,+0.0900]**. No broad clean-control regression appears.

On the 509 four-way jointly successful conditions, R/repaired versus K/raw
slightly improves common-raw root-relative MPKPE (−1.32 mm), body orientation
(−0.00483 rad), joint position (−0.00719 rad), acceleration (−0.0195 m/s²), and
jerk (−2.19 m/s³), but worsens anchor position (+15.4 mm), mechanical work
(+0.644 J/actuator), and contacting ankle-link speed (+0.0126 m/s). These are
descriptive only: one seed, a mechanism-selected panel, no frozen quality
margins, and no reference-contact timing metric.

Decision: **keep** the paired apparatus and use repair for over-budget routing
research; **do not** interpret this as validation of repaired-policy training or
replace sealed N7. Full segment-native training remains blocked on the exact
segment-boundary truncation/time-limit bootstrap, command integration, realized
invalid-frame telemetry, sampler-equivalent resume boundary, unit-table
provenance, and simulator frame trace.

## Post-pilot next gate

The core reviewer re-audited probability caps and found three numerical/device
edge cases: unit-count-scaled tolerance could hide a true floor conflict;
float32 normalization drift could falsely reject a feasible table; and a
float32 grouped post-check could falsely reject a no-op clip cap. All three
reproductions are now tests. Projection runs deterministically on CPU float64,
renormalizes after promotion, and checks unit caps, clip caps, exploration floor,
hard support, and total mass after allocation. The reviewer then ran 4,000
random feasible/infeasible certificates with no remaining P0/high finding. A
10,000-unit/1,000-clip projection costs 0.055 s and must be cached on the fixed
curriculum clock, never recomputed per environment step.

The exact-support path advanced without touching sealed `climb/commands.py`:

- `tools/screen_segments.py` now emits integer segment/window frames and
  continuous unsupported-force summaries. Its symmetric guard remains the
  published default; a backward-only mode supports SONIC forward lookahead.
- `tools/build_segment_unit_table.py` verifies source hashes, NPZ/sidecar
  timelines, exact feasible/severe partitioning, stable pre-filter unit IDs,
  horizon safety, and deployment mass. Missing sidecars fail closed.
- The outcome-independent 10-motion smoke panel yields 42 admissible units and
  4,679 legal 50-step starts (`reports/segment_v2_smoke/unit_table.json`).
- `climb/segment_runtime.py` provides the dedicated CPU RNG, cached uniform or
  adaptive distribution, fixed-clock attempt/failure attribution, concentration
  telemetry, and sampler state. An all-env-boundary resume reproduces the next
  100 unit/start draws exactly; this is sampler-equivalent resume, not full
  simulator continuation.

Final focused verification: **37 tests pass**, Ruff and ty pass. Training was
not launched. The immediate next implementation is a separate, unsealed command
term plus `time_out=True` segment-boundary termination. Its simulator trace must
prove first observation `s+1`, reward references `s+1…s+H`, timeout before
`segment_stop`, PPO timeout bootstrap, and no continuing teleport.
