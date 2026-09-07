# H1 submission experiment: frozen five-pair comparison

**Status: sealed prospectively, execution pending GPU capacity.** September 7,
2026. Implements the user's adoption of Fable revision 4; replaces the unlaunched
three-seed H1 draft as the production design. The completed U/A/R/D confirmation
and all its thresholds are unchanged.

Contract: `/home/linjiw/climb-gate-ablation-2026-09-06/reports/h1_fable_2026-09-07/contract.json`.
SHA-256: `fdc5354045bb848fb982822d5ebd6d9b40ca88cb14209acc6b880579eed4b474`.
Seal: adjoining `H1_FREEZE.sha256`, **624 bound entries**, including 514 source
files. A byte-identical contract/audit mirror is in
`reports/h1_fable_submission_2026-09-07/`. Do not edit the contract, manifest,
source inventory or bound files. Source is preserved on branch
`h1-fable-five-seed-2026-09-07`, production-source commit `1336601`;
`a4bb6d1` additionally preserves the existing CPU support/provenance artifacts.
The already implemented evaluator dependencies are archived unchanged on
`icra-evidence-archive-2026-09-07` at `6537359`.

The five fresh paired training seeds are **1041–1045**, selected and searched
against existing local JSON/YAML/log records in four research worktrees before
freezing. The audit does not assert absence from unrecorded external experiments.
Both GPU training smokes use the already validated development seed 81. Their
results must replay and their initial actors must match before any full run.

Each on/off pair uses the same conditional-failure D allocator, candidate
partition, legal non-wrapping 50-step semantics, learner, reward, caps and full
49,152,000-transition budget. On applies the admission mask; off retains rejected
intervals. The changed prior normalization is explicit. The shared table has
1,184 admitted and 465 rejected units, with 368,951 admitted of 417,072 legal starts.
This is the effect of admission under D, not an admission-by-R interaction.

## Fixed execution and decision

Exactly two GPU smokes, ten 4,000-iteration training runs, then forty evaluations
at 1000/2000/3000/3999. Training order alternates on/off order by seed. All ten
training records, all 410 full-run saved states, their exact sampler replay and
paired initial actors must pass before any held-out cell opens. Each evaluator
cell authenticates the checkpoint, inference tensors and immutability, reference
hashes, conditions and paired startup/initial-state hashes. The 100-clip panel
and 25 hard clips are reused from the earlier study, explicitly disclosed.

The final feasible-hard on-minus-off score is primary: positive if the two-sided
paired seed-level 95% t interval's lower bound exceeds zero, negative if its upper
bound is below zero, otherwise inconclusive (five independent pairs, df=4).
+0.02 is a reference line only. The all-panel interval is descriptive, with no
new pass/fail guard. The paired seed/clip bootstrap is supplementary and cannot
override the primary result. Earlier checkpoints are descriptive.

Every checkpoint must have zero invalid starts, invalid reference frames and
censored resets; all saved checkpoint tensors must be finite. On must have zero
rejected trials. Off must have positive rejected completed trials and at least
0.0923 post-cap rejected probability. Post-warm-up saved checkpoints retain
positive excess allocation above the prior on rejected intervals, its share of
all positive excess, and top-1 identity/rejected status. No-excess cases remain
undefined rather than assigned an invented share.

## Scheduler and cutoffs

```bash
/home/linjiw/climb-feasibility-first/mjlab-1.6.0/.venv/bin/python \
  /home/linjiw/climb-gate-ablation-2026-09-06/paper/h1/campaign.py \
  --contract /home/linjiw/climb-gate-ablation-2026-09-06/reports/h1_fable_2026-09-07/contract.json \
  --sha256 fdc5354045bb848fb982822d5ebd6d9b40ca88cb14209acc6b880579eed4b474
```

The durable scheduler was started with PID **3010547**. This command documents
the existing launch; do not start a second scheduler. `campaign/status.json`
contains live state. Each job has an exclusive start sentinel, log, verified
result and completion sentinel. `campaign/STOP` requests termination, including
the active child process group. No automatic retries or silent campaign restart.

Before each GPU job: at least 14,000 MiB free and utilization at most 60%; wait at
most two hours, then stop. First full training must start by September 8, 22:00
EDT; all training must complete by September 11, 12:00 EDT. The evidence cutoff
is September 12, 23:59:59 EDT. A calendar failure or incomplete campaign supplies
no H1 paper result. The September 10 midpoint review checks whether at least six
training gates have passed and whether completion remains plausible.

Validation before freezing: eight synthetic protocol/scheduler tests, positive,
negative, variable inconclusive and exact-zero decision cases; invalid panel and
missing training rejection; resource threshold, timeout, STOP and calendar gates;
both original CPU smokes replay with finite checkpoint tensors (on 0 rejected
completed trials, off 25). GPU execution is a separate prerequisite, not implied
by these checks. All 624 seal entries subsequently passed SHA-256 verification.
