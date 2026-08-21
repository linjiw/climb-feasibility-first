# From diagnosis to performance: how the findings buy tracking quality and training efficiency

*Written 2026-08-20 in response to Linji's three issues (causal closure; repair-vs-prune;
sim-to-real impact). Status labels throughout; new numbers below are **measured today from
artifacts on disk** (no sealed experiment touched). Anything requiring a new training run is a
proposal, not a seal.*

## 0. The efficiency ledger — what feasibility hygiene is worth before any retraining

Measured (`reports/wasted_exposure_accounting.json`):

| sampler / scope | exposure currently spent on infeasible content |
|---|---|
| failure-adaptive (as shipped upstream) | **48.8 % of all clip draws over training** land on a single clip (mean top-1 mass across 3 seeds; peak 87–89 %), **≥ 21.9 % of them on the impossible one** — and every draw that starts in or before its ground segment produces an episode with a guaranteed unlearnable failure |
| clip-uniform on tier_mixed100 | 25 % of clip draws hit flagged clips; ≈ 6.1 % of drawn frames are infeasible frames |
| AMASS→G1 bank-wide (10,705 clips) | 22.8 % of clips / 27.4 % of duration flagged; mean infeasible-frame share 9.8 % |

So the *cheapest* payoffs, in order: (1) the grounded sampler already caps the catastrophic case
(sealed ✓ — this is the 0.780 → 0.825 endpoint story); (2) pruning or repairing flagged clips
reclaims ~6–10 % of gradient exposure under uniform sampling and removes the attractor class that
failure-weighting amplifies to ~50 %; (3) the screen costs 1 CPU-s/clip — 3 hours for the whole
bank, against 21,000 GPU-hours for a SONIC-scale training run. **Feasibility hygiene is four to
five orders of magnitude cheaper than the training it protects.**

## 1. Closing the causal loop (issue 1) — what is sealed, what is added

The loop "diagnosis → fix → measured performance gain" has now produced three readouts:

- **N3 (sealed `af1b7c9f`) — mixed:** ground16 raises the feasible phase to 0.750 in both seeds
  and random16 stays 0.000, but the adaptive arm regresses and triggers the frozen E2 stop; E3
  and the descent prediction miss (`plan/N3_RESULT.md`).
- **N7 (sealed `90da8a08`) — joint fail:** the repaired-policy/repaired-reference deployment
  contrast is +0.0397, below the +0.05 SESOI. Raw-reference policy transfer is −0.0036, while
  reference-only benefit is +0.0233. Most aggregate gain is concentrated in 11 over-budget
  repairs, so the result motivates distortion-aware repair plus exact segment curation, not
  repair-all (`plan/N7_RESULT.md`).
- **E-HYG (sealed `a5494b7c…`) — null:** `uniform-800-pruned` versus `uniform-800` gives feasible
  heldout Δ −0.0101 (p=0.951), all-heldout Δ −0.0132, and no worst-decile concentration.
  Zero-shot ground Δ −0.0354 stays inside the coverage-cost bracket (`plan/E_HYG_RESULT.md`).

The predicted pruning signature did not appear. The next performance test must retain feasible
coverage while suppressing infeasible exposure: repair and bin-level eligibility, not another
clip-deletion arm.

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

**Census complete** (historical 2,443-row directory, sentinel `reports/repair_census/COMPLETED`;
strict flagged set 2,442 after C4; 2×2 historical table `reports/repair_census/summary.md`):
**65.8 % auto-recoverable** under the ≤ 15 cm /
≤ 5 %-residual budget — 73.1 % of the 10–25 % band, 61.7 % of the > 25 % band; by category:
quiet 80.9 %, ground 68.1 %, locomotion 64.8 %, dynamic 51.2 % (ballistics correctly refused);
by source: BMLhandball 92.5 %, BMLmovi 89.2 %, CNRS 65.8 %, CMU 55.1 %. So roughly **two-thirds
of the 22.8 % contamination is a 3-second script; one-third needs upstream regeneration.** The
trade-off thus stops being rhetorical: prune costs distribution coverage exactly where the bank
is thinnest (ground-contact = 3.2 % of training duration — pruning its flagged 39 % makes the N3
problem worse), repair keeps it at ~zero marginal cost, and the census quantifies the split per
category. N7's matched policy/reference cross is complete; it did not validate repair-all, and
its post-outcome audit makes motion fidelity a required endpoint for the next comparison
(`plan/N7_RESULT.md`).

## 3. Sim-to-real: what tracking an infeasible reference does to a real robot (issue 3)

We make no hardware claims; we ground the prediction in measured sim quantities and label it.

Measured in sim (`reports/effort_sat_at_fall.json`, from the G1-gate artifact): tracking the
airborne descent, **0 of 29 actuators saturate during the entire supported phase; within 0.6 s of
losing foot support, ≥ 4/29 actuators pin at ≥ 98 % of force range in 8/8
replicates — exactly 5/29 (17 %) in 7/8, mean 16.8 %**. Estimated (labeled estimate): the uncontrolled ~0.3 m fall the reference
forces implies ~2.4 m/s touchdown and ~95 J to dissipate through knees/wrists — joints not
designed as landing gear. Predicted real-robot phenomenology, per mechanism [exploratory,
sim-grounded]: (i) *impact loads on unprotected joints* — the failure is not gradual, it is a
free fall ending on wrists/knees; (ii) *thermal/current-limit events* — saturation bursts at
every attempted retry of the segment, invisible in average torque; (iii) *gain-amplified
oscillation* — observed on #44 in two exploratory replicates, but **not general or specific under
P-SIGN's sealed test** (7/12 family, 4/12 controls, 2/7 localised); and (iv) *DR futility* — G1 showed no physics
randomisation changes the outcome, so domain randomisation spends robustness budget on an
unfixable segment. The deployment corollary: the screen is a **pre-flight safety filter**
(1 CPU-s/clip). P-SIGN rejects the proposed runtime complement, so gain response must not be used
as an online detector (`plan/P_SIGN_RESULT.md`).

## Where each item lands

| issue | immediate (done today, CPU) | sealed/scheduled | needs approval |
|---|---|---|---|
| 1 causal loop | N3 mixed; E-HYG null; FGAS soft fail; N7 joint fail | segment-native lifecycle and paired evaluation next | — |
| 2 repair vs prune | operator + validation + **census: 65.8 % auto-recoverable** | N7 complete; distortion-aware hybrid next | — |
| 3 sim-to-real | saturation measurement; P-SIGN sealed fail | no runtime-guard claim | — |
