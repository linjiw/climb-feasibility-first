# Continuous failure retirement and reference readiness

7 September 2026. **Measured development simulation and reference-only audit.**
This advances C1 from successful traversal to natural-failure coverage. It does
not change the completed inconclusive U/A/R/D confirmation or any sealed source.

## Completed continuous failure test

Use the same two complete admitted training references, four conditions and
initial-state seeds as the earlier continuous CPU development run. Replace only
the development checkpoint with the undertrained R seed-41 policy at iteration
19. This is a lifecycle fixture, not a curriculum comparison or an estimate of
improvement from additional training: the two policies have different seeds and
training histories.

| Attempt | Declared horizon | First failure step | Survival | Terminal result |
| --- | ---: | ---: | ---: | --- |
| Flexion, replicate 0 | 429 steps | 49 | 0.98 s | failure |
| Flexion, replicate 1 | 429 steps | 64 | 1.28 s | failure |
| Rotation, replicate 0 | 306 steps | 40 | 0.80 s | failure |
| Rotation, replicate 1 | 306 steps | 37 | 0.74 s | failure |

All failures are natural simulator terminations; none was injected. All four
remain in the score denominator. The vector loop ends after 64 policy forwards,
with 27 steps containing both retired and active worlds. Five environment-reset
events and five reference-write events affect retired worlds only. No scored
attempt restarts, wraps, skips reference frames or resumes after failure.
All nine parameter tensors and four normalization buffers remain unchanged.

The new independent verifier reconstructs active masks from failure flags and
declared horizons, rather than trusting saved active masks. It authenticates the
design, source/input bindings, raw artifacts, checkpoint loading and reference
links, then reproduces native survival, success, failure frame and TrackingScore.
It also reproduces the earlier R11/2000 development run: all four attempts
complete, with 429 forwards and 123 partially active vector steps. Both runs have
exactly matching startup-randomization and initial-state hashes. These are eight
development attempts, not eight independent trained-policy replications.

Fourteen new tests cover hidden reactivation, early retirement, hidden failure,
active reset, incomplete execution, wrapping, extra steps, wrong success,
post-failure survival inflation, missing failure causes, duplicate conditions,
nonfinite metrics and failure on the final horizon step. All pass.

## Reference-only continuous-study readiness

The 100 held-out references all match the frozen panel's motion hashes, including
the 25 existing feasible-hard reference labels. Full raw-reference durations
(frames minus one, divided by 50 Hz) range from 4.98 to 72.06 seconds, with median
9.44 seconds and total 1,403.22 seconds. All exceed the original three-second
evaluation window. These are raw durations, not admitted durations or recovered
skills. No policy outcomes were read for this audit.

No named full-frame screen or sidecar for these references was found under
`reports/**/*.json` or `reports/**/*.json.gz` in screen/sidecar directories.
This is a scoped search, not proof that no archive exists elsewhere. The training
unit table covers the separate 800-clip bank; it cannot supply held-out admission.
The bank-wide brief screen contains clip summaries only. Furthermore, the severe
frame reducer includes in-contact torque-LP infeasibility, so even a small brief
`infeasible_frac` does not imply a wholly admitted reference.

The legacy screener cannot currently be invoked as-is: its hardcoded bank path,
default bridge interpreter, and `/tmp/s1_*/g1_compiled.xml.mj.xml` model source are
absent. Do not recreate an arbitrary latest model and call it the historical
screen. Either recover authenticated original frame screens, or declare and bind
a reproducible model/runtime for a separately identified screen. Match the actual
motion payloads, robot geometry, actuator limits, friction, screen code and
reducer settings before constructing continuous support. Any inability to prove
historical model equivalence must remain explicit.

## Next execution sequence

1. Recover frame-screen provenance or bind a reproducible screening entrypoint
   and model, recording whether equivalence to historical admission is established.
   Verify one known training-sidecar case before screening held-out references.
2. Produce contiguous reference-defined intervals with the full reference-access
   footprint. Report complete clips and interior intervals separately, all
   exclusions, durations and motion-family coverage. Never join rejected gaps.
3. Complete CUDA continuity validation and production C1 provenance/analysis.
   Preserve the separate physical-sensitivity exact-parity failure; individual
   lifecycle validity is not a replacement for that aggregate gate.
4. Freeze the separate U/D/R, three-seed final-policy comparison before its new
   scores are read. Keep common initial conditions, every failed attempt, and
   completion plus liveness-weighted fidelity. A reused held-out panel remains
   disclosed. No method-specific reference selection or entry advantage.

H1 admission value remains the other immediate behavioral priority. Its effect
under D and any later progress-signal intervention remain separate questions.
The September 10 claim-selection and September 12 evidence milestones stand;
the current evidence still supports neither a curriculum-benefit claim nor an
efficiency-accelerator claim.

## Commands and evidence

Pinned task: `Climb-Tracking-Flat-Unitree-G1`, CPU, four worlds; environment seed
26090691, joint-noise seed 26090692, joint noise 0.05, non-nominal startup;
development training seed 41, checkpoint 19. Exact argv:
`reports/continuous_failure_preparation_2026-09-07/command.json`.

Design and simulator outputs in the isolated worktree:
`/home/linjiw/climb-icra-evidence-2026-09-06/reports/continuous_failure_development_2026-09-07/`.
Design SHA-256:
`32afe7fc330edbc6c39d93a3ecb0085d9425b1394731a8449863af37fc2bfd20`.

New isolated tool/test:
`tools/verify_continuous_trace.py`, `tests/test_continuous_trace_replay.py`.
Run from that worktree:

```bash
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /home/linjiw/climb-feasibility-first/mjlab-1.6.0/.venv/bin/python -m pytest -q tests/test_continuous_trace_replay.py
```

Original-workspace artifacts under
`reports/continuous_failure_preparation_2026-09-07/`: `smoke.log`, `replay.json`,
`replay.log`, `tests.log`, `reference_candidates.csv`, `reference_readiness.json`,
and source `audit_reference_candidates.py`. The reference audit opens only
reference/split metadata and named screen/sidecar paths; it reads no policy score.
