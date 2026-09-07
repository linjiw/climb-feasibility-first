#!/usr/bin/env python3
"""Test historical serialization/warm-up recipes against two unmatched hashes.

Candidates are isolated and accepted only by the existing full-file identities.
This is payload recovery, never an outcome-based motion substitution.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

from restore_dfrp_validation_payload import MANIFEST, ROOT, require_hash, sha256


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warmups", type=int, required=True)
    parser.add_argument("--format", default="%.8f")
    parser.add_argument("--warmup-clip", type=int, choices=(0, 1), default=0)
    parser.add_argument("--recovery", type=Path, default=ROOT / "bank/dfrp_validation_recovery")
    args = parser.parse_args()
    if not 0 <= args.warmups <= 10:
        parser.error("--warmups must be in [0,10]")
    recovery = args.recovery.resolve()
    audit = json.loads((recovery / "raw_audit_cuda_0.json").read_text())
    missing = [r for r in audit["checks"] if not r["pass"]]
    if len(missing) != 2:
        raise ValueError("expected the two documented CUDA mismatches")
    out = recovery / f"probe_w{args.warmups}_{args.format.replace('%', '').replace('.', '_')}"
    if args.warmup_clip:
        out = out.with_name(out.name + f"_clip{args.warmup_clip}")
    out.mkdir(exist_ok=False)
    csv_dir = out / "csv"
    csv_dir.mkdir()
    for row in missing:
        name = row["clip"]
        values = np.load(recovery / "source" / f"{name}.npy", allow_pickle=False)
        np.savetxt(csv_dir / f"{name}.csv", values, delimiter=",", fmt=args.format)
    first = csv_dir / f"{missing[args.warmup_clip]['clip']}.csv"
    for i in range(args.warmups):
        shutil.copyfile(first, csv_dir / f"000_warmup_{i}_120_jpos.csv")
    raw = out / "raw"
    subprocess.run([
        sys.executable, str(ROOT / "tools/build_motion_bank.py"), "--input-dir", str(csv_dir),
        "--output-dir", str(raw), "--input-fps", "120", "--infer-fps", "--device", "cuda:0",
    ], check=True)
    subprocess.run([sys.executable, str(ROOT / "tools/ground_align_bank.py"),
                    "--bank", str(raw)], check=True)
    checks = []
    for row in missing:
        path = raw / f"{row['clip']}.npz"
        actual = sha256(path)
        checks.append({**row, "actual": actual, "path": str(path),
                       "pass": actual == row["expected"]})
    (out / "result.json").write_text(json.dumps({"warmups": args.warmups,
        "format": args.format, "checks": checks}, indent=1) + "\n")
    print(json.dumps(checks, indent=1), flush=True)
    # A mixed verified view can use any exact candidate; original attempts stay intact.
    candidates = {r["clip"]: recovery / "raw_cuda_0" / f"{r['clip']}.npz"
                  for r in audit["checks"] if r["pass"]}
    for result in sorted(recovery.glob("probe_*/result.json")):
        for row in json.loads(result.read_text())["checks"]:
            if row["pass"]:
                candidates[row["clip"]] = Path(row["path"])
    if len(candidates) != 26:
        print(f"Exact identities available: {len(candidates)}/26", flush=True)
        return 0
    manifest = json.loads(MANIFEST.read_text())
    verified = recovery / "raw_verified"
    verified.mkdir(exist_ok=True)
    for row in manifest["clips"]:
        source = candidates[row["name"]]
        require_hash(source, row["original"]["sha256"])
        target = verified / source.name
        if not target.exists():
            target.symlink_to(source)
        require_hash(target, row["original"]["sha256"])
    from dfrp_repair import repair_motion
    model = ROOT / manifest["inputs"]["model"]
    require_hash(model, manifest["inputs"]["model_sha256"])
    require_hash(ROOT / "tools/dfrp_repair.py", manifest["inputs"]["repair_tool_sha256"])
    repaired = recovery / "repaired"
    repaired.mkdir(exist_ok=True)
    for row in manifest["clips"]:
        target = repaired / f"{row['name']}.npz"
        if not target.exists():
            repair_motion(motion_path=verified / target.name, model_path=model, output_path=target,
                          gap_m=0.06, clearance_m=0.003, smoothing_s=0.24,
                          repair_enabled=row["flagged"])
        require_hash(target, row["training_motion"]["sha256"])
    receipt = json.loads((recovery / "source_receipt.json").read_text())
    receipt.update({"raw_verified": 26, "repaired_verified": 26,
                    "raw_bank": str(verified), "repaired_bank": str(repaired), "pass": True,
                    "recovery_candidates": {name: str(path) for name, path in candidates.items()}})
    with (recovery / "recovery_result.json").open("x") as handle:
        json.dump(receipt, handle, indent=1)
        handle.write("\n")
    print("PASS all 26 historical raw and selected DFRP identities", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
