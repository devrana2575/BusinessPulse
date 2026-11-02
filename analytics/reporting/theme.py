"""Shared visual style for BusinessPulse charts."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PALETTE = {
    "navy": "#1F3A5F",
    "teal": "#2A9D8F",
    "amber": "#E9C46A",
    "coral": "#E76F51",
    "slate": "#6C757D",
    "light": "#EEF3F7",
    "green": "#4C956C",
    "red": "#C8553D",
}
SERIES = [
    PALETTE["navy"],
    PALETTE["teal"],
    PALETTE["amber"],
    PALETTE["coral"],
    PALETTE["green"],
    PALETTE["slate"],
]


def apply_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#D9E2EC",
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": "#E6EDF3",
            "grid.linewidth": 0.8,
            "axes.titleweight": "bold",
            "axes.titlesize": 13,
            "axes.titlecolor": PALETTE["navy"],
            "axes.labelsize": 10,
            "axes.labelcolor": "#34495E",
            "xtick.color": "#34495E",
            "ytick.color": "#34495E",
            "font.size": 9,
            "legend.frameon": False,
            "figure.dpi": 110,
        }
    )


def save_figure(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
