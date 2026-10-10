"""Figs 11 and 13 for the n = 10 per-policy VG-MM vs RANDOM comparison.

Seeds 11-13: prospective arms (ROUND2_FINAL_REPAIR/results/r2_arms; VG-MM seed 11
is the historical run in results/vgmm_result.json). Seeds 14-20: extension
(results/r2_arms_ext). Statistics are read from results/r2_ext_stats.json
(written by r2_ext_stats.py). Trajectories use the archived log-replay
reconstruction of r2_figures_FONTPATCH.py.
"""
import glob
import json
import os
import sys

import numpy as np
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

HERE = os.path.dirname(os.path.abspath(__file__))
Q1 = os.path.dirname(HERE)
R2 = os.path.join(Q1, "ROUND2_FINAL_REPAIR")
WS = os.path.dirname(Q1)
MSFIG = os.path.join(Q1, "MATERIALS_DESIGN_TRANSFER", "manuscript", "figures")
sys.path.insert(0, os.path.join(R2, "code"))
import r2_figures_FONTPATCH as rf  # noqa: E402  (trajectory reconstruction)

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["STIXGeneral", "DejaVu Serif"],
    "mathtext.fontset": "stix", "font.size": 9, "axes.labelsize": 9.5,
    "axes.titlesize": 10, "legend.fontsize": 8, "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5, "axes.linewidth": 0.9, "xtick.direction": "out",
    "ytick.direction": "out", "axes.grid": False, "figure.facecolor": "white",
    "savefig.facecolor": "white", "pdf.fonttype": 42, "ps.fonttype": 42,
    "legend.frameon": False})
C = {"vgmm": "#D55E00", "rand": "#0072B2", "det": "#009E73",
     "fullfe": "#555555", "demonly": "#CC79A7"}


def style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(length=3.2, width=0.8, pad=2.5)
    ax.yaxis.grid(True, ls=":", lw=0.55, color="0.75", zorder=0)
    ax.set_axisbelow(True)


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(MSFIG, f"{name}.{ext}"), dpi=300,
                    bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    print("wrote", name)


def load():
    arms = {}
    for f in glob.glob(os.path.join(R2, "results", "r2_arms", "arm_*.json")) + \
            glob.glob(os.path.join(R2, "results", "r2_arms_ext", "arm_*.json")):
        a = json.load(open(f))
        arms[a["arm"]] = a
    hist = json.load(open(os.path.join(rf.v2.WS, "results", "vgmm_result.json")))
    rep = json.load(open(os.path.join(R2, "results", "r2_pool_replay.json")))
    st = json.load(open(os.path.join(R2, "results", "r2_ext_stats.json")))
    return arms, hist, rep, st


def trajectories(arms, hist, pol):
    out = {}
    for s in range(11, 21):
        if pol == "vgmm" and s == 11:
            out[s] = rf.hist_traj(hist)
        else:
            out[s] = rf.best_so_far_traj(arms[f"{pol}{s}"])
    return out


def on_grid(tr, n=60):
    """Best-so-far value on unique-design counts 1..n (step-post)."""
    xs, ys = map(np.asarray, tr)
    g = np.arange(1, n + 1)
    idx = np.searchsorted(xs, g, side="right") - 1
    return g, np.where(idx >= 0, ys[np.clip(idx, 0, None)], 0.0)


