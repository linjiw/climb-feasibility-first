# 8. Causal tests (one mixed result, three null mechanisms, one open test)

Everything before this section is observational or mechanistic. Four sealed training interventions
and one unsealed wiring pilot have now read out. They do not support the broad conclusion that
"feasibility intervention works" or that it does not. They support narrower diagnoses: N3 changes
behaviour but trips its interpretation stop; E-HYG removes exposure the policy was not converting;
soft FGAS fails its allocation gate; N7's benefit sits on the changed reference and its interaction
with training; and the segment-v2 adaptive distribution is nearly its own uniform control. Thus no
interpretable adaptive exact-segment allocation arm has yet run. That missing manipulation—not an
assumed positive result—is the open causal test. Support moderation also remains open.

## 8.1 N3 — targeted composition [sealed mixed outcome]

**Sealed** 2026-08-19-era (`plan/PREREGISTRATION_N3_coverage.md`, `af1b7c9f…`; precondition
`plan/N3_PRECONDITION_env_admits.md`, `3c331e18…` — terminations verified not to fire on the
reference; naive PD-follow shown uninformative; contact-supported dynamics verified). Design:
tier_mixed100 + **ground16** (16 nearest *feasibility-screened* kneel/crawl neighbours) vs
+ **random16**; uniform ×2 seeds (keystone), adaptive ×1, random-control ×1; stratified-start
evaluation.

The frozen analyzer (`b118b2d3…`; `reports/N3_result.json`) records E1 and E4 as passes: #44's
feasible kneel/crawl-phase survival is **0.750 in both ground16 seeds**, against base s1/s2/s3
0.000/0.031/0.188, while random16 remains **0.000**. All three evaluated ground16 probes improve
in training. Its arithmetic decision E1∧E4 is therefore true.

The preflight also fixed a stop rule: do not interpret E1/E4 if E2 fails anywhere. It does in the
adaptive arm — heldout survival moves **−0.0346** versus the three-seed base and one easy control
falls to 0.857. The two uniform keystone arms themselves do not regress (−0.0096/+0.0004), but we
retain the stricter global stop and call this a **mixed outcome**, not unqualified causal closure.
E3 also fails: maximum top-1 mass after iteration 2000 is 0.784 (needed <0.50). Most surprisingly,
the predicted unlearnable descent reaches 1.000/0.688, so composition changes tracking even over
the reference-invalid transition. N3 thus demonstrates a strong, specific training effect while
falsifying the clean phase-separation account (`plan/N3_RESULT.md`).

## 8.2 N7 — repair the impossible [sealed joint fail]

The repair-all arm completed at fixed N=800, clip names, ordering, sampler, seed, and compute
(`reports/N7_result.json`, `plan/N7_RESULT.md`). The 2×2 policy/reference cross gives a positive
deployment contrast: R/repaired minus K/raw is **+0.0397**, motion-bootstrap 95% CI
[+0.0153,+0.0658]. It nevertheless misses the sealed +0.05 smallest effect of interest. The
heldout point guard passes (−0.0104), but the zero-shot-ground coverage rule fails (R−K −0.0199;
R−P +0.0155, which needed +0.03), so the joint decision is false.

The cross localises the gain. R/raw minus K/raw is −0.0036, while K/repaired minus K/raw is +0.0233
and the policy-by-reference interaction is +0.0200. Thus `−0.0036 + 0.0233 + 0.0200 = +0.0397`:
there is no raw-reference policy transfer, but the repaired target is easier and the repair-trained
policy co-adapts to it. Post-outcome audit further shows that most gain comes from 11 repairs beyond
the 0.15 m distortion budget (+0.2305 mean versus +0.0160 on 78 certified repairs). Eight names in
`heldout100` overlap tier800; the disjoint92 delta is −0.0122. These qualifications do not replace
the sealed result. They require reference-fidelity and paired motion-quality endpoints before
survival on a heavily altered target can be called better motion.

## 8.3 E-HYG — clip pruning at scale [sealed null]

