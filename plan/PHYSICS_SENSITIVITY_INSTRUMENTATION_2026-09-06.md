# Physical-sensitivity operators: CPU instrumentation result

Date: 2026-09-06. **Unsealed development addendum** to
`ICRA_EVIDENCE_ROADMAP_2026-09-06.md`. The physical-sensitivity draft is called
S1 here; it is separate from historical S1 conformance experiments. No historical
seal, confirmation source, profile or evaluation condition changes.

## Completed stage and scientific scope

All eight proposed intervention conditions now have implemented operators and
passing CPU actuator-fixture measurements on the pinned G1 model. An independent
saved-trace verifier reproduces their measurements. A repeated baseline matches
exactly. Fourteen focused tests pass, including eight deliberate corruptions of
delay, force, hip limits, friction, initial state, reset history, repeat trajectory
and condition completeness.

This answers whether the intended interventions take effect in the fixture. It
does **not** answer whether a trained policy tolerates them, whether R improves
control, or whether the model matches physical hardware. No motion reference,
trained checkpoint, held-out endpoint, PPO update or hardware action was used.
The original confirmation remains queued behind shared-GPU capacity at this
stage's final snapshot; the noise pilot and efficiency postprocessor remain alive.

Code and measured artifacts are isolated in
`/home/linjiw/climb-icra-evidence-2026-09-06`. Original runtime inventory verification
still passes for all 376 files. Both checked seals pass. Exact command records,
source/artifact hashes and live snapshots are in the original repository's
`reports/physics_sensitivity_stage_2026-09-06/`.

## Operators and specificity

`tools/physics_sensitivity.py` implements the eight conditions: unchanged;
fixed command delays 5/10/20 ms; knee-only clamps 120/90 N·m; and fixed foot
sliding-friction coefficients 0.3/1.2. Delay steps are 1/2/4 at the pinned 5 ms
physics timestep, not control steps of 20 ms.

The knee operator edits the two named MjSpec actuator limits **after entity
construction and before compilation**. This improves on the draft's suggested
configuration-group split: it preserves actuator ordering and leaves the hip-roll
limits untouched despite their shared upstream group. Both knee names and their
joint targets are checked before mutation. Compiled actuator order, force limits,
gains, biases, gears, armatures, joint ranges and body masses are compared across
conditions; only the intended knee bounds differ.

Friction is overridden in the expanded per-world model tensor **after common
fixture startup draws**. Exactly 14 foot collision geometries are selected;
non-foot geometry and torsional/rolling coefficients are checked unchanged. The
override consumes no global RNG draws. This is not yet a check of the original
evaluator's COM/encoder/friction startup pipeline or its random stream pairing.

## Measured CPU smoke

Task: `Climb-G1-Physics-Sensitivity-Actuator-Fixture`; seed **26090641**;
device **cpu**; two fixture worlds; 12 physics steps per condition; eight conditions
plus one unchanged repeat: **216 integrated world physics steps**. Additional
clamp and reset probes call control/forward operations without integration.
The reported 1.65554 s covers the fixture exercises, excluding original contract
verification and imports; it is not a policy-evaluation runtime estimate.

| Measurement | Result | Interpretation limit |
| --- | --- | --- |
| Command target trace | Exact zero/one/two/four-step lag at every recorded physics substep | Command path only; no motor or observation-latency identification |
| Saturation forces | All 29 actuators reach both signed configured limits under forced large targets; knee variants reach ±120/±90 N·m; hip roll stays ±139 N·m | Deliberate nonintegrated clamp probe, not policy torque use or a safe robot command |
| Foot friction | Exact requested tensor values within floating-point representation; all unrelated coefficients preserved | Not measured contact response or hardware friction |
| Fixture initial state | Identical qpos, qvel, pre-intervention friction and dedicated RNG-state tensors across all eight conditions | Standalone fixture; actual evaluator initialization remains unvalidated |
| Reset | Reset world's first target backfills its delay buffer; other world's history remains intact | Empty-history startup does not represent an already warmed physical command queue |
| Repeat | Unchanged baseline controls, positions, forces, friction and reset controls exactly repeat | Deterministic reproduction, not an independent statistical replicate |

Raw traces: worktree `reports/physics_sensitivity_2026-09-06/cpu_smoke/traces.pt`.
Online receipt: `cpu_smoke/result.json`; independent receipt:
`trace_verification.json`. Exportable figure: `intervention_checks.{png,pdf}`.
The figure was visually inspected and explicitly labels its instrumentation scope.

## Next implementation gate

`s1_preparation_draft.json` binds this code, the original panel/conditions/strata,
and the proposed four-arm × three-seed × eight-condition final-checkpoint grid.
It has `full_evaluation_enabled=false`; it is neither a scientific freeze nor an
executable campaign. Its 96 cells / 268,800 condition instances are planned counts.

Next, integrate the operators into a separate paired policy evaluator. First
require zero-intervention agreement with the original evaluator on development
inputs: same checkpoint/normalizers, reference/start placement, startup random
draws, first observation/action and matched initial state. Then verify every
intervention's realized traces throughout full policy rollouts, preserving failed
conditions and survivor denominators. Bind the reset-buffer rule prospectively.
Run the development GPU lifecycle only when the existing queues have priority.

Only after those gates and a separate prospective source/configuration/input
freeze may the fixed S1 policy grid execute. Do not use held-out policy scores to
tune stress levels, select motions or change the original primary test. Practical
gate benefit remains the H1 comparison's question, and stationary-policy noise
remains the already queued pilot's question. These fixture results replace neither.
