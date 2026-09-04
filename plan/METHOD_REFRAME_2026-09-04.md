# CLIMB method reframe and next research program

**Date:** 2026-09-04  
**Status:** unsealed research/writing plan. It changes no sealed result, Phase-G arm, gate, or
endpoint. The framing follows the local Xiao-inspired evidence-writing rubric; it is not an
impersonation, review prediction, or endorsement.

## Decision

Reframe the short paper as a methods paper about **feasibility-gated humanoid motion tracking**,
not as a passive audit report. The physical bottleneck is **reference--physics misalignment
(RPM)**: policy error is an ambiguous curriculum signal when the final retargeted trajectory
demands a wrench or actuator effort that the declared robot/scene model cannot supply.

CLIMB is the method:

1. **Screen:** evaluate the final robot-space trajectory with contact-free inverse dynamics and a
   torque-limited contact-capacity program.
2. **Route:** admit supported intervals; attach missing scene context where appropriate; send
   qualified borderline cases through root/contact projection and re-screening; quarantine
   residual or fidelity failures.
3. **Gate and allocate:** construct exact non-wrapping legal starts and apply learning-progress
   allocation only inside the admitted support.

The current Phase-G method is the interpretable hard-gate special case

`q_u(k) proportional to F_u * b_u * (LP_u(k) + lambda)`, with `F_u in {0,1}`,

followed by a joint operator that mixes the deployment prior, preserves the exact exploration
floor, and reallocates focused mass under unit/clip caps. A smooth residual score is a new
intervention, not a rename of the queued experiment.

## What the evidence already supports

| claim | evidence | strongest current statement |
|---|---|---|
| RPM can create a curriculum attractor | three historical training seeds plus one hash-bound reference anatomy | the same unsupported kneel/crawl reference repeatedly becomes dominant; campaign peak top-1 mass is 0.870--0.893, but another clip owns the maximum in two seeds |
| the screen operates at bank scale | 10,705-clip primary pipeline and 4,950-clip production pairing | 2,442/10,705 and 7/4,950 cross the same nominal threshold in two separately scoped corpus/pipeline measurements |
| the implementation signal reproduces | deterministic flag-enriched 40-clip same-input panel | 39/40 strict decisions agree; score rho is 0.9836 and kappa is 0.9485 on this panel |
| the hard gate is a complete training interface | exact 800-motion unit table and runtime contract | 1,184 units expose 368,951 legal 50-step starts; rejected intervals receive zero mass under the declared model |
| repair is an implemented route | DFRP v1 exact CPU panel | 22/26 flagged candidates qualify, 4/4 feasible controls remain byte-identical, and the curated view has 10,561 starts; this is not a bank-wide recovery rate |
| repair improves the controller | sealed N7 boundary | not established: deployment delta +0.0397 misses the +0.05 SESOI, raw-reference policy transfer is -0.0036, and coverage fails |
| ALP adds value after gating | Phase G | pending endpoint-blind calibration and therefore not yet claimable |

The manuscript may say that CLIMB **prevents rejected intervals from receiving training mass under
the declared model**. It may not yet say that CLIMB improves tracking, broadens coverage, prevents
all collapse, transfers to hardware, or is state of the art.

## Literature boundary

The current primary-source scan supports a narrow delta:

