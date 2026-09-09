"""Generate printable STL specimens for experimental validation.

Two compression specimens at identical volume fraction (Vf = 0.193):
  1) uniform gyroid sheet, t = 0.30
  2) optimized graded gyroid, theta* from the E3 coordinate search

Each specimen is an n x n x n tessellation of the unit cell (the graded
field is periodic by construction, so it tiles exactly), converted to a
watertight surface by marching cubes on the analytic level set and scaled
to a physical cell size L_CELL. A small ridge along one x1-edge marks the
optimized (loading) direction; it is placed identically on both specimens
so the stiffness ratio is unaffected.

Usage: python make_specimen_stl.py
Outputs: specimen_uniform_t0.30.stl, specimen_graded_opt.stl + a report.
"""
import json
import struct
from pathlib import Path

import numpy as np
from skimage import measure

HERE = Path(__file__).parent
N3 = HERE.parent / "research" / "n3"

# ---------------- parameters ----------------
N_CELLS = 4          # cells per side (4x4x4 specimen)
RES = 64             # voxels per cell for marching cubes
L_CELL = 20.0        # mm, physical cell size
T_UNIFORM = 0.30
T_MIN, T_MAX = 0.12, 0.55
RHO_PA12 = 1.01e-3   # g/mm^3, sintered PA12
MARKER = True        # ridge along one x1 edge to mark the loading axis
MARKER_W = 1.2       # mm

MODES = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, 0, 1), (0, 1, 1)]
res = json.load(open(N3 / "e3_coord_search.json"))
THETA = np.array(res["theta"])
DT0 = res["t0shift"]

def gyroid_F(u, v, w):
    X, Y, Z = 2 * np.pi * u, 2 * np.pi * v, 2 * np.pi * w
    return (np.sin(X) * np.cos(Y) + np.sin(Y) * np.cos(Z)
            + np.sin(Z) * np.cos(X))

def grad_F_mag(u, v, w):
    X, Y, Z = 2 * np.pi * u, 2 * np.pi * v, 2 * np.pi * w
    gx = np.cos(X) * np.cos(Y) - np.sin(Z) * np.sin(X)
    gy = -np.sin(X) * np.sin(Y) + np.cos(Y) * np.cos(Z)
    gz = -np.sin(Y) * np.sin(Z) + np.cos(Z) * np.cos(X)
    return 2 * np.pi * np.sqrt(gx**2 + gy**2 + gz**2)

def t_graded(u, v, w):
    val = T_UNIFORM + DT0
    for i, (a, b, c) in enumerate(MODES):
        ph = 2 * np.pi * (a * u + b * v + c * w)
        val = val + THETA[2 * i] * np.cos(ph) + THETA[2 * i + 1] * np.sin(ph)
    return np.clip(val, T_MIN, T_MAX)

def phi(u, v, w, graded):
    t = t_graded(u, v, w) if graded else T_UNIFORM
    return np.abs(gyroid_F(u, v, w)) - t

def write_stl_binary(path, verts, faces):
    tri = verts[faces]                                   # (F,3,3)
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-30)
    with open(path, "wb") as f:
        f.write(b"\0" * 80)
        f.write(struct.pack("<I", len(faces)))
        blk = np.zeros((len(faces), 12), dtype="<f4")
        blk[:, 0:3] = n
        blk[:, 3:6] = tri[:, 0]
        blk[:, 6:9] = tri[:, 1]
        blk[:, 9:12] = tri[:, 2]
        pad = np.zeros((len(faces), 1), dtype="<u2")
        raw = b"".join(
            blk[i].tobytes() + pad[i].tobytes() for i in range(len(faces)))
        f.write(raw)

def build(graded, name):
    Ntot = N_CELLS * RES
    g = (np.arange(Ntot + 1)) / RES                      # 0 .. N_CELLS, cell units
    U, V, W = np.meshgrid(g, g, g, indexing="ij")
    P = phi(U % 1.0, V % 1.0, W % 1.0, graded)
    if MARKER:                                           # ridge marks +x1 edge
        mw = MARKER_W / L_CELL
        ridge = np.maximum(V - mw, W - mw)               # <0 inside ridge
        P = np.minimum(P, ridge)
    Ppad = np.pad(P, 1, constant_values=1.0)             # close the boundary
    verts, faces, _, _ = measure.marching_cubes(Ppad, level=0.0)
    verts = (verts - 1.0) / RES * L_CELL                 # mm
    write_stl_binary(HERE / f"{name}.stl", verts, faces)

    # metrics on cell-interior samples (marker excluded)
    rng = np.random.default_rng(0)
    s = rng.random((2_000_000, 3))
    vf = float(np.mean(phi(s[:, 0], s[:, 1], s[:, 2], graded) < 0))
    # wall thickness ~ 2 t / |grad_x F|, evaluated on near-surface samples
    t_s = t_graded(s[:, 0], s[:, 1], s[:, 2]) if graded else T_UNIFORM
    Fmag = np.abs(gyroid_F(s[:, 0], s[:, 1], s[:, 2]))
    near = np.abs(Fmag - t_s) < 0.02
    wall = (2 * np.atleast_1d(t_s)[near if graded else slice(None)]
            / grad_F_mag(s[near, 0], s[near, 1], s[near, 2])) * L_CELL
    vol = vf * (N_CELLS * L_CELL) ** 3
    print(f"{name}: Vf={vf:.4f}  bbox={N_CELLS*L_CELL:.0f} mm cube  "
          f"solid={vol/1e3:.1f} cm^3  mass(PA12)~{vol*RHO_PA12:.1f} g  "
          f"wall min/med/max = {wall.min():.2f}/{np.median(wall):.2f}/"
          f"{wall.max():.2f} mm  ({len(faces)} triangles)")
    return vf

if __name__ == "__main__":
    vf_u = build(False, "specimen_uniform_t0.30")
    vf_g = build(True, "specimen_graded_opt")
    print(f"iso-volume check: uniform {vf_u:.4f} vs graded {vf_g:.4f} "
          f"({abs(vf_g/vf_u-1)*100:.2f}% apart)")
