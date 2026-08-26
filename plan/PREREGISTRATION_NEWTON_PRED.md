# Pre-registration — Newton 1.5 no-training predictive gate

**Sealed:** 2026-08-26 EDT, before any Newton axis outcome on this panel was measured  
**Role:** Phase N-c gate; no training is authorized by this document  
**Manifest:** `plan/PREREGISTRATION_NEWTON_PRED.md.sha256`

## Question and consequence

Does a three-axis Newton fragility vector measured with one frozen development
policy predict the signed degradation of a held-out policy beyond the dynamic
feasibility screen and reference-only kinematics?

This is a hard gate. A valid measurement passes only under the joint rule in
this document. If it fails, Newton remains an analysis instrument and **G3
fragility-weighted sampling never runs**. A harness or manipulation failure is
reported as **not tested**, repaired under a dated addendum, and re-run before
any predictive verdict; it is not counted as a scientific null.

## Frozen panel and reference-only controls

Population: all 42 `admissible_units` from the ten-clip segment-v2 mechanism
panel in `reports/segment_v2_smoke/unit_table.json`.

- unit-table file SHA-256:
  `d80e228c1e44f7c669e033cba2bd7f774ff1fb4d5c6bdf39d1da5b7405584b16`;
- embedded canonical payload SHA-256:
  `2aaeaa741959eabbfc9510a18820f9745bc7e879dfa423423385e835b6f120a6`;
- reference-control table:
  `reports/newton15_pred/reference_features.csv`, SHA-256
  `406ec4076402973a2bbd9644fb9e562760366a2427aaf311a3c89a844013c02e`;
- reference-control provenance:
  `reports/newton15_pred/PANEL.json`, SHA-256
  `2157fcf430caa3210d25ecbd481fdef1d204d99aaf14570500758dd8fee9ee69`.
- reference-control builder: `tools/build_newton_pred_panel.py`, SHA-256
  `971ee63fe94d0d7cdfb8b7d3969ba9467316a36a73625be2944f00975a64b120`.

The fixed start for a unit is
`admissible_start_first + floor((legal_start_count - 1) / 2)`. The probe uses
frames `[start, start + 25)`, which remain inside the unit's stricter frozen
50-step support. The 25 control steps are 0.50 s at 50 Hz.

The baseline control block has exactly seven columns:

1. clip-level `infeasible_frac` from the hash-bound source sidecar;
2. root linear-speed RMS;
3. root angular-speed RMS;
4. joint-speed RMS;
5. joint-acceleration RMS;
6. body linear-speed RMS;
7. root-height range.

The six kinematic controls are computed only over the fixed 25-frame window.
`unit_unsupported_ratio_mean` is preserved in the CSV for description but is
not a primary-model covariate. No policy or simulator outcome was opened to
select the units, starts, controls, or thresholds.

## Frozen policies

All checkpoints are existing iteration-3999 policies; none is trained or
fine-tuned for this gate.

| role | checkpoint | SHA-256 |
|---|---|---|
| development feature | `logs/rsl_rl/g1_tracking/2026-08-15_20-29-21_uniform-mixed100-s1/model_3999.pt` | `6099a7072afdcfa4bca17201dc4b1092ec373e8621ff50e6d7ffd2792a7de079` |
| primary held-out policy | `logs/rsl_rl/g1_tracking/2026-08-15_23-42-12_adaptive-mixed100-s1/model_3999.pt` | `22079dde59496a4f6e44de95bd0dfc9a6ce362436ad448261fa52eba64f58085` |
| directional replication | `logs/rsl_rl/g1_tracking/2026-08-16_09-03-16_grounded-mixed100-s1/model_3999.pt` | `e97881c05dc9674af0734964c30a6272549038361ee7818231ebad5cecf4b7f1` |

The adaptive policy is the sole primary held-out target. Grounded is a
predeclared directional replication, not a second chance to pass the primary
test. Other checkpoints and outcomes are excluded from the gate.

## Physics and rollout contract

The stack is the isolated Newton 1.5 environment in
`plan/NEWTON15_PINS.md`: Newton 1.5.0, Warp 1.16.0, MuJoCo 3.11.0, MuJoCo Warp
3.11.0, mjlab 1.6.0, and the G1 MJCF at SHA-256
`febdcbeffbbf84051556ae41a5ac1b43fb479a5d76bdb3f54824dbc2721c20aa`.
Phase N-b passed before this seal; its result is
`reports/newton15_recert/result.json` at SHA-256
`d997af51d81aaf083446cf8790d7fea605bc100cc791305619b3bcedda82603d`.
The seven live-model import residuals found there must be mirrored before any
probe.

Each policy × unit uses eight paired initial-condition replicates. The random
draw for `(table_index, replicate)` is shared across base and all axes and,
where dimensions agree, across policies. The generator is Torch CPU seed
`20260827`; perturbations inherit N5 exactly: joint position independently
uniform in ±0.05 rad, root linear velocity in ±0.10 m/s, and root angular
velocity in ±0.20 rad/s. A reference placement plus one perturbation is saved
as the canonical state, and every condition is reset to that same state,
constraint warm start, reference index, and observation-history state.

Nominal dynamics use Newton `SolverMuJoCo`, the certified model mirror, and
MuJoCo-native contact generation. The three one-at-a-time axes are:

| axis label | perturbed condition | paired base | sign convention |
|---|---|---|---|
| `delay_20ms` | one complete 20 ms policy-action delay; FIFO initialized from the first undelayed target | nominal Newton | delayed minus base |
| `motor_clamp_85pct` | maximum actuator effort clamped to 85 % of the nominal per-joint limit; controller gains/biases unchanged | nominal Newton | clamped minus base |
| `newton_contact` | `SolverMuJoCo(use_mujoco_contacts=False)`, Newton point-contact generation; dynamics, actuators, step size, iterations, and model otherwise identical | `use_mujoco_contacts=True` | Newton-contact minus MuJoCo-contact |

