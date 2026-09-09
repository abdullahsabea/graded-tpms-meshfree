"""Publication figures v2 for the TPMS mesh-free TO manuscript.

Standalone (numpy + matplotlib only). Regenerates paper/figures/fig1..fig4
as 300-dpi PNG and vector PDF with a consistent journal style.
"""
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = Path(__file__).parent
FIG = HERE / "figures"
FIG.mkdir(exist_ok=True)
N3 = HERE.parent / "research" / "n3"

# ---- journal style ---------------------------------------------------------
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["STIXGeneral", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 9.5,
    "axes.labelsize": 10,
    "axes.titlesize": 10,
    "legend.fontsize": 8.5,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "axes.linewidth": 0.8,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linewidth": 0.6,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "legend.framealpha": 0.95,
    "legend.edgecolor": "0.8",
})
# Okabe-Ito colorblind-safe palette
C_FEM = "#009E73"    # green
C_DEM = "#E69F00"    # orange
C_COND = "#0072B2"   # blue
C_ACC = "#D55E00"    # vermillion
C_SOLID = "#4A6FA5"  # muted steel blue for 3D solids
C_SOLID2 = "#A5484A"

K = 2 * np.pi
FEM_REF_T045 = 0.18114   # code_aster N128, converged (see Table A.5)

def gyroid_F(X, Y, Z):
    return np.sin(X)*np.cos(Y) + np.sin(Y)*np.cos(Z) + np.sin(Z)*np.cos(X)

def primitive_F(X, Y, Z):
    return np.cos(X) + np.cos(Y) + np.cos(Z)

def diamond_F(X, Y, Z):
    return (np.sin(X)*np.sin(Y)*np.sin(Z) + np.sin(X)*np.cos(Y)*np.cos(Z)
            + np.cos(X)*np.sin(Y)*np.cos(Z) + np.cos(X)*np.cos(Y)*np.sin(Z))

def save(fig, name):
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"{name}.{ext}", dpi=300, bbox_inches="tight",
                    pad_inches=0.04)
    plt.close(fig)
    print(name, "done")

# ------------------------------------------------------------------- Fig 1
def fig1():
    N = 64
    c = (np.arange(N) + 0.5) / N
    X, Y, Z = np.meshgrid(K*c, K*c, K*c, indexing="ij")
    fig = plt.figure(figsize=(9.8, 3.4))
    for i, (name, F) in enumerate([("Gyroid", gyroid_F),
                                   ("Primitive", primitive_F),
                                   ("Diamond", diamond_F)]):
        absF = np.abs(F(X, Y, Z))
        thr = np.quantile(absF.ravel(), 0.19)     # matched Vf = 0.19
        solid = absF < thr
        ax = fig.add_subplot(1, 3, i+1, projection="3d")
        ax.voxels(solid, facecolors=C_SOLID, edgecolor="none", shade=True)
        ax.set_title(f"({chr(97+i)}) {name}", fontsize=11, pad=0)
        ax.set_box_aspect((1, 1, 1))
        ax.set_axis_off()
        ax.view_init(elev=22, azim=38)
    fig.subplots_adjust(left=0, right=1, top=0.98, bottom=0, wspace=0.02)
    save(fig, "fig1_tpms_families")

# ------------------------------------------------------------------- Fig 2
def fig2():
    fig, ax = plt.subplots(figsize=(10.8, 3.8))
    ax.set_xlim(0, 11.6)
    ax.set_ylim(0, 3.9)
    ax.axis("off")
    ax.grid(False)
    W, H, Y0 = 1.86, 1.42, 1.55
    boxes = [
        (0.25, "Analytic TPMS\nlevel set\n$\\phi=|F(k\\mathbf{x})|-t(\\mathbf{x})$", "#DCE9F7"),
        (2.55, "Rejection-sampled\nMC collocation\nin $\\{\\phi<0\\}$", "#DCE9F7"),
        (4.85, "Conditional DEM\n$u(\\mathbf{x},t)$\n$\\min_\\theta\\,\\Pi(u_\\theta)$", "#FBE5D4"),
        (7.15, "Objective + analytic\nsensitivities\n$\\partial\\Pi/\\partial\\theta,\\ \\partial V_f/\\partial\\theta$", "#FBE5D4"),
        (9.45, "Design update\n$\\theta$, $\\delta t_0$\n($V_f$ fixed)", "#DFEEDA"),
    ]
    for x, txt, color in boxes:
        ax.add_patch(FancyBboxPatch((x, Y0), W, H, boxstyle="round,pad=0.09",
                                    fc=color, ec="0.25", lw=1.0))
        ax.text(x + W/2, Y0 + H/2, txt, ha="center", va="center", fontsize=9)
    for x in (2.18, 4.48, 6.78, 9.08):
        ax.add_patch(FancyArrowPatch((x - 0.02, Y0 + H/2), (x + 0.32, Y0 + H/2),
                                     arrowstyle="-|>", mutation_scale=16,
                                     lw=1.3, color="0.2"))
    # loop-back arrow: design update -> level set (no remeshing)
    ax.add_patch(FancyArrowPatch((9.45 + W/2, Y0 + H + 0.12),
                                 (0.25 + W/2, Y0 + H + 0.12),
                                 arrowstyle="-|>", mutation_scale=16, lw=1.2,
                                 color="0.2",
                                 connectionstyle="arc,angleA=90,angleB=90,armA=28,armB=28,rad=8"))
    ax.text(5.8, Y0 + H + 0.72, "updated $t(\\mathbf{x};\\theta)$: new geometry, no remeshing",
            ha="center", fontsize=9, style="italic", color="0.15")
    # verification strip
    ax.add_patch(FancyBboxPatch((0.25, 0.28), 11.06, 0.62,
                                boxstyle="round,pad=0.06",
                                fc="#F2F2F2", ec="0.45", lw=0.9,
                                linestyle=(0, (4, 2))))
    ax.text(5.78, 0.59, "verification gates (voxel FEM, code_aster):  "
            "N1 level-set identities  /  N2 solver benchmarks  /  "
            "N3 homogenization  /  FE re-analysis of optimum",
            ha="center", va="center", fontsize=8.8, color="0.15")
    save(fig, "fig2_pipeline")

