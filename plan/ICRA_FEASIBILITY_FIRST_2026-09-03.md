# CLIMB feasibility-first ICRA direction and execution plan

**Date:** 2026-09-03
**Status:** working research plan. This file is not a seal and does not change any sealed result.

## Decision

The most promising next result is **G2 ALP versus G1 deployment-uniform on the identical exact
feasible support**, with treatment separation established before any confirmatory endpoint is
read. The primary endpoint is a liveness-weighted continuous TrackingScore on an outcome-blind
feasible-hard-reference partition. This is the shortest path to either:

- a positive training contribution—better precision at equal survival is allowed; or
- a definitive, useful null recommending the simpler exact-support G1 allocation in the tested
  setting.

The paper should be organized as one system with three evidence-bearing stages:

| pillar | role | defensible contribution now | missing evidence before a strong ICRA claim |
|---|---|---|---|
| **Screen (`refeas`)** | data ingestion | measured dynamic-feasibility audit; 2,442/10,705 clips exceed the fixed threshold for this AMASS / whole_body_tracking / G1 / flat-ground pairing; independent cross-implementation agreement panel | public metadata/license review; per-frame masks require the licensed payload |
| **Segment-native evaluation** | benchmark | fixed starts and horizons, paired seed/noise conditions, terminal-state reads, disjoint hash-bound panel, reference-only feasible-hard partition; validation-gated contact-event instrument | blinded manual contact labels and held-out validation result; final Phase-G condition/seal review |
| **Grounded curriculum** | training | exact hard support, explicit horizon truncation, true mixture floor, ALP attribution, TV/concentration gates | endpoint-blind treatment calibration, independent validation, then three confirmatory seeds |

This framing is stronger than “all fixes failed,” while retaining the result ledger: CLIMB
identifies where feasibility enters the pipeline, supplies conformance tests that prevent false
physics conclusions, and tests whether curriculum complexity adds value after support is clean.

## Page review

The local 2026-09-03 page candidate is the latest and strongest version. Its best material is the
causal chain—impossible reference → failure-adaptive exposure → collapse—and the visible
evidence/status discipline. The public GitHub Pages copy was still the older 2026-08-21 version
when last checked, so “latest” currently means the local candidate, not a deployed page.

Before using the page as the ICRA front door:

1. Lead with the three-stage feasibility-first system above, then show the audit history as the
   evidence that motivated each stage.
2. Keep “22.8%” scoped at first mention to this corpus/pipeline/robot/scene.
3. Replace generic “adaptive is worse” phrasing with the exact sampler and passed/failed
   manipulation gate.
4. Add the G2 result only after the Phase-G seal and readout; until then it stays pending.
5. Link the typed dataset candidate and the practitioner guide, but label the former as
   clip-level and license-review-pending.

## Experiment G: treatment before outcome

### G-cal. Endpoint-blind calibration

`plan/G2_CALIBRATION_GRID.json` freezes 12 combinations of exploration ratio and ALP floor.
Every candidate receives 50 PPO iterations on seed 20260903. Ledgers at iterations 30/40/49
are the only admissible selection inputs. `tools/calibrate_g2_treatment.py` selects the passing
candidate closest to TV 0.10 and validates it once on seed 20260904. It rejects undeclared fields
in the run map so evaluator results cannot enter through the calibration schema.
`tools/run_g2_calibration.py` launches only training and emits that narrow ledger map; its
`--dry-run` mode exposes every command before GPU use.

A final launcher audit found and closed a seed split: the environment variable previously seeded
the segment sampler, while mjlab's training entry point reset PPO and environment randomness to
its default 42. The runner, environment, and sampler now receive one explicit stage seed, and
the selector rejects ledgers in which the recorded seeds differ.

The actual update clock supports this duration: one PPO iteration collects 24 environment steps,
the sampler advances every 50 steps, and `W=10` fills after roughly 21 PPO iterations. Iteration
49 therefore contains about 14 adaptive sampler ticks, rather than a nominal pilot that remains
inside warm-up.

### G1/G2 confirmation