The delay starts affecting the second control step. The probe horizon, policy
rate, and reference rate remain 25 steps / 0.50 s / 50 Hz. Auto-reset is off for
terminal reads. Termination and metric definitions are identical across all
conditions.

## Instrument and manipulation checks

Before opening the effect table:

1. Independently rebuild and repeat the nominal condition twice for every
   policy × unit at replicate 0. Observations, actions, states, contacts,
   reference indices, and termination flags must have exactly zero dispersion.
2. The first cross-condition canonical state, warm start, reference index, and
   observation history must be byte-identical. Invalid starts and escaped
   reference frames must both be zero.
3. Runtime assertions must confirm a one-step FIFO offset in every delay world,
   unchanged gain/bias arrays plus exactly 0.85 nominal effort limits in every
   clamp world, and the requested `use_mujoco_contacts` value in every contact
   world. At least 12 of 42 units must realize a nonzero motor-clamp event in at
   least one of their eight replicates; otherwise the motor component has not
   been manipulated and the gate is not tested.
4. For every policy × unit × axis row, at least 80 % of the 8 × 25 paired time
   points must be jointly alive. Below that threshold the short-horizon N5
   tracking statistic is not interpreted; the gate is not tested.

The probe completion manifest must bind the effects CSV by SHA-256 and contain
`pass_preflight=true` plus exact zeros for
`deterministic_repeat_max_abs_delta`, `invalid_starts`,
`escaped_reference_frames`, and
`cross_condition_initial_state_max_abs_delta`. The frozen analysis fails closed
if these conditions are absent.

## Effect table

Primary metric `phi` is mjlab `error_body_pos` in metres, reported as
millimetres. For replicate `r`, unit `u`, and axis `k`, compute

`S_r(u,k) = mean_t(phi_perturbed(t) - phi_base(t))`

over paired-alive frames in the fixed 25-step window. The recorded signed
effect is `S(u,k) = mean_r S_r(u,k)` with exactly eight replicates, matching
N5's replicate-mean signed statistic. Positive means the intervention worsens
tracking. The development vector is the three `S` values from the uniform
policy. The held-out targets are the corresponding signed `S` values from the
adaptive and grounded policies.

Paired-bootstrap 95 % intervals over the eight replicates, RMST/termination
regret, anchor-orientation error, contact-set/timing change, foot slip, work,
saturation, and joint-limit exposure are recorded as diagnostics only. They do
not enter the pass rule and cannot rescue it.

The analyzer requires exactly 126 unique rows (42 units × three named axes),
exactly eight replicates per policy, and the paired-alive threshold above.

## Frozen analysis

Analysis tool: `tools/analyze_newton_pred.py`, SHA-256
`1324aa6fcd7a97c95af6617b3c319b6c31878f7832cf2f08e488e7a6386863f2`.

All continuous variables are average-rank transformed. Axis indicators are
included in every model. For each held-out policy:

1. **Partial Spearman.** Residualize rank(`development_s_mm`) and
   rank(`heldout_s_mm`) separately on the seven frozen controls plus axis
   indicators by OLS; correlate the two residual vectors.
2. **Grouped predictive lift.** Fit ridge regression with fixed alpha 1.0 and
   leave one source clip out at a time. The baseline is the seven controls plus
   axis indicators. The augmented model adds three axis-specific development-S
   columns. Score each model by Spearman rho over all out-of-fold predictions;
   report `rho_augmented - rho_baseline`.
3. **Permutation baseline.** Run exactly 10,000 draws with NumPy seed
   `20260826`. In each source clip, reassign intact three-axis development
   vectors among its units, independently across clips. Recompute both
   statistics. The one-sided p-value is `(1 + count(null >= observed)) / 10001`.
   This preserves source-clip composition, unit counts, the three-axis
   dependence, outcomes, and all reference controls.

Raw per-axis Spearman correlations and the permutation p-value for the grouped
prediction lift are descriptive. There is no axis selection, sign flipping,
outlier deletion, or alternative feature subset after outcomes.

## Sealed decision rule

The gate passes only if all of the following hold:

- all instrument/manipulation checks pass;
- on the primary adaptive policy, partial Spearman rho is at least **+0.25**;
- its one-sided within-clip permutation p-value is at most **0.05**;
- its grouped leave-one-clip-out Spearman lift is at least **+0.05**; and
- on the grounded replication, both partial rho and grouped prediction lift
  are strictly positive.

The +0.05 prediction lift mirrors the atlas feasibility-feature SESOI. The
+0.25 partial-rho threshold demands a moderate residual association on a small
development panel rather than significance alone. Grounded is direction-only
because it is a replication across a changed support policy, not an additional
powered primary test.

Joint pass keeps G3 eligible for a later, separately sealed wiring screen; it
does not establish a training benefit. Any valid-data failure closes G3
permanently for this project. Thresholds will not be softened after inspection.

## Execution order and artifacts

1. Verify hashes and run the sealed analyzer's `--synthetic` pass/null/
   discordant dry-run. Save `reports/newton15_pred/SYNTHETIC.json`.
2. Implement/run the probe contract without changing this file or the frozen
   analyzer. Record the implementation SHA-256 in the probe manifest.
3. Only after the completion manifest passes, run the real 10,000-permutation
   analysis and write `reports/newton15_pred/result.json` plus a sentinel.
4. Record the measured verdict in `plan/STATUS.md` and
   `paper/RESULTS_LOG.md`, including a valid null.

Any necessary protocol change requires a dated addendum sealed before opening
the affected outcome. No GPU training, bank-wide repair, or G3 work is part of
this gate.
