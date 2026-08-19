# Auditing Dynamic Feasibility of Retargeted Humanoid Motion Data

*Companion note draft v0.2 (2026-08-20; v0.1 archived in git history). Target: arXiv +
workshop, submittable Sept 5. 4–6 pages. Status labels: **sealed ✓ / sealed ✗ (kept) / measured /
exploratory / pending 🕐** appear on every claim, including captions. Every number cites its
artifact path (`paper/RESULTS_LOG.md` is the master index). Engine pins (used throughout):
MuJoCo 3.11.0 (C) · MuJoCo Warp 3.11.0 · mjlab v1.6.0 · Newton commit `7bb6d02d`
(pip 1.6.0.dev0) · warp-lang 1.16.0 · Unitree G1 model `g1.xml` sha `febdcbef…`
(`plan/PREREGISTRATION_G1_clip44.md` §Pins). The conformance certificate is a property of this
version pair — see §6 and the re-certification spec.*

## Abstract

Large humanoid motion-tracking systems train on tens of thousands of retargeted mocap clips that
pass kinematic quality control: joint limits respected, velocities smooth, feet roughly grounded.
We show that kinematic QC misses a distinct and consequential failure class — references that are
*dynamically impossible* for the target robot given the contacts they make available — and give a
screen that catches it at ~1 CPU-second per clip: contact-free inverse dynamics for the base
wrench the environment must supply, then a torque-limited linear program over friction cones at
the contacts within reach. On a 10,705-clip AMASS→Unitree-G1 bank [measured], 22.8 % of clips
demand unsupported forces exceeding half the robot's weight for more than 10 % of their frames;
the rate varies from 0.1 % to 100 % across source datasets under a single retargeting pipeline,
marking it as a pipeline property rather than a motion property. We validate the screen on the
clip that broke a failure-adaptive training curriculum: a kneel whose retargeted descent is
airborne for a full second (median 329 N unsupported against a 327 N robot weight) [measured],
which a pre-registered physics-parameter gate could not rescue in any of ten configurations
[sealed ✗, kept], and whose flagged windows are corroborated in two seed-sets by a rollout-only signature —
increasing motor strength worsens tracking precisely inside them [exploratory; generality
pre-registered, pending]. We quantify downstream costs: contaminated evaluation sets
(29/100 held-out clips) [measured], poisoned failure-weighted samplers [sealed ✓], and difficulty
labels that transfer across policies only once feasibility features are added (Spearman
0.567 → 0.609 on the headline pair, permutation p = 0.010; direction positive on 6/6 pairs, 4/6
significant) [sealed ✓]. We release the screen, an error-class checklist for coupling physics
stacks to RL harnesses, and recommend feasibility-stratified evaluation.

## 1. The failure class kinematic QC cannot see

A 100-clip Unitree-G1 tracking curriculum of the BeyondMimic/mjlab family collapsed: its
failure-adaptive sampler concentrated 87–89 % of exposure on one kneel-and-crawl clip in 3/3
seeds and lost to uniform sampling (held-out survival 0.780 vs 0.810; per-seed Δ
+0.030/+0.028/+0.030) [sealed ✓; `reports/campaign_summary_3arm.json`,
`reports/A5_coverage_dose.json`; sampler mechanism filed as mjlab #1153 /
whole_body_tracking #73]. The clip itself passed every kinematic check: zero joint-limit
violations against the G1's ranges, joint speeds ≤ 5.6 rad/s, smooth [measured;
`plan/N1_RESULT.md`]. A pre-registered gate over physics parameters — action delay, motor
strength, foot friction, contact stiffness, contact model, torso CoM; 1,440 paired worlds —
failed its own sealed criteria: no intervention changed the clip's survival in any configuration
[sealed ✗, kept; `plan/PREREGISTRATION_G1_clip44.md` `41e4b20c`, `plan/G1_RESULT.md`,
`reports/G1/run0/`].

