"""Smooth 3D renders of analytic TPMS cells (PyVista/VTK) for Figs. 1, 6 and 7.

Surfaces are isosurfaces of the analytic level set (not the voxel mask), closed
at the cell faces. Fig. 7 colours are the per-element code_aster strain energies
of the 96^3 FE solves, converted to energy density at unit applied strain and
sampled trilinearly onto the surface (display only).
"""
import json
from pathlib import Path

import numpy as np
import pyvista as pv
from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates

pv.OFF_SCREEN = True
ROOT = Path(__file__).resolve().parents[2]
N3 = ROOT / "research" / "n3"
OUT = Path(__file__).resolve().parents[1] / "_deep_review" / "render3d"
OUT.mkdir(parents=True, exist_ok=True)
MODES = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, 0, 1), (0, 1, 1)]
TWO_PI = 2 * np.pi
FE_EPS, FE_N = 1.0e-3, 96
SMOOTH_SIGMA = 1.0  # node spacings; display-only smoothing of the FE field


def F_gyroid(x, y, z):
    X, Y, Z = TWO_PI * x, TWO_PI * y, TWO_PI * z
    return np.sin(X) * np.cos(Y) + np.sin(Y) * np.cos(Z) + np.sin(Z) * np.cos(X)


def F_primitive(x, y, z):
    return np.cos(TWO_PI * x) + np.cos(TWO_PI * y) + np.cos(TWO_PI * z)


def F_diamond(x, y, z):
    X, Y, Z = TWO_PI * x, TWO_PI * y, TWO_PI * z
    return (np.sin(X) * np.sin(Y) * np.sin(Z) + np.sin(X) * np.cos(Y) * np.cos(Z)
            + np.cos(X) * np.sin(Y) * np.cos(Z) + np.cos(X) * np.cos(Y) * np.sin(Z))


def graded_t(theta, shift, t_lo, t_hi, t0=0.30):
    def t_of(x, y, z):
        val = t0 + shift
        for i, (a, b, c) in enumerate(MODES):
            ph = TWO_PI * (a * x + b * y + c * z)
            val = val + theta[2 * i] * np.cos(ph) + theta[2 * i + 1] * np.sin(ph)
        return np.clip(val, t_lo, t_hi)
    return t_of


def cell_surface(F, t_of, n=220, pad=0.02):
    ax = np.linspace(-pad, 1 + pad, n)
    X, Y, Z = np.meshgrid(ax, ax, ax, indexing="ij")
    box = np.maximum.reduce([np.abs(X - 0.5), np.abs(Y - 0.5), np.abs(Z - 0.5)]) - 0.5
    phi = np.maximum(np.abs(F(X, Y, Z)) - t_of(X, Y, Z), 6.0 * box)
    h = ax[1] - ax[0]
    grid = pv.ImageData(dimensions=(n, n, n), spacing=(h, h, h), origin=(-pad,) * 3)
    grid["phi"] = phi.ravel(order="F")
    surf = grid.contour([0.0], scalars="phi").triangulate().clean()
    return surf.compute_normals(auto_orient_normals=True, split_vertices=False)


def fe_density_on(surf, npz):
    """Nodal FE strain-energy density (code_aster ENEL, on the 97^3 node grid),
    normalized to unit applied strain, sampled trilinearly at surface points."""
    d = np.load(npz)
    n = FE_N + 1
    idx = np.rint(d["xyz"] * FE_N).astype(int)
    dens = np.full((n,) * 3, np.nan)
    dens[idx[:, 0], idx[:, 1], idx[:, 2]] = d["ENEL"] / FE_EPS**2
    near = distance_transform_edt(~np.isfinite(dens), return_distances=False,
                                  return_indices=True)
    dens = gaussian_filter(dens[tuple(near)], SMOOTH_SIGMA, mode="wrap")
    coords = (np.clip(surf.points, 0, 1) * FE_N).T
    return map_coordinates(dens, coords, order=1, mode="nearest")


