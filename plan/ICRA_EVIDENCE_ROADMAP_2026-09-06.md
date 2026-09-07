# ICRA evidence roadmap and physical-assumption audit

Date: 2026-09-06. **Unsealed addendum.** Current U/A/R/D confirmation remains
governed by contract `8f2192a9b937060a9ba6aa4fbd1b4a6aed8a7da183abf1c64fa9db557a5af013`.
This implements follow-on analysis and a model audit; it changes no frozen source,
threshold, profile, seed, support, reference, or evaluation condition.

## Research question and contribution to earn

Does allocating exact, model-admissible practice by relative progress improve
held-out G1 control at equal training transitions, and does that effect persist
under specified changes to physical assumptions? Allocation contrast establishes
that training exposure changed. It cannot establish useful learning, forgetting
recovery, physical feasibility on a particular robot, or transfer.

The intended contribution is an exact-support sampling interface with 50-step
trials (**implemented**), a four-arm comparison across three paired training seeds
(**pending policy evidence**), and a bounded account of admission, estimator noise,
and physical sensitivity (**development checks measured; outcome studies pending**).
These are separate evidence obligations; a positive allocator result alone does
not establish the gate's practical value or physical deployment readiness.

## Reconciliation with the supplied guidance

1. Phase A has completed. Both D calibrations passed, including seed 32's mean TV
   0.0859387133. All seed-51 entrypoint smokes passed. The existing freezer
   reproduced prerequisites and all 12 configurations, then sealed the contract.
   Evidence: `reports/relative_progress_2026-09-05/confirmation_freeze/freeze_result.json`
   and `reports/research_next_2026-09-06/calibration_verification.json`.
2. Phase B's original scheduler is active, waiting for the shared GPU before its
   first arm at this stage's audit. It retains 12 training jobs and 48 evaluation
   cells. All 12 training gates precede access to the held-out outcomes. Its
   existing per-job GPU wait limit is 7,200 seconds; a timeout must remain visible,
   with no silent relaunch or weakening of the resource gate.
3. The frozen primary decision is final feasible-hard R−U TrackingScore mean
   at least +0.02, positive lower **two-sided** 95% paired t bound (df=2), plus
   all-panel lower bound above −0.01. The Chinese guidance's one-sided interval
   is not substituted. The existing paired seed-and-clip bootstrap is supplementary;
   it is not a fallback decision rule or a substitute for more training seeds.
4. The approximately 46.7% declining-estimate excess allocation is descriptive.
   Existing exact development summaries are 46.6047% and 46.8090% for R11/R12.
   It does not identify forgetting or wasted compute. Continue the already queued
   frozen-policy instrumentation pilot, then define independent scored noise
   measurements; only a targeted, matched practice intervention could establish
   recovery attributable to additional practice.
5. Treat hardware relevance as an evidence priority, not a guarantee of acceptance
   or an asserted universal ICRA hardware requirement. A robustness evaluation
   supports simulation sensitivity claims. HIL measures only its actual included
   hardware/control components; neither label automatically proves physical G1
   transfer. Hardware access is unconfirmed; proceed with simulation preparation.

## Completed work: efficiency postprocessor

New tools are isolated in `/home/linjiw/climb-icra-evidence-2026-09-06`, a detached
worktree at `1552c99`. They read the original frozen implementation by absolute
path. The original runtime inventory includes all top-level Python tools, so even
adding a new tool there would invalidate confirmation. No packages were installed.

`tools/analyze_icra_efficiency.py` waits optionally for the original terminal
record, rejects stopped/invalid campaigns, verifies bound source bytes, invokes
the original complete campaign analyzer, and requires reproduction of its saved
analysis before producing any real secondary report. It reports:

- Feasible-hard and all-panel per-seed learning curves and normalized trapezoidal
  AULC over iterations 1000–3999. The hard-panel AULC must match the original.
- Each seed's U final score as a **descriptive, outcome-derived** target, used for
  all four paired arms. All subsequent observed checkpoints must retain attainment.
- First-observation attainment and targets never attained explicitly; no invented
  crossing between checkpoints, monotone fit, or finite ratio for non-attainment.
- Exact training transitions `(iteration+1) × 512 × 24`: checkpoints follow
  zero-indexed PPO updates. Iteration 2000 therefore uses 2001/4000 = 50.025% of
  the full training budget. This arithmetic is not an observed efficiency gain.

These outputs remain **exploratory secondaries**. No new threshold was added to
confirmation, and no favorable secondary can change its primary disposition.
The actual readiness report returns `pending`, with no endpoints opened. Synthetic
fixtures check censoring, transient crossings, original-AULC disagreement, invalid
scores, and stopped-campaign access. The real completed-data path remains untested
until actual confirmation evidence exists; synthetic tests are not policy results.

## Completed work: physical-assumption audit

`tools/audit_icra_physics.py` reproduced all 12 frozen configuration hashes and
compiled the unchanged robot on CPU, exposing all 29 actuator force limits.
Evidence: `reports/icra_evidence_2026-09-06/physics_audit.json` in the original repo.
No simulator rollout, trained checkpoint evaluation, or hardware run was performed.

