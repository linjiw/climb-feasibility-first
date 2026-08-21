# 9. A calibrated instrument for physics sensitivity

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

**The anomaly it certifies** (exploratory, two supporting cases): on the impossible clip,
**+15 % motor strength makes tracking worse** (+11.5 / +12.8 mm across seeds,
CIs excluding zero) while helping every other clip (−2.6 to −14.2 mm). Windowed against the N1
contact flags, the reversal is absent while the reference is supportable (+0.3 / −1.4 mm),
switches on in the airborne window (+15.0 / +16.0 mm), and persists into its aftermath. Reading:
*a stronger robot executes this untrackable reference harder.*

**P-SIGN rejects the general detector** [sealed ✗, kept; `c7916e8c…`]. On 12 named infeasible
family clips, 7 (needed 8) show ≥ +5 mm airborne effects with CI > 0; only 2 of those 7 meet the
3× airborne/standing localisation rule. Just 4/12 feasible controls stay within the required
2 mm whole-clip bound. The joint rule fails (`reports/P_SIGN/run0/p_sign_summary.json`,
`plan/P_SIGN_RESULT.md`). The two #44 replications remain valid exploratory measurements, but
motor sensitivity is neither sufficiently general nor sufficiently specific to serve as a
rollout-only infeasibility detector or runtime guard.
