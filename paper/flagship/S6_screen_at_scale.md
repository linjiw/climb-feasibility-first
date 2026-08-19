# 6. The feasibility screen at scale (compressed; method and full tables in the companion note)

**Method.** For each frame of a retargeted reference: (i) q, q̇ from the clip and q̈ by central
differences; (ii) contact-free inverse dynamics (MuJoCo `mj_inverse`, contacts disabled) → the
6-D base wrench W the environment must supply and the joint torques with no contact; (iii) candidate
contacts = collision geoms within 6 cm of the plane (`mj_geomDistance`, nearest point);
(iv) contact forces in pyramidal friction cones (μ 0.6, or frictionless non-foot geoms for the sim
model) that best explain W — an NNLS for the unconstrained residual and a torque-limited LP for the
smallest unsupported wrench achievable within actuator force ranges. Per-clip features: airborne
fraction (no candidate contact), infeasible fraction (torque-limited unsupported wrench > ½ weight),
unsupported impulse per weight, torque-infeasible fraction. ~1 s per clip on one CPU core.

**#44.** Standing (0–0.75 s): supported. **Descent 0.75–1.75 s: no collision geom within 6 cm of the
floor** — the feet float 7–10 cm above it while the pelvis falls 0.79 → 0.40 m — leaving 329 N ≈ body
weight (327 N) unsupported in 86 % of frames; the retargeted human sat back onto the heels, the G1's
leg cannot fold that far, and the retarget lifted the whole leg. Kneel/crawl 1.75–7.25 s: fully
supportable by shins, thighs, hands and feet within actuator limits, even with frictionless knees.
Rise 8.0–8.5 s: airborne again (250–330 N). The policy's tracking error starts growing exactly at
0.75 s and every world dies at 2.2–3.0 s. Kinematically the clip is ordinary (no joint-limit
violations, ≤ 5.6 rad/s), which is why the atlas's kinematic features could not see it.

**Prevalence** (10,705 clips, ~1 CPU-s each; `reports/feasibility_all/prevalence_report.txt`,
sentinel `reports/feasibility_all/COMPLETED`): **22.8 % of the bank exceeds 10 % dynamically
infeasible frames** — ground-contact category 39 %, dynamic 59 %, locomotion 25 %, quiet 13 % —
and by source dataset the rate spans **0.1 % (GRAB) to 100 % (CNRS)**, Transitions 90 %, CMU 40 %.
A three-orders-of-magnitude spread across sources under one pipeline and one robot is a
pipeline × source property, not a difficulty gradient. Of the attractor's 40 nearest kneel/crawl
neighbours, 20 exceed the threshold; the KIT kneel_down_to_crawl clips sit at 3–8 %.

**Evaluation-set contamination.** 29 of our own 100 held-out clips are flagged. They depress every
policy's aggregate by 6–11 points and cannot separate samplers (§4). Policy, sealed before any new
number existed (`plan/GLOBAL_EVAL_ADDENDUM.md`, `a93a87a0…`): primary endpoints on the
feasible-only stratum, all-clips secondary, infeasible-only descriptive; the threshold's
provenance (it predates the policy) is recorded in the seal. We do not swap the evaluation set
mid-project.

**A second hygiene finding, and a null.** Reference poses also carry hand–hip interpenetration
(> 1 cm on a median 13 % of frames; 53 % of clips exceed 10 %), so the self-collision penalty is
charged against accurate tracking. Sealed test P-TAX (`plan/PREREGISTRATION_P_TAX.md`,
`7960057a…`) asked whether this tax predicts difficulty beyond the feasibility flag: **it does
not** (heldout partial ρ −0.04 to −0.15, no positive CI excluding zero on any arm — sealed rule
0/3; `plan/P_TAX_RESULT.md`, `reports/P_TAX_result.json`). It remains a recommendation — audit
reward terms against the reference, not only the policy — and nothing more.

**Consequence for the argument** (details §5, slots §8)**.** #44 decomposes into a physically impossible transition and a
feasible skill the bank does not contain. The two are separable by start offset, and the
pre-registered composition experiment (N3) conditions on it: augmentation is predicted to make the
kneel/crawl phase trackable and to leave the descent unlearnable; a later repair experiment (N7)
projects the transition back onto contact and predicts the descent becomes learnable and the
motor-strength sign reversal disappears.
