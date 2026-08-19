# DRAFT — NOT FILED. For Linji's approval. Target: whole_body_tracking (BeyondMimic) issue tracker.

**Title: Retargeted AMASS references can be dynamically infeasible on the G1: airborne transitions
needing ~body weight of support with no contact available (22.8 % of a 10.7k-clip bank affected at
the >10 %-of-frames level)**

Thanks again for the quick engagement on #73 — this is a companion data-quality finding from the
same project, this time about the *retargeting output* rather than the sampler.

## Summary

Screening the retargeted-to-G1 AMASS bank (the `train_converted_complete` CSV release, 10,705
clips after conversion) with a per-frame dynamic-feasibility test — contact-free inverse dynamics
for the base wrench the environment must supply, then a torque-limited LP over friction cones at
the contacts actually available within 6 cm of the plane — we find:

- **22.8 % of clips have > 10 % dynamically infeasible frames** (torque-limited unsupported wrench
  above half the robot's weight); 14.8 % exceed 25 % of frames.
- By motion category: ground-contact clips 39 %, dynamic 59 %, locomotion 25 %, quiet 13 %.
- By source dataset the rate ranges from **0.1 % (GRAB) to 100 % (CNRS)**, with Transitions at
  90 % — pointing at pipeline/source interaction rather than motion difficulty.

## Minimal reproduction (one clip)

`BMLmovi_Subject_64_F_MoSh_Subject_64_F_9_poses_120_jpos` (a kneel-down-to-crawl motion). The
retargeted descent, 0.75–1.75 s, has **no collision geom within 6 cm of the floor** — the feet
float 7–10 cm above the plane while the pelvis drops 0.79 → 0.40 m — so ~329 N ≈ the G1's full
weight is unsupported for a second; the rise at 8.0–8.5 s repeats it. Kinematically the clip is
clean (zero joint-limit violations, ≤ 5.6 rad/s). See attached
`clip44_airborne_repro.png` (stick frames + unsupported-force trace) and the screen output.
Plausible mechanism: the human sits back onto the heels; the G1's leg cannot fold that far, and
the retarget resolves the conflict by lifting the whole leg instead of lowering the root.

Downstream this is not cosmetic: this clip is the single worst training attractor in our
curriculum experiments — a failure-weighted sampler (see #73) locks onto it precisely because no
policy can track a hovering reference, and 12+ of its 40 nearest neighbours (BMLmovi/CMU sit-kneel
family) carry the same artefact. A second systematic defect the screen surfaces: hand–hip/thigh
interpenetration on the reference (present in > 1 cm depth on a median 13 % of frames bank-wide),
which self-collision reward terms then charge against the policy for tracking accurately.

## Scope

The artefact is demonstrated in the **retarget-to-G1 output**; we make no claim about the source
mocap (CNRS/Transitions rates suggest source conventions — e.g. units/skeleton — interact with the
pipeline; we have not root-caused that side). Screen tool (Apache-2.0, ~1 CPU-s/clip, MuJoCo +
SciPy only): [refeas v0.1.0 — link]. Happy to share per-clip flags for the full bank.

## Suggested actions

1. A feasibility screen in the retarget release pipeline (we're glad to upstream ours).
2. Ground-contact-aware root-height resolution for postures the target robot cannot reach
   (kneel/sit family), instead of leg lifting.
3. Publishing per-clip feasibility flags with the dataset so training/eval code can stratify.

*(Attachments: clip44_airborne_repro.png, demo screen JSON, per-source prevalence table.)*
