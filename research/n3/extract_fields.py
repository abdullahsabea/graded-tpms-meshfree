"""Extract nodal fields from a code_aster MED result into a .npz (runs INSIDE
the simvia/code_aster container, where medcoupling lives).

    docker run --rm -v <n3>:/shared simvia/code_aster:stable \
        bash -c 'source /opt/activate.sh; python3 /shared/extract_fields.py <tag>'

Writes /shared/fields_<tag>.npz with:
    xyz    (n,3) node coordinates
    DX,DY,DZ   displacement components
    VMIS       von Mises stress
    ENEL       elastic energy density
"""
import sys
import numpy as np
import medcoupling as mc

tag = sys.argv[1]
path = f"/shared/fields_{tag}.rmed"
data = mc.MEDFileData(path)

mesh = data.getMeshes()[0]
m0 = mesh.getMeshAtLevel(0)
coords = m0.getCoords().toNumPyArray()
out = {"xyz": coords}
# element centroids: every voxel has the same volume, so element quantities are
# an unbiased volume-weighted sample of the solid (nodal ones are not)
try:
    out["cell_xyz"] = m0.computeCellCenterOfMass().toNumPyArray()
except Exception as exc:      # noqa: BLE001
    print("centroids unavailable:", exc, flush=True)

for f in data.getFields():
    name = f.getName()
    f1ts = f[f.getTimeSteps()[0][:2]] if f.getTimeSteps() else f[0]
    da = f1ts.getUndergroundDataArray()
    arr = da.toNumPyArray()
    comps = [c.split("[")[0].strip() for c in da.getInfoOnComponents()]
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    print(f"field {name!r}: shape {arr.shape} components {comps}", flush=True)
    up = name.upper()
    if "DEPL" in up:
        for i, c in enumerate(comps[:3]):
            out[c if c in ("DX", "DY", "DZ") else f"D{i}"] = arr[:, i]
    elif "SIEQ" in up:
        j = next((i for i, c in enumerate(comps) if "VMIS" in c.upper()), 0)
        out["VMIS"] = arr[:, j]
    elif "ENEL_ELEM" in up:
        j = next((i for i, c in enumerate(comps) if "TOTALE" in c.upper()), 0)
        out["ENEL_ELEM"] = arr[:, j]
    elif "ENEL" in up:
        j = next((i for i, c in enumerate(comps) if "TOTALE" in c.upper()), 0)
        out["ENEL"] = arr[:, j]

np.savez_compressed(f"/shared/fields_{tag}.npz", **out)
print("wrote", f"/shared/fields_{tag}.npz",
      {k: v.shape for k, v in out.items()}, flush=True)
