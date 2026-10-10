import numpy as np, medcoupling as mc
d = mc.MEDFileData("/shared/fields_reac_uniform.rmed")
m0 = d.getMeshes()[0].getMeshAtLevel(0)
out = {"xyz": m0.getCoords().toNumPyArray()}
for f in d.getFields():
    ts = f.getTimeSteps()
    f1 = f[ts[0][:2]] if ts else f[0]
    a = f1.getUndergroundDataArray()
    arr = a.toNumPyArray(); comps=[c.split("[")[0].strip() for c in a.getInfoOnComponents()]
    if arr.ndim==1: arr=arr.reshape(-1,1)
    up=f.getName().upper()
    print(f.getName(), arr.shape, comps[:4], flush=True)
    if "REAC" in up:
        for i,c in enumerate(comps[:3]): out["R"+c[-1]] = arr[:,i]
    elif "ENEL_ELEM" in up:
        out["ENEL_ELEM"]=arr[:,0]
np.savez_compressed("/shared/fields_reac_uniform.npz", **out)
print("ok", {k:v.shape for k,v in out.items()})
