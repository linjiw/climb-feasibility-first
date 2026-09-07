# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

CLIMB is a research codebase for feasibility-gated humanoid motion tracking (Unitree G1, mjlab /
BeyondMimic lineage). It is simultaneously a Python extension (`climb/`), a set of CLI instruments
(`tools/`), an experiment ledger (`plan/`), measured outputs (`reports/`), manuscript sources
(`paper/`), and a GitHub Pages site (`docs/`). `AGENTS.md` holds the style, commit, and
research-integrity rules and is authoritative; `README.md` and `WORKSPACE.md` hold the scientific
status and bank-building notes.

## Environment and commands

Everything runs from the repository root with the pinned interpreter
`mjlab-1.6.0/.venv/bin/python` (Python 3.13, mjlab v1.6.0 git worktree, ignored by git). There is
no `pyproject.toml`, `pytest.ini`, or root formatter; `ruff` exists in the venv but is not
configured and reports hundreds of pre-existing findings, so do not treat it as a gate.

```bash
PY=mjlab-1.6.0/.venv/bin/python

# unit tests (≈310 tests, CPU-only, a few seconds each file). Note AGENTS.md predates this suite.
$PY -m pytest tests -q
$PY -m pytest tests/test_segment_runtime.py -q
$PY -m pytest tests/test_dfrp.py -q -k "manifest"

# validate any motion bank before use
$PY tools/validate_motion_npz.py --dir bank/SOMEBANK --quiet

# whitespace check expected before commits
git diff --check

# offline analyses have --synthetic dry-run modes (frozen analysis code for sealed experiments)
$PY tools/analyze_n3.py --synthetic
$PY tools/analyze_p_sign.py --synthetic

# training (GPU). Bank comes from env vars so mjlab's full CLI still works.
CLIMB_CLIPS=$PWD/bank/tiers/tier_50.txt CLIMB_BANK=$PWD/bank/amass MUJOCO_GL=egl WANDB_MODE=offline \
  $PY tools/climb_train.py Climb-Tracking-Flat-Unitree-G1 --env.scene.num-envs 4096 --agent.max-iterations 4000

# segment-native / Phase-G training reads CLIMB_SEGMENT_* from research.env (copy research.env.example)
$PY tools/research_preflight.py --g2-stage calibration --verify-motion-hashes --strict
$PY tools/climb_segment_train.py ...

# re-render docs/companion.html and docs/flagship.html after editing paper/ markdown (never hand-edit them)
$PY tools/render_paper_html.py

# anonymous ICRA PDF (downloads pinned tectonic + ieeeconf into a cache; output in paper/icra/build/)
paper/icra/build.sh
```

Large or licensed data is not in the repo: `bank/` (AMASS→G1 motion bank), `logs/`, `runs/`,
checkpoints, and the `mjlab-1.6.0/`, `newton15/`, `refeas/` environments. Use
`tools/restore_phase_g_bank.py` to link a local bank and `tools/research_preflight.py` to verify
hashes. GPU work must be recorded as a smoke run with exact command, seed, task id, and artifact path.

## Architecture

**`climb/` is an mjlab extension, not a fork.** `climb/__init__.py` registers task ids on import
(`Climb-Tracking-Flat-Unitree-G1`, `-Adaptive`, `-Grounded`); any mjlab entry point picks them up.
`env_cfg.py` takes mjlab's own G1 flat tracking config and swaps *only* the motion command, so
rewards, terminations, and observations stay byte-identical to upstream and the sampler is the single
manipulated variable across arms.

Layers, bottom to top:

- `motion_bank.py` — concatenates many clips along time with a per-clip offset table so mjlab's
  single-clip `time_steps` becomes a global index and all upstream accessors work untouched.
- `commands.py` — `MultiClipMotionCommand`: adds the *clip* sampling axis (uniform / adaptive /
  grounded / start). "Uniform" is uniform over clips, not frames, deliberately.
- `eligibility.py` — feasibility sidecars (fixed-width frame bins) expanded to frames and clip
  weights; masked sampling. Enabled via `CLIMB_ELIGIBILITY_*` env vars.
- `dfrp.py` — Dynamic Feasibility Repair Pipeline artifact contract: hash-bound manifests,
  fail-closed validation, exact full-horizon support sidecars. Scientific routing (admit / repair /
  quarantine) is separate from training readiness.
- `segment_curriculum.py` (pure math) → `segment_runtime.py` (stateful, checkpointable
  `SegmentSampler` with conditional failure rates and learning-progress ranking) →
  `segment_command.py` + `segment_env_cfg.py` (mjlab command that ends each fixed-horizon segment as
  an explicit time-out so references never wrap mid-transition; replaces the upstream 10 s
  `time_out` termination and adds a dt-corrected terminal failure penalty).
- `relative_progress.py` — exploratory scale-relative ALP layered on `SegmentSampler`; kept
  separate from the frozen E4 sampler.
- `contact_timing.py` / `contact_validation.py` — kinematic contact proxy and the validation
  protocol that must pass before the proxy may be treated as contact ground truth.

**Experiments are frozen by separation, not by branches.** When an experiment is sealed, its
sampler/command module is left untouched and follow-ups get a *new* module (FGAS → segment-native →
relative progress). Preserve this: never modify a module whose docstring says it is frozen or
sealed; add a sibling.

**Tools are contract-driven.** `tools/` scripts follow build → run → analyze chains keyed on JSON
manifests with sha256-bound artifacts (for example `build_g_run_manifest.py` →
`analyze_g_segment.py`; `select_dfrp_exact_panel.py` → `run_dfrp_exact_panel.py` →
`analyze_dfrp_exact_panel.py`). Analyzers reject identity mismatches before reading any result row.
Campaign shells (`run_campaign*.sh`, `run_when_free.sh`, `with_sentinel.sh`) write `COMPLETED.json`
sentinels under `reports/`. Tests in `tests/` exercise these tools with synthetic fixtures
(`tests/relative_*_fixture.py`), so a new tool normally gets a test that builds its inputs in
`tmp_path`.

## Research-integrity rules (from AGENTS.md; non-negotiable)

- Never edit sealed files or `plan/*.sha256` manifests; corrections go in a dated addendum.
- Every paper-bound number carries exactly one status label (`sealed ✓` / `sealed ✗ (kept)` /
  `measured` / `exploratory` / `pending 🕐`) and must be traceable to a `reports/` artifact via
  `paper/RESULTS_LOG.md`. Update that log whenever a paper-bound number changes.
- Analysis code for sealed experiments is frozen and dry-run on `--synthetic` data before outcomes exist.
- `plan/STATUS.md` is the live ledger; new plan/report documents are dated in the filename
  (`NAME_YYYY-MM-DD.md`).
- Motion-bank traps that fail silently (see `WORKSPACE.md`): body order must be MuJoCo depth-first,
  AMASS retargets need `--infer-fps`, AMASS banks need `ground_align_bank.py`, and `bank/lafan1` vs
  `bank/lafan1_gmr` must never be mixed in one condition.
- `docs/assets/relative-progress/snapshots.csv` keeps CRLF endings on purpose (`.gitattributes`).
