# Segment-native follow-up — independent review and v2 contract

**Status:** isolated runtime and evaluator implemented; one unsealed two-arm GPU
wiring pilot completed. It is not a registration and does not authorize a full
training launch. Three independent reviews covered core sampling, evaluation
fairness, and research strategy after FGAS and N7 completed.

## Load-bearing findings

1. The frozen sampler adapts to raw failure arrivals, not conditional failure
   probability. Expected score scales with current sampling share and trial
   duration, creating winner-take-all feedback. Attempts/successes never enter
   `clip_failed_ema`.
2. A clip boundary resamples and teleports the robot without a terminal PPO
   transition. About 84.6% of flat proposals reach a boundary within the 10 s
   episode; changing starts can therefore change discontinuity timing by arm.
3. Eligibility constrains only the start. Rollouts can traverse rejected frames,
   while `sampling_ineligible_mass` reports proposal mass rather than realized
   invalid observations or optimizer steps.
4. `bin_score` is occupancy of a binary kept-frame mask, not the directive's
   continuous unsupported-impulse severity. Repeating it across a partial bin
   gives known-invalid frames positive probability.
5. Sidecars fail open on missing/all-zero support, sampler state is not restored
   on checkpoint resume, and categorical top-1 IDs are averaged into invalid
   pseudo-indices.

The completed soft arm is arithmetically faithful to its preregistration, but it
is not a clean test of the segment-native method described in the directive.

## V2 algorithm contract

The adaptive unit is an exact `(clip, feasible segment/start cell)`, never a
whole clip. For each unit, record attempts and failures and estimate conditional
difficulty, updating only visited units. Let `d_u` be the frozen deployment prior,
`m_u` hard admissibility, and `r_u` the conditional failure estimate:

`base_u ∝ d_u m_u`; `focus_u ∝ d_u m_u ψ(r_u)`;
`p_u = ρ base_u + (1−ρ) focus_u`.

Use `ρ=0.1` in both control and treatment. Hard admissibility defines support and
must fail closed; continuous physical severity/confidence may rank only starts
already known to be safe. A fixed trial horizon must fit wholly inside its
segment. Segment completion emits an explicit truncation/reset, never a continuing
teleport. Predeclared per-unit and per-clip caps bound persistent-hard-unit
concentration while preserving the exploration floor. `climb/segment_curriculum.py`
implements and tests these CPU invariants without modifying the sealed FGAS files.

Required telemetry: exact probability vector snapshots; attempts/failures per
unit; proposed rejected-start mass; realized rejected-frame and optimizer-step
fractions; invalid-attributed failures; segment truncations; clip/segment ESS,
entropy, maximum mass; complete RNG and sampler state for resume.

The isolated v2 runtime now builds a hash-frozen exact unit table and owns a
dedicated CPU generator plus fixed-clock conditional sufficient statistics.
Unit/clip cap projection is CPU-float64 and passed 4,000 randomized certificates;
the 10k-unit/1k-clip latency is 0.055 s, so distributions must be cached. The
10-motion mechanism panel contains 42 admissible units and 4,679 legal 50-step
starts. Sampler-equivalent boundary resume passes; command/termination and full
simulator state restoration are not implemented yet.

The 2026-08-20 pilot additionally exposed curriculum total variation from the
capped deployment control. This manipulation check is required because entropy
and top-1 caps can pass even when adaptive and control distributions are nearly
identical.

## Fair evaluation contract

Freeze a per-world condition manifest `(motion, start_frame, replicate, initial
noise, dynamics randomization)` and replay it byte-identically across policies and
references in one software environment. Set the environment seed before creation,
disable auto-reset while terminal metrics are captured, recompute observations
after every reference assignment, reject invalid offsets instead of clipping, and
write per-episode rows with code/config/list hashes.

Use unique phase- or segment-stratified starts across the full clip. Primary
outcomes are fixed-window survival/RMST and motion-equal paired deltas. Motion
quality includes root-relative MPKPE, anchor/body orientation error, joint and
velocity error, acceleration/jerk, contact timing and foot slip, actuator
saturation/work, joint-limit exposure, and reference distortion. Report quality
on paired common-survivor frames plus survival so early failure cannot improve an
error average. Use at least three training seeds and a seed×motion hierarchical
bootstrap; require the noninferiority CI, not only its point estimate, to stay
above the regression margin.

