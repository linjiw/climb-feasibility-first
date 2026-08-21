# Segment-Native Research Log — 2026-08-20 22:59 EDT

## Objective

Turn the three-reviewer audit into a safe, testable segment-native training path. Update the project page without changing sealed claims, then prove the fixed-horizon command lifecycle in the simulator before spending GPU time on PPO.

## Baseline and provenance

- The working tree was already dirty at entry; existing edits and artifacts are preserved.
- `docs/index.html` was already modified before this run.
- FGAS and N7 sealed inputs/results remain read-only.
- Prior corrected paired pilot: 29 repair-panel motions, 4 cells, 3,296 trials. R/repaired minus K/raw success was +0.1355 (motion-bootstrap 95% CI +0.0505 to +0.2365).
- Raw-reference policy transfer remains unresolved: R/raw minus K/raw was +0.0234 (95% CI -0.0123 to +0.0825).
- The repair benefit was concentrated in over-budget cases (+0.2630); residual cases were +0.0153.
- CPU contracts currently cover 42 exact feasible units and 4,679 legal 50-step starts. The deterministic capped probability projection passed 4,000 randomized review certificates.

## Review decisions

1. Sample exact feasible frame segments, not clip-level occupancy masks.
2. Attribute failures and attempts to stable unit IDs on a fixed update clock.
3. Enforce hard-zero invalid starts, an explicit exploration floor, and per-unit/per-clip probability caps.
4. End each segment trial with an explicit truncation before the reference can wrap. A clip-end teleport must never be a continuing PPO transition.
5. Pair evaluation seeds and compare quality only on common survivor frames.
6. Treat repaired-reference lift as routing/target evidence, not proof that the repaired-trained policy is broadly better.

## Gates for this run

| Gate | Requirement | Status |
|---|---|---|
| Website | Exploratory panel is accurate, locally valid, and does not alter sealed claims | passed |
| Static contracts | Full focused tests pass in the pinned mjlab environment | passed: 25 focused tests; Ruff and ty pass |
| Timeline | Vectorized trace proves first frame, reward frames, H-step truncation, and no wrap | passed: 24/24 GPU trials |
| Sampler health | Zero invalid mass; configured floor/caps hold; unit IDs receive correct outcomes | passed in trace: top-1 0.05, ESS 31.21, zero invalid counters |
| GPU smoke | Only after prior gates: bounded run shows actual GPU allocation and finite PPO telemetry | passed: 512 envs, 245,760 steps, finite PPO, zero invalid/censored |
| Paired pilot | Frozen starts/DR, terminal-safe metrics, common-survivor quality | passed mechanically: 504 paired worlds/policy; benefit gate not met |

## Claim policy

This run is exploratory and unsealed. It may validate mechanics and decide whether a training experiment is warranted. It cannot amend FGAS/N7 outcomes or support a training/performance benefit claim without a new preregistration, controls, and multi-seed evaluation.

## Iterations

| Stage | Change | Result | Decision |
|---|---|---|---|
| T1 | Initial 8-env GPU timeline trace | stopped before env creation: Torch memory-stat API rejected a CUDA device string | fix instrumentation to pass `torch.device`; keep algorithm and trace parameters unchanged |
| T2 | Retry with `torch.device` | stopped before env creation: CUDA context was not initialized before resetting peak memory stats | initialize CUDA explicitly and use its numeric device index |
| T3 | 8-env × 3-cycle GPU lifecycle trace | passed: 24 distinct assignments, exact 50-step trials, pure truncations, 0 invalid/censored | keep runtime integration; advance to bounded PPO smoke |
| S1 | 512-env adaptive PPO smoke launch | stopped at CLI parse: Tyro rejected scalar syntax for the GPU list; env never started | omit flag and use the declared default `[0]` |
| S2 | 512-env adaptive PPO, 20 iterations | training passed: 245,760 GPU steps, ~10k steps/s, finite losses, zero invalid/censored counters; checkpoint sidecar failed on float64→float32 scatter | keep PPO integration; fix ledger dtype before pilot |
| S3 | 512-env adaptive ledger test, 2 iterations | passed: model, JSON segment ledger, and sampler-only state saved at both checkpoints | open paired 200-iteration uniform/adaptive pilot |
| P0 | Uniform pilot, stopped after checkpoint 100 (interrupt landed at 117) | failed health gate: mean episode length 21→5.5/50, failure rate 0.9992 while return improved; model/checkpoint ledger valid and invalid/censored counts stayed zero | do not launch adaptive; diagnose early-termination incentive |

