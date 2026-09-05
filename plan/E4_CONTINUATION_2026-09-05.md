# E4 continuation and DFRP policy validation

Status: approved research execution; written before confirmation endpoint access.

Linji's 2026-09-05 follow-up requests the three-seed Exact Uniform versus Exact ALP
comparison and a same-policy raw versus DFRP-repaired tracking evaluation. This
extends the earlier seed-1-only execution approval. It does not change the sealed
Phase-G scientific contract or its seed-1 stop rule. Publication labels are E4,
Exact Uniform, and Exact ALP; artifact labels remain Phase G, G1, and G2.

## E4 execution

1. Finish the running seed-1 G1/G2 chain and recompute its ledger-only gate.
2. Only on `pass_for_evaluation`, run seeds 2 and 3 at the same 512 environments,
   4,000 iterations, rho 0.40, lambda 0.05, and all remaining sealed settings.
3. Verify the complete sampler manipulation contract before evaluator access.
4. Evaluate each arm/seed at iterations 1000, 2000, 3000, and 3999 using the
   existing 2,800-condition manifest. Build the hash-complete run manifest and
   execute the frozen analyzer. Publish every status and subgroup.

Training and evaluation use the shared-GPU availability gate. The added
orchestrator only composes the sealed entrypoints; it cannot revise their rules.
No threshold or hyperparameter changes are permitted in response to these runs.
A seed-1 failure ends this confirmation as `not_tested`.

## DFRP same-policy comparison

Use the final Exact Uniform seed-1 checkpoint, selected by arm and iteration
before outcomes. Evaluate all 22 qualified repairs and four byte-identical
controls from the existing curated manifest. Hold checkpoint, phases, horizon,
noise seeds, and evaluator fixed between raw and repaired reference banks.
Use the raw bank as the common fidelity reference. Report paired survival,
liveness-weighted TrackingScore, common-survivor errors and their denominator,
mechanical work, and the recorded reference-distortion diagnostics. Stratify the
two training-overlap clips separately; the whole panel is not held out.

This is an exploratory fixed-policy deployment/reference comparison, not a
policy-training ablation. It does not establish uninterrupted full-clip execution
from repeated short windows. Report frame-zero windows separately; do not assume
the old attractor's zero survival applies to every panel clip. Neither >80%
survival nor a before/after rescue is stipulated as a result. All failed trials
and all missing payloads must appear in the accounting.

Raw and repaired NPZ identities must match the existing manifest before evaluation.
At intake, only 2/26 raw and 1/26 selected payloads exist at their recorded paths;
recovering the remaining exact identities is the immediate data prerequisite.

## Writing claim map

| Claim | Evidence and limit |
|---|---|
| E1 collapse | Three historical seeds; peak **clip** mass 0.870–0.893 |
| E2 transfer | 100 held-out clips; same architecture, different training curricula; rho 0.567→0.609, random-feature p=0.010 |
| E3 repair | 22/26 qualified panel candidates plus four unchanged controls; qualification is not tracking success |
| E4 calibration | 50 iterations, independent validation; mean TV 0.1056, min effective units 700.1, max **unit** mass 0.0134 |
| E4 policy benefit | Pending frozen confirmation; null is not equivalence |
| Pilot fidelity | One-seed exploratory common-survivor comparison; insufficient manipulation for ALP attribution |

The historical clip and calibration unit concentration measures cannot be joined
into a direct 88%→1.5% effect. The factorization is a decision framework, not an
empirical proof of independence or a universal physical invariant.
