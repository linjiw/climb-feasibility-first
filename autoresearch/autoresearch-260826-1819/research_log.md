# Fable Phase-N execution log — 2026-08-26

## Scope and invariants

- Goal: execute `fable.md` rev-2 Phase N-a through N-c without starting GPU training.
- The existing trainer environment was not modified; Newton 1.5 lives only in ignored
  `newton15/.venv`.
- Existing sealed files and manifests were not edited. One new predictive protocol was sealed
  before any 42-unit axis outcome was measured.
- The GPU remained occupied by a foreign process at 96% utilization, so no panel outcome was
  opened. Implementation and synthetic checks used the CPU window.

## Acceptance checks

| item | acceptance criterion | result |
|---|---|---|
| N-a isolated stack | Newton 1.5 / Warp / MuJoCo / MJWarp pins; trainer venv unchanged | pass: `plan/NEWTON15_PINS.md` |
| N-b exact-unit recert | easy + contact-rich unit; placement/obs/action/state/contact/timing pass; `|Δqdot| <= 3e-5`; repeat dispersion zero | pass: every measured delta zero in `reports/newton15_recert/result.json` |
| N-c seal timing | protocol hash recorded before any axis outcome | pass: `plan/PREREGISTRATION_NEWTON_PRED.md`, SHA-256 `b1773fc585a9a2ea064953712b74cbc2685c041619005d66e09d2e8b94254a4e` |
| frozen panel | exactly 42 admissible units and fixed 25-step midpoint windows | pass: `reports/newton15_pred/reference_features.csv`, SHA-256 `406ec4076402973a2bbd9644fb9e562760366a2427aaf311a3c89a844013c02e` |
| analysis dry-run | pass, valid-null, and discordant-replication branches decide as sealed | pass: `reports/newton15_pred/SYNTHETIC.json` |
| probe dry-run | signed N5 effect aggregation yields +10 mm on the constructed case | pass in both trainer and Newton 1.5 interpreters |

## Recertification iteration

The first Newton 1.5 port exposed four harness/integration issues rather than scientific solver
effects: a stale observation after exact-segment assignment; contact snapshots compared at
different integration phases; nonzero repeat noise until Warp `RUN_TO_RUN` determinism was enabled;
and a warm-start side effect from shadow probes. A field audit then found seven Newton-1.5 import
residuals across 44 mapped live-model fields. Mirroring replacement-ground geometry/contact bits,
the free-joint range, and actuator gain/bias/control-range fields reduced the audit to zero.

Before the final mirror, one canonical substep reached `|Δqdot| = 8.285e-5` and correctly failed.
After the mirror and warm-start restoration, 48 resynchronized substeps and the independent
0.24-second closed-loop diagnostic are exactly equal. Two independent same-seed rebuilds of each
stack have zero dispersion in observations, actions, state, contacts, and terminations.

Durable hashes:

- recert result: `d997af51d81aaf083446cf8790d7fea605bc100cc791305619b3bcedda82603d`;
- trajectory archive: `26cf4a097883d7a88253ee58fb00f60d08039e1ae3755a31b0f7c25be8ee9d0e`;
- completion sentinel: `2792529c08eb670b50795a955c957e051ecac84273ef5ca8a0fd6fe06e24c6df`;
- recert harness: `2d50a1d7dc1274bb1df351042609b8bd65a8a82c3e67522bc6a178c421840ac4`.

## Predictive-gate disposition

The sealed primary uses the uniform seed-1 checkpoint to construct a three-axis signed vector
(+20 ms delay, 85% motor-effort clamp, Newton vs MuJoCo contact generation). Adaptive seed 1 is
the sole primary held-out target; grounded seed 1 is a directional replication. The test controls
clip `infeasible_frac` and six window-local reference-kinematic features.

The gate requires adaptive partial Spearman at least +0.25, one-sided within-clip vector-permutation
`p <= 0.05`, grouped leave-one-clip-out Spearman lift at least +0.05, and positive partial/lift on
grounded. Failure on valid data means G3 never runs. A failed deterministic/manipulation check is
reported as not tested. The analyzer is frozen at SHA-256
`1324aa6fcd7a97c95af6617b3c319b6c31878f7832cf2f08e488e7a6386863f2`.

The unsealed probe implementation (`tools/newton15_pred_probe.py`, SHA-256
`994d48335cd60cda4452b16f30ade7213c34a71e79b9138a2f4a43b368e81284`) now enforces the sealed
starts/noise/axes, performs independent deterministic rebuilds, and writes the fail-closed manifest
expected by the analyzer. It has not run on the real panel.

## Keep/discard decision

Keep the final recertification artifacts, sealed N-c protocol, frozen reference table/analyzer, and
synthetic-validated probe implementation. Discard the interpretation of every pre-mirror fork as a
Newton result; those runs were integration diagnostics. Do not launch the real probe until GPU
utilization provides a genuine gap, and do not start G3 regardless of any diagnostic result unless
the sealed joint predictive gate passes.
