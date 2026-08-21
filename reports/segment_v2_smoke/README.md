# Segment-v2 lifecycle smoke artifacts

- `clips.txt` freezes the 10-motion mechanism panel.
- `unit_table.json` contains 42 exact feasible units and 4,679 legal 50-step
  starts, including source hashes.
- `timeline_trace.json` records 24 vectorized GPU trials. Every trial exposed
  exactly 50 reference steps and ended by explicit truncation with zero invalid
  starts, escaped references, failures, or censored resets.

The trace verifies mechanics only. It is not a policy-quality result.
