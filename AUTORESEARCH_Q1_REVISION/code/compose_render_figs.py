"""Compose manuscript Figs. 1, 6 and 7 from the render3d.py images (house serif style)."""
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
N3 = ROOT / "research" / "n3"
REN = HERE.parent / "_deep_review" / "render3d"
FIGS = HERE.parent / "MATERIALS_DESIGN_TRANSFER" / "manuscript" / "figures"
sys.path.insert(0, str(HERE))
from render3d import MODES  # noqa: E402

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["STIXGeneral", "DejaVu Serif"],
    "mathtext.fontset": "stix", "font.size": 9, "axes.labelsize": 9,
    "axes.titlesize": 9.5, "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
    "legend.fontsize": 8, "axes.linewidth": 0.8, "savefig.dpi": 450,
})
W = 6.3


def img(name):
    return np.asarray(Image.open(REN / f"{name}.png").convert("RGB"))


def show(ax, name, title):
    ax.imshow(img(name), interpolation="lanczos")
    ax.set_axis_off()
    ax.set_title(title, fontsize=9.5, pad=4)


def save(fig, stem):
    fig.savefig(FIGS / f"{stem}.png", bbox_inches="tight", pad_inches=0.03, facecolor="white")
    fig.savefig(REN / f"{stem}_preview.png", dpi=150, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    print("wrote", stem)


def fig1():
    fig, axs = plt.subplots(1, 3, figsize=(W, 2.35))
    for ax, (name, t) in zip(axs, [("gyroid", "0.3000"), ("primitive", "0.3387"), ("diamond", "0.2360")]):
        show(ax, f"fam_{name}", f"({'abc'[list(axs).index(ax)]}) {name.capitalize()}, $t={t}$")
    fig.subplots_adjust(wspace=0.04, left=0, right=1, top=0.9, bottom=0)
    save(fig, "fig1_tpms_families")


def fig7():
    meta = json.loads((REN / "render_meta.json").read_text())
    fig = plt.figure(figsize=(W, 3.55))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 0.045], hspace=0.12, wspace=0.04)
    show(fig.add_subplot(gs[0, 0]), "sed_uniform", r"(a) uniform $t=0.30$ (baseline)")
    show(fig.add_subplot(gs[0, 1]), "sed_graded", r"(b) optimized graded (FE: $-4.4\%$)")
    cax = fig.add_subplot(gs[1, :])
    pos = cax.get_position()
    cax.set_position([pos.x0 + 0.22 * pos.width, pos.y0, 0.56 * pos.width, pos.height])
    cb = fig.colorbar(ScalarMappable(Normalize(0, meta["sed_vmax"]), cmap="magma"),
                      cax=cax, orientation="horizontal")
    cb.set_label(r"FE strain-energy density at unit applied strain ($E=1$)", fontsize=8.5)
    cb.ax.tick_params(labelsize=8, length=2.5)
    cb.outline.set_linewidth(0.6)
    save(fig, "fig8_stress_contours")


