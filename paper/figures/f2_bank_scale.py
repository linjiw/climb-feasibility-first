#!/usr/bin/env python3
"""Render the ICRA bank-scale prevalence and implementation-agreement figure."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper/figures/f2_bank_scale"
DOCS_OUT = ROOT / "docs/assets/f2_bank_scale.png"

RED = "#B3261E"
TEAL = "#0B7285"
INK = "#15222B"
GRAY = "#5C6B75"
LIGHT_GRAY = "#DDE3E6"
AMBER = "#B7791F"


def read_rows(path: Path) -> list[dict[str, str]]:
    """Read a CSV as dictionaries."""
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def strict_count(path: Path) -> tuple[int, int]:
    """Return total clips and strict infeasible-fraction count."""
    rows = read_rows(path)
    return len(rows), sum(float(row["infeasible_frac"]) > 0.10 for row in rows)


def prevalence_panel(ax) -> None:
    """Panel a: separate denominators and measured strict-flag fractions."""
    primary_n, primary_flagged = strict_count(ROOT / "reports/feasibility_all/feasibility.csv")
    production_n, production_flagged = strict_count(
        ROOT / "reports/feasibility_sonic/hygiene_screen.csv"
    )
    totals = np.array([primary_n, production_n])
    flagged = np.array([primary_flagged, production_flagged])
    rates = 100.0 * flagged / totals
    y = np.array([1.0, 0.0])

    ax.barh(y, rates, color=RED, height=0.38, label="strict flagged")
    ax.barh(y, 100.0 - rates, left=rates, color=LIGHT_GRAY, height=0.38, label="not flagged")
    ax.set_yticks(
        y,
        ["AMASS → WBT → G1\nCLIMB, μ=0.6", "filtered BONES-SEED → G1\nindependent, μ=0.7"],
    )
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.65, 1.75)
    ax.set_xlabel("clips [%]", fontsize=8)
    ax.set_title("(a) Separate corpus/pipeline measurements", loc="left", fontsize=9, pad=7)
    ax.tick_params(axis="both", labelsize=7.2)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", color=LIGHT_GRAY, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    for yi, count, total, rate in zip(y, flagged, totals, rates, strict=True):
        rate_text = f"{rate:.1f}%" if rate >= 1.0 else f"{rate:.2f}%"
        ax.text(
            98.5,
            yi,
            f"{count:,}/{total:,}  ({rate_text})",
            ha="right",
            va="center",
            fontsize=7.4,
            color=INK,
        )
    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, -0.43),
        ncol=2,
        frameon=False,
        fontsize=7.2,
        handlelength=1.2,
        columnspacing=1.0,
    )
    ax.text(
        0.0,
        1.68,
        "Do not pool: corpus, filtering, robot file,\nfriction, and implementation differ.",
        fontsize=6.7,
        color=GRAY,
        va="top",
    )


def agreement_panel(ax) -> None:
    """Panel b: same-input score and decision agreement."""
    rows = read_rows(ROOT / "reports/feasibility_xcheck/agreement.csv")
    styles = {
        "AMASS-wbt-G1": (TEAL, "o", "AMASS panel"),
        "BONES-SEED": (AMBER, "s", "BONES-SEED panel"),
    }
    for bank, (color, marker, label) in styles.items():
        bank_rows = [row for row in rows if row["bank"] == bank]
        ax.scatter(
            [float(row["climb_infeasible_frac"]) for row in bank_rows],
            [float(row["sonic_infeasible_frac"]) for row in bank_rows],
            s=22,
            marker=marker,
            color=color,
            alpha=0.78,
            edgecolor="white",
            linewidth=0.35,
            label=label,
            zorder=3,
        )

    upper = 0.72
    ax.plot([0, upper], [0, upper], color=GRAY, linewidth=0.8, linestyle="--", zorder=1)
    ax.axvline(0.10, color=RED, linewidth=0.7, linestyle=":")
    ax.axhline(0.10, color=RED, linewidth=0.7, linestyle=":")

    disagreement = next(row for row in rows if row["flag_agree"] == "0")
    dx = float(disagreement["climb_infeasible_frac"])
    dy = float(disagreement["sonic_infeasible_frac"])
    ax.scatter([dx], [dy], s=54, facecolor="none", edgecolor=RED, linewidth=1.2, zorder=4)
    ax.annotate(
        "one threshold disagreement\nburpee: 0.019 vs 0.136",
        xy=(dx, dy),
        xytext=(0.23, 0.24),
        fontsize=7.0,
        color=INK,
        arrowprops={"arrowstyle": "-|>", "color": RED, "lw": 0.8},
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.88, "pad": 1.0},
    )
    ax.text(
        0.70,
        0.018,
        "39/40 agree · ρ=0.984 · κ=0.948",
        ha="right",
        va="bottom",
        fontsize=6.9,
        color=INK,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 1.0, "pad": 1.0},
    )
    ax.set_xlim(-0.018, upper)
    ax.set_ylim(-0.018, upper)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("CLIMB infeasible fraction", fontsize=8)
    ax.set_ylabel("independent infeasible fraction", fontsize=8)
    ax.set_title("(b) Same clips, two implementations (n=40)", loc="left", fontsize=9, pad=7)
    ax.tick_params(labelsize=7.2)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper left", frameon=False, fontsize=6.9, handletextpad=0.3)


def main() -> None:
    """Render paper and website outputs."""
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(7.1, 2.65),
        gridspec_kw={"width_ratios": [1.05, 1.0]},
    )
    prevalence_panel(axes[0])
    agreement_panel(axes[1])
    fig.tight_layout(w_pad=1.6)
    for extension in ("png", "pdf"):
        metadata = {"CreationDate": None, "ModDate": None} if extension == "pdf" else None
        fig.savefig(
            OUT.with_suffix(f".{extension}"),
            dpi=220,
            bbox_inches="tight",
            metadata=metadata,
        )
    fig.savefig(DOCS_OUT, dpi=220, bbox_inches="tight")
    print(f"wrote {OUT}.png/.pdf and {DOCS_OUT}")


if __name__ == "__main__":
    main()
