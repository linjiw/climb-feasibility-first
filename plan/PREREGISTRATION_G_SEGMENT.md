# Pre-registration (DRAFT) — Phase G: one causal test of segment-native allocation

**Status:** DRAFT, **unsealed and seal-ready pending approval**. Written 2026-08-27 on CPU;
updated 2026-09-04 after the Newton N-c result, a launch-readiness audit, the feasibility-first
narrative review, a bounded primary-source curriculum scan, and the endpoint-blind G2
calibration plus independent validation.
Target seal date **2026-09-10**. Confirmatory training is not authorized until the seal hash
exists in `plan/G_SEGMENT_FREEZE.sha256` and every item in §9 is closed. The endpoint-blind
calibration explicitly defined in §3 may run unsealed after the licensed bank passes hash
verification because its launcher cannot invoke the evaluator.
**Role:** the Phase-G seal called for in `fable.md` §3/§8.3. It covers the seed-1 manipulation
gate inside a three-seed confirmation of two arms. G3 (Newton fragility-weighted sampling)
is **not** part of this document: the sealed N-c gate failed on valid data, so G3 must never
run (`plan/NEWTON_PRED_RESULT.md`).

## 1. Question and why it is the one worth GPU

Every prior intervention arm in this project either changed nothing the policy could convert
(E-HYG), failed its wiring gate (FGAS soft), moved the reference rather than the policy (N7), or
was uniform wearing an adaptive label (segment-v2 pilot, TV 0.014). No arm has yet tested
**whether adaptive allocation over an exact feasible support helps**, because no adaptive arm
has passed a manipulation check. This document tests exactly that, with the manipulation check
sealed *before* the endpoint and evaluated *before* the endpoint is opened.

One controlled contrast:

| contrast | meaning | status if positive | status if null with gate passed |
|---|---|---|---|
| **G2 − G1** (primary) | ALP allocation over identical exact support, on a continuous tracking score | first positive intervention result | "ALP allocation does not materially help once hygiene is exact" — a bounded design result |

**Pre-seal comparator correction (2026-09-03):** G0 is removed. Its command samples clips
uniformly and then frames uniformly within clip, whereas G1 is uniform over legal starts and
therefore allocates clip mass in proportion to admissible duration. A G1−G0 contrast would change
both support hygiene and cross-clip exposure, so it cannot isolate either mechanism. This is the
already-declared first budget drop, exercised before Phase-G outcomes exist. The sealed E-HYG
result remains historical context, not a Phase-G comparator.

## 2. Arms

| arm | support | sampler | invariants |
|---|---|---|---|
| G1 | exact feasible 50-step trials built from `tier_800` guard-0 sidecars (`reports/segments_v2_tier800_guard0/`) with `tools/build_segment_unit_table.py` | deployment-uniform over all 368,951 legal starts; the 1,184 units are attribution strata, not equal-mass atoms | exact support mask; explicit truncation; zero invalid starts |
| G2 | identical unit table and deployment prior to G1 (same file hash) | `segment_sampling_mode="adaptive"` with the **learning-progress rank** of §3 | endpoint-blind calibrated exploration **rho = 0.40** and progress floor **lambda = 0.05**; unit cap 0.05; clip cap 0.25; stable unit attribution |

Both arms: 4,000 iterations, 512 envs, identical PPO configuration, identical environment seed
per training seed, failure penalty as in the segment-v2 pilot (−10). Seeds for confirmation:
**1, 2, 3** (`CLIMB_SEGMENT_SEED` = PPO seed = environment seed = sampler seed per arm). Seed 1
is the early confirmation manipulation gate; calibration instead uses the isolated seeds
20260903 and 20260904 from §3.