# ------------------------------------------------------------------- Fig 3
def fig3():
    vf = np.array([0.1288, 0.1934, 0.2910])
    # finest-grid code_aster references: N96, N64, N128 (see Table A.5)
    fem = np.array([0.06724, 0.10725, FEM_REF_T045])
    dem = np.array([0.0705, 0.1127, 0.1856])
    audit = json.load(open(N3 / "e3_cond_audit.json"))
    ts = sorted(float(k) for k in audit)
    cond = np.array([audit[f"{t:.2f}"]["C1111"] for t in ts])
    tab = json.load(open(N3 / "e3_vf_table.json"))
    vf_cond = np.interp(ts, tab["t"], tab["vf"])

    fig, (ax, axb) = plt.subplots(1, 2, figsize=(9.4, 3.7),
                                  gridspec_kw={"width_ratios": [1.35, 1]})
    # (a) stiffness vs volume fraction
    ax.plot(vf_cond, cond, "-", color=C_COND, lw=1.8, zorder=2,
            label="conditional DEM $u(\\mathbf{x},t)$, one training run")
    ax.plot(vf_cond, cond, "o", color=C_COND, ms=3.5, zorder=2)
    ax.plot(vf, dem, "s", color=C_DEM, ms=8, mec="white", mew=0.8, zorder=3,
            label="single-thickness DEM")
    ax.plot(vf, fem, "o", color=C_FEM, ms=8, mec="white", mew=0.8, zorder=4,
            label="voxel FEM (code_aster), mesh-converged")
    for x, y in zip(vf, fem):
        ax.annotate(f"{y:.4f}", (x, y), textcoords="offset points", xytext=(8, -11),
                    fontsize=8, color="0.25")
    ax.set_xlabel("solid volume fraction $V_f$")
    ax.set_ylabel("$C_{1111}$  (KUBC, $\\bar\\varepsilon_{11}$)")
    ax.legend(loc="upper left")
    ax.set_title("(a)", loc="left", fontsize=10)

    # (b) relative deviation at the FEM anchors
    dev_dem = (dem / fem - 1) * 100
    dev_cond = np.array([audit[f"{t:.2f}"]["C1111"] for t in (0.2, 0.3, 0.45)])
    dev_cond = (dev_cond / fem - 1) * 100
    xpos = np.arange(3)
    wbar = 0.34
    axb.axhspan(-5, 5, color="0.92", zorder=0)
    axb.axhline(0, color="0.4", lw=0.8, zorder=1)
    b1 = axb.bar(xpos - wbar/2, dev_dem, wbar, color=C_DEM,
                 label="single-thickness DEM", zorder=2)
    b2 = axb.bar(xpos + wbar/2, dev_cond, wbar, color=C_COND,
                 label="conditional DEM", zorder=2)
    for bars in (b1, b2):
        for b in bars:
            v = b.get_height()
            axb.text(b.get_x() + b.get_width()/2,
                     v + (0.25 if v >= 0 else -0.75),
                     f"{v:+.1f}", ha="center", fontsize=7.5, color="0.2")
    axb.set_xticks(xpos)
    axb.set_xticklabels(["$V_f=0.13$\n$(t=0.20)$", "$V_f=0.19$\n$(t=0.30)$",
                         "$V_f=0.29$\n$(t=0.45)$"], fontsize=8.5)
    axb.set_ylabel("deviation from FEM  [%]")
    axb.set_ylim(-1.5, 9.5)
    axb.legend(loc="upper right")
    axb.set_title("(b)", loc="left", fontsize=10)
    axb.text(2.42, -1.15, "$\\pm5\\%$ band", fontsize=8, color="0.4",
             ha="right")
    fig.tight_layout(w_pad=2.0)
    save(fig, "fig3_c1111_vs_vf")

