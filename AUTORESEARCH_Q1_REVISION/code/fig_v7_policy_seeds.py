"""v7 replacement for Fig. 13: filtered search vs random proposals under the
same finite-element acceptance rule, ten quadrature seeds.

Changes from the v6 figure: no p-values; seeds 11-13 (fixed before the runs)
are drawn apart from the exploratory extension 14-20; the effect estimate is
the mean difference with its bootstrap interval, labelled exploratory; axis
labels use the paper's terms."""
import json

import numpy as np
from matplotlib.lines import Line2D

import v7_style as S
import matplotlib.pyplot as plt

st = json.loads((S.Q1 / "ROUND2_FINAL_REPAIR" / "results" / "r2_ext_stats.json").read_text())
PROS = {11, 12, 13}
COL = {"vgmm": S.POL["filtered"], "rand": S.POL["random"]}
LAB = {"vgmm": "filtered search", "rand": "random proposals"}

fig, (ax, ax2) = plt.subplots(1, 2, figsize=(S.FULL_W, 2.55), gridspec_kw={"width_ratios": [1.0, 1.0]})
S.grid_y(ax)
grids = [("64^3 search", 0, "$64^3$ (search grid)"), ("96^3 confirm", 1, "$96^3$ (re-evaluation)")]
rng = np.random.default_rng(7)
for gi, (key, k, glab) in enumerate(grids):
    for pi, pol in enumerate(("vgmm", "rand")):
        x0 = gi * 2.7 + pi * 1.0
        seeds = sorted(int(s) for s in st["per_seed"][pol])
        v = np.array([st["per_seed"][pol][str(s)][k] for s in seeds])
        ax.hlines(v.mean(), x0 - 0.28, x0 + 0.28, color=COL[pol], lw=1.6, zorder=3)
        jit = rng.uniform(-0.16, 0.16, len(v))
        for s, vv, j in zip(seeds, v, jit):
            pro = s in PROS
            ax.plot(x0 + j, vv, "o", ms=4.4 if pro else 3.6, mfc=COL[pol] if pro else "white",
                    mec="black" if pro else COL[pol], mew=0.8, zorder=4)
    s = st[key]
    d, (lo, hi) = s["mean_diff"], s["boot95"]
    y, x0 = 7.25, gi * 2.7
    ax.plot([x0, x0, x0 + 1, x0 + 1], [y - 0.12, y, y, y - 0.12], color="0.3", lw=0.7)
    ax.text(x0 + 0.5, y + 0.06, f"mean difference ${d:+.2f}$ pp\nbootstrap 95%: [{lo:.2f}, {hi:.2f}]",
            ha="center", va="bottom", fontsize=6.8, linespacing=1.1)
    ax.text(x0 + 0.5, -0.17, glab, transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=7.5)
ax.set_xticks([0, 1, 2.7, 3.7])
ax.set_xticklabels(["filtered", "random", "filtered", "random"])
ax.set_xlim(-0.55, 4.25)
ax.set_ylim(0.2, 8.25)
ax.set_yticks(range(2, 9))
ax.set_ylabel("FE gain over uniform at end of search [%]")
ax.set_title("(a) exploratory ten-seed comparison (one trained network)", loc="left", pad=4)
h = [Line2D([], [], ls="none", marker="o", ms=4.4, mfc="0.5", mec="black", mew=0.8, label="seeds 11–13, fixed before the runs"),
     Line2D([], [], ls="none", marker="o", ms=3.6, mfc="white", mec="0.4", mew=0.8, label="seeds 14–20, exploratory extension"),
     Line2D([], [], color="0.3", lw=1.6, label="mean of ten seeds")]
ax.legend(handles=h, loc="lower left", fontsize=6.6, handletextpad=0.3, borderaxespad=0.2)

S.grid_y(ax2)
for pol in ("vgmm", "rand"):
    for k, ls, lw in ((0, (0, (3, 1.5)), 0.9), (1, "-", 1.6)):
        v = np.sort([p[k] for p in st["per_seed"][pol].values()])
        yy = np.arange(1, len(v) + 1) / len(v)
        ax2.step(np.r_[1.5, v], np.r_[0, yy], where="post", color=COL[pol], lw=lw, ls=ls)
vmin = st["96^3 confirm"]["vgmm"]["min"]
ax2.axvline(vmin, color=COL["vgmm"], lw=0.6, ls=":")
f96 = st["96^3 confirm"]["frac_rand_below_min_vgmm"]
ax2.text(vmin - 0.08, 0.97, f"lowest filtered endpoint\n({f96 * 10:.0f}/10 random endpoints below, $96^3$)",
         ha="right", va="top", fontsize=6.6, color="0.2")
ax2.set_xlim(1.5, 7.2)
ax2.set_ylim(0, 1.03)
ax2.set_xlabel("FE gain over uniform at end of search [%]")
ax2.set_ylabel("fraction of seeds $\\leq$ gain")
ax2.set_title("(b) empirical distribution of endpoints", loc="left", pad=4)
h2 = [Line2D([], [], color=COL["vgmm"], lw=1.6, label=LAB["vgmm"]),
      Line2D([], [], color=COL["rand"], lw=1.6, label=LAB["rand"]),
      Line2D([], [], color="0.3", lw=1.6, label="$96^3$"),
      Line2D([], [], color="0.3", lw=0.9, ls=(0, (3, 1.5)), label="$64^3$")]
ax2.legend(handles=h2, loc="lower right", fontsize=6.8)
fig.subplots_adjust(left=0.065, right=0.99, top=0.9, bottom=0.2, wspace=0.24)
S.save(fig, "fig_v7_policy_seeds")
