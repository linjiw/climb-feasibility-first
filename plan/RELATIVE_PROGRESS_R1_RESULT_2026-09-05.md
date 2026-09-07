# R1 result and continuation recovery

Status: **measured exploratory simulation; manipulation pass on one seed**.
Policy benefit and independent replication remain pending. No frozen E4 endpoint
was read, no R1 gate changed, and no sealed file was edited.

## Complete seed-11 result

Task `Climb-Tracking-Flat-Unitree-G1-RelativeALP-Probe`, seed 11, 512 environments,
4,000 PPO iterations, 49,152,000 simulator transitions. Training completed
2026-09-05 12:30:02 EDT, rc=0, elapsed 2,680 seconds (0.744444 elapsed GPU-hours).
This GPU is shared; the log's 1,382/12,841 MiB baseline/peak total memory is not
isolated process memory or a clean throughput benchmark.

| Fixed check | Measured value | Disposition |
| --- | --- | --- |
| Complete checkpoint-linked telemetry | 41 snapshots, including final 3999 | pass |
| Post-warm-up snapshots | 37 at iterations ≥400 | complete |
| Mean TV in [0.05,0.15] | 0.0832113932 | pass |
| Individual post-warm-up TV range | [0.0489606076,0.1082347059] | descriptive; threshold applies to mean |
| Minimum effective units ≥12 | 616.249846 | pass |
| Maximum post-warm-up unit probability ≤0.05 | 0.0177382897 | pass |
| Maximum post-warm-up clip probability ≤0.25 | 0.0184985448 | pass |
| Final saturation <0.90 | 0.7373310811 | pass |
| Invalid starts / invalid reference frames / censored resets | 0 / 0 / 0 | pass |
| Final completed trials | 1,087,814 | measured accounting |
| Sampler, checkpoint, source and exact-support identities | exact replay and bindings pass | pass |

Original result: `reports/relative_progress_2026-09-05/study_s11/long_result.json`.
Reproduced decision: `reports/relative_progress_2026-09-05/seed11_recovery_verification.json`.
Verified complete figure and CSV:
`reports/relative_progress_2026-09-05/continuation_recovery/seed11_figure/`.

This supports sustained nonuniform allocation in one fresh training seed. It
does not show that progress rankings are informative or that tracking improved.
Comparison with E4's 0.0296587 mean TV is a cross-run mechanism comparison with
different seeds, not a matched policy effect estimate. The rise in saturation
also motivates retaining the independent full-horizon replication.

## Execution bug, preserved failure and exact correction

The first continuation ended at 12:30:04 EDT with `execution_stopped: smoke result
does not reproduce`. It launched no seed-12 run. The saved smoke summary had
relative ledger-path keys; `verify_study()` resolved them to absolute paths before
calling the checker. Consequently, the regenerated `bindings` dictionary used
different key strings even though the files, hashes, measurements and gates were
identical. Direct replay using the saved path spelling reproduced both original
smoke and long results exactly; the absolute-path variant differed only in smoke
`bindings` keys.

The fix preserves path spelling during replay. It does not loosen equality,
ignore metadata, alter floating-point tolerances, or change the scientific gate.
A regression test exercises this relative-smoke/absolute-long combination.
The failed source was archived byte-for-byte and hash-checked against its launch
design at `reports/relative_progress_2026-09-05/continuation/source_at_failed_launch.py`.
The failed design/log/terminal result remain intact. The checker and the R1/R2
training entrypoint remain unchanged.

Recovery uses the corrected continuation in a fresh `continuation_recovery/`
directory; it has already reproduced R1 and generated the complete figure.
Seed 12 is queued for ≥14,000 MiB free and ≤60% GPU utilization. The GPU is
currently shared with a separate project; no other job is interrupted.

```bash
mjlab-1.6.0/.venv/bin/python tools/continue_relative_progress.py \
  --predecessor reports/relative_progress_2026-09-05/study_s11 \
  --out-dir reports/relative_progress_2026-09-05/continuation_recovery
```

Recovery supervisor PID at launch: 1035465; durable argv/PID record:
`reports/relative_progress_2026-09-05/continuation_recovery_launch.json`.

## Prospective R3 comparator decision

