# Frozen five-pair H1 submission study

This directory adds a production adapter around the unchanged, CPU-validated H1
runtime. It lives outside the archived `tools/` inventory so the original 386
source bindings remain reproducible. `protocol.py` changes the assigned seeds
in the launch process only; it does not rewrite the earlier three-seed draft.

Contract: `reports/h1_fable_2026-09-07/contract.json`, SHA-256
`fdc5354045bb848fb982822d5ebd6d9b40ca88cb14209acc6b880579eed4b474`.
`H1_FREEZE.sha256` binds 624 artifacts, including these Python sources. Do not
edit them after freeze. The Markdown README is an unsealed navigation aid.

The existing scheduler owns `reports/h1_fable_2026-09-07/campaign/`. Read
`status.json` for progress; `STOP` requests termination. Do not relaunch the
scheduler or rerun tests that overwrite the sealed test receipt. There is one
attempt per job, all ten full training gates precede all forty held-out cells,
and a stopped or partial campaign yields no paper result.

The manuscript and research ledger are maintained in the main research worktree:
`/home/linjiw/climb-feasibility-first/plan/H1_FABLE_FREEZE_2026-09-07.md`.
Motion payloads and model checkpoints remain local; metadata and reconstruction
instructions are distinct from permission to redistribute licensed motions.
