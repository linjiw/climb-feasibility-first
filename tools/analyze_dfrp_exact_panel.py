#!/usr/bin/env python3
"""Adjudicate the frozen DFRP v1 exact-repair panel."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from climb.dfrp import validate_dfrp_manifest


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_selection(selection: dict[str, Any]) -> None:
    claimed = selection.get("payload_sha256")
    payload = {key: value for key, value in selection.items() if key != "payload_sha256"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    actual = hashlib.sha256(encoded).hexdigest()
    if actual != claimed:
        raise ValueError(f"selection payload mismatch: {claimed} != {actual}")


def _distribution(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    array = np.asarray(values, dtype=np.float64)
    return {
        "mean": float(array.mean()),
        "p50": float(np.percentile(array, 50)),
        "p95": float(np.percentile(array, 95)),
        "max": float(array.max()),
    }


def analyze(
    *,
    selection: dict[str, Any],
    manifest: dict[str, Any],
    timings: dict[str, Any],
    repaired_dir: Path,
) -> dict[str, Any]:
    """Return frozen-gate metrics and per-clip diagnoses."""
    _validate_selection(selection)
    validate_dfrp_manifest(manifest)
    if timings["selection_payload_sha256"] != selection["payload_sha256"]:
        raise ValueError("timings refer to a different selection")
    manifest_names = [row["name"] for row in manifest["clips"]]
    selection_names = [row["name"] for row in selection["clips"]]
    if manifest_names != selection_names:
        raise ValueError("manifest clip order differs from frozen selection")

    manifest_by_name = {row["name"]: row for row in manifest["clips"]}
    timing_by_name = {row["name"]: row for row in timings["clips"]}
    clip_results = []
    flagged_ready = 0
    controls_ready = 0
    controls_identical = 0
    joint_limit_violations = 0
    ik_residual_violations = 0
    joint_limit_violations_all = 0
    ik_residual_violations_all = 0
    reason_counts: Counter[str] = Counter()
    fidelity_values: dict[str, list[float]] = {
        "body_mpjpe_m_p95": [],
        "joint_delta_rad_p95": [],
        "root_displacement_m_max": [],
        "root_velocity_delta_mps_p95": [],
        "root_acceleration_delta_mps2_p95": [],
    }

    for selected in selection["clips"]:
        name = selected["name"]
        row = manifest_by_name[name]
        timing = timing_by_name[name]
        repaired_path = repaired_dir / f"{name}.npz"
        record_path = Path(row["repair"]["record_path"]) if row.get("repair") else None
        record = json.loads(record_path.read_text()) if record_path else None
        is_flagged = selected["role"] == "flagged_primary_candidate"
        exact_ready = bool(
            is_flagged
            and row["route"] == "repair_primary"
            and row["training_eligible"]
        )
        byte_identical = bool(
            not is_flagged
            and repaired_path.is_file()
            and sha256_file(repaired_path) == row["original"]["sha256"]
        )
        control_ready = bool(
            not is_flagged
            and row["route"] == "raw_feasible"
            and row["training_eligible"]
        )
        flagged_ready += int(exact_ready)
        controls_ready += int(control_ready)
        controls_identical += int(byte_identical)
        for reason in row["route_reasons"]:
            reason_counts[reason] += 1
        if record:
            joint_invalid = not bool(record["joint_limits_valid"])
            ik_invalid = float(record["ik_contact_residual_m"]) > 0.01
            joint_limit_violations_all += int(joint_invalid)
            ik_residual_violations_all += int(ik_invalid)
            if row["training_eligible"]:
                joint_limit_violations += int(joint_invalid)
                ik_residual_violations += int(ik_invalid)
        fidelity = row["repair"]["fidelity"] if row.get("repair") else None
        if is_flagged and fidelity:
            for key, values in fidelity_values.items():
                values.append(float(fidelity[key]))
        clip_results.append(
            {
                "name": name,
                "role": selected["role"],
                "stratum": selected["stratum"],
                "route": row["route"],
                "training_eligible": bool(row["training_eligible"]),
                "exact_ready": exact_ready,
                "byte_identical_control": byte_identical,
                "route_reasons": row["route_reasons"],
                "infeasible_frac_before": float(row["screen"]["infeasible_frac"]),
                "infeasible_frac_after": (
                    float(row["repair"]["infeasible_frac_after"])
                    if row.get("repair")
                    else None
                ),
                "offset_max_m": (
                    float(row["repair"]["offset_max_m"])
                    if row.get("repair")
                    else None
                ),
                "legal_starts": (
                    int(row["training_sidecar"]["legal_starts"])
                    if row["training_eligible"] and row.get("training_sidecar")
                    else 0
                ),
                "joint_limits_valid": (
                    bool(record["joint_limits_valid"]) if record else None
                ),
                "ik_contact_residual_m": (
                    float(record["ik_contact_residual_m"]) if record else None
                ),
                "nonleg_support_frames": (
                    int(record["nonleg_support_frames"]) if record else None
                ),
                "elapsed_s": float(timing.get("elapsed_s", 0.0)),
            }
        )

    integrity = manifest["integrity"]
    integrity_failures = sum(len(value) for value in integrity.values())
    flagged_total = selection["counts"]["flagged"]
    controls_total = selection["counts"]["controls"]
    guards = {
        "flagged_ready_at_least_75pct": flagged_ready >= 20,
        "controls_training_ready": controls_ready == controls_total == 4,
        "controls_byte_identical": controls_identical == controls_total == 4,
        "manifest_integrity_clean": integrity_failures == 0,
        "joint_limits_clean_among_admitted": joint_limit_violations == 0,
        "ik_residual_clean_among_admitted": ik_residual_violations == 0,
    }
    return {
        "schema_version": "dfrp_exact_panel_result/1",
        "classification": "unsealed measured CPU repair result; no policy claim",
        "selection_payload_sha256": selection["payload_sha256"],
        "manifest_payload_sha256": manifest["payload_sha256"],
        "repair_tool_sha256": timings["repair_tool_sha256"],
        "counts": {
            "flagged": flagged_total,
            "flagged_exact_ready": flagged_ready,
            "flagged_exact_ready_rate": flagged_ready / flagged_total,
            "controls": controls_total,
            "controls_training_ready": controls_ready,
            "controls_byte_identical": controls_identical,
            "legal_starts": sum(row["legal_starts"] for row in clip_results),
        },
        "gate": {"passed": all(guards.values()), "guards": guards},
        "violations": {
            "manifest_integrity": integrity_failures,
            "joint_limits_admitted": joint_limit_violations,
            "ik_residual_admitted": ik_residual_violations,
            "joint_limits_all": joint_limit_violations_all,
            "ik_residual_all": ik_residual_violations_all,
        },
        "route_reasons": dict(sorted(reason_counts.items())),
        "runtime_s": _distribution(
            [float(row.get("elapsed_s", 0.0)) for row in timings["clips"]]
        ),
        "fidelity": {
            key: _distribution(values) for key, values in fidelity_values.items()
        },
        "clips": clip_results,
    }


def render_markdown(result: dict[str, Any]) -> str:
    """Render a compact gate report."""
    counts = result["counts"]
    verdict = "PASS" if result["gate"]["passed"] else "FAIL"
    guards = "\n".join(
        f"- {'PASS' if passed else 'FAIL'}: `{name}`"
        for name, passed in result["gate"]["guards"].items()
    )
    failures = [row for row in result["clips"] if row["role"].startswith("flagged") and not row["exact_ready"]]
    failure_lines = "\n".join(
        f"- `{row['name']}`: route `{row['route']}`; "
        f"after={row['infeasible_frac_after']}; reasons={row['route_reasons']}"
        for row in failures
    ) or "- none"
    runtime = result["runtime_s"]
    return f"""# DFRP v1 exact-repair panel result

