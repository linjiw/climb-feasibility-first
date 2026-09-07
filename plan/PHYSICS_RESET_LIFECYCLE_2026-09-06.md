# Physical-evaluator reset lifecycle: measured defect and isolated correction

Date: 2026-09-06. **Unsealed development addendum.** Confirmation contract,
statistical rules, source inventory and original simulator files remain unchanged.
All implementation and raw fixtures are in the isolated ICRA worktree:
`/home/linjiw/climb-icra-evidence-2026-09-06`.

## Prospective fixture and preserved negative result

The fixture uses the original paired evaluator, development R11/2000 policy,
first two fixed training clips, phases 0/0.5, four worlds, one-second horizons,
CPU, environment seed 26090651, joint-noise seed 26090652 and task
`Climb-Tracking-Flat-Unitree-G1`. It adds a clearly named termination term,
`fixture_injected_failure`, with this fixed schedule:

| Control step | World | Intended path |
| --- | --- | --- |
| 10 | 0 | Active failure followed by partial reset |
| 20 | 0 | Another termination after that world has retired from scoring |
| 25 | 1 | Active failure while other worlds continue |
| 50 | 3 | Failure at the final horizon; failure must take precedence |

World 2 continues successfully to step 50. Expected survival steps are
[10,25,50,50] and success flags [0,0,1,0]. These are injected software conditions,
not observations of a policy's natural failure rate or robustness.

All nine original/physical conditions execute, but independent replay rejects
the three command-delay conditions. At the first partial reset, delay counters
change from [40,40,40,40] to [1,41,41,41]. Unselected history is advanced despite
no integrated physics step. The original environment reset calls
`scene.write_data_to_sim()`, which reaches the delayed built-in actuator group's
append/compute path. Some delayed output values also change during this write.
The six conditions without command delay pass the reset checks.

The complete failed fixture is preserved in
`reports/injected_reset_fixture_2026-09-06/`, including `failed_audit.json`,
per-condition CSVs, raw lifecycle/physics/policy tensors, receipts and logs.
Its pre-execution design SHA-256 is
`22deb195053d111ddfb15bfa8de150c783b1d98fb34b243649e9c6bb6a4a265c`.
Completion receipts indicate successful execution; the failed audit controls
the conformance conclusion. No failed artifact was overwritten or relabeled.

## Isolated correction and measured verification

`tools/eval_physics_reset_fixed.py` scopes a correction to the audited all-delayed
built-in G1 actuator configuration during partial reset. The ordinary reset still
clears selected buffers. The subsequent control write updates selected worlds
directly without appending a fictitious command frame. Their first integrated
physics command backfills the cleared history; unselected histories and controls
retain their existing state. Unsupported mixed/custom actuator layouts fail
explicitly. Zero-delay conditions use the original path.

This correction is currently a **development adapter**, not a change to original
confirmation sources or a deployment of the full physical-sensitivity study.
A new source-bound design was recorded before rerunning all nine conditions:
`ad0c91998ce659817a9a028bf7251042f0491589ca3fae26d05b0173200291db`.
The unchanged acceptance checks now pass in
`reports/injected_reset_fixed_2026-09-06/verification.json`:

- Nine cells × four worlds = **36 injected-fixture episode rows**; **27 partial
  resets**. Each cell has the planned survival and success flags.
- All reset IDs match actual done masks, including the already-retired world.
  Failure at the horizon remains failure.
- **80 native metric values per cell** reproduce from active-only accumulated
  and terminal metrics. Retired worlds contribute no later samples.
- Unselected qpos, qvel, motion clocks and recorded delay state remain identical
  across partial resets. Selected command buffers are cleared.
- **200 physics steps × four worlds per cell** replay the requested lag, with
  history clipped to each world's own latest reset boundary.
- Original/unchanged CSV parity, physical startup/initial input pairing,
  intervention specificity, force bounds and policy immutability pass.

The unaffected world 2's complete CSV row matches the earlier no-injection
reference in **all nine conditions both before and after the correction**.
All six non-delay full CSVs also remain unchanged. Thus this fixture establishes
a buffer-clock defect and correction, not an observed tracking-score improvement.
Repeated conditions and injected outcomes are not independent efficacy samples.

## Verification and next work

Thirteen tests pass: full corrected artifact replay, rejection of all three
preserved delayed failures, and nine corruptions of score/retirement/reset/delay
telemetry. An initial test expected only the counter mismatch; it was corrected
to accept the first detected history-value or counter mismatch while explicitly
checking the observed counter increment. The initial and final test logs remain
in the original repo's `reports/reset_lifecycle_2026-09-06/`.

Exact per-cell launch argv, task and seeds are in each fixture's `*_launch.json`.
Analyzer command:

```bash
mjlab-1.6.0/.venv/bin/python /home/linjiw/climb-icra-evidence-2026-09-06/tools/analyze_physics_reset_fixture.py --run /home/linjiw/climb-icra-evidence-2026-09-06/reports/injected_reset_fixed_2026-09-06 --out /home/linjiw/climb-icra-evidence-2026-09-06/reports/injected_reset_fixed_2026-09-06/verification.json
```

The analyzer writes a new output file exclusively; use a new output path when
replaying. Exact compile/test/seal commands, artifact hashes and CSV comparisons:
`reports/reset_lifecycle_2026-09-06/verification.json` in the original repository.
Both checked seals and all 376 original runtime hashes still match.

**Pending:** naturally failing policy trajectories, successful retirement before
the maximum vector horizon, GPU graph conformance, integration of this correction
into a separately bound general evaluation adapter, and a prospective freeze
before any full physical-sensitivity policy grid. Confirmation and its already
queued frozen-policy progress pilot retain GPU priority.

At the 12:22:30 EDT queue snapshot, U21 and A21 are the only completed confirmation
arms (2/12); no held-out endpoint is open (0/48). Scheduler and follow-on workers
remain alive. GPU free memory is 4,323 MiB and utilization 95%, so R21 continues
waiting under the existing 14,000 MiB / at-most-60% gate. Evidence:
`reports/reset_lifecycle_2026-09-06/queue_snapshot.json`.
