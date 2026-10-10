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
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Circle
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize

HERE = Path(__file__).parent
FIG = HERE / "scratch_out" / "figures"
FIG.mkdir(exist_ok=True, parents=True)
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

def save(fig, name, svg=False, extra_dpi=None):
    """Save PNG (300 dpi) + vector PDF always; optionally SVG and a separate
    high-dpi PNG preview (used for the two schematic figures delivered as
    journal-submission-ready vector artwork)."""
    exts = ["png", "pdf"] + (["svg"] if svg else [])
    for ext in exts:
        fig.savefig(FIG / f"{name}.{ext}", dpi=300, bbox_inches="tight",
                    pad_inches=0.04)
    if extra_dpi:
        fig.savefig(FIG / f"{name}_{extra_dpi}dpi.png", dpi=extra_dpi,
                    bbox_inches="tight", pad_inches=0.04)
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
    """Five-stage mesh-free optimization loop, with the return arrow (updated
    design -> analytic geometry, no remeshing) above and the three-gate voxel
    FE verification protocol below, restructured into individually readable
    tagged cells rather than one crowded sentence."""
    MM = 1 / 25.4
    FS_TITLE, FS_EQ, FS_LOOP, FS_GATE = 9.0, 8.3, 7.8, 7.3
    C_BORDER = "0.18"

    # GAP widened (0.30 -> 0.48) so the forward-flow arrows have a visibly
    # clear shaft between box borders instead of the arrowhead appearing
    # to touch both boxes at once (found by direct inspection of the
    # compiled page).
    BOX_W, BOX_H, GAP = 3.15, 1.60, 0.48
    N = 5
    x0 = 0.30
    box_x = [x0 + i * (BOX_W + GAP) for i in range(N)]
    x_right = box_x[-1] + BOX_W
    Y0 = 2.55   # box bottom edge

    boxes = [
        ("Analytic TPMS field", "$\\phi=|F(k\\mathbf{x})|-t(\\mathbf{x})$", "#DCE9F7"),
        ("Rejection-sampled\nMC volume", "sampled in $\\{\\phi<0\\}$", "#DCE9F7"),
        ("Conditional DEM", "$u(\\mathbf{x},t),\\ \\min_\\theta\\,\\Pi(u_\\theta)$", "#FBE5D4"),
        ("Objective &\nsensitivities", "$\\partial\\Pi/\\partial\\boldsymbol{\\theta},\\ \\partial V_f/\\partial\\boldsymbol{\\theta}$", "#FBE5D4"),
        ("Design update", "$\\boldsymbol{\\theta},\\ \\delta t_0$   ($V_f$ fixed)", "#DFEEDA"),
        ("Objective &\nsensitivities", "$\\partial\\Pi/\\partial𝛉,\\ \\partial V_f/\\partial𝛉$", "#FBE5D4"),
        ("Design update", "$𝛉,\\ \\delta t_0$   ($V_f$ fixed)", "#DFEEDA"),
    ]

    fig, ax = plt.subplots(figsize=(175 * MM, 62 * MM))

    for x, (title, eq, color) in zip(box_x, boxes):
        ax.add_patch(FancyBboxPatch((x, Y0), BOX_W, BOX_H, boxstyle="round,pad=0.09",
                                    fc=color, ec=C_BORDER, lw=1.15, zorder=2))
        ax.text(x + BOX_W / 2, Y0 + BOX_H * 0.66, title, ha="center", va="center",
                fontsize=FS_TITLE, fontweight="bold", linespacing=1.3)
        ax.text(x + BOX_W / 2, Y0 + BOX_H * 0.28, eq, ha="center", va="center",
                fontsize=FS_EQ)

    # forward-flow arrows, endpoints pulled back further from both box
    # borders (0.06 -> 0.11) so the arrowhead and its shaft are visibly
    # separate from the boxes it connects, not touching either one.
    for x in box_x[1:]:
        ax.annotate("", xy=(x - 0.11, Y0 + BOX_H / 2),
                    xytext=(x - GAP + 0.11, Y0 + BOX_H / 2),
                    arrowprops=dict(arrowstyle="-|>", color=C_BORDER, lw=1.35,
                                    mutation_scale=15))

    # -- return loop: symmetric, orthogonal, well clear of the boxes ---------
    loop_y = Y0 + BOX_H + 0.95
    last_cx = box_x[-1] + BOX_W / 2
    first_cx = box_x[0] + BOX_W / 2
    path = [(last_cx, Y0 + BOX_H + 0.12), (last_cx, loop_y),
            (first_cx, loop_y), (first_cx, Y0 + BOX_H + 0.14)]
    _orth_arrow(ax, path, color=C_BORDER, lw=1.3, mutation_scale=15, zorder=2)
    # NOTE (PRESENTATION POLISH): removed a pre-existing dangling duplicate
    # positional string argument here (this line and the one it replaced
    # both existed in the original file, which would raise a TypeError
    # from matplotlib's Text() at runtime; not applied to the original
    # file, reported separately as a pre-existing defect).
    ax.text((first_cx + last_cx) / 2, loop_y + 0.22,
            "updated $\\boldsymbol{\\theta},\\ \\delta t_0$: new geometry, no remeshing",
            ha="center", va="bottom", fontsize=FS_LOOP, style="italic", color="0.15")

    # -- verification-gates panel: compact tagged cells, not one sentence ----
    gates = [
        ("N1", "level-set identities"),
        ("N2", "solver benchmarks"),
        ("N3", "homogenization"),
        ("FE re-analysis", "of optimum"),
    ]
    panel_top = Y0 - 0.42
    panel_h = 1.55
    panel_bot = panel_top - panel_h
    ax.add_patch(FancyBboxPatch((x0, panel_bot), x_right - x0, panel_h,
                                boxstyle="round,pad=0.06", fc="#F5F5F5",
                                ec="0.4", lw=1.0, linestyle=(0, (4, 2)), zorder=1))
    ax.text(x0 + 0.22, panel_top - 0.28,
            "verification (voxel FE, code_aster):",
            ha="left", va="center", fontsize=FS_GATE + 0.3, color="0.15",
            fontweight="bold")

    n_g = len(gates)
    g_gap = 0.24
    g_w = (x_right - x0 - 0.44 - (n_g - 1) * g_gap) / n_g
    g_y = panel_bot + 0.30
    g_h = 0.62
    for i, (tag, desc) in enumerate(gates):
        gx = x0 + 0.22 + i * (g_w + g_gap)
        ax.add_patch(FancyBboxPatch((gx, g_y), g_w, g_h, boxstyle="round,pad=0.04",
                                    fc="white", ec="0.55", lw=0.85, zorder=2))
        ax.text(gx + g_w / 2, g_y + g_h * 0.62, tag, ha="center", va="center",
                fontsize=FS_GATE, fontweight="bold", color="0.1")
        ax.text(gx + g_w / 2, g_y + g_h * 0.24, desc, ha="center", va="center",
                fontsize=FS_GATE - 0.3, color="0.25")

    ax.set_xlim(x0 - 0.25, x_right + 0.25)
    ax.set_ylim(panel_bot - 0.25, loop_y + 0.75)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.grid(False)
    fig.subplots_adjust(left=0.005, right=0.995, top=0.99, bottom=0.01)
    save(fig, "fig2_pipeline", svg=True, extra_dpi=600)

