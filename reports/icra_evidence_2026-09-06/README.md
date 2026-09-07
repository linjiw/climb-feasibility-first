# ICRA evidence preparation, 2026-09-06

Classification: **measured configuration audit and synthetic implementation checks**.
Confirmation policy utility, efficiency, physical sensitivity and hardware transfer
remain **pending**. Plan: `plan/ICRA_EVIDENCE_ROADMAP_2026-09-06.md`.

New sources are in `/home/linjiw/climb-icra-evidence-2026-09-06`:

- `tools/audit_icra_physics.py`: verify original contract/configurations and compile
  robot force limits on CPU; no policy rollout or simulator step.
- `tools/analyze_icra_efficiency.py`: original complete campaign verification before
  any real derived efficiency output; explicit pending/stopped access handling.
- `tests/test_icra_efficiency.py`: 14 focused tests, all passing.

All commands run from `/home/linjiw/climb-feasibility-first`. Output JSON files use
exclusive creation; reproduction requires fresh output names. Original sources,
package installation, bank data, profiles, seals and original queued jobs remain
unchanged. `verification.json` records 376 unchanged bound runtime files.

```bash
mjlab-1.6.0/.venv/bin/python /home/linjiw/climb-icra-evidence-2026-09-06/tools/audit_icra_physics.py --campaign-root /home/linjiw/climb-feasibility-first --contract-sha256 8f2192a9b937060a9ba6aa4fbd1b4a6aed8a7da183abf1c64fa9db557a5af013 --out reports/icra_evidence_2026-09-06/physics_audit.json
mjlab-1.6.0/.venv/bin/python /home/linjiw/climb-icra-evidence-2026-09-06/tools/analyze_icra_efficiency.py --synthetic --out reports/icra_evidence_2026-09-06/efficiency_synthetic.json
mjlab-1.6.0/.venv/bin/python /home/linjiw/climb-icra-evidence-2026-09-06/tools/analyze_icra_efficiency.py --campaign-root /home/linjiw/climb-feasibility-first --contract-sha256 8f2192a9b937060a9ba6aa4fbd1b4a6aed8a7da183abf1c64fa9db557a5af013 --out reports/icra_evidence_2026-09-06/efficiency_readiness.json
mjlab-1.6.0/.venv/bin/python -m pytest /home/linjiw/climb-icra-evidence-2026-09-06/tests/test_icra_efficiency.py -q
sha256sum --status -c plan/G_SEGMENT_FREEZE.sha256
sha256sum --status -c reports/relative_progress_2026-09-05/confirmation_freeze/confirmation.sha256
git diff --check
```

The physics audit verified the 12 exact frozen configurations and CPU-compiled all
29 actuators, including both knee clamps ±139 N·m. It records zero command delay,
5 ms physics / 20 ms control steps, training perturbations and non-nominal
evaluation startup conditions. This is configuration evidence, not a rollout
saturation measurement or hardware calibration. The manufacturer comparison and
physical-study implementation gaps are in the plan.

The synthetic report is an illustration of analysis behavior, generated before
the final additional AULC-consistency check; its arithmetic is unchanged. The final
source hash and final 14-test run are recorded in `verification.json`.
`efficiency_readiness.json` returns pending without reading policy outcomes.

`efficiency_queue_launch.json` contains the exact structured argv, PID, source
hash and log path for the single CPU postprocessing worker. It waits up to 48 h
for the original campaign terminal, attempts analysis once only on completion,
and refuses stopped/invalid campaigns. Its output will be
`efficiency_after_confirmation.json`. It launches no training/evaluation jobs and
does not change or restart either existing supervisor. A timeout yields pending;
an original execution stop yields unavailable. Exceptions remain in the queue log.
This queue is operational preparation, not a measured efficiency finding.

The original campaign's current schedule and eventual terminal are in
`reports/relative_progress_2026-09-05/confirmation_freeze/campaign/`.
At this audit no first-arm training artifact or campaign terminal existed;
the scheduler and frozen-policy pilot queue were alive. Snapshot timestamps and
shared GPU occupancy are retained in `verification.json`, `process_snapshot.txt`
and `gpu_snapshot.txt`. No GPU job was launched by this stage.