G0 was removed during the pre-seal comparator audit. The old command is uniform over clips and
then within clip, while G1 is uniform over legal starts; their contrast would change both
feasibility support and clip-duration exposure. Dropping it now follows the draft's first budget
drop and leaves one controlled sampling-allocation variable.

- support: the same 1,184 attribution units and 368,951 legal starts;
- control: G1 deployment-uniform over legal starts, not equal mass over variable-length units;
- treatment: the independently validated ALP setting;
- seeds: 1, 2, 3; 4,000 iterations; 512 environments;
- manipulation: mean TV in `[0.05, 0.15]`, effective units ≥12, top-1 ≤0.05, zero
  invalid/censored trials, final rank saturation <0.90;
- endpoint: feasible-hard-reference TrackingScore
  `h·exp(−MPKPE/0.30m)·exp(−anchor_angle/0.40rad)`, where `h` is the survived-horizon fraction;
- key decomposition: survival, all-panel TrackingScore, AULC, MPKPE, orientation, and mechanical
  work;
- contact timing: a fixed source-hash-bound proxy, 20-clip blinded validation panel, one-to-one
  ±40 ms scorer, and evaluator gate are ready; it remains exploratory unless held-out labels pass
  every gate before the seal.

The primary score scales come from the already-fixed G1 task rewards, not Phase-G outcomes. The
horizon multiplier closes the early-termination selection loophole. See the full draft contract
in `plan/PREREGISTRATION_G_SEGMENT.md`. The no-results table topology is fixed in
`paper/PHASE_G_RESULT_TABLE_SHELL.md` so failed gates and losing subgroups cannot disappear after
readout. Training ledgers now bind checkpoint and launcher hashes; evaluator sidecars bind the
checkpoint, task, condition manifest, evaluator, and active/common references; and
`tools/build_g_run_manifest.py` constructs the hash-complete input that the analyzer verifies
before parsing any endpoint row.

## Dataset, model, simulator, and Newton readiness

| component | status | evidence / blocker |
|---|---|---|
| clip-level dataset | **ready internally; public release blocked** | `datasets/amass_g1_feasibility_v1.parquet`: 10,705 typed rows, 18 columns, round-trip checked; adjacent manifest binds source/output hashes; 2,442 flags reproduce. The AMASS no-distribution term requires written permission or a documented legal determination before publication |
| per-frame feasibility masks | **blocked** | aggregate CSV cannot reconstruct masks; rerun `refeas` after the licensed 14 GB motion payload is restored, bind every mask to motion SHA-256 |
| G1 model | **ready** | preflight verifies the pinned MJCF SHA-256 `febdcbe…` |
| mjlab simulator | **ready** | mjlab 1.6.0 / MuJoCo + MuJoCo-Warp 3.11 / Warp 1.14 / Torch 2.9; actual 4-world, 5-step CUDA cartpole smoke passed |
| Newton | **ready as an instrument** | isolated Newton 1.5.0 / Warp 1.16 stack allocates on CUDA; measured two-unit recertification passes; its predictive gate failed, so G3 remains killed |
| Phase-G compact inputs | **ready** | exact unit table, 100-clip disjoint panel, 2,800 paired conditions, 25/75 outcome-blind strata, hash-complete evaluation provenance, analyzer and calibration synthetic tests |
| contact-timing instrument | **ready; validation pending** | fixed proxy builder, synchronized reference-only dual-view renderer, 10-development/10-held-out panel, source/model/tool hashes, per-foot event scorer, and evaluator gate pass synthetic/model/render tests; no force-plate truth is claimed and manual labels are absent |
| G2 calibration | **ready except payload** | finite 12-setting design, PPO/environment/sampler seed binding, ledger-only selector, independent validation, and training-only launcher pass synthetic/dry-run checks |
| Phase-G motion payload | **blocked** | `bank/amass` is absent; all 800 source motions must exist and match the unit-table hashes |
| Phase-G seal | **not yet allowed** | calibration result, contact-timing disposition, and current-hardware 512-env footprint remain open |

## Hardware-consequence bridge

The existing result is narrower than “actuator destruction”: on clip #44, closed-loop simulated
force saturation is 0 before support loss and peaks at a mean 16.8% of actuators in the fall
window; the reference audit measures median unsupported demand 328.6 N against 327.1 N robot
weight. These motivate a hardware-consequence experiment but do not establish over-current,
thermal damage, back-EMF limitation, or real-robot safety.