# --------------------------------------------------------- Fig 2b (network)
def _mlp_layer(ax, x, ys, r, color, lw_edge=1.0):
    """Draw one column of neurons at x-position x, y-positions ys."""
    for y in ys:
        ax.add_patch(Circle((x, y), r, fc=color, ec="0.2", lw=lw_edge, zorder=4))

def _mlp_connect(ax, x0, ys0, x1, ys1, color="0.65", lw=0.35, alpha=0.55):
    segs = [[(x0, y0), (x1, y1)] for y0 in ys0 for y1 in ys1]
    ax.add_collection(LineCollection(segs, colors=color, linewidths=lw,
                                     alpha=alpha, zorder=1))

def _orth_arrow(ax, pts, color="0.25", lw=1.2, style="-", mutation_scale=13, zorder=2):
    """Polyline through pts (right-angle path), arrowhead only on the last segment."""
    for (x0, y0), (x1, y1) in zip(pts[:-2], pts[1:-1]):
        ax.add_line(plt.Line2D([x0, x1], [y0, y1], color=color, lw=lw,
                               linestyle=style, zorder=zorder, solid_capstyle="round"))
    ax.annotate("", xy=pts[-1], xytext=pts[-2],
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw,
                                linestyle=style, mutation_scale=mutation_scale),
                zorder=zorder)

