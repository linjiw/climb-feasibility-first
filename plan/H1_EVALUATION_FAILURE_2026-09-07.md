# H1 stopped before its first evaluation cell — diagnosis and decision

**Status: measured harness failure; no policy endpoint was opened; no scientific setting is
wrong.** 7 September 2026. Unsealed diagnosis. This document changes no contract, threshold,
arm, seed, panel or decision rule, and authorizes nothing by itself.

## What happened

The sealed five-paired-seed H1 campaign (contract SHA-256 `fdc5354045bb…`) completed **12 of its
52 jobs**: both GPU entrypoint smokes and all **ten** 4,000-iteration training runs, each with
`gate_training_pass`. It then stopped on the **first** evaluation job.

```
"status": "stopped_without_complete_H1",
"job": "evaluate_on_s1041_i1000",
"reason": "evaluate_on_s1041_i1000 failed with exit code 1; no automatic retry",
"completed_at": "2026-09-07T13:45:50Z"
```

Training therefore finished well inside its 11 September cutoff, at a mean of 28.2 minutes per
run. The scheduler behaved exactly as designed: one attempt per job, no silent retry, a preserved
terminal record.

## Root cause

`paper/h1/job.py` calls `eval_paired_v2.evaluate()` directly. That function ends at

```
ValueError: reports/g_segment/eval_conditions.json:
            existing condition manifest differs from requested setup
```

`eval_paired_v2.load_or_create_manifest` rebuilds the expected condition manifest and compares it
to the stored one with strict dictionary equality. The stored Phase-G manifest carries two
provenance keys that the builder does not emit:

- `classification`: "outcome-blind Phase-G evaluation conditions; built before any Phase-G arm exists"
- `panel_txt_sha256`: `ec23b7b959dbb6bd…`

**Everything else is identical.** Reproduced directly from H1's own evaluator arguments and its
bank: all 2,800 conditions match, all 100 motion records match, and every scientific parameter
matches — environment seed 20260910, joint-noise seed 20260911, joint noise 0.05, four episodes
per start, 3.0-second window, seven phases, `nconmax` 70, `nominal` false. The only difference is
those two extra annotation keys.

The completed U/A/R/D confirmation never hit this because it ran through
`tools/eval_relative_confirmation.py`, which replaces the loader with `load_sealed_conditions`.
That function rebuilds the same expected manifest and then adds the two provenance keys before
comparing. H1's job runner simply omits that adapter.

Verified both directions, with no policy loaded and nothing written:

| Loader | Result on the stored manifest with H1's exact arguments |
| --- | --- |
| `eval_paired_v2.load_or_create_manifest` (what H1 used) | `ValueError`, the observed failure |
| `eval_relative_confirmation.load_sealed_conditions` (what the confirmation used) | accepted: 2,800 conditions, 100 motions |

So the fix is to route H1's evaluation through the adapter that is **already inside H1's own
sealed source inventory** (`…/tools/eval_relative_confirmation.py` is one of the 514 bound files).

## Two facts that bound the damage

**No endpoint was opened.** The failure occurs during manifest validation, before any checkpoint
is loaded, before any rollout, and before any CSV is written. The job's output directory is
empty. Nothing about the held-out comparison has been observed by anyone.

**Nothing scientific is wrong.** The ten training runs are complete, gate-passing and hash-bound.
The support partition, panel, hard stratum, decision rule, seeds and budget are all as sealed and
were independently verified earlier today
(`reports/fable_independent_verification_2026-09-07/`).

## Why the campaign cannot simply be continued

Continuation in place is blocked deliberately, in three independent ways:

1. `protocol.dump` writes sentinels with `open('x')`. `evaluate_on_s1041_i1000.started.json` and
   its log already exist, so re-running that job raises rather than overwriting.
2. `terminal_status.json` already exists and records `stopped_without_complete_H1`. The sealed
   code cannot rewrite it, and overwriting it by hand would destroy the record of the failure.
3. `report_h1.py` requires `contract['campaign']` to equal the campaign directory it is given, so
   a fresh directory cannot be used under the current contract.

This is the seal working as intended: a stopped campaign is terminal.

The source inventory does leave room for a repair. `protocol.sources()` globs
`paper/h1/*.py`, `tools/*.py` and `climb/**/*.py` across two worktrees. Verified empirically: a
file added under `paper/h1_eval_fix/` leaves the inventory at 514 entries and the contract still
verifies, whereas a file added under `paper/h1/` takes it to 515 and breaks verification. A
corrected runner can therefore live outside the bound tree. But it still cannot write into the
terminated campaign directory, for the reasons above.

## The decision, and what it costs

Completing H1 requires a **contract revision** — a new frozen document that changes only the
campaign path and the evaluation loader, and nothing scientific. That is a preregistration
decision, so it is recorded here rather than taken.

**Option A — ship without H1.** The manuscript is already complete and correct in this
configuration: eight pages, zero overfull boxes, all citations resolved, and the twelve
independent repairs applied. The title stays "When Failure Is Not Difficulty", the paper claims
two contributions, and admission remains the named next experiment. Cost: no admission result;
roughly five GPU-hours of completed training goes unused. Risk: none.

**Option B — revise the contract and run only the evaluation.** Freeze
`h1_fable_contract/3`, identical to v2 except that it (i) names a new campaign directory,
(ii) binds the ten completed v2 training results by SHA-256 as inputs rather than re-running
them, and (iii) applies the sealed-conditions adapter in the evaluation path. Verify that v3's
per-arm configuration digests equal v2's, which they will, since no scientific setting changes.
Then run the 40 evaluation cells and the aggregate.

Cost: roughly one GPU-hour. The GPU is now free. This leaves seven days before the 15 September
deadline and is inside the 12 September evidence cutoff. The acceptance gate is unchanged:
`report_h1.py` re-derives the entire analysis and requires exact reproduction, so a faithful run
passes and an unfaithful one fails.

**Option C — revise and re-run everything**, training included, under a single clean v3 contract.
Cost: roughly six GPU-hours, still inside the deadline, and it avoids carrying results across a
contract boundary. Slower, and it discards ten valid training runs for bookkeeping tidiness.

**Recommendation: Option C, with Option B as the fast alternative.**

Doing the repair at all is well supported: the failure is provably pre-endpoint, the fix contains
no scientific content, the adapter is already bound inside the seal, and `report_h1.py`'s exact
replay is a strong acceptance gate. The only real choice is whether to carry the ten completed
training runs across a contract boundary.

Time is not the binding constraint. The GPU is free, the deadline is eight days out, and the
evidence cutoff is five. Six GPU-hours is a single overnight. Option C therefore buys the cleaner
record for a cost the schedule can absorb: one contract, one campaign, ten training runs and forty
evaluations all under the same seal, and a preregistration entry that needs no footnote explaining
which artifacts came from which revision. For a project whose central asset is that its seals mean
exactly what they say, that is worth five GPU-hours.

Choose Option B instead if the H1 result is wanted today, or if the GPU becomes contended again.
It is scientifically equivalent; it just records that the training and the evaluation were
executed under different revisions of the same frozen design.

Whichever is chosen, this document and the preserved `terminal_status.json` are the record that
the first attempt stopped, why, and that no outcome was observed before it did.

## What was done instead, today

The twelve verified manuscript repairs were applied and the paper rebuilt to eight pages with all
gates passing. Details, per-repair justification and the artifact-level checks behind each are in
`reports/fable_independent_verification_2026-09-07/`.
