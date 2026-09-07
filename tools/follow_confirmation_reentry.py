#!/usr/bin/env python3
"""Postprocess a named reentry campaign without relaunching scientific jobs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_binding(binding: dict) -> None:
    for path, digest in binding["sources"].items():
        if sha256(Path(path)) != digest:
            raise ValueError(f"postprocessing dependency changed: {path}")
    if sha256(Path(binding["contract"]["path"])) != binding["contract"]["sha256"]:
        raise ValueError("confirmation contract changed")


def postprocess(binding: dict) -> dict:
    verify_binding(binding)
    campaign = Path(binding["campaign"])
    terminal = json.loads((campaign / "terminal_status.json").read_text())
    if terminal.get("status") != "completed":
        return {"status": "unavailable", "original_terminal": terminal,
                "policy_endpoints_opened": False}
    manifest = campaign / "campaign_manifest.json"
    if json.loads(manifest.read_text())["contract"] != binding["contract"]:
        raise ValueError("campaign links another contract")
    root = Path(binding["root"])
    sys.path[:0] = [str(root / "tools"), str(root)]
    from analyze_relative_campaign import analyze
    from analyze_icra_efficiency import summarize
    reproduced = analyze(manifest)
    saved = campaign / "analysis.json"
    if reproduced != json.loads(saved.read_text()):
        raise ValueError("complete original analysis does not reproduce")
    if "AULC_R_minus_U_descriptive" not in reproduced:
        raise ValueError("complete original AULC summary missing")
    return {**summarize(reproduced), "policy_endpoints_opened": True,
            "contract": binding["contract"], "campaign": str(campaign),
            "original_analysis_sha256": sha256(saved), "manifest_sha256": sha256(manifest)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--binding-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if sha256(args.binding) != args.binding_sha256 or args.out.exists():
        raise ValueError("binding changed or output already exists")
    binding = json.loads(args.binding.read_text())
    verify_binding(binding)
    terminal = Path(binding["campaign"]) / "terminal_status.json"
    deadline = time.monotonic() + binding["wait_seconds"]
    print("Waiting for reentry confirmation terminal; no endpoints opened", flush=True)
    try:
        while not terminal.exists() and time.monotonic() < deadline:
            time.sleep(min(30, max(0, deadline - time.monotonic())))
        result = postprocess(binding) if terminal.exists() else {
            "status": "pending", "reason": "wait deadline; no automatic retry",
            "policy_endpoints_opened": False}
    except Exception as exc:
        result = {"status": "postprocessing_failed", "reason": str(exc)}
    result["binding_sha256"] = args.binding_sha256
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": result["status"]}), flush=True)
    if result["status"] == "postprocessing_failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
