"""WP-A9 (D4): slice-averaged thickness and solid fraction along x1, x2, x3 for
the five PBC designs, using the exact analytic fields of the body-fitted meshes.
Loaded faces under eps_bar_11: x1 = 0, 1."""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "AUTORESEARCH_Q1_REVISION" / "code"))
import v7_style as VS
import matplotlib.pyplot as plt
sys.path.insert(0, str(ROOT / "research" / "n3" / "conforming"))
from make_conforming_mesh import F, t_field
DES = [("uniform", "Uniform $t=0.30$"), ("printable", "Band-and-smoothness-restricted"),
       ("vgmm", "VG-MM (seed 11)"), ("fullfe", "FE-scored coordinate search"),
       ("graded", "Unconstrained graded")]
n = 160
g = (np.arange(n) + 0.5) / n
X, Y, Z = np.meshgrid(g, g, g, indexing="ij")
Fv = np.abs(F(X, Y, Z))
res, prof = {}, {}
for key, lab in DES:
    t = t_field(key)(X, Y, Z)
    solid = Fv <= t
    r = {"Vf_grid": float(solid.mean())}
    p = {}
    for ax in range(3):
        oth = tuple(a for a in range(3) if a != ax)
        tm = t.mean(axis=oth)                                   # plane-mean t
        ts = (t * solid).sum(axis=oth) / solid.sum(axis=oth)    # mean t on solid
        sf = solid.mean(axis=oth)                               # solid area fraction
        p[ax] = (tm, ts, sf)
        near = (g < 0.1) | (g > 0.9)
        r[f"x{ax+1}"] = {"t_plane_near_faces": float(tm[near].mean()), "t_plane_core": float(tm[~near].mean()),
                         "solid_share_near_faces": float(solid.mean(axis=oth)[near].sum() / sf.sum()),
                         "t_plane_min": float(tm.min()), "t_plane_max": float(tm.max())}
    tt = t[solid]
    r["t_on_solid_p5_p95"] = [float(np.percentile(tt, 5)), float(np.percentile(tt, 95))]
    r["frac_at_lower_bound"] = float(np.mean(t <= t.min() + 1e-9)) if key != "uniform" else 0.0
    res[key], prof[key] = r, p
    print(key, json.dumps(r, indent=None))
base = {ax: res["uniform"][f"x{ax+1}"]["solid_share_near_faces"] for ax in range(3)}
print("\nsolid share within 0.1 of face pair, relative to uniform (uniform = 0.200 by construction of slab width):")
for key, _ in DES:
    print(f"  {key:10s}", "  ".join(f"x{ax+1}: {res[key][f'x{ax+1}']['solid_share_near_faces']/base[ax]:.3f}" for ax in range(3)))
json.dump(res, open("a9_thickness_profiles.json", "w"), indent=2)
fig, axs = plt.subplots(2, 3, figsize=(VS.FULL_W, 3.9), sharex=True, sharey="row")
cols = [VS.DES[k]["c"] for k in VS.ORDER]
for (key, _), c, vk in zip(DES, cols, VS.ORDER):
    lab = VS.DES[vk]["short"]
    for ax in range(3):
        tm, ts, sf = prof[key][ax]
        axs[0, ax].plot(g, tm, color=c, lw=1.1, ls="--" if key == "uniform" else "-", label=lab)
        axs[1, ax].plot(g, sf, color=c, lw=1.1, ls="--" if key == "uniform" else "-")
for ax in range(3):
    for r_ in range(2):
        axs[r_, ax].axvspan(0, 0.1, color="0.9", zorder=0); axs[r_, ax].axvspan(0.9, 1, color="0.9", zorder=0)
    axs[1, ax].set_xlabel(f"$x_{ax+1}$ (cell units)")
    axs[0, ax].set_title(f"slices normal to $x_{ax+1}$" + (" (loaded faces)" if ax == 0 else ""), fontsize=8)
axs[0, 0].set_ylabel("plane-mean thickness $t$")
axs[1, 0].set_ylabel("solid area fraction")
axs[0, 2].legend(fontsize=6.6, loc="upper center", ncol=2, columnspacing=0.8, handlelength=1.6)
fig.tight_layout()
out = ROOT / "AUTORESEARCH_Q1_REVISION" / "MATERIALS_DESIGN_TRANSFER" / "manuscript" / "figures" / "fig_wpa_thickness_profiles"
fig.savefig(str(out) + ".pdf"); fig.savefig(str(out) + ".png", dpi=200)
