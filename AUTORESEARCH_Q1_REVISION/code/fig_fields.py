"""Manuscript Figs. 8 (field verification) and 9 (design mechanism), unified style.

Data: archived mid-plane slices (research/n3/slice_*.npz, energy density at unit
applied strain) and field_stats.json. Display-side bilinear upsampling only; the
thin grey line is the analytic wall boundary |F| = t on the slice.
"""
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from scipy.ndimage import zoom

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from render3d import F_gyroid, F_primitive, graded_t  # noqa: E402

N3 = HERE.parents[1] / "research" / "n3"
FIGS = HERE.parent / "MATERIALS_DESIGN_TRANSFER" / "manuscript" / "figures"
PREV = HERE.parent / "_deep_review" / "render3d"
W = 6.3
C_UNI, C_GRD = "#009E73", "#D55E00"

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["STIXGeneral", "DejaVu Serif"],
    "mathtext.fontset": "stix", "font.size": 8.5, "axes.labelsize": 8.5,
    "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "axes.linewidth": 0.6,
    "xtick.major.size": 2.5, "ytick.major.size": 2.5, "xtick.major.width": 0.6,
    "ytick.major.width": 0.6, "savefig.dpi": 450,
})


def upsample(a, k=4):
    m = np.isfinite(a)
    z = zoom(np.where(m, a, 0.0), k, order=1)
    zm = zoom(m.astype(float), k, order=1)
    return np.ma.masked_invalid(np.where(zm > 0.55, z, np.nan))


def outline(ax, F, t_of, z=0.5, n=500):
    c = np.linspace(0, 1, n)
    X, Y = np.meshgrid(c, c, indexing="ij")
    phi = np.abs(F(X, Y, np.full_like(X, z))) - t_of(X, Y, np.full_like(X, z))
    ax.contour(c, c, phi.T, levels=[0.0], colors="0.45", linewidths=0.45)


def field(ax, arr, cmap, vmin, vmax):
    a = upsample(arr)
    g = np.linspace(0, 1, a.shape[0])
    return ax.pcolormesh(g, g, a.T, cmap=cmap, vmin=vmin, vmax=vmax,
                         shading="auto", rasterized=True)


