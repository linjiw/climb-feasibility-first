# Auditing Dynamic Feasibility of Retargeted Humanoid Motion Data

*Companion note draft v0.1 (2026-08-19). Target: arXiv + workshop, submittable Sept 5. 4–6 pages.
Every number's artifact path: `paper/RESULTS_LOG.md`. Tool: refeas v0.1.0 (Apache-2.0).*

## Abstract (draft)

Large humanoid motion-tracking systems train on tens of thousands of retargeted mocap clips that
pass kinematic quality control: joint limits respected, velocities smooth, feet roughly grounded.
We show that kinematic QC misses a distinct and consequential failure class — references that are
*dynamically impossible* for the target robot given the contacts they make available — and give a
screen that catches it at ~1 CPU-second per clip: contact-free inverse dynamics for the base
wrench the environment must supply, then a torque-limited linear program over friction cones at
the contacts within reach. On a 10,705-clip AMASS→Unitree-G1 bank, 22.8 % of clips demand
unsupported forces exceeding half the robot's weight for more than 10 % of their frames; the rate
varies from 0.1 % to 100 % across source datasets under a single pipeline, marking it as a
retargeting-pipeline property rather than a motion property. We validate the screen on the clip
that broke a failure-adaptive training curriculum — a kneel whose retargeted descent is airborne
for a full second (~329 N unsupported), which no intervention on physics parameters could rescue
and whose flagged windows are independently corroborated by a rollout-only signature (increasing
motor strength *worsens* tracking precisely inside them). We quantify the downstream cost:
contaminated evaluation sets (29 of our 100 held-out clips), poisoned failure-weighted samplers,
and difficulty labels that do not transfer across policies until feasibility features are added
(Spearman 0.567 → 0.609, permutation p = 0.01). We recommend screening before training and
reporting feasibility-stratified endpoints, and release the tool.

## 1. The failure class kinematic QC cannot see

[Draft prose — the #44 story in three paragraphs: a clip with zero joint-limit violations and
≤ 5.6 rad/s that no policy could track past its second second; a failure-weighted sampler that
spent 87–89 % of its exposure on it; and the resolution — for 0.75–1.75 s no collision geom is
within 6 cm of the floor while the pelvis drops 0.35 m. Figure 1 = the stick-frame + unsupported-
force panel (`reports/upstream_drafts/clip44_airborne_repro.png` source script).]

## 2. Method

Per frame of the retargeted reference: (i) q, q̇ from the clip, q̈ by smoothed central differences;
(ii) `mj_inverse` with contacts disabled → base wrench W + contact-free joint torques; (iii)
candidate contacts = collision geoms within `gap` (6 cm) of the plane via exact geom distances;
(iv) NNLS over pyramidal friction-cone generators for the unconstrained residual, and a
torque-limited LP (variables: cone coefficients + L1 slack; constraints: joint torques within
actuator force ranges) for the *smallest unsupported wrench any controller could leave*. Clip
features: `airborne_frac`, `infeasible_frac` (torque-limited unsupported > ½ weight),
`unsupported_impulse_per_weight_s` (seconds of free-fall equivalent), `torque_infeasible_frac`,
under both a uniform-μ and the simulator's own per-geom contact model. Limits stated: plane-only
terrain; genuine flight registers airborne but not (usually) infeasible; the screen judges the
retargeted output *on the target robot*, not the source mocap.

## 3. Validation: anatomy of one impossible clip

[The N1 table (stand/descent/kneel/rise/stand phases with unsupported force and contacts);
the start-offset death table (fails from every offset in the ground segment, 0.5–0.9 s, ~0
saturation); the pre-registered physics-parameter gate that could not move survival in any of ten
configurations (G1, cited to the flagship); and the independent corroboration: the motor-strength
sign reversal localises to the flagged windows (+15–16 mm airborne vs ≈ 0 standing, replicated
across two IC seeds). A control clip from the same bank is supported at every frame.]

## 4. Prevalence

[Table 1: category × {>10 %, >25 %, median, duration-share flagged} — 22.8 % overall, ground
39 %, dynamic 59 %. Table 2: by source — GRAB 0.1 %, TCD 1.6 %, KIT 17 %, BMLmovi 22 %,
Eyes-Japan 23 %, BMLhandball 27 %, CMU 40 %, ACCAD 42 %, HUMAN4D 55 %, Transitions 90 %, CNRS
100 %. The spread under one pipeline and one robot is the argument that this is a
pipeline × source-convention interaction. Caveat paragraph: dynamic category inflated by real
flight; ground category's 39 % cannot be, and is the #44 family writ large. Figure 2 = category ×
source heat/bar panel (`paper/figures/f4_prevalence.py`).]

## 5. Downstream costs

**Samplers.** A failure-weighted curriculum treats "impossible" as "maximally informative" and
collapses onto it (top-1 mass 0.87–0.89; flagship §3). **Evaluation.** 29/100 of our held-out
clips are flagged; they depress every policy's aggregate 6–11 points and cannot separate training
methods (grounded-vs-uniform edge: +0.025 feasible-only, −0.009 infeasible-only) — we now report
feasibility-stratified endpoints by sealed policy. **Difficulty labels.** Reference-feature models
of difficulty transfer across policies at 0.567; adding the three screen features lifts every
transfer pair, four of six beyond a random-feature permutation baseline (p = 0.010–0.045) — the
feasibility component is the part of "difficulty" that belongs to the clip rather than the run.
**A near-miss.** A second reference artifact (hand–hip interpenetration, 53 % of clips > 10 % of
frames) taxes the self-collision reward on accurate tracking — but a sealed test found it does
*not* predict difficulty beyond the feasibility flag (partial ρ −0.04…−0.15, no positive CI): an
audit finding, honestly bounded.

## 6. Recommendations

1. Screen retargeted banks before training; publish per-clip flags with datasets.
2. Report feasibility-stratified endpoints; never average difficulty over start offsets that
   straddle infeasible segments (the "0.31 survival" artifact).
3. Retargeting pipelines: resolve unreachable postures by root-height/contact projection, not limb
   lifting; audit reward terms against the reference itself.
4. For flagged-but-wanted motions: repair (contact-restoring projection), don't just drop —
   [forward-pointer to the flagship's N7 slot].

## 7. Tool

refeas v0.1.0: `screen.py` (single clip, `--brief` batch mode), G1 worked example with a synthetic
hover clip that the screen flags at 45 % infeasible, output schema table, Apache-2.0.
[Repo link on release; version hash pinned in the project's sealed evaluation policy.]

---
*Figures to generate: F1 anatomy (adapt repro script), F2 prevalence panel. Numbers frozen as of
2026-08-19; artifact paths in `paper/RESULTS_LOG.md`. Author list / acknowledgements TBD with
Linji. The two upstream notes (`reports/upstream_drafts/`) are drafts awaiting approval and are
cross-referenced, not duplicated, here.*
