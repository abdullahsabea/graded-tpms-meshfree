"""Reduce the FE nodal fields to mid-plane slice arrays on the voxel node grid.

The voxel meshes are structured, so the plane z = 0.5 is exactly a node plane of
the N^3 grid: no interpolation is needed, only a selection. Void nodes stay NaN.

Writes research/n3/slice_fe_<tag>.npz with x, y, ENEL, VMIS, DX (all normalized
to unit applied strain) on an (N+1, N+1) grid.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
EPS_FE = 1.0e-3          # applied strain in homog_fields.comm
N = 96
ZPLANE = 0.5


def slice_one(tag):
    d = np.load(os.path.join(HERE, f"fields_{tag}.npz"))
    xyz = d["xyz"]
    sel = np.abs(xyz[:, 2] - ZPLANE) < 1e-9
    if not sel.any():
        raise SystemExit(f"{tag}: no nodes on z={ZPLANE}")
    x, y = xyz[sel, 0], xyz[sel, 1]
    i = np.rint(x * N).astype(int)
    j = np.rint(y * N).astype(int)

    out = {}
    g = np.arange(N + 1) / N
    X, Y = np.meshgrid(g, g, indexing="ij")
    out["x"], out["y"] = X, Y
    for key, scale in (("ENEL", 1.0 / EPS_FE**2),   # energy density at unit strain
                       ("VMIS", 1.0 / EPS_FE),      # stress at unit strain
                       ("DX", 1.0 / EPS_FE)):       # displacement at unit strain
        arr = np.full((N + 1, N + 1), np.nan)
        arr[i, j] = d[key][sel] * scale
        out[key] = arr
    # fluctuation of the axial displacement: full field minus the imposed affine part
    out["fluct_u1"] = out["DX"] - X
    n_solid = int(np.isfinite(out["ENEL"]).sum())
    path = os.path.join(HERE, f"slice_fe_{tag}.npz")
    np.savez_compressed(path, **out)
    print(f"{tag}: {n_solid} solid nodes on z={ZPLANE}, "
          f"mean ENEL {np.nanmean(out['ENEL']):.4e} -> {os.path.basename(path)}")


if __name__ == "__main__":
    tags = sys.argv[1:] or ["uniform", "graded", "primitive", "diamond"]
    for t in tags:
        slice_one(t)
