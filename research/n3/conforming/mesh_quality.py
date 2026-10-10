"""Mesh-quality diagnostics for the body-fitted PBC meshes (final review B1):
per tetrahedron, the shortest-to-longest edge ratio (the quantity code_aster's
MODELISA8_15 alarm tests against 1e-3) and the volume; reports how many
elements and how much volume fall below the threshold, for all ten meshes."""
import json
import sys

import numpy as np


def read_mail(path):
    coords, tets = {}, []
    sec = None
    with open(path) as f:
        for line in f:
            s = line.strip()
            if s in ("COOR_3D", "TETRA4"):
                sec = s
                continue
            if s == "FINSF":
                sec = None
                continue
            if sec == "COOR_3D":
                p = s.split()
                coords[p[0]] = (float(p[1]), float(p[2]), float(p[3]))
            elif sec == "TETRA4":
                p = s.split()
                tets.append(p[1:5])
    names = list(coords)
    idx = {n: i for i, n in enumerate(names)}
    X = np.array([coords[n] for n in names])
    T = np.array([[idx[n] for n in t] for t in tets])
    return X, T


out = {}
for stem in sys.argv[1:]:
    X, T = read_mail(stem + ".mail")
    P = X[T]                                          # (n,4,3)
    pairs = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
    L = np.stack([np.linalg.norm(P[:, a] - P[:, b], axis=1) for a, b in pairs], axis=1)
    ratio = L.min(1) / L.max(1)
    vol = np.abs(np.einsum("ij,ij->i", P[:, 1] - P[:, 0], np.cross(P[:, 2] - P[:, 0], P[:, 3] - P[:, 0]))) / 6
    bad = ratio < 1e-3
    out[stem] = dict(n_tet=int(len(T)), n_bad=int(bad.sum()), frac_bad=float(bad.mean()),
                     vol_share_bad=float(vol[bad].sum() / vol.sum()), min_ratio=float(ratio.min()),
                     n_below_0p01=int((ratio < 1e-2).sum()))
    print(stem, out[stem], flush=True)
json.dump(out, open("mesh_quality.json", "w"), indent=1)
