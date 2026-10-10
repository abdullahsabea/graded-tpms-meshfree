"""Publication figures for the TPMS mesh-free TO paper.
Outputs: paper/figures/fig1..fig4 as PNG (300 dpi) and PDF.
"""
import sys, os, json
from pathlib import Path
sys.path.insert(0, str(Path(sys.executable).parent.parent.parent))
from daimon_runtime import setup_plot
setup_plot()
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = Path(__file__).parent
PAPER = HERE.parent / "paper"
FIG = PAPER / "figures"
FIG.mkdir(parents=True, exist_ok=True)
N3 = HERE / "n3"

def gyroid_F(X, Y, Z):  return np.sin(X)*np.cos(Y) + np.sin(Y)*np.cos(Z) + np.sin(Z)*np.cos(X)
def primitive_F(X, Y, Z): return np.cos(X) + np.cos(Y) + np.cos(Z)
def diamond_F(X, Y, Z):
    return (np.sin(X)*np.sin(Y)*np.sin(Z) + np.sin(X)*np.cos(Y)*np.cos(Z)
            + np.cos(X)*np.sin(Y)*np.cos(Z) + np.cos(X)*np.cos(Y)*np.sin(Z))

K = 2*np.pi

# ---------------------------------------------------------------- Fig 1
def fig1():
    N = 56
    c = (np.arange(N)+0.5)/N
    X, Y, Z = np.meshgrid(K*c, K*c, K*c, indexing="ij")
    fig = plt.figure(figsize=(9.6, 3.1))
    for i, (name, F, t) in enumerate([("Gyroid", gyroid_F, 0.55),
                                      ("Primitive", primitive_F, 1.10),
                                      ("Diamond", diamond_F, 0.75)]):
        solid = np.abs(F(X, Y, Z)) < t
        # match ~19% VF by quick threshold tune
        absF = np.abs(F(X, Y, Z)).ravel()
        thr = np.quantile(absF, 0.19)
        solid = (np.abs(F(X, Y, Z)) < thr)
        ax = fig.add_subplot(1, 3, i+1, projection="3d")
        ax.voxels(solid, facecolors="#4C72B0", edgecolor="none", shade=True)
        ax.set_title(name, fontsize=12)
        ax.set_box_aspect((1,1,1)); ax.set_axis_off()
        ax.view_init(elev=22, azim=38)
    fig.suptitle("")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"fig1_tpms_families.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("fig1 done")

# ---------------------------------------------------------------- Fig 2
def fig2():
    fig, ax = plt.subplots(figsize=(10.5, 3.4))
    ax.set_xlim(0, 10.5); ax.set_ylim(0, 3.4); ax.axis("off")
    boxes = [
        (0.15, "Analytic TPMS\nlevel set\n$\\phi=|F(kx)|-t(x)$", "#DDEBF7"),
        (2.35, "Monte-Carlo\ncollocation\ninside $\\{\\phi<0\\}$", "#DDEBF7"),
        (4.55, "Deep energy\nminimization\n$u^*=\\arg\\min\\,\\Pi(u)$", "#FCE4D6"),
        (6.75, "Analytic\nsensitivities\n$\\partial\\phi/\\partial t,\\ \\partial\\phi/\\partial k$", "#FCE4D6"),
        (8.95, "Grading\noptimization\n$\\theta^*$, $V_f$ fixed", "#E2EFDA"),
    ]
    for x, txt, color in boxes:
        ax.add_patch(FancyBboxPatch((x, 1.05), 1.75, 1.5, boxstyle="round,pad=0.08",
                                    fc=color, ec="k", lw=1.0))
        ax.text(x+0.875, 1.8, txt, ha="center", va="center", fontsize=9.5)
    for x in (1.95, 4.15, 6.35, 8.55):
        ax.add_patch(FancyArrowPatch((x, 1.8), (x+0.38, 1.8),
                                     arrowstyle="-|>", mutation_scale=18, lw=1.4))
    ax.text(5.25, 0.45, "verification: voxel FEM (code aster)  $\\rightarrow$  N1 identities / N2 benchmarks / N3 homogenization / E3 optimized cell",
            ha="center", fontsize=9, style="italic")
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"fig2_pipeline.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("fig2 done")