What no kinematic feature could see: for the second between 0.75 s and 1.75 s of the retargeted
descent, **no part of the robot's collision geometry is within 6 cm of the floor** — the feet
float 7–10 cm up while the pelvis falls 0.79 → 0.40 m — so a median 329 N (p90 348 N) must come
from nowhere; the robot weighs 327 N [measured; `reports/N1_clip44_knee_id.json`]. The mechanism
is prosaic: the human sat back onto their heels; the G1's legs cannot fold that far; the
retargeter resolved the conflict by lifting the legs instead of lowering the root. Under frame-0
starts the clip's survival is 0.00 for every policy we trained; the previously reported 0.31 was
an artifact of averaging over start offsets that skip the impossible segment [measured;
`reports/N3_baseline_uniform-s1_strat.csv`] — one of two evaluation-protocol lessons this note
carries (§5). Figure 1 shows the anatomy.

*Figure 1 [measured]: reference stick-frames (red panels: no contact available) and the
torque-limited unsupported force; descent and rise pinned at ≈ body weight. Script + data:
`tools/n1_knee_id.py` → `reports/N1_clip44_knee_id.json`; rendering
`reports/upstream_drafts/clip44_airborne_repro.png`.*

## 2. The screen

Per frame of a retargeted reference: (i) q, q̇ from the clip; q̈ by smoothed central differences;
(ii) contact-free inverse dynamics (`mj_inverse`, contacts disabled) → the 6-D base wrench W the
environment must supply, plus contact-free joint torques; (iii) candidate contacts = collision
geoms within `gap` = 6 cm of the plane (exact geom distances); (iv) two solves over pyramidal
friction-cone generators at those contacts: NNLS for the unconstrained residual, and a
torque-limited LP (cone coefficients + L1 wrench slack, joint torques constrained to actuator
force ranges) for the **smallest unsupported wrench any controller could leave**. Clip features:
`airborne_frac` (no candidate contact), `infeasible_frac` (torque-limited unsupported > ½ weight),
`unsupported_impulse_per_weight_s` (seconds of free-fall equivalent), `torque_infeasible_frac`,
each under a uniform-μ and the simulator's own per-geom contact model. ~1 CPU-second per clip.

Stated limits: plane-only terrain; **true ballistic flight is exempt by construction** (a body in
free fall demands no support — q̈ ≈ g leaves no unsupported wrench), though non-ballistic floating
around take-offs is flagged, correctly (§4); the screen certifies the *retargeted output on the
target robot*, never the source mocap. The `gap` choice matters and is justified rather than assumed [measured;
`reports/N1_gap_sensitivity.json`]: at 3 cm even the feasible control is flagged 42 % (the bank
carries a systematic ~3 cm stance-clearance offset from retarget ground alignment, so real
contacts sit just outside a 3 cm band); at 10 cm the screen degenerates the other way (geometry
7–10 cm airborne is granted as a contact candidate and the attractor's descent reads 0 %
infeasible). 6 cm sits between the two failure modes — above the bank's clearance offset, below
physically bridgeable distance. The ½-weight bound is not delicate: the attractor's flagged-frame
fraction moves only 15.1 % → 13.1 % → 12.5 % across bounds of 0.25/0.5/0.75× weight, because the
flagged mass concentrates near 1× weight.
Tool: **refeas v0.1.0** (Apache-2.0; MuJoCo + SciPy; G1 worked example whose synthetic hover clip
is flagged at 45 % infeasible — `refeas/examples/demo_hover_brief.json`).

## 3. Validation on the clip that mattered

Phase-resolved verdict for the attractor clip [measured; `reports/N1_clip44_knee_id.json`]:
standing 0–0.75 s supported (torque-limited residual 0 N); descent 0.75–1.75 s **airborne in
86 % of frames, median unsupported 329 N**; kneel/crawl 1.75–7.25 s fully supportable within
actuator limits *even with the simulator's frictionless knees*; rise 8.0–8.5 s airborne again;
final stand supported. A matched-easy control from the same bank is supported at every frame
(torque ratio p95 0.66) [measured; `reports/N1_CMU76_knee_id.json`]. The family is systematic:
20 of the clip's 40 nearest kneel/crawl neighbours exceed the 10 %-infeasible-frame threshold
[measured; `reports/N3_candidate_feasibility.json`].

