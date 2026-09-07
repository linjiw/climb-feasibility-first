# Natural policy failure and mixed-horizon lifecycle validation

2026-09-06. **Unsealed development addendum.** No confirmation endpoint, threshold,
sealed source or runtime inventory changes. New code and raw data live in
`/home/linjiw/climb-icra-evidence-2026-09-06`.

## Fixed batch, selected without policy outcomes

Selection inspected all 800 training reference files for frame count and joint
velocity RMS. The batch is the shortest reference, the two largest joint-speed
RMS references and the first two fixed training-list entries. No policy outcome
was used for selection. The resulting five clips are disjoint from the held-out
panel:

1. `CMU_105_105_06_poses_120_jpos` — 57 frames, shortest training reference.
2. `BMLmovi_Subject_24_F_MoSh_Subject_24_F_2_poses_120_jpos` — 144 frames.
3. `CMU_108_108_20_poses_120_jpos` — 116 frames.
4. `KIT_1229_flexion_with_help_02_poses_100_jpos` — 430 frames.
5. `KIT_1229_in_out_rotation_with_help_03_poses_100_jpos` — 307 frames.

The existing development R11/2000 checkpoint is used. The original condition
builder generates seven unique worlds at phases 0/0.5 with horizons
[56,143,115,150,150,150,150] control steps. Requested window is 3 seconds;
environment seed 26090661, joint-noise seed 26090662, joint noise 0.05, CPU,
task `Climb-Tracking-Flat-Unitree-G1`. Short references retain their actual shorter
horizons; no clip was cropped or synthesized. The injected-failure schedule is
empty; its recorder term remains false on every step.

Reference inventory, selected clip list, condition manifest and pre-execution
design are in `reports/natural_lifecycle_2026-09-06/`. Design SHA-256:
`e7781d27d87ddd7c48542a2c0feb4596a1bdb03ed1a0bf0e2e373dc2b2bc19eb`.
All nine conditions and all outcomes are retained.

## Instrumentation gap found and resolved

The environment-level recorder was insufficient for longer trajectories: when
a retired reference wraps around, the motion command can teleport/reset the
robot directly. This clears its command-delay history without an environment
`reset()` call. The first audit therefore fails delay replay for the three delay
conditions. It is preserved as `incomplete_audit.json` together with all raw data.
This is a missing-recording diagnosis, not a demonstrated new simulator defect.

`tools/eval_natural_entity_lifecycle.py` adds recording around the actual entity
reset method. It labels environment-reset and motion-resample calls and records
their per-world physics boundaries and before/after state. It reuses the prior
isolated partial-reset correction; no simulation behavior changes were added.
A separate pre-execution design binds the extension:
`ed6344f18b82ed16eac8a3f434ebfe0a55f9e73bc556aa1eb7c1bb970c594b14`.
The complete rerun is in `reports/natural_entity_lifecycle_2026-09-06/`.
Every CSV is byte-identical to its previous counterpart.

## Measured CPU coverage

| Condition | Executed control steps | Natural failure rows | Early successful rows | Environment resets |
| --- | --- | --- | --- | --- |
| Original | 150 | 2 | 1 | 2 |
| Unchanged adapter | 150 | 2 | 1 | 2 |
| Delay 5 ms | 150 | 2 | 1 | 4 |
| Delay 10 ms | 150 | 2 | 1 | 3 |
| Delay 20 ms | 131 | 6 | 1 | 10 |
| Knee 120 N·m | 150 | 2 | 1 | 2 |
| Knee 90 N·m | 150 | 2 | 1 | 2 |
| Foot friction 0.3 | 150 | 2 | 1 | 2 |
| Foot friction 1.2 | 150 | 1 | 2 | 2 |

Total: **63 episode rows**, **21 natural failure rows**, **10 early successful
rows**, **29 environment reset calls**, **101 entity-reset calls**, including
**37 motion-resample calls**. An environment reset can call entity reset more
than once; these counts are distinct layers and must not be added as episodes.
Each condition reuses the same selected batch and development policy, so rows
and reset events are not independent efficacy replications.

In the original run, the shortest clip finishes successfully at step 56 (1.12 s).
The two high-speed clips fail the `ee_body_pos` termination check at steps 104
and 32. The four longer worlds survive to step 150. In the 20 ms delay run, all
worlds retire by step 131 and the vector loop stops then. These are observed
development trajectories, not a general robustness or sample-efficiency estimate.

The independent analyzer verifies:

- Original/unchanged CSV parity, exact prior CSV reproduction and source/receipt
  hashes; selected references stay outside the confirmation panel.
- Per-world survival, natural failure causes, early-success retirement, final
  success flags and native mean/terminal metrics from active-only samples.
- Environment resets match simulator done masks; both environment and command
  resets preserve unselected recorded state and clear selected delayed history.
- Actual control values obey the requested lag with history bounded by every
  world-specific entity reset, including resampling after clip wraparound.
- Paired physical initialization, named force/friction interventions, force
  bounds and unchanged policy/normalization tensors. Inference-call counts match
  actual loop length, including the 131-step early completion.

Eleven tests pass: complete measured coverage, variable inference length and nine
corruptions covering missing resampling resets, bad reset boundaries, altered
histories, changed retired scores, false success, injected failures, missing final
steps and cross-reset command errors. Exact tests, compilation, source hashes and
seal checks are recorded in the original repository's
`reports/natural_lifecycle_2026-09-06/verification.json`. Both seals and all 376
original runtime hashes match.

The full artifact verifier is `tools/analyze_natural_entity_lifecycle.py`. Exact
run commands, seeds and task IDs are in each cell's `*_launch.json`; raw logs,
CSVs, metadata, policy/physical/lifecycle tensors and aggregate `verification.json`
are retained beside the design. To replay, invoke the pinned Python with that
analyzer, `--run` pointing to the complete run and `--out` a fresh JSON filename.

## Next gate and live confirmation status

The planned CPU lifecycle cases are now covered. Next: a separately bound GPU
development adapter and same-input original/unchanged parity check, followed by
all physical interventions on GPU. GPU validation must check realized lag and
reset behavior as well as outputs; CPU conformance alone does not establish GPU
graph correctness. This work retains confirmation and the queued frozen-policy
progress pilot's GPU priority. Full physical-sensitivity evaluation remains disabled
until the general adapter is verified and its own prospective contract is frozen.

At 12:37:16 EDT, confirmation remains U21/A21 complete (2/12), no held-out cell
evaluated (0/48), with the scheduler and both follow-on workers alive. R21 awaits
capacity; the GPU has 4,319 MiB free and 91% utilization against the existing
14,000 MiB / at-most-60% launch gate. Snapshot:
`reports/natural_lifecycle_2026-09-06/queue_snapshot.json` in the original repo.
