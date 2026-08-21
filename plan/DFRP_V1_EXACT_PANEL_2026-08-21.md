# DFRP v1 — exact repair panel gate

**Date:** 2026-08-21
**Status:** unsealed CPU-only research plan. This does not authorize GPU
training, change sealed inputs, or establish policy benefit.

## Scope

Test the released `dfrp_root_contact_ik_v1` operator on a deterministic panel
drawn from the 644 legacy primary candidates, then admit only hash-matched,
exactly rescreened clips to segment-native training artifacts.

The panel is fixed before execution:

- all two rare candidates with legacy displacement `<= 0.02 m`;
- four candidates from each cell of
  `{0.02–0.04, 0.04–0.06, 0.06–0.08} m` ×
  `{0.10–0.20, >0.20}` initial infeasibility;
- four byte-identity controls from the most represented source families in the
  selected flagged panel.

Within each cell, selection is deterministic from the census payload and
prefers source diversity before a seeded SHA-256 ordering. The resulting panel
has 26 flagged clips and four controls. No policy outcome enters selection.

## Primary metric and gate

The primary metric is the exact-ready flagged rate:

`flagged clips with complete repair qualification, residual <= 0.05, an
offset <= 0.08 m, and at least one legal 50-step start / 26`.

The gate passes only if all conditions hold:

1. exact-ready flagged rate is at least 75% (at least 20/26);
2. all four controls are byte-identical no-ops and training-ready;
3. there are zero manifest-integrity, joint-limit, or 10 mm IK-residual
   violations among admitted clips;
4. selection and manifest payload hashes reproduce on a second build.

Secondary diagnostics are residual infeasibility, legal-start yield, repair
runtime, root displacement, joint delta, body MPJPE, root-velocity delta, and
root-acceleration delta. These characterize the gate but cannot rescue a
primary failure.

## Autoresearch loop

Run at most six iterations including the frozen v1 baseline. If the baseline
fails, diagnose failures and change one bounded operator mechanism or parameter
at a time. Keep a change only when it increases exact-ready flagged count
without violating a guard; ties prefer lower p95 body MPJPE, then lower p95
root acceleration. Do not change panel membership, the 6 cm screen gap, the
10%/5% thresholds, the 8 cm budget, the 10 mm IK bound, or the 50-step horizon.

Every iteration records code hash, command, elapsed time, panel result, and
keep/discard decision in `autoresearch/autoresearch-260821-0115/`.

## Verification

- rebuild the DFRP manifest twice and compare payload hashes;
- require `tools/dfrp_pipeline.py --require-training-ready --check-only` only
  for the materialized eligible subset, not for failed panel members;
- build the exact segment unit table and instantiate the real sampler;
- run focused CPU tests, Python compilation, Ruff, and `git diff --check`;
- leave FGAS and N7 sealed manifests unchanged and hash-valid.
