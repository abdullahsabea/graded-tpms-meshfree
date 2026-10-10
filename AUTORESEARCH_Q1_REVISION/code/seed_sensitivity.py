"""EXP-03 (reduced, per 03_candidate_contributions / 04_preregistered_plan):
sensitivity of the VG-MM DEM ranking and greedy path to the fixed quadrature
cloud seed. DEM-only: the same frozen protocol is replayed with cloud seeds
12 and 13 (no FE calls); we report (a) per-checkpoint pick agreement with the
canonical seed-11 run, (b) whether the final returned design changes, and
(c) DEM-score spread of the seed-11 picks under the alternative clouds.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vgmm_common as vc  # noqa: E402

WS = vc.WS
canon = json.load(open(os.path.join(WS, "results", "vgmm_result.json")))
UNI = canon["uniform_64"]


def greedy_path(seed):
    score = vc.make_scorer(cloud_seed=seed)
    theta = [0.0] * vc.N_MODES
    picks = []
    best_dem = score(theta, vc.bisect_shift_discrete(64, theta))
    for s in range(vc.SWEEPS):
        for m in range(vc.N_MODES):
            trials = []
            for cand in vc.GRID:
                tr = list(theta); tr[m] = float(cand)
                trials.append(tr)
            scored = sorted(
                ((score(tr, vc.bisect_shift_discrete(64, tr)), tr)
                 for tr in trials), key=lambda p: -p[0])
            cand = next((tr for sc, tr in scored if tr[m] != theta[m]), None)
            picks.append(dict(sweep=s, mode=m,
                              pick=None if cand is None else float(cand[m])))
            if cand is not None:
                theta = cand
    final_dem = score(theta, vc.bisect_shift_discrete(64, theta))
    return picks, theta, final_dem


out = {"seeds": {}}
canon_picks = [dict(sweep=r["sweep"], mode=r["mode"], pick=r.get("pick"))
               for r in canon["log"] if "pick" in r or r.get("action") == "no_move_all_equal_incumbent"]
canon_map = {(r["sweep"], r["mode"]): r.get("pick") for r in canon["log"]}
canon_final_theta = canon["theta_final"]

for seed in (12, 13):
    picks, theta_f, final_dem = greedy_path(seed)
    agree = sum(1 for p in picks
                if ((p["pick"] is None and canon_map[(p["sweep"], p["mode"])] is None)
                    or (p["pick"] is not None
                        and abs((canon_map[(p["sweep"], p["mode"])] or 9e9) - p["pick"]) < 1e-12)))
    same_design = bool(np.allclose(theta_f, canon_final_theta, atol=1e-12))
    out["seeds"][seed] = {
        "checkpoints": len(picks),
        "pick_agreement_with_seed11": agree,
        "pick_agreement_rate": agree / len(picks),
        "final_theta": [float(x) for x in theta_f],
        "final_theta_same_as_seed11": same_design,
        "final_dem_score": final_dem,
        "final_dem_score_implied_gain_pct": 100 * (final_dem / 0.11430107802152634 - 1),
    }
    print(seed, json.dumps(out["seeds"][seed]), flush=True)

canon_final_dem = None
sc = vc.make_scorer(cloud_seed=11)
canon_final_dem = sc(canon_final_theta,
                     vc.bisect_shift_discrete(64, canon_final_theta))
out["seed11_final_dem_score"] = canon_final_dem
out["dem_score_spread_final_design_pct"] = None
vals = [canon_final_dem] + [out["seeds"][s]["final_dem_score"] for s in (12, 13)]
out["dem_score_spread_final_design_pct"] = float(100 * (max(vals) - min(vals)) / np.mean(vals))
json.dump(out, open(os.path.join(WS, "results", "seed_sensitivity.json"), "w"),
          indent=2)
print("spread_pct", out["dem_score_spread_final_design_pct"])
