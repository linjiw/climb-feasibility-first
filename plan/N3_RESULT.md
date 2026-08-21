# N3 result — coverage causality (run 2026-08-20, seal `af1b7c9f…`)

**Sealed readout: the E1/E4 arithmetic decision passes, but the preflight stop rule prevents an
unqualified causal claim because E2 fails in the adaptive arm.** Frozen analyzer
`tools/analyze_n3.py` (sha `b118b2d3…`) produced `reports/N3_result.json`.

| endpoint | sealed criterion | result | verdict |
|---|---|---|---|
| E1, #44 feasible kneel/crawl phase | survival ≥ 0.25 in both augmented-uniform seeds | **0.750 / 0.750**; base s1/s2/s3 = 0.000 / 0.031 / 0.188 | **pass** |
| E4, random16 specificity | survival < 0.10 | **0.000** | **pass** |
| E2, no regression | easy clips ≥ 0.95 and heldout Δ within ±0.03 in every arm | augmented uniform heldout Δ −0.0096 / +0.0004 and random16 +0.0117 pass; adaptive heldout **−0.0346** and BMLhandball easy **0.857** fail | **fail** |
| E3, adaptive release | maximum top-1 mass after iteration 2000 < 0.50 | **0.784** | **fail** |
| descent prediction | augmented-uniform survival ≤ 0.25 | **1.000 / 0.688** | **miss** |

The frozen analyzer therefore records `coverage_causal: true` because its sealed arithmetic rule is
E1 ∧ E4. The later frozen preflight (`plan/N3_PREFLIGHT.md`) additionally says to stop interpretation
if E2 fails anywhere. Both facts are retained: targeted composition strongly changes the two
keystone policies and the random-volume control does not, but this run does **not** support the
unqualified statement that coverage alone is causal without regression.

E5 moves in the predicted direction for all three evaluated ground16 probes: base→augmented
survival is 0.000→0.750, 0.531→1.000, and 0.375→1.000 (`reports/N3_result.json`). This is a
training-set effect. The adaptive top-1 mass ends at 0.329, but the sealed maximum-after-2000 rule
fails; no per-clip exposure ledger exists for the required terminal failure-EMA clause.

## What must not be claimed

- Do not describe N3 as an unqualified causal confirmation; cite the E2 stop.
- Do not claim infeasible descent cannot be tracked: both augmented seeds violate that prediction.
- Do not claim the adaptive attractor released or treat missing exposure telemetry as zero.

Disposition: carry the mixed result into the N7 seal. N7 may test repair versus prune versus keep,
but its predictions must not assume the descent/feasible-phase separation observed by N1 is also a
learning boundary.
