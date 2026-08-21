# DFRP v0 CPU result — contract, development panel, and legacy census

**Status:** unsealed measured implementation result. No GPU training was run
and no policy-benefit claim is made.

## Contract and runtime gate

`dfrp_bank_manifest/1` now separates scientific routing from training
readiness, hashes every selected motion/screen/repair/sidecar, and routes clips
under strict 10%, residual 5%, and 8/15 cm budgets. The exact-unit builder
accepts an optional DFRP manifest and embeds its payload and route. Runtime
startup re-verifies the DFRP file hash, payload identity, source identity, and
unit-table hash.

Focused CPU suite: **41 passed** across DFRP, exact support, sampler, runtime,
and reducer tests. Artifact: test command in this result's verification block.

## Two-clip development panel

The feasible control
`BMLmovi_Subject_3_F_MoSh_Subject_3_F_21` is a byte-identical no-op with a
full feasible 80-frame sidecar. `CMU_108_108_10` is repaired from
`infeasible_frac 0.1010 -> 0.0303` and airborne `0.1111 -> 0.0000` with a
39.8 mm maximum root shift. Contact IK ran on 11 frames, changed at most 0.158
rad, stayed inside joint limits, and left a 0.992 mm maximum selected-contact
residual. The materialized view contains two training-ready units and **76
legal 50-step starts**.

Artifacts: `reports/dfrp_v0/dev_panel/manifest.json` (payload
`5a6897dd2cb9a0fe7205d9a6f30143c219677e092d6ecc19fec9bc0a4e6ba992`),
`unit_table.json`, repair records, full screens, and exact sidecars.

## Full legacy-artifact routing census

Strict `>0.10` flags 2,442/10,705. Of these, 644 (26.4%) are inside the 8 cm
primary displacement budget and 962 (39.4%) are additional 8–15 cm exploratory
candidates; 1,606/2,442 (65.8%) recover through 15 cm. The remaining 836 lack
a qualifying repair under the old operator. Because all recovered files are
legacy root-only artifacts and bank-wide exact sidecars are absent, all 644
nominal primary candidates are qualification-incomplete and **zero are
training-eligible**.

The audit also corrects the historical census membership; see
`paper/CORRECTIONS_2026-08-21_DFRP.md`.

## Verification

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 mjlab-1.6.0/.venv/bin/python -m pytest -q \
  tests/test_dfrp.py tests/test_segment_curriculum.py \
  tests/test_segment_runtime.py tests/test_segment_unit_table.py \
  tests/test_screen_segments.py

mjlab-1.6.0/.venv/bin/python tools/build_segment_unit_table.py \
  --clips reports/dfrp_v0/dev_panel/training_clips.txt \
  --bank bank/dfrp_v0_dev_panel \
  --sidecars reports/dfrp_v0/dev_panel/training_sidecars \
  --horizon-steps 50 \
  --dfrp-manifest reports/dfrp_v0/dev_panel/manifest.json \
  --out reports/dfrp_v0/dev_panel/unit_table.json
```

## Decision

Keep the contract and new operator. Do not promote the legacy 644 or start a
training arm. The next CPU work is a larger source/severity-stratified root+IK
panel and exact rescreening; Newton recertification remains subsequent.
