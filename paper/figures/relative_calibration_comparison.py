#!/usr/bin/env python3
"""Compare complete, replay-verified R and D allocation histories without outcomes."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from check_relative_progress_probe import check_run, sha256
from run_relative_failure_calibration import verify_calibration
from analyze_relative_cost import execution_cost


def read_result(path: Path, design_path: Path | None = None) -> dict:
    """Require full real verifiers and unique source/checkpoint bindings."""
    saved = json.loads(path.read_text())
    parents = {Path(name).parent for name in saved["bindings"]}
    if len(parents) != 1:
        raise ValueError("ambiguous training history")
    run = parents.pop()
    if saved["schema_version"] == "relative_progress_probe_result/1":
        arm = "R"
        if saved["stage"] != "long" or saved["seed"] not in (11, 12):
            raise ValueError("expected one of the complete planned R probes")
        result = check_run(run, ROOT / "reports/g_segment/unit_table.json", seed=saved["seed"], stage="long")
        log = path.parent / "long.log"
    elif saved["schema_version"] == "relative_failure_calibration/1":
        arm = "D"
        if design_path is None or saved["seed"] not in (31, 32):
            raise ValueError("D requires its fixed execution design and assigned seed")
        design = json.loads(design_path.read_text())
        result = verify_calibration(run, saved["seed"], design["sources"])
        log = path.parent / f"seed{saved['seed']}.log"
    else:
        raise ValueError("unsupported allocation result schema")
    if result != saved:
        raise ValueError("complete result does not reproduce")
    post = [row for row in saved["snapshots"] if row["iteration"] >= 400]
    return {"arm": arm, "seed": saved["seed"], "status": saved["status"],
            "decision": {"path": str(path.resolve()), "sha256": sha256(path)},
            "execution_design": None if design_path is None else {"path": str(design_path.resolve()), "sha256": sha256(design_path)},
            "snapshots": saved["snapshots"], "post_warmup_snapshots": len(post),
            "mean_tv": saved["gate"]["mean_tv"],
            "tv_range": [min(row["tv"] for row in post), max(row["tv"] for row in post)],
            "minimum_effective_units": min(row["effective_units"] for row in post),
            "maximum_unit_mass": max(row["top1_unit_mass"] for row in post),
            "maximum_clip_mass": max(row["max_clip_mass"] for row in post),
            "final_saturation": saved["snapshots"][-1]["saturation"],
            "completed_trials": saved["snapshots"][-1]["completed_trials"],
            "execution_log": {"path": str(log.resolve()), "sha256": sha256(log)},
            "execution_cost": execution_cost(log.read_text())}


def generate(results: list[dict], out: Path) -> dict:
    """Plot all supplied complete runs, explicitly preserving unequal replication."""
    identities = [(row["arm"], row["seed"]) for row in results]
    if not identities or len(set(identities)) != len(identities):
        raise ValueError("empty or duplicate arm/seed histories")
    out.mkdir(parents=True, exist_ok=False)
    report = {"classification": "measured exploratory allocation; not policy utility or a paired method comparison",
              "runs": results, "policy_endpoints_opened": False,
              "limitations": ["Only supplied completed runs; any unfinished assigned replication stays pending.",
                              "Different development seeds; no paired policy contrast or method-level uncertainty estimate.",
                              "Similar TV does not mean similar allocation, useful progress ranks, or equal startup behavior.",
                              "D has no 0.15 upper mean-TV gate; do not impose the R upper gate on D.",
                              "Cost is elapsed shared-device training time only; excludes smokes, waiting, evaluation and engineering."],
              "plotter_sha256": sha256(Path(__file__))}
    with (out / "result.json").open("x") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    rows = [{"arm": run["arm"], "seed": run["seed"], **row} for run in results for row in run["snapshots"]]
    with (out / "snapshots.csv").open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.7), constrained_layout=True)
    for run in results:
        rows = run["snapshots"]
        label = f"{run['arm']} seed {run['seed']} ({run['status'].removesuffix('_pass')})"
        for ax, metric in zip(axes, ("tv", "effective_units", "saturation")):
            ax.plot([row["iteration"] for row in rows], [row[metric] for row in rows], label=label, lw=1.6)
    axes[0].axhline(0.05, color="gray", ls="--", lw=1, label="Minimum post-warm-up mean TV")
    axes[2].axhline(0.9, color="gray", ls="--", lw=1, label="Final saturation limit")
    axes[0].set(ylabel="TV from deployment prior", ylim=(0, 0.16))
    axes[1].set(ylabel="Entropy-effective units")
    axes[2].set(ylabel="Saturated unit fraction", ylim=(0, 1))
    for ax in axes:
        ax.axvline(400, color="gray", ls=":", lw=1)
        ax.set(xlabel="PPO iteration")
        ax.grid(alpha=0.2)
    axes[0].legend(fontsize=7)
    fig.suptitle("Verified development allocation histories — unequal replication; no policy comparison", fontsize=11)
    for suffix in ("png", "pdf"):
        fig.savefig(out / f"allocation_comparison.{suffix}", dpi=180)
    plt.close(fig)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--relative-results", type=Path, nargs="+", required=True)
    parser.add_argument("--failure-results", type=Path, nargs="+", required=True)
    parser.add_argument("--failure-design", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    runs = [read_result(path) for path in args.relative_results]
    runs += [read_result(path, args.failure_design) for path in args.failure_results]
    generate(runs, args.out_dir.resolve())
    print(json.dumps([{key: row[key] for key in ("arm", "seed", "status", "mean_tv", "minimum_effective_units",
                      "final_saturation", "completed_trials")} for row in runs], indent=2))
