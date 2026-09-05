# E1–E4 publication and execution checkpoint

Measured verification, 2026-09-05. No confirmatory policy endpoint is reported.

- `bash paper/icra/build.sh`: passed, seven US Letter pages, embedded fonts,
  no Type 3 fonts, overfull boxes, or unresolved citations.
- Method equations and E4 results visually inspected in `method.png` and
  `results.png`; project-page E4 section inspected in `site_e4.png`.
- `mjlab-1.6.0/.venv/bin/python -m pytest tests/test_e4_continuation.py -q`:
  six tests passed, including missing/changed/failed seed-1 records, a
  failed all-seed gate preventing evaluator launch, and explicit common-reference
  binding in all 24 evaluation commands.
- `tools/run_e4_confirmation.py --dry-run`: four remaining training arms and
  24 evaluation cells, gated by the existing seed-1 and complete-manipulation
  contracts.
- Python compilation and `git diff --check`: passed.
- `sha256sum --check --status plan/G_SEGMENT_FREEZE.sha256`: all 41 sealed
  artifacts unchanged.

The writing skill informed the evidence boundaries: same-architecture transfer,
clip-versus-unit concentration denominators, exploratory pilot fidelity, and
distinguishing a null from an equivalence result. The revision adds a dedicated
E4 results subsection, publication names for its arms, mathematical notation in
both draft sources, and the existing DFRP derivative-distortion measurements.

DFRP recovery has staged 26/26 source arrays from the immutable source revision,
each checked against its Git LFS SHA-256. The restored `refeas` model matches the
historical model hash. A CPU reconstruction matches 0/26 historical raw output
hashes and is rejected; CUDA reconstruction remains the next payload step.
Licensed arrays and all reconstruction products stay in ignored `bank/`.
