# Fable guidance execution log — 2026-08-26

## Scope and invariants

- Goal: advance the unsealed `fable.md` Phase-W guidance using CPU and writing work only.
- Sealed files and their SHA-256 manifests were not edited.
- No GPU training, new preregistration, external filing, publishing, or bank-wide repair was run.
- The pre-existing untracked `fable.md` is preserved as supplied.

## Acceptance checks

| item | acceptance criterion | result |
|---|---|---|
| W2 SONIC artifact hygiene | durable 4,950-row CSV + successful sentinel | pass: `reports/feasibility_sonic/`; 4,950 rows, 0 failures |
| W2 numerical reproduction | registered threshold counts reproduced | pass: infeasible 29/7/5 and airborne 225/111/32 at >0.05/>0.10/>0.20; flagged duration 0.000939 |
| W3 intervention framing | no adaptive exact-segment arm represented as tested | pass in flagship §8, companion §8, and §10 limitations |
| W4 DFRP framing | exact contract reported as implementation-, not policy-validated | pass in flagship §6 and companion §8 |
| W5 assembly | section sources, assembled draft, and rendered pages agree | pass; both HTML pages regenerated |
| RED_TEAM #3 | current upstream thread/code state checked | pass: both issues open, no maintainer acknowledgement or linked fix; drafts say only "filed" |

## SONIC durable rerun

Command (from the external screen implementation, writing only into this repository):

```bash
/home/robotixx/miniconda3/envs/env_isaaclab/bin/python \
  /home/robotixx/GR00T-WholeBodyControl/scripts/research/hygiene_screen_bank.py \
  --bank /data/robotixx/groot-wbc-sonic-research/datasets/bones_seed_official_headline_scale4950/robot_filtered \
  --out /data/robotixx/climb/reports/feasibility_sonic \
  --workers 8
```

The first interpreter attempted (`GR00T-WholeBodyControl/.venv`) lacked `joblib` and stopped at
import before screening. The pinned IsaacLab environment completed 4,950/4,950 clips in 179.838 s
wall with zero failures. Per-clip JSON intermediates were removed after the consolidated CSV and
sentinel were verified; they are redundant with the row-complete CSV and were not part of W2's
durable deliverable.

- CSV SHA-256: `c28fccbdd28db090c1b2e5edbfbc58d41f3c22161fab6eb8ee44427195f9a2f6`
- sentinel SHA-256: `605fd2d3e9671adad57a8db879ad249214bced5256799f5e13fca4aa9f1600bf`
- external screen SHA-256: `4ccc96f773af2163117bbcd1239e4743a45814da2775007507657100ab51eb1e`
- external bank-runner SHA-256: `aa58dcb6bf8f78fbb5279091a6da0b4921624be47fcdec3a2485c8d0dc4bf51f`
- external repository HEAD at reproduction: `9b66afbd26c47e73c4224e229c60291cb0670acb`

## Iteration disposition

Keep the durable screen artifacts and prose changes if assembly/render checks and whitespace
validation pass. Do not interpret the segment-v2 outcome as an adaptive-sampling null: its
allocation manipulation is only 0.014 TV from control.

Verification completed with `python -m py_compile tools/render_paper_html.py`, section-to-draft
diffs (content-identical; assembled copy adds only its separator newline), rendered-text searches,
and `git diff --check`. No sealed file or seal manifest appears in `git diff --name-only`.
