# A2 — Pre-registration of the Experiment-2 outcome specification

**Written:** 2026-08-16
**Registers:** Research Plan v2 §5, for the grounded-vs-uniform comparison (E2).
**Status at time of writing — the reason this document is admissible:**

```
grounded eval CSVs in reports/campaign/ : 0
grounded training progress             : seed 1, iteration ~1091 / 4000
uniform + adaptive cells               : complete (54 evals, analysed, reported)
```

No grounded checkpoint has been evaluated. Nothing below is chosen with knowledge
of a grounded result. The uniform and adaptive arms are already analysed and
their numbers are fixed and public in the Exp-1 report; the target level below is
derived **only** from the uniform control arm, which was measured before the
grounded arm existed as code.

Verify independently:
`ls /data/robotixx/climb/reports/campaign/grounded-*.csv` returned nothing at
write time, and the file timestamps of every `uniform-*` / `adaptive-*` CSV
precede this document.

---

## 1. Primary endpoint

**Normalised AULC of held-out survival rate over iterations 0–4000.**

Trapezoid integral of the mean held-out survival curve, divided by the iteration
span, so the value reads on the same scale as a survival rate. Held-out set is
`bank/tiers/heldout100.txt` (100 clips, zero overlap with the training bank,
difficulty-matched at composite 0.684 vs 0.697).

Computed by `tools/analyze_campaign.py` with no arm-specific options.

## 2. Co-primary endpoint

**Iterations-to-target, target = 0.810 held-out survival.**

0.810 is the uniform arm's Exp-1 endpoint mean (0.8096, rounded), fixed here
before any grounded analysis and derived from the control arm alone. This is the
quantity reported as the "×" compute-reduction figure:

```
compute reduction = iters_to_target(uniform) / iters_to_target(grounded)
```

Right-censored if unreached within 4000 iterations. An arm that never reaches
target is reported as censored, **not** dropped and not extrapolated. If both
arms are censored the co-primary is reported as uninformative and the primary
stands alone.

Target crossing is taken at the first checkpoint whose mean meets or exceeds
0.810, with no interpolation between checkpoints (the ladder is 500-iteration
spaced; finer resolution is not claimed).

## 3. Secondary endpoints

Reported, but cannot be promoted to primary after the fact.

- **RMST-style mean steps survived**, right-censored at the 10 s horizon.
- **Tracking error on survived episodes** — reported *with* an explicit
  survivorship caveat, because episodes that fail early contribute no late-phase
  error and the statistic is therefore conditioned on success.
- A **blended outcome** may be explored and reported as exploratory. It may not
  replace the primary.

## 4. Design and analysis

- **Pairing.** Arms share seed IDs (network init + env seeds), so analysis is
  paired by seed.
- **Seeds.** n = 3 for screening cells. n = 5 for the headline pair before any
  headline claim.
- **Tests.** Paired permutation / bootstrap on AULC with hierarchical bootstrap
  CIs. The exact sign test is retained as the assumption-free companion, always
  reported together with its n-floor (0.125 at n=3, 0.031 at n=5), because at the
  measured seed reproducibility (±0.005 endpoint s.d.) the floor, not the data,
  is the binding constraint on the sign test's p.
- **Per-seed curves** go in the appendix. No seed is dropped for any reason other
  than a documented run failure, and any such drop is reported.

## 5. Interpretation, pre-committed

The three-outcome table in the Exp-1 report §05 governs and **is not amended
here**, restated for completeness:

| If grounded… | Then |
|---|---|
| beats uniform | grounding converts a harmful curriculum into a helpful one; mechanism, not prioritisation, is what matters |
| matches uniform | grounding repairs the damage but prioritisation adds nothing at this scale; the diversity axis (E3) becomes decisive |
| still loses | collapse was not the cause; clip-level failure weighting is itself harmful and the frontier premise needs revision |

"Beats" and "matches" are adjudicated on the **primary** endpoint with its CI,
not on whichever secondary happens to separate.

## 6. Evaluation resolution — a known limitation, registered now

8 episodes/clip quantises per-clip survival to steps of 0.125. That is adequate
for arm means (averaged over 100 clips) but coarse for frontier-band membership,
which is a per-clip property. Accordingly:

- Band occupancy (A1) is co-estimated from training-time EMAs, not from the
  8-episode evals alone.
- Headline cells add **16-episode** evaluations at iterations ~1500 / 2500 / 4000.

## 7. What would falsify the programme's central bet

Recorded so it cannot be quietly reframed later: if grounded ≈ uniform at 100
clips **and** Δ(grounded − uniform) does not grow at 800 clips (E3), then H2b —
the plan's central bet that curriculum benefit scales with bank diversity — is
not supported, and the work becomes Frame 2 (*why adaptive curricula fail*). That
outcome is publishable on the diagnosis, the gates, and the atlas, and this
document exists partly so that pivot reads as a planned branch rather than a
salvage.
