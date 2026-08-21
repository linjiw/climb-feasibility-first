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
sentinel `reports/feasibility_all/COMPLETED`): **22.8 % of this AMASS→G1 bank exceeds 10 % dynamically
infeasible frames** — ground-contact category 39 %, dynamic 59 %, locomotion 25 %, quiet 13 % —
and by source dataset the rate spans **0.1 % (GRAB) to 100 % (CNRS)**, Transitions 90 %, CMU 40 %.
A three-orders-of-magnitude spread across sources under one pipeline and one robot is a
source-corpus × pipeline property, not a difficulty gradient. Of the attractor's 40 nearest kneel/crawl
neighbours, 20 exceed the threshold; the KIT kneel_down_to_crawl clips sit at 3–8 %.

**Cross-bank: the rate belongs to a corpus-and-pipeline pairing, not to retargeting as such**
[measured; pre-registered; independent re-implementation]. 22.8 % is a measurement of *one*
pipeline. The same method — re-implemented independently against a different G1 model
(`g1_29dof_rev_1_0.xml`, sha `15a330f1…`; μ 0.7 rather than 0.6, identical 6 cm gap and ½-weight
bound) — was run over all 4,950 clips of the BONES-SEED bank that trains SONIC [NVIDIA GEAR,
arXiv:2511.07820]: **7 clips (0.14 %) exceed 10 % infeasible frames, against 22.8 % here — a
factor of 160**, and 0.09 % of duration against 27.4 %. The measurement was pre-registered with
its consequence pre-committed — a rate under 10 % descopes the planned SONIC training ablation —
and the ablation is descoped (P10, `GR00T-WholeBodyControl/docs/prediction_register.md`; screen
`gear_sonic/research/hygiene/screen.py`, 4,950 clips in 131.7 s wall on 8 CPU workers, 0 failures).
This is not "SONIC is clean and AMASS is broken". The class is *present* in the cleaner bank —
111 clips (2.24 %) exceed 10 % airborne frames, and five of the seven flagged clips are jumps —
four named for the 50 cm box they use, which is absent from the flat scene — a real defect that
passed both kinematic QC and a shipped release filter, though a different defect: a scene mismatch
whose fix is terrain or exclusion, not root projection (§8.2). What the contrast establishes is
methodological: **infeasibility prevalence is a property of a particular corpus-and-pipeline
pairing and must be measured per corpus, never carried over.** At 0.145 CPU-seconds per clip in
that implementation (0.84 ms per screened frame; ~1 CPU-s in ours), minutes per corpus, that
measurement is affordable as a standing release gate rather than a one-off audit. Caveat carried:
the two banks are different source corpora screened by two implementations of one method, with a
shipped release filter on one side only, so the comparison bounds generality rather than isolating
the retargeter — the controlled version (two retargeters, same source clips) remains parked (§10).

The same run is also the sharpest evidence that *airborne* and *infeasible* must remain separate
axes: seven `kneeling_loop_*` clips sit at airborne fraction 1.000 with infeasible fraction 0.000 —
feet 7–9 cm off the floor for the whole clip, weight carried on the knees, supportable at every
frame. A filter that read "airborne" as "broken" would delete exactly the rare ground-contact
behaviour these banks are short of (3.2 % of our training duration, §5.3).

**Evaluation-set contamination.** 29 of our own 100 held-out clips are flagged. They score 6.0–8.4 points below each policy's
all-clips aggregate (8.4–11.8 below its feasible stratum; `reports/N_atlas_v21.json`) and cannot
separate samplers (§4). Policy, sealed before any new
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

**Consequence for the argument** (details §5, readout §8)**.** #44's reference still decomposes
physically into an impossible transition and a feasible skill the bank scarcely contains, but N3
shows that this physical phase boundary is not a learning boundary: ground16 augmentation raises
kneel/crawl survival to 0.750 in both seeds **and** unexpectedly raises descent survival to
1.000/0.688. Its adaptive arm regresses, triggering the preflight stop on an unqualified causal
claim. N7 must therefore compare repair, keep, and prune directly rather than assume only repair
can move the descent.

**What hygiene costs, and what segment-level curation returns** [measured]. Clip-level pruning is
the blunt instrument, and it is what our own sealed hygiene arm uses: on `tier_800` the screen
flags 99 clips = 20.2 min of the bank's 152.4 min, so pruning discards **13.3 % of its duration**.
Re-screening those 99 clips at segment resolution (`tools/screen_segments.py` over per-frame screen
output; 99 clips in 45 s wall on 6 nice'd CPU workers) shows most of that is feasible material.
With no reference lookahead — mjlab's tracking observation is the current anchor only, guard 0 s —
contiguous feasible segments recover **12.5 of the 20.2 min (61.7 %)**, 584 of 1,259 sampler bins
stay usable, and only **3 of 99** clips are lost end to end: 8.2 % of the bank handed back. Widen
the guard band to 1.0 s, which is what an observation carrying 10 × 0.1 s of future reference
requires, and recovery falls to 5.8 min (28.9 %), 305 bins, 26 of 99 clips lost — 3.8 % of the
bank. Identical screen, identical clips: **the value of segment-level curation falls as the
policy's reference lookahead grows**, which makes the guard band a property of the framework, not
of the data. Pruning is therefore a lower bound on what feasibility hygiene can buy, not its
ceiling — the other route is repair, and the legacy operator recovers 1,606 of the strict 2,442
flagged clips bank-wide (65.8%; the historical 2,443-row directory includes one feasible no-op
control; `reports/dfrp_v0/census/summary.md`; §8.2). Caveat: the 1.0 s minimum segment
length and the strict bin-eligibility rule (any severe frame disqualifies a bin) are choices, not
measurements, and the recovery figures are *duration* claims — no training arm has yet consumed
curated segments.

**Deployment implication (measured in sim; hardware phenomenology predicted, labeled).** Tracking
the airborne descent saturates zero actuators until support is lost, then pins ≥ 4/29 at ≥ 98 %
force range within 0.6 s in 8/8 replicates — exactly 5/29 in 7/8, mean 16.8 %
(`reports/effort_sat_at_fall.json`) — an unplanned ~0.3 m fall
onto wrists and knees at every attempt. G1 showed no physics parameter rescues the original
outcome [sealed ✗, kept], so the offline screen functions as a pre-deployment safety filter:
1 CPU-second per clip against impact retries, current-limit bursts, and wasted DR budget on
unfixable segments. P-SIGN rejects the proposed runtime complement [sealed ✗: 7/12 family,
4/12 clean controls, 2/7 localised], so gain response must not be used as an online
infeasibility detector.
