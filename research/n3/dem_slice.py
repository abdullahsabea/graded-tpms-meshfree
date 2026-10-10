"""Sample a trained DEM model on a plane of the unit cell.

The mesh-free solution is a continuous field, so it can be evaluated directly
on any plane at any resolution -- no interpolation from a discretization. This
writes the same quantities code_aster exports (displacement fluctuation and
elastic energy density), normalized by the applied strain so that the DEM runs
(eps = 1e-2) and the FE runs (eps = 1e-3) are directly comparable.

Usage: python dem_slice.py <family> <t> <ckpt> <out.npz> [z_plane] [n_grid] [grid]

  grid = "cell" (default, cell-centred, any resolution) or "node", which places
  the samples exactly on the nodes of the N^3 voxel FE mesh so that a
  difference field can be formed without interpolating either solution.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
import torch
from torch.func import jacrev, vmap

import dem_tpms as D          # network definition, constants, level set
from tpms_levelset import TPMSSheet

FAMILY = sys.argv[1]
T_PARAM = float(sys.argv[2])
CKPT = sys.argv[3]
OUT = sys.argv[4]
ZPLANE = float(sys.argv[5]) if len(sys.argv) > 5 else 0.5
NG = int(sys.argv[6]) if len(sys.argv) > 6 else 400
GRID = sys.argv[7] if len(sys.argv) > 7 else "cell"

torch.set_default_dtype(torch.float64)
tpms = TPMSSheet(FAMILY, k=2 * np.pi, t=T_PARAM)

model = D.make_model()
blob = torch.load(CKPT, weights_only=True)
sd = blob["state"] if isinstance(blob, dict) and "state" in blob else blob
model.load_state_dict({k: v.double() for k, v in sd.items()})

g = np.arange(NG + 1) / NG if GRID == "node" else (np.arange(NG) + 0.5) / NG
X, Y = np.meshgrid(g, g, indexing="ij")
shape = X.shape
pts = torch.tensor(np.stack([X.ravel(), Y.ravel(),
                             np.full(X.size, ZPLANE)], axis=-1))

with torch.no_grad():
    inside = tpms.inside(pts).numpy()
u = model(pts).detach().numpy()
dens = D.strain_energy(model, pts).detach().numpy()

EPS = D.EPS
# fluctuation = full field minus the imposed affine part, normalized by strain
fluct = (u[:, 0] - EPS * pts[:, 0].numpy()) / EPS
enel = dens / EPS**2                       # energy density at unit strain

np.savez_compressed(
    OUT,
    x=X, y=Y, z=ZPLANE, grid=GRID,
    inside=inside.reshape(shape),
    fluct_u1=fluct.reshape(shape),
    enel=enel.reshape(shape),
    ux=(u[:, 0] / EPS).reshape(shape),
    family=FAMILY, t=T_PARAM, ckpt=os.path.basename(CKPT),
)
n_in = int(inside.sum())
print(f"{FAMILY} t={T_PARAM} z={ZPLANE}: {NG}x{NG} grid, {n_in} points in solid, "
      f"mean energy density {enel[inside].mean():.4e} -> {OUT}")
