# Segment-native and evaluation audit loop

Date: 2026-08-20. Scope: post-outcome reasoning and isolated validation; no
sealed implementation, registration, manifest, or result was changed.

## Baseline

- FGAS soft completed but failed its implementation gate: hard20 delta
  `-0.0196`, late rejected-start mass `0.199`.
- N7 completed normally. Deployment repair delta was `+0.0397`, but the sealed
  joint rule failed; raw-reference policy transfer was `-0.0036`.

## Independent review findings

Three parallel reviews audited sampling, evaluation, and research strategy.
They independently identified raw failure-flux feedback, nonterminal clip-wrap
teleports, start-only masking, binary occupancy presented as continuous severity,
unpaired startup randomization, clipped duplicate offsets, stale first
observations, and reset-contaminated terminal metrics.

## Candidates and decision

- Discard: strengthen the clip-level eligibility multiplier.
- Keep: exact admissible segments/start cells, hard support plus soft ranking,
  conditional failures per attempted unit, horizon-safe explicit trials, and
  paired phase-stratified evaluation.
- Platform order: develop in MJLab; use SONIC for external validation because
  its released bank's 0.14% flagged prevalence has little power for hygiene
  training.

## Kept changes

- `climb/segment_curriculum.py`: fail-closed exact support, conditional-rate EMA,
  deployment-floor sampling, and fixed-horizon start construction.
- `tests/test_segment_curriculum.py`: eight v2 invariant tests.
- `tools/diagnose_n7_result.py`: decomposition, repair strata, heldout overlap,
  and offset-protocol audit.
- `tools/eval_paired_v2.py`: frozen conditions, seeded environment/noise,
  horizon-safe phases, no auto-reset before terminal reads, clean observations,
  sufficient contact capacity, causes, quality metrics, and artifact hashes.

## Verification

- Ruff: pass. Ty: pass.
- Focused test suite: 16 passed.
- Paired evaluator synthetic invariants: pass.
- One-world seeded GPU success smoke: pass twice; success/survival identical,
  startup-randomization and initial-state hashes identical; continuous metrics
  varied only by small GPU floating-point noise.
- Forced-failure smoke: `anchor_pos` at 0.30 s with nonzero terminal errors and
  effort; no broadphase overflow after pinning `nconmax=70`.
- FGAS and N7 seal manifests: rechecked at handoff end.

## Next measurable loop

Implement explicit segment-boundary truncation/resume state, then gate a
10-motion/512-env/at-most-200-iteration smoke on zero invalid starts, no
continuing teleports, exact sampling floor, exposure-invariant priority, and
exact checkpoint resume. Only then seal a three-arm, three-seed MJLab study.
