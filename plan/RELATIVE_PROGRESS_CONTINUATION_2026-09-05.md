# R1 → R2 continuation and R3 preparation

Status: **authorized execution / prospective analysis preparation**, 2026-09-05.
The user requested continued work toward the experiment and accepted design.
This addendum changes no R1/R2 settings, gates, or sealed artifact. The design
bound by the running seed-11 study remains byte-identical.

## Active execution

R1 seed 11 continues its original 512-environment, 4,000-iteration run. A separate
supervisor, `tools/continue_relative_progress.py`, waits for the complete terminal
decision, verifies the unchanged design/source identities and successful training
sentinel, and reproduces both smoke and long results from saved checkpoint-linked
ledgers and sampler states. A partial trajectory cannot authorize R2.

- Scientific failure: preserve the complete failed result and figure; stop R2.
- Missing, malformed, changed, or inconsistent evidence: record execution stop.
- Complete pass: wait for ≥14,000 MiB free and ≤60% shared-GPU utilization, then
  execute unchanged seed-12 smoke → full run → verification. No OOM retries or
  automatic hyperparameter substitutions are introduced.
- Both seeds pass: record `replicated_manipulation` and generate the two-seed
  figure and CSV. Policy benefit remains pending. This supervisor stops at R2.

The wait budget is 7,200 seconds for R1 completion and the subsequent GPU wait;
seed-12 training then runs to its fixed iteration limit. This is an operational
timeout, not a scientific stopping boundary. Output directories are exclusively
created so an attempt cannot overwrite another attempt.

```bash
mjlab-1.6.0/.venv/bin/python tools/continue_relative_progress.py \
  --predecessor reports/relative_progress_2026-09-05/study_s11 \
  --predecessor-pid 830991 \
  --out-dir reports/relative_progress_2026-09-05/continuation
```

At launch the continuation supervisor PID was 866282. Durable command identity:
`reports/relative_progress_2026-09-05/continuation_launch.json`. Its log is
`continuation_launcher.log`, its binding is `continuation/design.json`, and its
terminal result will be `continuation/terminal_status.json`.

The plotter accepts only complete reproduced long results, draws all 41 snapshots
per seed, labels scientific pass/fail, marks the post-warm-up boundary, and writes
PNG, PDF, CSV and source provenance. The TV band applies to the post-warm-up
mean; the saturation criterion applies to the final snapshot. Neither figure
licenses a policy-performance claim.

## R3 analysis implementation

`tools/analyze_relative_policy.py` now implements a pure prospective kernel:

1. Exact condition accounting before aggregation: fail on missing, extra or
   duplicate rows, mismatched clips/start frames/replicates/horizons, short
   windows, and nonfinite or invalid measurements. Zero-survival trials remain
   in the clip mean. TrackingScore uses the retained 0.30 m / 0.40 rad scales
   and multiplies precision by survived-window fraction.
2. Matched score arrays for all U/A/R/D arms, exactly seeds 21/22/23 and 100 clips,
   with 25 reference-defined feasible-hard indices. Each clip receives equal
   weight after averaging its fixed conditions.
3. Primary R−U and all-panel non-regression use paired seed deltas and a two-sided
   Student-t 95% interval with two degrees of freedom. This makes the design's
   seed-level interval explicit; it assumes approximately normal independent
   seed deltas, which three seeds cannot diagnose. Report the raw deltas.
4. Paired hierarchical seed/clip percentile intervals, 10,000 draws, seed 20260905,
   supplement that decision. Primary and all-panel intervals resample their
   respective clip populations; neither replaces the independent seed count.
5. Positive requires primary mean ≥0.02, positive lower seed interval, and the
   all-panel lower interval >−0.01. A primary upper interval below 0.02 is
   `negative_for_prespecified_effect`; otherwise inconclusive. All-panel
   regression can block a positive hard-clip result. R−A/R−D are descriptive.

Synthetic cases cover positive, negative-for-SESOI, inconclusive, hard-clip gains
with all-panel regression, invalid provenance, and failed manipulation. Separate
tests reject condition loss/duplication and seed/clip-count errors.

The CLI intentionally accepts only `--synthetic`: actual authenticated evaluator
ingestion is **not implemented**. Boolean gate arguments are integration hooks,
not proof of provenance. Existing E4 policy endpoints remain unopened. This
kernel is not yet a frozen confirmatory analyzer or a complete R3 launch tool.

## Data readiness and remaining dependencies

The existing preflight verified all 900 motion hashes (800 training + 100
evaluation), the 1,184-unit table/368,951 starts, the disjoint 100-motion panel,
2,800 full-window evaluation conditions and 25/75 reference strata. The complete
preflight returned **not launch-ready** because its old G2-specific environment
variables were absent in this invocation. It is an input-availability audit,
not approval or readiness of the new R3 experiment. The original failed check
is retained without relabeling it:
`reports/relative_progress_2026-09-05/r3_input_preflight.{json,log}`.

Exact invocation:

```bash
mjlab-1.6.0/.venv/bin/python tools/research_preflight.py \
  --g2-stage confirmation --verify-motion-hashes --strict \
  --json-out reports/relative_progress_2026-09-05/r3_input_preflight.json
```

This general preflight also ran its built-in 4-environment/5-step MJLab smoke
and Newton allocation check while R1 was active. They passed; they briefly shared
the GPU. The R1 configuration and evaluator-access boundary were unchanged.
Future input-only audits should avoid that broad simulator preflight during a
training arm. Contact timing remains omitted without independent validation.

Before R3 can run: both R1/R2 complete passes; the conditional-failure baseline's
training-only calibration contract and explicit tuning-budget accounting; all
four arm configurations and lifecycle smoke; a hash-complete checkpoint/ledger/
CSV/metadata adapter; a final prospective manifest and numerical analyzer freeze.
No R3 training seeds or policy evaluations are launched by this continuation.