- [BeyondMimic](https://arxiv.org/abs/2508.08241) prioritizes motion segments with high empirical
  failure rates.
- [GMT](https://arxiv.org/abs/2506.14770) maps completion/tracking performance into normalized
  sampling probabilities and also clips long sequences.
- [EGM](https://arxiv.org/abs/2512.19043) maintains EMA composite tracking errors for globally
  indexed motion bins.
- [PHUMA](https://arxiv.org/abs/2510.26236),
  [AMO](https://doi.org/10.15607/RSS.2025.XXI.061),
  [SPIDER](https://arxiv.org/abs/2511.09484), and
  [kinodynamic retargeting](https://arxiv.org/abs/2603.09956) establish that physics-aware
  curation, contact-guided repair, and dynamically constrained retargeting already exist.

Therefore the defensible contribution is not “the first physics filter.” It is the explicit
composition of a low-cost, policy-independent, final-trajectory dynamic-admissibility test with
an exact-support adaptive curriculum, plus the matched experiment that separates the gate from
the allocator.

## Claim-isolating experiment sequence

### G — allocator value inside a fixed gate (current critical path)

| field | contract |
|---|---|
| question | Does calibrated ALP improve feasible-hard tracking after admissibility and legal-start exposure are fixed? |
| changed variable | G2 ALP versus G1 deployment-uniform allocation |
| fixed | robot, task, PPO, reward, exact support, duration-correct base prior, caps, compute, seeds, evaluator |
| primary | liveness-weighted TrackingScore on 25 reference-defined feasible-hard clips |
| secondaries | survival; all-panel TrackingScore; AULC; common-survivor MPKPE, anchor error, and mechanical work |
| decision | positive / null / inconclusive / not-tested after manipulation and provenance gates |

Do not add smooth feasibility, repair, or dirty-support arms to Phase G. Doing so would destroy the
one-variable contrast and invalidate the calibration work already in progress.

### H1 — does the gate prevent a matched dirty-support attractor? (highest-leverage follow-up)

This is the experiment required before using a title or abstract that says CLIMB *prevents
pathological curriculum collapse*.

| field | contract |
|---|---|
| question | Under a contaminated bank, does the binary gate stop a failure-based curriculum from allocating to inadmissible intervals and preserve feasible held-out learning? |
| changed variable | `F_u=1` for every exact non-wrapping candidate unit versus the frozen binary feasibility gate, with the same failure-based allocator in both arms |
| fixed | candidate motions, horizon semantics, duration prior, caps, PPO, reward, compute, seeds, evaluator |
| manipulation | rejected-mass, top-1 identity/mass, TV from base, entropy-effective units, invalid/censored counts |
| primary | feasible-hard held-out TrackingScore; sampler collapse is a co-primary mechanism readout only if fixed before training |
| interpretation | isolates gate efficacy under one dirty bank and one failure allocator; it does not establish smooth gating or hardware benefit |

The ungated control must still use exact non-wrapping horizons so wraparound and duration exposure
cannot explain the difference. The only intended change is dynamic admission.

### H2 — hard versus smooth feasibility weighting (only after H1)

Define the smooth score from normalized wrench/torque slack before reading outcomes, calibrate it
on reference-only and sampler telemetry, and compare it against the binary gate with the allocator
otherwise fixed. A smooth gate should be pursued only if its expected gain is explicit: retaining
borderline diversity without restoring attractor mass. Required plots are score calibration,
retained-duration coverage, top-1 exposure, and feasible-hard TrackingScore. A smooth score that
cannot be calibrated across pipelines remains exploratory.

### H3 — filter versus certified repair

| arm | training support | purpose |
|---|---|---|
| hard gate | exact feasible intervals only | filtering baseline |
| hard gate + certified repair | same exact support plus DFRP-qualified repaired intervals | repair-system comparison |

Use the same allocator in both arms. Evaluate unchanged feasible clips, repaired/raw paired clips,
and missing-context clips separately. Report survival beside root-relative MPKPE, reference
fidelity, contact timing (only if validated), saturation exposure, and mechanical work. The
decisive repair claim requires benefit on certified repairs without regression on unchanged
references; aggregate improvement driven by over-budget edits does not pass.

## Metric policy

The current paper can report:

- liveness-weighted TrackingScore;
- survived-horizon fraction;
- common-survivor root-relative MPKPE and anchor-orientation error;
- absolute mechanical work per actuator;
- contact-event timing only if the blinded instrument gate passes.

Torque saturation rate, torque derivative energy, electrical current, winding temperature, and
hardware safety remain new measurements. Add them only with source-cited actuator envelopes and a
validated evaluator; torque commands alone do not establish thermal or electrical harm.

## Manuscript transformation

| old emphasis | revised role |
|---|---|
| audit / warning | RPM as the operational constraint that motivates CLIMB |
| clip-level flagging | stage 1 of an active screen--route--gate method |
| exact-support contract | the training interface that makes `F_u * LP_u` implementable and testable |
| negative controls | evidence that deletion, weak allocation, and unconstrained repair are not substitutes for the method |
| Phase-G contract language | a positive claim-isolating ablation with exhaustive status reporting |
| disclaimers throughout | one model-relative limitations section with the next discriminating observations |

The revised paper title is:

> **Feasibility-Gated Humanoid Motion Tracking: Separating Reference Physics from Curriculum
> Difficulty**

The stronger alternative—“Preventing Pathological Curriculum Collapse”—is reserved for a passed
H1 gate-and-outcome comparison. “FeasTrack” is not introduced: CLIMB is already the repository and
method identity, and adding a second decorative name would not create a contribution.

## Immediate execution order

1. Keep the endpoint-blind 12-row Phase-G calibration watcher alive at the conservative 14,000 MiB
   availability gate; do not inspect policy endpoints.
2. If calibration and independent validation pass, copy only the selected sampler parameters into
   the unsealed Phase-G draft, close the contact-instrument disposition and measured footprint,
   then seal.
3. Run G1/G2 confirmation and populate exactly one frozen result branch.
4. Rebuild the paper, update the claim ledger, and run the arithmetic/anonymity/page/font audit.
5. Design H1 only after Phase G; it is the smallest new experiment that licenses the proposed
   “prevents collapse” headline.