**Status:** unsealed measured CPU result. **Gate: {verdict}.** No policy-benefit
or hardware claim is made.

The frozen panel produced **{counts['flagged_exact_ready']}/{counts['flagged']}**
({counts['flagged_exact_ready_rate']:.1%}) exact-ready flagged clips and
**{counts['controls_byte_identical']}/{counts['controls']}** byte-identical
controls. The admitted panel exposes **{counts['legal_starts']:,}** legal
50-step starts. Median per-clip runtime was {runtime['p50']:.2f} s and p95 was
{runtime['p95']:.2f} s.

## Frozen guards

{guards}

## Flagged clips not admitted

{failure_lines}

Selection payload: `{result['selection_payload_sha256']}`.
Manifest payload: `{result['manifest_payload_sha256']}`.
Operator SHA-256: `{result['repair_tool_sha256']}`.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--timings", type=Path, required=True)
    parser.add_argument("--repaired-dir", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(
        selection=json.loads(args.selection.read_text()),
        manifest=json.loads(args.manifest.read_text()),
        timings=json.loads(args.timings.read_text()),
        repaired_dir=args.repaired_dir,
    )
    markdown = render_markdown(result)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(result, indent=1) + "\n")
    args.out_md.write_text(markdown)
    print(markdown)
    return 0 if result["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