def fig_network():
    """Illustration of the DEM network internals: coordinate input, multi-scale
    Fourier features (grouped by role), the MLP, the hard-BC construction, and
    the physics-informed training loop (autodiff strain, energy density, MC
    integration, Adam/L-BFGS), with the backpropagation path closing the loop
    around the outside of the diagram so it crosses no other element."""
    MM = 1 / 25.4
    FS_TITLE, FS_EQ, FS_ANNOT, FS_SMALL = 9.2, 8.4, 7.8, 7.2
    C_FOURIER = "#6B4C9A"
    C_NEURON = "#0072B2"
    C_OUT = "#4A6FA5"
    C_PHYS = "#D55E00"
    C_OPT = "#009E73"
    C_LINE = "0.25"

    # YLIM enlarged (top and bottom) to give the Fourier-feature title, the
    # role captions now placed outside their boxes, and the widened
    # physics/optimizer chain enough canvas room without crowding.
    XLIM = (-1.8, 17.6)
    YLIM = (-1.0, 12.5)
    fig, ax = plt.subplots(
        figsize=(175 * MM, 175 * MM * (YLIM[1] - YLIM[0]) / (XLIM[1] - XLIM[0])))
    ax.set_xlim(*XLIM)
    ax.set_ylim(*YLIM)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.grid(False)

    Y0 = 7.6   # forward-pass row (input -> Fourier -> MLP -> output -> hard-BC)

    # -- (A) input -----------------------------------------------------------
    ax.add_patch(Circle((0.55, Y0), 0.34, fc="#EDEDED", ec="0.25", lw=1.2, zorder=4))
    ax.text(0.55, Y0, "$\\mathbf{x}$", ha="center", va="center", fontsize=FS_TITLE + 1, zorder=5)
    ax.text(0.55, Y0 - 1.15, "$(t)$ conditional", ha="center", fontsize=FS_SMALL,
            color="0.4", style="italic")

    # -- (B) Fourier features: two labeled sub-groups by role. Role captions
    #    ("macroscopic mode" / "wall-thickness gradients") are placed OUTSIDE
    #    each sub-box, in the clear gap between them (top) or below the
    #    whole group (bottom), instead of crammed against the inner bottom
    #    edge -- the prior layout let this text visually cross the box
    #    border. The outer dashed group box is enlarged to match.
    fx0, fx1 = 2.15, 4.30
    fcx = (fx0 + fx1) / 2
    grp_top_y = (Y0 + 1.05, Y0 + 2.70)     # coarse group span
    grp_bot_y = (Y0 - 2.70, Y0 - 1.05)     # fine group span
    groups = [
        (grp_top_y, 1, "coarse $\\sigma{=}1$", "macroscopic mode"),
        (grp_bot_y, 2, "fine $\\sigma\\in\\{4,12\\}$", "wall-thickness\ngradients"),
    ]
    all_fy = []
    dot_dx, dot_dy = 0.30, 0.30
    for (ylo, yhi), n_rows, tag, role in groups:
        ax.add_patch(FancyBboxPatch((fx0, ylo), fx1 - fx0, yhi - ylo,
                                    boxstyle="round,pad=0.02", fc="#F1ECF8",
                                    ec=C_FOURIER, lw=0.9, zorder=2))
        ax.text(fcx, yhi - 0.26, tag, ha="center", va="center", fontsize=FS_SMALL,
                color=C_FOURIER)
        dot_mid = (ylo + yhi) / 2 - 0.14
        row_ys = np.linspace(0, -(n_rows - 1) * dot_dy, n_rows) + dot_mid \
            + (dot_dy * (n_rows - 1) / 2 if n_rows > 1 else 0)
        for ry in np.atleast_1d(row_ys):
            for cxo in (-dot_dx / 2, dot_dx / 2):
                ax.add_patch(Circle((fcx + cxo, ry), 0.095, fc=C_FOURIER, alpha=0.88,
                                    ec="0.2", lw=0.6, zorder=4))
                all_fy.append(ry)
    # role captions sit OUTSIDE their box: the coarse-group caption in the
    # clear gap between the two sub-boxes, the fine-group caption below
    # the whole dashed group -- both fully clear of every box border.
    ax.text(fcx, (grp_top_y[0] + grp_bot_y[1]) / 2, groups[0][3],
            ha="center", va="center", fontsize=6.8, color="0.3", style="italic")
    ax.text(fcx, grp_bot_y[0] - 0.62, groups[1][3],
            ha="center", va="top", fontsize=6.8, color="0.3", style="italic",
            linespacing=1.3)
    ax.add_patch(FancyBboxPatch((fx0 - 0.12, grp_bot_y[0] - 0.12), fx1 - fx0 + 0.24,
                                grp_top_y[1] - grp_bot_y[0] + 0.24,
                                boxstyle="round,pad=0.02", fc="none",
                                ec=C_FOURIER, lw=1.1, linestyle=(0, (3, 2)), zorder=1))
    # Wrapped to two lines (was one long line whose right edge touched the
    # backpropagation loop's vertical segment) so the title's horizontal
    # footprint stays within the Fourier group, clear of the loop.
    fourier_title_y = grp_top_y[1] + 0.55
    ax.text(fcx, fourier_title_y, "multi-scale\nFourier features",
            ha="center", va="bottom", fontsize=FS_ANNOT, color=C_FOURIER,
            fontweight="bold", linespacing=1.3)
    ax.annotate("", xy=(fx0 - 0.12, Y0), xytext=(0.93, Y0),
                arrowprops=dict(arrowstyle="-|>", color=C_LINE, lw=1.2))

    # -- (C) MLP: 4 hidden layers -------------------------------------------
    n_show = 6
    spread = 2.0
    mlp_x0 = fx1 + 1.15
    layer_x = [mlp_x0 + 1.18 * i for i in range(4)]
    prev_x, prev_y = fx1 + 0.12, all_fy
    layer_ys = []
    for lx in layer_x:
        ys = list(np.linspace(Y0 + spread / 2, Y0 - spread / 2, n_show))
        layer_ys.append(ys)
        _mlp_connect(ax, prev_x, prev_y, lx, ys)
        _mlp_layer(ax, lx, ys, 0.125, C_NEURON)
        prev_x, prev_y = lx, ys
    mlp_box_top = Y0 + spread / 2 + 0.4
    mlp_box_x0, mlp_box_x1 = layer_x[0] - 0.42, layer_x[-1] + 0.42
    ax.add_patch(FancyBboxPatch((mlp_box_x0, Y0 - spread / 2 - 0.4),
                                mlp_box_x1 - mlp_box_x0, spread + 0.8,
                                boxstyle="round,pad=0.03", fc="#EAF1FA",
                                ec=C_NEURON, lw=1.1, zorder=0, alpha=0.65))
    ax.text(mlp_box_x0 + 0.15, mlp_box_top + 0.16,
            "$\\mathcal{N}_\\theta$:  MLP,  width 128 $\\times$ 4,  tanh",
            ha="left", va="bottom", fontsize=FS_ANNOT, color=C_NEURON, fontweight="bold")

    # -- raw output N_theta(x) ------------------------------------------------
    ox = layer_x[-1] + 1.15
    oys = [Y0 + 0.32, Y0, Y0 - 0.32]
    _mlp_connect(ax, layer_x[-1], layer_ys[-1], ox, oys, alpha=0.55)
    _mlp_layer(ax, ox, oys, 0.14, C_OUT)
    ax.text(ox, Y0 - 0.95, "$\\mathcal{N}_\\theta(\\mathbf{x})\\in\\mathbb{R}^3$",
            ha="center", fontsize=FS_SMALL, color=C_OUT)

    # -- (D) hard-BC construction ---------------------------------------------
    # Box moved further right of the output neurons and enlarged, so the
    # "hard KUBC, exact" caption line no longer runs behind the output
    # dots' connector lines, and the equation/caption have clear vertical
    # separation inside the box.
    hx, hw, hh = ox + 2.55, 2.95, 1.65
    ax.add_patch(FancyBboxPatch((hx - hw / 2, Y0 - hh / 2), hw, hh,
                                boxstyle="round,pad=0.09", fc="#FBE5D4",
                                ec="0.3", lw=1.15, zorder=3))
    ax.text(hx, Y0 + 0.34, "$\\mathbf{u}_\\theta=d(\\mathbf{x})\\,\\mathcal{N}_\\theta"
            "+\\bar\\varepsilon\\mathbf{x}$", ha="center", va="center", fontsize=FS_EQ)
    ax.text(hx, Y0 - 0.40, "hard KUBC, exact", ha="center", va="center",
            fontsize=FS_SMALL, color="0.35")
    ax.annotate("", xy=(hx - hw / 2 - 0.10, Y0), xytext=(ox + 0.20, Y0),
                arrowprops=dict(arrowstyle="-|>", color=C_LINE, lw=1.2))

    # -- (E)/(F) physics chain, descending below the hard-BC box --------------
    # Step spacing widened (1.5 -> 1.85 per stage) and the annotation
    # column pushed further right (+0.55 -> +0.90) so each side-caption no
    # longer visually merges with its equation's closing glyphs.
    px = hx
    steps = [
        (Y0 - 2.00, "$\\boldsymbol{\\varepsilon}=\\frac{1}{2}(\\nabla\\mathbf{u}+\\nabla\\mathbf{u}^T)$",
         "autodiff strain"),
        (Y0 - 3.85, "$\\psi(\\boldsymbol{\\varepsilon})=\\frac{1}{2}\\lambda(\\mathrm{tr}\\,\\boldsymbol{\\varepsilon})^2"
         "+\\mu\\,\\boldsymbol{\\varepsilon}\\!:\\!\\boldsymbol{\\varepsilon}$",
         "energy density"),
        (Y0 - 5.70, "$\\Pi(\\mathbf{u}_\\theta)\\approx V_f\\dfrac{1}{N}\\sum_i\\psi(\\boldsymbol{\\varepsilon}_i)$",
         "MC collocation,\nresampled per iteration"),
    ]
    box_w, box_h = 3.35, 0.95
    ann_x = px + box_w / 2 + 0.90   # aligned annotation column, right of the boxes
    yprev_bot = Y0 - hh / 2
    for yy, formula, caption in steps:
        ax.add_patch(FancyBboxPatch((px - box_w / 2, yy - box_h / 2), box_w, box_h,
                                    boxstyle="round,pad=0.07", fc="#FBE5D4",
                                    ec="0.3", lw=1.05, zorder=3))
        ax.text(px, yy, formula, ha="center", va="center", fontsize=FS_EQ)
        ax.annotate("", xy=(px, yy + box_h / 2 + 0.02), xytext=(px, yprev_bot - 0.06),
                    arrowprops=dict(arrowstyle="-|>", color=C_LINE, lw=1.2))
        # short leader from box edge to the aligned annotation column
        ax.plot([px + box_w / 2, ann_x - 0.06], [yy, yy], color=C_PHYS,
                lw=0.7, ls=(0, (1, 1.3)), zorder=2)
        ax.text(ann_x, yy, caption, ha="left", va="center", fontsize=FS_ANNOT,
                color=C_PHYS, style="italic", linespacing=1.25)
        yprev_bot = yy - box_h / 2

    # small MC point-cloud icon docked to the left of the integration box,
    # non-overlapping horizontal connector
    rng = np.random.default_rng(0)
    mc_y = steps[-1][0]
    cx, cy, rr = px - box_w / 2 - 1.15, mc_y, 0.55
    ang = rng.uniform(0, 2 * np.pi, 40); rad = rr * np.sqrt(rng.uniform(0, 1, 40))
    ax.scatter(cx + rad * np.cos(ang), cy + rad * np.sin(ang), s=5, color=C_PHYS,
              alpha=0.8, zorder=4)
    ax.add_patch(Circle((cx, cy), rr, fc="none", ec="0.4", lw=0.9,
                        linestyle=(0, (2, 2))))
    ax.text(cx, cy + rr + 0.20, "$\\Omega_s=\\{\\phi<0\\}$", ha="center", va="bottom",
            fontsize=FS_SMALL, color="0.35")
    ax.annotate("", xy=(px - box_w / 2 - 0.06, mc_y), xytext=(cx + rr + 0.08, mc_y),
                arrowprops=dict(arrowstyle="-|>", color=C_LINE, lw=1.05))

    # -- optimizer ---------------------------------------------------------
    # ly2 recomputed from the (now-widened) physics-chain bottom edge,
    # not a fixed offset from Y0, so it stays correctly clear of the last
    # step regardless of the chain spacing above; box height increased
    # for more internal padding between its two text lines.
    box_w2, box_h2 = 4.55, 1.50
    ly2 = yprev_bot - 0.65 - box_h2 / 2
    ax.add_patch(FancyBboxPatch((px - box_w2 / 2, ly2 - box_h2 / 2), box_w2, box_h2,
                                boxstyle="round,pad=0.08", fc="#DFEEDA",
                                ec=C_OPT, lw=1.25, zorder=3))
    ax.text(px, ly2 + 0.24, "Adam (resampled cloud)",
            ha="center", va="center", fontsize=FS_EQ, color="0.1")
    ax.text(px, ly2 - 0.24, "$\\rightarrow$ L-BFGS polish",
            ha="center", va="center", fontsize=FS_EQ, color="0.1")
    ax.annotate("", xy=(px, ly2 + box_h2 / 2 + 0.02), xytext=(px, yprev_bot - 0.06),
                arrowprops=dict(arrowstyle="-|>", color=C_LINE, lw=1.2))

    # -- (G) backprop: routed around the outside, crosses nothing ------------
    # enters the MLP box from its LEFT side, below the (left-aligned) title
    # row, so the arrow never crosses any text; arrowhead stops short of the
    # box border rather than touching it.
    left_x = -1.55
    fourier_title_top = fourier_title_y + 0.70  # 2-line title, was 0.35 for 1 line
    top_y = max(mlp_box_top, fourier_title_top) + 0.40
    opt_left = px - box_w2 / 2
    entry_y = Y0                      # mid-gap between the two Fourier groups
    drop_x = (fx1 + 0.12 + mlp_box_x0) / 2   # mid-gap between Fourier and MLP boxes
    path = [(opt_left, ly2), (left_x, ly2), (left_x, top_y),
            (drop_x, top_y), (drop_x, entry_y),
            (mlp_box_x0 - 0.10, entry_y)]
    _orth_arrow(ax, path, color=C_OPT, lw=1.35, style=(0, (5, 2.2)),
               mutation_scale=13, zorder=2)
    ax.text(left_x + 0.25, top_y + 0.20,
            "backpropagation:  $\\partial\\Pi/\\partial\\theta$",
            ha="left", va="bottom", fontsize=FS_ANNOT, color=C_OPT, style="italic")

    fig.subplots_adjust(left=0.005, right=0.995, top=0.98, bottom=0.02)
    save(fig, "fig2b_network", svg=True, extra_dpi=600)

