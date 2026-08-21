# DFRP v1 exact-panel autoresearch log

Scope, metric, guards, and selection policy are frozen in
`plan/DFRP_V1_EXACT_PANEL_2026-08-21.md` before panel execution.

| iteration | operator hash | exact-ready flagged | controls | decision | note |
|---:|---|---:|---:|---|---|
| 0 | `8ddd6987...` | 22/26 | 1/4 byte-identical | discard | Frozen gate failed: two IK-residual violations; repair entry was not enforced for controls. Apparatus audit also found sidecars lacked a source-motion hash, so two residual failures were incorrectly eligible for `segment_only`. |
| 1 | `40c367ad...` | 22/26 | 4/4 byte-identical | keep | Gate passed after enforcing strict repair entry and exact source-motion/partition bindings. Two residual and two IK-qualification failures remain excluded. |

Iteration budget: 6 including baseline. Primary objective: exact-ready flagged
count. Guard hierarchy and tie-breakers follow the frozen plan.

Iteration 0 manifest payload:
`6896a5806b15ba3977d2c31cd054e5bf7e6fb604382db744aadefcd2db7c6542`.
The result remains an audit artifact, not a promotable DFRP bank.

Iteration 1 full-panel manifest payload:
`ca505482ccda7b6d1096f054c8535eff58063bc78af34ed0ace1235427eec175`.
Curated 26-clip manifest payload:
`d2a733b983df011dd35a1987f2b2bc7bf1f82bbb17e3b6070f0514d5f2ff7218`.
The exact runtime table contains 36 admissible units and 10,561 legal starts.

## Final verification

- Deterministic selection rebuild: byte-identical; payload `900c2dbf…`.
- Full 30-clip manifest check-only rebuild: payload `ca505482…`.
- Curated 26-clip `--require-training-ready --check-only` rebuild: payload
  `d2a733b9…`.
- Exact unit-table rebuild: 36 units, 10,561 starts, SHA-256 `0df66390…`.
- Real adaptive `SegmentSampler`, 100,000 draws: all 26 clips observed, every
  trial horizon-safe, probability sum 1.0, pre-update adaptation TV 0.0.
- `tools/validate_motion_npz.py --dir bank/dfrp_v1_exact_panel --quiet`:
  26/26 pass.
- Focused CPU suite: 53 tests pass in 4.72 s.
- Changed/new Python files compile; Ruff reports all checks passed.
- `plan/FGAS_FREEZE.sha256` and `plan/N7_FREEZE.sha256` remain valid.
- `git diff --check` passes; both edited HTML pages parse successfully.

Final disposition: objective met in iteration 1. Stop the repair loop and hand
off to the isolated Newton v1.5 recertification gate. No GPU work or publishing
was performed.
