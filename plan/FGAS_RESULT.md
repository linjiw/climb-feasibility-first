# FGAS result — soft guard-0 eligibility

**Read out:** 2026-08-20, only after `reports/FGAS/COMPLETED` existed. The
registration and frozen implementation remain unchanged (`plan/PREREGISTRATION_FGAS.md`,
`plan/FGAS_FREEZE.sha256`).

## Completeness and runtime integrity

All three seeds reached iteration 3999/4000 and produced final checkpoints. Each
final heldout CSV has 100 motion rows; all six hard20 stratified CSVs have the
expected 160 data rows. No traceback, CUDA error, OOM, NaN report, or killed
process appears in the train/eval logs. The GPU became idle because the complete
launcher reached its analyzer and wrote the sentinel, not because training stalled.

## Frozen readout

| rule | result | verdict |
|---|---:|---|
| feasible-hard20 survival | 0.7586 → 0.7390; Δ **−0.0196**, seed×motion bootstrap 95% CI [−0.0497,+0.0134] | primary benefit fails |
| feasible heldout survival | 0.8586 → 0.8462; Δ **−0.0123**, CI [−0.0452,+0.0200] | no-regression gate passes |
| late top-1 flagged / top-1 mass | 0.861 / 0.501 | attractor gate fails |
| late hard-rejected start mass | **0.199** (seed means 0.218/0.204/0.176) | `<0.15` implementation gate fails |

The sealed analyzer therefore records no performance benefit and
`failed_or_harmful`. Because the implementation gate fails, the scoped scientific
reading is narrower: **this clip-mean soft-mask formulation is not validated and
does not establish whether a stronger segment-native FGAS works.**

## Post-outcome diagnosis

`tools/diagnose_fgas_result.py` reconstructs final rejected-start mass from the
frozen exposure ledgers and sidecars within 0.0022 of the logged values. The
telemetry is therefore genuine, not an accounting defect. The flat pre-training
projection was 0.10269, but it was not a bound under failure adaptation.

One partially eligible motion (`Eyes_Japan_Dataset_kawaguchi_gesture_etc-39-giant_baba…`)
retains soft eligibility 0.702 yet receives final sampling mass 0.618/0.376/0.222
across seeds. It alone contributes 0.194/0.118/0.070 rejected-start mass. A
clip-mean multiplier is too weak once a persistent failure signal concentrates.

The already-declared hard-bin apparatus counterfactual makes rejected **start**
mass exactly zero, but it can correctly retain a clip-level flagged leader because
the method preserves that clip's feasible segments. Thus `P(top-1 clip flagged)`
is not a valid general mechanism target for a segment-native follow-up.

## Next method iteration

Do not relabel or rerun this arm. A follow-up must be separately sealed and make
eligible bins/segments—not whole clips—the adaptive unit, exclude invalid failures
from the prioritization signal, and measure rejected exposure directly. The hard
start-mask ablation may be run as exploratory apparatus but must not be pooled with
the completed soft primary.
