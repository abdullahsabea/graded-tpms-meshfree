"""Measured periodicity residual of a body-fitted PBC solve.

The unknown of homog_conf_pbc.comm is the fluctuation w (macro strain enters
through PRE_EPSI), so periodicity means w(x + e_d) = w(x). For every node on a
'+' face (x_d = 1) the displacement is compared with w interpolated at its image
(x_d = 0) on the opposite face, using the quadratic TRIA6 shape functions of
that face (the same interpolation LIAISON_MAIL uses), so the comparison adds no
interpolation error of its own. Residuals are reported relative to the
macroscopic displacement scale eps_bar * L (L = 1) and to max|w|.

usage: python periodicity_residual.py resid_<stem>.med [EPS]
"""
import json
import sys

import meshio
import numpy as np
from scipy.spatial import cKDTree

med = sys.argv[1]
EPS = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0e-3
m = meshio.read(med)
P = m.points
key = [k for k in m.point_data if "DEPL" in k.upper()]
W = np.asarray(m.point_data[key[0]])[:, :3]
tri = np.vstack([c.data for c in m.cells if c.type == "triangle6"])
tol = 1e-9


def tri6_shape(L):
    L1, L2, L3 = L
    return np.array([L1 * (2 * L1 - 1), L2 * (2 * L2 - 1), L3 * (2 * L3 - 1),
                     4 * L1 * L2, 4 * L2 * L3, 4 * L3 * L1])


out = {"file": med, "eps": EPS, "n_nodes": int(len(P)), "max_abs_w": float(np.abs(W).max()), "faces": {}}
allres = []
for d, name in enumerate("xyz"):
    other = [a for a in range(3) if a != d]
    mt = tri[np.all(P[tri[:, :3], d] < tol, axis=1)]          # master triangles on x_d = 0
    slaves = np.where(P[:, d] > 1 - tol)[0]                    # nodes on x_d = 1
    c2 = P[mt[:, :3]][:, :, other]                             # (T,3,2) corner coords in-plane
    tree = cKDTree(c2.mean(axis=1))
    res, res_out, dist_out = [], [], []
    for s in slaves:
        q = P[s, other]
        _, cand = tree.query(q, k=24)
        best = None
        for t in np.atleast_1d(cand):
            a, b, c = c2[t]
            T = np.array([[a[0] - c[0], b[0] - c[0]], [a[1] - c[1], b[1] - c[1]]])
            try:
                l12 = np.linalg.solve(T, q - c)
            except np.linalg.LinAlgError:
                continue
            L = np.array([l12[0], l12[1], 1 - l12.sum()])
            if best is None or L.min() > best[1].min():
                best = (t, L)
            if L.min() >= -1e-7:
                break
        t, L = best
        if L.min() >= -1e-7:
            res.append(np.linalg.norm(W[s] - tri6_shape(L) @ W[mt[t]]))
        else:
            # image outside the master face polygon (cap boundary): project onto the
            # nearest triangle, as the tie does, and record the projection distance
            Lc = np.clip(L, 0, None); Lc /= Lc.sum()
            xc = Lc @ c2[t]
            dist_out.append(float(np.linalg.norm(xc - q)))
            res_out.append(np.linalg.norm(W[s] - tri6_shape(Lc) @ W[mt[t]]))
    res, res_out = np.array(res), np.array(res_out)
    allres.append(np.concatenate([res, res_out]))
    out["faces"][name] = dict(n_slave=int(len(slaves)), n_inside=int(len(res)), n_projected=int(len(res_out)),
                              max_over_epsL=float(res.max() / EPS), p99_over_epsL=float(np.percentile(res, 99) / EPS),
                              median_over_epsL=float(np.median(res) / EPS),
                              projected_max_over_epsL=float(res_out.max() / EPS) if len(res_out) else 0.0,
                              projected_p99_over_epsL=float(np.percentile(res_out, 99) / EPS) if len(res_out) else 0.0,
                              projected_max_distance=float(max(dist_out)) if dist_out else 0.0,
                              max_over_maxw=float(res.max() / np.abs(W).max()))
allres = np.concatenate(allres)
out["overall_max_over_epsL"] = float(allres.max() / EPS)
out["overall_max_over_maxw"] = float(allres.max() / np.abs(W).max())
print(json.dumps(out, indent=1))
json.dump(out, open(med.replace(".med", "_residual.json"), "w"), indent=1)