`plan/R3_BASELINE_CONTRACT_2026-09-05.json` fixes the U/A/R profiles already
specified by the research design and the conditional-failure comparator D.
D uses rank `failure`, exponent 1, and exploration 0.80. This coefficient follows
from R's existing ρ=0.40, κ=2 decomposition: before active caps,
R = 0.80 × deployment prior + 0.20 × normalized progress-weighted prior.
D substitutes normalized conditional failure rates in that effective mixture.
Its setting was selected algebraically, before D training or policy outcomes.

The explicit cap-floor decomposition differs (R's protected floor is 0.40b,
D's is 0.80b), as does the initial history warm-up. Therefore R−D is an allocator
comparison, not a strict rank-only ablation. The primary R−U contrast is unchanged.
U/A retain the original common configuration; U disables adaptation by mode.

New outcome-driven tuning budget: **zero parameter changes for every arm**, one
fixed candidate per arm, no best-candidate search. D will receive pass/fail
training-only calibration at seeds 31 and 32, 512 environments, 4,000 iterations
each, after the lifecycle smokes and independent R replication pass. Both D seeds
must retain mean post-warm-up TV ≥0.05, effective units ≥12, final saturation
<0.90, valid exact support, zero invalid/censored events, and the common caps.
There is no upper 0.15 TV selection target for D; do not weaken the baseline to
match R's observed TV. D's 0.80 exploration mathematically limits TV from the
uncapped base to 0.20 when that base is admissible under the caps.

A failed D calibration stops benchmark readiness and requires a new design
addendum; no alternate setting is selected on those outcomes. Historical A/R
development costs and the new D calibration compute are unequal and must be
reported. Equal new tuning opportunities do not imply equal historical cost.
Final U/A/R/D benchmark training still uses equal compute and fresh paired seeds
21/22/23; the proposed effect/non-regression margins remain unchanged.

## Implementation and queued lifecycle verification

`tools/train_relative_policy.py` builds all four arms through the same environment
factory, adds explicit arm/stage/profile bindings, and validates actual seed and
environment count at each checkpoint. Confirmation invocation is rejected until
the future authenticated evaluator/run manifest and launch contract are ready.
The existing relative sampler and all sealed runtime files are unchanged.

`tools/run_relative_policy_smokes.py` is queued behind the recovered independent
replication. It reproduces both seeds' decisions, then runs U/A/R/D sequentially:
seed 41, 8 environments, 20 iterations per arm. It verifies exact sampler state,
checkpoint/source/profile linkage and completed/failed-trial accounting. These
CPU fixture tests are implemented; the real simulator smokes are **pending**.
Their exact argv/environment will be written before each launch under
`reports/relative_progress_2026-09-05/policy_smokes/`; task IDs are
`Climb-Tracking-Flat-Unitree-G1-Policy-{U,A,R,D}-Development`.

```bash
mjlab-1.6.0/.venv/bin/python tools/run_relative_policy_smokes.py \
  --replication-dir reports/relative_progress_2026-09-05/continuation_recovery \
  --seed11-dir reports/relative_progress_2026-09-05/study_s11 \
  --out-dir reports/relative_progress_2026-09-05/policy_smokes
```

The smoke supervisor PID at launch is 1039495. Its prerequisite wait has a
five-hour operational timeout; it cannot start before the two independent
manipulation passes. It launches neither D full calibration nor confirmation.
Authenticated evaluator ingestion remains the next CPU implementation dependency.

## Evaluator provenance component implemented

`tools/relative_policy_provenance.py` now verifies one evaluation cell's artifact
digests and cross-links without parsing CSV outcomes: checkpoint↔training ledger,
arm/stage/seed/profile, evaluator and dependency sources, software versions,
condition/reference identities, full-window population, and initial-state /
startup-randomization hashes. Its pairing checker requires all 4 arms × 3 seeds
× 4 checkpoints = 48 cells and common evaluator randomization identities.

Twelve synthetic artifact tests pass, including rehashed-but-inconsistent
metadata, replaced CSV bytes, wrong training seed, missing cells and mismatched
randomization. A deliberately invalid CSV body is accepted by the provenance-only
test when its bindings are valid, demonstrating that this layer does not parse
policy outcomes. The separate aggregation layer validates the rows afterward.

This is a component of the future adapter, not a complete campaign gate. The
outer loader must still authenticate a prospective frozen contract, reproduce
all training/calibration manipulation evidence, validate all 48 cells before
reading any outcome, and assemble the planned score arrays and learning curves.
The current development contract has `confirmation.enabled=false`, which this
component rejects for real confirmation analysis. No evaluator has been launched.