The unit table used by G1/G2 is built: `reports/g_segment/unit_table.json` — 800 clips,
1,841 source units, **1,184 admissible 50-step units, 368,951 legal starts** (657 short units
discarded); file SHA-256 `a98c48541fbc4aa4627d9b24c5a08e9e67f0d6bc9bb94103da57313b94766739`, payload SHA-256
`a52a668e5570c24e01a1af821164cbd19a38a3cd9007f245f78494ce11af9606`. Its sidecars
(`reports/g_segment/sidecars_guard0/`, 800 files) were reduced by `tools/screen_segments.py`
(SHA-256 `993c448af3185f955bea7f7718c1849837b7d9957366bbf3d8fcd618f208915b`) at guard 0 s / symmetric / min-seg 0 / bin 50 / severe / real model from
full-mode per-frame screens: the 99 flagged clips' existing screens
(`reports/segments_tier800/full/`) and **701 new full-mode screens of the unflagged clips**
(`reports/g_segment/screen_full/`, `n1_knee_id.py --gap 0.06`, μ 0.6). The 99 legacy sidecars
reproduce with zero field mismatches. **Finding:** 140 of the 701 unflagged clips contain at
least one severe window at guard 0 — the FGAS-era `tier_800_assumeunflagged_guard0_bin50`
eligibility (which treated unflagged clips as fully feasible) was not exact. G1/G2 use the exact
table. The eight-clip N7 overlap must not recur: the evaluation panel of §5 is
already hash-verified disjoint from `tier_800` and every other list an arm can see.

## 3. The G2 rank (must be named exactly, because this is what sank every earlier arm)

**Retired:** conditional failure rate as the sole rank. It saturates near 1 on an exact support
(pilot: 0.014 TV from uniform) and rewards unlearnable units.

**Primary rank — absolute learning progress (ALP).** The sampler already maintains a fixed-clock,
Beta-smoothed conditional success estimate per unit, `s_u(k)`, at sampler clock `k`
(`climb/segment_curriculum.py::conditional_failure_rate`, prior 0.5 / strength 2). Define, with
window `W = 10` sampler clock ticks,

    LP_u(k) = | s_u(k) − s_u(k − W) |            (absolute learning progress, Matiisen et al. 2017 / ALP-GMM form)

and the focus term `focus_u ∝ base_u · (LP_u + λ)`. `difficulty_power` is **0** in G2 (the
failure rate enters only through `s_u`, never as a multiplicative rank). Exploration `ρ` mixes
the G1 deployment prior back in; the unit/clip caps are enforced exactly as in
`_apply_probability_caps`. During the first `W` ticks ALP is undefined and the sampler equals
G1. With 24 environment steps per PPO iteration and a 50-step sampler clock, the first adaptive
distribution occurs during iteration 20–21; a 50-iteration calibration therefore exercises
roughly 14 post-warm-up clock ticks.

**Treatment-strength calibration, before the seal.** The finite grid in
`plan/G2_CALIBRATION_GRID.json` crosses `ρ ∈ {0.05, 0.10, 0.20, 0.40}` with
`λ ∈ {0.001, 0.01, 0.05}`. Each candidate runs exactly 50 PPO iterations on calibration seed
20260903 through `tools/run_g2_calibration.py` and writes manipulation ledgers at iterations
30, 40, and 49. No evaluator CSV,
survival, reward, or tracking endpoint may enter the calibration run map. Among candidates that
pass the safety checks of §4, `tools/calibrate_g2_treatment.py` deterministically selects the
candidate closest to TV 0.10, then lowest across-ledger TV standard deviation, then listed grid
order. That one candidate is repeated once on independent calibration seed 20260904. Only a
passing validation can be copied into this document and frozen. A failed validation returns the
project to design; it does **not** license trying candidates against confirmatory endpoints.

**Measured calibration result (2026-09-04; manipulation only, no policy endpoint read).**
Two of 12 screen candidates passed. The deterministic selector chose `rho040_floor0050`
(rho = 0.40, lambda = 0.05): screen checkpoint TVs 0.1310/0.1063/0.0865, mean 0.1079,
SD 0.0182. The only permitted independent validation, seed 20260904, passed with TVs
0.1292/0.1045/0.0831, mean 0.1056, SD 0.0188, minimum 700.1 entropy-effective units,
maximum top-1 mass 0.0134, zero invalid/censored events, and final saturation 0.2365.
The exact 12-row decision, run-map hashes, and per-ledger hashes are in
`reports/g_segment/calibration/result.json` and
`plan/G2_CALIBRATION_RESULT_2026-09-04.md`. These values select treatment strength only;
they are not evidence of policy benefit.

The uncertainty rank remains implemented for prior diagnostics but is no longer a Phase-G
fallback. No rank, power, window, floor, cap, or candidate outside the grid is admissible after
calibration begins. Confirmation seeds 1, 2, and 3 are not calibration seeds.