def render(surf, path, scalars=None, cmap=None, clim=None, color="#6f8fb3",
           size=1500, azimuth=-58, elevation=22, zoom=0.92):
    pl = pv.Plotter(off_screen=True, window_size=(size, size), lighting="three lights")
    pl.set_background("white")
    kw = dict(smooth_shading=True, specular=0.25, specular_power=18,
              ambient=0.18, diffuse=0.85, show_scalar_bar=False)
    if scalars is None:
        pl.add_mesh(surf, color=color, **kw)
    else:
        pl.add_mesh(surf, scalars=scalars, cmap=cmap, clim=clim, **kw)
    # Unit-cell outline and x1/x2/x3 triad at the origin corner.
    pl.add_mesh(pv.Box(bounds=(0, 1, 0, 1, 0, 1)).extract_all_edges(), color="#7a7a7a", line_width=2.0)
    tri = {"x_1": (1, 0, 0), "x_2": (0, 1, 0), "x_3": (0, 0, 1)}
    for lab, d in tri.items():
        start = np.array([-0.12, -0.12, -0.12])
        pl.add_mesh(pv.Arrow(start=start, direction=d, scale=0.28, tip_length=0.25,
                             tip_radius=0.07, shaft_radius=0.022), color="#404040")
    pl.add_point_labels(np.array([[-0.12 + 0.33 * d[0], -0.12 + 0.33 * d[1], -0.12 + 0.33 * d[2]]
                                  for d in tri.values()]),
                        ["x1", "x2", "x3"], font_size=54, text_color="#333333", shape=None,
                        show_points=False, font_family="times", always_visible=True)
    a, e = np.radians(azimuth), np.radians(elevation)
    focal = np.array([0.5, 0.5, 0.5])
    pos = focal + 6.0 * np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    pl.camera_position = [tuple(pos), tuple(focal), (0, 0, 1)]
    pl.enable_parallel_projection()
    pl.reset_camera()
    pl.camera.zoom(zoom)
    pl.enable_anti_aliasing("ssaa")
    img = pl.screenshot(return_img=True)
    pl.close()
    rows = np.where((img < 250).any(axis=(1, 2)))[0]
    cols = np.where((img < 250).any(axis=(0, 2)))[0]
    m = 12
    img = img[max(rows[0] - m, 0):rows[-1] + m, max(cols[0] - m, 0):cols[-1] + m]
    from PIL import Image
    Image.fromarray(img).save(path)
    return path


def main():
    const = lambda v: (lambda x, y, z: np.full_like(x, v))
    fam = {"gyroid": (F_gyroid, 0.3000), "primitive": (F_primitive, 0.3387),
           "diamond": (F_diamond, 0.2360)}
    for name, (F, t) in fam.items():
        render(cell_surface(F, const(t)), OUT / f"fam_{name}.png")
        print("family", name)

    cs = json.loads((N3 / "e3_coord_search.json").read_text())
    t_graded = graded_t(np.array(cs["theta"]), cs["t0shift"], 0.12, 0.55)
    g = cell_surface(F_gyroid, t_graded)
    u = cell_surface(F_gyroid, const(0.30))

    g["t"] = t_graded(*g.points.T)
    render(g, OUT / "graded_thickness.png", scalars="t", cmap="viridis", clim=(0.12, 0.55))

    u["w"] = fe_density_on(u, N3 / "fields_uniform.npz")
    g["w"] = fe_density_on(g, N3 / "fields_graded.npz")
    vmax = float(np.percentile(np.concatenate([u["w"], g["w"]]), 98.5))
    for surf, tag in ((u, "uniform"), (g, "graded")):
        render(surf, OUT / f"sed_{tag}.png", scalars="w", cmap="magma", clim=(0.0, vmax))
    json.dump({"sed_vmax": vmax,
               "sed_mean_surface": {"uniform": float(np.mean(u["w"])), "graded": float(np.mean(g["w"]))}},
              open(OUT / "render_meta.json", "w"), indent=1)
    print("sed vmax", vmax)


if __name__ == "__main__":
    main()
