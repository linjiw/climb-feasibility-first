# Next research checkpoint — exact-support learning-progress allocation

> The ICRA-oriented feasibility-first integration, endpoint revision, calibration design,
> dataset candidate, and actuator-bridge boundaries continue in
> `plan/ICRA_FEASIBILITY_FIRST_2026-09-03.md`.

**Status:** unsealed research direction and environment audit, 2026-09-03. This file does not
amend any sealed result. Endpoint-blind treatment calibration may run before the Phase-G seal;
confirmatory G1/G2 training may not.

## Verdict

The most promising next experiment is the **G2−G1 segment-native contrast**: learning-progress
allocation versus uniform allocation on the same exact feasible support. It is the smallest
test that resolves the intervention uncertainty left by the project. Newton is ready as a
reproducible simulator instrument, but it is not the next training direction: its sealed
no-training predictive gate failed on valid data, so G3 remains killed.

## Why this is the most promising direction now

The result would answer an unresolved causal question rather than add another correlated
difficulty feature. Recent primary work makes adaptive allocation a central design choice:
[GMT](https://arxiv.org/abs/2506.14770) balances easy and difficult motions, while
[EGM](https://arxiv.org/abs/2512.19043) allocates motion bins using tracking error and reports
sampling ablations alongside a broader architecture. The July 2026
[YAHMP empirical study](https://arxiv.org/abs/2607.19903) separately argues for controlled,
one-factor-at-a-time comparisons on the Unitree G1. CLIMB's next experiment asks a narrower
question those systems do not settle for this pipeline: after exact feasible support and the
evaluation lifecycle are fixed, does allocation by changing competence outperform uniform
allocation?

This is positioning from a targeted primary-source scan, not an exhaustive novelty review and
not evidence that G2 will work. Its attraction is falsifiability: a passed manipulation gate
followed by a confidence interval below the predeclared effect size would close the allocation
claim cleanly.

## Operational bottleneck

The first segment-native pilot fixed invalid starts, wrap teleports, outcome attribution, and
terminal evaluation, but its adaptive distribution was only 0.014 total variation from control.
Therefore its survival interval cannot distinguish “allocation has no value” from “the treatment
did not materially change allocation.” The explanation is measured for that pilot; whether a
learning-progress rank creates an informative treatment and improves policy learning is untested.

## Smallest contribution and falsifiable claim

Retain the Unitree G1 task, PPO, reward, exact 50-step support, caps, compute, and paired
evaluator. First calibrate the ALP exploration ratio and floor without evaluator access; in the
confirmation, change only the sampling allocation:

> Under the exact feasible Phase-G support, learning-progress allocation should create a
> predeclared distribution shift relative to deployment-uniform allocation and improve the
> liveness-weighted feasible-hard TrackingScore by at least 0.02.

The mechanism is not tested if TV does not enter `[0.05, 0.15]`, entropy-effective units fall
below 12, any invalid/censored mass appears, top-1 mass exceeds 0.05, or the conditional
estimates saturate. With the manipulation gate passed, the result is a clean allocation null
only when the TrackingScore interval excludes +0.02 and the survival interval excludes +0.05.
The pre-seal comparator audit removed G0 because its uniform-over-clips allocation differs from
G1's uniform-over-legal-starts allocation; a G1−G0 contrast would confound support hygiene with
clip-duration exposure. Phase G now spends compute only on the controlled G2−G1 comparison.

## Experiment card

| Field | Decision |
| --- | --- |
| Scientific question | Does adaptive allocation help after feasibility/support are held exact? |
| Changed variable | G2 learning-progress rank versus G1 uniform deployment mass; all other task and PPO settings fixed |
| Setting and split | 1,184 admissible units / 368,951 legal starts for training; 100 hash- and name-disjoint clips, 2,800 full-window conditions for evaluation |
| Primary outcome | G2−G1 feasible-hard `h·exp(−MPKPE/0.30m−anchor_angle/0.40rad)` at iteration 3,999; SESOI +0.02; seed×clip hierarchical bootstrap |
| Replication | Endpoint-blind 12-setting calibration on seed 20260903; independent validation on seed 20260904; confirmation seeds 1, 2, 3 only after validation and sealing |
| Manipulation | Mean TV `[0.05, 0.15]`; entropy-effective units ≥12; top-1 ≤0.05; invalid frames and censored resets =0; saturation <0.90 |
| Provenance | Every evaluator CSV, metadata sidecar, policy checkpoint, training ledger, condition manifest, active/common reference hash map, and code entrypoint must match before endpoint rows are parsed |
| Quality guard | Common-survivor MPKPE, anchor-orientation error, and work within the predeclared 10% noninferiority margin |
| Interpretation | Positive, clean null, inconclusive, or not tested exactly as drafted in `PREREGISTRATION_G_SEGMENT.md` |

## Readiness audit

| Component | Current state | Evidence / action |
| --- | --- | --- |
| MJLab simulator | ready | v1.6.0 worktree imports; MuJoCo/MJWarp 3.11.0; CLIMB tasks register; a 4-env/5-step CUDA smoke has finite rewards; synthetic Phase-G analyzer passes |
| Unitree G1 model | ready | `g1.xml` SHA-256 `febdcbeffbbf84051556ae41a5ac1b43fb479a5d76bdb3f54824dbc2721c20aa` |
| Newton | ready as instrument | isolated Newton 1.5.0 / Warp 1.16.0 stack imports and allocates on CUDA; measured two-unit recertification PASS |
| Newton curriculum feature | closed | sealed predictive gate FAIL on 40 valid units; G3 must never run |
| Phase-G compact inputs | ready | committed exact unit table, 800 sidecars, 100-clip panel, and 2,800-condition manifest pass structural checks |
| Feasible-hard endpoint | ready | reference-only demand ranking creates a hash-bound 25/75 panel split; survival-weighted analyzer and six synthetic decision/provenance branches pass |
| Evaluation provenance | ready | training ledgers bind checkpoint/launcher hashes; evaluator sidecars bind checkpoint/task/conditions/references; `tools/build_g_run_manifest.py` creates the fail-closed analyzer input without parsing outcomes |
| Contact-timing instrument | ready; real validation pending | fixed kinematic proxy builder, reference-only dual-view renderer, balanced outcome-blind 10-development/10-held-out panel, immutable manifests, one-to-one ±40 ms scorer, and evaluator validation gate pass synthetic/model/render tests; no manual labels exist, so the metric remains exploratory |
| G2 calibration | ready except payload | 12-setting finite design, PPO/environment/sampler seed binding, ledger-only selector, independent validation, and training-only launcher pass synthetic/dry-run checks |
| Training launcher | ready for explicit rank | `CLIMB_SEGMENT_RANK`, numeric sampler contract, and configurable checkpoint interval reach the command configuration; regression tests added |
| Clip-level release candidate | ready internally | typed 10,705-row Parquet and manifest reproduce the aggregate screen; AMASS license review blocks public distribution |
| Motion payload | **blocked** | the licensed AMASS→G1 `.npz` bank is absent from this checkout and no hash-matching copy was found under `/home/linjiw` |
| Historical policy checkpoints | optional / absent | ignored checkpoint files are absent; only historical reruns need them, while Phase-G G1/G2 train from scratch |
| Seal | open by design | calibration may run unsealed; review the calibrated contract, contact-timing disposition, and 512-env footprint before confirmation |

Last verified on this machine, 2026-09-03: **16 checks passed, four warnings, one blocker** for
the calibration stage. The sole blocker is the licensed motion payload. Warnings cover the
pending real contact-timing labels, the deliberately absent confirmation seal, and the optional
historical policy checkpoint, plus the currently busy shared GPU. It was at 62% utilization with
8,369 MiB free during this check; availability is a point measurement, not a reservation.

The blocker-resolution contract is now explicit in
`plan/NEXT_STAGE_PAYLOAD_INTAKE_2026-09-03.md`. Calibration requires the 800 hash-bound training
motions; full confirmation requires those plus 100 hash- and name-disjoint evaluation motions,
for 900 unique identities. `tools/restore_phase_g_bank.py` validates a researcher-supplied local
directory before optionally creating the ignored `bank/amass` symlink. It does not download,
copy, or substitute motion data.

Newton 1.5.0 remains the evidence-bound environment. The official
[Newton changelog](https://github.com/newton-physics/newton/blob/main/CHANGELOG.md) lists 1.5.1
as released on 2026-08-27, after the project pin. Do not silently upgrade the measured stack:
any future Newton 1.5.1 use needs a separate environment and recertification. The local 1.5.0
stack is ready for reproducing the recorded instrument checks.

Run the machine-readable audit with:

```bash
mjlab-1.6.0/.venv/bin/python tools/research_preflight.py \
  --g2-stage calibration --strict
```

The sealed `tier_800` list can be reconstructed without inventing data because its exact source
order and hash are already bound inside `reports/g_segment/unit_table.json`:

```bash
mjlab-1.6.0/.venv/bin/python tools/research_preflight.py --materialize-clips
```

After the licensed bank is restored, add `--verify-motion-hashes`; all 800 calibration identities
must pass before a calibration launch, and all 900 full-scope identities must pass before the seal
or confirmatory training. The ignored local `research.env` is ready to source;
`research.env.example` is the shareable template. The preflight treats a missing or changed G2
contract as a blocker. The local GPU is shared, so a passing preflight is not ownership; launch
remains routed through `tools/run_when_free.sh`.

## Corrected resource estimate

The exploratory pilot measured 2,457,600 transitions for 200 iterations at 512 environments,
or 12,288 transitions per iteration. Therefore one 4,000-iteration arm is **49,152,000
transitions**. At the observed approximately 10,000 transitions/s, the training-only estimate is
approximately **1.37 GPU-hours per arm**, before startup, evaluation, retries, and contention.
The two-arm, three-seed confirmation is 294,912,000 transitions and approximately 8.2
training GPU-hours at that unverified pilot throughput; G0's removal avoids another 147,456,000
transitions and three confounded training runs.
The earlier 1.05-billion / 29-hour estimate multiplied by 512 twice and is corrected in the
unsealed Phase-G draft.

## Project-page review

`docs/index.html` and `docs/segment-native.html` were rendered at 1440 × 1100 and 390 × 844.
The hierarchy, statistics, navigation, and responsive layouts remain readable, and every local
link resolves. The revised home page leads with the three-stage feasibility-first system; the
segment-native page presents the endpoint-blind calibration and continuous endpoint without
promoting G2 as a result. Newton remains an instrument, G3 is closed, and G2−G1 is pending. This
review is of the local 2026-09-03 candidate. The public GitHub Pages site still serves the
2026-08-21 version; publishing requires the normal reviewed commit/push workflow.

## Verification record

```text
python -m pytest -q  # CLIMB launch variables cleared
1155 passed, 10 warnings

MJLab CUDA/MJWarp cart-pole smoke
4 environments, 5 steps, finite rewards: PASS

python tools/analyze_g_segment.py --synthetic --out /tmp/climb_g_segment_synthetic.json
positive / null / inconclusive / low-TV / wrong-seed / wrong-provenance branches: PASS

python tools/validate_contact_proxy.py --synthetic
validated / failed-validation / insufficient-support branches: PASS

contact-label MuJoCo kinematics smoke
G1 nq=36, nbody=31, seven collision geoms per foot, four-frame mask: PASS

reference-only dual-view renderer smoke
four 50 Hz frames, headless H.264 encode: PASS

python tools/calibrate_g2_treatment.py --synthetic \
  --out /tmp/climb_g2_calibration_synthetic.json
selection and independent-validation branches: PASS

newton15/.venv/bin/python tools/newton15_recert.py --synthetic \
  --out /tmp/climb_newton15_synthetic.json
passing, failing, and deterministic-repeat comparator branches: PASS

python tools/research_preflight.py --g2-stage calibration \
  --verify-motion-hashes --strict
16 ok, 4 warnings, 1 blocker (licensed bank absent; shared GPU at 62%; expected fail-closed result)

git diff --check
PASS
```
