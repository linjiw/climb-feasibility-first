# G1 — the clip #44 gate: result

**Run:** 2026-08-17 23:05–23:30 EDT, `reports/G1/run0/` (meta, armA/B/C.npz, `g1_summary.json`,
`g1_tables.md`, `fig_F_body_pos_err.png`). Pre-registration `PREREGISTRATION_G1_clip44.md`
(sealed `41e4b20c…`, addendum `2a9ceaca…`) — analysed exactly as written by `tools/analyze_g1.py`.
480 worlds: 6 clips × 8 replicate initial conditions × 10 configurations, arm A (Newton, paired
±δ), arm B (Newton, non-foot contacts frictional), arm C (stock mjlab, noise floor). G0 was
closed before the run (`S1_RESULT.md`).

## Verdict: **G1 does not pass.** Clip #44's failure is not attributable to any of the five physical mechanisms; the alternative-source check points to policy representation failure.

### The pre-registered statistics

Clip-level fragility (mean |Δ body_pos_err| over paired-alive frames, ratio to the matched-easy mean; the same-solver floor is the identical-physics pairing A-base vs C-base):

| axis | #44 (BMLmovi_64_9) | easy CMU_76 | easy BMLhandball | hard 50027 jump | hard 50025 jump | dyn CMU_35 |
|---|---:|---:|---:|---:|---:|---:|
| delay +20 ms | 1.43 | 0.64 | 1.36 | 2.12 | 1.72 | 2.48 |
| motor ±15 % | **2.16** | 0.62 | 1.38 | 1.36 | 0.66 | 2.21 |
| foot μ 0.4/0.8 | 1.63 | 0.64 | 1.36 | 1.28 | 0.98 | 2.29 |
| solref 12/28 ms | 0.91 | 0.50 | 1.50 | 1.10 | 0.75 | 0.85 |
| torso CoM ±2 cm | 1.30 | 0.55 | 1.45 | 0.84 | 0.78 | 1.10 |
| non-foot condim 3 | 1.33 | 0.50 | 1.50 | 1.31 | 1.04 | 0.92 |
| signal / floor (max over axes) | 3.0 | 2.1 | 1.4 | 2.0 | 1.0 | 3.2 |

- **P1 fails.** The contact-model axis (1.33×) and the torso-CoM axis (1.30×) are not ≥ 2× the
  easy pair; the one axis above 2× is motor strength (2.16×), which P1 predicted would *not* be
  elevated. And no (clip, axis) reaches the pre-registered 5× same-solver floor — the largest is
  3.2× — so under the pre-registration nothing is reportable as a mechanism signal.
- **P2 partially holds, trivially.** #44's F(t) peaks at 2.5–2.7 s in every axis (peak/median
  5–11), which is *at* the first termination (2.2–2.9 s), not before it — the divergence blows up
  as the robot falls. Only the motor axis is elevated earlier (from ~1.0 s, see figure).
- **P3 holds in the expected direction for the controls** (delay: CMU_35 2.48×, jumps 1.7–2.1×;
  friction: CMU_35 2.29×), but this does not rescue #44.
- **Termination fragility is zero everywhere:** #44 dies in 8/8 replicates in *all ten*
  configurations of arm A and in arm B; the two one-leg-jump clips likewise; the easy pair
  survives 8/8 everywhere. No ±δ changes survival on any clip. Failure times agree across arms
  A and C to ≤ 0.1 s.

### Alternative-source check (v4: run before any expansion)

`g1_alt44.py` (nominal robot, no DR, 4 replicates per start offset, 40 worlds):

| start offset in clip | dies after | at clip time | cause |
|---|---|---|---|
| 0.0 s (standing) | 2.9–3.0 s | 2.9–3.0 s | anchor_pos, ee_body_pos |
| 1.0 / 1.5 / 2.0 s (going down) | 0.9–1.9 s | 2.4–3.3 s | anchor_pos |
| 2.5 / 3.0 / 3.5 s (kneeling) | 0.5–0.7 s | 3.0–4.0 s | anchor_pos (+ee) |
| 4.5 / 6.0 s (crawl) | 0.6–0.9 s | 5.1–6.9 s | anchor_pos (+anchor_ori) |
| 8.0 s (rising) | 2.4–3.3 s | 10.4–11.3 s | ee_body_pos / anchor_ori |

