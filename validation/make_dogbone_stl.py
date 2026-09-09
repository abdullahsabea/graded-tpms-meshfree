"""FDM tensile demonstrators: dog-bone specimens with a TPMS gauge section.

Two specimens, identical outline and identical gauge volume fraction:
  1) dogbone_uniform.stl    gauge = uniform gyroid sheet, t = 0.30
  2) dogbone_optimized.stl  gauge = optimized graded gyroid (theta* from E3),
                            stiff direction x1 aligned with the tensile axis

The whole specimen is ONE analytic level set, no CAD:
  phi(x) = max( phi_outline(x),  (|F(k x)| - t_spec(x)) * L/(2*pi) )
where t_spec ramps from the gauge design field to t_solid = 1.6 > max|F|
inside the transition, which makes the grip ends solid. This is the same
thickness-grading mechanism the paper optimizes; solid material is just the
limit t -> t_solid of the design space.

Geometry (mm): length 160, grip width 45, gauge width 30, thickness 15,
gauge length 60, fillet radius 25, cell size 15 (gauge = 4 x 2 x 1 cells).
Print flat (x1-x2 plane on the bed); the gyroid is self-supporting.

Usage: python make_dogbone_stl.py          (STLs + preview PNG + report)
"""
import json
import struct
from pathlib import Path

import numpy as np
from skimage import measure
from scipy.sparse import coo_matrix

HERE = Path(__file__).parent
N3 = HERE.parent / "research" / "n3"

# ---------------- parameters (mm) ----------------
L_TOT, W_GRIP, W_GAUGE, THICK = 160.0, 45.0, 30.0, 15.0
L_GAUGE, R_FILLET = 60.0, 25.0
L_CELL = 15.0
T0, T_MIN, T_MAX, T_SOLID = 0.30, 0.12, 0.55, 1.6
RAMP_A, RAMP_B = 30.0, 40.0        # |x1-c| band over which t ramps to solid
                                   # RAMP_A = L_GAUGE/2: the pure-lattice band
                                   # spans exactly 4 x 2 x 1 cells, so both
                                   # designs integrate to the same gauge Vf
VOX = 0.24                          # marching-cubes voxel (mm)
SMOOTH_ITERS = 2                    # Taubin (non-shrinking) smoothing passes
MARK_X1 = (30.0, 130.0)             # witness-line x1 positions (see notes below)
RHO_PLA = 1.24e-3                   # g/mm^3
CENTER = L_TOT / 2.0

MODES = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, 0, 1), (0, 1, 1)]
res = json.load(open(N3 / "e3_coord_search.json"))
THETA = np.array(res["theta"])
DT0 = res["t0shift"]

def gyroid_F(u, v, w):
    X, Y, Z = 2 * np.pi * u, 2 * np.pi * v, 2 * np.pi * w
    return (np.sin(X) * np.cos(Y) + np.sin(Y) * np.cos(Z)
            + np.sin(Z) * np.cos(X))

def t_design(u, v, w, graded):
    if not graded:
        return np.full_like(u, T0)
    val = T0 + DT0
    for i, (a, b, c) in enumerate(MODES):
        ph = 2 * np.pi * (a * u + b * v + c * w)
        val = val + THETA[2 * i] * np.cos(ph) + THETA[2 * i + 1] * np.sin(ph)
    return np.clip(val, T_MIN, T_MAX)

def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)

def half_width(x1):
    g = np.abs(x1 - CENTER)
    h = np.full_like(x1, W_GRIP / 2)
    s = g - L_GAUGE / 2                       # distance beyond gauge
    smax = np.sqrt(R_FILLET**2 - (R_FILLET - (W_GRIP - W_GAUGE) / 2) ** 2)
    fil = (s > 0) & (s < smax)
    h = np.where(g <= L_GAUGE / 2, W_GAUGE / 2, h)
    h_f = W_GAUGE / 2 + R_FILLET - np.sqrt(
        np.maximum(R_FILLET**2 - np.where(fil, s, 0.0) ** 2, 0.0))
    return np.where(fil, h_f, h)

GROOVE_HALF_W, GROOVE_DEPTH = 0.4, 0.4   # witness-line notch (mm)

def witness_groove(x1, x3):
    """Shallow scribe line across the top face at each MARK_X1, marking
    the extensometer/DIC gauge points identically on every print."""
    d_line = np.minimum(np.abs(x1 - MARK_X1[0]), np.abs(x1 - MARK_X1[1]))
    d_depth = THICK - x3
    groove_solid = np.maximum(d_line - GROOVE_HALF_W, d_depth - GROOVE_DEPTH)
    return -groove_solid                # >0 inside the notch -> carve it

