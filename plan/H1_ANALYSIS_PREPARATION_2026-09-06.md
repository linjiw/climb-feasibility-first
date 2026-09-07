# H1 statistical kernel and evaluation-order preparation

2026-09-06. **Unsealed prospective development addendum.** No original confirmation
decision rule, source or held-out output has been changed. New code is isolated in
`/home/linjiw/climb-icra-evidence-2026-09-06/tools/h1_analysis_protocol.py`.

## What is implemented

The pure H1 final-score kernel accepts gate-on/off clip-level arrays of shape
3 × 100, with rows explicitly labelled by proposed training seeds **61/62/63**
and exactly 25 distinct reference-defined feasible-hard indices. It computes
gate-on minus gate-off paired seed means on the hard and all-clip panels. The
independent unit remains the training seed, with a two-sided 95% Student-t
interval and **df=2**. Clip/episode counts do not inflate the independent sample.

The kernel follows the existing H1 draft:

- Improvement requires hard-panel mean at least **+0.02**, hard lower t bound
  strictly above zero, and all-panel lower t bound strictly above **−0.01**.
- Preservation requires both hard and all-panel lower bounds strictly above
  **−0.01**. A preservation-only result is noninferiority within these margins,
  not equivalence or improvement.
- A paired seed-and-shared-clip bootstrap is supplementary. The development
  proposal fixes 10,000 draws and RNG seed 20260906; these choices still require
  inclusion in the future H1 freeze. Bootstrap intervals cannot rescue a failed
  primary seed-level t decision.

Invalid provenance and failed training gates yield unavailable decisions before
the kernel inspects arrays. The CLI accepts **synthetic fixtures only**; it has
no measured endpoint input or experimental launch command.

The companion schedule helper describes six training jobs followed by 24
checkpoint evaluation cells at 1000/2000/3000/3999. Proposed training order is
on/off for seed 61, off/on for seed 62, and on/off for seed 63. This alternates
within-seed order but is not perfectly balanced with three seeds; it remains
prospective and must be bound in the eventual scheduler/freeze.

`load_after_training` requires exactly six training records and calls every
training verifier before invoking any outcome loader. It rejects smoke runs,
wrong arm/seed/device/budget, missing scheduled checkpoints and failed verifier
returns. Production callers must supply source-bound, contract-authenticated
verifiers/loaders. The current callback tests use **synthetic records** and do
not authenticate or authorize a scientific experiment.

## Validation and scope

Sixteen tests pass, covering:

- Improvement, preservation-only and uncertain decisions with correct seed labels.
- The analytic three-seed t interval and the all-panel regression guard.
- A deliberately positive bootstrap interval that cannot rescue seed uncertainty.
- Invalid score shapes/ranges/nonfinite values and duplicate hard-panel indices.
- Failed provenance/training gates without outcome-array access.
- All six verifier calls preceding all 24 outcome calls; a missing run, failure
  of the sixth verifier, smoke result or incomplete checkpoint list causing
  **zero outcome-loader calls**.

Exact synthetic/test commands and logs are in the isolated worktree's
`reports/h1_analysis_preparation_2026-09-06/`. The output `synthetic.json` is
explicitly classified synthetic and includes the proposed 30-job schedule.
It must never be reported as measured H1 performance. Compilation passes; both
original seals and all 376 original runtime hashes remain unchanged. Original
repository verification record:
`reports/h1_analysis_preparation_2026-09-06/verification.json`.

This completes the pure decision/order kernel, **not** the production H1 scheduler.
Remaining work includes authenticating the full paired evaluation manifest and
training-source contracts, binding the callback implementations, actual GPU
entrypoint smokes, a complete fresh-seed audit, original confirmation disposition,
and the independent prospective H1 freeze. Full H1 training remains disabled.

## Live confirmation progress

R seed 21 is training on GPU under the original frozen contract. At
**14:44:23 EDT**, checkpoint **2100** has matching content hash and **76 finite
checkpoint tensors**. Its saved sampler probabilities replay exactly, with
**596,494 completed trials**, including **197,689 failures**, zero invalid
starts/reference frames/censored resets, and point allocation TV
**0.0882566243200943**. This is interim manipulation/integrity telemetry,
not the final R21 training gate or tracking utility.

Checkpoint, ledger and sampler paths/hashes are recorded in
`reports/h1_analysis_preparation_2026-09-06/r21_snapshot.json` in the original
repository. U21 and A21 remain the two complete training arms; all 48 held-out
evaluation cells remain unopened. The confirmation, pilot, efficiency and
GPU-conformance supervisors remain alive. No additional GPU job was launched by
this H1 preparation.