def fig6():
    pn = json.loads((N3 / "paper_numbers.json").read_text())
    cs = json.loads((N3 / "e3_coord_search.json").read_text())
    theta, mid = np.array(cs["theta"]), cs["t0shift"]
    e3 = pn["e3"]

    def t_of(x, y, z):
        v = 0.30 + mid
        for i, (a, b, c) in enumerate(MODES):
            ph = 2 * np.pi * (a * x + b * y + c * z)
            v = v + theta[2 * i] * np.cos(ph) + theta[2 * i + 1] * np.sin(ph)
        return np.clip(v, 0.12, 0.55)

    H = 2.7
    fig = plt.figure(figsize=(W, H))
    sq_w, sq_h = 1.02 / W, 1.02 / H
    y0 = 0.28
    im = None
    for j, z0 in enumerate((0.25, 0.5)):
        ax = fig.add_axes([0.005 + j * (sq_w + 0.012), y0, sq_w, sq_h])
        im = ax.pcolormesh(cc_t := (np.arange(240) + 0.5) / 240, cc_t,
                           t_of(*np.meshgrid(cc_t, cc_t, indexing="ij"), z0).T, cmap="viridis",
                           vmin=0.12, vmax=0.55, shading="auto", rasterized=True)
        ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_linewidth(0.5); sp.set_color("0.4")
        ax.text(0.05, 0.95, f"$z={z0}$", transform=ax.transAxes, ha="left", va="top",
                fontsize=7.5, color="white")
        if j == 0:
            pass
    cax = fig.add_axes([0.005 + 2 * (sq_w + 0.012), y0, 0.013, sq_h])
    cb = fig.colorbar(im, cax=cax, ticks=[0.2, 0.3, 0.4, 0.5])
    cb.set_label("$t$", fontsize=8.5, labelpad=1)
    cb.ax.tick_params(labelsize=7.5, length=2); cb.outline.set_linewidth(0.5)

    axb = fig.add_axes([0.41, 0.03, 0.25, 0.84]); axb.set_zorder(-1)
    show(axb, "graded_thickness", "")

    ax = fig.add_axes([0.755, 0.22, 0.16, 0.64])
    designs = [("uniform", "uniform", "0.35", "o"), ("graded", "unconstr.", "#D55E00", "D"),
               ("printable", "constr.", "#CC79A7", "s")]
    for key, lab, col, mk in designs:
        dem = e3[key]["dem"]["C1111"]; fem = e3[key]["stats"]["mean"]; err = e3[key]["stats"]["half_range"]
        ax.plot([0, 1], [dem, fem], "-", color=col, lw=1.4, zorder=2)
        ax.plot(0, dem, mk, color=col, ms=5.5, mec="white", mew=0.6, zorder=3)
        ax.errorbar(1, fem, yerr=err, fmt=mk, color=col, ms=5.5, mec="white", mew=0.6,
                    elinewidth=0.9, capsize=2, zorder=3)
        if key != "uniform":
            ax.annotate(f"{e3[key]['dem_gain_pct']:+.1f}%", (0, dem), xytext=(-5, 0),
                        textcoords="offset points", ha="right", va="center", fontsize=7.5, color=col)
        g = "" if key == "uniform" else "\n" + f"{e3[key]['gain_mean_pct']:+.1f}%"
        dy = {"uniform": 0.0, "graded": -5, "printable": 6}[key]
        ax.annotate(f"{lab}{g}", (1, fem), xytext=(6, dy), textcoords="offset points",
                    ha="left", va="center", fontsize=7.3, color=col, linespacing=0.95)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["DEM\npredicted", "voxel FE\nverified"])
    ax.set_xlim(-1.15, 1.08)
    ax.set_ylabel(r"$C_{1111}$ (KUBC)")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="0.9", lw=0.6)
    for x, txt in ((0.005, r"(a) thickness field $t(\mathbf{x})$"), (0.42, "(b) optimized cell, colour $= t$"),
                   (0.715, "(c) predicted vs verified")):
        fig.text(x, 0.93, txt, fontsize=9.5, ha="left", va="bottom")
    save(fig, "fig4_e3_result")


if __name__ == "__main__":
    fig1(); fig7(); fig6()


