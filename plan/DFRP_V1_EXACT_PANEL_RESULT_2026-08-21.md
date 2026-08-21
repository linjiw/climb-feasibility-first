# DFRP v1 exact repair panel — result

**Date:** 2026-08-21
**Status:** unsealed measured CPU implementation result. **Frozen gate: PASS.**
This is not a policy-benefit, bank-wide recovery-rate, or hardware claim.

## Decision

Keep the strict repair-entry rule and the hash-bound exact-support contract.
Promote only the curated 26-clip view produced by this panel: 22 newly repaired
flagged clips and four byte-identical feasible controls. Do not promote the four
failed panel members or infer the panel's 84.6% result as a census recovery rate.

The next research gate is the isolated Newton v1.5 recertification described in
`plan/NEWTON_SEGMENT_DIRECTION_2026-08-21.md`. No GPU training is authorized by
this result.

## Frozen panel

The panel and decision rule were fixed in
`plan/DFRP_V1_EXACT_PANEL_2026-08-21.md` before execution. It contains 26
strict-flagged repair candidates and four source-matched controls. Flagged
candidates cover both rare legacy `<=2 cm` cases and four examples from each
cell of `{2–4, 4–6, 6–8 cm}` displacement × `{10–20%, >20%}` initial
infeasibility.

- selection payload: `900c2dbff2cfd709aefb9b308ac2980710efaa2a16c076206bda6fafe723a355`
- source census payload: `6b41fc24f31c9b5abc87d6683dbfd02c61059656eb45e1ea1339f61c3d332d34`
- selection: `reports/dfrp_v1_exact_panel/selection.json`

The pass gate required at least 20/26 exact-ready flagged clips, 4/4
byte-identical and ready controls, zero integrity/joint-limit/10 mm IK-residual
violations among admitted clips, and reproducible selection and manifest
payloads.

## Iteration ledger

| iteration | exact-ready flagged | controls byte-identical | result | disposition |
|---:|---:|---:|---|---|
| 0 | 22/26 | 1/4 | FAIL | Discarded. Repair entry was not enforced for feasible controls. Exact sidecars were not bound to the selected motion hash, allowing repaired support to masquerade as raw support; short feasible islands also left frames outside the support partition. |
| 1 | 22/26 | 4/4 | **PASS** | Kept. Enforced strict `infeasible_frac > 0.10` repair entry, source-motion sidecar binding, and a feasible/excluded partition over every frame. |

The failed baseline remains under `reports/dfrp_v1_exact_panel/baseline/` as an
apparatus audit. Its manifest payload is
`6896a5806b15ba3977d2c31cd054e5bf7e6fb604382db744aadefcd2db7c6542`.

## Frozen result

Iteration 1 admits **22/26 flagged clips (84.6%)** and **4/4 controls**. All
four controls are byte-identical no-ops. Among the admitted clips there are:

- zero manifest-integrity failures;
- zero joint-limit violations;
- zero repairs above the 10 mm contact-IK residual bound;
- 36 admissible exact units and **10,561 legal 50-step starts**.

Per-clip CPU repair and exact-screen runtime is 2.57 s median, 6.29 s p95,
and 18.50 s maximum. Across the 26 flagged candidates, the recorded p95-of-clip
fidelity diagnostics are 72.53 mm body MPJPE, 0.0202 rad joint delta, 75.57 mm
maximum root displacement, 1.210 m/s root-velocity delta, and 34.91 m/s²
root-acceleration delta. These are diagnostics, not acceptance thresholds, and
the large derivative changes remain a reason to require predictive and policy
gates before scale-up.

## Excluded flagged clips

| clip | before → after infeasible fraction | root offset | reason |
|---|---:|---:|---|
| `Transitions_mocap_mazen_c3d_punchboxing_walk_poses_120_jpos` | 0.1133 → 0.0517 | 19.0 mm | residual exceeds 5%; quarantine |
| `CMU_20_21_rory1_20_10_poses_120_jpos` | 0.2546 → 0.0833 | 32.6 mm | residual exceeds 5%; quarantine |
| `SFU_0005_0005_SideSkip001_poses_120_jpos` | 0.1460 → 0.0066 | 67.7 mm | 10.44 mm IK residual; qualification incomplete |
| `BMLmovi_Subject_47_F_MoSh_Subject_47_F_15_poses_120_jpos` | 0.1920 → 0.0000 | 72.8 mm | 51.44 mm IK residual; qualification incomplete |

These failures demonstrate why residual feasibility and geometric
qualification must remain separate gates. The latter two would look recovered
from infeasibility alone but are correctly withheld from training.

## Promoted artifact contract

- full 30-clip audit manifest payload:
  `ca505482ccda7b6d1096f054c8535eff58063bc78af34ed0ace1235427eec175`
- kept repair operator SHA-256:
  `40c367ad18894f6a7cf2ef83bc85d2765b68cbce9830dbe1d866417c32c597da`
- curated 26-clip manifest payload:
  `d2a733b983df011dd35a1987f2b2bc7bf1f82bbb17e3b6070f0514d5f2ff7218`
- exact unit-table SHA-256:
  `0df66390ceb6c9258c64c50bb4c31a9ee33d0412a3635d8dab72f0b789bdd2ff`
- machine-readable result:
  `reports/dfrp_v1_exact_panel/iter1/result.json`

The runtime verifies motion, screen, repair record, model, exact sidecar,
source-motion binding, DFRP payload, and unit-table identities before sampling.
A 100,000-draw CPU smoke used the real `SegmentSampler`: all 26 clips were
sampled, every draw was horizon-safe, probabilities summed to one, and the
unadapted distribution matched its reference exactly.

## Verification record

The kept result was checked by rebuilding both manifests and the unit table,
running the real sampler smoke, and validating all 26 materialized motions with
`tools/validate_motion_npz.py`. Focused tests, Python compilation, Ruff,
`git diff --check`, and the FGAS/N7 seal checks complete the local verification.
Exact commands and outcomes are recorded in
`autoresearch/autoresearch-260821-0115/research_log.md` and its handoff.