# ---------------------------------------------------------------- Fig 3
def fig3():
    vf = np.array([0.1288, 0.1934, 0.2910])
    fem = np.array([0.06724, 0.10725, 0.18581])
    dem = np.array([0.0705, 0.1127, 0.1856])
    audit = json.load(open(N3 / "e3_cond_audit.json"))
    ts = sorted(float(k) for k in audit)
    cond = np.array([audit[f"{t:.2f}"]["C1111"] for t in ts])
    cond_vf = np.array([0.1288, None, 0.1934, None, None, 0.2910])
    # vf for the extra audit t values via interp on the vf table
    tab = json.load(open(N3 / "e3_vf_table.json"))
    vf_all = np.interp(ts, tab["t"], tab["vf"])

    fig, ax = plt.subplots(figsize=(5.6, 4.2))
    ax.plot(vf_all, cond, "-", color="#4C72B0", lw=1.8,
            label="conditional DEM $u(x,t)$ (this work)")
    ax.plot(vf, dem, "s", color="#DD8452", ms=8, label="single-thickness DEM")
    ax.plot(vf, fem, "o", color="#55A868", ms=8, label="voxel FEM (code aster)")
    for x, y in zip(vf, fem):
        ax.annotate(f"{y:.4f}", (x, y), textcoords="offset points",
                    xytext=(6, -12), fontsize=8)
    ax.set_xlabel("solid volume fraction $V_f$")
    ax.set_ylabel("$C_{1111}$ (KUBC, $\\varepsilon_{xx}$)")
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"fig3_c1111_vs_vf.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("fig3 done")

# ---------------------------------------------------------------- Fig 4
def fig4():
    res = json.load(open(N3 / "e3_coord_search.json"))
    theta = np.array(res["theta"]); mid = res["t0shift"]
    MODES = [(1,0,0),(0,1,0),(0,0,1),(1,1,0),(1,0,1),(0,1,1)]
    def t_of(X, Y, Z):
        val = 0.30 + mid
        for i, (a, b, c) in enumerate(MODES):
            ph = 2*np.pi*(a*X + b*Y + c*Z)
            val = val + theta[2*i]*np.cos(ph) + theta[2*i+1]*np.sin(ph)
        return np.clip(val, 0.12, 0.55)

    fig = plt.figure(figsize=(11.5, 3.6))
    # (a) t(x) slices
    N = 200
    c = (np.arange(N)+0.5)/N
    X, Y = np.meshgrid(c, c, indexing="ij")
    for j, z0 in enumerate((0.25, 0.5)):
        ax = fig.add_subplot(1, 4, j+1)
        tv = t_of(X, Y, np.full_like(X, z0))
        im = ax.pcolormesh(c, c, tv, cmap="viridis", vmin=0.12, vmax=0.55)
        ax.set_title(f"$t(x)$ slice $z={z0}$", fontsize=10)
        ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
        fig.colorbar(im, ax=ax, shrink=0.8)
    # (b) 3D render of graded design
    Nv = 52
    cc = (np.arange(Nv)+0.5)/Nv
    X3, Y3, Z3 = np.meshgrid(cc, cc, cc, indexing="ij")
    tv3 = t_of(X3, Y3, Z3)
    solid = np.abs(gyroid_F(K*X3, K*Y3, K*Z3)) < tv3
    ax = fig.add_subplot(1, 4, 3, projection="3d")
    ax.voxels(solid, facecolors="#C44E52", edgecolor="none", shade=True)
    ax.set_title("optimized graded cell", fontsize=10)
    ax.set_box_aspect((1,1,1)); ax.set_axis_off(); ax.view_init(elev=22, azim=38)
    # (c) performance bars
    ax = fig.add_subplot(1, 4, 4)
    labels = ["uniform\n(FEM)", "graded\n(FEM)", "uniform\n(DEM)", "graded\n(DEM)"]
    # DEPRECATED (2026-08-25): superseded face-basis numbers; canonical
    # energy-basis values live in research/n3/paper_numbers.json (master
    # synthesis C1). Figure regeneration must switch to paper_numbers.json (Q12).
    vals = [0.10725, 0.11699, 0.1139, 0.1338]
    colors = ["#55A868", "#55A868", "#4C72B0", "#4C72B0"]
    bars = ax.bar(labels, vals, color=colors, width=0.65)
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, v+0.001, f"{v:.4f}", ha="center", fontsize=8)
    ax.annotate("+9.1 %", xy=(1, 0.122), ha="center", fontsize=11,
                color="#55A868", fontweight="bold")
    ax.set_ylabel("$C_{1111}$")
    ax.set_ylim(0, 0.15)
    ax.set_title("iso-volume $V_f=0.193$", fontsize=10)
    ax.tick_params(labelsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"fig4_e3_result.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("fig4 done")

if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4()
    print("all figures in", FIG)
