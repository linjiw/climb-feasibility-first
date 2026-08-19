# Branch decision — E2 grounded arm, read against the A2 pre-registration

**Date:** 2026-08-17 · **Read after** A2 and E10 were sealed; no endpoint or
criterion was chosen or altered after seeing these numbers.

## Result

Held-out survival on `heldout100`, 3 seeds/arm, mean ± s.d.

| iter | adaptive | grounded | uniform |
|---:|---:|---:|---:|
| 500 | 0.516 ± 0.009 | 0.517 ± 0.033 | 0.472 ± 0.016 |
| 1000 | 0.667 ± 0.005 | 0.705 ± 0.004 | 0.709 ± 0.008 |
| 1500 | 0.675 ± 0.016 | 0.755 ± 0.010 | 0.761 ± 0.015 |
| 2000 | 0.685 ± 0.012 | 0.763 ± 0.019 | 0.775 ± 0.001 |
| 2500 | 0.658 ± 0.003 | 0.778 ± 0.007 | 0.803 ± 0.008 |
| 3000 | 0.715 ± 0.021 | 0.780 ± 0.020 | 0.807 ± 0.009 |
| 3500 | 0.769 ± 0.027 | 0.808 ± 0.017 | 0.807 ± 0.012 |
| **3999** | 0.780 ± 0.006 | **0.825 ± 0.009** | 0.810 ± 0.005 |

| arm | **primary: AULC** | endpoint | iters-to-0.810 |
|---|---:|---:|---:|
| adaptive | 0.6403 | 0.7804 | censored |
| grounded | **0.6956** | **0.8246** | 3999 |
| uniform | **0.6979** | 0.8096 | censored |

Paired at iter 3999: uniform − grounded = **−0.0150**, **0/3** seeds favour
uniform (i.e. 3/3 favour grounded), 1.9 seed s.d.

## Verdict: **Branch B — grounded ≈ uniform**

Adjudicated on the **primary** endpoint, as A2 requires: AULC 0.6956 vs 0.6979,
a difference of **−0.0023** (0.3% relative). That is a match, not a win.

This is called against the pull of the endpoint result, which favours grounded by
+0.0150 with 3/3 seeds. A2 states plainly that "beats" and "matches" are settled
on the primary "not on whichever secondary happens to separate", and the primary
is AULC. Branch B it is.

**Per the pre-registered table: E3 (diversity, 800 clips) becomes decisive.**

## The co-primary is uninformative here — a defect in how I fixed it

The target was set at 0.810, described in A2 as "uniform's Exp-1 endpoint mean
(0.8096, rounded)". Rounding **up** means uniform must clear a bar 0.0004 above
its own measured mean, and it is duly censored at its own target. Grounded
reaches it only because it exceeds uniform.

So "grounded reaches target, uniform does not" is arithmetically true and
scientifically empty. It is reported as **uninformative**, and no compute-
reduction "×" is claimed from it. The lesson for E3's registration: derive the
target from the control arm's *lower CI bound* or state it unrounded, never a
rounded point estimate of the arm that must clear it.

## What is genuinely established

**H2a, first clause — supported decisively.** Grounded ≫ error-adaptive:
AULC +0.055, endpoint +0.044, and 3/3 seeds. Coverage-grounding does rescue
failure-weighted adaptivity from collapse. Combined with the A4 derivation and
the upstream filings, the diagnosis-plus-repair is the solid contribution.

**H2a, second clause — not supported at 100 clips.** Grounded ≥ uniform holds on
the endpoint and fails on the primary. Prioritisation adds nothing here beyond
undoing its own damage.

**A6 answered: no ε-schedule arm is needed.** Grounded reproduces adaptive's
early lead essentially exactly — iter 500: grounded 0.517, adaptive 0.516,
uniform 0.472. The early benefit is captured automatically as failures equalise,
which was the default expectation. No new arm.

## The trajectory argues for E4, and says so before E4 runs

Uniform plateaus from iteration 2500 (0.803 → 0.807 → 0.807 → 0.810). Grounded is
**still rising** at the horizon (0.778 → 0.780 → 0.808 → 0.825) and crosses above
uniform between 3500 and 4000. AULC over 0–4000 integrates grounded's slower
middle and is therefore the metric least favourable to a late-crossing arm.

This is exactly v2 §8's "gap closes at long horizon" risk running in reverse: the
window may be truncating an advantage rather than flattering one. **E4
(12–15k iterations) is now the highest-value cell after E3**, and its result is
genuinely uncertain — which is the right condition for running it.

Recorded so it cannot be retrofitted: if E4 shows grounded pulling further ahead
after 4000, that is a real sample-efficiency claim at long horizon; it does
**not** retroactively convert this 4000-iteration read into Branch A.

## Correction to the evidence register (E4 row)

The v2 register cites grounded telemetry as "top-1 peaks 0.186 → decays 0.045".
Those numbers came from a **512-env, 60-iteration smoke test** and do not hold at
campaign scale. Measured across the three 4096-env, 4000-iteration runs:

| arm | mean entropy | min entropy | max top-1 |
|---|---:|---:|---:|
| uniform | 1.000 | 1.000 | 0.010 |
| grounded | 0.596–0.620 | 0.394–0.451 | **0.568–0.696** |
| adaptive | 0.377–0.402 | 0.120–0.153 | 0.870–0.893 |

The mixture bounds top-1 at (1−ε) = 0.901; it does not prevent concentration.
Grounded still reaches 57–70% mass on one clip. So ε = 0.1 is **too weak at this
scale**, which independently motivates E8 (ε sensitivity) and the E10 cap arm,
and means the L1 instantiation as currently parameterised is a partial repair
rather than a full one.

## A5 with the collinearity broken

Nine runs across three distinct coverage levels: ρ(max top-1, AULC) = −0.633,
ρ(mean entropy, AULC) = +0.533. Directionally right, but the relationship is
**not monotone**: uniform (top-1 0.010) and grounded (0.57–0.70) have nearly
identical AULC, while adaptive (0.87–0.89) falls off sharply. Coverage looks
**thresholded** rather than dose-linear — damage appears past some concentration,
and below it more coverage buys nothing.

Within-arm correlations at n = 3 are not interpretable (uniform has zero entropy
variance by construction) and are not used.

## Immediate consequences

1. **E3 is decisive and unchanged in position** (post-Sept-15). Its
   pre-registration must fix the target unrounded, or from the control's lower CI.
2. **E4 promoted** to run alongside E3 rather than after it, on the strength of
   the late crossing.
3. **E10 proceeds as pre-registered**, and its cap arm gains motivation: the
   mixture alone leaves 57–70% top-1 mass at this scale.
4. **Frame is not yet decided.** Branch B keeps both frames live: Frame 1 if E3
   shows the diversity interaction, Frame 2 otherwise. The diagnosis, the gates,
   the atlas, and the upstream filings carry Frame 2 regardless.
