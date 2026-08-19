# 9. A calibrated instrument for physics sensitivity (complete except the P-SIGN slot)

**Why an instrument section exists.** The G1 gate (§5.2) produced a methodological finding that
outranks its negative: the natural fragility statistic — mean |φ⁺ − φ⁻| along paired
single trajectories — is **chaos-dominated**. Two runs of *identical* physics from identical
states (the conformance pair of §5.1) already diverge by 2.5–8.4 mm of body-position error within
seconds; closed-loop humanoid tracking has a Lyapunov horizon of ~1–2 s at the millimetre scale.
Every intervention effect in the pre-registered analysis (0.003–0.019 m) sat at that floor, which
is why nothing could be reported under the sealed 5× rule. An instrument that folds the sign
measures divergence, not mechanism.

**The calibration** (`tools/analyze_g1_v2.py`; `reports/G1/run0/g1_v2_*`; labelled *instrument
calibration*, not a re-adjudication of G1). Three replacements, each with the floor measured
identically from the stock-engine arm: **S**, the signed replicate-mean effect
E_r[mean_t(φ⁺ − φ⁻)] with paired-bootstrap CIs (chaos averages out; shrinks with R); **D**, the
Wasserstein-1 distance between pooled φ distributions minus the identical-physics W1; **T**,
paired timing statistics (first-termination shift, contact-onset shift). Resolution criterion:
|S| > 2× the floor CI half-width with the CI excluding zero.

**What it resolves** (R = 8): the floor drops to ≈ 0 ± 1 mm on long clips, and mechanism effects
of 6–14 mm stand clear of it — motor strength on 5/6 clips, delay on the dynamic clips
(+11.9 mm on the 99th-percentile-speed clip), while stiffness/CoM/condim sit at 2–3 mm and
contact onsets never move (≤ 0.03 s under every intervention). Timing adds a phase channel: +20 ms
of action delay brings the attractor's fall forward by 0.51 ± 0.14 s.

**It replicates.** An independent replicate set (IC seed 1, `reports/G1/run1_seed1/`): Pearson
r = 0.92 across the 36 (axis, clip) signed effects, and **6/6 sign agreement on every effect
above 5 mm**; 2–4 mm effects flip sign exactly as their CIs permit (`plan/N5_RESULT.md`). The
instrument is reproducible where it claims resolution and says so where it does not.

**The one anomaly it certifies** (exploratory, two supporting cases): on the impossible clip —
and only there — **+15 % motor strength makes tracking worse** (+11.5 / +12.8 mm across seeds,
CIs excluding zero) while helping every other clip (−2.6 to −14.2 mm). Windowed against the N1
contact flags, the reversal is absent while the reference is supportable (+0.3 / −1.4 mm),
switches on in the airborne window (+15.0 / +16.0 mm), and persists into its aftermath. Reading:
*a stronger robot executes an untrackable reference harder.* If general, this is a rollout-only
infeasibility detector — no inverse dynamics, no model of the reference, just paired rollouts.

**[P-SIGN SLOT — sealed `c7916e8c…` (`plan/PREREGISTRATION_P_SIGN.md`): ≥ +5 mm airborne-window
effect with CI excluding zero on ≥ 8 of the 12 named family clips; < 2 mm on ≥ 8 of 12 feasible
matched controls; ≥ 3× airborne/standing localisation. Pass → this paragraph becomes a
"rollout-only infeasibility detector" subsection and a candidate runtime guard (deployment: when
tightening gains worsens a segment, suspect the reference, not the controller). Fail → the
anomaly stays exactly this one paragraph. Runs in genuine GPU gap capacity; fills when run.]**