# ---------------------------------------------------- Fig 8 (3D contours)
def _voxel_field_96(npz_path, N=96):
    """Rebuild the (N,N,N) per-element field from the exported FE element
    centroids and values (exact, no interpolation: centroids sit at
    (i+0.5)/N by construction of the voxel mesh generator)."""
    d = np.load(npz_path)
    idx = np.clip(np.rint(d["cell_xyz"] * N - 0.5).astype(int), 0, N - 1)
    val = np.full((N, N, N), np.nan)
    val[idx[:, 0], idx[:, 1], idx[:, 2]] = d["ENEL_ELEM"]
    return val


def _downsample_block_mean(val, factor):
    """Block-average a (N,N,N) field (NaN = void) down by an integer factor.
    A block is solid if any of its sub-cells is solid; its value is the mean
    over the solid sub-cells. This is a genuine reduction of the FE element
    data (not a resampled/interpolated visual), used only to keep the voxel
    render tractable -- matplotlib's Axes3D.voxels does not scale to the
    ~170,000 exposed faces of the native 96^3 thin-sheet mesh."""
    N = val.shape[0]
    n = N // factor
    v = val[:factor * n, :factor * n, :factor * n].reshape(
        n, factor, n, factor, n, factor)
    with np.errstate(invalid="ignore"):
        out = np.nanmean(v, axis=(1, 3, 5))
    return out


