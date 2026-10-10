"""House style for the v7 (SMO) figures: one font, one colour per design.

Every v7 figure imports this module so that a design has the same colour,
label and marker in every panel of the paper.
"""
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
Q1 = HERE.parent
ROOT = Q1.parent
FIGS = Q1 / "MATERIALS_DESIGN_TRANSFER" / "manuscript" / "figures"

# Springer two-column page: 84 mm column, 174 mm full width.
COL_W = 84 / 25.4
FULL_W = 174 / 25.4

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["STIXGeneral", "DejaVu Serif"],
    "mathtext.fontset": "stix", "font.size": 8, "axes.labelsize": 8,
    "axes.titlesize": 8.5, "legend.fontsize": 7, "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5, "axes.linewidth": 0.7, "xtick.major.width": 0.7,
    "ytick.major.width": 0.7, "xtick.major.size": 2.8, "ytick.major.size": 2.8,
    "legend.frameon": False, "figure.facecolor": "white", "savefig.facecolor": "white",
    "pdf.fonttype": 42, "ps.fonttype": 42, "axes.spines.top": False,
    "axes.spines.right": False,
})

# Okabe-Ito based; designs keep these colours in every figure.
DES = {
    "uniform":   dict(c="#000000", m="o", lab="Uniform $t=0.30$",            short="Uniform"),
    "band":      dict(c="#009E73", m="s", lab="Band-and-smoothness-restricted", short="Band-restricted"),
    "vgmm":      dict(c="#D55E00", m="^", lab="Filtered search, seed 11",    short="Filtered s11"),
    "fullfe":    dict(c="#0072B2", m="D", lab="FE coordinate search",        short="FE search"),
    "graded":    dict(c="#CC79A7", m="v", lab="Unconstrained score design",  short="Unconstrained"),
}
ORDER = ["uniform", "band", "vgmm", "fullfe", "graded"]
# search policies (not designs)
POL = {"filtered": "#D55E00", "random": "#7F7F7F", "det": "#E69F00"}


def grid_y(ax):
    ax.yaxis.grid(True, ls=":", lw=0.5, color="0.78", zorder=0)
    ax.set_axisbelow(True)


def save(fig, stem, png_dpi=400):
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / f"{stem}.pdf", bbox_inches="tight", pad_inches=0.02)
    fig.savefig(FIGS / f"{stem}.png", dpi=png_dpi, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print("wrote", stem)
