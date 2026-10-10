"""WP-A2: external uniform gyroid-sheet PBC benchmark.
Fisher et al. 2023 (GitHub jwf23/Equation-Based-Lattice-Structure-Dataset): voxel PBC,
  data say E = 2 GPa, nu = 0.30 (solid C12/C11 = 0.4286, C44 = 0.769 GPa).
Mele et al. 2025 (OSF c2hr4): nTop tet PBC, E = 70 GPa, nu = 0.33; |f| <= t/2, t = 0.6 <-> our t = 0.3.
Ours: body-fitted TETRA10 PBC, N48 M96, E = 1, nu = 0.30."""
import json
import numpy as np
import pandas as pd
import scipy.io as sio
m = sio.loadmat("Gyroid_homogenization_data.mat")
C, VF = m["surf_C"], m["surf_VF"][:, 0] / 100
Cs = C[:, :, 11]
nu_f = Cs[0, 1] / (Cs[0, 0] + Cs[0, 1]); E_f = Cs[3, 3] * 2 * (1 + nu_f)
c_f = np.array([C[0, 0, i] for i in range(4)]) / E_f
lv, lc = np.log(VF[1:4]), np.log(c_f[1:4])
p = np.polyfit(lv, lc, 2)
ours_v, ours_c = 0.19388831571, 0.098024135878
fisher_at_ours = float(np.exp(np.polyval(p, np.log(ours_v))))
import os  # noqa: E402
MELE = "homogenization_results.csv"            # file name on OSF (doi:10.17605/OSF.IO/C2HR4)
if not os.path.exists(MELE):
    MELE = "mele_homogenization_results.csv"   # local copy, same file renamed
d = pd.read_csv(MELE); d.columns = [c.strip() for c in d.columns]
g = d[(d["%GY"] == 1.0) & (d["t"].isin([0.5, 0.6, 0.7]))].sort_values("t")
mv, mc = g["VF"].values, g["C11"].values / 70000.0
pm = np.polyfit(np.log(mv), np.log(mc), 2)
mele_at_ours = float(np.exp(np.polyval(pm, np.log(ours_v))))
out = dict(fisher=dict(E=float(E_f), nu=float(nu_f), VF=VF[1:4].tolist(), C11_over_E=c_f[1:4].tolist(),
                       res_voxels=m["surf_RES"][1:4, 0].tolist(), C11_over_E_at_our_Vf=fisher_at_ours,
                       ours_over_fisher=ours_c / fisher_at_ours),
           mele=dict(E=70000.0, nu=0.33, t=g["t"].tolist(), VF=mv.tolist(), C11_over_E=mc.tolist(),
                     C11_over_E_at_our_Vf=mele_at_ours, ours_nu030_over_mele_nu033=ours_c / mele_at_ours),
           ours=dict(Vf=ours_v, C1111_PBC=ours_c, nu=0.30))
json.dump(out, open("a2_results.json", "w"), indent=2)
print(json.dumps(out, indent=1))
