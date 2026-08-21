# Newton-grounded segment curriculum — direction addendum

**Date:** 2026-08-21
**Status:** design revision after the unsealed segment-v2 pilot; not a
preregistration and not authorization for confirmatory training.

## Decision

Keep the exact segment lifecycle and paired evaluator. Do not spend additional
seeds on the current conditional-failure sampler: its final distribution was
only 0.014 total variation from the exact-uniform control, and its paired
survival interval crossed zero. Re-center the next experiment on a falsifiable
question:

> Does a Newton-measured, segment-level physics fragility signal predict
> held-out tracking degradation and improve matched-compute training beyond
> exact feasibility hygiene and online learning progress?

Newton is the **measurement teacher**. MJLab remains the trainer. This preserves
the proven high-throughput PPO path while using Newton where it is distinctive:
paired solver/contact/actuator probes under one model.

## Evidence that forces the revision

- Exact-uniform success was 0.6746; adaptive was 0.6825. The paired unit-clustered
  delta was +0.0079, 95% interval [−0.0536,+0.0714].
- Common-survivor body-position and anchor-orientation errors improved, but one
  seed and a mechanism-selected panel cannot establish a general quality benefit.
- Failure estimates saturated near 1 across most units. A linear conditional-rate
  rank therefore produced almost no treatment separation even though entropy and
  top-1 concentration looked healthy.
- Feasibility screening answers whether a requested transition is supportable.
  It does not answer which feasible transition is sensitive to delay, torque
  saturation, collision model, or solver semantics.

## Newton capability correction

The old recertification note targeted Newton 1.0. The current official release is
Newton 1.5.0, so all new work must use a fresh, isolated environment and record
the exact Newton, Warp, MuJoCo, and MuJoCo Warp pins. Do not modify the pinned
MJLab trainer environment, which currently has no `newton` package.

Newton 1.5 adds scalable multi-world workflows, masked solver resets,
deterministic hydroelastic contact generation, vectorized joint control, and
MuJoCo/MuJoCo Warp 3.11 dependencies. Newton 1.4 added opt-in deterministic
solver paths, articulated inverse dynamics, and explicit use of Newton contacts
with `SolverMuJoCo`. Newton 1.2 added composable delay and motor-clamping actuator
models. These features make controlled short-horizon physics probes practical.

One limitation is load-bearing: the current solver matrix does **not** mark
`SolverMuJoCo` differentiable. Differentiable contact kinematics are experimental,
and Newton freezes the discrete narrow phase. Gradient-based fragility is therefore
a later Featherstone/SemiImplicit spike, never an assumption behind the first
benefit test.

Official references: [Newton v1.5 release](https://github.com/newton-physics/newton/releases/tag/v1.5.0),
[solver feature matrix](https://newton-physics.github.io/newton/stable/solvers/index.html),
and [collision pipeline](https://newton-physics.github.io/newton/stable/concepts/collisions.html).

## Measurement contract

For every exact feasible unit:

1. Roll the frozen policy once in the nominal, conformance-certified stack and
   save canonical states, actions, contacts, and reference indices.
2. Resynchronize every probe at the same canonical state. Use 0.25–0.50 s
   horizons so long-horizon chaos cannot masquerade as physics sensitivity.
3. Run deterministic repeats first; any nonzero same-configuration dispersion is
   a harness failure. Then add an explicit, paired noise ensemble.
4. Vary one named axis at a time: actuation delay and motor saturation first;
   MuJoCo versus Newton contact generation second; solver formulation only after
   state/action/contact conformance passes.
5. Record an axis vector, not one averaged score: survival/RMST regret, body and
   anchor tracking error, contact-set/timing change, foot slip, work, saturation,
   and joint-limit exposure.
6. Call the signal useful only if it predicts a held-out axis or held-out policy
   beyond reference kinematics and the feasibility screen. Solver agreement is
   not physical truth.

## Training design

The clean causal design has four fresh, matched-compute arms:

| Arm | Start support | Priority | Contrast answered |
|---|---|---|---|
| G0 | Unmasked grounded starts | Deployment prior | Cost/benefit of exact hygiene |
| G1 | Exact feasible segments | Deployment prior | G1−G0: hygiene effect |
| G2 | Exact feasible segments | Online learning-progress/uncertainty | G2−G1: adaptive allocation |
| G3 | Exact feasible segments | Learning progress + validated Newton fragility | G3−G2: incremental physics information |

Raw failure probability is retired as the sole rank because it saturates and can
reward unlearnable units. All adaptive arms retain the exact support mask, fixed
50-step trials, explicit truncation, exploration floor, 0.05 unit cap, 0.25 clip
cap, stable unit attribution, and paired evaluation.

Before outcome evaluation, require a manipulation check: adaptive probability
total variation from G1 must remain in a predeclared informative band (candidate
0.05–0.15 after warm-up), entropy-effective units must remain at least 12, and
invalid/censored exposure must be zero. A post-hoc power-4 calculation reaches
0.055 TV without violating caps, but it is only a calibration candidate.

## Staged gates and kill criteria

1. **Recertify Newton 1.5:** one G1 policy, one easy unit and one contact-rich
   unit. Match placement, first observation, action, state, and contact timing.
2. **No-training predictive gate:** on a development-only unit panel, test whether
   the Newton vector improves held-out degradation prediction over screen and
   reference features. Kill the training arm if it does not.
3. **One-seed wiring screen:** run G0–G3 only after the feature gate passes.
   Reject any arm with weak manipulation, cap violation, objective collapse, or
   worse feasible-disjoint quality beyond the declared margin.
4. **Three-seed confirmation:** advance only if G3 improves survival/AULC over G2
   and keeps common-survivor motion quality noninferior. Use a seed×unit
   hierarchical bootstrap and a disjoint evaluation panel.

If solver conformance fails, retain contact-pipeline and actuator axes. If the
Newton vector predicts only diagnostics but not held-out degradation, publish it
as an analysis instrument and do not claim curriculum benefit. If G3 does not
beat G2, keep the exact hygiene lifecycle and stop escalating physics-weighted
training.
