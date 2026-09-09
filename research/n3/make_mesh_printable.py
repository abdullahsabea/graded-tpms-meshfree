"""Voxel mesh of the manufacturability-constrained graded gyroid cell
(e3_opt_result_printable.json: t in [0.20,0.45], smoothness-penalized)
for code_aster verification, same protocol as make_mesh_graded.py.

Usage: python make_mesh_printable.py 64,96
"""
import numpy as np
import sys, os, json
from make_mesh import gyroid_F, write_mail

def load():
    res = json.load(open(os.path.join(os.path.dirname(__file__), "e3_opt_result_printable.json")))
    return (np.array(res["theta"]), float(res["t0shift"]),
            [tuple(m) for m in res["modes"]], res["t0"], res["t_min"], res["t_max"])

def t_of(X, Y, Z, theta, mid, modes, t0, tmin, tmax):
    val = t0 + mid
    for i, (a, b, c) in enumerate(modes):
        ph = 2*np.pi*(a*X + b*Y + c*Z)
        val = val + theta[2*i]*np.cos(ph) + theta[2*i+1]*np.sin(ph)
    return np.clip(val, tmin, tmax)

def build_graded(N, theta, mid, modes, t0, tmin, tmax):
    h = 1.0 / N
    c = (np.arange(N) + 0.5) * h
    X, Y, Z = np.meshgrid(c, c, c, indexing="ij")
    tv = t_of(X, Y, Z, theta, mid, modes, t0, tmin, tmax)
    solid = (np.abs(gyroid_F(X, Y, Z)) - tv) < 0.0
    ids = np.argwhere(solid)
    eid = {tuple(v): n + 1 for n, v in enumerate(ids)}
    nmap, nodes, elems = {}, [], []
    for (i, j, k) in ids:
        corner = [(i, j, k), (i+1, j, k), (i+1, j+1, k), (i, j+1, k),
                  (i, j, k+1), (i+1, j, k+1), (i+1, j+1, k+1), (i, j+1, k+1)]
        row = []
        for key in corner:
            if key not in nmap:
                nmap[key] = len(nodes) + 1
                nodes.append((key[0]*h, key[1]*h, key[2]*h))
            row.append(nmap[key])
        elems.append((eid[tuple((i, j, k))], row))
    nodes = np.array(nodes)
    tol = 1e-9
    on_x0 = nodes[:, 0] < tol; on_x1 = nodes[:, 0] > 1 - tol
    on_y0 = nodes[:, 1] < tol; on_y1 = nodes[:, 1] > 1 - tol
    on_z0 = nodes[:, 2] < tol; on_z1 = nodes[:, 2] > 1 - tol
    bound = on_x0 | on_x1 | on_y0 | on_y1 | on_z0 | on_z1
    groups = {
        "X0": np.where(on_x0)[0] + 1, "X1": np.where(on_x1)[0] + 1,
        "Y0": np.where(on_y0)[0] + 1, "Y1": np.where(on_y1)[0] + 1,
        "Z0": np.where(on_z0)[0] + 1, "Z1": np.where(on_z1)[0] + 1,
        "BOUND": np.where(bound)[0] + 1,
    }
    return nodes, elems, groups, solid.mean()

if __name__ == "__main__":
    theta, mid, modes, t0, tmin, tmax = load()
    print(f"theta={np.round(theta,3).tolist()}  t0shift={mid:+.4f}  bounds=[{tmin},{tmax}]")
    Ns = [int(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else [64]
    for N in Ns:
        nodes, elems, groups, vf = build_graded(N, theta, mid, modes, t0, tmin, tmax)
        write_mail(f"gyroid_printable_N{N}.mail", nodes, elems, groups, vf, N, -1)
