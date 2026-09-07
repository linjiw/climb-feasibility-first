# Physical-sensitivity CPU instrumentation

**Measured development fixture; no policy evaluation or hardware transfer.**
Plan: `plan/PHYSICS_SENSITIVITY_INSTRUMENTATION_2026-09-06.md`.

All new sources and raw measurements are in
`/home/linjiw/climb-icra-evidence-2026-09-06`:

- `tools/physics_sensitivity.py`: eight intervention operators.
- `tools/smoke_physics_sensitivity.py`: named CPU G1 fixture, seed 26090641.
- `tools/analyze_physics_sensitivity_smoke.py`: independent saved-trace validation.
- `tests/test_physics_sensitivity.py`: 14 passing tests, including eight corruptions.
- `paper/figures/physics_sensitivity_fixture.py`: measured instrumentation figure.

Worktree artifacts are in `reports/physics_sensitivity_2026-09-06/`:
`cpu_smoke/{design.json,result.json,traces.pt}`, `trace_verification.json`,
`s1_preparation_draft.json`, and `intervention_checks.{png,pdf}`.
The preparation draft explicitly disables full policy evaluation.

This original-repository directory retains exact structured commands and observed
exit codes in `execution.json`, hashes/checks in `verification.json`, validation
logs, and process/GPU snapshots. The first smoke's console output remains in the
interactive tool transcript; it was not captured to a separate raw log file.
Its design/result and full tensor traces are durable. No command below edits a
frozen file; use fresh output paths when reproducing because outputs are exclusive.

Run from `/home/linjiw/climb-feasibility-first`:

```bash
mjlab-1.6.0/.venv/bin/python /home/linjiw/climb-icra-evidence-2026-09-06/tools/smoke_physics_sensitivity.py --campaign-root /home/linjiw/climb-feasibility-first --contract-sha256 8f2192a9b937060a9ba6aa4fbd1b4a6aed8a7da183abf1c64fa9db557a5af013 --out-dir /home/linjiw/climb-icra-evidence-2026-09-06/reports/physics_sensitivity_2026-09-06/cpu_smoke
mjlab-1.6.0/.venv/bin/python /home/linjiw/climb-icra-evidence-2026-09-06/tools/analyze_physics_sensitivity_smoke.py --campaign-root /home/linjiw/climb-feasibility-first --smoke-dir /home/linjiw/climb-icra-evidence-2026-09-06/reports/physics_sensitivity_2026-09-06/cpu_smoke --out /home/linjiw/climb-icra-evidence-2026-09-06/reports/physics_sensitivity_2026-09-06/trace_verification.json
mjlab-1.6.0/.venv/bin/python -m pytest /home/linjiw/climb-icra-evidence-2026-09-06/tests/test_physics_sensitivity.py -q
```

Eight two-world conditions plus the baseline repeat integrate 216 world physics
steps total, with additional nonintegrated force/reset probes. Measured delay
traces are exact; knee saturation is ±120/±90 N·m in the corresponding conditions,
while hip roll stays ±139 N·m. Friction interventions preserve untargeted values.
Baseline repeats and pre-intervention fixture states match exactly. This is a
deterministic engineering check, not statistical replication or a policy result.

The original confirmation scheduler, frozen-policy pilot queue and efficiency
postprocessor were alive at the snapshot, with confirmation waiting for GPU
capacity. All 376 original runtime files and both checked seals remain unchanged.
No GPU training/evaluation job was started by this stage.
