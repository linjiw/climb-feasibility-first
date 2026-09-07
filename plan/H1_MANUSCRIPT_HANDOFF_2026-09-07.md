# H1 complete-result manuscript handoff — September 7

**Scope: H1 and manuscript only, following Fable revision 4.** This is an
operational manuscript addendum, not a new experiment, source freeze, endpoint,
or permission to reopen a stopped research thread. It does not alter the H1
contract `fdc5354045bb848fb982822d5ebd6d9b40ca88cb14209acc6b880579eed4b474`
or the completed allocation study.

At 07:43 EDT both GPU smokes and eight full H1 runs passed; on/1045 was running,
off/1045 remained, and zero held-out cells had opened. Training-first sequencing,
five fixed pairs, forty cells and all original resource/calendar gates remain.
Live campaign path:
`/home/linjiw/climb-gate-ablation-2026-09-06/reports/h1_fable_2026-09-07/campaign/`.
Scheduler PID 3010547 must not be duplicated. The historical snapshot receipt is
`reports/h1_manuscript_preparation_2026-09-07/training_snapshot.json`.

## Durable CPU handoff

1. Reporter PID 3357512 waits for the campaign terminal record. Only a complete
   campaign can enter `paper/icra/report_h1.py`. It verifies the contract and
   saved analyzer binding, repeats the frozen full aggregation, requires exact
   serialized equality, authenticates job sentinels and checks training-first
   ordering. It exports all five paired differences, registered intervals and
   disposition, learning curves, and the declared rejected-excess mechanism.
2. Manuscript worker PID 3377266 waits for that verified report. Before editing,
   it verifies its source and manuscript-base hashes. It backs up the current
   paper, integrates the complete actual result, and builds within eight pages.
   A failed candidate is retained for diagnosis and the previous paper restored.
3. A passing candidate receives an anonymous statistical companion, page images,
   and exact result/digest entries in `RESULTS_LOG.md` and `STATUS.md`. The terminal
   record explicitly leaves visual review, author review, and submission false.
   No worker pushes Git, updates the website or submits the paper.

Output, only after complete replay:
`reports/h1_submission_results_2026-09-07/`.
Worker designs, command arguments, start and terminal records:
`reports/h1_manuscript_preparation_2026-09-07/handoff/` and
`reports/h1_manuscript_preparation_2026-09-07/manuscript_handoff_r2/`.

Exact worker commands (already running; do not duplicate):

```bash
mjlab-1.6.0/.venv/bin/python paper/icra/follow_h1.py --design reports/h1_manuscript_preparation_2026-09-07/handoff/design.json --sha256 02f79dc61cf9ca4537f93a9a9a59f81a4d6dc0944191003256e5aac3fd93d6ad
mjlab-1.6.0/.venv/bin/python paper/icra/complete_h1_handoff.py --design reports/h1_manuscript_preparation_2026-09-07/manuscript_handoff_r2/design.json --sha256 999f9d5e31aec35a557b8835a77f00a4afbec34ac6cdc83a0f2420a22002fb1b
```

These editing guards protect an unsealed manuscript from concurrent overwrites;
they are distinct from the scientific seal. The initial manuscript worker in
`manuscript_handoff/` was stopped before integration to add the explicit
historical non-floor sampler qualification. Its STOP and terminal records remain.
The R2 design binds the qualified base and documents that supersession. No H1
science file or decision changed. Preserve edits and rebind explicitly if future
manuscript changes are needed while waiting.

The reporter closes September 13 at 00:30 EDT; manuscript postprocessing closes
02:00 EDT. These permit processing of already-complete evidence after the
September 12 evidence cutoff, not late experiment execution. A stopped campaign
produces no partial H1 effect or H1 manuscript contribution.

## Verification and completion criteria

Four synthetic reporter tests passed. The actual no-H1 paper builds at seven
pages, and its statistical companion replays. An isolated, explicitly synthetic
H1 insertion builds at eight pages, including references. Rehearsal values never
enter the actual report or current paper. Build evidence:
`paper/icra/BUILD_AUDIT_2026-09-07_ADDENDUM.md`.

After the actual complete H1 handoff: inspect every paired value and interval,
confirm the title/abstract/conclusion follow the observed sign and uncertainty,
check mechanism denominators and all-panel qualifications, and inspect every
actual PDF page. Keep the earlier allocation disposition inconclusive. Commit
the verified evidence and final draft, then complete author/conference review.
Do not create a submission tag until submission actually happens. The project
is not complete merely because background jobs or a manuscript candidate exist.
