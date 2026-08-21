# Repository Guidelines

## Project Structure & Module Organization

`climb/` contains the Python extension that registers multi-clip mjlab tasks and implements motion-bank sampling. Executable training, evaluation, conversion, and analysis programs live in `tools/`. Treat `plan/` as the experiment ledger, `reports/` as measured outputs, `paper/` as manuscript sources and figure scripts, and `docs/` as the published site. `bank/`, `runs/`, and `logs/` hold large local data and are ignored. `mjlab-1.6.0/`, `bridge/`, and `refeas/` are pinned or separately managed environments; do not fold their changes into this repository casually.

## Build, Test, and Development Commands

Run commands from the repository root with the pinned mjlab environment:

```bash
mjlab-1.6.0/.venv/bin/python tools/validate_motion_npz.py --dir bank/SOMEBANK --quiet
mjlab-1.6.0/.venv/bin/python tools/analyze_rq1.py --features reports/features_amass.csv --eval reports/eval_tier50.csv
CLIMB_CLIPS=$PWD/bank/tiers/tier_50.txt CLIMB_BANK=$PWD/bank/amass MUJOCO_GL=egl WANDB_MODE=offline mjlab-1.6.0/.venv/bin/python tools/climb_train.py Climb-Tracking-Flat-Unitree-G1
git diff --check
```

The first validates bank schema and body ordering; the second runs an offline analysis; the third launches a local training arm; the last catches whitespace errors. See `WORKSPACE.md` for bank building, ground alignment, and evaluation commands.

## Coding Style & Naming Conventions

Use Python 3 type hints, four-space indentation, concise docstrings, and standard PEP 8 layout. Name modules, functions, and variables `snake_case`, classes `PascalCase`, and constants `UPPER_SNAKE_CASE`. Keep CLI tools narrowly scoped and expose descriptive long options such as `--episodes-per-clip`. No root formatter is configured; match nearby code and keep imports grouped standard-library, third-party, then local.

## Testing Guidelines

There is no root pytest suite or coverage threshold. Validate the smallest affected workflow: compile changed Python files, run relevant `--synthetic` analysis modes where available, and validate any generated motion bank. GPU or simulator changes require a documented smoke run with the exact command, seed, task ID, and artifact path.

## Commit & Pull Request Guidelines

Recent commits use imperative, outcome-focused subjects (for example, `Render companion and flagship drafts`). Keep commits scoped and mention the experiment or artifact when useful. Pull requests should summarize the scientific or code impact, list exact verification commands, link issues or preregistrations, and identify generated reports/figures. Include screenshots for `docs/` or rendered-paper changes.

## Research Integrity

Never edit sealed files or their `plan/*.sha256` manifests; record corrections in an addendum. Preserve claim labels (`sealed`, `measured`, `exploratory`, or `pending`) and update `paper/RESULTS_LOG.md` whenever a paper-bound number changes.