The checkpoint-100 ledger records 149,133 completed trials, 148,988 failures, and zero censored or invalid trials. The failure spans every source clip (clip rates 0.9975–1.0), so this is not a sampler attractor. It is a shared objective problem: the policy can avoid a long stream of net-negative tracking/action/contact reward by terminating early. The next controlled change adds mjlab's existing failure-only reward term, calibrated as an actual one-off event cost after dt scaling; time-outs remain unpenalized.

| R1 | Uniform reward gate: one-off failure cost −5, 40 iterations | directionally better but failed gate: final mean episode length 15.7/50, failure rate 0.9856, no segment completions in final batch | reject −5 as too small; test −10, which exceeds the observed ~8-return cost of a full initial horizon |
| R2 | Uniform reward gate: one-off failure cost −10, 40 iterations | passed anti-collapse gate: final mean episode length 25.7/50, failure 0.9609, segment time-outs present, zero invalid/censored | use −10 symmetrically in the exploratory paired pilot; stop if length <15 or failure >0.99 after iteration 50 |
| P1 | Uniform, 512 env × 200 iterations with failure cost −10 | completed 2,457,600 GPU steps; final batch length 36.52/50, cumulative failure 0.9141; zero invalid/censored | keep as paired control checkpoint |
| P2 | Adaptive, 512 env × 200 iterations with identical seed/config | completed 2,457,600 GPU steps; final batch length 34.68/50, cumulative failure 0.9162; unit/clip caps 0.05/0.25, zero invalid/censored | advance to frozen paired evaluation |
| E1 | Exact 42-unit evaluation, 3 phases × 4 reps | 504 worlds/policy; environment, condition, initial-state, and startup-DR hashes match | analyze with unit-clustered bootstrap and common-survivor frames |
| E2 | Paired analysis | adaptive−uniform success +0.0079, 95% CI [−0.0536,+0.0714]; survival +0.0115 s [−0.0100,+0.0346] | no survival-benefit claim; do not scale this configuration to confirmatory seeds |
| E3 | Common-survivor quality, 22,321 paired frames | body-position error −4.20 mm [−6.63,−1.90]; anchor-orientation error −0.0280 rad [−0.0397,−0.0163]; anchor/joint/work intervals cross zero | retain as a preliminary motion-quality signal only |
| D1 | Curriculum manipulation audit | final adaptive distribution differs from control by L1 0.0279 (TV 0.0140; correlation 0.998) | add adaptation-TV telemetry; require a predeclared minimum separation before another outcome pilot |

## Review-session conclusion

The runtime and evaluator changes are kept: exact starts, stable attribution,
explicit segment truncation, probability caps, terminal-safe reads, and paired
randomization all passed. The initial reward was rejected because it rewarded
early failure; the shared one-off failure cost corrected that pathology.

The policy result is deliberately not promoted. Survival is statistically
unresolved, and the treatment was only 1.40% total-variation away from its
control at the final checkpoint. The common-survivor body/orientation improvements
are encouraging, but one seed on a mechanism-selected panel cannot establish a
training or motion-quality benefit.

The next experiment must first pass a curriculum-manipulation gate on a separate
development panel. A post-hoc, outcome-blind sensitivity check shows that raising
the conditional-difficulty power from 1 to 4 would increase final distribution
TV from 1.40% to 5.50% while preserving 0.05/0.25 caps and 31.74 entropy-effective
units. That is a candidate for preregistration, not a tuned result. The three-arm
comparison and additional seeds remain paused until this gate and the missing
unmasked-grounded control are frozen.

Timeline artifact: `reports/segment_v2_smoke/timeline_trace.json`. Peak Torch allocation was 40.0 MB (62.9 MB reserved) on `cuda:0`; this directly confirms that the trace executed on the GPU.

Pilot artifacts: `reports/segment_v2_pilot/result.json`, the two paired CSVs and
per-step trajectory files in that directory, and checkpoint ledgers under
`reports/segment_v2_pilot/training/segment_v2_pilot/`. This entire block remains
unsealed and exploratory.
