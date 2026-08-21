# N7 result — repair-all versus keep/prune

**Read out:** 2026-08-20, after `reports/N7/COMPLETED` existed. The frozen
registration, analyzer, and manifest remain unchanged (`plan/N7_DRAFT_repair.md`,
`plan/N7_FREEZE.sha256`).

## Runtime integrity

The repair arm reached iteration 3999/4000 and wrote its final checkpoint and
exposure ledger. All four flagged99 policy/reference cells, heldout100, and
zero-shot-ground evaluations have their expected row counts. The campaign log
contains no traceback, CUDA error, OOM, NaN report, or killed process. GPU use
stopped because the analyzer completed and wrote the sentinel.

## Frozen readout

| rule | result | verdict |
|---|---:|---|
| flagged99 deployment, R/repaired − K/raw | **+0.0397**, motion-bootstrap 95% CI [+0.0153,+0.0658] | positive, but misses the sealed +0.05 SESOI |
| training transfer, R/raw − K/raw | **−0.0036**, CI [−0.0179,+0.0103] | no policy-only gain |
| reference-only, K/repaired − K/raw | **+0.0233**, CI [+0.0022,+0.0456] | repaired target is easier |
| heldout100, R − K | **−0.0104**, CI [−0.0293,+0.0023] | point no-regression gate passes |
| ZS-ground, R − K / R − P | **−0.0199 / +0.0155** | coverage rule fails (`R−P` needed +0.03) |

Overall N7 therefore **fails its sealed joint decision**. Its primary contrast is
encouraging but decomposes exactly as `−0.0036 + 0.0233 + 0.0200 = +0.0397`:
no raw-reference policy transfer, a reference-only benefit, and a positive
policy-by-reference interaction.

## Post-outcome audit and scope

`tools/diagnose_n7_result.py` records two qualifications without changing the
sealed result. First, `heldout100` overlaps the tier800 training list by eight
motions. On the 92 disjoint motions the delta is −0.0122, CI
[−0.0316,+0.0012]; on the 68 both feasible and disjoint it is −0.0137, CI
[−0.0391,+0.0024]. The frozen point gate still passes, but “heldout100” must not
be described as fully unseen.

Second, benefit is concentrated in the 11 repairs declared over the 0.15 m
distortion budget: their mean deployment delta is +0.2305, versus +0.0160 for
the 78 certified repairs and +0.0143 for the 10 residual repairs. Those large
edits account for most of the aggregate improvement and require reference-
fidelity and motion-quality metrics before they can be called better motion.

The evaluation audit also found unpaired startup randomization, clipped duplicate
offsets, and incomplete late-motion coverage. Existing survival values remain
sealed measurements under their harness; future causal claims require the paired
v2 evaluator in `plan/SEGMENT_NATIVE_FOLLOWUP_2026-08-20.md`.

## Scientific reading

Repair-all did not meet the pre-registered benefit or coverage gates. It provides
evidence that projection can make affected deployed references easier and that a
policy can co-adapt to them, but not that repair improves the underlying policy
on unchanged motions. The strongest follow-up is a distortion-aware hybrid:
repair physically faithful cases, retain exact feasible segments elsewhere, and
evaluate survival together with reference fidelity and motion quality.
