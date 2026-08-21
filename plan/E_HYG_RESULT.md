# E-HYG result — bank-scale feasibility pruning (run 2026-08-20)

**Verdict: sealed null — hygiene-at-scale is not confirmed.** Frozen analyzer
`tools/analyze_ehyg.py` (sha `5f8eb56e…`) produced `reports/E_HYG_result.json` against
`plan/PREREGISTRATION_E_HYG.md`.

| endpoint | comparator | pruned | Δ pruned − comparator | verdict |
|---|---:|---:|---:|---|
| feasible heldout (n=71; P1) | 0.918 | 0.907 | **−0.0101**, one-sided permutation p=0.951 | **fail** (needed ≥ +0.015) |
| all heldout (n=100) | 0.893 | 0.879 | −0.0132 | descriptive |
| infeasible heldout (n=29; P4) | 0.831 | 0.810 | −0.0209 | descriptive |
| zero-shot ground (n=60; P3) | 0.469 | 0.434 | −0.0354 | inside [−0.05,+0.02] |
| zero-shot dynamic (n=60) | 0.917 | 0.907 | −0.0101 | descriptive |

P2 also fails: the comparator's worst feasible decile moves −0.0153 versus −0.0035 for its best
half; the easy stratum moves −0.0051. The predicted concentration of positive gain is absent, so
the decision P1 ∧ P2 is false. Source artifacts are the six
`reports/E_HYG_uniform-amass800{,p}-s1_*_strat.csv` files and the analyzer JSON.

This is a one-seed, matched-compute test of **clip pruning at 12.4% flagged prevalence**, not a
test of the feasibility screen, contact-projection repair, segment masking, or FGAS. The pruned
bank is less dirty, not clean: 140 retained clips still admit 5.43 minutes of infeasible bins
(`plan/FGAS_DIRECTIVE_2026-08-19.md`). The result says the lost coverage is not repaid by faster
learning at this contamination level and budget; the in-bracket ground loss is consistent with
the pre-registered coverage-cost boundary.

## What must not be claimed

- Do not claim pruning improves training performance or that a null hides a positive direction.
- Do not generalize this result to repair or eligibility-masked sampling.
- Do not call `tier_800_pruned` clean, and do not infer a population effect from one seed.

Disposition: keep the sealed null. Use N7 to distinguish repair from discard, and use FGAS to test
whether retaining feasible segments avoids the coverage loss observed here.
