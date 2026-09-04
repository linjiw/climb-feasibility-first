# Feasibility dataset release candidates

`amass_g1_feasibility_v1.parquet` is a typed, validated view of the measured
10,705-row clip-level table in `reports/feasibility_all/feasibility.csv`.
It contains derived feasibility summaries and clip identifiers only—no AMASS
motion trajectories.

Scope matters: every row describes one AMASS corpus / `whole_body_tracking`
retarget / Unitree G1 / flat-ground pairing. The `22.8%` result is not a rate
for AMASS generally, for every G1 retarget, or for every scene.

This is currently an **internal release candidate**, not a public release. The
adjacent manifest records hashes, schema, writer version, and limitations. The
official AMASS license prohibits making the dataset available to third parties
without prior written permission. Do not publish this derived table or masks
until written permission or a documented legal determination covers them:
<https://amass.is.tue.mpg.de/license.html>.

## Deliberate limitation

Despite the proposed filename in the advisor guidance, the committed source
table contains clip aggregates, not per-frame feasibility masks. The v1
Parquet therefore does not pretend otherwise. Producing masks requires the
licensed local motion payload plus the per-frame `refeas` pass; the release
must then bind each mask to its source-motion SHA-256.

## Rebuild

```bash
uv pip install --python mjlab-1.6.0/.venv/bin/python pyarrow==21.0.0
mjlab-1.6.0/.venv/bin/python tools/build_feasibility_release.py
```