**Implementation status (updated 2026-09-04):** both ranks are implemented as
`SegmentSampler(rank="learning_progress" | "uncertainty", progress_window=10, progress_floor=0.01)`
in `climb/segment_runtime.py`, plumbed through
`SegmentNativeMotionCommandCfg.segment_rank / segment_progress_window / segment_progress_floor`
in `climb/segment_command.py`. `difficulty_power ≠ 0` with a non-failure rank
is a launch error. The success-rate ring buffer round-trips through `state_dict` and the
sampler-equivalent resume test covers it (`tests/test_segment_runtime.py`, 10 tests). The ledger
records the rank, all calibrated parameters, caps, TV, concentration, saturation, sampler seed,
and PPO/environment training seed so the selector can reject a mismatched launch rather than
trusting directory names. Both seeds must equal the declared stage seed. This closes the launcher
gap found on 2026-09-03: `CLIMB_SEGMENT_SEED` previously reached the sampler but the mjlab
training entry point replaced the environment seed with the PPO default seed 42.
The default rank remains `failure`, so the pilot's behaviour is unchanged.

**Exploratory sampler diagnostic (no decision role).** At every post-warm-up G2 ledger,
report Spearman rank agreement among the raw ALP score, conditional failure `1-s_u`, and the
competence-frontier score `s_u(1-s_u)`. The ledger records `s_u` and ALP before the floor,
exploration mixture, or probability caps. The diagnostic has no threshold, adds no arm, and
cannot change calibration selection, the manipulation gate, or the Phase-G verdict. It asks
whether the treatment is following changing competence or approximately reconstructing one of
two established allocation heuristics; it does not establish why either ranking succeeds.

**Launch plumbing audit (2026-09-03; calibrated profile recorded 2026-09-04):**
`tools/climb_segment_train.py` now reads the explicit
training seed, rank, difficulty power, exploration, window, floor, cap, and calibration
save-interval settings and passes them through
`climb/segment_env_cfg.py` into both registered segment tasks. `research.env.example` records the
selected G2 confirmation profile while retaining the seal and approval warning. The future seal
binds both launcher files; a readiness check blocks if
the G2 environment is absent or differs from the draft contract.

## 4. Manipulation gates — calibration first, confirmation before endpoint readout

For the 50-iteration calibration, ledgers 30/40/49 must satisfy **all** of:

1. mean TV in **[0.05, 0.15]**, with every individual ledger in [0.025, 0.20];
2. entropy-effective unit count ≥ 12 and top-1 unit probability ≤ 0.05 at every ledger;
3. invalid starts, invalid reference frames, and censored resets all equal zero; and
4. final conditional-rate saturation fraction < 0.90.

The selected setting must pass these rules on the independent validation seed. This is a
manipulation calibration, not a policy-performance pilot.

For the 4,000-iteration confirmation, warm-up = the first 400 iterations. Over every sampler
ledger checkpoint (`model_N_segment.json`) after warm-up, G2 must satisfy **all** of:

1. mean `sampling_adaptation_total_variation` (TV between G2's realized unit distribution and
   the G1 deployment-uniform distribution over legal starts, aggregated by unit)
   **∈ [0.05, 0.15]**;
2. entropy-effective unit count **≥ 12** at every post-warm-up checkpoint, and top-1 unit
   probability ≤ 0.05 by construction (a cap violation is a launch error, not a soft fail);
3. realized invalid starts, invalid reference frames, and censored resets all **= 0** (exact
   support makes these checkable; a nonzero value is a wiring bug);
4. conditional-rate saturation check: fewer than 90 % of admissible units have `s_u` outside
   (0.05, 0.95) at the final checkpoint — otherwise the rank had nothing to rank and the arm is
   reported as not tested, exactly like the pilot.

Gate failure on confirmation seed 1 → **stop; do not launch seeds 2–3**. Return to a new,
explicitly labelled experiment design; do not reopen this analysis. Gate failure is reported as
**not tested**, never as a null.

G1 has its own control check: TV from its declared uniform distribution < 0.01.

## 5. Evaluation

- Evaluator: `tools/eval_paired_v2.py` (paired v2; frozen condition manifest; auto-reset off
  for terminal reads; joint-noise seed fixed). The condition manifest is built once before
  sealing from the panel below and bound by hash; `eval_paired_v2` validates it byte-exactly.
