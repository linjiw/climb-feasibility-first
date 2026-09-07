# Confirmation evaluator audit and sealed-provenance adapter

Date: 2026-09-05. Classification: **measured implementation audit; policy utility pending**.
This is an unsealed correction addendum to
`RELATIVE_CONFIRMATION_EXECUTION_2026-09-05.md`. No sealed file or manifest changes.

## Finding and consequence

The actual scheduled evaluator CLI rejected the frozen Phase-G condition file
before simulator construction. `eval_paired_v2.load_or_create_manifest` compares
its entire reconstructed dictionary with the saved file. The sealed saved file
additionally contains `panel_txt_sha256` and `classification`; the sealed builder
emits neither field. All shared fields, including all 2,800 conditions, match.
The previous CPU reference audit was correct about the condition payload but
insufficient to establish compatibility with the actual evaluator entrypoint.
The prior scheduling and synthetic metadata tests did not expose this interface
mismatch. Four new evaluator-interface tests reproduced it, one per arm.

This is an execution defect, not a changed scientific population or a policy
result. The original evaluator and conditions are both sealed. Removing fields
from the original file or editing the original evaluator would violate the
research ledger. The preserved evaluator SHA-256 is
`284886608d81ff957e69b32a5a9d1448917ee0a9867a7c23253831b53233e367`;
the condition SHA-256 is
`74b723d42c4050eea9f4ea7ff87d22771e8e32c5155b56829900bf4cb3744a4e`.

## Minimal implementation

`tools/eval_relative_confirmation.py` reuses the sealed evaluator CLI, condition
builder and rollout implementation. During its call only, it substitutes a
condition loader that requires the exact sealed file path and SHA-256, rebuilds
all condition fields, validates the panel hash and exact classification, and
compares the complete dictionary. Changed seeds, horizons, repetitions, noise,
nominal settings or contact allocation cannot pass. It returns the original
full dictionary and never rewrites the condition artifact. The original loader
is restored even on failure.

After a completed rollout, the adapter adds its own path, hash and protocol to
the newly generated evaluation metadata. The underlying evaluator identity
remains the sealed identity. The strict contract verifier binds the adapter;
the evaluation-cell verifier requires its exact metadata identity. Missing or
changed adapter metadata blocks aggregation. The scheduler now invokes this
adapter for all 48 cells. This is a compatibility change only: no score,
termination, reference, reset, randomization, denominator or policy changes.

## New validation coverage

The complete synthetic campaign now exercises the **new** contract schema through
its real production verifiers, including recursive draft/entrypoint-smoke checks,
both R prerequisites, all four development smokes, both D calibrations, all
12 confirmation histories with 41 snapshots each, all 48 evaluation cells and
final aggregation. Real bank identities, configuration factories, runtime/source
checks and sampler replay are used. Histories, checkpoints, costs, startup hashes
and evaluation rows are constructed synthetic data. A synthetic positive outcome
only checks analyzer behavior; it is not evidence for the method.

Corruption tests reject changed entrypoint decisions, rehashed smoke results,
runtime identity, reference cross-links, training configuration, evaluation
pairing and adapter identity before outcome aggregation. The positive test does
not replace scientific or provenance verifiers. Corruption tests replace only
aggregation with a sentinel to prove it was not reached.

The actual scheduled CLI is additionally tested through its real parser,
condition validation and configuration construction. Only the simulator
constructor is replaced by a stop sentinel. Across U/A/R/D, actor/critic
observation definitions (with the existing evaluation noise switch), actions,
robot entities, body ordering, anchor, control interval and actor configuration
match training. The fixed environment seed, 2,800 worlds, disabled auto-reset and
contact allocation are checked. This closes a CPU interface gap; it does not
validate GPU allocation, checkpoint deserialization, runtime randomization
pairing or actual rollout behavior.

Artifacts: `reports/relative_progress_2026-09-05/evaluator_adapter_correction/`.
`cpu_preflight_result.json` records the original rejection, exact two-field
mismatch, unchanged sealed identities and successful new-draft preflight.
`verification.json` records exact test/compile/seal/whitespace commands, outputs
and source hashes. `source_before/` preserves the changed unsealed production
files from the earlier preparation.

## Queue supersession and current execution path

The prior seed-51 supervisor PID 1490062 was stopped at 21:18:03 EDT while it
was waiting for D calibration. Its directory contained only its design; no
smoke had launched and no policy endpoint had opened. Its design, launch log,
old draft and runtime inventory remain preserved. Its new terminal record says
`superseded_before_any_smoke_launch`; `queue_supersession.json` records why.
This is not a failed or discarded scientific seed.

The original seed-41 development-smoke worker and D seed-31/32 calibration
worker remain unchanged. A fresh preparation under `confirmation_preparation_adapter/`
binds 376 runtime files including the new adapter and the same 36 G1 assets.
All 12 configuration hashes and the reference audit reproduce. It remains a
draft with confirmation disabled. The old `confirmation_preparation/` is a
historical artifact and no longer matches the current unsealed runtime.

The replacement supervisor uses `confirmation_entrypoint_smokes_adapter/` and
waits for the same fixed D calibration. Its exact command, PID and timestamp
are recorded in `confirmation_entrypoint_smokes_adapter_launch.json`. It runs
only U/A/R/D seed-51 lifecycle smokes, eight environments and 20 iterations,
under the same shared-GPU gate. It never launches confirmation automatically.

## Research decision and remaining gates

Continue the unchanged relative-progress candidate and the fixed U/A/R/D
comparison. The strongest current scientific evidence remains two-seed
exploratory allocation replication. The four-arm experiment is needed to test
held-out policy value and distinguish progress allocation from conditional
failure allocation. The adapter introduces no tuning or additional method arm.

Next: finish development smokes and both fixed D calibration runs, complete the
new trainer's simulator smokes, and finish any checkpoint-loading lifecycle check
on development inputs. Then create a prospective frozen confirmation contract
with the completed prerequisites before using seeds 21–23. The actual fixed-panel
evaluator runs only after all 12 training gates pass; paired startup identities
must match before outcome aggregation. An evaluator failure remains an execution
stop or invalid result, not permission to alter conditions. Full benchmark runtime
integration and policy utility remain pending despite the expanded CPU and
synthetic checks. Preserve negative, inconclusive, invalid and not-tested
dispositions as declared.


Integrated verification: **175 tests passed in 292.93 s**. Python compilation,
whitespace checks and all 41 sealed Phase-G identity checks pass.
The replacement seed-51 supervisor is queued after fixed D calibration;
its launch identity is recorded in `confirmation_entrypoint_smokes_adapter_launch.json`.
