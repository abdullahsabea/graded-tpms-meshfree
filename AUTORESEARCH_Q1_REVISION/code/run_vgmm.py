"""EXP-02: VG-MM primary run (preregistered in 04_preregistered_plan.md).

Frozen protocol: greedy 2-sweep x 12-mode coordinate search on the same
grid/modes/bounds as e3_fe_baseline.py; the frozen conditional-DEM soft
scorer (fixed 50k cloud, seed 11) ranks the 9 trials per mode; ONLY the
DEM-selected non-incumbent trial is FE-evaluated (64^3, discrete-Vf
calibrated); the move is ACCEPTED only if its FE value strictly exceeds the
FE-best incumbent. Winner confirmed at 96^3 against the archived uniform
96^3 value. Budget: <=30 FE calls (each distinct candidate query counts,
cache hits included).
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vgmm_common as vc  # noqa: E402

WS = vc.WS
arch = json.load(open(os.path.join(vc.N3, "e3_fe_baseline.json")))
UNI_64 = arch["C1111_uniform_search"]
UNI_96 = arch["C1111_uniform_confirm"]
SEARCH_N, CONFIRM_N = arch["search_N"], arch["confirm_N"]

calls = []          # every FE query (value, key, legacy, newly_solved)
log = []            # per-checkpoint records

def fe_call(N, theta, shift, purpose):
    v, k, leg, new = vc.fe_solve(N, theta, shift)
    calls.append(dict(N=N, key=k, value=v, legacy=leg, newly_solved=new,
                      purpose=purpose))
    return v

score = vc.make_scorer(cloud_seed=11)

theta = [0.0] * vc.N_MODES
sh_inc = vc.bisect_shift_discrete(SEARCH_N, theta)
best_FE = fe_call(SEARCH_N, theta, sh_inc, "baseline_uniform")
incumbent_FE = best_FE
t_start = time.time()

for s in range(vc.SWEEPS):
    for m in range(vc.N_MODES):
        trials = []
        for cand in vc.GRID:
            tr = list(theta); tr[m] = float(cand)
            trials.append(tr)
        scored = sorted(
            ((score(tr, vc.bisect_shift_discrete(SEARCH_N, tr)), tr)
             for tr in trials), key=lambda p: -p[0])
        cand = next((tr for sc, tr in scored
                     if tr[m] != theta[m]), None)
        rec = dict(sweep=s, mode=m,
                   dem_rank_top3=[[round(sc, 6), tr[m]] for sc, tr in scored[:3]])
        if cand is None:
            rec.update(action="no_move_all_equal_incumbent", fe_calls=0)
            log.append(rec)
            print(f"s{s} m{m:2d}: no non-incumbent candidate", flush=True)
            continue
        sh_c = vc.bisect_shift_discrete(SEARCH_N, cand)
        fe_val = fe_call(SEARCH_N, cand, sh_c, f"checkpoint_s{s}_m{m}")
        accepted = fe_val > best_FE
        rec.update(pick=float(cand[m]), dem_score=scored[0][0],
                   fe_val=fe_val, incumbent_FE=incumbent_FE,
                   action="ACCEPT" if accepted else "REJECT",
                   gain_vs_uniform_pct=100 * (fe_val / UNI_64 - 1),
                   fe_calls=1)
        if accepted:
            theta = cand
            best_FE = fe_val
        incumbent_FE = best_FE
        log.append(rec)
        print(f"s{s} m{m:2d}: pick {cand[m]:+.3f} FE {fe_val:.6f} "
              f"({'ACCEPT' if accepted else 'REJECT'}) best {best_FE:.6f} "
              f"({time.time()-t_start:.0f}s)", flush=True)

sh_w = vc.bisect_shift_discrete(CONFIRM_N, theta)
c_win_96 = fe_call(CONFIRM_N, theta, sh_w, "winner_confirm_96")
sh_w64 = vc.bisect_shift_discrete(SEARCH_N, theta)
c_win_64, _, _, _ = vc.fe_solve(SEARCH_N, theta, sh_w64)  # already queried if last checkpoint; read-only reuse

G_confirm = 100 * (c_win_96 / UNI_96 - 1)
G_search = 100 * (c_win_64 / UNI_64 - 1)
n_calls = len(calls)
n_new = sum(1 for c in calls if c["newly_solved"])

out = dict(
    protocol="VG-MM per 04_preregistered_plan.md (frozen 2026-09-13)",
    search_N=SEARCH_N, confirm_N=CONFIRM_N,
    uniform_64=UNI_64, uniform_96=UNI_96,
    theta_final=[float(x) for x in theta],
    C_winner_search64=c_win_64, C_winner_confirm96=c_win_96,
    G_search64_pct=G_search, G_confirm96_pct=G_confirm,
    fe_calls_total=n_calls, fe_calls_new_solves=n_new,
    accept_events=sum(1 for r in log if r.get("action") == "ACCEPT"),
    reject_events=sum(1 for r in log if r.get("action") == "REJECT"),
    calls=calls, log=log,
)
json.dump(out, open(os.path.join(WS, "results", "vgmm_result.json"), "w"),
          indent=2)
print(json.dumps({k: v for k, v in out.items()
                  if k not in ("calls", "log")}, indent=2), flush=True)
