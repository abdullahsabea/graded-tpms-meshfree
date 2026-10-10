"""v7 network figure: the archived fig_network() drawing with corrections
checked against the code (research/n3/e3_conditional.py):

* t is appended raw after the Fourier features, z = [sin(xB), cos(xB), t];
  the old drawing fed only x and labelled t vaguely as "(t) conditional";
* network weights are written w (theta is the paper's design vector);
* interpretive role captions ("macroscopic mode", "wall-thickness gradients")
  removed: not verified;
* L-BFGS polish is marked as used for the single-thickness models only.
"""
import re
from pathlib import Path

import numpy as np
import v7_style as S
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle
from matplotlib.collections import LineCollection

SRC = S.Q1 / "EABE_PRESENTATION_POLISH" / "code" / "make_figs_v2_POLISH.py"
src = SRC.read_text(encoding="utf-8")
a = src.index("def _mlp_layer")
b = src.index("def _voxel_field_96")
code = src[a:b]

REPL = [
    # remove vague conditional label under x
    ('    ax.text(0.55, Y0 - 1.15, "$(t)$ conditional", ha="center", fontsize=FS_SMALL,\n'
     '            color="0.4", style="italic")\n', ''),
    # remove interpretive role captions
    ('    ax.text(fcx, (grp_top_y[0] + grp_bot_y[1]) / 2, groups[0][3],\n'
     '            ha="center", va="center", fontsize=6.8, color="0.3", style="italic")\n', ''),
    ('    ax.text(fcx, grp_bot_y[0] - 0.62, groups[1][3],\n'
     '            ha="center", va="top", fontsize=6.8, color="0.3", style="italic",\n'
     '            linespacing=1.3)\n', ''),
    # notation: network has no theta subscript; weights are w
    ('"$\\\\mathcal{N}_\\\\theta$:  MLP,  width 128 $\\\\times$ 4,  tanh"',
     '"$\\\\mathcal{N}$:  MLP,  width 128 $\\\\times$ 4,  tanh"'),
    ('"$\\\\mathcal{N}_\\\\theta(\\\\mathbf{x})\\\\in\\\\mathbb{R}^3$"',
     '"$\\\\mathcal{N}(\\\\mathbf{x},t)\\\\in\\\\mathbb{R}^3$"'),
    ('"$\\\\mathbf{u}_\\\\theta=d(\\\\mathbf{x})\\\\,\\\\mathcal{N}_\\\\theta"\n'
     '            "+\\\\bar\\\\varepsilon\\\\mathbf{x}$"',
     '"$\\\\mathbf{u}=d(\\\\mathbf{x})\\\\,\\\\mathcal{N}"\n'
     '            "+\\\\bar\\\\varepsilon\\\\mathbf{x}$"'),
    ('"$\\\\Pi(\\\\mathbf{u}_\\\\theta)\\\\approx V_f', '"$\\\\Pi(\\\\mathbf{u})\\\\approx V_f'),
    ('"backpropagation:  $\\\\partial\\\\Pi/\\\\partial\\\\theta$"',
     '"backpropagation:  $\\\\partial\\\\Pi/\\\\partial\\\\mathbf{w}$  (network weights)"'),
    ('"Adam (resampled cloud)"', '"Adam, resampled cloud"'),
    ('"$\\\\rightarrow$ L-BFGS polish"', '"+ L-BFGS (single-$t$ models)"'),
    # save under the v7 name in the manuscript figure folder
    ('    save(fig, "fig2b_network", svg=True, extra_dpi=600)\n',
     '    _add_t_input(ax, Y0, fx0, layer_x, spread)\n    S.save(fig, "fig_v7_network")\n'),
]
for old, new in REPL:
    assert old in code, old[:70]
    code = code.replace(old, new)


def _add_t_input(ax, Y0, fx0, layer_x, spread):
    """t enters the MLP directly (appended raw after the Fourier features)."""
    ty = Y0 - 3.55
    ax.add_patch(Circle((0.55, ty), 0.34, fc="#EDEDED", ec="0.25", lw=1.2, zorder=4))
    ax.text(0.55, ty, "$t$", ha="center", va="center", fontsize=10.2, zorder=5)
    ax.text(0.55, ty - 0.62, "thickness, appended raw", ha="center", va="top",
            fontsize=7.0, color="0.35", style="italic")
    mlp_bot = Y0 - spread / 2 - 0.4
    x_in = layer_x[0] - 0.05
    ax.plot([0.93, x_in], [ty, ty], color="0.25", lw=1.2, zorder=2)
    ax.annotate("", xy=(x_in, mlp_bot - 0.06), xytext=(x_in, ty),
                arrowprops=dict(arrowstyle="-|>", color="0.25", lw=1.2))


ns = dict(np=np, plt=plt, FancyBboxPatch=FancyBboxPatch, Circle=Circle,
          LineCollection=LineCollection, S=S, _add_t_input=_add_t_input)
exec(compile(code, str(SRC), "exec"), ns)
ns["fig_network"]()