def fig11(arms, hist, rep, st):
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(9.8, 3.9),
                                  gridspec_kw={"width_ratios": [1.45, 1.25]})
    style_ax(ax)
    style_ax(ax2)
    XMAX = 30
    cum = np.asarray(rep["best_so_far_trajectory"], float)
    ax.step(np.arange(1, len(cum) + 1), cum, where="post", color=C["fullfe"],
            lw=1.6, zorder=3)
    ff = rep["fullfe_truncated"]
    g26 = ff["best_gain_at_26_unique_pct"]
    ax.plot([26], [g26], "*", ms=10, color=C["fullfe"], zorder=6)
    gfull = 100 * (rf.arch_val(rep, "C1111_winner_search") / rf.UNI64 - 1)
    ax.axhline(gfull, color=C["fullfe"], lw=0.9, ls=(0, (5, 2)))
    ax.text(XMAX - 0.3, gfull + 0.12, f"full-FE optimum {gfull:+.2f}% (194 unique)",
            ha="right", va="bottom", fontsize=7.6, color=C["fullfe"])
    for pol in ("rand", "vgmm"):
        tr = trajectories(arms, hist, pol)
        grid = []
        for s, t in tr.items():
            ax.step(*t, where="post", color=C[pol], lw=0.75, alpha=0.38, zorder=2)
            grid.append(on_grid(t, 26)[1])
        g, med = np.arange(1, 27), np.median(grid, axis=0)
        ax.step(g, med, where="post", color=C[pol], lw=2.2, zorder=4)
    xs, ys = rf.best_so_far_traj(arms["det"])
    ax.step(xs, ys, where="post", color=C["det"], lw=1.5, ls=(0, (4, 1.6)), zorder=3)
    ax.axhline(0, color="0.35", lw=0.7, ls=":")
    ax.set_xlim(0, XMAX)
    ax.set_ylim(-0.3, 7.4)
    ax.set_xlabel("unique $64^3$ search-grid designs")
    ax.set_ylabel(r"FE-verified $C_{1111}$ gain vs uniform [%]")
    ax.set_title("(a)  verified gain vs budget", loc="left", fontsize=10, pad=6)
    h = [Line2D([], [], color=C["vgmm"], lw=2.2, label="VG-MM median"),
         Line2D([], [], color=C["vgmm"], lw=0.8, alpha=0.5, label="VG-MM seeds 11–20"),
         Line2D([], [], color=C["rand"], lw=2.2, label="RANDOM median"),
         Line2D([], [], color=C["rand"], lw=0.8, alpha=0.5, label="RANDOM seeds 11–20"),
         Line2D([], [], color=C["det"], lw=1.5, ls=(0, (4, 1.6)), label="DETERMINISTIC"),
         Line2D([], [], color=C["fullfe"], lw=1.6, marker="*", ms=8,
                label=f"full-FE search (@26: {g26:+.2f}%)")]
    ax.legend(handles=h, loc="upper center", bbox_to_anchor=(0.5, 1.30), ncol=3,
              fontsize=7.3, handlelength=1.8, columnspacing=0.9)

    # (b) endpoints, all policies
    rng = np.random.default_rng(3)
    groups = [("VG-MM\n$n=10$", "vgmm", "o"), ("RANDOM\n$n=10$", "rand", "s"),
              ("DET", "det", "^"), ("DEM-only\n$n=3$", "demonly", "D")]
    for gi, (lab, pol, mk) in enumerate(groups):
        if pol == "det":
            pts = [(arms["det"]["G26_pct"], arms["det"]["G_confirm96_pct"])]
        elif pol == "demonly":
            pts = [(arms[f"demonly{s}"]["G26_pct"], arms[f"demonly{s}"]["G_confirm96_pct"])
                   for s in (11, 12, 13)]
        else:
            pts = [tuple(v) for v in st["per_seed"][pol].values()]
        p = np.asarray(pts)
        for k, (dx, filled) in enumerate(((-0.17, True), (0.17, False))):
            x = gi + dx + rng.uniform(-0.06, 0.06, len(p))
            ax2.plot(x, p[:, k], mk, ls="none", ms=5.2, color=C[pol],
                     mfc=C[pol] if filled else "white", mec=C[pol] if not filled else "white",
                     mew=1.1 if not filled else 0.5, zorder=4, alpha=0.95)
            if len(p) >= 10:
                m = p[:, k].mean()
                ax2.plot([gi + dx - 0.13, gi + dx + 0.13], [m, m], color="k", lw=1.3, zorder=5)
    ax2.axhline(g26, color=C["fullfe"], lw=1.0, ls="--")
    ax2.text(3.55, g26 + 0.15, f"full-FE @26 unique\n({g26:+.2f}%)", ha="right",
             va="bottom", fontsize=7.4, color=C["fullfe"])
    ax2.axhline(0, color="0.35", lw=0.7, ls=":")
    ax2.set_xticks(range(len(groups)))
    ax2.set_xticklabels([g[0] for g in groups])
    ax2.set_xlim(-0.55, 3.6)
    ax2.set_ylabel("matched-budget gain $G_{26}$ [%]")
    ax2.set_title("(b)  26-call endpoints, all policies", loc="left", fontsize=10, pad=6)
    h2 = [Line2D([], [], marker="o", color="0.35", mfc="0.35", mec="white", ls="none",
                 ms=5.5, label="search $64^3$"),
          Line2D([], [], marker="o", color="0.35", mfc="white", mec="0.35", mew=1.1,
                 ls="none", ms=5.5, label="confirm $96^3$"),
          Line2D([], [], color="k", lw=1.3, label="mean")]
    ax2.legend(handles=h2, loc="lower left", fontsize=7.6, handlelength=1.4)
    fig.subplots_adjust(left=0.07, right=0.99, top=0.78, bottom=0.17, wspace=0.27)
    save(fig, "fig11_vgmm_budget")


