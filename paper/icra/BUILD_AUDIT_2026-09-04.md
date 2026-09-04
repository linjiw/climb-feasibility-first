# ICRA build audit — 2026-09-04

**Status:** unsealed manuscript verification. This audit reports document mechanics only; it does
not authorize Phase-G endpoint access or convert pending text into a result.

## Build result

| check | result |
|---|---|
| official class | PaperCept `ieeeconf.cls`, SHA-256 `4befef671c2a996889d325f5170d3387bf42aac9a37dcaa93724ad49816e4ec2` |
| compiler | Tectonic 0.17.0 static Linux build, archive SHA-256 `8533d07f9ccbd7a65824b9e0459041bca34af1eb33daba48f59215593753a3b7` |
| output | `paper/icra/ICRA_DRAFT.pdf`, SHA-256 `f86345d656b5949012935ec32651641cd712021b70c6ad57b6c744a917b6638c` |
| page gate | 6 of 8 total pages |
| page geometry | US Letter, 612 × 792 pt |
| fonts | all embedded; zero Type 3 fonts |
| layout log | zero overfull boxes |
| citations | 22/22 cited entries resolved; canonical metadata in `paper/icra/references.bib` |
| anonymity | anonymous author block; no author affiliation or identifying repository URL in the PDF |

Reproduce from the repository root:

```bash
paper/icra/build.sh
```

The script fails on more than eight pages, non-Letter geometry, Type 3 or unembedded fonts,
overfull boxes, or unresolved citations. The build fixes `SOURCE_DATE_EPOCH`; the final audit
reruns it twice and records the matching PDF digest under the pinned inputs.

## Remaining paper-critical slots

- Replace the Phase-G pending sentence and subsection only through the exhaustive frozen status.
- Add the calibration/validation and confirmation result tables without exceeding the remaining
  page budget.
- Replace the generic anonymous-artifact availability sentence with the final anonymous review
  artifact route.
- Run the bounded 2025–2026 proceedings novelty check, PDF checker, and final anonymity sweep.

The six-page count leaves two pages for the frozen Phase-G result objects; it is capacity evidence,
not a submission-ready verdict.
