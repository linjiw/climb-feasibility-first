#!/usr/bin/env python3
"""Describe completed ALP histories without loading policy outcomes or a GPU."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import spearmanr
import torch

from check_relative_progress_probe import check_run, sha256
from climb.segment_curriculum import segment_sampling_probabilities

ROOT = Path(__file__).resolve().parents[1]


def correlation(left: np.ndarray, right: np.ndarray) -> float | None:
    if np.ptp(left) == 0 or np.ptp(right) == 0:
        return None
    return float(spearmanr(left, right).statistic)


def describe_history(history: np.ndarray, probabilities: np.ndarray, base: np.ndarray) -> dict:
    """Partition positive excess sampling by signed conditional-rate change."""
    if (history.ndim != 2 or history.shape[0] != 11 or history.shape[1] != len(base)
            or probabilities.shape != base.shape
            or not np.isfinite(history).all() or ((history < 0) | (history > 1)).any()
            or not np.isfinite(probabilities).all() or (probabilities < 0).any()
            or not np.isfinite(base).all() or (base < 0).any()
            or not np.isclose(base.sum(), 1) or not np.isclose(probabilities.sum(), 1)):
        raise ValueError("invalid complete-window sampler history")
    signed = history[-1] - history[0]
    progress = np.abs(signed)
    extra = np.maximum(probabilities - base, 0)
    extra_total = float(extra.sum())
    # The tolerance only classifies floating-point zero; no selection uses it.
    masks = {"improving": signed > 1e-12, "declining": signed < -1e-12,
             "unchanged": np.abs(signed) <= 1e-12}
    return {"progress_prior_weighted_mean": float(base @ progress),
            "positive_excess_mass": extra_total,
            **{f"excess_fraction_{name}": float(extra[mask].sum() / extra_total)
               if extra_total > 1e-12 else None for name, mask in masks.items()},
            **{f"unit_fraction_{name}": float(mask.mean()) for name, mask in masks.items()}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    saved = json.loads(args.result.read_text())
    if saved["stage"] != "long":
        raise ValueError("diagnostic requires a complete long result")
    parents = {Path(name).parent for name in saved["bindings"]}
    if len(parents) != 1:
        raise ValueError("ambiguous run")
    manifest = ROOT / "reports/g_segment/unit_table.json"
    if check_run(parents.pop(), manifest, seed=saved["seed"], stage="long") != saved:
        raise ValueError("complete result does not reproduce")
    units = json.loads(manifest.read_text())["admissible_units"]
    mass = np.array([unit["deployment_mass"] for unit in units], dtype=np.float32).astype(float)
    base = mass / mass.sum()
    clips = torch.tensor([unit["clip_id"] for unit in units], dtype=torch.long)
    previous = None
    rows = []
    paths = sorted(map(Path, saved["bindings"]), key=lambda path: int(path.name.split("_")[1]))
    for path in paths:
        ledger = json.loads(path.read_text())
        if ledger["iteration"] < 400:
            continue
        state_path = path.with_name(path.name.replace("_segment.json", "_segment_sampler.pt"))
        state = torch.load(state_path, map_location="cpu", weights_only=True)["sampler"]
        history = state["rate_history"].numpy()
        progress = np.abs(history[-1] - history[0])
        segment = ledger["segment"]
        if not np.array_equal(progress, np.array(segment["learning_progress"])):
            raise ValueError("reported progress disagrees with saved history")
        probabilities = np.array(segment["probabilities"])
        attempts = state["lifetime_attempts"].numpy()
        failure = 1 - history[-1]
        d = segment_sampling_probabilities(
            torch.tensor(failure), torch.ones(len(base), dtype=torch.float64),
            torch.tensor(mass), exploration_ratio=0.8, difficulty_power=1.0,
            clip_ids=clips, max_unit_probability=0.05, max_clip_probability=0.25,
        ).numpy()
        row = {"iteration": ledger["iteration"],
               **describe_history(history, probabilities, base),
               "rho_progress_failure": correlation(progress, failure),
               "rho_progress_previous_snapshot": None if previous is None else correlation(progress, previous[0]),
               "rho_progress_recent_attempt_count": None if previous is None else correlation(progress, attempts - previous[1]),
               "D_fixed_history_counterfactual_tv": float(np.abs(d - base).sum() / 2),
               "ledger_sha256": sha256(path), "state_sha256": sha256(state_path)}
        rows.append(row)
        previous = (progress, attempts)
    summary = {key: float(np.mean([row[key] for row in rows if row[key] is not None]))
               for key in ("excess_fraction_declining", "rho_progress_failure",
                           "rho_progress_previous_snapshot", "rho_progress_recent_attempt_count",
                           "D_fixed_history_counterfactual_tv")}
    output = {"schema_version": "relative_rank_diagnostic/1",
              "classification": "post-hoc exploratory sampler telemetry and fixed-history counterfactual",
              "seed": saved["seed"], "policy_endpoints_opened": False,
              "result_sha256": sha256(args.result), "tool_sha256": sha256(Path(__file__)),
              "rows": rows, "unweighted_snapshot_means": summary,
              "limitations": ["Snapshots and units are correlated; no p-values or independent-replication claim.",
                              "Declining estimates can reflect forgetting or estimation noise, not necessarily wasted practice.",
                              "Attempt-count correlation includes endogenous sampling exposure.",
                              "D counterfactual holds R's histories fixed; it is not a D training result.",
                              "No diagnostic changes R2 or the predeclared D profile."]}
    args.out_dir.mkdir(parents=True, exist_ok=False)
    (args.out_dir / "result.json").write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    with (args.out_dir / "snapshots.csv").open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.5), constrained_layout=True)
    for ax, key, label in zip(axes,
            ("progress_prior_weighted_mean", "excess_fraction_declining", "rho_progress_previous_snapshot"),
            ("Prior-weighted absolute progress", "Extra mass on declining estimates", "Rank correlation with prior snapshot")):
        ax.plot([row["iteration"] for row in rows], [row[key] for row in rows], marker=".")
        ax.set(xlabel="PPO iteration", ylabel=label)
        ax.grid(alpha=0.25)
    axes[0].set_yscale("log")
    axes[1].set_ylim(0, 1)
    axes[2].set_ylim(-1, 1)
    fig.suptitle("Seed 11 sampler diagnostic — exploratory; no policy-benefit test", fontsize=11)
    for suffix in ("png", "pdf"):
        fig.savefig(args.out_dir / f"rank_signal.{suffix}", dpi=180)
    plt.close(fig)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
