# Phase-G G2 treatment calibration result

**Status:** measured, endpoint-blind manipulation calibration; **ready to freeze**.
This is not a policy-performance result. No evaluator CSV, survival, reward, MPKPE,
orientation error, or TrackingScore was opened or supplied to the selector.

## Decision

Freeze G2 with learning-progress rank, exploration ratio **rho = 0.40**, progress
floor **lambda = 0.05**, progress window 10, difficulty power 0, unit cap 0.05,
and clip cap 0.25. This was the deterministic selection from the predeclared grid
and it passed the one permitted independent validation.

The screen used seed 20260903 and sampler ledgers at iterations 30, 40, and 49.
Two of 12 candidates passed every predeclared manipulation/safety gate. The
selector chose the passing candidate closest to the TV target 0.10.

| candidate (rho, lambda) | mean TV | TV SD | minimum effective units | maximum top-1 | final saturation | gate |
|---|---:|---:|---:|---:|---:|---|
| 0.05, 0.001 | 0.3825 | 0.0193 | 700.1 | 0.0072 | 0.2948 | fail |
| 0.05, 0.01 | 0.3054 | 0.0035 | 742.8 | 0.0079 | 0.2804 | fail |
| 0.05, 0.05 | 0.1692 | 0.0352 | 719.3 | 0.0113 | 0.2584 | fail |
| 0.10, 0.001 | 0.3638 | 0.0245 | 734.3 | 0.0075 | 0.2584 | fail |
| 0.10, 0.01 | 0.2879 | 0.0098 | 752.7 | 0.0122 | 0.2889 | fail |
| 0.10, 0.05 | 0.1653 | 0.0312 | 720.1 | 0.0144 | 0.2584 | fail |
| 0.20, 0.001 | 0.3106 | 0.0160 | 752.0 | 0.0089 | 0.2745 | fail |
| 0.20, 0.01 | 0.2483 | 0.0109 | 757.7 | 0.0087 | 0.2593 | fail |
| 0.20, 0.05 | 0.1443 | 0.0306 | 718.2 | 0.0131 | 0.2542 | pass |
| 0.40, 0.001 | 0.2316 | 0.0110 | 754.5 | 0.0078 | 0.2551 | fail |
| 0.40, 0.01 | 0.1906 | 0.0087 | 752.7 | 0.0113 | 0.2584 | fail |
| **0.40, 0.05** | **0.1079** | **0.0182** | **691.2** | **0.0154** | **0.2255** | **pass / selected** |

Every screen candidate had zero invalid starts, invalid reference frames, and
censored resets in the three decision ledgers. Exact values and per-checkpoint
TVs are in `reports/g_segment/calibration/result.json`.

## Independent validation

Seed 20260904 was run only for the selected candidate. Its checkpoint TVs were
**0.1292, 0.1045, and 0.0831** (mean **0.1056**, SD **0.0188**); minimum
entropy-effective units were **700.1**, maximum top-1 mass was **0.0134**, final
saturation was **0.2365**, and invalid/censored count was **0**. It passed every
gate, changing the selector status to `ready_to_freeze`.

## Resource and execution record

All 12 screen jobs completed with return code 0. Their elapsed times were 36--49 s
(median 37 s) and summed to **0.126947 sampled GPU-hours**. Sampled peak total
VRAM was 3,599--8,441 MiB (median 3,788.5 MiB); sampled peak delta was
2,278--7,254 MiB (median 2,416.5 MiB). One job carried the peak outlier; the
sentinel records it without assigning a cause. The selected independent validation
completed with return code 0 in 36 s (**0.010000 GPU-hours**), from 1,186 MiB
baseline to 3,598 MiB peak total (2,412 MiB delta).

The committed evidence is deliberately compact: the run maps, selector result,
and the 39 hash-bound decision ledgers. Local ONNX exports, checkpoints,
TensorBoard events, and launch logs total several gigabytes and are excluded.

## Reproducibility correction before freezing

The first generated run maps serialized absolute repository paths. Before any
seal, `tools/run_g2_calibration.py` was changed to serialize repository-relative
paths and `tools/calibrate_g2_treatment.py` was changed to resolve those paths
from the repository root. The two run maps were normalized mechanically. No
ledger byte changed: every ledger SHA-256 in the selector result is unchanged,
and rerunning the selector produced the same candidate and validation verdict.
The selector's synthetic endpoint-schema and seed-refusal tests still pass.

## Artifact contract

- design: `plan/G2_CALIBRATION_GRID.json`, SHA-256
  `c1eb9b757d2bf7f1e893fc646599d720a1750e4030624c5254fc3d70dde381de`;
- screen map: `reports/g_segment/calibration/screen_runs.json`;
- validation map: `reports/g_segment/calibration/validation_runs.json`;
- exact result and per-ledger hashes: `reports/g_segment/calibration/result.json`;
- selector: `tools/calibrate_g2_treatment.py`;
- training-only orchestrator: `tools/run_g2_calibration.py`.

The selector result binds the run-map hashes and every decision-ledger hash. The
calibrated pair may now be copied into the unsealed Phase-G preregistration.
Confirmation remains unauthorized until the contact-timing disposition is
recorded, the full preflight passes, the Phase-G seal is reviewed and written,
and explicit approval to run the confirmatory experiment is given.