def frame(ax, xl=False, yl=False):
    ax.set_aspect("equal"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_xticks([0, 0.5, 1]); ax.set_yticks([0, 0.5, 1])
    ax.set_xticklabels(["0", "0.5", "1"] if xl else [])
    ax.set_yticklabels(["0", "0.5", "1"] if yl else [])
    if xl:
        ax.set_xlabel("$x_1$", labelpad=1)
    if yl:
        ax.set_ylabel("$x_2$", labelpad=1)
    for s in ax.spines.values():
        s.set_color("0.35")


def cbar(fig, im, rect, label, ticks=None):
    cax = fig.add_axes(rect)
    cb = fig.colorbar(im, cax=cax, ticks=ticks)
    cb.set_label(label, fontsize=8, labelpad=2)
    cb.ax.tick_params(labelsize=7, length=2)
    cb.outline.set_linewidth(0.5)


def load_arrow(fig, x, y):
    fig.patches.append(mpl.patches.FancyArrow(x, y, 0.07, 0, width=0.004, head_width=0.018,
                       head_length=0.015, transform=fig.transFigure, color="0.2", lw=0))
    fig.text(x + 0.095, y, r"$\bar\varepsilon_{11}$", va="center", fontsize=8.5)


def fig8():
    H = 4.55
    fig = plt.figure(figsize=(W, H))
    s_w, s_h = 1.40 / W, 1.40 / H
    xs = [0.10, 0.10 + s_w + 0.016, 0.10 + 2 * s_w + 0.016 + 0.125]
    ys = [0.565, 0.12]
    rows = [("Gyroid, $t=0.30$", "slice_fe_uniform.npz", "slice_dem_gyroid.npz",
             "slice_dem_gyroid_nodes.npz", F_gyroid, 0.30),
            ("Primitive, $t=0.3387$", "slice_fe_primitive.npz", "slice_dem_primitive.npz",
             "slice_dem_primitive_nodes.npz", F_primitive, 0.3387)]
    for r, (lab, fe_f, dem_f, demn_f, F, t) in enumerate(rows):
        fe, dem, demn = np.load(N3 / fe_f), np.load(N3 / dem_f), np.load(N3 / demn_f)
        e_fe = fe["ENEL"]
        e_dem = np.where(dem["inside"], dem["enel"], np.nan)
        vmax = np.nanpercentile(np.concatenate([e_fe[np.isfinite(e_fe)], e_dem[np.isfinite(e_dem)]]), 99)
        both = np.isfinite(e_fe) & demn["inside"]
        diff = np.where(both, (demn["enel"] - e_fe) / np.nanmean(e_fe[both]) * 100, np.nan)
        lim = np.nanpercentile(np.abs(diff), 98)
        tconst = lambda x, y, z, t=t: np.full_like(x, t)
        for c, (arr, ttl, cm, lo, hi) in enumerate([
                (e_fe, "voxel FE", "magma", 0, vmax), (e_dem, "mesh-free DEM", "magma", 0, vmax),
                (diff, r"DEM $-$ FE", "RdBu_r", -lim, lim)]):
            ax = fig.add_axes([xs[c], ys[r], s_w, s_h])
            im = field(ax, arr, cm, lo, hi)
            outline(ax, F, tconst)
            frame(ax, xl=(r == 1), yl=(c == 0))
            ax.set_title(f"({'abcdef'[3 * r + c]}) {ttl}", fontsize=9, pad=3)
            if c == 1:
                cbar(fig, im, [xs[1] + s_w + 0.012, ys[r], 0.012, s_h], "energy density")
            if c == 2:
                cbar(fig, im, [xs[2] + s_w + 0.012, ys[r], 0.012, s_h], "% of mean density")
        fig.text(0.022, ys[r] + s_h / 2, lab, rotation=90, va="center", ha="center", fontsize=9)
    load_arrow(fig, 0.78, 0.975)
    fig.savefig(FIGS / "fig6_field_verification.png", facecolor="white")
    fig.savefig(PREV / "fig8_preview.png", dpi=150, facecolor="white")
    plt.close(fig)
    print("fig8 done")


def fig9():
    fu, fg = np.load(N3 / "slice_fe_uniform.npz"), np.load(N3 / "slice_fe_graded.npz")
    st = json.loads((N3 / "field_stats.json").read_text())
    cs = json.loads((N3 / "e3_coord_search.json").read_text())
    t_g = graded_t(np.array(cs["theta"]), cs["t0shift"], 0.12, 0.55)
    H = 2.45
    fig = plt.figure(figsize=(W, H))
    s_w, s_h = 1.50 / W, 1.50 / H
    y0 = 0.19
    vmax = np.nanpercentile(np.concatenate([fu["ENEL"].ravel(), fg["ENEL"].ravel()]), 99)
    im = None
    for i, (d, ttl, tf) in enumerate([(fu, r"(a) uniform $t=0.30$", lambda x, y, z: np.full_like(x, 0.30)),
                                      (fg, "(b) optimized graded", t_g)]):
        ax = fig.add_axes([0.07 + i * (s_w + 0.018), y0, s_w, s_h])
        im = field(ax, d["ENEL"], "magma", 0, vmax)
        outline(ax, F_gyroid, tf)
        frame(ax, xl=True, yl=(i == 0))
        ax.set_title(ttl, fontsize=9, pad=3)
    cbar(fig, im, [0.07 + 2 * s_w + 0.018 + 0.012, y0, 0.012, s_h], "energy density")

    ax = fig.add_axes([0.752, y0, s_w, s_h])
    Lu, Lg = st["uniform"]["lorenz"], st["graded"]["lorenz"]
    mu, eu = np.array(Lu["material"]), np.array(Lu["energy"])
    mg, eg = np.array(Lg["material"]), np.array(Lg["energy"])
    ax.fill_between(mg, np.interp(mg, mu, eu), eg, color=C_GRD, alpha=0.15, lw=0)
    ax.plot([0, 1], [0, 1], ":", color="0.55", lw=0.9)
    ax.plot(mu, eu, color=C_UNI, lw=1.6)
    ax.plot(mg, eg, color=C_GRD, lw=1.6)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_aspect("equal")
    ax.set_xticks([0, 0.5, 1]); ax.set_yticks([0, 0.5, 1])
    ax.set_xlabel("cumulative material share", labelpad=1)
    ax.set_ylabel("cumulative energy share", labelpad=1)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    u, g = st["uniform"], st["graded"]
    ax.text(0.03, 0.97, f"uniform (Gini {u['gini']:.2f})", color=C_UNI, fontsize=7.5,
            transform=ax.transAxes, va="top")
    ax.text(0.03, 0.87, f"graded (Gini {g['gini']:.2f})", color=C_GRD, fontsize=7.5,
            transform=ax.transAxes, va="top")
    ax.text(0.03, 0.77, f"top 20% of material:\n{u['top20_energy_pct']:.0f}% → {g['top20_energy_pct']:.0f}% of energy",
            ha="left", va="top", fontsize=7.3, color="0.25", transform=ax.transAxes)
    ax.set_title("(c) energy concentration", fontsize=9, pad=3)
    load_arrow(fig, 0.07, 0.965)
    fig.savefig(FIGS / "fig7_design_mechanism.png", facecolor="white")
    fig.savefig(PREV / "fig9_preview.png", dpi=150, facecolor="white")
    plt.close(fig)
    print("fig9 done")


if __name__ == "__main__":
    fig8(); fig9()
