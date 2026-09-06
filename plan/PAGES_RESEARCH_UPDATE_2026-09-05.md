# Publish the relative-progress research checkpoint

Date: 2026-09-05. Classification: **publication of measured exploratory evidence;
policy benefit pending**. The public snapshot is fixed at 23:10 EDT, with D
seed 32 saved through iteration 2800 and no complete calibration decision yet.

The project landing page now reports the completed E4 `not_tested` disposition
and the completed fixed-policy DFRP comparison. The new
`docs/relative-progress.html` explains the normalization, its equivalent 80/20
mixture before active caps, the two completed R runs, the first D calibration,
unresolved progress-versus-noise mechanism, and the fixed four-arm confirmation.
The earlier segment-native page links forward while retaining its pilot scope.

Public evidence exports live in `docs/assets/relative-progress/`. The JSON
snapshot identifies original source paths and SHA-256 values. The figure and
123-row CSV are byte-identical copies of the verified R11/R12/D31 comparison.
They exclude the unfinished D32 history and do not constitute a complete
reproduction bundle. Motion payloads and trained weights are not included.
Historical design notes and the current results ledger accompany the page.

The latest read-only freeze check still returns `prerequisites_pending` (exit 2)
for D32 and the four U/A/R/D seed-51 entrypoint smokes. It creates no enabled
configuration and launches no job. Runtime files, fixed profiles, assigned seeds,
and existing sealed artifacts were not modified by this publication work.

## Validation

- `node reports/pages_update_2026-09-05/check_pages.cjs`: Playwright 1.63.0 with
  system Google Chrome, headless and GPU disabled; three pages × two widths
  (390/1440) × two color schemes pass. No script errors, broken images, missing
  local files/anchors, or horizontal document overflow. Install the review-only
  dependency with `npm install --prefix /tmp/climb-pages-review playwright@1.63.0
  --no-audit --no-fund`; serve `docs/` at 127.0.0.1:8766 before running.
- Export audit: all 123 CSV rows present, each 37-snapshot mean reproduces,
  original source hashes match, and figure/CSV copies are byte-identical.
- `sha256sum -c plan/G_SEGMENT_FREEZE.sha256`: all 41 entries pass.
- `git diff --check`: passes. The staged check initially flagged the copied
  CSV's standard CRLF row endings. A path-specific `.gitattributes` entry
  preserves those original bytes and recognizes CRLF; the full publication
  diff check then passes without changing the evidence export.

Screenshots: [desktop](../reports/pages_update_2026-09-05/relative-progress_1440_light.png),
[mobile dark](../reports/pages_update_2026-09-05/relative-progress_390_dark.png),
and [complete evidence section](../reports/pages_update_2026-09-05/evidence_desktop.png).
Machine-readable review results are in the same report directory.

Publishing uses the repository's existing legacy GitHub Pages configuration:
`master`, `/docs`. The live update is
https://linjiw.github.io/climb-feasibility-first/relative-progress.html.
Deployment success must be checked after the scoped publication commit is pushed.
