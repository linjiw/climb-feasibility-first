#!/usr/bin/env python3
"""Compose the ICRA Figure 1 CLIMB system pipeline.

The diagram separates reference feasibility, bank-relative support, and
intrinsic motion demand before policy outcomes enter the allocator. Counts are
read from the frozen exact-support and DFRP artifacts rather than hand-entered.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper/figures/f1_feasibility_first"
DOCS_OUT = ROOT / "docs/assets/f1_feasibility_first.png"

RED = "#B3261E"
RED_FILL = "#F7DEDB"
TEAL = "#0B7285"
TEAL_FILL = "#D9EEF1"
BLUE = "#315A8C"
BLUE_FILL = "#E1EAF4"
GOLD = "#9A6700"
GOLD_FILL = "#F5EBCF"
INK = "#15222B"
GRAY = "#5C6B75"
LIGHT_GRAY = "#F1F3F4"
WHITE = "#FFFFFF"


def rounded_box(
    ax,
    xy: tuple[float, float],
    width: float,
    height: float,
    text: str,
    *,
    edge: str,
    face: str,
    fontsize: float = 9.0,
    linewidth: float = 1.25,
) -> None:
    """Draw one centered rounded box in axes coordinates."""
    patch = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.018,rounding_size=0.025",
        linewidth=linewidth,
        edgecolor=edge,
        facecolor=face,
        transform=ax.transAxes,
    )
    ax.add_patch(patch)
    ax.text(
        xy[0] + width / 2,
        xy[1] + height / 2,
        text,
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=fontsize,
        color=INK,
        linespacing=1.25,
    )


def arrow(
    ax,
    start: tuple[float, float],
    stop: tuple[float, float],
    *,
    color: str = GRAY,
    rad: float = 0.0,
    linewidth: float = 1.25,
) -> None:
    """Draw a directed connection in axes coordinates."""
    ax.add_patch(
        FancyArrowPatch(
            start,
            stop,
            arrowstyle="-|>",
            mutation_scale=10,
            linewidth=linewidth,
            color=color,
            connectionstyle=f"arc3,rad={rad}",
            transform=ax.transAxes,
        )
    )


def artifact_counts() -> tuple[int, int, int, int]:
    """Read exact-support and repair counts from their result artifacts."""
    units = json.loads((ROOT / "reports/g_segment/unit_table.json").read_text())
    repairs = json.loads(
        (ROOT / "reports/dfrp_v1_exact_panel/iter1/result.json").read_text()
    )
    return (
        int(repairs["counts"]["flagged_exact_ready"]),
        int(repairs["counts"]["flagged"]),
        int(units["counts"]["admissible_units"]),
        int(units["counts"]["legal_starts"]),
    )


def draw_factorization(ax) -> None:
    """Draw the three quantities that CLIMB keeps separate."""
    ax.text(
        0.015,
        0.915,
        "Tracking difficulty is a gated object",
        transform=ax.transAxes,
        fontsize=10.2,
        fontweight="bold",
        color=INK,
        va="center",
    )
    factor_y = 0.84
    box_w = 0.205
    rounded_box(
        ax,
        (0.30, factor_y),
        box_w,
        0.095,
        r"FEASIBILITY  $\mathcal{F}(r;M,E)$" "\nrobot + scene admissibility",
        edge=TEAL,
        face=TEAL_FILL,
        fontsize=8.2,
    )
    ax.text(
        0.518,
        factor_y + 0.048,
        r"$\times$",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=14,
    )
    rounded_box(
        ax,
        (0.535, factor_y),
        box_w,
        0.095,
        r"SUPPORT  $\mathcal{S}(r;\mathcal{B})$" "\nbank-relative representation",
        edge=BLUE,
        face=BLUE_FILL,
        fontsize=8.2,
    )
    ax.text(
        0.753,
        factor_y + 0.048,
        r"$\times$",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=14,
    )
    rounded_box(
        ax,
        (0.77, factor_y),
        box_w,
        0.095,
        r"INTRINSIC  $\mathcal{I}(r)$" "\nmotion demand",
        edge=GOLD,
        face=GOLD_FILL,
        fontsize=8.2,
    )


def draw_pipeline(ax) -> None:
    """Draw the screen--repair--allocate data-to-policy loop."""
    repaired, repair_total, units, starts = artifact_counts()
    y = 0.40
    height = 0.27

    rounded_box(
        ax,
        (0.02, y + 0.035),
        0.12,
        0.20,
        "ROBOT-SPACE\nMOTION STREAM\n\nrobot + scene model",
        edge=GRAY,
        face=LIGHT_GRAY,
        fontsize=8.3,
    )
    rounded_box(
        ax,
        (0.18, y),
        0.18,
        height,
        "1  ·  refeas SCREEN\n\ncontact-free inverse dynamics\n+ contact-capacity LP\n\nframe-level slack + cause",
        edge=TEAL,
        face=TEAL_FILL,
        fontsize=8.4,
    )
    rounded_box(
        ax,
        (0.40, y),
        0.20,
        height,
        "2  ·  DFRP ROUTE + REPAIR\n\nadmit supported intervals\nproject candidate contacts\nre-screen + fidelity gates\n\n"
        f"{repaired}/{repair_total} panel candidates qualify",
        edge=BLUE,
        face=BLUE_FILL,
        fontsize=8.25,
    )
    rounded_box(
        ax,
        (0.64, y),
        0.20,
        height,
        "3  ·  EXACT-SUPPORT ALP\n\nnon-wrapping legal starts\nhard gate: rejected mass = 0\nunit + clip concentration caps\n\n"
        f"{units:,} units · {starts:,} starts",
        edge=GOLD,
        face=GOLD_FILL,
        fontsize=8.25,
    )
    rounded_box(
        ax,
        (0.875, y + 0.035),
        0.105,
        0.20,
        "G1 TRACKING\nPOLICY\n\npaired held-out\nevaluation",
        edge=INK,
        face=WHITE,
        fontsize=8.3,
    )

    arrow(ax, (0.14, y + 0.135), (0.18, y + 0.135))
    arrow(ax, (0.36, y + 0.135), (0.40, y + 0.135))
    arrow(ax, (0.60, y + 0.135), (0.64, y + 0.135))
    arrow(ax, (0.84, y + 0.135), (0.875, y + 0.135))

    rounded_box(
        ax,
        (0.425, 0.18),
        0.15,
        0.095,
        "QUARANTINE\nresidual / excess distortion",
        edge=RED,
        face=RED_FILL,
        fontsize=7.9,
        linewidth=1.0,
    )
    arrow(ax, (0.50, y), (0.50, 0.275), color=RED, linewidth=1.0)

    arrow(
        ax,
        (0.94, y + 0.235),
        (0.74, y + height),
        color=TEAL,
        rad=0.42,
        linewidth=1.35,
    )
    ax.text(
        0.84,
        0.735,
        "policy outcomes update learning progress\nonly inside admitted support",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=8.0,
        color=TEAL,
    )

    ax.text(
        0.5,
        0.065,
        "Screening changes admission; DFRP recovers qualified data; ALP changes compute allocation. "
        "Each interface is measured separately.",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=8.5,
        color=INK,
    )


def main() -> None:
    """Render PNG and vector PDF outputs."""
    fig, ax = plt.subplots(figsize=(9.6, 3.45))
    ax.set_axis_off()
    draw_factorization(ax)
    draw_pipeline(ax)
    fig.suptitle(
        "CLIMB: close the reference–physics loop before allocating policy updates",
        fontsize=12.0,
        y=0.995,
        color=INK,
        fontweight="bold",
    )
    fig.subplots_adjust(left=0.015, right=0.985, bottom=0.02, top=0.92)
    for extension in ("png", "pdf"):
        metadata = {"CreationDate": None, "ModDate": None} if extension == "pdf" else None
        fig.savefig(
            OUT.with_suffix(f".{extension}"),
            dpi=180,
            bbox_inches="tight",
            metadata=metadata,
        )
    fig.savefig(DOCS_OUT, dpi=180, bbox_inches="tight")
    print(f"wrote {OUT}.png/.pdf and {DOCS_OUT}")


if __name__ == "__main__":
    main()
