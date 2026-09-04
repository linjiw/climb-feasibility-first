#!/usr/bin/env python3
"""Compose the ICRA Figure 1 problem/mechanism contrast.

Panel (a) is an interpretation diagram grounded in the three-seed campaign.
Panel (b) is measured from ``reports/N1_clip44_knee_id.json``.
Panel (c) is a schematic of the frozen Phase-G exact-support contract; it is
explicitly not a policy result.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper/figures/f1_feasibility_first"

RED = "#B3261E"
RED_FILL = "#F7DEDB"
TEAL = "#0B7285"
TEAL_FILL = "#D9EEF1"
INK = "#15222B"
GRAY = "#5C6B75"
LIGHT_GRAY = "#E8ECEF"


def rounded_box(ax, xy, width, height, text, *, edge, face, fontsize=8.2) -> None:
    """Draw one centered rounded box in axes coordinates."""
    box = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.025,rounding_size=0.03",
        linewidth=1.3,
        edgecolor=edge,
        facecolor=face,
        transform=ax.transAxes,
    )
    ax.add_patch(box)
    ax.text(
        xy[0] + width / 2,
        xy[1] + height / 2,
        text,
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=fontsize,
        color=INK,
    )


def arrow(ax, start, stop, *, color=GRAY, rad=0.0) -> None:
    """Draw an arrow between axes-coordinate points."""
    ax.add_patch(
        FancyArrowPatch(
            start,
            stop,
            arrowstyle="-|>",
            mutation_scale=10,
            linewidth=1.2,
            color=color,
            connectionstyle=f"arc3,rad={rad}",
            transform=ax.transAxes,
        )
    )


def campaign_summary() -> tuple[int, float, float]:
    """Return the repeated-attractor seed count and campaign peak range."""
    dose = json.loads((ROOT / "reports/A5_coverage_dose.json").read_text())
    attractor = json.loads((ROOT / "reports/A7_attractor.json").read_text())["arms"]["adaptive"]
    per_seed = attractor["per_seed"]
    if not attractor["same_clip_across_seeds"]:
        raise ValueError("Figure 1 requires the recorded shared adaptive attractor")
    peaks = [float(row["max_top1"]) for row in dose["runs"] if row["arm"] == "adaptive"]
    if len(peaks) != len(per_seed):
        raise ValueError("Adaptive campaign and attractor seed counts disagree")
    return len(per_seed), min(peaks), max(peaks)


def failure_loop(ax) -> None:
    """Panel a: policy error feeds exposure without a feasibility check."""
    n_seeds, peak_min, peak_max = campaign_summary()
    ax.set_axis_off()
    rounded_box(
        ax,
        (0.04, 0.58),
        0.35,
        0.18,
        "retargeted\nreference defect",
        edge=RED,
        face=RED_FILL,
    )
    rounded_box(
        ax,
        (0.60, 0.58),
        0.35,
        0.18,
        "persistent\npolicy failure",
        edge=GRAY,
        face=LIGHT_GRAY,
    )
    rounded_box(
        ax,
        (0.32, 0.20),
        0.36,
        0.18,
        "sampler assigns\nmore exposure",
        edge=RED,
        face=RED_FILL,
    )
    arrow(ax, (0.39, 0.67), (0.60, 0.67))
    arrow(ax, (0.76, 0.58), (0.62, 0.38), color=RED)
    arrow(ax, (0.34, 0.29), (0.18, 0.58), color=RED)
    ax.text(
        0.5,
        0.04,
        f"Observed in {n_seeds}/{n_seeds} seeds: the same attractor recurs.\n"
        f"Campaign peak top-1 mass: {peak_min:.2f}–{peak_max:.2f}.",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=7.5,
        color=INK,
    )
    ax.set_title("(a) Failure is not always learning value", loc="left", fontsize=10, pad=9)


def unsupported_trace(ax) -> None:
    """Panel b: measured unsupported force for the shared attractor."""
    payload = json.loads((ROOT / "reports/N1_clip44_knee_id.json").read_text())
    frames = payload["frames"]
    time = np.array([float(row["t"]) for row in frames])
    no_contact = np.array([int(row["n_contacts"]) == 0 for row in frames])
    unsupported = np.array(
        [
            float(row["real"]["tl_unsupported_force_N"])
            if row["real"]["tl_unsupported_force_N"] is not None
            else (
                float(row["real"]["unsupported_force_N"])
                if int(row["n_contacts"]) == 0
                else 0.0
            )
            for row in frames
        ]
    )
    weight = float(payload["total_mass_kg"]) * 9.81
    descent = (time >= 0.75) & (time <= 1.75) & no_contact
    descent_median = float(np.median(unsupported[descent]))

    ax.fill_between(time, unsupported, color=RED, alpha=0.23, step="mid")
    ax.plot(time, unsupported, color=RED, linewidth=1.25)
    ax.fill_between(
        time,
        0,
        390,
        where=no_contact & (unsupported > 0.5 * weight),
        color=RED,
        alpha=0.09,
        step="mid",
    )
    ax.axhline(weight, color=GRAY, linestyle="--", linewidth=1.0)
    ax.text(9.75, weight + 9, f"robot weight {weight:.0f} N", ha="right", fontsize=7.3, color=GRAY)
    ax.annotate(
        f"0.75–1.75 s: no admissible contact\nmedian unsupported ≈{descent_median:.0f} N",
        xy=(1.27, 322),
        xytext=(3.1, 345),
        fontsize=7.4,
        color=INK,
        arrowprops={"arrowstyle": "-|>", "color": RED, "lw": 1.0},
    )
    ax.set_xlim(0, 9.9)
    ax.set_ylim(0, 390)
    ax.set_xlabel("reference time [s]", fontsize=8.5)
    ax.set_ylabel("unsupported force [N]", fontsize=8.5)
    ax.tick_params(labelsize=7.5)
    ax.set_title("(b) Audit the final robot-space trajectory", loc="left", fontsize=10, pad=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def support_contract(ax) -> None:
    """Panel c: same support, only allocation varies."""
    unit_table = json.loads((ROOT / "reports/g_segment/unit_table.json").read_text())
    n_units = int(unit_table["counts"]["admissible_units"])
    n_starts = int(unit_table["counts"]["legal_starts"])
    ax.set_axis_off()
    ax.set_title("(c) Hold support exact; test allocation only", loc="left", fontsize=10, pad=9)

    feasible = [(0.03, 0.24), (0.36, 0.30), (0.76, 0.20)]
    rejected = [(0.27, 0.08), (0.67, 0.08)]
    timeline_y = 0.76
    ax.text(0.0, timeline_y + 0.08, "screened reference", transform=ax.transAxes, fontsize=7.5)
    for start, width in feasible:
        ax.add_patch(
            Rectangle(
                (start, timeline_y),
                width,
                0.06,
                transform=ax.transAxes,
                facecolor=TEAL,
                edgecolor="none",
            )
        )
    for start, width in rejected:
        ax.add_patch(
            Rectangle(
                (start, timeline_y),
                width,
                0.06,
                transform=ax.transAxes,
                facecolor=RED,
                edgecolor="none",
                hatch="////",
            )
        )
    ax.text(0.03, timeline_y - 0.06, "feasible intervals", transform=ax.transAxes, fontsize=7.0, color=TEAL)
    ax.text(0.62, timeline_y - 0.06, "excluded", transform=ax.transAxes, fontsize=7.0, color=RED)

    unit_x = np.array([0.08, 0.22, 0.43, 0.58, 0.80, 0.91])
    control = np.array([0.55, 0.48, 0.70, 0.62, 0.50, 0.66])
    treatment = np.array([0.30, 0.72, 0.42, 0.82, 0.52, 0.58])
    bar_w = 0.035
    base_y = 0.28
    scale = 0.24
    for x, height in zip(unit_x, control, strict=True):
        ax.add_patch(
            Rectangle(
                (x - bar_w, base_y),
                bar_w,
                height * scale,
                transform=ax.transAxes,
                facecolor=GRAY,
                edgecolor="none",
            )
        )
    for x, height in zip(unit_x, treatment, strict=True):
        ax.add_patch(
            Rectangle(
                (x, base_y),
                bar_w,
                height * scale,
                transform=ax.transAxes,
                facecolor=TEAL,
                edgecolor="none",
            )
        )
    ax.plot([0.03, 0.97], [base_y, base_y], transform=ax.transAxes, color=INK, linewidth=0.8)
    ax.text(0.03, base_y + 0.22, "allocation over identical units", transform=ax.transAxes, fontsize=7.5)
    legend_y = 0.15
    ax.add_patch(Rectangle((0.10, legend_y), 0.035, 0.035, transform=ax.transAxes, facecolor=GRAY))
    ax.text(0.145, legend_y + 0.017, "G1 uniform", transform=ax.transAxes, fontsize=7.1, va="center")
    ax.add_patch(Rectangle((0.52, legend_y), 0.035, 0.035, transform=ax.transAxes, facecolor=TEAL))
    ax.text(0.565, legend_y + 0.017, "G2 calibrated ALP", transform=ax.transAxes, fontsize=7.1, va="center")
    ax.add_patch(
        FancyBboxPatch(
            (0.0, 0.0),
            1.0,
            0.10,
            boxstyle="round,pad=0.004,rounding_size=0.01",
            linewidth=0.9,
            edgecolor=TEAL,
            facecolor=TEAL_FILL,
            transform=ax.transAxes,
            clip_on=False,
        )
    )
    ax.text(
        0.5,
        0.063,
        f"Same {n_units:,} units · {n_starts:,} legal starts · hashes · PPO · compute",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=6.8,
        color=INK,
    )
    ax.text(
        0.5,
        0.025,
        "Policy outcome pending",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=7.1,
        color=INK,
    )


def main() -> None:
    """Render PNG and vector PDF outputs."""
    fig, axes = plt.subplots(1, 3, figsize=(11.2, 3.45), gridspec_kw={"width_ratios": [1.0, 1.3, 1.1]})
    failure_loop(axes[0])
    unsupported_trace(axes[1])
    support_contract(axes[2])
    fig.suptitle(
        "Feasibility first: separate reference defects from allocation effects",
        fontsize=11.5,
        y=1.01,
        color=INK,
    )
    fig.tight_layout(w_pad=2.0)
    for extension in ("png", "pdf"):
        fig.savefig(OUT.with_suffix(f".{extension}"), dpi=180, bbox_inches="tight")
    print(f"wrote {OUT}.png/.pdf")


if __name__ == "__main__":
    main()