Independent corroboration, from rollouts that never see the screen: with a calibrated
paired-rollout statistic (signed replicate-mean effects over a published identical-physics floor
of ≈ 0 ± 1 mm — the floor matters because identical physics already diverges 2.5–8 mm within
seconds; `reports/G1/run0/g1_v2_summary.json`), **+15 % motor strength worsens body-position
tracking by +15.0/+16.0 mm exactly inside the screen-flagged airborne window and ≈ 0 mm
(+0.3/−1.4) in the supported standing window, replicated across two IC-seed sets
(instrument-wide agreement across all 36 axis×clip effects: r = 0.92)** [exploratory — two cases; `plan/N5_RESULT.md`,
`reports/G1/run1_seed1/g1_v2_summary.json`]. A generality test on 12 family clips vs 12 feasible
controls is pre-registered with three pass criteria [pending 🕐; `plan/PREREGISTRATION_P_SIGN.md`
`c7916e8c`] and does no load-bearing work in this note.

## 4. Prevalence

Bank-wide screen — AMASS→Unitree-G1, this pipeline, this robot (10,705 clips) [measured;
`reports/feasibility_all/prevalence_report.txt`, sentinel `COMPLETED`]:

| category | n | > 10 % infeasible frames | > 25 % | duration share flagged |
|---|---:|---:|---:|---:|
| dynamic | 804 | 58.6 % | 32.6 % | 54.5 % |
| ground-contact | 175 | 39.4 % | 18.3 % | 44.1 % |
| locomotion | 5,591 | 24.5 % | 17.4 % | 31.2 % |
| quiet | 4,135 | 12.9 % | 7.5 % | 19.8 % |
| **all** | **10,705** | **22.8 %** | 14.8 % | 27.4 % |

By source: GRAB 0.1 %, TCD 1.6 %, KIT 16.5 %, BMLmovi 21.8 %, Eyes-Japan 23.2 %, BMLhandball
27.4 %, CMU 39.7 %, ACCAD 41.7 %, HUMAN4D 55.4 %, Transitions 89.6 %, **CNRS 100 %** — three
orders of magnitude of spread under one retargeter and one robot. Hand-checks of the extremes
[measured; `reports/upstream_drafts/CNRS_AUDIT.md`]: the CNRS clips are *ordinary fast walks*
whose retargeted trajectory rides ~4–5 cm high — in the median frame nothing on the robot is
within 6 cm of the floor (median lowest-geom clearance 6.2–7.7 cm; contact only momentary) — the
"lift the limb, not lower the root" failure expressed continuously; Transitions is genuinely
acrobatic content whose *flagged frames* are non-ballistic floating around take-off/landing
(per-clip severity moderate: 22 % vs CNRS's 57–66 %). The dynamic category's rate is partially
content-inflated the same way; the ground category's 39 % cannot be, and is the attractor's
family writ large. *Figure 2 [measured]: `paper/figures/f4_prevalence.png` (script
`f4_prevalence.py`, data `reports/feasibility_all/feasibility.csv`).*

## 5. Downstream costs

**Samplers** [sealed ✓]: a failure-weighted curriculum reads "impossible" as "maximally
informative" (§1). **Evaluation** [measured]: 29/100 of our held-out clips are flagged; flagged clips score 6.0–8.4 points below each policy's all-clips aggregate (8.4–11.8 below its
feasible stratum; `reports/N_atlas_v21.json` endpoints_2b) and cannot separate training methods — the
grounded-vs-uniform endpoint edge is +0.025 on feasible clips and −0.009 on infeasible ones
(`reports/N_atlas_v21.json` endpoints_2b). Our project now reports feasibility-stratified
endpoints under a sealed policy whose threshold predates it
(`plan/GLOBAL_EVAL_ADDENDUM.md` `a93a87a0`). **Difficulty labels** [sealed ✓ / sealed null kept]:
reference-feature difficulty models transfer across policies at ρ = 0.567–0.579; adding the three
screen features moves all six transfer pairs in the right direction, four significantly beyond a
200-draw random-feature baseline (headline 0.567 → 0.609, p = 0.010)
(`reports/N_atlas_v21.json`); bank-relative *support* features alone did not clear the same
baseline — a sealed null we keep (`reports/N2_atlas_support.json`). **A bounded near-miss**
[sealed null, kept]: a second reference artifact — hand–hip interpenetration > 1 cm on a median
13 % of frames, taxing the self-collision reward on accurate tracking — does *not* predict
difficulty beyond the feasibility flag (heldout partial ρ −0.04…−0.15, no positive CI on any
arm, sealed rule 0/3; `plan/P_TAX_RESULT.md`, `reports/P_TAX_result.json`). It remains a
hygiene recommendation, not a claim.