The next simulator protocol should compare raw #44, an excluded/screened deployment control, and
a fidelity-certified repaired reference under the same frozen policy/start conditions. The
actuator layer must include source-cited G1 parameters for continuous/peak torque, speed-dependent
torque, bus voltage/back-EMF, current limit, and an identified thermal model. Pre-register:

- peak and time-above-limit current per motor;
- time-above continuous and peak torque envelopes;
- winding temperature rise and thermal-limit crossing;
- mechanical work, electrical-energy proxy, support-loss time, and contact impulse;
- reference fidelity for repaired clips;
- a kill rule that forbids “safe/destructive” language if motor parameters are unavailable or
  unvalidated.

The official Unitree RL/MJLab constants provide four simulated motor classes with effort limits
25/88/139/5 N·m and velocity limits 37/32/20/22 rad/s. The official SDK safety helpers expose
default soft stops at 120 °C winding temperature, 85 °C casing temperature, and 10 rad/s joint
velocity. These are useful anchors, but neither source supplies the electrical/thermal parameters
needed to infer temperature or over-current from torque alone:

- <https://github.com/unitreerobotics/unitree_rl_mjlab/blob/main/src/assets/robots/unitree_g1/g1_constants.py>
- <https://github.com/unitreerobotics/unitree_sdk2/blob/main/include/unitree/robot/g1/common/terminations.hpp>

No physical G1 deployment is authorized by this plan. Hardware work needs an owner, a robot,
vendor limits, an emergency-stop procedure, and a separate safety approval.

## Positive framing of closed negative gates

- **Physics-fragility gate:** measured parameter interventions did not explain failure under the
  tested 480-world design. Say this bounds a tempting diagnosis; do not say it proves all
  out-of-distribution humanoid failures are not physics-sensitive.
- **Newton predictive gate:** the frozen three-axis vector did not add predictive value on the
  valid panel (`p=0.158`, LOCO lift `−0.006`). Say it demotes this metric to an instrument; do not
  infer that all cross-engine disagreement is integration artifact.
- **N7 repair gate:** the deployment contrast was +0.0397 but raw-reference policy transfer was
  −0.0036, with reference-only and interaction terms explaining the difference. Say the tested
  projection enabled reference/policy co-adaptation without demonstrated unchanged-reference
  skill transfer.

## Claim–evidence map for the manuscript

| claim | evidence status | artifact | allowed wording |
|---|---|---|---|
| feasibility defects can dominate a curriculum | measured + sealed sampler evidence | `paper/RESULTS_LOG.md`, N1/A7 artifacts | specific to the audited pipeline and sampler |
| the screen finds dynamic defects at scale | measured | `reports/feasibility_all/`, cross-implementation panel | 22.8% for this corpus/pipeline pairing |
| segment-native evaluation removes reset/start artifacts | measured harness evidence | paired-v2 conditions, S1 conformance ledger | protocol correction; benchmark contribution after packaging |
| grounded ALP improves robust tracking | pending | Phase G | no claim until gate passes and result is positive |
| exact-support uniform is the preferred default | pending conditional null | Phase G | only if both TrackingScore and survival null rules pass |
| infeasible references create realistic actuator harm | pending | new actuator protocol | no thermal/safety claim from force-range saturation alone |

## Immediate next action

Restore the licensed AMASS→G1 bank at `bank/amass`, then run:

```bash
source research.env
mjlab-1.6.0/.venv/bin/python tools/research_preflight.py \
  --g2-stage calibration --verify-motion-hashes --strict
```

If all blockers clear, build the fixed contact proxy and blinded reference renders, run the 12
calibration candidates at 50 iterations, select with `tools/calibrate_g2_treatment.py`, and
validate the one selection on seed 20260904. Copy only the validated sampler parameters into the
Phase-G draft; then record either a passing contact-instrument report or an explicit
exploratory-only disposition, measure the 512-env footprint, and seal. Do not launch
confirmation seeds or inspect Phase-G evaluator endpoints before those steps are complete.
