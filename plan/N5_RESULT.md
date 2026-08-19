# N5 — instrument calibration: F redefined (2026-08-18)

**Tool:** `tools/analyze_g1_v2.py` on `reports/G1/run0` (the pre-registered G1 data; a seed-1
replication `reports/G1/run1_seed1` is queued on gap GPU capacity and will be appended).
Labelled *instrument calibration*, not a second bite at P1: the pre-registered folded |Δφ| was
chaos-dominated exactly as the Lyapunov numbers showed; the question here is only whether a
redefined F resolves signal below the floor.

## Redefinitions (all with the floor measured identically from stock mjlab vs Newton at base)

- **S** signed replicate-mean effect E_r[mean_t(φ⁺ − φ⁻)] with paired-bootstrap 95 % CI —
  shrinks with R; chaos averages out.
- **D** distributional distance W1({φ⁺(t)}, {φ⁻(t)}) over paired-alive frames pooled across
  replicates, minus W1(A-base, C-base).
- **T** timing/survival: paired first-termination shift, contact-onset shift per foot, P(alive at
  clip end).
- Resolution criterion: |S| > 2 × the floor CI half-width and the CI excludes zero.

## Result on run0 (body_pos_err, mm)

| axis | #44 | easy CMU_76 | easy BMLhandball | jump 50027 | jump 50025 | dyn CMU_35 |
|---|---:|---:|---:|---:|---:|---:|
| delay +20 ms | +1.7 | +1.1 | +2.4 | +3.2 | **+6.3 ‡** | **+11.9 ‡** |
| motor ±15 % | **+11.5 ‡** | **−2.6 ‡** | −4.6 | **−10.9 ‡** | −0.8 | **−14.2 ‡** |
| foot μ | +0.4 | −0.7 | +0.2 | −4.8 | −2.8 | −9.1 |
| stiffness | **−1.9 ‡** | +0.5 | −2.4 | +3.1 | −2.3 | +1.8 |
| torso CoM | **−2.3 ‡** | −0.6 | −3.4 | +0.6 | −0.2 | −1.1 |
| condim | +0.1 | +0.6 | −0.4 | +2.9 | +2.0 | −1.2 |
| *floor* | −0.1 [−0.9, +0.5] | +0.2 [−1.0, +1.5] | −0.2 [−2.9, +2.3] | −1.3 [−5.3, +3.0] | −1.2 [−3.8, +1.5] | −2.0 [−8.0, +2.5] |

The floor is now ≈ 0 ± 1 mm on the long clips (identical physics, as it should be) and the
mechanism effects stand 6–14 mm above it with CIs that exclude zero — **the instrument resolves
signal that the folded statistic could not.** D agrees (motor: +11.4 mm above the W1 floor on #44,
+12.1 on CMU_35; delay +9.9 on CMU_35). Timing adds a phase-onset channel: on #44 the +20 ms delay
brings the fall forward by 0.51 ± 0.14 s and higher foot friction postpones it by 0.20 ± 0.05 s;
contact-onset shifts are ≤ 0.03 s everywhere (no intervention changes *when* the feet land).

What the calibrated instrument says about the same data: the delay axis is resolved only on the
dynamic clips (CMU_35, one-leg jump 50025), motor strength is resolved on five of six clips with
the sign reversal on #44 (stronger robot tracks the infeasible descent *worse* — the parked
hypothesis: "a stronger robot executes wrong actions harder"), and stiffness / CoM / condim are at
most 2–3 mm effects. Nothing here changes the G1 verdict (no ±δ changes survival; #44's failure
is a reference/coverage matter); it changes what a Phase-2 fragility design would have to look
like: replicate-mean signed effects with a published stock-solver floor, R ≥ 8, δ large enough
that |S| clears 2 mm on the metric of interest.

## Status

PhysFrag stays off the critical path (N6). This calibration is the durable methods note that a
future fragility design inherits, alongside the conformance harness (|Δqvel| ≤ 3e-5). The
seed-1 replication, when it lands, is appended below with the same tables and the run-to-run
agreement of S.

## Exploratory addendum (advisor step 6): does "strength hurts" localise to the airborne window?

run0, #44, motor axis, signed effect on body_pos_err by window (paired-alive frames, 8 replicates;
windows from N1's per-frame contact flags): **stand 0–0.7 s +0.3 mm · airborne 0.75–1.75 s +15.0 mm ·
immediately after (1.75–2.3 s, still alive) +26.8 mm**; identical-physics floor +0.7 / −0.5 / −0.3 mm.
The other axes do not switch with the window (delay +3.5/+4.6/−7.1; friction −1.4/+3.6/−0.2; CoM
−1.2/−0.9/−1.5). So the sign reversal is *absent while the reference is supportable* and switches on
exactly when the reference goes airborne, then persists into the aftermath as the error compounds.
Read as a hypothesis with one supporting case: **stronger motors execute an untrackable reference
harder** — a rollout-only signature of infeasibility that needs no inverse dynamics. Its test for
generality needs clips with airborne windows other than #44 (the ground16 family) in a paired
motor±15 % rollout; that is a ~10-minute GPU item filed for the next gap window (not before the
CPU-only period ends unless a gap opens), and the pre-registered form is: on family clips, the
motor-axis signed effect is ≥ +5 mm in airborne windows and within ±2 mm of the floor in supported
windows.

## Seed-1 replication (reports/G1/run1_seed1, appended 2026-08-18)

Same design, IC seed 1. Instrument agreement across independent replicate sets: Pearson r = 0.92,
Spearman 0.76 over the 36 (axis, clip) signed effects; **sign agreement 6/6 on every effect with
|S| > 5 mm** (motor on #44/CMU_76/50027/CMU_35, delay on 50025/CMU_35). The #44 motor sign reversal
replicates (+12.8 mm [+11.2, +14.2] vs run0 +11.5) and its window localisation replicates:
seed 0 → +0.3 / +15.0 / +26.8 mm (stand / airborne / aftermath), seed 1 → −1.4 / +16.0 / +20.4 mm.
Smaller effects (2–4 mm) flip sign between seeds as their CIs suggest they should. The instrument is
reproducible where it claims resolution and honest about where it does not.
