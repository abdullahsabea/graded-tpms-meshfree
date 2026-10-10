"""EXP-01 pilot: smallest runs that can falsify feasibility of EXP-02.

P1  DEM scorer anchor: recompute the soft C1111 at the archived coordinate-
    search optimum (e3_coord_search.json) and compare with the archived
    0.13524633646011353. Tolerance 1% (scorer is a reimplementation; the
    original Stage-2 script is not preserved in the repo - provenance gap
    recorded in the intake).
P2  Legacy cache/hash path: fe_solve(64, zeros, bisect64(zeros)) must return
    the archived uniform value 0.10528125601 from research/n3/febase.
P3  Fresh docker solve: one NEW candidate (not in any cache) solved at 64^3;
    verifies the docker code_aster path end to end.
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vgmm_common as vc  # noqa: E402

out = {"P1": {}, "P2": {}, "P3": {}}

# P1 -----------------------------------------------------------------------
arch = json.load(open(os.path.join(vc.N3, "e3_coord_search.json")))
theta_a = arch["theta"]; shift_a = arch["t0shift"]
score = vc.make_scorer(cloud_seed=11)
t0 = time.time()
s_val = score(theta_a, shift_a)
out["P1"] = {"archived_soft_C": arch["C1111"], "recomputed_soft_C": s_val,
             "rel_diff_pct": 100 * abs(s_val - arch["C1111"]) / arch["C1111"],
             "scorer_seconds": time.time() - t0}
print("P1", json.dumps(out["P1"]), flush=True)

# P2 -----------------------------------------------------------------------
theta0 = list(np.zeros(vc.N_MODES))
sh0 = vc.bisect_shift_discrete(64, theta0)
v0, key0, legacy0, new0 = vc.fe_solve(64, theta0, sh0)
out["P2"] = {"shift": sh0, "key": key0, "value": v0,
             "archived": 0.10528125601,
             "abs_diff": abs(v0 - 0.10528125601),
             "from_legacy_cache": legacy0, "newly_solved": new0}
print("P2", json.dumps(out["P2"]), flush=True)

# P3 -----------------------------------------------------------------------
# off-grid value 0.075 guarantees the candidate was never evaluated by the
# archived FE-in-loop search (which used only the 9-point grid and incumbent
# states built from grid values). First pilot choice 0.055 turned out to be
# an archived sweep-0/mode-2 trial - a pilot-choice error, corrected here.
theta_p = list(np.zeros(vc.N_MODES)); theta_p[2] = 0.075
sh_p = vc.bisect_shift_discrete(64, theta_p)
kp = vc.cand_key(64, theta_p, sh_p)
pre_existing = os.path.exists(os.path.join(vc.FE_LEGACY, f"oute_{kp}.mess"))
t0 = time.time()
vp, keyp, legp, newp = vc.fe_solve(64, theta_p, sh_p)
out["P3"] = {"theta": theta_p, "shift": sh_p, "key": keyp,
             "C1111": vp, "pre_existing": pre_existing,
             "newly_solved": newp, "solve_seconds": time.time() - t0}
print("P3", json.dumps(out["P3"]), flush=True)

# gate ----------------------------------------------------------------------
g1 = out["P1"]["rel_diff_pct"] < 1.0
g2 = out["P2"]["abs_diff"] < 1e-9
g3 = (not out["P3"]["pre_existing"]) and out["P3"]["newly_solved"] \
     and 0.05 < out["P3"]["C1111"] < 0.5
out["GATE"] = {"P1_scorer_pass": bool(g1), "P2_cache_pass": bool(g2),
               "P3_docker_pass": bool(g3),
               "PILOT_PASS": bool(g1 and g2 and g3)}
json.dump(out, open(os.path.join(vc.WS, "results", "pilot_exp01.json"), "w"),
          indent=2)
print("GATE", json.dumps(out["GATE"]), flush=True)
