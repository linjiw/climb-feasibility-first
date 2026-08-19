# DRAFT — NOT FILED. For Linji's approval. Target: dataset-level advisory (AMASS community /
# dataset maintainers of the affected subsets; venue to be decided with the retargeting note).

**Title: Advisory — two AMASS subsets produce near-universally infeasible G1 retargets
(CNRS 100 %, Transitions 90 % of clips flagged)**

## What we measured

Dynamic feasibility of retargeted-to-Unitree-G1 references (whole_body_tracking pipeline output),
per frame: can the base wrench demanded by the reference motion be supplied by any contact forces
within friction cones at the contacts available (≤ 6 cm to the plane), within actuator torque
limits? Clip flag: > 10 % of frames infeasible (unsupported wrench > ½ robot weight).

## Finding

| source subset | clips in bank | flagged |
|---|---:|---:|
| CNRS | 79 | **100 %** |
| Transitions | 106 | **89.6 %** |
| HUMAN4D | 121 | 55.4 % |
| ACCAD | 230 | 41.7 % |
| CMU | 1,978 | 39.7 % |
| … | | |
| GRAB | 1,340 | 0.1 % |
| TCD | 62 | 1.6 % |
| **all** | **10,705** | **22.8 %** |

A 0.1 %-to-100 % spread across sources under one retargeting pipeline and one robot is not a
motion-difficulty gradient. Hand-checks (2026-08-20, `CNRS_AUDIT.md`) pin the mechanisms:

- **CNRS (100 % flagged):** the clips are *ordinary fast walks* (6.9–7.4 m of root travel in
  5–7 s) whose retargeted trajectory rides ~4–5 cm high — in the median frame **no part of the
  robot is within 6 cm of the floor** (median lowest-geom clearance 6.2–7.7 cm; feet dip to
  contact only momentarily). The source motion is fine; the output floats. This is a subset-wide
  root-height/leg-length convention interaction — the "lift the limb instead of lowering the
  root" failure expressed continuously.
- **Transitions (90 % flagged):** genuinely acrobatic content (airkicks, jumps, twists), so the
  rate over-indexes on content — but the screen already exempts true ballistic flight (a body in
  free fall demands no support), so the flagged frames are *non-ballistic floating* around
  take-off and landing; per-clip severity is moderate (e.g. jump-in-place: 22 % infeasible vs
  CNRS's 57–66 %).

One secondary QC observation (exploratory, one clip): a 40 rad/s joint-velocity spike in
CNRS_283_-01_L_1 — a retarget glitch class our screen does not target.

## Why it matters

These clips enter humanoid-tracking training banks silently: they pass kinematic QC (joint limits,
velocities, smoothness). Downstream they (a) poison failure-adaptive samplers — a failure-weighted
curriculum locks onto motions that are impossible rather than hard (documented case:
whole_body_tracking #73 companion); (b) contaminate evaluation sets — in our 100-clip held-out
set, 29 clips are flagged and score 6.0–8.4 points below each policy's all-clips aggregate; (c) corrupt difficulty
labels used for curricula and benchmarks.

## Ask

- Treat per-robot dynamic feasibility as a release-time QC dimension alongside kinematic checks
  (tool: refeas v0.1.0, Apache-2.0, ~1 CPU-s/clip).
- For CNRS-class defects: a per-source *root-height/contact consistency pass* (stance feet should
  touch the floor during locomotion) would catch entire subsets wholesale; per-clip flags catch
  the remainder.
- For Transitions-class content: report airborne and infeasible fractions separately (the screen
  distinguishes them; free fall is exempt from the infeasible flag).
- We are demonstrating an artifact of the *retargeted output*; the source mocap itself may be
  fine — the advisory is about the pairing.

*(Attachments: full per-source table, clip44_airborne_repro.png as the worked anatomy, tool link.)*
