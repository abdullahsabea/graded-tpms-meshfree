"""Third dog-bone: manufacturability-constrained optimized gauge.

Uses e3_opt_result_printable.json (t in [0.20,0.45], smoothness-penalized
optimization, research/n3/e3_optimize_printable.py) instead of the original
unconstrained theta* (t in [0.12,0.55]). Same outline, same witness marks,
same mesh settings as make_dogbone_stl.py -- only the gauge design field
differs. Predicted gain (mesh-free, own model): +8.3% vs uniform, smaller
than the unconstrained +17.5% but built to avoid the steep local thickness
gradients that triggered the "floating regions" slicer warning.
"""
import json
from pathlib import Path

import numpy as np
from skimage import measure
from scipy.sparse import coo_matrix

HERE = Path(__file__).parent
N3 = HERE.parent / "research" / "n3"

L_TOT, W_GRIP, W_GAUGE, THICK = 160.0, 45.0, 30.0, 15.0
L_GAUGE, R_FILLET = 60.0, 25.0
L_CELL = 15.0
T_SOLID = 1.6
RAMP_A, RAMP_B = 30.0, 40.0
VOX = 0.24
SMOOTH_ITERS = 2
MARK_X1 = (30.0, 130.0)
CENTER = L_TOT / 2.0
RHO_PLA = 1.24e-3

res = json.load(open(N3 / "e3_opt_result_printable.json"))
THETA = np.array(res["theta"])
T0 = res["t0"]
DT0 = res["t0shift"]
MODES = [tuple(m) for m in res["modes"]]
T_MIN, T_MAX = res["t_min"], res["t_max"]

def gyroid_F(u, v, w):
    X, Y, Z = 2*np.pi*u, 2*np.pi*v, 2*np.pi*w
    return np.sin(X)*np.cos(Y) + np.sin(Y)*np.cos(Z) + np.sin(Z)*np.cos(X)

def t_design(u, v, w):
    val = T0 + DT0
    for i, (a, b, c) in enumerate(MODES):
        ph = 2*np.pi*(a*u + b*v + c*w)
        val = val + THETA[2*i]*np.cos(ph) + THETA[2*i+1]*np.sin(ph)
    return np.clip(val, T_MIN, T_MAX)

def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x*x*(3 - 2*x)

def half_width(x1):
    g = np.abs(x1 - CENTER)
    h = np.full_like(x1, W_GRIP/2)
    s = g - L_GAUGE/2
    smax = np.sqrt(R_FILLET**2 - (R_FILLET - (W_GRIP-W_GAUGE)/2)**2)
    fil = (s > 0) & (s < smax)
    h = np.where(g <= L_GAUGE/2, W_GAUGE/2, h)
    h_f = W_GAUGE/2 + R_FILLET - np.sqrt(np.maximum(R_FILLET**2 - np.where(fil, s, 0.0)**2, 0.0))
    return np.where(fil, h_f, h)

GROOVE_HALF_W, GROOVE_DEPTH = 0.4, 0.4

def witness_groove(x1, x3):
    d_line = np.minimum(np.abs(x1-MARK_X1[0]), np.abs(x1-MARK_X1[1]))
    d_depth = THICK - x3
    return -np.maximum(d_line - GROOVE_HALF_W, d_depth - GROOVE_DEPTH)

def phi_mm(x1, x2, x3):
    outline = np.maximum.reduce([
        np.abs(x2) - half_width(x1),
        np.abs(x3 - THICK/2) - THICK/2,
        np.abs(x1 - CENTER) - L_TOT/2,
    ])
    u, v, w = x1/L_CELL, x2/L_CELL, x3/L_CELL
    g = np.abs(x1 - CENTER)
    s = smoothstep((g - RAMP_A)/(RAMP_B - RAMP_A))
    t_spec = t_design(u, v, w)*(1-s) + T_SOLID*s
    tpms = (np.abs(gyroid_F(u, v, w)) - t_spec) * (L_CELL/(2*np.pi))
    body = np.maximum(outline, tpms)
    return np.maximum(body, witness_groove(x1, x3))

def taubin_smooth(verts, faces, iterations=SMOOTH_ITERS, lam=0.5, mu=-0.53):
    e = np.vstack([faces[:,[0,1]], faces[:,[1,2]], faces[:,[2,0]]])
    e = np.vstack([e, e[:,::-1]])
    n = len(verts)
    A = coo_matrix((np.ones(len(e)), (e[:,0], e[:,1])), shape=(n,n)).tocsr()
    deg = np.asarray(A.sum(axis=1)).ravel(); deg[deg==0] = 1.0
    v = verts.copy()
    for _ in range(iterations):
        avg = (A @ v)/deg[:,None]; v = v + lam*(avg-v)
        avg = (A @ v)/deg[:,None]; v = v + mu*(avg-v)
    return v

def write_stl_binary(path, verts, faces):
    tri = verts[faces]
    n = np.cross(tri[:,1]-tri[:,0], tri[:,2]-tri[:,0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-30)
    blk = np.zeros((len(faces), 12), dtype="<f4")
    blk[:,0:3] = n; blk[:,3:6] = tri[:,0]; blk[:,6:9] = tri[:,1]; blk[:,9:12] = tri[:,2]
    rec = np.zeros(len(faces), dtype=[("d","<f4",12),("p","<u2")])
    rec["d"] = blk
    with open(path, "wb") as f:
        f.write(b"\0"*80); f.write(np.array([len(faces)], dtype="<u4").tobytes())
        f.write(rec.tobytes())

gx = np.arange(-VOX, L_TOT+2*VOX, VOX)
gy = np.arange(-W_GRIP/2-VOX, W_GRIP/2+2*VOX, VOX)
gz = np.arange(-VOX, THICK+2*VOX, VOX)
X1, X2, X3 = np.meshgrid(gx, gy, gz, indexing="ij")
P = phi_mm(X1, X2, X3).astype(np.float32)
verts, faces, _, _ = measure.marching_cubes(P, level=0.0, spacing=(VOX,VOX,VOX))
verts += np.array([gx[0], gy[0], gz[0]])
n_tri = len(faces)
verts = taubin_smooth(verts, faces)
write_stl_binary(HERE/"dogbone_optimized_printable.stl", verts, faces)

vol = float((P<0).mean()) * (gx[-1]-gx[0])*(gy[-1]-gy[0])*(gz[-1]-gz[0])
rng = np.random.default_rng(1)
q = rng.random((1_000_000,3))
qx = CENTER - RAMP_A + 2*RAMP_A*q[:,0]
qy = -W_GAUGE/2 + W_GAUGE*q[:,1]
qz = THICK*q[:,2]
vf = float(np.mean(phi_mm(qx,qy,qz) < 0))
print(f"dogbone_optimized_printable: mass(PLA)~{vol*RHO_PLA:.0f} g  "
      f"solid={vol/1e3:.1f} cm^3  gauge Vf={vf:.4f}  ({n_tri} triangles)")
