#!/usr/bin/env python3
"""Render every DFRP validation clip, without selecting successful examples."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42})


def render(result: dict, design: dict, out: Path, *, synthetic: bool = False) -> None:
    """Plot paired window-completion rates and common-reference TrackingScore."""
    records = sorted(design["clips"], key=lambda row: row["clip"])
    names = [row["clip"] for row in records]
    if set(names) != set(result["per_clip"]):
        raise ValueError("figure must contain every design clip exactly once")
    if len(names) != len(set(names)):
        raise ValueError("duplicate design clip")
    if not synthetic and result.get("status") != "measured":
        raise ValueError("figure requires measured validated results")
    fig, axes = plt.subplots(1, 2, figsize=(9.6, max(4.0, len(names) * 0.27 + 2.0)),
                             sharey=True, layout="constrained")
    y = np.arange(len(names))
    for axis, key, title in zip(
        axes, ("success", "tracking_score"),
        ("Window completion rate", "Common-raw-reference TrackingScore"),
    ):
        for i, row in enumerate(records):
            metrics = result["per_clip"][row["clip"]]["metrics"][key]
            raw, repaired = metrics["raw"], metrics["repaired"]
            axis.plot([raw, repaired], [i, i], color="#8c969c", linewidth=1.5)
            axis.scatter(raw, i, marker="o", s=28, color="#596875",
                         label="Raw reference" if i == 0 else None, zorder=3)
            axis.scatter(repaired, i, marker="D", s=28, color="#0b8296",
                         label="DFRP / unchanged control" if i == 0 else None, zorder=3)
        axis.set_xlim(-0.035, 1.035)
        axis.set_title(title, fontsize=11)
        axis.grid(axis="x", alpha=0.2)
        axis.set_axisbelow(True)
        axis.spines[["top", "right"]].set_visible(False)
    axes[0].set_yticks(y, [
        f"{i + 1:02d}  {'repair' if r['qualified_repair'] else 'control'}"
        f"{' *' if r['training_overlap'] else ''}"
        for i, r in enumerate(records)
    ], fontsize=8)
    axes[0].invert_yaxis()
    axes[1].legend(loc="lower right", fontsize=8)
    prefix = "SYNTHETIC CHECK — " if synthetic else "Exploratory, one fixed policy — "
    fig.suptitle(prefix + "raw vs. DFRP references", fontsize=12)
    fig.supxlabel("All sampled windows, including failures; horizons ≤3 s.  "
                  "* overlaps training. Clip identities: companion CSV.", fontsize=9)
    out.parent.mkdir(parents=True, exist_ok=True)
    for suffix in (".png", ".pdf", ".csv"):
        target = out.with_suffix(suffix)
        if target.exists():
            raise ValueError(f"refusing figure overwrite: {target}")
    fig.savefig(out.with_suffix(".png"), dpi=170)
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)
    with out.with_suffix(".csv").open("x", newline="") as handle:
        fields = ("row", "clip", "qualified_repair", "training_overlap", "conditions",
                  "raw_completion", "repaired_completion", "raw_score", "repaired_score")
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for i, row in enumerate(records):
            summary = result["per_clip"][row["clip"]]
            metrics = summary["metrics"]
            writer.writerow({
                "row": i + 1, "clip": row["clip"],
                "qualified_repair": row["qualified_repair"],
                "training_overlap": row["training_overlap"],
                "conditions": summary["conditions"],
                "raw_completion": metrics["success"]["raw"],
                "repaired_completion": metrics["success"]["repaired"],
                "raw_score": metrics["tracking_score"]["raw"],
                "repaired_score": metrics["tracking_score"]["repaired"],
            })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--design", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    if args.synthetic:
        design = {"clips": [
            {"clip": f"synthetic_{i:02}", "qualified_repair": i < 22,
             "training_overlap": i in (0, 22)} for i in range(26)
        ]}
        result = {"status": "synthetic", "per_clip": {
            row["clip"]: {"conditions": 28, "metrics": {
                key: {"raw": (i % 8) / 8,
                      "repaired": min(1.0, max(0.0, (i % 8) / 8 + (i % 3 - 1) * 0.15))}
                for key in ("success", "tracking_score")}}
            for i, row in enumerate(design["clips"])
        }}
    else:
        if args.result is None or args.design is None:
            parser.error("--result and --design required except with --synthetic")
        result = json.loads(args.result.read_text())
        design = json.loads(args.design.read_text())
        if hashlib.sha256(args.design.read_bytes()).hexdigest() != result["design_sha256"]:
            raise ValueError("result/design hash mismatch")
    render(result, design, args.out, synthetic=args.synthetic)


if __name__ == "__main__":
    main()
