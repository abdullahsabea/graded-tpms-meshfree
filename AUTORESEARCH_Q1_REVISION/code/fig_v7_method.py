"""Reproducible vector redraw of Fig. 14 (VG-MM workflow diagram).

Regenerates fig14_method_diagram.pdf/.png directly into
PRESENTATION_FINAL/manuscript/figures/. Pure matplotlib vector drawing
(no generative imagery). Branch structure follows r2_arms.py::run_arm
exactly (see PRESENTATION_CHANGELOG.md for the box-by-box justification):

  * baseline FE(64^3) of the uniform design is call 1 of the 26-call budget;
  * each of the 2 sweeps x 12 modes = 24 checkpoints: the frozen conditional
    DEM surrogate ranks the 9 grid trials for that mode (arm.proposal_vgmm),
    the top-scored NON-incumbent trial is selected, and ONLY that trial is
    FE-evaluated at 64^3 (one budget call per checkpoint -> 24 calls);
  * accept iff FE(proposal) is strictly greater than the FE-best incumbent
    (r["value"] > best_FE in run_arm), else retain incumbent;
  * after 24 checkpoints, 1 (baseline) + 24 (checkpoints) = 25 calls have
    been spent; the 26th call is the reserved final confirmation FE(96^3)
    of the incumbent (winner_confirm_96) -- never an extra search call.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.path import Path
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "MATERIALS_DESIGN_TRANSFER", "manuscript", "figures")

plt.rcParams.update({
    "font.size": 12, "pdf.fonttype": 42, "ps.fonttype": 42,
    "font.family": "serif", "font.serif": ["STIXGeneral", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "svg.fonttype": "none",
})

DEM_FC, DEM_EC = "#FDE3D0", "#D55E00"   # frozen conditional DEM surrogate
FE_FC, FE_EC = "#DCEEF7", "#0072B2"     # volume-calibrated voxel FE
ST_FC, ST_EC = "#EAEAEA", "#555555"     # bookkeeping / control logic
DEC_FC, DEC_EC = "#FFFFFF", "#333333"   # decision nodes

FS = 13.5       # box/diamond body text
FS_LAB = 13.0   # Yes/No branch labels

BW, BH = 1.62, 0.85   # standard box width/height


def box(ax, x, y, w, h, text, fc, ec, fs=FS):
    p = mpatches.FancyBboxPatch((x, y), w, h,
                                 boxstyle="round,pad=0.045,rounding_size=0.07",
                                 fc=fc, ec=ec, lw=1.3)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
             fontsize=fs, linespacing=1.35)
    return dict(cx=x + w / 2, cy=y + h / 2, x0=x, x1=x + w, y0=y, y1=y + h)


def diamond(ax, cx, cy, hw, hh, text, fc=DEC_FC, ec=DEC_EC, fs=FS):
    verts = [(cx, cy + hh), (cx + hw, cy), (cx, cy - hh), (cx - hw, cy)]
    ax.add_patch(mpatches.Polygon(verts, closed=True, fc=fc, ec=ec, lw=1.3))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs,
            linespacing=1.3)
    return dict(cx=cx, cy=cy, top=(cx, cy + hh), bot=(cx, cy - hh),
                left=(cx - hw, cy), right=(cx + hw, cy))


def orth_arrow(ax, pts, col="k", lw=1.3, ls="-"):
    """Multi-vertex orthogonal connector with a single arrowhead at pts[-1]."""
    path = Path(pts, [Path.MOVETO] + [Path.LINETO] * (len(pts) - 1))
    ax.add_patch(mpatches.FancyArrowPatch(path=path, arrowstyle="-|>",
                                           mutation_scale=12, lw=lw,
                                           color=col, ls=ls,
                                           shrinkA=0, shrinkB=0,
                                           joinstyle="miter",
                                           capstyle="butt"))


def orth_line(ax, pts, col="k", lw=1.3, ls="-"):
    """Multi-vertex orthogonal connector with NO arrowhead (feeder line)."""
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=col, lw=lw, ls=ls, solid_joinstyle="miter")


def label(ax, x, y, text, col="k"):
    ax.text(x, y, text, ha="center", va="center", fontsize=FS_LAB,
            color=col, fontweight="bold", linespacing=1.2,
            bbox=dict(fc="white", ec="none", pad=0.6))


def make():
    fig = plt.figure(figsize=(8.1, 8.3))
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_xlim(-0.95, 7.30)
    ax.set_ylim(-1.55, 7.10)
    ax.set_aspect("equal")
    ax.axis("off")

    # ---------------- Row 1: initialization -> DEM ranking -> selection -> FE
    GAP = 0.18
    x0 = 0.20
    b1 = box(ax, x0, 5.65, BW, BH,
              "Start at uniform\n$\\theta=0$; voxel FE,\n$64^3$ (1 query)",
              ST_FC, ST_EC)
    b2 = box(ax, x0 + (BW + GAP), 5.65, BW, BH,
              "Frozen local-\nthickness score\nranks 9 trials",
              DEM_FC, DEM_EC)
    b3 = box(ax, x0 + 2 * (BW + GAP), 5.65, BW, BH,
              "Select top\nnon-incumbent\ntrial $\\to\\theta'$",
              ST_FC, ST_EC)
    b4 = box(ax, x0 + 3 * (BW + GAP), 5.65, BW, BH,
              "Voxel FE of\nthe proposal,\n$64^3$ (1 query)",
              FE_FC, FE_EC)

    orth_arrow(ax, [(b1["x1"], b1["cy"]), (b2["x0"], b2["cy"])])
    orth_arrow(ax, [(b2["x1"], b2["cy"]), (b3["x0"], b3["cy"])])
    orth_arrow(ax, [(b3["x1"], b3["cy"]), (b4["x0"], b4["cy"])])

    # ---------------- Decision 1: does FE stiffness improve? (below b3)
    d1 = diamond(ax, b3["cx"], 4.35, 1.05, 0.75,
                 "FE $C_{1111}$ above\nFE incumbent?")
    orth_arrow(ax, [(b4["cx"], b4["y0"]), (b4["cx"], d1["cy"]), d1["right"]])

    # Yes -> update incumbent, straight down from the bottom vertex
    upd = box(ax, d1["bot"][0] - BW / 2, 2.35, BW, BH,
               "Update\nincumbent\n($\\theta\\leftarrow\\theta'$)",
               ST_FC, ST_EC)
    orth_arrow(ax, [d1["bot"], (upd["cx"], upd["y1"])])
    label(ax, d1["bot"][0] + 0.62, (d1["bot"][1] + upd["y1"]) / 2,
          "Yes", col="#0B6B00")

    # No -> retain incumbent, left then down from the left vertex
    ret_cx = d1["left"][0] - 1.35
    ret = box(ax, ret_cx - BW / 2, 2.35, BW, BH,
               "Retain\nincumbent", ST_FC, ST_EC)
    orth_arrow(ax, [d1["left"], (ret["cx"], d1["left"][1]),
                    (ret["cx"], ret["y1"])])
    label(ax, (d1["left"][0] + ret["cx"]) / 2, d1["left"][1] + 0.30,
          "No", col="#8A2BE2")

    # ---------------- Rejoin, then decision 2: checkpoint/budget
    d2cx = (upd["cx"] + ret["cx"]) / 2
    collector_y = ret["y0"] - 0.42
    d2 = diamond(ax, d2cx, collector_y - 0.80, 1.25, 0.80,
                 "All 24\ncheckpoints\ndone?")
    orth_line(ax, [(ret["cx"], ret["y0"]), (ret["cx"], collector_y),
                   (d2cx, collector_y)])
    orth_line(ax, [(upd["cx"], upd["y0"]), (upd["cx"], collector_y),
                   (d2cx, collector_y)])
    orth_arrow(ax, [(d2cx, collector_y), d2["top"]])

    # No -> loop back up to Row-1 DEM-ranking box (next checkpoint)
    rail_x = -0.55
    rail_y_top = 6.75
    orth_arrow(ax, [d2["left"], (rail_x, d2["left"][1]),
                    (rail_x, rail_y_top), (b2["cx"], rail_y_top),
                    (b2["cx"], b2["y1"])],
               col="#555555", ls=(0, (3.2, 2.2)))
    label(ax, (d2["left"][0] + rail_x) / 2, d2["left"][1] + 0.42,
          "No: next\ncheckpoint", col="#555555")

    # Yes -> final 96^3 confirmation, then return
    conf = box(ax, d2["bot"][0] - BW / 2, d2["bot"][1] - 0.33 - BH, BW, BH,
                "Re-evaluate\nincumbent,\n$96^3$ (1 query)",
                FE_FC, FE_EC)
    orth_arrow(ax, [d2["bot"], (d2["cx"], conf["y1"])])
    label(ax, d2["bot"][0] + 0.68, (d2["bot"][1] + conf["y1"]) / 2,
          "Yes", col="#0B6B00")

    ret2 = box(ax, conf["x1"] + 0.30, conf["y0"], BW + 0.15, BH,
                "Return design;\nFE gain over uniform\nat $64^3$ and $96^3$",
                ST_FC, ST_EC)
    orth_arrow(ax, [(conf["x1"], conf["cy"]), (ret2["x0"], ret2["cy"])])

    fig.savefig(os.path.join(OUT, "fig_v7_method.pdf"),
                bbox_inches="tight", pad_inches=0.10)
    fig.savefig(os.path.join(OUT, "fig_v7_method.png"), dpi=300,
                bbox_inches="tight", pad_inches=0.10)
    plt.close(fig)
    print("wrote fig14_method_diagram.pdf/.png")


if __name__ == "__main__":
    make()
