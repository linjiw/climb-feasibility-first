#!/usr/bin/env python3
"""Reconstruct the existing 26-clip DFRP panel in an isolated local directory.

Source arrays come from the same immutable source revision that reproduced the
900 E4 identities. Every raw and repaired output must match the old manifest.
No historical artifact or active training bank is modified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REVISION = "275c4c4a028cadf5241c10a613c2f11913531ad2"
MANIFEST = ROOT / "reports/dfrp_v1_exact_panel/iter1/curated_manifest.json"


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def require_hash(path: Path, expected: str) -> None:
    if not path.is_file() or sha256(path) != expected:
        raise ValueError(f"missing or mismatched artifact: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text())
    rows = manifest["clips"]
    tree = subprocess.check_output([
        "git", "-C", str(args.source_repo), "ls-tree", "-r", "--name-only", REVISION,
    ], text=True).splitlines()
    lookup: dict[str, list[str]] = {}
    for path in tree:
        if path.startswith("g1/") and path.endswith(".npy"):
            stem = path[3:-4].replace("/", "_").replace(" ", "_")
            lookup.setdefault(stem, []).append(path)
    source_records = []
    csv_dir = out / "csv"
    csv_dir.mkdir(exist_ok=True)
    for row in rows:
        name = row["name"]
        paths = lookup.get(name, [])
        if len(paths) != 1:
            raise ValueError(f"{name}: expected unique source, got {paths}")
        source_path = paths[0]
        pointer = subprocess.check_output([
            "git", "-C", str(args.source_repo), "show", f"{REVISION}:{source_path}",
        ], text=True)
        digest = next(line.split("sha256:")[1] for line in pointer.splitlines()
                      if line.startswith("oid sha256:"))
        local = out / "source" / f"{name}.npy"
        local.parent.mkdir(exist_ok=True)
        if not local.exists():
            url = ("https://huggingface.co/datasets/fleaven/Retargeted_AMASS_for_robotics/"
                   f"resolve/{REVISION}/{quote(source_path, safe='/')}")
            with urlopen(url, timeout=60) as response, local.open("xb") as handle:
                shutil.copyfileobj(response, handle)
        require_hash(local, digest)
        values = np.load(local, allow_pickle=False)
        if values.ndim != 2 or values.shape[1] != 36 or not np.isfinite(values).all():
            raise ValueError(f"{name}: invalid source shape or values")
        csv_path = csv_dir / f"{name}.csv"
        if not csv_path.exists():
            np.savetxt(csv_path, values, delimiter=",", fmt="%.8f")
        source_records.append({"clip": name, "source": source_path,
                               "source_sha256": digest, "csv_sha256": sha256(csv_path)})
        print(f"SOURCE {name}", flush=True)
    # Three disposable conversions absorb the historical converter warm-up transient.
    first = csv_dir / f"{rows[0]['name']}.csv"
    for i in range(3):
        warm = csv_dir / f"000_warmup_{i}_120_jpos.csv"
        if not warm.exists():
            shutil.copyfile(first, warm)
    receipt = {"source_revision": REVISION, "manifest_sha256": sha256(MANIFEST),
               "classification": "local licensed-payload reconstruction; no policy outcome",
               "sources": source_records}
    (out / "source_receipt.json").write_text(json.dumps(receipt, indent=1) + "\n")
    if args.prepare_only:
        print(f"Prepared {len(rows)} hash-verified sources; no simulator started")
        return 0
    raw = out / f"raw_{args.device.replace(':', '_')}"
    subprocess.run([
        sys.executable, str(ROOT / "tools/build_motion_bank.py"),
        "--input-dir", str(csv_dir), "--output-dir", str(raw),
        "--input-fps", "120", "--infer-fps", "--device", args.device,
    ], check=True)
    subprocess.run([
        sys.executable, str(ROOT / "tools/ground_align_bank.py"), "--bank", str(raw),
    ], check=True)
    raw_checks = []
    for row in rows:
        path = raw / f"{row['name']}.npz"
        actual = sha256(path) if path.exists() else None
        raw_checks.append({"clip": row["name"], "expected": row["original"]["sha256"],
                           "actual": actual, "pass": actual == row["original"]["sha256"]})
    (out / f"raw_audit_{args.device.replace(':', '_')}.json").write_text(
        json.dumps({"device": args.device, "checks": raw_checks}, indent=1) + "\n"
    )
    if not all(row["pass"] for row in raw_checks):
        print(f"RAW historical hashes match: {sum(r['pass'] for r in raw_checks)}/{len(rows)}")
        return 2
    print(f"RAW {len(rows)}/{len(rows)} historical hashes match", flush=True)
    from dfrp_repair import repair_motion
    model = ROOT / manifest["inputs"]["model"]
    require_hash(model, manifest["inputs"]["model_sha256"])
    require_hash(ROOT / "tools/dfrp_repair.py", manifest["inputs"]["repair_tool_sha256"])
    repaired = out / "repaired"
    repaired.mkdir(exist_ok=True)
    for row in rows:
        source = raw / f"{row['name']}.npz"
        target = repaired / source.name
        if not target.exists():
            repair_motion(motion_path=source, model_path=model, output_path=target,
                          gap_m=0.06, clearance_m=0.003, smoothing_s=0.24,
                          repair_enabled=row["flagged"])
        require_hash(target, row["training_motion"]["sha256"])
        print(f"REPAIRED {row['name']}: historical hash matches", flush=True)
    (out / "clips.txt").write_text("".join(f"{r['name']}\n" for r in rows))
    receipt.update({"raw_verified": len(rows), "repaired_verified": len(rows),
                    "raw_bank": str(raw), "repaired_bank": str(repaired), "pass": True})
    (out / "recovery_result.json").write_text(json.dumps(receipt, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