`tools/eval_paired_v2.py` implements the general contract as a separate, unsealed
harness. Its condition manifest freezes exact start frames and both environment
and joint-noise seeds; it disables auto-reset until terminal reads are complete,
recomputes the post-assignment observation, rejects wrap-unsafe starts, records
per-episode causes plus tracking, effort, work, joint-limit, foot-contact/slip,
penetration, acceleration, and jerk channels, and pins contact capacity to 70
per world. Repeated one-world and staggered three-world GPU smokes reproduced
startup-randomization and initial-state hashes plus discrete outcomes; continuous
differences stayed below 0.1% relative in the worst short-world channel. A known
difficult clip terminated at 0.30 s with `anchor_pos` and nonzero terminal errors,
confirming that the failure row is not reset-state contaminated. The strict
analyzer restricts quality to jointly successful full-window conditions. True
common-prefix aggregation and robot-versus-reference contact timing remain open.

For segment-v2, `tools/eval_segment_policy.py` now replays exact unit/start rows,
pairs environment/startup-randomization hashes, disables auto-reset for terminal
reads, and stores per-step trajectories. `tools/analyze_segment_pilot.py` compares
quality only on paired common-survivor frames. Reference-contact timing remains
open.

## Exploratory existing-checkpoint pilot

The unsealed paired-v2 harness evaluated K and R on a 32-motion repair panel
(11 certified, 11 over-budget, 10 residual) under raw and repaired references.
Each cell used the same 824-condition manifest; 812 conditions and 29 motions
supported the full 3 s window. R/repaired minus K/raw improved motion-equal
success by +0.1355 (motion-bootstrap 95% interval [+0.0505,+0.2365]) and survival
by +0.2626 s ([+0.1208,+0.4238]). Raw-reference R minus K was only +0.0234
success points ([-0.0123,+0.0825]), while K/repaired minus K/raw was +0.0961
([+0.0320,+0.1773]). The deployment gain is therefore chiefly reference-side.

The deployment success delta was +0.2630 on over-budget repairs, +0.0844 on
certified repairs, and +0.0153 on full-window residual repairs. A disjoint
12-motion clean/raw panel found R minus K success +0.0208 ([0,+0.0625]) and
survival +0.0149 s ([-0.0454,+0.0900]). Common-raw quality on four-way survivors
is mixed: MPKPE improves 1.32 mm, while anchor error worsens 15.4 mm and work
rises 0.644 J/actuator. This one-seed, mechanism-selected pilot is repair-routing
and evaluator evidence only; it does not replace sealed N7 or validate training.
Artifacts: `reports/eval_v2_pilot/` and
`autoresearch/evals-260820-1734/review_log.md`.

## Minimal staged experiment

1. **Completed exploratorily:** CPU tests and a 10-motion, 512-env,
   200-iteration simulator smoke.
   Gates: zero invalid starts/failures, realized invalid frames ≤0.5%, exact floor,
   exposure-invariant priorities, no nonterminal teleport, and sampler-equivalent
   boundary resume. Full simulator continuation remains explicitly deferred.
2. **Partially completed:** the one-seed exact-feasible uniform/adaptive wiring
   screen is mechanically clean, but survival is unresolved and final curriculum
   TV is only 0.0140. Freeze a minimum manipulation gate and the missing
   segment-unmasked grounded control before more training. The planned arms are
   segment-unmasked grounded control, exact-feasible uniform hygiene, and
   exact-feasible conditional segment-adaptive v2. Run two more seeds only after
   all mechanism gates pass. Do not reuse the old grounded arm as the control.
3. **Pending:** confirm benefit only if feasible-disjoint survival and AULC improve with a
   positive hierarchical-CI lower bound, coverage and motion-quality
   noninferiority pass, and no concentration/contamination gate fails.
4. **Completed exploratorily:** evaluate existing K/R checkpoints under the
   paired v2 harness. Route over-budget repairs to repair research; route
   residual cases to exact segments/replacement unless later evidence improves.

Pilot result and decision: `plan/SEGMENT_NATIVE_PILOT_RESULT_2026-08-20.md`.

MJLab is the development platform because its bank contains enough measured
contamination and its training loop is already instrumented. The released SONIC
bank has only 0.14% flagged clips, so SONIC is an evaluation-only external-
validity target until a genuinely contaminated, pre-filter bank is available.
For SONIC's forward lookahead, use backward/causal exclusion before an invalid
window; the current symmetric guard removes valid post-window material and must
not be reused unchanged.
