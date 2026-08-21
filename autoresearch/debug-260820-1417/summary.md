# FGAS/N7 training debug — 2026-08-20

Metric: completed checkpoints/evaluations, GPU liveness, and exact reconstruction
of `sampling_ineligible_mass`.

| hypothesis | test | result |
|---|---|---|
| FGAS stalled or crashed | processes, logs, sentinels, final artifacts | falsified: 3/3 seeds reached 3999/4000; analyzer and `COMPLETED` exist |
| GPU/driver failure stopped the run | `nvidia-smi`, timestamps, error scan | falsified: no CUDA/OOM/traceback; GPU idle only after completion |
| rejected-mass telemetry is wrong | reconstruct from final exposure ledgers + sidecars | falsified: maximum discrepancy 0.00211 |
| flat 0.10269 projection remains valid after adaptation | compare final reconstructed mass | falsified: final 0.265/0.244/0.201; late mean 0.199 |
| clip-mean soft eligibility is overwhelmed by persistent failure | contribution decomposition | confirmed: one 0.702-eligible clip receives 0.618/0.376/0.222 final mass |

Actions:

- Added `tools/diagnose_fgas_result.py` and `reports/FGAS_diagnosis.json`.
- Recorded the scoped sealed outcome in `plan/FGAS_RESULT.md` and synchronized status/paper/site.
- Preserved the frozen FGAS code and manifest unchanged.
- Launched sealed N7 bundle `reports/N7/_frozen/20260820T182037Z`; GPU utilization verified.

Decision: no runtime repair is needed. Do not rerun or relabel soft FGAS. A future
method must use eligible bins/segments as the adaptive unit and receive a new seal.