The cheapest intervention — remove the 99 flagged clips from `tier_800`, hold training compute
fixed — does **not** improve performance (`reports/E_HYG_result.json`,
`plan/E_HYG_RESULT.md`). Feasible heldout survival moves 0.918→0.907 (Δ **−0.0101**, one-sided
permutation p=0.951; P1 needed +0.015), and the predicted worst-decile concentration is absent
(−0.0153 versus −0.0035 for the best half), so P1∧P2 fails. All-heldout Δ is −0.0132. Zero-shot
ground moves −0.0354, inside the pre-registered [−0.05,+0.02] coverage-cost bracket.

This one-seed null is specific to blunt clip pruning at 12.4% contamination. The removed clips are
ones the comparator already fails on, so pruning removes exposure the policy was not converting; it
does not create a distinct allocation over the feasible material that remains. It does not test the
screen, repair, or bin-level eligibility. Together with the segment census, it sharpens the next
method question: can masking infeasible bins retain coverage that pruning discards?

## 8.4 FGAS — clip-mean soft eligibility [sealed implementation-gate fail]

The three-seed soft guard-0 arm completed (`reports/FGAS_result.json`, `plan/FGAS_RESULT.md`). On
the frozen feasible-hard20 primary, survival moves 0.7586→0.7390 (Δ **−0.0196**, hierarchical
bootstrap 95% CI [−0.0497,+0.0134]), rather than the predicted gain of at least 0.05. Feasible
heldout moves −0.0123 and stays inside the −0.03 no-regression bound.

The implementation gate fails: late hard-rejected start mass is **0.199** (required <0.15), and
the top clip is flagged in 0.861 of late iterations. Post-outcome reconstruction matches the live
telemetry within 0.0022. Failure adaptation overwhelms the clip-mean soft multiplier; one clip
with eligibility 0.702 retains 0.618/0.376/0.222 final mass across seeds. This is therefore a
negative result for the implemented soft formulation, not a clean test of segment-native adaptive
sampling: the intended treatment never controlled the realized allocation. A follow-up must make
eligible segments the adaptive unit and be sealed separately.

## 8.5 Segment-v2 — exact mechanics, failed manipulation [exploratory; not tested]

The v2 runtime fixes the old sampler and evaluator mechanics: exact horizon-safe support, stable
unit attribution, explicit 50-step truncation, paired startup randomization, terminal reads before
reset, and zero invalid or censored trials (`plan/SEGMENT_NATIVE_FOLLOWUP_2026-08-20.md`). Its
one-seed, 42-unit wiring pilot moves paired success by +0.0079, with a unit-clustered 95% interval
[−0.0536,+0.0714] (`reports/segment_v2_pilot/result.json`). That outcome is not the load-bearing
readout. The load-bearing manipulation check is that the final adaptive allocation is only
**0.014 total variation** from its capped uniform control (correlation 0.998), because conditional
failure saturates near one across most units.

Accordingly, this pilot is a mechanical pass and an allocation fail. Calling its outcome a null for
adaptive segment sampling would treat two nearly identical distributions as different treatments.
The next arm must predeclare and pass an informative allocation band before outcome evaluation;
until then, exact-feasible adaptive allocation is **not tested**.

## 8.6 E3 — support moderation at scale [SLOT]

**Sealed** (`plan/PREREGISTRATION_E3_addendum.md` `f7929136…` + v2 `2c38845b…` + the D1 policy
`a93a87a0…`): uniform-800 ×3 vs grounded-800 ×3 (+ ≤1 adaptive demo, optional LP arm);
bank-invariant support (clean-bank z-space, fixed kernel h = 2.00); **bidirectional named
predictions** — the 22 dynamic held-out clips all lose support 100→800 and are predicted to get
*harder* (P-A, the risky half); the 20 largest support gainers get easier (P-B); grounded's
advantage concentrates on the losers (P-D, H2b-S: ρ(Δᴳ⁻ᵁ, Δlog-support) ≤ −0.25). Feasible-only
primary endpoints per D1; bank composition (ground 3.2 % → 0.65 %, dynamic 11.8 % → 1.9 %) is an
analysed variable; feasibility flags are a launch gate (already computed for all 900 clips,
`reports/feasibility_e3/feasibility.csv`, sentinel present).

**Fills:** after N3 in the Sept-15+ GPU order; results freeze Dec 1.
