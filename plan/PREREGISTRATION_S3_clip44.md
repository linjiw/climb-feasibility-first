# Pre-registration — clip #44 discrimination (v3 §6), before S3 runs

**Written:** 2026-08-17, before any multi-solver probe of clip #44 exists.
**Clip:** `BMLmovi_Subject_64_F_MoSh_Subject_64_F_9_poses_120_jpos`, 9.98 s, AMASS bank.
**Why it matters:** the attractor in all six adaptive/grounded runs (A7); measured
survival 0.3125 under the uniform control against a bank mean of 0.892.

## Correction to the record, made now rather than after S3

The v3 plan (and my own retrospective) describe #44's atlas profile as *benign*,
citing μ = 0.18 and peak GRF 1.42×. Both numbers are correct and both are the
wrong columns. The full atlas row, expressed as bank percentiles:

| feature | value | bank percentile |
|---|---:|---:|
| `nonfoot_ground_frac` | 0.613 | **99.7%** |
| `body_penetration_max` | 0.036 m | 98.4% |
| `foot_penetration_max` | 0.004 m | 90.9% |
| `foot_clearance_p50` | 0.038 m | 83.0% |
| `jerk_p95` | 1282 | 80.0% |
| `double_support_frac` | 0.028 | 26.8% |
| `support_margin_mean` | −0.477 | **4.5%** |
| `required_mu_p95` | 0.181 | 61.9% |
| `vert_force_bw_max` | 1.42 | 72.8% |

Sixty-one percent of the clip has a non-foot body on the floor. This is a
low-posture / ground-contact motion — the family the full-bank correlation
already showed is essentially orthogonal to kinematic intensity (ρ = −0.10 vs
CoM speed). The atlas *does* have signal on #44; it lives in the multi-contact
axis, which the regression's support rule excluded (6% nonzero) and which the
"benign" reading skipped.

So F1's phrasing sharpens: it is not that the reference carries no information
about #44 — it is that a **single per-clip scalar cannot express contact-mode-
dependent difficulty**, and the sampler that collapsed onto it was reading a
failure count, not a contact mode. The correct wording goes into the addendum.

## The three explanations, ordered as v3 §6 requires

**(a) Data artifact.** Interpenetration, foot-skate, or retarget residual.
- *Prediction if true:* the clip fails identically across every physics
  configuration, with anomalous contact sets — a bad reference is bad in every
  solver. Between-config variance ≈ 0. Contact-set Hamming distance across
  solvers ≈ 0 while absolute failure is high.
- *Prior evidence:* body penetration 0.036 m is 98th percentile but below the
  0.10 m screen; foot penetration 0.004 m is trivial. Not obviously corrupt, but
  the ground-contact phases (61% of the clip) are where retarget quality is
  weakest bank-wide (GMR-vs-wbt clearance gap was 20 mm), so this stays live.
- *Additional check, run before S3:* foot-skate — planar foot velocity while
  the foot is in the contact band. High skate ⇒ retarget artifact.

**(b) Estimator artifact.** A7 already covers this: dominant identity is
seed-invariant across six runs, and measured survival under uniform is 0.31 —
neither mastered nor unlearnable. The stale-estimator reading is *not*
supported. Retained here only for completeness; the discrimination is now
between (a) and (c).

**(c) Genuine motion × robot × contact interaction.**
- *Prediction if true:* high **between-config** variance in excess of the
  within-config noise ensemble, concentrated in the ground-contact segments
  (where `nonfoot_ground` is active), with the contact-model axis (default vs
  hydroelastic/SDF) and the actuation axis showing more spread than the
  friction/mass axis. Solvers *disagree* about what happens when a knee, hand or
  torso is loaded against the plane.
- *Falsified if:* between-config variance on #44 is no higher than on a matched
  control clip of the same duration with `nonfoot_ground_frac ≈ 0`.

## Matched controls (fixed now)

Two controls, drawn before S3, both from `tier_mixed100` so the same frozen
policy has trained on them:

1. A **kinematically-matched, no-ground-contact** clip: nearest neighbour to #44
   on {com_speed_p95, jerk_p95, duration_s} with `nonfoot_ground_frac = 0`.
   Isolates the ground-contact axis.
2. A **mastered** clip (uniform-control survival ≥ 0.95) of similar duration.
   Sets the between-config floor for a clip the policy handles.

## What each outcome does

| result | reading | consequence |
|---|---|---|
| between ≈ within on #44, and ≈ controls | fragility as defined is empty for this clip | H-F1's motivating anomaly weakens; H-F1 rests on the LUCID correlation |
| between ≫ within on #44, ≫ controls, concentrated in ground-contact segments | genuine interaction, localised | F1 confirmed with a mechanism; the ground-contact family becomes the first fragility-map target |
| between ≫ within on #44 but flat across time, not segment-localised | model-dependent but not phase-specific | still fragility, but the "per-segment" claim needs a different clip |
| skate/penetration audit fails | data artifact | #44 is dropped from the anomaly narrative *and* flagged in the bank; check the rest of the 99th-percentile ground clips |

## Audit results (run 2026-08-17, before S3)

**Contact anatomy of #44** (exact geom-to-plane distance, every frame):

| | fraction of frames |
|---|---:|
| left foot in contact band | 0.06 |
| right foot in contact band | 0.08 |
| any non-foot body on floor | **0.61** |
| right knee down | 0.56 |
| right hip-yaw link down | 0.50 |
| left knee down | 0.44 |
| right wrist down | 0.28 |

Ground-contact phase is contiguous: **frames 91–396 = 1.8 s – 7.9 s**. This is a
kneel / floor-sit / crawl motion. The feet carry load for well under a second in
total.

**Foot-skate:** planar foot speed while in the contact band, p50 0.13–0.25 m/s.
Not interpretable as skate here — the feet are in the band for only 6–8% of
frames, and those are the entry/exit transitions, not stance. The skate test is
designed for locomotion clips and does not apply. The relevant retarget-quality
question is whether **knee, hip and wrist loading** is physically consistent —
which is precisely what a multi-solver probe measures, so (a) and (c) are
discriminated by S3 itself, not by a pre-check.

**Refined (a)/(c) prediction:** the between-config variance, if it exists,
should be concentrated in the two *transitions* — into ground support around
1.8 s and out of it around 7.9 s — and in the knee-loaded interval. A data
artifact would show constant anomalous knee contact across all configs; a
genuine interaction would show the configs disagreeing about whether the knee
support holds. Recorded before S3.

**Matched controls, drawn now** (from `tier_mixed100`, uniform-control survival
from `reports/A7_trainbank_uniform_s1.csv`):
- kinematically-matched no-ground clip: nearest on {com_speed_p95, jerk_p95,
  duration_s} with `nonfoot_ground_frac = 0` — resolved in the S3 script and
  logged with its name.
- mastered clip: highest-survival clip of duration within ±3 s of 10 s.
