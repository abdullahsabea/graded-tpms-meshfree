"""Training-seed study summary and decomposition of the uniform-gyroid DEM deviation.

dem_seed.py scaled energies by V_SOLID from one 10^6-point Monte Carlo draw
(0.19390), 1.2 standard errors above the converged analytic solid fraction
0.19345 (midpoint quadrature, 600^3-1000^3: 0.19345, 0.19348, 0.19343). C1111 is
linear in V_SOLID, so the seed values are rescaled here; the raw JSON files are
left unchanged. The archived single-thickness model (n3_dem_metrics.json) used
0.1935 and needs no correction beyond 0.03%.

Body-fitted FE: conforming/summarize_conf.py (KUBC, TETRA10, values corrected to
V_f = 0.19328 with exponent 1.21, then moved here to the analytic 0.19345).
Writes n3_dem_seed_summary.json.
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
VF = 0.19345          # analytic gyroid solid fraction at t = 0.3
VT, A = 0.19328, 1.21  # common design volume and volume exponent
VOX, VOX_V = 0.10554, 0.1933  # voxel-FE ladder mean (Table 3) and its V_f

seeds = []
for s in range(5):
    d = json.load(open(os.path.join(HERE, f"n3_dem_seed{s}.json")))
    seeds.append(d["C1111_dem"] * VF / d["V_solid"])
seeds = np.array(seeds)
arch = json.load(open(os.path.join(HERE, "n3_dem_metrics.json")))
arch_c = arch["C1111_dem"] * VF / arch["V_solid"]

conf = json.load(open(os.path.join(HERE, "conforming", "conf_summary.json")))
bf_vt = np.array([conf["kubc"][k]["C_at_VT"] for k in ("N48_M96", "N60_M96", "N72_M96")])
bf = bf_vt * (VF / VT) ** A
vox = VOX * (VF / VOX_V) ** A

out = dict(
    V_analytic=VF,
    dem_seed_C=seeds.tolist(), dem_seed_mean=seeds.mean(), dem_seed_sd=seeds.std(ddof=1),
    dem_archived_C=arch_c,
    fe_bodyfitted_C=bf.tolist(), fe_bodyfitted_mean=bf.mean(),
    fe_voxel_C=vox,
    staircase_pct=100 * (bf.mean() / vox - 1),
    dem_vs_bodyfitted_pct=100 * (seeds.mean() / bf.mean() - 1),
    dem_vs_bodyfitted_sd_pct=100 * seeds.std(ddof=1) / bf.mean(),
    archived_vs_seedmean_pct=100 * (arch_c / seeds.mean() - 1),
    archived_vs_voxel_pct=100 * (arch_c / vox - 1),
)
for k, v in out.items():
    print(f"{k:28s} {np.round(v, 6) if not isinstance(v, list) else np.round(v, 6).tolist()}")
json.dump(out, open(os.path.join(HERE, "n3_dem_seed_summary.json"), "w"), indent=1)