## 6. The harness had to be proven first (and the proof is version-pinned)

None of §3's rollout numbers would be meaningful over a broken coupling. Before any of them, the
same engine (MuJoCo Warp 3.11.0) reached through two integration stacks — mjlab v1.6.0 directly
vs Newton `7bb6d02d` via SolverMuJoCo, with classic MuJoCo 3.11.0 (C) as third referee — was
driven to per-substep agreement |Δq̇| ≤ 3×10⁻⁵ rad/s, after a four-stage elimination surfaced
four silent coupling errors whose combined effect (a 40-point survival fork with matching mean
error) we had initially misread as a physics finding and formally withdrew [measured + withdrawn
verdict; `plan/S1_RESULT.md`, `reports/S1_KIT1226_n32_absorb.json`]. The generalised checklist —
nine error classes, each with symptom, detector, and instance — is this note's Appendix A and
ships in the tool's docs. The certificate is a property of the pinned version pair (release numbering of the Newton line
differs from this checkout's package metadata; the commit hash is the pin); a re-certification
against Newton 1.0 GA (which changed the collision stack) is specified as future work
[pending 🕐; `plan/SPEC_newton_recert.md`].

## 7. Recommendations

1. **Screen before training** (~1 CPU-s/clip); publish per-clip feasibility flags with datasets.
2. **Report feasibility-stratified endpoints**; never average survival over start offsets that
   straddle infeasible segments.
3. **Retargeting pipelines**: resolve unreachable postures by root-height/contact projection, not
   limb lifting; add a per-source stance-contact consistency pass (the CNRS class); audit reward
   terms against the reference itself.
4. **Couplings**: certify any second physics stack at the substep level against the Appendix-A
   checklist before believing closed-loop differences; pin and publish both stack versions.
5. For flagged-but-wanted motions: repair, don't just drop [pending 🕐 — repair experiment
   sealed-after-N3, `plan/N7_DRAFT_repair.md`].

## Appendix A — coupling-error taxonomy

(→ `appendix_coupling_taxonomy.md`, shipped verbatim; also `refeas/docs/COUPLING_TAXONOMY.md`.)

---
*Pre-registered future work referenced with hashes, none load-bearing here: N3 composition
causality `af1b7c9f` 🕐; E3 support moderation `2c38845b` 🕐; P-SIGN `c7916e8c` 🕐; N7 repair
(seal pending N3). Figures: F1 anatomy, F2 prevalence — scripts + data in `paper/RESULTS_LOG.md`.
Author list / acknowledgements TBD with Linji. Upstream note drafts are separate documents
awaiting approval (`reports/upstream_drafts/`).*

## 5b. What tracking an infeasible reference does — measured in sim, predicted for hardware

*(Added v0.3, 2026-08-20; requires review before submission — logged in REVIEW addendum.)*

Measured [`reports/effort_sat_at_fall.json`, from `reports/G1/run0/armA.npz`]: tracking the
airborne descent, **zero of 29 actuators saturate at any point in the supported phase; within
0.6 s of the post-airborne contact event, 5/29 actuators (wrists, waist) pin at ≥ 98 % of force
range, in 8/8 replicates**. The failure mode is not gradual degradation — it is a commanded hover
ending in an unplanned ~0.3 m fall onto joints that are not landing gear (estimated ~2.4 m/s
touchdown, ~95 J to dissipate [estimate]). Predicted hardware phenomenology [exploratory,
sim-grounded, no hardware claims]: impact loading on wrists/knees at every attempt of the
segment; current/thermal-limit bursts invisible in average torque; and — per the sign-reversal
mechanism [exploratory; `plan/P_SIGN_PREP.md`] — *gain increases make these segments worse*, so
the standard sim-to-real reflex of stiffening the controller is counter-productive exactly here.
The G1 gate adds a fourth cost [sealed ✗, kept]: no physics randomisation changes the outcome, so
DR budget spent on these segments buys nothing. Practical consequence: the screen is a
1-CPU-second **pre-deployment safety filter**, and its runtime complement — flag a segment when
tightening gains worsens tracking — is exactly the pre-registered P-SIGN detector [pending 🕐].
