# Advisor guidance — End-to-End Dynamic Feasibility & Repair Pipeline

**Received:** 2026-08-21
**Status:** user-supplied, unsealed research direction. This file preserves the
guidance; it is not a result, preregistration, or authorization to edit sealed
artifacts. Numerical statements retain their supplied wording and must be
checked against the CLIMB artifact ledger before publication.

## Proposed direction

Build an **End-to-End Dynamic Feasibility & Repair Pipeline (DFRP)** directly
integrated into `mjlab`, with an eventual compatibility path for massive-scale
motion tracking frameworks such as SONIC. The motivation is the CLIMB finding
that 22.8% of one AMASS→G1 corpus-and-pipeline pairing is dynamically
infeasible, allowing failure-adaptive curricula to concentrate on impossible
references.

The preferred strategy is pre-training repair plus simplex-grounded sampling:

| approach | supplied bottleneck / risk | supplied expected ROI |
|---|---|---|
| downstream reward shaping | makes RL spend on torque-impossible workarounds | low |
| pure filtering | removes dynamic/agile coverage with the rejected clips | medium |
| automated repair + simplex grounding | repair recoverable clips, quarantine the tail, and preserve a fixed coverage floor | highest |

The supplied three-stage architecture is:

```text
raw/retargeted bank
  -> refeas contact-free inverse-dynamics + torque-limited LP screen
  -> feasible clips OR contact-projection repair
  -> recovered clips OR quarantine
  -> curated training bank
  -> simplex-grounded curriculum
  -> MJLab GPU training
  -> stratified-start evaluation
```

### Supplied data-pipeline policy

- Candidate collision geoms lie within 6 cm of terrain.
- Clips with `infeasible_frac > 0.10` enter repair.
- Repair applies vertical root projection and constrained leg IK.
- A repaired clip should reach `infeasible_frac <= 0.05`.
- The supplied deployment displacement budget is 8 cm; failures should be
  quarantined rather than silently used for training.

### Supplied sampler policy

Replace the upstream additive pseudo-count rule with a scale-invariant simplex
mixture. The guidance gave the illustrative form

```text
p = (1 - rho) * softmax(failure / temperature) + rho * uniform
rho = 0.10
```

and asked for failure-EMA updates, a fixed coverage floor, and integration into
the MJLab motion-tracking manager.

### Supplied evaluation policy

- Stratify whole-clip starts at `{0.00, 0.25, 0.50, 0.75} * clip_duration`.
- Treat feasible-only AULC and terminal survival as primary.
- Keep all-clip survival as descriptive secondary.
- Track peak normalized joint torque and motor-strength sign reversals as
  transfer/safety diagnostics.

### Supplied experimental matrix

| arm | training corpus | sampler |
|---|---|---|
| 0 | raw 10k AMASS bank | upstream additive adaptive |
| 1 | screen-filtered bank | upstream additive adaptive |
| 2 | repaired bank | upstream additive adaptive |
| 3 | repaired bank | simplex-grounded, `rho=0.10` |

The supplied hypotheses were a curriculum-entropy floor, at least +3.5%
held-out survival for the proposed arm, at least 15% lower torque-limit p95, and
elimination of motor-strength sign reversals. The supplied schedule proposed a
four-week screen/repair, integration, three-seed training, and upstream-PR
program.

## Longer-horizon vision preserved from the guidance

1. **Differentiable feasibility:** port inverse dynamics and contact
   optimization to differentiable PyTorch/JAX and use unsupported-wrench loss
   to guide video-to-motion or diffusion generation.
2. **Cross-embodiment atlas:** evaluate the same source motions on G1, H1, T1,
   GR-1, and Figure-class embodiments and solve morphology-aware repair.
3. **Complex terrain and contact graphs:** replace the flat-plane assumption
   with mesh/SDF distance queries and support multi-contact transitions across
   feet, hands, knees, steps, rails, and objects.
4. **Hardware runtime guard:** screen an incoming reference buffer and blend to
   balance recovery when predicted wrench or actuator demand is unsafe.

The supplied high-impact proposal names are **D-Feas**, **Universal Feasibility
Atlas**, **Terrain-refeas**, and **SafeTrack**.

## Reconciliation required by the existing record

The following corrections are part of preserving the guidance honestly:

- The measured 65.8% census used the legacy root-only operator and a 15 cm
  success budget. It is not evidence for an 8 cm root+IK recovery rate.
- N7 missed its sealed benefit and coverage gates. Its positive deployment
  contrast was mostly reference-side and concentrated in over-budget edits.
- P-SIGN failed its sealed generality/control criteria, so sign reversal cannot
  be a load-bearing runtime detector claim.
- The illustrative sampler fixes the simplex algebra but omits exact support,
  conditional attribution, fixed-horizon truncation, caps, and resumable state.
  The segment-native v2 runtime is the implementation base.
- The 22.8% rate belongs to one corpus-and-pipeline pairing; the screened
  BONES-SEED/SONIC release measured 0.14%.
- “Four orders of magnitude,” zero-shot hardware safety, differentiable
  feasibility, cross-embodiment universality, and terrain generality remain
  hypotheses until separately measured.