def fig3_pipeline():
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    H = 2.75
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
    geo, phy, des = ("#DCE9F5", "#3A6EA5"), ("#FBE3D2", "#C0602A"), ("#DDEFE0", "#2E8B57")
    cards = [
        ("Analytic TPMS\nlevel set", r"$\phi=|F(k\mathbf{x})|-t(\mathbf{x})$", "fam_gyroid", geo),
        ("MC collocation", r"$\mathbf{x}_i\sim\mathcal{U}\{\phi<0\}$", "mc_cloud", geo),
        ("Conditional DEM", r"$\mathbf{u}(\mathbf{x},t)=\arg\min\,\Pi$", None, phy),
        ("Analytic\nsensitivities", r"$\partial\Pi/\partial\boldsymbol{\theta},\ \partial V_f/\partial\boldsymbol{\theta}$", None, phy),
        ("Graded design", r"$\boldsymbol{\theta},\ \delta t_0$  ($V_f$ fixed)", "graded_thickness", des),
    ]
    cw, gap, x0, yb, ch = 1.06, 0.17, 0.09, 0.78, 1.52
    centers = []
    for i, (title, eq, im, (fc, ec)) in enumerate(cards):
        x = x0 + i * (cw + gap)
        ax.add_patch(FancyBboxPatch((x, yb), cw, ch, boxstyle="round,pad=0.0,rounding_size=0.08",
                                    fc=fc, ec=ec, lw=1.1))
        ax.text(x + cw / 2, yb + ch - 0.07, title, ha="center", va="top", fontsize=8.3,
                fontweight="bold", color="0.15", linespacing=1.0)
        ax.text(x + cw / 2, yb + 0.08, eq, ha="center", va="bottom", fontsize=7.2, color="0.15")
        if im:
            iax = fig.add_axes([(x + 0.14) / W, (yb + 0.30) / H, (cw - 0.28) / W, 0.82 / H])
            iax.imshow(img(im), interpolation="lanczos"); iax.axis("off")
        elif i == 2:
            for k, (layer, n) in enumerate([(0, 3), (1, 5), (2, 5), (3, 3)]):
                ys = yb + 0.72 + (np.arange(n) - (n - 1) / 2) * 0.13
                xs = x + 0.2 + layer * 0.235
                if k < 3:
                    nxt = [(1, 5), (2, 5), (3, 3)][k][1]
                    y2 = yb + 0.72 + (np.arange(nxt) - (nxt - 1) / 2) * 0.13
                    for a in ys:
                        for b in y2:
                            ax.plot([xs, xs + 0.235], [a, b], color="0.7", lw=0.35, zorder=1)
                ax.scatter(np.full(n, xs), ys, s=16, color=ec, zorder=2, edgecolor="white", lw=0.4)
            ax.text(x + cw / 2, yb + 0.33, "Fourier features, MLP\nhard KUBC", ha="center",
                    va="center", fontsize=6.5, color="0.3", linespacing=1.0)
        else:
            ax.text(x + cw / 2, yb + 0.75, "exact Hessian\nsmoothed membership\nno remeshing",
                    ha="center", va="center", fontsize=6.8, color="0.3", linespacing=1.15)
        centers.append(x + cw / 2)
        if i < 4:
            ax.add_patch(FancyArrowPatch((x + cw + 0.02, yb + ch / 2), (x + cw + gap - 0.02, yb + ch / 2),
                                         arrowstyle="-|>", mutation_scale=9, lw=1.1, color="0.25"))
    top = yb + ch
    ly = top + 0.2
    ax.plot([centers[4], centers[4], centers[0]], [top + 0.01, ly, ly], color="0.3", lw=1.0)
    ax.add_patch(FancyArrowPatch((centers[0], ly), (centers[0], top + 0.01), arrowstyle="-|>",
                                 mutation_scale=9, lw=1.0, color="0.3"))
    ax.text((centers[0] + centers[4]) / 2, ly + 0.04, r"update $\boldsymbol{\theta}$: new analytic geometry, no remeshing",
            ha="center", va="bottom", fontsize=7.4, style="italic", color="0.25")
    gates = [("N1", "level-set identities", 0), ("N2 · N3", "solver and KUBC benchmarks", 2),
             ("FE re-analysis · VG-MM", "voxel FE of designs", 4)]
    gy = 0.08
    ax.text(1.30, gy + 0.21, "independent verification", fontsize=7.4, color="0.35", style="italic")
    for label, desc, target in gates:
        cx = centers[target]
        bw = 1.3 if target == 2 else 1.06
        ax.add_patch(FancyBboxPatch((cx - bw / 2, gy), bw, 0.42, boxstyle="round,pad=0,rounding_size=0.05",
                                    fc="white", ec="0.45", lw=0.8, ls="--"))
        ax.text(cx, gy + 0.28, label, ha="center", va="center", fontsize=7.6, fontweight="bold", color="0.2")
        ax.text(cx, gy + 0.11, desc, ha="center", va="center", fontsize=6.4, color="0.35")
        ax.plot([cx, cx], [gy + 0.42, yb - 0.01], color="0.5", lw=0.7, ls=":")
    fig.savefig(FIGS / "fig2_pipeline.pdf", facecolor="white")
    fig.savefig(REN / "fig3_pipeline_preview.png", dpi=150, facecolor="white")
    plt.close(fig)
    print("wrote fig3 pipeline")
