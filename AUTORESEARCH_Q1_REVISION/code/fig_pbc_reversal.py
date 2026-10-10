"""Fig: KUBC vs periodic-BC gains of the five gyroid designs (body-fitted FE).

Reads research/n3/conforming/conf_summary.json (summarize_conf.py): cap-refined
meshes (N = 48, M = 96, TETRA10), same mesh for both boundary conditions, values
moved to V_f = 0.19328 with C ~ V_f^1.21.
"""
import json
import os

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
Q1 = os.path.dirname(HERE)
WS = os.path.dirname(Q1)
MSFIG = os.path.join(Q1, "MATERIALS_DESIGN_TRANSFER", "manuscript", "figures")
S = json.load(open(os.path.join(WS, "research", "n3", "conforming", "conf_summary.json")))

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["STIXGeneral", "DejaVu Serif"],
    "mathtext.fontset": "stix", "font.size": 9, "axes.labelsize": 9.5,
    "axes.titlesize": 10, "legend.fontsize": 8, "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5, "axes.linewidth": 0.9, "pdf.fonttype": 42,
    "ps.fonttype": 42, "legend.frameon": False, "savefig.facecolor": "white"})

D = [  # key, label, colour
    ("", "uniform", "#000000"),
    ("printable", "band-restricted", "#009E73"),
    ("vgmm", "VG-MM winner", "#D55E00"),
    ("fullfe", "full-FE winner", "#555555"),
    ("graded", "unconstrained", "#CC79A7"),
]


def vals(key):
    k = "N48_M96" + (f"_{key}" if key else "") + "_rc"
    kg = S["kubc_gain_pct"].get(k, 0.0)
    pg = S["pbc_gain_pct"].get(k, 0.0)
    ratio = S["pbc"][k]["C_stress"] / S["kubc"][k]["C"]
    return kg, pg, ratio


fig, (ax, ax2) = plt.subplots(1, 2, figsize=(9.0, 3.7), gridspec_kw={"width_ratios": [1.25, 1.0]})
for a in (ax, ax2):
    a.spines["top"].set_visible(False)
    a.spines["right"].set_visible(False)
    a.yaxis.grid(True, ls=":", lw=0.55, color="0.75")
    a.set_axisbelow(True)

def pct(v):
    return f"{v:+.1f}%".replace("-", "−")


for key, lab, col in D:
    kg, pg, _ = vals(key)
    ax.plot([0, 1], [kg, pg], "-o", color=col, lw=1.8, ms=5.5, mec="white", mew=0.6, zorder=3)
    dy = {"fullfe": 0.5, "vgmm": -0.5}.get(key, 0.0)
    ax.text(-0.05, kg + dy, f"{lab}  {pct(kg)}", ha="right", va="center", fontsize=7.8, color=col)
    ax.text(1.05, pg, pct(pg), ha="left", va="center", fontsize=7.8, color=col)
ax.set_xlim(-0.95, 1.35)
ax.set_xticks([0, 1])
ax.set_xticklabels(["KUBC\n(optimized and verified)", "periodic BC"])
ax.set_ylabel(r"$C_{1111}$ gain vs uniform at equal $V_f$ [%]")
ax.set_title("(a)  design gains under the two boundary conditions", loc="left", fontsize=10, pad=6)

xs = np.arange(len(D))
r = [vals(k)[2] for k, _, _ in D]
ax2.bar(xs, r, width=0.62, color=[c for _, _, c in D], alpha=0.85, edgecolor="white", zorder=3)
for x, v in zip(xs, r):
    ax2.text(x, v + 0.006, f"{v:.3f}", ha="center", va="bottom", fontsize=7.8)
ax2.set_ylim(0.7, 0.95)
ax2.set_xticks(xs)
ax2.set_xticklabels(["uniform", "band-\nrestricted", "VG-MM\nwinner", "full-FE\nwinner", "uncon-\nstrained"], fontsize=8)
ax2.set_ylabel(r"$C_{1111}^{\mathrm{PBC}}/C_{1111}^{\mathrm{KUBC}}$ (same mesh)")
ax2.set_title("(b)  stiffness lost to the KUBC constraint", loc="left", fontsize=10, pad=6)
fig.subplots_adjust(left=0.2, right=0.99, bottom=0.2, top=0.88, wspace=0.42)
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(MSFIG, f"fig_pbc_reversal.{ext}"), dpi=300, bbox_inches="tight", pad_inches=0.04)
print("wrote fig_pbc_reversal")
