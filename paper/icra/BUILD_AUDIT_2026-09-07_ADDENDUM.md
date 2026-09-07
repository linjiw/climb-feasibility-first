# H1 manuscript preparation — September 7, 07:43 EDT

**Measured document checks; unsealed manuscript; H1 pending.** This addendum
records the current PDF. The earlier September 7 audit retains its historical
digest. No completed scientific result or frozen source changed.

| Check | Current result |
| --- | --- |
| PDF SHA-256 | `c38db9617a6c4e05866386d6e49e93056330a043881099b173816f7abb4fb7d3` |
| Length | Seven US-Letter pages including references |
| Build | Embedded fonts, zero Type 3, no overfull boxes, resolved citations; 24 cited entries |
| Visual inspection | All seven current page images inspected; equations, tables and figures legible |
| Added evidence | Shared learner/PPO settings; historical non-floor sampler qualification |
| Allocation result | Complete and inconclusive; all numeric outcomes unchanged |
| H1 | No actual outcome in source or PDF |
| Anonymous statistical companion | Seven files; SHA-256 `77a8a5fdb2cb7dc7b8c0676677922eea92057a285d0e3d2f74cabd891aa94989` |
| Companion replay | Archive hashes and paired-seed Student-t calculations pass |
| Ingestion tests | Four synthetic checks pass: incomplete, foreign, changed and mechanism evidence |
| H1 layout rehearsal | Isolated eight-page build passes; every page explicitly marked synthetic |

Artifacts are under `reports/h1_manuscript_preparation_2026-09-07/`:
`qualified_build.log`, `current-page-1.png` through `current-page-7.png`,
`learner_configuration.json`, `package_r2.json`, `package_replay_r2.log`,
`reporter_tests.log`, and `synthetic_layout_r2/`. The synthetic PDF and plots are
layout fixtures, not policy findings. Earlier candidate logs/packets are retained.

The companion validates the disclosed paired-seed statistics; it does not
reproduce simulator training or the full hierarchical bootstrap. Its literal
anonymity screen is not an official conference PDF or anonymity certification.
The current PDF is a review candidate, not a submitted paper.

Exact build/rehearsal commands:

```bash
paper/icra/build.sh
mjlab-1.6.0/.venv/bin/python paper/icra/package_review.py --out reports/h1_manuscript_preparation_2026-09-07/NO_H1_REVIEW_BUNDLE_R2.zip
mjlab-1.6.0/.venv/bin/python reports/h1_manuscript_preparation_2026-09-07/check_h1_layout_r2.py
pdftoppm -scale-to 1100 -png paper/icra/ICRA_DRAFT.pdf reports/h1_manuscript_preparation_2026-09-07/current-page
git diff --check
```

Do not rerun write-once packet or rehearsal commands over existing outputs.
H1's scientific seal stays unchanged. Its complete result will trigger the
separately guarded manuscript handoff described in
`plan/H1_MANUSCRIPT_HANDOFF_2026-09-07.md`; that new PDF requires a fresh actual-result
claim and visual audit.
