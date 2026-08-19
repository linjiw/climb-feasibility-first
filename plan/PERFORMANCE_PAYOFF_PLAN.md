# From diagnosis to performance: how the findings buy tracking quality and training efficiency

*Written 2026-08-20 in response to Linji's three issues (causal closure; repair-vs-prune;
sim-to-real impact). Status labels throughout; new numbers below are **measured today from
artifacts on disk** (no sealed experiment touched). Anything requiring a new training run is a
proposal, not a seal.*

## 0. The efficiency ledger — what feasibility hygiene is worth before any retraining

Measured (`reports/wasted_exposure_accounting.json`):

| sampler / scope | exposure currently spent on infeasible content |
|---|---|
| failure-adaptive (as shipped upstream) | **48.8 % of all clip draws over training** go to the one impossible clip (mean top-1 mass across 3 seeds; peak 87–89 %) — and every draw that starts in or before its ground segment produces an episode with a guaranteed unlearnable failure |
| clip-uniform on tier_mixed100 | 25 % of clip draws hit flagged clips; ≈ 6.1 % of drawn frames are infeasible frames |
| bank-wide (10,705 clips) | 22.8 % of clips / 27.4 % of duration flagged; mean infeasible-frame share 9.8 % |

So the *cheapest* payoffs, in order: (1) the grounded sampler already caps the catastrophic case
(sealed ✓ — this is the 0.780 → 0.825 endpoint story); (2) pruning or repairing flagged clips
reclaims ~6–10 % of gradient exposure under uniform sampling and removes the attractor class that
failure-weighting amplifies to ~50 %; (3) the screen costs 1 CPU-s/clip — 3 hours for the whole
bank, against 21,000 GPU-hours for a SONIC-scale training run. **Feasibility hygiene is four to
five orders of magnitude cheaper than the training it protects.**

## 1. Closing the causal loop (issue 1) — what is sealed, what is added

The loop "diagnosis → fix → measured performance gain" closes in three steps, two already sealed:

- **N3 (sealed `af1b7c9f`, preflight frozen)**: composition — do 16 *feasible* kneel/crawl clips
  make the feasible phase trackable? This is the *support* axis's causal test. Runs first GPU
  block after Sept 15.
- **N7 (draft, seal after N3 — now extended, see §2)**: repair — does fixing the impossible
  transition make the *descent* trackable, and does the sign-reversal vanish? This is the
  *feasibility* axis's causal test, now with a prune arm so repair-vs-prune is answered in the
  same run.
