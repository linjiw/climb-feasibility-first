# Final confirmation freeze command

Date: 2026-09-05. Classification: **implemented prospective finalization; actual freeze pending**.
This extends `RELATIVE_D_SEED31_RESULT_2026-09-05.md`. The fixed R/U/A/D design,
assigned seeds, statistical rules and queued simulation runtime are unchanged.

## Purpose and implementation

`tools/freeze_relative_confirmation.sh` closes the finalization step between
completed development evidence and the confirmation scheduler. It uses the
pinned Python environment and existing production verifiers. It never trains
a policy or opens an evaluation endpoint.

The command verifies the exact draft identity, current runtime and reference
audit, resolves its predeclared pending artifact paths, and refuses if any
required result is missing. An available non-pass decision is rejected even
when other results are still pending. Once all files exist, it reproduces both
R studies, all four seed-41 smokes, both fixed D calibrations, and all four
seed-51 new-trainer smokes. The latter must bind this exact draft. It rebuilds
and checks all twelve arm/seed configuration digests before creating output.

`--check-only` reports readiness without creating any output directory. With
complete passing prerequisites, finalization creates a new exclusive directory
containing:

- `profiles.json`: a new copy changing only confirmation enablement to true.
- `contract.json`: completed evidence bindings, original draft identity and
  timestamp, unchanged configuration hashes, and explicit freezer identity.
- `schedule.json`: the fixed 12 training and 48 evaluation jobs.
- `launch_command.json`: exact scheduler argv; not executed by the freezer.
- `freeze_result.json`: full verification receipt, with zero jobs launched.
- `confirmation.sha256`: a new seal for these records, the runtime inventory
  and freezer source; the existing Phase-G seal is untouched.

The strict full contract verifier runs again before finalization succeeds.
Existing output directories cannot be overwritten. A failure after creating
an output directory retains a `freeze_failure.json` record; it does not silently
retry or claim a successful freeze.

This is an administrative shell entrypoint, not new simulator Python code.
Its identity is explicitly added to the frozen contract's checked source group
and new seal. Therefore the existing queued smoke runtime remains valid, while
any later edit to the freezer invalidates its finalized source binding.

## Exact pending-stage command

```bash
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 tools/freeze_relative_confirmation.sh --draft reports/relative_progress_2026-09-05/confirmation_preparation_adapter/draft_contract.json --draft-sha256 74857935900acac9c14b2a865845c658da89a8e06bbfeac72ac96d6bc91552f2 --out-dir reports/relative_progress_2026-09-05/confirmation_freeze --check-only
```

The actual current draft returns `prerequisites_pending` (exit 2), identifies
D seed 32 and all four seed-51 results, and writes zero files. D seed 31 already
passed; D seed 32 is still running. No actual confirmation freeze or enabled
profile copy has been produced.

After the remaining actual results pass, run the same command without
`--check-only`. Inspect its complete verification receipt and new seal, then
execute the structured argv in `launch_command.json` through the existing
scheduler. All 12 training manipulation gates must pass before any of the
48 fixed-panel evaluation jobs. The existing single-attempt, pairing,
provenance and outcome rules remain in force.

## Validation scope

`tests/test_relative_freeze_transition.py` exercises the real command via
subprocess. It covers pending prerequisites with no output, an available failed
prerequisite, complete check-only readiness, complete finalization, full contract
re-verification, new seal verification and refusal to overwrite. The positive
case uses the complete explicitly **synthetic** prerequisite fixture and retains
that label in the generated contract. No production verifier is replaced and
no scientific job is launched.

The fixture helper now predeclares its own synthetic entrypoint-decision paths,
so the promotion test resolves its own completed records rather than actual
queued smoke paths. The complete strict-contract integration test is rerun to
check that this fixture change preserves preflight-to-aggregation behavior.
These tests supply implementation evidence only; actual seed-51 simulator
validation and benchmark policy utility remain pending.

Exact commands, outputs, source hashes, actual readiness result and operational
snapshot are recorded under
`reports/relative_progress_2026-09-05/freeze_command_validation/`.

## Research direction

Continue the fixed relative-progress candidate through the conditional-failure
baseline comparison. D's first complete calibration shows a sustained nonuniform
intervention, but both D seeds are required and its temporal allocation differs
from R. Finalization does not promote similar allocation TV into a policy claim.
A valid held-out R−U result and its prescribed all-panel guard remain the primary
policy test; R−D is descriptive evidence about the mechanism under the stated
startup/cap/floor differences. Preserve inconclusive and negative results.
