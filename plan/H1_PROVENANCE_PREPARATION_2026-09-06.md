# H1 evaluation provenance preparation — 2026-09-06

Classification: measured development integrity and training allocation; synthetic
grid checks; full H1 study pending. This addendum changes no sealed contract.

## Confirmation progress

At 20:26 EDT, eight of twelve confirmation training jobs are complete: all four
arms for seeds 21 and 22. R23 is running and has saved checkpoint 1700. No held-out
endpoint has opened. Independent replay reproduces all eight saved training gates
exactly, covering 328 checkpoint states. Mean allocation TV is:

| Arm | Seed 21 | Seed 22 |
| --- | ---: | ---: |
| U | 0 | 0 |
| A | 0.0297591702 | 0.0293385942 |
| R | 0.0834849490 | 0.0824919974 |
| D | 0.0839106895 | 0.0858650925 |

R and D pass their allocation gates. These measurements establish intervention
and training integrity, not tracking benefit, sample efficiency or recovery from
forgetting. Shared-GPU elapsed time is recorded as execution cost and is not an
unconfounded speed comparison.

Evidence: `reports/h1_provenance_preparation_2026-09-06/confirmation_replay.json`
and `integrity.json`. The confirmation scheduler and all three follow-on
supervisors are alive. Original seals pass, the original 376-file runtime inventory
and gate 386-file source inventory match exactly, and all pilot (520), efficiency
(378) and GPU-device (417) file bindings remain unchanged.

## Development completed

New isolated tool:
`/home/linjiw/climb-icra-evidence-2026-09-06/tools/h1_evaluation_provenance.py`.
It links each evaluation to the checkpoint and ledger from an authenticated
training result, checks ledger identity/configuration and zero invalid/censored
events, then checks evaluation task/device, conditions, references, software,
evaluator source and the complete six-entry runtime metadata map. Missing or extra
runtime entries fail. Artifact content and input/output paths must match.

Pair checks require the exact declared arm/seed/checkpoint grid, distinct CSV and
metadata paths, and matching startup and initial-state hashes. Both existing
seed-81 CPU development evaluations pass against their original receipts. Their
policies are checkpoint 19 from 8-environment, 20-iteration training; evaluation
uses two training clips, four worlds per arm and a one-second horizon. No new GPU
or simulator run was required for this provenance stage.

Nineteen tests pass: the measured development replay, corrupt runtime metadata,
wrong paths/device/checkpoint hash, malformed pairing hash, wrong ledger identity,
and swapped training links rejected before reading an outcome. Synthetic 24-cell
fixtures test complete grids and rejection of missing/duplicate cells, reused
artifacts and unpaired states. Synthetic tests are not 24 completed evaluations.

The helper requires already authenticated design and training inputs. The CLI
authenticates the existing CPU development design and training runs only. It does
not authenticate a production H1 manifest, evaluate episode scores, replace the
loaded-policy immutability audit, or enable full training. Production integration
must retain those checks and the all-six-training-before-outcome-read rule.

## Verification commands

From `/home/linjiw/climb-icra-evidence-2026-09-06`, with the original pinned Python:

```bash
/home/linjiw/climb-feasibility-first/mjlab-1.6.0/.venv/bin/python tools/h1_evaluation_provenance.py --development-run reports/gate_evaluator_environment_fixed_2026-09-06 --out /home/linjiw/climb-feasibility-first/reports/h1_provenance_preparation_2026-09-06/development_verification.json
/home/linjiw/climb-feasibility-first/mjlab-1.6.0/.venv/bin/python -m pytest -q tests/test_h1_evaluation_provenance.py
/home/linjiw/climb-feasibility-first/mjlab-1.6.0/.venv/bin/python -m py_compile tools/h1_evaluation_provenance.py tests/test_h1_evaluation_provenance.py
git diff --check
```

The output option writes exclusively; preserve existing results on re-execution.
Root report directory contains development verification, test log, independent
training replay, live integrity snapshot and gate inventory verification.

## Next execution gates

1. Let the active original scheduler complete R23, D23, U23 and A23, verify all
   twelve training gates, then run the frozen 48-cell held-out evaluation.
2. Compute the original primary endpoint and queued sample-efficiency analysis
   with unchanged thresholds. The pilot and subsequent CUDA lifecycle validation
   retain their existing prerequisite and GPU-capacity gates.
3. Finish H1 production manifest authentication, score-analysis integration and
   scheduler; complete the fresh-seed audit and GPU entrypoint smokes before its
   separate freeze. Full H1 training remains disabled.
4. Interpret mechanism and physical-sensitivity evidence only after their
   respective validation gates. Hardware tracking and Sim2Real remain pending.
