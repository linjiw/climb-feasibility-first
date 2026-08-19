# Pre-registration addendum — E3 (800-clip bank), written 2026-08-18 before E3 launches

Supplements v2 §E3 / H2b and `BRANCH_DECISION.md`. E3 remains post-Sept-15 (gap-capacity only);
this addendum fixes what N1–N3 changed about how E3 must be run and read.

## 1. H2b sharpened to support-moderation

v2 H2b: Δ(grounded − uniform) at 800 clips > at 100 clips ("diversity grows the effect").
Sharpened: **the per-clip curriculum effect at 800 is moderated by the clip's change in support
between the two banks.** For each held-out clip c (heldout100, identical across banks):

- Δ_c = difficulty under uniform-800 − difficulty under grounded-800 (positive = grounded helps);
- ΔS_c = log support-density(c | tier_800) − log support-density(c | tier_mixed100), from
  `tools/analyze_atlas_support.py` (`support_features_tier_800.csv` gives the bank; held-out
  values are recomputed against it before unblinding).

**H2b-S (pre-registered):** ρ(Δ_c, ΔS_c) ≤ −0.25 — grounded's advantage concentrates on clips whose
support *fell* or stayed low, because uniform-800 spends its exposure where support rose and
grounded's coverage floor protects the rest. Low-support clips are identified in advance:
`support_features_heldout100_wrt_mixed100.csv` bottom quartile by density (25 clips), listed
here as the analysed subgroup. Secondary: mean Δ over that quartile > mean Δ over the top quartile.

Also pre-registered from N2 (E3-S1..S3): clips that gain support get easier under uniform-800
(ρ(Δdifficulty_{800−100}, ΔS) ≤ −0.25); intrinsic+support fitted on the 100-bank policies transfers
to the 800-bank policies better than intrinsic alone by ≥ +0.05 ρ beyond a 200-draw noise-feature
baseline; held-out ground-contact clips get *harder* under 800 (ground share 3.2 % → 0.65 %) while
locomotion clips get easier.

## 2. Bank composition is an analysed variable

Category composition by duration (rule: ground `nonfoot_ground_frac>0.1`; dynamic `com_speed_p95>1.2`;
quiet `<0.35`; else locomotion — `flight_phase_frac` unusable, see N1/N2):

| bank | locomotion | quiet | dynamic | ground |
|---|---:|---:|---:|---:|
| tier_mixed100 (100) | 62.3 % (43) | 22.7 % (31) | 11.8 % (24) | 3.2 % (2) |
| tier_800 (800) | 51.0 % (422) | 43.4 % (331) | 1.9 % (38) | 0.65 % (9) |

The 800 bank is *quieter* and has less dynamic and less ground content than the 100. Every E3
result is reported per category, and the headline Δ(grounded − uniform) is reported both pooled
and category-stratified. If H2b holds only in the categories whose share fell, that is the
support-moderation reading, not "diversity".

## 3. Evaluation protocol: stratified starts, everywhere

The campaign's "random start" survival averages over start offsets and therefore conflates *where*
a policy fails with *how much* of the clip is failable — #44 read 0.31 because episodes that
began after its ground segment survived; under frame-0 starts it is 0.00. Every difficulty label
E3 produces (per-clip difficulty for H2b, atlas labels, support tests) uses
`tools/eval_stratified.py`: offsets {0,1,2,3,4,6,8} s (clipped to clip length), 3 s windows,
8 episodes per offset, DR on, no pushes; per-clip difficulty = 1 − offset-mean survival, with the
per-offset profile kept. The atlas's own labels (RQ1/A3) are re-derived under this protocol
before E3 unblinds and the transfer numbers restated; the random-start numbers remain in the
record as the confounded version.

## 4. Reference feasibility as a label-hygiene step

N1 showed the descent of #44 is airborne (retarget artefact) and that 12 of 40 nearest ground
clips share it. Before E3 labels are generated at scale, `tools/n1_knee_id.py` (gap 6 cm,
torque-limited LP) runs over tier_800 and heldout100 (~1 CPU-hour, 16 workers) and every clip
carries `infeasible_frac`; clips above 10 % are *kept* in the bank (they were trained on in the
100 campaign too) but flagged, reported as a category, and excluded from the support-transfer
regressions as a sensitivity analysis.

## 5. Arms

Unchanged from v2: uniform-800 × 3 seeds, grounded-800 × 3 seeds; ≤ 1 adaptive demo seed.
**Optional LP arm** (learning-progress sampler, if the window allows one more run): motivated by
N3 — LP deprioritises zero-progress attractors by construction (sampler-side fix) whereas N3's
augmentation is the data-side fix; both address the unsupported-attractor mechanism from
opposite ends. Pre-registered prediction if run: LP's top-1 exposure share ≤ grounded's, and its
Δ vs uniform on the low-support quartile lies between grounded and uniform. Adding it does not
change any of the primary endpoints above.

## 6. What E3 cannot claim regardless of outcome

No sim-to-real; no physics-fragility claim (PhysFrag off the critical path, N6); no bank beyond
800 (v4 line). A positive H2b-S makes support a *transferable atlas object* (N2's open claim);
a null leaves the atlas descriptive and the paper in Frame 2 with the composition result intact.