- Panel: `reports/g_segment/panel/panel.txt` — 100 clips, 23.4 min, drawn outcome-blind from
  `bank/tiers/clean.txt` with `frames ≥ 250`, `infeasible_frac ≤ 0.10`, `airborne_frac ≤ 0.10`
  (NumPy seed 20260827); verified disjoint **by name and by motion-file SHA-256** from
  `tier_800`, `tier_800_pruned`, `tier_800_flagged99`, `tier_mixed100`, `heldout100`, the DFRP
  v1 panel, and the 42-unit mechanism panel (0 overlaps on every list).
  `panel.txt` SHA-256 `ec23b7b959dbb6bd05015f5821c99ac9d5a70dd966ef5448443d060b4a3127fe`;
  manifest `reports/g_segment/panel/panel_manifest.json`; builder
  `tools/build_g_eval_panel.py` SHA-256
  `dd36fedcdfbb125f6396cf01d29d3b1ecf381d1aa9d0351d87d928549c603627`.
- Conditions: 7 phases × 4 replicates × 3.0 s windows per clip (the eval-v2 pilot design),
  same for every arm and seed. Built: `reports/g_segment/eval_conditions.json` — **2,800
  conditions, all full-window**, environment seed 20260910, joint-noise seed 20260911, joint
  noise 0.05, nconmax 70; SHA-256 `74b723d42c4050eea9f4ea7ff87d22771e8e32c5155b56829900bf4cb3744a4e`.
- Feasible-hard partition: `reports/g_segment/panel/strata.csv` designates the top 25 of the
  100 panel clips by a reference-only rank average of the seven dynamic-demand features already
  declared in `tools/screen_bank.py`, computed against the 6,197 clips that satisfy the panel's
  frame/feasibility/airborne eligibility. This is **reference-hardness**, fixed without a policy
  or endpoint; it is not retrospectively selected low survival. The remaining 75 clips form the
  feasible remainder. Manifest: `reports/g_segment/panel/strata.manifest.json`.
- **Primary endpoint:** at iteration 3,999 on the 25 feasible-hard-reference clips,

      TrackingScore_i = h_i · exp(−MPKPE_i / 0.30 m) · exp(−θ_anchor,i / 0.40 rad),

  where `h_i = min(survival_s / 3.0 s, 1)`. The horizon factor prevents an early-terminated
  rollout from winning by accumulating errors over fewer frames. MPKPE is common-reference
  root-relative body MPKPE and `θ_anchor` is common-reference anchor quaternion angle. The
  scales 0.30 m / 0.40 rad are the already-fixed body-position / anchor-orientation reward scales
  in the G1 task, not fitted to Phase-G outcomes. The contrast is G2 − G1 over three seeds with
  a seed × clip hierarchical bootstrap (10,000 draws, NumPy seed 20260910), 95 % percentile CI.
- **Key secondary decomposition:** survival on feasible-hard; TrackingScore and survival on all
  100 clips; TrackingScore AULC over checkpoints {1000, 2000, 3000, 3999}.
- **Common-survivor quality/non-harm** (G2 vs G1 on conditions both survive): MPKPE,
  anchor-orientation error, and absolute mechanical work per actuator; margin 10 % relative;
  the CI upper bound must be below +10 % because lower is better.
- **Contact timing:** instrumentation is implemented but validation is pending; contact fraction
  and switch rate are not substitutes. `tools/build_reference_contact_labels.py` creates a
  source-motion/model/tool-hash-bound kinematic proxy, and the evaluator reports one-to-one
  left/right touchdown/liftoff F1 at ±2 source frames (40 ms) only when a hash-linked blinded
  validation report says `validated`. `plan/G_CONTACT_TIMING_VALIDATION.md` freezes a balanced
  10-clip rater-development / 10-clip held-out protocol and prevents no-event windows from being
  scored as perfect. Until every validation gate passes, contact timing remains an explicitly
  exploratory secondary and cannot enter the positive verdict.
- Any repaired-reference contrast (G-2 later, not here) reports the N7 2×2 decomposition
  (policy / reference / interaction) plus fidelity diagnostics.

## 6. Decision rule (draft; to be frozen verbatim at seal time)

TrackingScore SESOI = **+0.02 absolute** on its [0, 1] scale. Survival SESOI remains **+0.05**.