# ------------------------------------------------------------------- Fig 4
def fig4():
    res = json.load(open(N3 / "e3_coord_search.json"))
    theta = np.array(res["theta"])
    mid = res["t0shift"]
    MODES = [(1,0,0), (0,1,0), (0,0,1), (1,1,0), (1,0,1), (0,1,1)]

    def t_of(X, Y, Z):
        val = 0.30 + mid
        for i, (a, b, c) in enumerate(MODES):
            ph = 2*np.pi*(a*X + b*Y + c*Z)
            val = val + theta[2*i]*np.cos(ph) + theta[2*i+1]*np.sin(ph)
        return np.clip(val, 0.12, 0.55)

    fig = plt.figure(figsize=(11.6, 3.5))
    gs = fig.add_gridspec(1, 4, width_ratios=[1, 1, 1.15, 1.25],
                          wspace=0.28)
    # (a) t(x) slices, shared colorbar
    N = 240
    c = (np.arange(N) + 0.5) / N
    X, Y = np.meshgrid(c, c, indexing="ij")
    ims = []
    for j, z0 in enumerate((0.25, 0.5)):
        ax = fig.add_subplot(gs[0, j])
        tv = t_of(X, Y, np.full_like(X, z0))
        im = ax.pcolormesh(c, c, tv.T, cmap="viridis", vmin=0.12, vmax=0.55,
                           shading="auto", rasterized=True)
        ims.append(im)
        ax.set_title(f"(a{j+1})  $t(\\mathbf{{x}})$,  $z={z0}$", fontsize=9.5)
        ax.set_aspect("equal")
        ax.set_xticks([]); ax.set_yticks([])
        ax.grid(False)
    cb = fig.colorbar(ims[0], ax=fig.axes[:2], shrink=0.82, pad=0.02,
                      aspect=18)
    cb.set_label("$t$", fontsize=9)
    cb.ax.tick_params(labelsize=8)
    # (b) 3D voxel render
    Nv = 56
    cc = (np.arange(Nv) + 0.5) / Nv
    X3, Y3, Z3 = np.meshgrid(cc, cc, cc, indexing="ij")
    tv3 = t_of(X3, Y3, Z3)
    solid = np.abs(gyroid_F(K*X3, K*Y3, K*Z3)) < tv3
    ax = fig.add_subplot(gs[0, 2], projection="3d")
    ax.voxels(solid, facecolors=C_SOLID2, edgecolor="none", shade=True)
    ax.set_title("(b)  optimized graded cell", fontsize=9.5, pad=0)
    ax.set_box_aspect((1, 1, 1))
    ax.set_axis_off()
    ax.view_init(elev=22, azim=38)
    # (c) performance bars
    ax = fig.add_subplot(gs[0, 3])
    labels = ["uniform", "graded", "uniform", "graded"]
    vals = [0.10725, 0.11699, 0.1139, 0.1338]
    xp = np.array([0, 1, 2.4, 3.4]) * 0.72
    colors = [C_FEM, C_FEM, C_COND, C_COND]
    bars = ax.bar(xp, vals, width=0.6, color=colors, zorder=2)
    bars[0].set_alpha(0.55)
    bars[2].set_alpha(0.55)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width()/2, v + 0.002, f"{v:.4f}",
                ha="center", fontsize=7.5, color="0.15")
    ax.annotate("", xy=(xp[1], 0.129), xytext=(xp[0], 0.129),
                arrowprops=dict(arrowstyle="->", color=C_FEM, lw=1.2))
    ax.text((xp[0]+xp[1])/2, 0.131, "+9.1%", ha="center", fontsize=9.5,
            color=C_FEM, fontweight="bold")
    ax.annotate("", xy=(xp[3], 0.145), xytext=(xp[2], 0.145),
                arrowprops=dict(arrowstyle="->", color=C_COND, lw=1.2))
    ax.text((xp[2]+xp[3])/2, 0.147, "+17.5%", ha="center", fontsize=9.5,
            color=C_COND, fontweight="bold")
    ax.set_xticks(xp)
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.text((xp[0]+xp[1])/2, -0.022, "FEM (code_aster)", ha="center",
            fontsize=8.5, color=C_FEM)
    ax.text((xp[2]+xp[3])/2, -0.022, "DEM (mesh-free)", ha="center",
            fontsize=8.5, color=C_COND)
    ax.set_ylabel("$C_{1111}$")
    ax.set_ylim(0, 0.158)
    ax.set_title("(c)  iso-volume $V_f=0.193$", fontsize=9.5)
    ax.grid(axis="y", alpha=0.25)
    ax.grid(axis="x", visible=False)
    save(fig, "fig4_e3_result")

if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4()
    print("all figures written to", FIG)
