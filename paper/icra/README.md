# ICRA manuscript build

`root.tex` is the anonymous, unsealed submission source. The September 7 revision
reports the completed allocation confirmation as **inconclusive** and separates
it from the earlier E4 `not_tested` disposition. `DRAFT.md` is the readable
manuscript companion; `ICRA_DRAFT.pdf` is the compiled handoff.

```bash
mjlab-1.6.0/.venv/bin/python paper/icra/render_submission_figures.py
paper/icra/build.sh
```

The build downloads the official PaperCept class and a static Tectonic compiler
into an external cache and checks pinned hashes. Generated intermediates stay in
`build/` (ignored). The build checks at most eight US-Letter pages including
references, embedded fonts, no Type 3 fonts, no overfull boxes and resolved
citations. It updates `ICRA_DRAFT.pdf` only after passing.

The manuscript uses its own figures with embedded TrueType fonts. Published
result artifacts and the website are unchanged. The one-time migration script
`revise_completed_results.py` records how the earlier draft was revised; it is
not part of the build and must not be reapplied to the current source.

H1 is a separate prospectively frozen five-seed admission experiment. No pending
H1 outcome appears in the abstract or contribution list. Its result can enter only
after the complete comparison passes provenance and the calendar rules. Final
author review, the H1 inclusion decision and submission remain outstanding.
