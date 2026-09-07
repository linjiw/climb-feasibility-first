# Useful-practice continuation, 2026-09-06

Research plan: `plan/USEFUL_PRACTICE_NEXT_STEPS_2026-09-06.md`.
The original confirmation's scientific configuration is unchanged.

`calibration_verification.json` records independent complete replay of both D
calibrations. `development_inputs.json` binds 12 read-only development checkpoints
and their ledgers/sampler states. `branch_state_inventory.json` records optimizer
and observation-normalizer presence, not tested restoration behavior.

`source_snapshot.json` binds the current source copies in the separate detached
worktree `/home/linjiw/climb-signal-quality-2026-09-06`, including untracked sources
that a bare HEAD checkout would omit. New code lives only in that worktree.
New diagnostic output also lives there; this directory contains the original
campaign's operational handoff and research-ledger evidence.

The handoff's exact argv/PID are in `handoff_launch.json`. It waits for the
existing seed-51 smoke worker, then uses the original freezer and its exact
scheduler argv. Its logs and terminal record live in `handoff/`. No automatic
retry, checkpoint substitution or scientific-parameter change is permitted.
The original 12-training-before-48-evaluation ordering is enforced by the
unchanged scheduler. All future policy results belong in
`reports/relative_progress_2026-09-05/confirmation_freeze/campaign/`.

At launch, no confirmation job had started. The GPU was occupied by an existing
unrelated job and the smoke supervisor was waiting. Do not launch another worker
over these output paths. If a worker stops, inspect its terminal disposition and
actual launch logs before choosing any documented continuation.

Reproduce the synthetic illustration into a fresh output filename:

```bash
mjlab-1.6.0/.venv/bin/python /home/linjiw/climb-signal-quality-2026-09-06/tools/reproduce_noise_only_tv.py --out /home/linjiw/climb-signal-quality-2026-09-06/reports/research_next_2026-09-06/noise_only_tv_repeat.json
```

It labels its independent Gaussian/equal-prior/inactive-cap assumptions and
never reads a robot policy or confirmation endpoint. A fixed RNG seed reproduces
the result; this is not a frozen-policy simulator study.

Verification is recorded in `verification.json` and the accompanying logs.
The two new handoff tests exercise rejection of failed/endpoint-opened smokes,
changed contracts and altered scheduler argv. They are not simulator validation.
Current full D histories are replayed by the original production verifier.
The original runtime draft check and Phase-G seal check remain required before
launch, independently of these tests.
