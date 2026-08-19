# TASK cnrs-audit — hand-check of the extreme sources (2026-08-20)

*Status labels: measured. Artifacts: this file + per-clip numbers below recomputed live from
`bank/amass/*.npz` with the pinned screen model; screen values from
`reports/feasibility_all/feasibility.csv`. UNVERIFIED: none.*

## CNRS (3 of 79 clips hand-checked: CNRS_283_-01_L_1, _L_2, _R_1)

| check | finding |
|---|---|
| units / skeleton | retarget output is G1-sized (ankle→torso span median 0.75 m, matches other sources) — no unit-scale error in the output |
| frame rate | 50 fps as converted; durations 4.9–6.7 s; consistent |
| motion content | **ordinary fast locomotion**: root xy drift 6.9–7.4 m per clip, root z median 0.81–0.84 m |
| floor / root convention | **the defect**: minimum geom-to-plane distance has median **6.2–7.7 cm** and p90 10.7–12.9 cm — i.e. in the median frame *nothing* on the robot is within 6 cm of the floor. The feet dip to contact (min −0.7 to 0.0 cm) only momentarily. Root z median 0.81–0.84 vs the G1's 0.79 standing height — the whole trajectory rides ~4–5 cm high, and swing+stance clearances ride with it |
| screen agreement | screen said infeasible 0.57–0.66 / airborne 0.52–0.64; hand-check reproduces (54–64 % of frames no geom within 6 cm) |
| other artifacts | CNRS_283_-01_L_1 has a 40.1 rad/s joint-velocity spike (retarget glitch); siblings 9–10 rad/s |

**Verdict: ingest/retarget interaction, not motion content.** A walking human retargeted with a
root-height convention that leaves the G1's feet ~5–8 cm off the floor for most of every stride.
Plausible mechanism: subject-calibration/leg-length handling for this subset (root height carried
from the human's proportions while the G1's shorter legs hang, feet floating) — the same "lift the
limb instead of lowering the root" family as clip #44, expressed continuously instead of at one
transition. 100 % flag rate follows: every clip is a walk, and every walk floats.

## Transitions (1 of 106 hand-checked: mocap_mazen_airkick_jumpinplace)

| check | finding |
|---|---|
| motion content | genuinely acrobatic (jump in place; subset is airkicks/twists/long-jumps); root z 0.62–1.09 m; xy drift 0.04 m — content is as labeled |
| screen semantics | infeasible 0.22 / airborne 0.30. Important: **true ballistic flight does not trigger the infeasible flag** (a body in free fall needs no support — q̈ ≈ g leaves no unsupported wrench), so the 22 % is *non-ballistic* airborne dynamics: preparation/landing frames floating with near-zero acceleration |
| floor | median lowest-geom distance 3.6 cm (reasonable), p90 10.7 cm |

**Verdict: mixed.** The 90 % source-level flag rate over-indexes on acrobatic content, but the
flagged *frames* are still artifacts (floating at ~0 acceleration is not flight); the per-clip
severity is much lower than CNRS (0.22 vs 0.57–0.66 median infeasible).

## Consequences for the dataset advisory (wording changes applied to the draft)

1. CNRS: state the mechanism concretely — *systematic root-height elevation leaving feet 5–8 cm
   airborne during ordinary locomotion; output-side; reproducible on any clip of the subset* —
   and drop any implication that the source mocap is at fault (the walk itself is fine).
2. Transitions: soften to "flag rate inflated by acrobatic content; flagged frames are
   non-ballistic floating (the screen already exempts true free fall); per-clip severity moderate."
3. Both: the advisory's ask becomes sharper — a *root-height/contact consistency pass per source
   subset* would catch CNRS-class defects wholesale; per-clip flags catch the rest.
4. Add the 40 rad/s velocity-spike observation as a secondary QC item (one clip; not quantified
   bank-wide — labeled exploratory).

Advisory draft updated accordingly (`DRAFT_dataset_advisory_extreme_sources.md`); **still not
filed — awaiting Linji's approval** per D2c.
