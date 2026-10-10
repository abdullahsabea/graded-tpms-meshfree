"""Where does the mesh-free solver disagree with FE, in 3D?

The mid-plane slice shows near-identical agreement for the gyroid and the
primitive, yet their integral deviations differ by an order of magnitude
(+3.9% vs +15.5%). This evaluates the DEM at every FE node of the cell and
localizes the difference against two candidate explanations:

  * the hard-BC ansatz u = d_cube(x) N(x) + affine, which could leave a
    boundary layer -> bin by distance to the cube face;
  * bending-dominated thin-wall regions -> bin by distance from the TPMS
    mid-surface, |F|/t (0 = mid-surface, 1 = free surface).

Usage: python dem_vs_fe_volume.py <family> <t> <ckpt> <fe_tag>
Writes research/n3/demfe_<family>.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
import torch

import dem_tpms as D
from tpms_levelset import TPMSSheet

HERE = os.path.dirname(os.path.abspath(__file__))
FAMILY, T_PARAM, CKPT, FE_TAG = sys.argv[1], float(sys.argv[2]), sys.argv[3], sys.argv[4]
EPS_FE = 1.0e-3

torch.set_default_dtype(torch.float64)
tpms = TPMSSheet(FAMILY, k=2 * np.pi, t=T_PARAM)
model = D.make_model()
blob = torch.load(os.path.join(HERE, CKPT), weights_only=True)
sd = blob["state"] if isinstance(blob, dict) and "state" in blob else blob
model.load_state_dict({k: v.double() for k, v in sd.items()})

fe = np.load(os.path.join(HERE, f"fields_{FE_TAG}.npz"))
xyz = fe["xyz"]
e_fe = fe["ENEL"] / EPS_FE**2

# evaluate the mesh-free solution at the FE nodes, in chunks
e_dem = np.empty(len(xyz))
CH = 20000
for i in range(0, len(xyz), CH):
    p = torch.tensor(xyz[i:i + CH])
    e_dem[i:i + CH] = (D.strain_energy(model, p).detach().numpy() / D.EPS**2)

# geometric coordinates for the two hypotheses
d_face = np.minimum(xyz, 1.0 - xyz).min(axis=1)          # distance to the cube boundary
with torch.no_grad():
    Fv = tpms.F(2 * np.pi * torch.tensor(xyz)).numpy()
depth = np.clip(np.abs(Fv) / T_PARAM, 0, 1)              # 0 mid-surface, 1 free surface

solid = np.abs(Fv) < T_PARAM
out = {"family": FAMILY, "n_nodes": int(len(xyz)), "n_solid": int(solid.sum()),
       "mean_ratio_all": float(e_dem.mean() / e_fe.mean()),
       "mean_ratio_solid": float(e_dem[solid].mean() / e_fe[solid].mean())}


def profile(coord, edges, mask):
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = mask & (coord >= lo) & (coord < hi)
        if m.sum() < 50:
            continue
        rows.append({"lo": float(lo), "hi": float(hi), "n": int(m.sum()),
                     "fe": float(e_fe[m].mean()), "dem": float(e_dem[m].mean()),
                     "ratio": float(e_dem[m].mean() / e_fe[m].mean()),
                     "energy_share_fe": float(e_fe[m].sum() / e_fe[solid].sum())})
    return rows


out["by_distance_to_face"] = profile(d_face, np.array([0, .02, .05, .1, .15, .2, .3, .5]), solid)
out["by_depth_in_wall"] = profile(depth, np.linspace(0, 1, 9), solid)

json.dump(out, open(os.path.join(HERE, f"demfe_{FAMILY}.json"), "w"), indent=2)
print(f"{FAMILY}: DEM/FE mean energy ratio (solid nodes) = {out['mean_ratio_solid']:.3f}")
print("  distance to cube face:")
for r in out["by_distance_to_face"]:
    print(f"    {r['lo']:.2f}-{r['hi']:.2f}  n={r['n']:6d}  ratio {r['ratio']:.3f}"
          f"   (holds {100*r['energy_share_fe']:.0f}% of FE energy)")
print("  depth in wall (0 = mid-surface, 1 = free surface):")
for r in out["by_depth_in_wall"]:
    print(f"    {r['lo']:.2f}-{r['hi']:.2f}  n={r['n']:6d}  ratio {r['ratio']:.3f}"
          f"   (holds {100*r['energy_share_fe']:.0f}% of FE energy)")
