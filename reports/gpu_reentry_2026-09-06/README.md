# GPU reentry and CPU evaluator progress

The original campaign timed out before its first scientific job. Its records are
preserved at `reports/relative_progress_2026-09-05/confirmation_freeze/campaign/`.
The user explicitly authorized execution once GPU capacity became available.

**Current campaign:**
`reports/relative_progress_2026-09-05/confirmation_freeze/campaign_gpu_reentry_2026-09-06/`.
U seed 21 is actually training. At the saved 10:41:51 EDT snapshot, checkpoint 1700
was complete and hash-verified; full training and all policy outcomes remain pending.

- `launch.json`: exact scheduler argv, PID, previous terminal hash and operational changes.
- `schedule_equivalence.json`: all 60 jobs unchanged except their output directory.
- `followups_launch.json`: pilot and efficiency continuation argv/PIDs.
- `pilot_queue_design.json`: unchanged scientific pilot jobs, new terminal dependency.
- `efficiency_binding.json`: exact new campaign and source/contract bindings.
- `scheduler.log`, `pilot_queue.log`, `efficiency_queue.log`: live worker logs.
- `execution_snapshot.json`, `gpu_snapshot.txt`, `process_snapshot.txt`: dated evidence.
- `verification.json` and check logs: 15 passing tests, compilation, whitespace,
  both seals and all 376 original runtime hashes preserved.

The new operational allowance waits up to 86,400 s for GPU availability; it retains
the existing free-memory/utilization gate and never retries a scientific job.
The 12-training/48-evaluation sequence and endpoint-access gate remain unchanged.

Exact scheduler command, run from `/home/linjiw/climb-feasibility-first`:

```bash
mjlab-1.6.0/.venv/bin/python tools/run_relative_confirmation.py --contract reports/relative_progress_2026-09-05/confirmation_freeze/contract.json --contract-sha256 8f2192a9b937060a9ba6aa4fbd1b4a6aed8a7da183abf1c64fa9db557a5af013 --out-dir reports/relative_progress_2026-09-05/confirmation_freeze/campaign_gpu_reentry_2026-09-06 --gpu-wait-seconds 86400
```

Do not rerun this command while the scheduler is alive. Its output uses exclusive
creation; the recorded absolute argv in `launch.json` is the actual launched form.
Current arm logs and checkpoints are inside the new campaign directory. A new
failure must remain visible and be diagnosed, not automatically retried.

CPU development evidence is in the isolated worktree
`/home/linjiw/climb-icra-evidence-2026-09-06/reports/physics_evaluator_development_2026-09-06/`.
Its `design.json` binds R11/2000, two training clips, four exact conditions,
environment seed 26090651, joint-noise seed 26090652 and a one-second window.
Every cell has a structured `*_launch.json` and raw `*.log`.

The original evaluator and all eight instrumented variants complete 36 episode
rows. Zero-intervention CSV parity, matched startup/initial policy inputs, exact
substep delay, force bounds and targeted friction are independently verified.
These are **development lifecycle results**, not confirmation, statistical
robustness or hardware transfer. Full S1 evaluation is still disabled.

Verification commands, also from the original repository root:

```bash
mjlab-1.6.0/.venv/bin/python /home/linjiw/climb-icra-evidence-2026-09-06/tools/analyze_physics_development.py --run-dir /home/linjiw/climb-icra-evidence-2026-09-06/reports/physics_evaluator_development_2026-09-06 --out /home/linjiw/climb-icra-evidence-2026-09-06/reports/physics_evaluator_development_2026-09-06/verification.json
mjlab-1.6.0/.venv/bin/python -m pytest /home/linjiw/climb-icra-evidence-2026-09-06/tests/test_confirmation_reentry.py /home/linjiw/climb-icra-evidence-2026-09-06/tests/test_physics_development.py -q
git diff --check
```

The verification output already exists; choose a new output name to reproduce.
Detailed findings, current limitations and next gates:
`plan/GPU_REENTRY_AND_EVALUATOR_PROGRESS_2026-09-06.md`.
