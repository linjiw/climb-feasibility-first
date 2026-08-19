# E10 — pre-registration: does freshness or liveness drive the collapse?

**Written:** 2026-08-16, **before** any grounded performance result has been read.

```
grounded eval CSVs on disk : 27  (3 seeds x 9 checkpoints, complete)
grounded results analysed  : NO  — analyze_campaign.py has not been run on them
branch decision            : not taken
```

The grounded arm finished training while the A-queue was in progress. Its CSVs
exist but have not been opened. Everything below is fixed without knowledge of
whether grounded beat, matched, or lost to uniform, so the E10 predictions
cannot have been reverse-engineered from the branch.

---

## 1. Why this cell exists

A1 found the frontier is *temporal*: 69% of clips cross the band but each spends
~16% of the run inside it, so the band holds ~16% of the bank at any instant.
That suggested estimator responsiveness, not the utility function, is the binding
constraint.

The advisor's refinement, adopted here: **"responsiveness" is two things.**

- **Signal freshness** — how fast an estimate moves per update. Set by `α`.
- **Estimator liveness** — whether a clip keeps *getting* updates at all. Set by
  how much sampling mass it receives.

These are not interchangeable. `α` acts per update, but a clip's estimate only
receives updates in proportion to its sampling mass. In the collapsed arm the 99
cold clips shared ~12% of the mass, so their estimates refreshed roughly an order
of magnitude slower than under uniform. **No global `α` fixes an allocation
problem**: raising it mostly adds variance to the hot clip while the cold ones
stay near-frozen.

Read that way, A1 does not compete with the grounding story, it deepens it: the
ε floor does double duty — coverage for the learner, and refresh for the
estimator. If that survives E10, it is the spine of the mechanism section.

## 2. What A7 already established, and how it changes the design

A7 (run before this document):

- The dominant clip is **#44 in all six runs** — 3 adaptive seeds *and* 3
  grounded seeds. Seed-invariant identity rules out a purely stochastic
  staleness artefact.
- Clip #44's measured survival under the **uniform control** policy is
  **0.3125** (bank mean 0.892), dying after 1.14 s with tracking error 0.140,
  ~3× the bank median. So it is neither unlearnable nor mastered — it is the
  *persistently hardest* clip, sitting inside the frontier band.
- The atlas does **not** flag it: required_mu 0.18 and peak GRF 1.42 are both
  low. Another mark against L3, consistent with A3.

This triggers the advisor's stated conditional ("if one clip attracts the mass in
all seeds, the fix class is a per-clip mass cap and E10 gains a cap arm"), so a
cap arm is added below.

It also sharpens the freshness prediction. If the dominated clip genuinely keeps
failing, a *fresher* estimate reports the same thing — so freshness alone should
not rescue the unfloored arm. That is now a directional prediction rather than an
open question.

## 3. Design

Core 2×2 over {floor} × {α}. Two cells already exist from Exp-1 and are **not**
re-run:

| cell | floor | α | status |
|---|---|---|---|
| adaptive @ slow | none (additive) | 0.01 | exists (Exp-1) |
| grounded @ slow | ε-mixture | 0.01 | exists (E2) |
| **adaptive @ fast** | none (additive) | 0.10 | **new** |
| **grounded @ fast** | ε-mixture | 0.10 | **new** |

Plus, triggered by A7:

| cell | rule | α | status |
|---|---|---|---|
| **capped @ slow** | ε-mixture + per-clip cap `p_i ≤ c/N` | 0.01 | **new** |

Cap set to `c = 5`, i.e. no clip may exceed 5× uniform mass (0.05 at N=100).
Fixed now. Chosen so grounded's observed peak (0.186 ≈ 18.6× uniform) is bound
but the arm can still prioritise meaningfully; not tuned.

Everything else is held at the Exp-1 configuration: `tier_mixed100`,
`heldout100`, 4000 iterations, 4096 envs, ε = 0.1, same seed IDs, same evaluation
protocol and endpoints as pre-registered in A2.

**Seed allocation is the only branch-dependent element**, per the advisor:
Branch A → 2 seeds on adaptive@fast (reviewer counterfactual demo);
Branch B/C → 3 seeds on grounded@fast (headline cell). The capped arm takes 3
seeds in all branches, since A7 motivates it independently of the branch.

## 4. Predictions, on record

**P1 (liveness account).** Unfloored fast-α still collapses: adaptive@fast
reaches top-1 mass > 0.5 and minimum entropy < 0.4. Raising α cannot repair an
allocation failure.
*Falsified if* adaptive@fast holds top-1 < 0.3 throughout.

**P2 (freshness is not the binding constraint, given A7).** adaptive@fast does
not close the held-out AULC gap to uniform: it remains below uniform by more
than half the Exp-1 deficit (i.e. AULC gap > 0.029).
*Falsified if* adaptive@fast reaches parity with uniform.

**P3 (signal-limited account, the alternative).** grounded@fast pulls ahead of
uniform on AULC even where grounded@slow did not. This is the Branch-B rescue and
the Branch-C prime suspect; in Branch A it is the confound-killer.
*Falsified if* grounded@fast ≈ grounded@slow.

**P4 (cap, from A7).** The capped arm reduces collapse more than α does —
top-1 mass bounded near 0.05 by construction, and AULC ≥ grounded@slow. If the
attractor is what costs performance, capping is the direct remedy.
*Falsified if* capped ≤ grounded@slow on AULC despite bounded top-1, which would
say the mass concentration was not the mechanism after all.

**P5 (forgetting).** Downward band crossings order with coverage:
capped ≤ grounded ≤ adaptive at matched α. Exp-1 gave uniform 5.6, grounded 7.7,
adaptive 10.3 per 1k iterations.

## 5. What each outcome buys

| P1 | P2 | P4 | Reading |
|---|---|---|---|
| hold | hold | hold | Liveness + attractor. The floor's dual role is the mechanism; cap is the sharpened instrument. Strongest version of the mechanism section. |
| hold | hold | fail | Concentration is not the cost; something else about failure weighting harms. Branch C territory regardless of E2. |
| fail | — | — | Freshness mattered after all; A1's temporal reading is the primary mechanism and the ε story is secondary. |
| — | fail | — | A faster EMA alone fixes it — the simplest possible account, and the paper's contribution narrows to the diagnosis. |

## 6. Endpoints

Unchanged from A2: primary is normalised AULC of held-out survival over
iterations 0–4000; co-primary is iterations-to-target at 0.810. Sampler telemetry
(entropy, top-1 mass, and — from the ledger, once merged — per-clip visitation)
is a *mechanism* measurement and never substitutes for the outcome.
