"""v7 Fig. 1: the five designs of the study, rendered from the exact analytic
thickness fields of the body-fitted meshes, coloured by local thickness t,
with the KUBC and periodic gains from the body-fitted solves underneath."""
import json
import sys

import numpy as np
from PIL import Image

import v7_style as S
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize

sys.path.insert(0, str(S.ROOT / "research" / "n3" / "conforming"))
sys.path.insert(0, str(S.HERE))
from make_conforming_mesh import t_field  # noqa: E402  (same fields as the PBC meshes)
from render3d import F_gyroid, cell_surface, render  # noqa: E402

REN = S.Q1 / "_deep_review" / "render3d"
KEYMAP = {"uniform": "uniform", "band": "printable", "vgmm": "vgmm", "fullfe": "fullfe", "graded": "graded"}
NUM = json.loads((S.HERE / "v7_numbers.json").read_text())
CLIM = (0.12, 0.55)


def make_renders(force=False):
    meta = {}
    for k in S.ORDER:
        out = REN / f"v7_design_{k}.png"
        tf = t_field(KEYMAP[k])
        surf = cell_surface(F_gyroid, tf)
        surf["t"] = tf(*surf.points.T)
        g = (np.arange(120) + 0.5) / 120
        X, Y, Z = np.meshgrid(g, g, g, indexing="ij")
        t = tf(X, Y, Z)
        solid = np.abs(F_gyroid(X, Y, Z)) <= t
        meta[k] = dict(t_p5=float(np.percentile(t[solid], 5)), t_p95=float(np.percentile(t[solid], 95)))
        if force or not out.exists():
            render(surf, out, scalars="t", cmap="viridis", clim=CLIM, size=1300)
        print(k, meta[k])
    (REN / "v7_design_meta.json").write_text(json.dumps(meta, indent=1))
    return meta


def compose(meta):
    fig = plt.figure(figsize=(S.FULL_W, 2.12))
    w, gap, x0 = 0.188, 0.008, 0.01
    for i, k in enumerate(S.ORDER):
        d = S.DES[k]
        ax = fig.add_axes([x0 + i * (w + gap), 0.285, w, 0.635])
        ax.imshow(np.asarray(Image.open(REN / f"v7_design_{k}.png").convert("RGB")), interpolation="lanczos")
        ax.set_axis_off()
        ax.set_title(f"({'abcde'[i]}) {d['short']}", fontsize=8.2, color=d["c"], pad=2, fontweight="bold")
        lo, hi = meta[k]["t_p5"], meta[k]["t_p95"]
        trange = f"$t={lo:.2f}$" if hi - lo < 1e-3 else f"$t\\in[{lo:.2f},{hi:.2f}]$"
        gk, gp = NUM["gain_kubc"][k], NUM["gain_pbc"][k]
        txt = f"{trange}\nreference" if k == "uniform" else (
            f"{trange}\nKUBC ${gk:+.1f}\\%$   PBC ${gp:+.1f}\\%$")
        fig.text(x0 + i * (w + gap) + w / 2, 0.275, txt, ha="center", va="top", fontsize=7.2,
                 linespacing=1.25)
    cax = fig.add_axes([0.30, 0.075, 0.40, 0.035])
    cb = fig.colorbar(ScalarMappable(Normalize(*CLIM), cmap="viridis"), cax=cax, orientation="horizontal",
                      ticks=[0.12, 0.2, 0.3, 0.4, 0.55])
    cb.set_label("local sheet thickness parameter $t$  (wall 0.34–1.90 mm at a 15 mm cell)", fontsize=7.2, labelpad=2)
    cb.ax.tick_params(labelsize=7, length=2)
    cb.outline.set_linewidth(0.5)
    S.save(fig, "fig_v7_designs", png_dpi=450)


if __name__ == "__main__":
    compose(make_renders(force="--force" in sys.argv))
