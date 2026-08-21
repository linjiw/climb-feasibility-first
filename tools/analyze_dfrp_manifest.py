#!/usr/bin/env python3
"""Summarize one DFRP manifest without changing its routing decisions."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from climb.dfrp import validate_dfrp_manifest


def summarize(manifest: dict) -> dict:
    """Return the result table and continuous repair diagnostics."""
    validate_dfrp_manifest(manifest)
    flagged = [row for row in manifest["clips"] if row["flagged"]]
    primary = [row for row in flagged if row["route"] == "repair_primary"]
    exploratory = [
        row for row in flagged if row["route"] == "repair_exploratory"
    ]

    def distribution(rows: list[dict], key: str) -> dict[str, float] | None:
        values = np.array(
            [float(row["repair"][key]) for row in rows if row.get("repair")],
            dtype=np.float64,
        )
        if values.size == 0:
            return None
        return {
            "mean": float(values.mean()),
            "p50": float(np.percentile(values, 50)),
            "p95": float(np.percentile(values, 95)),
            "max": float(values.max()),
        }

    count = len(flagged)
    return {
        "schema_version": "dfrp_census_summary/1",
        "classification": (
            "unsealed measured routing audit; legacy repair qualification is incomplete"
        ),
        "manifest_payload_sha256": manifest["payload_sha256"],
        "thresholds": manifest["config"],
        "counts": manifest["counts"],
        "strict_flagged": count,
        "primary_8cm_legacy_candidates": len(primary),
        "primary_8cm_legacy_candidate_frac": len(primary) / count,
        "additional_8to15cm_exploratory": len(exploratory),
        "additional_8to15cm_exploratory_frac": len(exploratory) / count,
        "combined_recovered_through_15cm": len(primary) + len(exploratory),
        "combined_recovered_through_15cm_frac": (
            (len(primary) + len(exploratory)) / count
        ),
        "primary_qualification_complete": sum(
            row["repair"]["qualification"] == "complete" for row in primary
        ),
        "offset_primary_m": distribution(primary, "offset_max_m"),
        "offset_exploratory_m": distribution(exploratory, "offset_max_m"),
        "integrity": manifest["integrity"],
    }


def render_markdown(summary: dict) -> str:
    """Render a concise human-readable result with claim boundaries."""
    counts = summary["counts"]
    flagged = summary["strict_flagged"]
    primary = summary["primary_8cm_legacy_candidates"]
    exploratory = summary["additional_8to15cm_exploratory"]
    combined = summary["combined_recovered_through_15cm"]
    missing = summary["integrity"]["flagged_missing_repair_records"]
    extra = summary["integrity"]["repair_records_outside_strict_flag_set"]
    return f"""# DFRP v0 legacy-artifact routing census

**Status:** unsealed measured routing audit. This reclassifies existing root-only
artifacts; it is not an 8 cm root+IK recovery result or a policy-benefit result.

| route | clips | share of strict flagged set |
|---|---:|---:|
| primary candidate, `offset <= 0.08 m` | {primary} | {primary / flagged:.1%} |
| additional exploratory, `0.08 < offset <= 0.15 m` | {exploratory} | {exploratory / flagged:.1%} |
| recovered through 15 cm | {combined} | {combined / flagged:.1%} |
| quarantine pending exact-segment/stronger-repair work | {counts['by_route'].get('quarantine', 0)} | {counts['by_route'].get('quarantine', 0) / flagged:.1%} |

The strict `infeasible_frac > 0.10` rule flags **{flagged:,}** of
{counts['clips']:,} clips. All {primary} nominal primary candidates come from
the legacy root-only operator and therefore fail the new IK/contact
qualification; **zero legacy clips are promoted to DFRP training**. Exact
support sidecars are also absent bank-wide, so `training_eligible` is
{counts['training_eligible']} by construction.

## Boundary/provenance discrepancy

The old repair directory is not exactly the new strict flagged set: strict
screening has {len(missing)} missing repair record(s), while the repair directory
has {len(extra)} out-of-scope record(s).

- missing: `{', '.join(missing) if missing else 'none'}`
- out of scope: `{', '.join(extra) if extra else 'none'}`

This does not edit the published 2,443-row census. It explains why the strict
DFRP denominator is 2,442 and must be carried as an addendum rather than silently
replacing the historical artifact.

Manifest payload: `{summary['manifest_payload_sha256']}`.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    args = parser.parse_args()
    summary = summarize(json.loads(args.manifest.read_text()))
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(summary, indent=1) + "\n")
    args.out_md.write_text(render_markdown(summary))
    print(render_markdown(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