- **Positive:** feasible-hard G2 − G1 TrackingScore point ≥ +0.02, CI lower bound > 0, and all
  three common-survivor non-harm checks pass. Survival need not differ; it is reported as the
  decomposition that distinguishes more precise control from threshold crossing.
- **Sealed null:** TrackingScore CI upper bound < +0.02 **and** survival CI upper bound < +0.05,
  with the manipulation gate passed. Reported as "this ALP allocation does not materially help
  once support and exposure are exact." It supports recommending the simpler G1 control for this
  setting, not a state-of-the-art claim across humanoid trackers.
- **Inconclusive:** anything else with the gate passed; reported with the interval, no
  re-analysis.
- **Not tested:** the calibrated ALP setting fails the confirmation gate; no endpoint row is
  opened.

No threshold is softened after inspection.

## 7. Budget and drop order (decided now)

The segment-v2 pilot measured 2,457,600 transitions over 200 iterations at 512 environments
(12,288 transitions/iteration) and approximately 10k transitions/s. A 512 × 4,000 arm is
therefore **49,152,000 transitions, approximately 1.37 training GPU-hours at the pilot rate**,
before startup, evaluation, retries, and shared-GPU contention. The earlier draft estimate of
1.05 G transitions / 29 GPU-hours multiplied by the environment count twice. A full arm remains
unmeasured on the current hardware, so every calibration attempt records elapsed seconds,
GPU-hours, baseline VRAM, sampled peak total VRAM, and sampled peak delta in its durable sentinel.
G0 was dropped before sealing for comparator confounding, reducing the confirmation from nine to
six training runs. If three seeds × two arms do not fit before the Dec 1 freeze, drop seed 3;
never drop the manipulation/provenance gates or the panel.

## 8. Non-claims

Not a claim about repaired references (that is G-2), not about Newton (that is N-c/G3), not
about bank-wide curation, not about SONIC. A positive G2 − G1 is a claim about *this* calibrated
ALP rank on *this* support. A null licenses the simpler G1 recommendation only inside the tested
task, budget, support, and evaluator.

## 9. Pre-seal checklist (all must be closed before `G_SEGMENT_FREEZE.sha256` is written)

