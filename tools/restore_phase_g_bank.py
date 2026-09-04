#!/usr/bin/env python3
"""Verify and optionally link a licensed Phase-G AMASS-to-G1 motion bank.

This tool never downloads or redistributes motion data.  It accepts a local
directory supplied by the researcher, checks every required ``.npz`` against
the identities already committed for Phase G, and only then can expose that
directory at the repository's ignored ``bank/amass`` path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[1]
Scope = Literal["calibration", "full"]
SHA256_RE = re.compile(r"[0-9a-f]{64}")


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: Any) -> str:
    """Return the canonical JSON identity used by the Phase-G runtime."""
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _validate_identity(
    name: object, digest: object, *, source: str
) -> tuple[str, str]:
    """Validate one safe flat filename and SHA-256 pair."""
    if (
        not isinstance(name, str)
        or not name
        or name in {".", ".."}
        or Path(name).name != name
    ):
        raise ValueError(f"{source}: unsafe or invalid clip name {name!r}")
    if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
        raise ValueError(f"{source}: invalid SHA-256 for {name!r}")
    return name, digest


def load_requirements(
    unit_table_path: Path,
    panel_manifest_path: Path,
    *,
    scope: Scope,
) -> tuple[dict[str, str], dict[str, int], dict[str, str]]:
    """Load and validate the exact payload identities for one launch scope."""
    unit_table = json.loads(unit_table_path.read_text())
    frozen = {
        "horizon_steps": unit_table["horizon_steps"],
        "sources": unit_table["sources"],
        "source_units": unit_table["source_units"],
        "admissible_units": unit_table["admissible_units"],
    }
    if unit_table.get("schema_version") != "segment_unit_table/1":
        raise ValueError("unsupported Phase-G unit-table schema")
    if canonical_hash(frozen) != unit_table.get("unit_table_sha256"):
        raise ValueError("Phase-G unit-table canonical hash mismatch")

    training: dict[str, str] = {}
    for row in unit_table["sources"]:
        name, digest = _validate_identity(
            row.get("clip"), row.get("motion_sha256"), source="unit table"
        )
        if name in training:
            raise ValueError(f"unit table repeats motion {name!r}")
        training[name] = digest

    evaluation: dict[str, str] = {}
    if scope == "full":
        panel = json.loads(panel_manifest_path.read_text())
        panel_list_path = panel_manifest_path.with_name("panel.txt")
        if panel.get("schema_version") != "g_segment_eval_panel/1":
            raise ValueError("unsupported Phase-G evaluation-panel schema")
        raw_hashes = panel.get("motion_sha256")
        if not isinstance(raw_hashes, dict) or panel.get("size") != len(raw_hashes):
            raise ValueError("evaluation-panel size/hash-map mismatch")
        panel_names = [
            line.strip()
            for line in panel_list_path.read_text().splitlines()
            if line.strip()
        ]
        if (
            len(panel_names) != len(set(panel_names))
            or set(panel_names) != set(raw_hashes)
            or panel.get("panel_txt_sha256") != sha256_file(panel_list_path)
        ):
            raise ValueError("evaluation panel list/hash-map identity mismatch")
        for raw_name, raw_digest in raw_hashes.items():
            name, digest = _validate_identity(
                raw_name, raw_digest, source="evaluation panel"
            )
            evaluation[name] = digest

    requirements = dict(training)
    for name, digest in evaluation.items():
        if name in requirements and requirements[name] != digest:
            raise ValueError(f"conflicting identities for {name!r}")
        requirements[name] = digest
    counts = {
        "training": len(training),
        "evaluation": len(evaluation),
        "unique": len(requirements),
    }
    inputs = {
        "unit_table": sha256_file(unit_table_path),
        "panel_manifest": sha256_file(panel_manifest_path),
    }
    if scope == "full":
        inputs["panel"] = sha256_file(panel_manifest_path.with_name("panel.txt"))
    return requirements, counts, inputs


def audit_source(source_dir: Path, requirements: dict[str, str]) -> dict[str, object]:
    """Hash-check every required file in a researcher-supplied local bank."""
    if not source_dir.is_dir():
        return {
            "required": len(requirements),
            "verified": 0,
            "missing": [],
            "mismatched": [],
            "error": f"licensed source directory does not exist: {source_dir}",
            "pass": False,
        }
    missing: list[str] = []
    mismatched: list[dict[str, str]] = []
    for name, expected in requirements.items():
        path = source_dir / f"{name}.npz"
        if not path.is_file():
            missing.append(name)
            continue
        actual = sha256_file(path)
        if actual != expected:
            mismatched.append({"clip": name, "expected": expected, "actual": actual})
    return {
        "required": len(requirements),
        "verified": len(requirements) - len(missing) - len(mismatched),
        "missing": missing,
        "mismatched": mismatched,
        "pass": not missing and not mismatched,
    }


def link_bank(source_dir: Path, destination: Path) -> str:
    """Expose a verified bank with one non-destructive directory symlink."""
    source = source_dir.resolve()
    destination = destination.absolute()
    if destination.is_symlink():
        if destination.resolve() != source:
            raise FileExistsError(
                f"destination symlink points elsewhere: {destination} -> "
                f"{destination.resolve()}"
            )
        return "existing_verified_symlink"
    if destination.exists():
        if destination.resolve() == source:
            return "source_is_destination"
        raise FileExistsError(
            f"destination already exists; refusing to replace it: {destination}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    relative_source = os.path.relpath(source, start=destination.parent)
    destination.symlink_to(relative_source, target_is_directory=True)
    return "created_symlink"


def parse_args() -> argparse.Namespace:
    """Parse the local payload-intake CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument(
        "--scope",
        choices=("calibration", "full"),
        default="full",
        help="calibration checks 800 training motions; full also checks 100 evaluation motions",
    )
    parser.add_argument(
        "--unit-table",
        type=Path,
        default=ROOT / "reports/g_segment/unit_table.json",
    )
    parser.add_argument(
        "--panel-manifest",
        type=Path,
        default=ROOT / "reports/g_segment/panel/panel_manifest.json",
    )
    parser.add_argument(
        "--link-destination",
        type=Path,
        help="after verification, symlink the source directory here (for example bank/amass)",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="optional local receipt; absolute source paths are recorded",
    )
    return parser.parse_args()


def main() -> int:
    """Verify the exact source payload before performing any requested link."""
    args = parse_args()
    requirements, counts, inputs = load_requirements(
        args.unit_table,
        args.panel_manifest,
        scope=args.scope,
    )
    source = args.source_dir.expanduser().resolve()
    audit = audit_source(source, requirements)
    report: dict[str, object] = {
        "schema_version": "phase_g_bank_intake/1",
        "classification": "local licensed-payload receipt; no motion data redistributed",
        "scope": args.scope,
        "source_dir": str(source),
        "requirements": counts,
        "inputs": inputs,
        "audit": audit,
        "link": {"status": "not_requested"},
        "tool_sha256": sha256_file(Path(__file__).resolve()),
    }
    if not audit["pass"]:
        print(json.dumps(report, indent=1, sort_keys=True))
        return 2
    if args.link_destination is not None:
        destination = args.link_destination.expanduser()
        if not destination.is_absolute():
            destination = ROOT / destination
        status = link_bank(source, destination)
        report["link"] = {"status": status, "destination": str(destination)}
    if args.json_out is not None:
        output = args.json_out.expanduser()
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps(report, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
