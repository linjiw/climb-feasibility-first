# DFRP v1 exact repair panel

Unsealed CPU artifacts for the frozen 30-clip repair gate in
`plan/DFRP_V1_EXACT_PANEL_2026-08-21.md`.

- `selection.json` fixes 26 flagged candidates and four controls; payload
  `900c2dbf…`.
- `baseline/` is the discarded apparatus audit.
- `iter1/result.json` is the machine-readable passing result: 22/26 flagged
  exact-ready, 4/4 byte-identical controls.
- `iter1/curated_manifest.json` is the only promoted training contract: 26
  eligible clips, payload `d2a733b9…`.
- `iter1/unit_table.json` contains 36 units and 10,561 legal 50-step starts.

Large repaired `.npz` files are intentionally excluded from Git. Reproduce them
with `tools/run_dfrp_exact_panel.py`; the committed manifests, records,
sidecars, timings, and result bind their identities. See
`plan/DFRP_V1_EXACT_PANEL_RESULT_2026-08-21.md` for claim boundaries and the
verification record.