| # | item | done when |
|---|---|---|
| S1 ✅ | ALP rank implemented in `climb/segment_runtime.py`, plumbed through `segment_command.py`, `segment_env_cfg.py`, and `climb_segment_train.py`; `W`, `λ`, configuration propagation, and resume equivalence tested | re-hash at seal; `tests/test_segment_runtime.py`, `tests/test_segment_env_cfg.py` |
| S2 ✅ | `tier_800` guard-0 exact unit table built from full-mode screens of all 800 clips | `reports/g_segment/unit_table.json`, SHAs in §2 |
| S3 ✅ | condition manifest for the 100-clip panel built with `eval_paired_v2.build_conditions` | `reports/g_segment/eval_conditions.json`, SHA in §5 |
| S4 ✅ (draft) | analyzer `tools/analyze_g_segment.py`: manipulation gate first, then hash-complete evaluation provenance gate; bind calibration, PPO/environment/sampler seed, unit table, checkpoint, training entrypoint, evaluator, conditions, active/common references, CSV, and metadata before parsing endpoint rows; primary liveness-weighted TrackingScore on feasible-hard-reference; survival/all-panel/AULC decomposition; common-survivor non-harm; positive/null/inconclusive/not-tested rules | `--synthetic` passes positive, null, inconclusive, low-TV, wrong-seed, and wrong-checkpoint-provenance branches; `tools/build_g_run_manifest.py` constructs the accepted manifest without parsing CSV rows; re-hash at seal |
| S5 ✅ | `tools/run_when_free.sh` gates on free memory **and** utilization ≤ 60 %, retries on OOM / `Failed to allocate`, and appends per-attempt elapsed GPU-hours plus baseline/peak VRAM to durable sentinels. SHA-256 `ba945375055f2dee1a15437de2abfcdaac49306f6135e9fdd856094e890d87ac`. Thirteen 512-env calibration launches completed: 36--49 s, sampled peak-total VRAM 3,598--8,441 MiB, sampled peak delta 2,278--7,254 MiB. The availability gate remains conservatively 14,000 MiB because the peak outlier is retained rather than explained away | `tests/test_run_when_free.py`; `plan/G2_CALIBRATION_RESULT_2026-09-04.md` |
| S6 ✅ | confirmation training seeds fixed: **1, 2, 3** (seed 1 is the early manipulation gate); G0 removed before seal for comparator confounding; only seed 3 may be dropped for budget | — |
| S7 ✅ | G3 pointer: N-c failed on valid data; `PARKING.md` records that G3 must never run | `plan/NEWTON_PRED_RESULT.md` |
| S8 ✅ | 12-candidate, endpoint-blind 50-iteration ALP grid, ledger-only launch orchestrator and deterministic selector; `rho = 0.40`, `lambda = 0.05` selected and passed independent validation; result status is `ready_to_freeze` | `plan/G2_CALIBRATION_GRID.json`, `tools/run_g2_calibration.py`, `tools/calibrate_g2_treatment.py`, `reports/g_segment/calibration/result.json` |
| S9 ✅ | outcome-blind 25/75 evaluation strata built from reference features only | `reports/g_segment/panel/strata.csv`, adjacent manifest |
| S10 ✅ (exploratory-only disposition) | fixed proxy builder, reference-only dual-view renderer, outcome-blind 20-clip panel, one-to-one event scorer, passing/failing/insufficient-support synthetic branches, and evaluator gating are implemented; independent rater artifacts are absent, so contact timing is explicitly frozen out of the Phase-G v1 verdict | `plan/G_CONTACT_TIMING_VALIDATION.md`, `plan/G_CONTACT_TIMING_DISPOSITION_2026-09-04.md`, `reports/g_segment/contact_validation/` |
| S11 ✅ | fail-closed local intake separates the 800-motion calibration scope from the 900-motion full scope and checks committed SHA-256 identities before linking; all 900 identities pass, and the 512-env calibration footprint is measured | `tools/restore_phase_g_bank.py`, `tools/research_preflight.py`, `plan/G2_CALIBRATION_RESULT_2026-09-04.md`; strict calibration preflight has zero blockers; confirmation additionally requires the Phase-G seal |
| S12 ✅ (draft) | post-warm-up sampler ledgers expose conditional success and pre-mixture ALP vectors; the frozen analyzer reports Spearman agreement with failure and `p(1-p)` as exploratory-only | `climb/segment_command.py`, `tools/analyze_g_segment.py`, `paper/PHASE_G_RESULT_TABLE_SHELL.md`; re-hash at seal |

Seal: `sha256sum plan/PREREGISTRATION_G_SEGMENT.md plan/G2_CALIBRATION_GRID.json
tools/calibrate_g2_treatment.py tools/analyze_g_segment.py tools/build_g_run_manifest.py
tools/eval_paired_v2.py tools/build_g_eval_panel.py
tools/run_g2_calibration.py tools/build_g_eval_strata.py tools/climb_segment_train.py
tools/restore_phase_g_bank.py tools/research_preflight.py
tools/build_contact_validation_panel.py tools/build_reference_contact_labels.py
tools/render_contact_validation.py tools/validate_contact_proxy.py
plan/G_CONTACT_TIMING_VALIDATION.md
plan/G_CONTACT_TIMING_DISPOSITION_2026-09-04.md
reports/g_segment/panel/panel.txt
reports/g_segment/panel/panel_manifest.json reports/g_segment/panel/strata.csv
reports/g_segment/panel/strata.manifest.json
reports/g_segment/contact_validation/panel.csv
reports/g_segment/contact_validation/panel.manifest.json
reports/g_segment/unit_table.json reports/g_segment/eval_conditions.json
reports/g_segment/calibration/screen_runs.json
reports/g_segment/calibration/validation_runs.json
reports/g_segment/calibration/result.json
climb/segment_curriculum.py climb/segment_runtime.py climb/segment_command.py
climb/segment_env_cfg.py climb/contact_timing.py climb/contact_validation.py
> plan/G_SEGMENT_FREEZE.sha256`. Do not modify an older sealed manifest; record the new seal in
`plan/STATUS.md` as a new, dated entry.

If contact timing validates before the seal, append the generated proxy manifest, all referenced
proxy label artifacts, independent/manual consensus ledgers, and validation report to the seal.
If it does not validate, record the exploratory-only disposition before executing the command.