def _smooth_cell_geometry(npz_path, N=96, eps=1.0e-3):
    """Smooth surface reconstruction of a 96^3 FE voxel geometry: marching
    cubes on the solid indicator (padded, so the sheet's cut faces at the
    cube boundary are closed), with the per-element FE energy density
    trilinearly interpolated to the surface vertices. Display-side only:
    the analysis data are unchanged."""
    from skimage import measure
    from scipy.ndimage import map_coordinates
    val = _voxel_field_96(npz_path, N)
    mask = np.isfinite(val)
    vol = np.pad(mask.astype(float), 1)
    verts, faces, _, _ = measure.marching_cubes(vol, level=0.5)
    verts = (verts - 1.0) / N
    dens = np.nan_to_num(val) / eps**2
    vvals = map_coordinates(dens, (verts * N).T, order=1)
    return verts, faces, vvals


def _add_smooth_cell(ax, verts, faces, vvals, vmax, cmap_name="magma"):
    """Add the marching-cubes surface to a 3D axis, face-colored by the FE
    value with a simple directional-light lambert term for depth."""
    cmap = plt.get_cmap(cmap_name)
    fv = vvals[faces].mean(axis=1)
    fn = np.cross(verts[faces[:, 1]] - verts[faces[:, 0]],
                  verts[faces[:, 2]] - verts[faces[:, 0]])
    fn /= (np.linalg.norm(fn, axis=1, keepdims=True) + 1e-12)
    light = np.array([0.40, -0.50, 0.75])
    light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.clip(fn @ light, 0.0, 1.0)
    shade = 0.50 + 0.50 * np.clip(fn @ light, 0.0, 1.0)
    cols = cmap(np.clip(fv / vmax, 0.0, 1.0))[:, :3] * shade[:, None]
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    pc = Poly3DCollection(verts[faces],
                          facecolors=np.clip(cols, 0, 1), edgecolor="none")
    ax.add_collection3d(pc)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_zlim(0, 1)


def fig_contours_3d():
    """3D strain-energy-density contours on the actual FE geometry: uniform
    baseline versus the optimized graded cell, at the exact same view and
    color scale, using the real per-element FE data (fields_*.npz),
    reconstructed as a smooth surface from the 96^3 voxel geometry."""
    verts_u, faces_u, vv_u = _smooth_cell_geometry(N3 / "fields_uniform.npz")
    verts_g, faces_g, vv_g = _smooth_cell_geometry(N3 / "fields_graded.npz")
    vv_u = vv_u * 1e7
    vv_g = vv_g * 1e7
    vmax = np.percentile(np.concatenate([vv_u, vv_g]), 98)
    norm = Normalize(vmin=0, vmax=vmax)

    fig = plt.figure(figsize=(9.6, 4.7))
    fig.subplots_adjust(left=0.01, right=0.99, top=0.94, bottom=0.02, wspace=0.02)
    # NOTE (PRESENTATION POLISH): removed a pre-existing dangling duplicate
    # line here (same class of defect as above); fig_contours_3d() is not
    # regenerated this pass, this fix only lets the file parse.
    panels = [((verts_u, faces_u, vv_u), "(a) uniform $t=0.30$: baseline"),
              ((verts_g, faces_g, vv_g),
               "(b) optimized graded design")]
    for i, ((verts, faces, vvals), ttl) in enumerate(panels):
        ax = fig.add_subplot(1, 2, i + 1, projection="3d")
        _add_smooth_cell(ax, verts, faces, vvals, vmax)
        ax.set_title(ttl, fontsize=10)
        ax.set_box_aspect((1, 1, 1))
        ax.set_axis_off()
        ax.view_init(elev=22, azim=38)
    sm = plt.cm.ScalarMappable(cmap=plt.get_cmap("magma"), norm=norm)
    sm.set_array([])
    cax = fig.add_axes([0.32, 0.055, 0.36, 0.028])
    cb = fig.colorbar(sm, cax=cax, orientation="horizontal")
    cb.set_label("unit-normalized strain-energy density / $10^{-7}$", fontsize=9)
    cb.ax.tick_params(labelsize=8)
    save(fig, "fig8_stress_contours")