Body-position error grows monotonically from 0.037 m at t = 0 to 0.20 m by 2.0 s while actuator
saturation stays at 0.0–0.2 % — the collapse at 2.75–3.0 s is when wrists/waist finally saturate,
*after* tracking is already lost. Teleported into any ground-support pose the policy loses the
pelvis height within 0.5–0.9 s.

Reading: this is not a physics-parameter sensitivity and not torque limitation. It is the policy
being unable to execute or hold ground-support postures at all — **policy representation /
coverage failure** on the one kneel/crawl clip of its 100-clip tier (nonfoot_ground_frac 99.7th
percentile). The earlier "survival 0.31" was episodes that started after the ground segment.
S3's prediction (a) applies: with no between-configuration spread and failure everywhere, the
reference/policy pair, not the contact model, is the source. Whether the *reference* is also
physically implausible for G1 (retarget of a kneel) is the remaining open question; it is not
answered by ±δ physics.

### Reference-feasibility check (kinematic), run after the gate

`BMLmovi_64_9`: 499 frames at 50 fps; **zero joint-limit violations** against mjlab's G1 ranges
(tolerance 0.02 rad); joint speeds ≤ 5.6 rad/s (mean 0.4–0.7); the pelvis drops 0.80 → 0.42 m
between 1.0 and 1.5 s and stays at 0.40–0.43 m until 7 s (knees at 2–6 cm from 2.0 s, wrists at
0.15–0.25 m). The reference is a fast but kinematically ordinary kneel. The policy loses tracking
exactly during the 1.0–2.0 s drop (error 0.08 → 0.20 m) — i.e. on a feasible descent it never
learned. Dynamic feasibility (inverse-dynamics torques with knee contact) is not computed here;
nothing above suggests it is the limiting factor (saturation ≈ 0 until the fall).

### Exploratory (not pre-registered, reported separately)

Signed effect = mean over replicates of the time-mean (φ⁺ − φ⁻), paired bootstrap 95 % CI:

- **Motor strength sign reversal on #44:** +15 % motor tracks *worse* on #44 (+0.0115 m
  [+0.0092, +0.0138]) and *better* on every other clip (CMU_76 −0.0026\*, BMLhandball −0.0046\*,
  jump 50027 −0.0109\*, CMU_35 −0.0142\*). The elevated motor F(t) on #44 sits in 1.0–2.4 s,
  before the failure. A stiffer robot descends worse. This is a genuine, localised, mechanism-
  specific difference — but it does not change survival, and it is exploratory.
- Delay hurts the dynamic clips (CMU_35 +0.0119\*, jump 50025 +0.0063\*), higher foot friction
  helps them (−0.003 to −0.009\*), frictional knees/hands change nothing anywhere (condim CIs all
  cross zero, including on #44).

### A methodological finding that outranks the gate

The pre-registered fragility statistic — mean |φ⁺ − φ⁻| along paired single trajectories — is
dominated by chaotic divergence: **the identical-physics pairing (Newton vs mjlab, same state,
same policy) already gives 0.0025–0.0084 m of body-position difference**, the same order as every
intervention (0.003–0.019 m). Closed-loop humanoid tracking has a Lyapunov horizon of ~1–2 s at
the millimetre level; single-trajectory paired differences cannot separate mechanism from
divergence at these δ. Signed differences of replicate means (which shrink with R), distributional
distances, or survival/phase-onset statistics must replace |Δφ| in the PhysFrag definition of F.
Recorded here before any Phase 2 design.

### What this does to the plan (v4 rules)

- No expansion to 200/800/10,822 clips on the strength of #44 (v4: "否定则先查 … 不扩到").
- Alternative sources: termination artefact — no (three different terms fire, all reflect a real
  fall); initialisation — no (fails at every start offset); impossible reference — kinematically no (no limit violations, ≤ 5.6 rad/s); dynamically
  unchecked but unindicated (no saturation before the fall); policy representation failure — **yes, indicated**.
- The v4 first-order question "does #44 carry a physics-fragility signature the reference atlas
  missed" is answered *no* for this policy at these δ; the atlas *did* flag it (99.7th percentile
  ground contact) and the mechanism is coverage, which is a curriculum fact, not a physics one.