| Physical axis | Verified configuration / compiled model | Evidence limit and next test |
| --- | --- | --- |
| Knee torque | Both knee force ranges are [−139,+139] N·m, force limiting enabled, unit gear | Unitree publicly lists maximum knee torque 90 N·m for G1 and 120 N·m for G1 EDU. The model has not been calibrated to an identified hardware revision. |
| Other actuator assumptions | Built-in position actuators; upstream documents nominal linkage-armature approximation | Static clamps do not establish torque-speed, thermal, transmission or motor-response fidelity. |
| Command delay | All six actuator configuration groups have min/max delay 0/0 | Physics steps are 5 ms; control steps 20 ms. Command delay, motor response lag and observation latency are different perturbations. |
| Contact | Full collision config, feet condim=3; nominal foot friction 0.6; startup friction sampled over [0.3,1.2] | Configured friction/contact is not independently measured contact fidelity. |
| Training perturbations | Torso COM, encoder bias, friction, and interval pushes configured | Configuration audit establishes enabled events, not per-rollout realized magnitudes. |
| Evaluation | Sealed `nominal=false`; startup COM/friction/encoder randomization retained; pushes and observation corruption removed | This is not a factorial robustness study; do not label evaluation nominal or claim push robustness. |
| Terrain | Plane | Uneven-terrain robustness untested; placement and contact checks must precede any terrain sweep. |

The manufacturer comparison is from the [official G1 specification](https://www.unitree.com/g1/),
checked 2026-09-06. It establishes a discrepancy with public limits, not that a
particular physical motor has been measured or that the simulator result is invalid.
Preserve the original model and report its declared scope.

## Next physical-sensitivity experiment: prospective draft S1

Question: with policies frozen, how does changing one specified physical
assumption change TrackingScore and the paired R−U contrast? This is evaluation
of sensitivity, not a training-domain-randomization ablation or Sim2Real claim.

Proposed minimum grid: all U/A/R/D final checkpoints × seeds 21/22/23 × eight
conditions: unchanged sealed evaluation setup; fixed command delays 5/10/20 ms;
knee-only caps 120/90 N·m; fixed foot-friction 0.3/1.2. These are declared stress
levels and public-spec sensitivity points, not measured hardware distributions.
Retain all other startup perturbations, exact starts, condition seeds and failure
denominators; no adaptation or PPO during evaluation. Reuse the same 100-clip
panel transparently. The grid would have 96 cells and 268,800 condition instances
at 2,800 conditions per cell; this is a proposed budget, not executed work.

Before freeze, implement a separate evaluator with matched-state replay and
realized parameter telemetry. Split knee targets from hip-roll targets: they share
one upstream actuator configuration, so changing its effort limit wholesale would
confound a knee-only experiment. Delay values must use physics-step units and
the same reset-buffer rule across conditions. Preserve startup RNG draw order
and verify common initial states before applying the single perturbation.
Verify clamps on every targeted actuator, log saturation with all failed episodes,
and verify actual delay traces and friction values. Run development-only CPU/GPU
lifecycle checks before a prospective source/configuration/input freeze.

Report seed-level score degradation relative to unchanged evaluation, paired
R−U in every condition, worst specified condition and failure/exposure counts.
All S1 comparisons are exploratory unless a separate prospective statistical
contract is completed. A positive result in one stress condition does not prove
general robustness. Do not add a new randomization training arm to the current
campaign. Terrain and measured motor lag need separate validated implementations;
they are explicit follow-ups, not implied by the eight-cell grid.

## Execution order and manuscript decisions

Priority remains: complete original confirmation; run the already bound
frozen-policy pilot; prepare and freeze the matched D gate-on/off H1 study in its
existing worktree. S1 implementation can proceed on CPU independently; no S1 GPU
job displaces those queues. If the original campaign stops, preserve the terminal
reason and determine whether any scientific job started before any continuation.

| Evidence obtained | Permitted positioning |
| --- | --- |
| Frozen benefit and all-panel guard pass | Relative-progress sampling improves the declared simulated tracking endpoint; retain R−D limits. |
| Only intermediate curves/AULC favor R | Exploratory convergence lead; a confirmatory efficiency claim needs a new prospective study. |
| Wide seed intervals | Inconclusive at three seeds; bootstrap does not increase trained-policy replication. |
| Sensitivity results complete | Name the tested parameter levels and worst-case degradation; no unmeasured transfer claim. |
| Actual hardware/HIL trials complete | Name device/revision, included components, conditions, attempts, failures and interventions. |

For video preparation, specify 3–5 motion families from reference kinematics
before looking at policy rollouts: turning, crouching, dynamic stepping, optional
upper-body reach and recovery transition. Lock deterministic clip IDs, initial
conditions and all attempts before selection; include failures and residual curves.
Do not choose only successful clips. Hardware selection additionally depends on
the identified platform, operator and screened execution envelope; no physical
experiment is launched here.

The [official ICRA 2027 call](https://2027.ieee-icra.org/announcements/call-for-technical-papers/)
lists September 15, 2026 for contributed papers (checked 2026-09-06). Protect
the remaining writing window: lead with measured control outcomes, show individual
seed curves, retain negative decisions, and keep unexecuted components pending.
Exact commands, hashes, checks and queue state are in
`reports/icra_evidence_2026-09-06/README.md` and `verification.json`.