# ------------------------------------------------------------------- Fig 3
def fig3():
    vf = np.array([0.1287, 0.1933, 0.2911])
    # code_aster references: grid-averaged over the volume-calibrated ladders
    # (Table A.5), with the ladder half-range as the plotted uncertainty
    PN = json.load(open(N3 / "paper_numbers.json"))
    anchors = [PN["thickness"][k] for k in ("0.20", "0.30", "0.45")]
    fem = np.array([a["stats"]["mean"] for a in anchors])
    fem_err = np.array([a["stats"]["half_range"] for a in anchors])
    dem = np.array([a["dem"]["C1111"] for a in anchors])
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
    ax.errorbar(vf, fem, yerr=fem_err, fmt="o", color=C_FEM, ms=8, mec="white",
                mew=0.8, ecolor=C_FEM, elinewidth=1.2, capsize=3, zorder=4,
                label="voxel FEM (code_aster), grid-averaged")
    # Keep all three endpoint labels inside the axes.  The lowest point is
    # labelled above/right, the centre point below/right, and the highest
    # point below/left so neither boundary annotation is clipped.
    label_specs = [((6, 7), "left", "bottom"),
                   ((6, -10), "left", "top"),
                   ((-6, -10), "right", "top")]
    for (x, y), (offset, ha, va) in zip(zip(vf, fem), label_specs):
        ax.annotate(f"{y:.4f}", (x, y), textcoords="offset points",
                    xytext=offset, ha=ha, va=va, fontsize=8, color="0.25",
                    annotation_clip=True)
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
    # FE grid scatter of each anchor, the floor below which a deviation is
    # not attributable to the solver
    for x, e, f in zip(xpos, fem_err, fem):
        axb.plot([x - 0.48, x + 0.48], [100 * e / f] * 2, ls=":", lw=1.1,
                 color=C_FEM, zorder=3)
    axb.plot([], [], ls=":", lw=1.1, color=C_FEM, label="FE grid scatter")
    ymax = max(dev_dem.max(), dev_cond.max())
    axb.set_ylim(-1.5, ymax * 1.25 + 1)
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
    cb.ax.set_title("$t$", fontsize=9.5, pad=6)
    cb.ax.tick_params(labelsize=8)
    # (b) 3D surface render, colored by the real FE strain-energy density
    # (same data and colormap as Fig. 8, smooth marching-cubes geometry)
    verts_g, faces_g, vv_g = _smooth_cell_geometry(N3 / "fields_graded.npz")
    vmax_b = np.percentile(vv_g, 98)
    ax = fig.add_subplot(gs[0, 2], projection="3d")
    _add_smooth_cell(ax, verts_g, faces_g, vv_g, vmax_b)
    ax.set_title("(b)  optimized graded cell\n(FE strain energy density)",
                 fontsize=9, pad=0)
    ax.set_box_aspect((1, 1, 1))
    ax.set_axis_off()
    ax.view_init(elev=22, azim=38)
    # (c) prediction vs verification: DEM and FE rank the three designs
    # in opposite orders -- the central result of the case study
    ax = fig.add_subplot(gs[0, 3])
    PN = json.load(open(N3 / "paper_numbers.json"))
    e3 = PN["e3"]
    designs = ["uniform", "graded", "printable"]
    labels = ["uniform", "graded", "constr."]
    fem = [e3[d]["stats"]["mean"] for d in designs]
    fem_err = [e3[d]["stats"]["half_range"] for d in designs]
    dem = [e3[d]["dem"]["C1111"] for d in designs]
    xp = np.arange(3) * 0.9
    w = 0.34
    b1 = ax.bar(xp - w/2, dem, w, color=C_COND, alpha=0.85, zorder=2,
                label="DEM (mesh-free)")
    b2 = ax.bar(xp + w/2, fem, w, color=C_FEM, yerr=fem_err, capsize=3,
                ecolor="0.35", zorder=2, label="voxel FEM, energy")
    for bars in (b1, b2):
        for b in bars:
            ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.0025,
                    f"{b.get_height():.4f}", ha="center", fontsize=6.8,
                    color="0.15", rotation=0)
    for i in (1, 2):
        d = e3[designs[i]]
        ax.text(xp[i], 0.147,
                f"DEM ${d['dem_gain_pct']:+.1f}\\%$\nFEM ${d['gain_mean_pct']:+.1f}\\%$",
                ha="center", fontsize=8, color="0.15")
    ax.set_xticks(xp)
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("$C_{1111}$")
    ax.set_ylim(0, 0.162)
    ax.legend(loc="lower left", fontsize=7, framealpha=0.95)
    ax.set_title("(c)  iso-volume $V_f=0.19328$", fontsize=9.5)
    ax.grid(axis="y", alpha=0.25)
    ax.grid(axis="x", visible=False)
    save(fig, "fig4_e3_result")

# ------------------------------------------------------- Fig 5 (cross-family)
def fig_cross_family():
    """N3 cross-family gate: voxel-FE mesh ladder and DEM agreement for
    gyroid / primitive / diamond at matched continuum volume fraction."""
    S = json.load(open(N3 / "paper_numbers.json"))["families"]
    fams = ["primitive", "gyroid", "diamond"]
    labels = {"gyroid": "Gyroid", "primitive": "Primitive", "diamond": "Diamond"}
    cols = {"gyroid": C_COND, "primitive": C_ACC, "diamond": C_FEM}

    fig, (ax, axb) = plt.subplots(1, 2, figsize=(9.4, 3.7),
                                  gridspec_kw={"width_ratios": [1.3, 1]})
    # (a) FE ladder vs voxel size, with the DEM value as a dashed line
    for fam in fams:
        d = S[fam]
        rows = [r for r in d["rows"] if not r["excluded"]]
        h = np.array([1.0 / r["N"] for r in rows])
        c = np.array([r["C1111"] for r in rows])
        ax.plot(h, c, "o-", color=cols[fam], ms=5.5, lw=1.3, mec="white", mew=0.8,
                label=f"{labels[fam]}: voxel FE ladder")
        if d.get("dem"):
            ax.axhline(d["dem"]["C1111"], color=cols[fam], ls="--", lw=1.2, alpha=0.9)
            ax.text(0.0222, d["dem"]["C1111"], "DEM", fontsize=8,
                    color=cols[fam], va="bottom", ha="right")
    ax.set_xlabel("voxel size $h=1/N$")
    ax.set_ylabel("$C_{1111}$  (KUBC, $\\bar\\varepsilon_{11}$)")
    ax.set_xlim(0, 0.0235)
    ax.legend(loc="center left", fontsize=8)
    ax.set_title("(a)", loc="left", fontsize=10)

    # (b) DEM deviation from the grid-averaged FE reference, per family
    xpos = np.arange(len(fams))
    dev = [S[f]["dem"]["dev_pct_vs_mean"] for f in fams]
    scat = [S[f]["stats"]["scatter_pct"] for f in fams]
    axb.axhspan(-5, 5, color="0.92", zorder=0)
    axb.axhline(0, color="0.4", lw=0.8, zorder=1)
    bars = axb.bar(xpos, dev, 0.5, color=[cols[f] for f in fams], zorder=2)
    for b, v, s in zip(bars, dev, scat):
        axb.text(b.get_x() + b.get_width() / 2, v + 0.25,
                 f"{v:+.1f}%", ha="center", fontsize=8.5, color="0.15")
        axb.plot([b.get_x(), b.get_x() + b.get_width()], [s, s], ls=":", lw=1.1,
                 color="0.3", zorder=3)
    axb.plot([], [], ls=":", lw=1.1, color="0.3", label="FE grid scatter")
    axb.set_xticks(xpos)
    axb.set_xticklabels([labels[f] for f in fams], fontsize=9)
    axb.set_ylabel("DEM deviation from FE reference  [%]")
    axb.set_ylim(-1.5, max(dev) * 1.35 + 1)
    axb.legend(loc="upper left", fontsize=8)
    axb.set_title("(b)", loc="left", fontsize=10)
    axb.grid(axis="x", visible=False)
    fig.tight_layout(w_pad=2.0)
    save(fig, "fig5_cross_family")


