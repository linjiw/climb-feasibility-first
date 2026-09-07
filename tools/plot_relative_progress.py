#!/usr/bin/env python3
"""Plot every verified long-run manipulation snapshot; never policy outcomes."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from check_relative_progress_probe import check_run, sha256

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, nargs="+", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    results = []
    for path in args.results:
        saved = json.loads(path.read_text())
        if saved["stage"] != "long":
            raise ValueError("figure requires a complete long run")
        parents = {Path(name).parent for name in saved["bindings"]}
        if len(parents) != 1:
            raise ValueError("ambiguous run directory")
        reproduced = check_run(parents.pop(), ROOT / "reports/g_segment/unit_table.json",
                               seed=saved["seed"], stage="long")
        if reproduced != saved:
            raise ValueError("result did not reproduce")
        results.append(saved)
    if len({result["seed"] for result in results}) != len(results):
        raise ValueError("duplicate seed")
    args.out_dir.mkdir(parents=True, exist_ok=False)
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6), constrained_layout=True)
    axes[0].axhspan(0.05, 0.15, color="#d8eeda", alpha=0.7,
                    label="Required band for run mean")
    metrics = ("tv", "effective_units", "saturation")
    labels = ("TV from deployment prior", "Entropy-effective units", "Saturated unit fraction")
    rows = []
    for result in results:
        data = result["snapshots"]
        label = f"Seed {result['seed']} ({result['status'].replace('manipulation_', '')})"
        for ax, metric in zip(axes, metrics):
            ax.plot([row["iteration"] for row in data], [row[metric] for row in data],
                    marker=".", markersize=4, label=label)
        rows.extend({"seed": result["seed"], **row} for row in data)
    axes[1].axhline(12, color="grey", linestyle="--", linewidth=1)
    axes[2].axhline(0.9, color="grey", linestyle="--", linewidth=1)
    for ax, label in zip(axes, labels):
        ax.axvline(400, color="grey", linestyle=":", linewidth=1)
        ax.set(xlabel="PPO iteration", ylabel=label)
        ax.grid(alpha=0.2)
    axes[0].legend(fontsize=7)
    axes[2].set_ylim(0, 1)
    fig.suptitle("Relative-progress allocation: exploratory simulation, no policy-benefit test", fontsize=11)
    for suffix in ("png", "pdf"):
        fig.savefig(args.out_dir / f"allocation.{suffix}", dpi=180)
    plt.close(fig)
    with (args.out_dir / "snapshots.csv").open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (args.out_dir / "provenance.json").open("x") as handle:
        json.dump({"classification": "measured exploratory manipulation",
                   "results": {str(path): sha256(path) for path in args.results},
                   "plotter_sha256": sha256(Path(__file__)),
                   "note": "TV band constrains the post-warm-up mean; saturation threshold applies at final iteration."},
                  handle, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    main()
