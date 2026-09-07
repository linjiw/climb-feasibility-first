# Completed-result manuscript build audit — September 7

**Status: measured document checks; unsealed manuscript.** This supersedes the
September 4 pending-result build as the current handoff. It does not establish
H1 benefit or complete author review/submission.

| Check | Result |
| --- | --- |
| PDF | `paper/icra/ICRA_DRAFT.pdf` |
| PDF SHA-256 | `fa00b45669e0549e717434673a077464edfd257635e94e7e185694d65f3e950e` |
| Page count | 7 total, including references; maximum 8 |
| Geometry | US Letter, 612 × 792 pt |
| Fonts | All embedded; zero Type 3 |
| Layout and citations | No overfull boxes or unresolved references; 24 cited bibliography entries |
| Visual inspection | Seven pages inspected; final figure/table layout and references remain legible |
| Primary table | All 12 signed, five-decimal entries match the completed result summary |
| Anonymity screen | Anonymous author block; no `linjiw`, `github.io` or `/home/` in extracted PDF text |
| Stale result text | Removed E4 “in progress”; distinct E4 `not_tested` and completed R/U inconclusive results |
| Original seals | Phase-G 41/41 and confirmation 7/7 entries unchanged |
| Original runtime | 376/376 bound files unchanged |
| New H1 seal | 624/624 entries pass; 514 bound source files |

The official PaperCept class and pinned Tectonic 0.17.0 remain the same as the
September 4 audit. The reproducible build fixes `SOURCE_DATE_EPOCH`; the PDF's
creation timestamp is therefore not the date of this revision. Existing
font-resolution and underfull-box warnings remain in the log; no failed layout
or citation gate is suppressed.

```bash
mjlab-1.6.0/.venv/bin/python paper/icra/render_submission_figures.py
paper/icra/build.sh
git diff --check
```

The build now exports `DRAFT.md` from the authoritative LaTeX source. Both new
manuscript figures use embedded TrueType fonts; original published figures are
unchanged. The first compilation's missing math delimiter and the corrected
successful build are preserved in the audit directory. No scientific value was
changed to fix the build.

Artifacts: `reports/fable_submission_2026-09-07/` contains build logs, page
screenshots, exact-number checks, runtime/seal checks and an anonymity text
screen. The latter is a literal-identifier check, not a complete anonymity or
conference PDF-checker certification. Final author review, optional anonymous
artifact hosting and the H1 inclusion decision remain outstanding.