# ------------------------------------------------- Fig 6 (field verification)
def _masked(a):
    return np.ma.masked_invalid(a)


def _upsample_field(a, k=4):
    """Display-side bilinear upscaling of a node/cell field with NaN voids
    (mask re-applied after interpolation). Rendering only; the underlying
    FE/DEM data are untouched."""
    from scipy.ndimage import zoom
    m = np.isfinite(a)
    z = zoom(np.where(m, a, 0.0).astype(float), k, order=1)
    zm = zoom(m.astype(float), k, order=1)
    return np.where(zm > 0.55, z, np.nan)


def fig_field_verification():
    """Field-level comparison of the mesh-free solver against voxel FE on the
    mid-plane z=0.5, for the family the solver handles best (gyroid) and worst
    (primitive). Energy density is normalized to unit applied strain, so the
    FE runs (eps=1e-3) and DEM runs (eps=1e-2) are directly comparable."""
    rows = [("gyroid", "Gyroid", "slice_fe_uniform.npz", "slice_dem_gyroid.npz",
             "slice_dem_gyroid_nodes.npz"),
            ("primitive", "Primitive", "slice_fe_primitive.npz",
             "slice_dem_primitive.npz", "slice_dem_primitive_nodes.npz")]
    fig, axes = plt.subplots(2, 3, figsize=(9.6, 6.4))
    for r, (key, label, fe_f, dem_f, demn_f) in enumerate(rows):
        fe = np.load(N3 / fe_f)
        dem = np.load(N3 / dem_f)
        demn = np.load(N3 / demn_f)

        e_fe = _upsample_field(fe["ENEL"])
        e_dem = _upsample_field(np.where(dem["inside"], dem["enel"], np.nan))
        vmax = np.nanpercentile(np.concatenate([e_fe.ravel(), e_dem.ravel()]), 99)

        for c, (arr, ttl) in enumerate([(e_fe, "voxel FE"), (e_dem, "mesh-free DEM")]):
            ax = axes[r, c]
            im = ax.pcolormesh(np.linspace(0, 1, arr.shape[0]),
                               np.linspace(0, 1, arr.shape[1]),
                               _masked(arr).T, cmap="magma", vmin=0, vmax=vmax,
                               shading="auto", rasterized=True)
            ax.set_title(f"({chr(97 + 3*r + c)}) {label}: {ttl}", fontsize=9.5)
            ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
            ax.grid(False)
            if c == 1:
                cb = fig.colorbar(im, ax=axes[r, :2].tolist(), shrink=0.86,
                                  pad=0.015, aspect=16)
                cb.set_label("strain energy density", fontsize=8.5)
                cb.ax.tick_params(labelsize=7.5)

        # difference on the shared node grid, where both solutions exist
        both = np.isfinite(fe["ENEL"]) & demn["inside"]
        diff = np.where(both, (demn["enel"] - fe["ENEL"])
                        / np.nanmean(fe["ENEL"][both]) * 100, np.nan)
        diff = _upsample_field(diff)
        lim = np.nanpercentile(np.abs(diff), 98)
        ax = axes[r, 2]
        im = ax.pcolormesh(np.linspace(0, 1, diff.shape[0]),
                           np.linspace(0, 1, diff.shape[1]),
                           _masked(diff).T, cmap="RdBu_r", vmin=-lim, vmax=lim,
                           shading="auto", rasterized=True)
        ax.set_title(f"({chr(97 + 3*r + 2)}) DEM $-$ FE", fontsize=9.5)
        ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
        ax.grid(False)
        cb = fig.colorbar(im, ax=ax, shrink=0.86, pad=0.03, aspect=16)
        cb.set_label("% of mean density", fontsize=8.5)
        cb.ax.tick_params(labelsize=7.5)
    save(fig, "fig6_field_verification")


