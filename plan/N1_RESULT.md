# N1 — knee-contact inverse dynamics of clip #44's reference (2026-08-18)

**Tool:** `tools/n1_knee_id.py` (MuJoCo CPU; contact-free `mj_inverse` → base wrench W the
environment must supply; contact candidates = collision geoms within `gap` of the plane
(`mj_geomDistance`); pyramidal-cone NNLS for the unconstrained residual and a torque-limited LP
(HiGHS) for the smallest unsupported wrench achievable within actuator force ranges). Two contact
models: *real* (μ 0.6 everywhere) and *sim* (feet 0.6, non-foot geoms frictionless as in mjlab's
G1). Reference velocities/accelerations by central differences with 5-frame smoothing.
Outputs: `reports/N1_clip44_knee_id.json` (gap 6 cm), `reports/N1_CMU76_knee_id.json` (control).

## Result: the reference is dynamically **infeasible in the descent and the rise**, and feasible in the kneel/crawl itself

| phase (clip time) | contacts within 6 cm | unsupported force, unconstrained (median) | torque-limited residual (median) | frames with no contact at all |
|---|---|---:|---:|---:|
| stand 0–0.75 s | 14 foot capsules | 0 N | 0 N | 5 % |
| **descent 0.75–1.75 s** | **none** (feet 7–10 cm above the ground while the pelvis drops 0.79 → 0.40 m) | **329 N ≈ body weight (327 N)** | 22 N (only where a contact exists) | **86 %** |
| kneel / crawl 1.75–7.25 s | shins, thighs, hands, feet | 0 N | 0 N, all frames within actuator limits (both contact models) | 0 % |
| **rise 7.25–8.75 s** | right foot + shin, then feet | 37 N; 250–330 N in 8.0–8.5 s | 33 N; 166 N at 8.0–8.25 s | 23 % |
| stand 8.75–10 s | feet | 0 N | 0 N | 0 % |

Control: `CMU_76_02` (matched easy) is fully supported at every frame (0 % frames > 100 N,
torque ratio p95 0.66) with the same tool and gap.

Reading. The retargeted human sits back onto the heels; the G1's leg cannot fold that far, so the
retarget lifts the whole leg — for a full second the robot descends 0.4 m with **no foot within
7 cm of the floor**. No contact force can supply the ~1 g of support that phase needs: the reference
asks the robot to hover. The policy's tracking error starts growing at exactly this point (0.5 →
0.75 s onward), and every world dies at 2.2–3.0 s trying to reconcile a hovering reference with a
falling body. The kneel/crawl phase after 1.75 s is a *feasible* motion (knees + hands + feet carry
the weight within torque limits, even with frictionless knees), so the atlas's "ground-contact
family" is not per se infeasible — this clip's *transition into it* is.

Also visible: the standing feet sit 1.5 cm above the plane and the kneeling shins 2–3 cm below it,
so no single per-clip vertical offset (which is what `ground_align_bank.py` applies) reconciles the
clip; the ground-alignment residual is a symptom of the same retarget inconsistency.

## Consequences

1. **Alternative source resolved: impossible reference — YES** (dynamic, not kinematic: joint
   limits and speeds were fine). Together with G1 (no ±δ changes anything) and the start-offset
   check (fails at every offset in the ground segment): #44 is a retarget-infeasible reference on
   the descent, and a policy-coverage question on the kneel/crawl phase after it — the two are
   separable by starting episodes after 1.75 s, which the stratified-start protocol (N4) does.
2. **N3's primary prediction must condition on this.** Augmenting training with kneel/crawl
   neighbours cannot make the descent trackable; the pre-registered endpoint becomes ground-
   segment survival at **stratified start offsets after 1.75 s** (kneel/crawl phase), and the
   descent phase is reported separately as an infeasible segment. If augmentation raises kneel/
   crawl-phase survival, coverage is causal for the feasible part; the descent stays a data-quality
   finding.
3. **A bank-wide screen is now warranted and cheap**: the unsupported-wrench statistic (frames with
   no contact within 6 cm while |W| > 0.5·weight) is a physics-grounded retarget-quality feature
   the atlas lacks. `foot_clearance_p50` (83rd pct for #44) and `support_margin_mean` (5th pct)
   were its proxies. Adding it to N2's atlas is a one-line extension of `n1_knee_id.py`; running it
   over tier_mixed100 and the 800 bank is ~1 CPU-hour with 16 workers.
4. The G1 verdict stands (not a physics-fragility clip); its narrative sharpens: **airborne
   reference → policy cannot track → coverage story applies only to the feasible kneel/crawl
   phase.**
