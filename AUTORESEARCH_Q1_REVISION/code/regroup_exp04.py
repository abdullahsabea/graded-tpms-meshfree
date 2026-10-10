"""Post-processing fix for EXP-04: recompute the per-scan-group discordance
from the validated pool in pool_replay.json (24/24 reconstruction, 0 missing
keys). No new computation of solves or scores; pure regrouping.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vgmm_common as vc  # noqa: E402

WS = vc.WS
rep = json.load(open(os.path.join(WS, "results", "pool_replay.json")))
pool = rep["pool"]
pool_by_key = {p["key"]: p for p in pool}
arch = json.load(open(os.path.join(vc.N3, "e3_fe_baseline.json")))
search_N = arch["search_N"]
uni_val = arch["C1111_uniform_search"]

groups = []
theta = [0.0] * vc.N_MODES
nmiss = 0
for entry in arch["history"]:
    s, m = entry["sweep"], entry["mode"]
    tri, vfe_g, vdem_g = [], [], []
    for cand in vc.GRID:
        tr = list(theta); tr[m] = float(cand)
        sh = vc.bisect_shift_discrete(search_N, tr)
        k = vc.cand_key(search_N, tr, sh)
        p = pool_by_key.get(k)
        if p is None:
            nmiss += 1
            continue
        tri.append(k); vfe_g.append(p["C_FE"]); vdem_g.append(p["C_DEM"])
    sh_inc = vc.bisect_shift_discrete(search_N, theta)
    k = vc.cand_key(search_N, theta, sh_inc)
    p = pool_by_key.get(k)
    if p is not None:
        tri.append(k); vfe_g.append(p["C_FE"]); vdem_g.append(p["C_DEM"])
    if len(vfe_g) >= 2:
        groups.append(dict(sweep=s, mode=m,
                           fe_top1=tri[int(np.argmax(vfe_g))],
                           dem_top1=tri[int(np.argmax(vdem_g))],
                           agree=bool(int(np.argmax(vfe_g)) == int(np.argmax(vdem_g))),
                           fe_best_gain=float(100 * (max(vfe_g) / uni_val - 1)),
                           dem_pick_fe_gain=float(100 * (vfe_g[int(np.argmax(vdem_g))] / uni_val - 1))))
    theta[m] = entry["pick"]

disc = [g for g in groups if not g["agree"]]
diag = rep["diag"]
diag["scan_groups"] = len(groups)
diag["scan_groups_dem_top1_wrong"] = len(disc)
diag["scan_group_discordance_rate"] = len(disc) / len(groups) if groups else None
diag["median_fe_gain_of_dem_picks_in_groups"] = float(np.median([g["dem_pick_fe_gain"] for g in groups])) if groups else None
diag["median_fe_gain_of_fe_picks_in_groups"] = float(np.median([g["fe_best_gain"] for g in groups])) if groups else None
diag["groups_missing_keys"] = nmiss
rep["groups"] = groups
json.dump(rep, open(os.path.join(WS, "results", "pool_replay.json"), "w"),
          indent=2)
print(json.dumps({k: diag[k] for k in
                  ["scan_groups", "scan_groups_dem_top1_wrong",
                   "scan_group_discordance_rate",
                   "median_fe_gain_of_dem_picks_in_groups",
                   "median_fe_gain_of_fe_picks_in_groups",
                   "groups_missing_keys"]}, indent=2))
for g in groups:
    print(f"s{g['sweep']} m{g['mode']:2d} agree={g['agree']} "
          f"fe_pick={g['fe_best_gain']:+.2f}% dem_pick={g['dem_pick_fe_gain']:+.2f}%")
