# Newton 1.5 exact-unit recertification result

**Date:** 2026-08-26 EDT  
**Status:** unsealed measured conformance result; not a policy-benefit claim  
**Verdict:** **PASS**

Newton 1.5.0 reproduces the pinned mjlab/MJWarp stack on one easy and one
contact-rich exact DFRP v1 unit after the live model is mirrored. Placement,
first observation, first action, canonical-state evolution, contact timing,
termination timing, and deterministic-repeat checks all pass. This completes
Phase N-b; it does not measure the Newton predictive gate and does not authorize
G3.

## Bound inputs

- Stack pins and isolation proof: `plan/NEWTON15_PINS.md`.
- DFRP v1 unit-table file SHA-256:
  `b91e6342049dea90410052e75ccbe5d450887c102ea90812a23d5204e7cd4c48`.
- Unit-table payload SHA-256:
  `0df66390ceb6c9258c64c50bb4c31a9ee33d0412a3635d8dab72f0b789bdd2ff`.
- Frozen segment-v2 pilot checkpoint SHA-256:
  `84da3b706ad344efc8cf77423e1c540c4e74d7eea5122b6c83338498ec25075b`.
- Deterministic unit selection:
  `reports/newton15_recert/UNIT_SELECTION.json` (SHA-256
  `0b5df36c2495800c3873eaae4fe5c1a8fc0df3ea1935a3ac0097b7be5acaf860`).

The easy unit is DFRP table index 33 / unit 34, a raw-feasible BMLhandball
segment starting at frame 75. The contact-rich unit is table index 28 / unit
29, repaired `KIT_513_seesaw_up02` starting at frame 150, with non-foot contact
candidates throughout its 50-frame selection window.

## Protocol

The harness runs 12 control steps (0.24 s; 48 physics substeps) on two exact
units. The stock arm records the frozen policy's canonical action stream.
Newton independently computes the first action for the action check and then
replays the stock stream. The S1 state gate resynchronizes every physics probe
from the stock canonical `(q, qdot, constraint warm start, ctrl)` tuple. Both
stacks use Warp `RUN_TO_RUN` determinism with the G1 model-derived 630-record
bound. Two complete same-seed rebuilds per stack must be byte-identical.

Contact timing is checked twice: exact internal solver contact sets at every
resynchronized substep and a common post-control mjlab observer. This avoids
comparing Newton's pre-integration contact buffer to mjlab's post-forward
buffer, which was an early discarded harness error.

## Six checks

| check | measured value | gate | result |
|---|---:|---:|---:|
| placement | max `|Δq| = 0`, max `|Δqdot| = 0` | both ≤ `1e-7` | pass |
| first observation | max absolute delta `0` | ≤ `1e-6` | pass |
| first action | max absolute delta `0` | ≤ `1e-6` | pass |
| canonical-state evolution | max `|Δq| = 0`, max `|Δqdot| = 0` over 48 paired substeps | `1e-5`, `3e-5` | pass |
| contact + termination timing | exact solver and observer contact sets; exact termination vector | exact | pass |
| deterministic repeats | zero delta for observations, actions, states, contacts, and terminations in both stacks | zero dispersion | pass |

The matched 0.24 s closed-loop diagnostic is also exactly equal after the final
warm-start restoration fix; it is recorded but is not substituted for the
per-substep S1 gate.

## Newton 1.5 integration residuals

The pre-mirror audit found seven non-visual live-model mismatches across 44
mapped fields: replacement-ground `geom_size`, `geom_contype`, and
`geom_conaffinity`; inactive/free-joint `jnt_range`; and
`actuator_gainprm`, `actuator_biasprm`, and `actuator_ctrlrange`. The actuator
import residuals reached `4.5776e-5` in gain/bias and `4.2915e-6` in control
range. Mirroring these fields and recomputing MJWarp constants reduces the
44-field mapped audit to zero mismatches. Before that fix, one easy-unit
canonical substep reached `|Δqdot| = 8.285e-5` and correctly failed the frozen
`3e-5` gate.

Two other discarded harness errors reproduced documented G0 classes: a stale
first observation after `assign_segments()`, and a contact comparison made at
different integration phases. Neither discarded run is treated as a Newton
outcome.

## Artifacts and reproduction

- Result: `reports/newton15_recert/result.json` (SHA-256
  `d997af51d81aaf083446cf8790d7fea605bc100cc791305619b3bcedda82603d`).
- Trajectories: `reports/newton15_recert/trajectories.npz` (SHA-256
  `26cf4a097883d7a88253ee58fb00f60d08039e1ae3755a31b0f7c25be8ee9d0e`).
- Completion sentinel: `reports/newton15_recert/COMPLETED.json` (SHA-256
  `2792529c08eb670b50795a955c957e051ecac84273ef5ca8a0fd6fe06e24c6df`).
- Harness: `tools/newton15_recert.py` (SHA-256
  `2d50a1d7dc1274bb1df351042609b8bd65a8a82c3e67522bc6a178c421840ac4`).
- Synthetic comparator dry-run: `reports/newton15_recert/SYNTHETIC.json`.

```bash
newton15/.venv/bin/python tools/newton15_recert.py \
  --selection reports/newton15_recert/UNIT_SELECTION.json \
  --unit-table reports/dfrp_v1_exact_panel/iter1/unit_table.json \
  --bank reports/dfrp_v1_exact_panel/iter1/repaired \
  --checkpoint reports/segment_v2_pilot/training/segment_v2_pilot/2026-08-20_23-21-07_uniform-penalty10-pilot200-s20260820/model_199.pt \
  --out reports/newton15_recert/result.json \
  --probe-steps 12 --repeats 2 --device cuda:0
```

## Consequence

Phase N-c may proceed only under a sealed no-training predictive-gate protocol.
No Newton axes have been measured on that development panel yet. The kill rule
remains unchanged: failure of the predictive gate makes Newton an analysis
instrument only, and G3 never runs.