- **E-HYG (proposal, needs advisor approval — one rider arm on E3)**: the end-to-end claim at
  scale: `uniform-800-pruned` (drop the 800-bank's flagged clips, hold compute) vs `uniform-800`.
  Endpoints per D1: feasible-only held-out survival (primary), all-clips (secondary), plus
  **zero-shot category generalisation** — survival on held-out *ground-category feasible* clips,
  where pruning hurts if done naively and repair should win. One seed as a rider (~4 GPU-h);
  promotes to the flagship's §8 if approved. This is precisely the "端到端对比" asked for, at the
  minimum compute that makes it credible. *Not run, not sealed — awaiting approval.*

Prediction structure the three share (written now): hygiene helps *because* it redirects exposure,
so gains should concentrate exactly where exposure was being burned — worst-decile clips and the
categories the attractors sat in — and be ≈ 0 on the easy stratum. That signature distinguishes
"data cleaning" from "just fewer clips."

## 2. Repair vs prune (issue 2) — the operator now exists and is measured

**Operator** (`tools/repair_contact_projection.py`, CPU, ~3 s/clip): *kinodynamic contact
projection* — lower the root exactly enough that the lowest collision geom reaches the plane
wherever the reference demands unavailable support, gaussian-blended (0.24 s), never raising,
joints and orientations untouched; FK re-derives body poses, velocities re-differentiated;
re-screened afterwards. Success budget: `infeasible_frac` ≤ 0.05 after repair and ≤ 15 cm max
root adjustment.

**Validation (measured today):**

| clip | infeasible before → after | max root adj. | verdict |
|---|---|---|---|
| #44 (the attractor) | 0.13 → **0.00** | 8.2 cm | ✅ repaired |
| family 27_5 | 0.21 → **0.00** | 9.5 cm | ✅ |
| family 39_8 (worst) | 0.37 → 0.20 | 9.4 cm | needs stronger op (non-airborne infeasibility remains — IK/time-warp class) |
| CNRS walk (of the 100 %-flagged subset) | **0.66 → 0.01** | 13.9 cm | ✅ — root projection rescues the whole subset class |
| Transitions jump | 0.22 → 0.02 | 16.2 cm, +1.68 m/s added vel | ❌ correctly refused — the budget catches over-repair of genuine ballistics |
| CMU_76 control (feasible) | 0.00 → 0.00 | 0.0 cm | ✅ no-op on healthy clips, as required |

**Census complete** (2,443 flagged clips, sentinel `reports/repair_census/COMPLETED`;
2×2 table `reports/repair_census/summary.md`): **65.8 % auto-recoverable** under the ≤ 15 cm /
≤ 5 %-residual budget — 73.1 % of the 10–25 % band, 61.7 % of the > 25 % band; by category:
quiet 80.9 %, ground 68.1 %, locomotion 64.8 %, dynamic 51.2 % (ballistics correctly refused);
by source: BMLhandball 92.5 %, BMLmovi 89.2 %, CNRS 65.8 %, CMU 55.1 %. So roughly **two-thirds
of the 22.8 % contamination is a 3-second script; one-third needs upstream regeneration** — The
trade-off then stops being rhetorical: prune costs distribution coverage exactly where the bank
is thinnest (ground-contact = 3.2 % of training duration — pruning its flagged 39 % makes the N3
problem worse), repair keeps it at ~zero marginal cost, and the census quantifies the split per
category. N7's seal (post-N3) now includes a **prune arm** so the causal comparison is
repair-vs-prune-vs-keep in one run (draft updated, `plan/N7_DRAFT_repair.md`).

## 3. Sim-to-real: what tracking an infeasible reference does to a real robot (issue 3)

We make no hardware claims; we ground the prediction in measured sim quantities and label it.

Measured in sim (`reports/effort_sat_at_fall.json`, from the G1-gate artifact): tracking the
airborne descent, **0 of 29 actuators saturate during the entire supported phase; within 0.6 s of
the post-airborne contact, 17 % of actuators (5/29 — wrists, waist) pin at ≥ 98 % of force range
in 8/8 replicates**. Estimated (labeled estimate): the uncontrolled ~0.3 m fall the reference
forces implies ~2.4 m/s touchdown and ~95 J to dissipate through knees/wrists — joints not
designed as landing gear. Predicted real-robot phenomenology, per mechanism [exploratory,
sim-grounded]: (i) *impact loads on unprotected joints* — the failure is not gradual, it is a
free fall ending on wrists/knees; (ii) *thermal/current-limit events* — saturation bursts at
every attempted retry of the segment, invisible in average torque; (iii) *gain-amplified
oscillation* — the sign-reversal (stronger motors track the impossible plan more faithfully and
arrive at contact in a worse state) predicts that the common sim-to-real reflex of *raising*
gains makes exactly these segments worse; and (iv) *DR futility* — G1 showed no physics
randomisation changes the outcome, so domain randomisation spends robustness budget on an
unfixable segment. The deployment corollary: the screen is a **pre-flight safety filter**
(1 CPU-s/clip), and — if P-SIGN passes — the sign-reversal becomes its *runtime* complement: when
a gain increase worsens a segment, suspect the reference, don't retune the controller. Written
into the companion (§5b) and flagship (§6) as labeled prediction, with the P-SIGN/N7 falsifiers
attached.

## Where each item lands

| issue | immediate (done today, CPU) | sealed/scheduled | needs approval |
|---|---|---|---|
| 1 causal loop | efficiency ledger; prediction structure | N3 → N7 (extended) | E-HYG rider arm on E3 |
| 2 repair vs prune | operator + validation + census (running) | N7 prune arm (in draft, seals post-N3) | — |
| 3 sim-to-real | saturation measurement; labeled prediction sections | P-SIGN (runtime-guard half) | — |