def fig13(st):
    fig, axs = plt.subplots(1, 2, figsize=(9.6, 3.6), gridspec_kw={"width_ratios": [1.0, 1.15]})
    ax, ax2 = axs
    style_ax(ax)
    style_ax(ax2)
    grids = [("64^3 search", 0, "search $64^3$"), ("96^3 confirm", 1, "confirm $96^3$")]
    rng = np.random.default_rng(5)
    for gi, (key, k, lab) in enumerate(grids):
        s = st[key]
        for pi, (pol, mk) in enumerate((("vgmm", "o"), ("rand", "s"))):
            v = np.array([p[k] for p in st["per_seed"][pol].values()])
            x0 = gi * 2.6 + pi * 1.0
            bp = ax.boxplot(v, positions=[x0], widths=0.55, whis=(0, 100),
                            patch_artist=True, showfliers=False, zorder=2)
            for part in ("boxes",):
                for b in bp[part]:
                    b.set(facecolor=C[pol], alpha=0.16, edgecolor=C[pol], lw=0.9)
            for part in ("whiskers", "caps", "medians"):
                for b in bp[part]:
                    b.set(color=C[pol], lw=0.9)
            ax.plot(x0 + rng.uniform(-0.15, 0.15, len(v)), v, mk, ls="none", ms=4.6,
                    color=C[pol], mfc=C[pol] if k == 0 else "white", mec=C[pol] if k else "white",
                    mew=1.0 if k else 0.4, zorder=4)
        d, (lo, hi) = s["mean_diff"], s["boot95"]
        y = 7.35
        x0 = gi * 2.6
        ax.plot([x0, x0, x0 + 1, x0 + 1], [y - 0.12, y, y, y - 0.12], color="0.25", lw=0.8)
        ax.text(x0 + 0.5, y + 0.08,
                f"$\\Delta$ = {d:+.2f} pp [{lo:.2f}, {hi:.2f}]\n"
                f"MW $p$ = {s['mannwhitney_greater_p']:.3f}; spread $p$ = {s['levene_brown_forsythe_p']:.3f}",
                ha="center", va="bottom", fontsize=7.2)
    ax.set_xticks([0, 1, 2.6, 3.6])
    ax.set_xticklabels(["VG-MM", "RANDOM", "VG-MM", "RANDOM"])
    for gi, (_, _, lab) in enumerate(grids):
        ax.text(gi * 2.6 + 0.5, -0.11, lab, transform=ax.get_xaxis_transform(),
                ha="center", va="top", fontsize=8.8)
    ax.set_xlim(-0.6, 4.2)
    ax.set_ylim(1.8, 8.6)
    ax.set_ylabel("matched-budget gain $G_{26}$ [%]")
    ax.set_title("(a)  endpoint distributions, seeds 11–20", loc="left", fontsize=10, pad=6)

    # (b) ECDF at the confirmation grid: reliability vs lottery
    for pol, lab in (("vgmm", "VG-MM"), ("rand", "RANDOM")):
        for k, ls in ((0, (0, (3, 1.5))), (1, "-")):
            v = np.sort([p[k] for p in st["per_seed"][pol].values()])
            yy = np.arange(1, len(v) + 1) / len(v)
            ax2.step(np.r_[1.5, v], np.r_[0, yy], where="post", color=C[pol],
                     lw=1.8 if k else 1.0, ls=ls, alpha=1.0 if k else 0.7)
    ax2.axvline(st["96^3 confirm"]["vgmm"]["min"], color=C["vgmm"], lw=0.7, ls=":")
    f96 = st["96^3 confirm"]["frac_rand_below_min_vgmm"]
    f64 = st["64^3 search"]["frac_rand_below_min_vgmm"]
    ax2.text(st["96^3 confirm"]["vgmm"]["min"] - 0.08, 0.97,
             f"worst VG-MM run\n{f96*10:.0f}/10 RANDOM below ($96^3$)\n{f64*10:.0f}/10 below ($64^3$)",
             ha="right", va="top", fontsize=7.4, color="0.2")
    ax2.set_xlim(1.5, 7.2)
    ax2.set_ylim(0, 1.03)
    ax2.set_xlabel("matched-budget gain $G_{26}$ [%]")
    ax2.set_ylabel("fraction of runs $\\leq$ gain")
    ax2.set_title("(b)  empirical CDF of endpoints", loc="left", fontsize=10, pad=6)
    h = [Line2D([], [], color=C["vgmm"], lw=1.8, label="VG-MM"),
         Line2D([], [], color=C["rand"], lw=1.8, label="RANDOM"),
         Line2D([], [], color="0.3", lw=1.8, label="confirm $96^3$"),
         Line2D([], [], color="0.3", lw=1.0, ls=(0, (3, 1.5)), label="search $64^3$")]
    ax2.legend(handles=h, loc="lower right", fontsize=7.6)
    fig.subplots_adjust(left=0.07, right=0.99, top=0.88, bottom=0.18, wspace=0.26)
    save(fig, "fig13_policy_seeds")


if __name__ == "__main__":
    arms, hist, rep, st = load()
    fig11(arms, hist, rep, st)
    fig13(st)