# --------------------------------------------------- Fig 7 (design mechanism)
def fig_design_mechanism():
    """What the optimizer actually did: it polarizes the cell rather than
    equalizing it. Energy density of the uniform and optimized cells at the same
    scale, and the Lorenz curve of strain energy against material."""
    fu = np.load(N3 / "slice_fe_uniform.npz")
    fg = np.load(N3 / "slice_fe_graded.npz")
    stats = json.load(open(N3 / "field_stats.json"))

    fig = plt.figure(figsize=(10.2, 3.5))
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 1.15], wspace=0.3)
    vmax = np.nanpercentile(np.concatenate([fu["ENEL"].ravel(), fg["ENEL"].ravel()]), 99)
    for i, (d, ttl) in enumerate([(fu, "uniform $t=0.30$"), (fg, "optimized graded")]):
        ax = fig.add_subplot(gs[0, i])
        enel = _upsample_field(d["ENEL"])
        im = ax.pcolormesh(np.linspace(0, 1, enel.shape[0]),
                           np.linspace(0, 1, enel.shape[1]),
                           _masked(enel).T, cmap="magma", vmin=0, vmax=vmax,
                           shading="auto", rasterized=True)
        ax.set_title(f"({chr(97+i)}) {ttl}", fontsize=9.5)
        ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
        if i == 1:
            cb = fig.colorbar(im, ax=ax, shrink=0.88, pad=0.03, aspect=16)
            cb.set_label("strain energy density", fontsize=8.5)
            cb.ax.tick_params(labelsize=7.5)

    ax = fig.add_subplot(gs[0, 2])
    for key, lab, col in (("uniform", "uniform $t=0.30$", C_FEM),
                          ("graded", "optimized graded", C_ACC)):
        L = stats[key]["lorenz"]
        ax.plot(L["material"], L["energy"], lw=1.8, color=col, label=lab)
    ax.plot([0, 1], [0, 1], ls=":", lw=1.0, color="0.5", label="uniformly stressed")
    ax.set_xlabel("cumulative share of material\n(least loaded first)")
    ax.set_ylabel("cumulative share of strain energy")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.legend(loc="upper left", fontsize=8)
    ax.set_title("(c)", loc="left", fontsize=10)
    ax.text(0.97, 0.06,
            f"top 20% of material carries\n"
            f"{stats['uniform']['top20_energy_pct']:.0f}% (uniform) vs "
            f"{stats['graded']['top20_energy_pct']:.0f}% (graded)",
            transform=ax.transAxes, ha="right", fontsize=8, color="0.25")
    save(fig, "fig7_design_mechanism")


# --------------------------------------------- Fig 9 (mesh convergence)
def fig_mesh_convergence():
    """Appendix figure: convergence of the volume-calibrated voxel-FE
    ladders on the Hill-Mandel energy basis (filled markers), against the
    loaded-face reaction shortcut (hollow markers), for every reference in
    Table tab:mesh. All values from paper_numbers.json (same source as the
    consistency checker)."""
    PN = json.load(open(N3 / "paper_numbers.json"))
    ladders = [
        ("Gyroid $t=0.20$", PN["thickness"]["0.20"], "#8CD0D8"),
        ("Gyroid $t=0.30$", PN["thickness"]["0.30"], C_FEM),
        ("Gyroid $t=0.45$", PN["thickness"]["0.45"], "#005838"),
        ("Optimized graded", PN["e3"]["graded"], C_ACC),
        ("Constrained variant", PN["e3"]["printable"], C_DEM),
        ("Primitive", PN["families"]["primitive"], C_COND),
        ("Diamond", PN["families"]["diamond"], "#6A3D9A"),
    ]
    fig, (ax, axb) = plt.subplots(1, 2, figsize=(9.6, 4.8),
                                  gridspec_kw={"width_ratios": [1.25, 1]})

    for label, d, col in ladders:
        rows = [r for r in d["rows"] if not r["excluded"]]
        N = np.array([r["N"] for r in rows])
        c = np.array([r["C1111"] for r in rows])
        mean = float(d["stats"]["mean"])
        ax.plot(N, c, "o-", color=col, ms=5, lw=1.2, mec="white", mew=0.7,
                label=label)
        ax.axhline(mean, color=col, ls=":", lw=0.9, alpha=0.6)
        dev = (c / mean - 1) * 100
        cf = np.array([r["C1111_face"] for r in rows])
        devf = (cf / mean - 1) * 100
        axb.plot(N, dev, "o", color=col, ms=5, mec="white", mew=0.7,
                 label=label if label.startswith(("Gyroid $t=0.20",)) else None)
        axb.plot(N, devf, "o", mfc="none", mec=col, ms=5.5, mew=1.1)

    ax.set_xlabel("voxel grid $N$ (volume-calibrated)")
    ax.set_ylabel("$C_{1111}$  (energy basis)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2,
              fontsize=7.2, frameon=False, columnspacing=0.8,
              handletextpad=0.4)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2, fontsize=8.2, frameon=False, columnspacing=0.8, handletextpad=0.4)
    ax.set_title("(a)  FE ladders, energy basis", loc="left", fontsize=10)

    axb.axhspan(-1, 1, color="0.92", zorder=0)
    axb.axhline(0, color="0.4", lw=0.8, zorder=1)
    axb.set_xlabel("voxel grid $N$")
    axb.set_ylabel("deviation from ladder mean  [%]")
    axb.set_title("(b)  energy vs loaded-face shortcut", loc="left", fontsize=10)
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], marker="o", ls="", color="0.3",
                      label="energy basis (this paper)"),
               Line2D([], [], marker="o", mfc="none", mec="0.3", ls="",
                      label="loaded-face reaction sum"),
               Line2D([], [], color="0.3", ls=":", label="ladder mean")]
    axb.legend(handles=handles, loc="upper center",
               bbox_to_anchor=(0.5, -0.18), ncol=1, fontsize=7.2,
               frameon=False, handletextpad=0.5)
    axb.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=1, fontsize=8.2, frameon=False, handletextpad=0.5)
    axb.set_ylim(-14, 18)
    fig.subplots_adjust(left=0.085, right=0.99, top=0.90, bottom=0.31,
                        wspace=0.30)
    fig.subplots_adjust(left=0.085, right=0.99, top=0.90, bottom=0.31, wspace=0.30)
    save(fig, "fig9_mesh_convergence")


if __name__ == "__main__":
    # PRESENTATION POLISH: only regenerate the two diagram figures this
    # pass touches (rendered Figure 2 = fig2b_network via fig_network(),
    # rendered Figure 3 = fig2_pipeline via fig2()). No other figure is
    # regenerated here.
    fig2(); fig_network()
    print("figures written to", FIG)
