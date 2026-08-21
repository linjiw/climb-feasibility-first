# Segment-v2 exploratory pilot artifacts

**Classification:** unsealed, one-seed wiring pilot. These artifacts do not
amend FGAS or N7 and do not establish a survival benefit.

- `result.json` is the machine-readable paired analysis.
- `eval_conditions.json` freezes 42 exact units × 3 phases × 4 replicates.
- `eval_{uniform,adaptive}.csv.meta.json` record checkpoint, environment,
  condition, initial-state, and startup-randomization hashes.
- The two `model_199_segment.json` files under `training/` are final sampler and
  exposure ledgers. Model weights and per-step trajectory CSVs remain local due
  size; the aggregate result stores all published endpoints and intervals.

The exact training, reward-gate, evaluation, and analysis record is in
`autoresearch/segment-native-260820-2259/research_log.md`. The scientific verdict
is in `plan/SEGMENT_NATIVE_PILOT_RESULT_2026-08-20.md`.
