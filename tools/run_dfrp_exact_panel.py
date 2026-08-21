#!/usr/bin/env python3
"""Run the frozen DFRP exact-repair panel with resumable timing records."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_selection(selection: dict[str, Any]) -> None:
    """Reject edits to the canonical selection payload."""
    claimed = selection.get("payload_sha256")
    payload = {key: value for key, value in selection.items() if key != "payload_sha256"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    actual = hashlib.sha256(encoded).hexdigest()
    if claimed != actual:
        raise ValueError(f"selection payload mismatch: {claimed} != {actual}")


def _write_progress(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=1) + "\n")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--screen-dir", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--gap-m", type=float, default=0.06)
    parser.add_argument("--clearance-m", type=float, default=0.003)
    parser.add_argument("--smoothing-s", type=float, default=0.24)
    parser.add_argument("--flag-infeasible-frac", type=float, default=0.10)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    selection = json.loads(args.selection.read_text())
    validate_selection(selection)
    repo = Path(__file__).resolve().parents[1]
    repair_tool = repo / "tools" / "dfrp_repair.py"
    directories = {
        "repaired": args.out_root / "repaired",
        "records": args.out_root / "repair_records",
        "screens_full": args.out_root / "screens_full",
        "screens_brief": args.out_root / "screens_brief",
        "sidecars": args.out_root / "sidecars",
        "logs": args.out_root / "logs",
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)

    timing_path = args.out_root / "timings.json"
    previous: dict[str, Any] = {}
    if timing_path.is_file() and not args.force:
        previous_payload = json.loads(timing_path.read_text())
        previous = {row["name"]: row for row in previous_payload.get("clips", [])}
    results: list[dict[str, Any]] = []
    started = time.time()
    for index, row in enumerate(selection["clips"], start=1):
        name = row["name"]
        products = {
            "motion": directories["repaired"] / f"{name}.npz",
            "record": directories["records"] / f"{name}.json",
            "full_screen": directories["screens_full"] / f"{name}.json",
            "brief_screen": directories["screens_brief"] / f"{name}.json",
            "sidecar": directories["sidecars"] / f"{name}.json",
        }
        if all(path.is_file() for path in products.values()) and not args.force:
            result = dict(previous.get(name, {}))
            result.update(
                {
                    "name": name,
                    "role": row["role"],
                    "status": "resumed",
                    "motion_sha256": sha256_file(products["motion"]),
                    "record_sha256": sha256_file(products["record"]),
                }
            )
            results.append(result)
            print(f"[{index:02d}/{len(selection['clips'])}] resume {name}", flush=True)
            continue
        if any(path.exists() for path in products.values()) and not args.force:
            raise SystemExit(f"{name}: partial output exists; inspect it or pass --force")

        command = [
            sys.executable,
            str(repair_tool),
            "--clip",
            name,
            "--bank",
            str(args.bank),
            "--model",
            str(args.model),
            "--screen-before",
            str(args.screen_dir / f"{name}.json"),
            "--out-dir",
            str(directories["repaired"]),
            "--record-dir",
            str(directories["records"]),
            "--full-screen-dir",
            str(directories["screens_full"]),
            "--brief-screen-dir",
            str(directories["screens_brief"]),
            "--sidecar-dir",
            str(directories["sidecars"]),
            "--gap-m",
            str(args.gap_m),
            "--clearance-m",
            str(args.clearance_m),
            "--smoothing-s",
            str(args.smoothing_s),
            "--flag-infeasible-frac",
            str(args.flag_infeasible_frac),
        ]
        if args.force:
            command.append("--force")
        log_path = directories["logs"] / f"{name}.log"
        print(f"[{index:02d}/{len(selection['clips'])}] run {name}", flush=True)
        clip_started = time.perf_counter()
        with log_path.open("w") as log:
            completed = subprocess.run(
                command,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
        elapsed = time.perf_counter() - clip_started
        result = {
            "name": name,
            "role": row["role"],
            "status": "ok" if completed.returncode == 0 else "failed",
            "returncode": completed.returncode,
            "elapsed_s": elapsed,
            "log": str(log_path),
        }
        if completed.returncode == 0:
            result["motion_sha256"] = sha256_file(products["motion"])
            result["record_sha256"] = sha256_file(products["record"])
        results.append(result)
        payload = {
            "schema_version": "dfrp_exact_panel_timings/1",
            "selection_payload_sha256": selection["payload_sha256"],
            "repair_tool_sha256": sha256_file(repair_tool),
            "config": {
                "gap_m": args.gap_m,
                "clearance_m": args.clearance_m,
                "smoothing_s": args.smoothing_s,
                "flag_infeasible_frac": args.flag_infeasible_frac,
            },
            "clips": results,
        }
        _write_progress(timing_path, payload)
        print(f"  {result['status']} {elapsed:.2f}s", flush=True)

    failures = [row for row in results if row["status"] == "failed"]
    payload = {
        "schema_version": "dfrp_exact_panel_timings/1",
        "classification": "unsealed measured CPU timing artifact",
        "selection_payload_sha256": selection["payload_sha256"],
        "repair_tool_sha256": sha256_file(repair_tool),
        "config": {
            "gap_m": args.gap_m,
            "clearance_m": args.clearance_m,
            "smoothing_s": args.smoothing_s,
            "flag_infeasible_frac": args.flag_infeasible_frac,
        },
        "elapsed_s": time.time() - started,
        "failures": [row["name"] for row in failures],
        "clips": results,
    }
    _write_progress(timing_path, payload)
    if failures:
        print(f"panel completed with {len(failures)} failures", file=sys.stderr)
        return 1
    manifest_records = args.out_root / "manifest_repair_records"
    manifest_records.mkdir(parents=True, exist_ok=True)
    for row in selection["clips"]:
        if row["role"] != "flagged_primary_candidate":
            continue
        link = manifest_records / f"{row['name']}.json"
        target = Path("..") / "repair_records" / f"{row['name']}.json"
        if link.exists() or link.is_symlink():
            if not link.is_symlink() or link.resolve() != (link.parent / target).resolve():
                raise SystemExit(f"unexpected manifest repair-record view entry: {link}")
        else:
            link.symlink_to(target)
    raw_sidecars = args.out_root / "manifest_raw_sidecars"
    repaired_sidecars = args.out_root / "manifest_repaired_sidecars"
    raw_sidecars.mkdir(parents=True, exist_ok=True)
    repaired_sidecars.mkdir(parents=True, exist_ok=True)
    for row in selection["clips"]:
        view = (
            repaired_sidecars
            if row["role"] == "flagged_primary_candidate"
            else raw_sidecars
        )
        link = view / f"{row['name']}.json"
        target = Path("..") / "sidecars" / f"{row['name']}.json"
        if link.exists() or link.is_symlink():
            if not link.is_symlink() or link.resolve() != (link.parent / target).resolve():
                raise SystemExit(f"unexpected manifest sidecar view entry: {link}")
        else:
            link.symlink_to(target)
    (args.out_root / "REPAIRS_COMPLETED").write_text(
        selection["payload_sha256"] + "\n"
    )
    print(f"panel complete: {len(results)} clips", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
