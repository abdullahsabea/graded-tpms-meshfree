"""Shared publication style for the Q1 figure restyle.

Visual redesign only. No new analysis, no data invention.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
INSTRON = REPO / "validation" / "experimental_data"
TABLE8 = REPO / "validation" / "table8_results.json"

# Okabe–Ito, used consistently across the restyled set
C = {
    "fem": "#009E73",
    "dem": "#E69F00",
    "cond": "#0072B2",
    "graded": "#D55E00",
    "vgmm": "#D55E00",
    "rand": "#0072B2",
    "det": "#009E73",
    "fullfe": "#555555",
    "demonly": "#CC79A7",
    "uniform": "#0072B2",
    "primitive": "#E69F00",
    "gyroid": "#0072B2",
    "diamond": "#009E73",
}

RC = {
    "font.family": "serif",
    "font.serif": ["STIXGeneral", "DejaVu Serif", "Times New Roman"],
    "mathtext.fontset": "stix",
    "font.size": 8.5,
    "axes.labelsize": 9.0,
    "axes.titlesize": 9.5,
    "legend.fontsize": 7.5,
    "xtick.labelsize": 8.0,
    "ytick.labelsize": 8.0,
    "axes.linewidth": 0.8,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.major.width": 0.7,
    "ytick.major.width": 0.7,
    "xtick.major.size": 3.0,
    "ytick.major.size": 3.0,
    "axes.grid": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "savefig.edgecolor": "none",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
    "legend.frameon": False,
    "legend.handlelength": 1.6,
    "legend.handletextpad": 0.45,
    "legend.borderaxespad": 0.4,
    "axes.unicode_minus": False,
}


def apply_style():
    plt.rcParams.update(RC)


def style_ax(ax, ygrid=True):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(length=3.0, width=0.7, pad=2.2)
    if ygrid:
        ax.yaxis.grid(True, ls=":", lw=0.5, color="0.78", zorder=0)
        ax.set_axisbelow(True)


def panel_label(ax, text, x=-0.12, y=1.08):
    """Consistent (a)/(b)/(c) labels in axes coordinates, above the frame."""
    ax.text(
        x, y, text, transform=ax.transAxes, ha="left", va="bottom",
        fontsize=10, fontweight="bold", clip_on=False, zorder=20,
    )


def aligned_titles(fig, items, y, fontsize=9.5):
    """One-line panel headings on a shared horizontal baseline."""
    for ax, title in items:
        bbox = ax.get_position()
        fig.text(bbox.x0, y, title, ha="left", va="bottom",
                 fontsize=fontsize, fontweight="normal")


def save_figure(fig, outdir: Path, stem: str, dpi=400):
    outdir.mkdir(parents=True, exist_ok=True)
    png = outdir / f"{stem}.png"
    pdf = outdir / f"{stem}.pdf"
    svg = outdir / f"{stem}.svg"
    kw = dict(bbox_inches="tight", pad_inches=0.03, facecolor="white")
    fig.savefig(png, dpi=dpi, **kw)
    fig.savefig(pdf, **kw)
    fig.savefig(svg, **kw)
    plt.close(fig)
    print(f"wrote {png.name} / .pdf / .svg")
    return png, pdf


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_csv_xy(path: Path, xkey, ykey):
    rows = read_csv(path)
    xs = np.array([float(r[xkey]) for r in rows], dtype=float)
    ys = np.array([float(r[ykey]) for r in rows], dtype=float)
    return xs, ys