def phi_mm(x1, x2, x3, graded):
    outline = np.maximum.reduce([
        np.abs(x2) - half_width(x1),
        np.abs(x3 - THICK / 2) - THICK / 2,
        np.abs(x1 - CENTER) - L_TOT / 2,
    ])
    u, v, w = x1 / L_CELL, x2 / L_CELL, x3 / L_CELL
    g = np.abs(x1 - CENTER)
    s = smoothstep((g - RAMP_A) / (RAMP_B - RAMP_A))
    t_spec = t_design(u, v, w, graded) * (1 - s) + T_SOLID * s
    tpms = (np.abs(gyroid_F(u, v, w)) - t_spec) * (L_CELL / (2 * np.pi))
    body = np.maximum(outline, tpms)
    return np.maximum(body, witness_groove(x1, x3))

def taubin_smooth(verts, faces, iterations=SMOOTH_ITERS, lam=0.5, mu=-0.53):
    """Non-shrinking Laplacian smoothing to remove marching-cubes facets
    without eroding the design volume fraction."""
    e = np.vstack([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    e = np.vstack([e, e[:, ::-1]])
    n = len(verts)
    A = coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(n, n)).tocsr()
    deg = np.asarray(A.sum(axis=1)).ravel()
    deg[deg == 0] = 1.0
    v = verts.copy()
    for _ in range(iterations):
        avg = (A @ v) / deg[:, None]
        v = v + lam * (avg - v)
        avg = (A @ v) / deg[:, None]
        v = v + mu * (avg - v)
    return v

def write_stl_binary(path, verts, faces):
    tri = verts[faces]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-30)
    blk = np.zeros((len(faces), 12), dtype="<f4")
    blk[:, 0:3] = n
    blk[:, 3:6] = tri[:, 0]
    blk[:, 6:9] = tri[:, 1]
    blk[:, 9:12] = tri[:, 2]
    pad = np.zeros(len(faces), dtype="<u2")
    with open(path, "wb") as f:
        f.write(b"\0" * 80)
        f.write(struct.pack("<I", len(faces)))
        rec = np.zeros(len(faces), dtype=[("d", "<f4", 12), ("p", "<u2")])
        rec["d"] = blk
        rec["p"] = pad
        f.write(rec.tobytes())

def build(graded, name):
    gx = np.arange(-VOX, L_TOT + 2 * VOX, VOX)
    gy = np.arange(-W_GRIP / 2 - VOX, W_GRIP / 2 + 2 * VOX, VOX)
    gz = np.arange(-VOX, THICK + 2 * VOX, VOX)
    X1, X2, X3 = np.meshgrid(gx, gy, gz, indexing="ij")
    P = phi_mm(X1, X2, X3, graded).astype(np.float32)
    verts, faces, _, _ = measure.marching_cubes(P, level=0.0,
                                                spacing=(VOX, VOX, VOX))
    verts += np.array([gx[0], gy[0], gz[0]])
    n_tri = len(faces)
    verts = taubin_smooth(verts, faces)
    write_stl_binary(HERE / f"{name}.stl", verts, faces)

    vol = float((P < 0).mean()) * (gx[-1]-gx[0]) * (gy[-1]-gy[0]) * (gz[-1]-gz[0])
    # gauge volume fraction (pure-lattice band, inside outline box)
    rng = np.random.default_rng(1)
    q = rng.random((1_000_000, 3))
    qx = CENTER - RAMP_A + 2 * RAMP_A * q[:, 0]
    qy = -W_GAUGE / 2 + W_GAUGE * q[:, 1]
    qz = THICK * q[:, 2]
    vf = float(np.mean(phi_mm(qx, qy, qz, graded) < 0))
    print(f"{name}: mass(PLA)~{vol*RHO_PLA:.0f} g  solid={vol/1e3:.1f} cm^3  "
          f"gauge Vf={vf:.4f}  ({n_tri} triangles, VOX={VOX} mm, "
          f"{SMOOTH_ITERS} Taubin passes)")
    return vf

def preview():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 1, figsize=(10, 5.6))
    gx = np.arange(0, L_TOT, 0.25)
    gy = np.arange(-W_GRIP / 2, W_GRIP / 2, 0.25)
    X1, X2 = np.meshgrid(gx, gy, indexing="ij")
    X3 = np.full_like(X1, THICK / 2)
    for ax, graded, title in ((axes[0], False, "uniform gyroid gauge (t = 0.30)"),
                              (axes[1], True, "optimized graded gauge (theta*)")):
        solid = phi_mm(X1, X2, X3, graded) < 0
        ax.imshow(solid.T, origin="lower", cmap="Blues",
                  extent=[0, L_TOT, -W_GRIP/2, W_GRIP/2], aspect="equal",
                  interpolation="nearest")
        ax.set_title(f"mid-thickness section: {title}", fontsize=10)
        ax.set_xlabel("x1 (tensile axis) [mm]"); ax.set_ylabel("x2 [mm]")
    fig.tight_layout()
    fig.savefig(HERE / "dogbone_preview.png", dpi=220)
    print("preview written")

if __name__ == "__main__":
    vf_u = build(False, "dogbone_uniform")
    vf_g = build(True, "dogbone_optimized")
    print(f"gauge iso-volume check: {vf_u:.4f} vs {vf_g:.4f} "
          f"({abs(vf_g/vf_u-1)*100:.2f}% apart)")
    preview()
