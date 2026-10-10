"""r2_arms: controlled-comparison arm driver (ROUND2 plan Section 3).

Arms (all share initialization, mode order, bounds, volume enforcement,
FE-acceptance rule, and the 26-counted-call budget):
  B-VGMM(c)  python r2_arms.py vgmm 12|13      (c=11 is the historical run)
  B-RAND(r)  python r2_arms.py rand 11|12|13
  B-DET      python r2_arms.py det
  B-DEMONLY(c) python r2_arms.py demonly 11|12|13  (endpoint audit only)

Output: results/r2_arms/arm_<name>.json (fails if the file exists).
Logs: logs/arm_<name>.log (append by the shell redirect).

Implementation guarantees (PI plan compliance):
  * proposal functions see NO FE values of unqueried candidates;
  * every distinct candidate query counts as one call, cache hit or not;
  * new solves respect the global <=200 cap (vg2_common budget guard);
  * phase timings recorded per checkpoint (score_s, bisect_s, mesh_s,
    solve_s, cache_s);
  * the historical VG-MM seed-11 run is NOT rerun.
"""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vg2_common as v2  # noqa: E402

R2 = v2.R2
ARMS_DIR = os.path.join(R2, "results", "r2_arms")
LOG_DIR = os.path.join(R2, "logs")
os.makedirs(ARMS_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

DET_ORDER = [-0.22, 0.22, -0.165, 0.165, -0.11, 0.11, -0.055, 0.055]
CALL_BUDGET = 26


class Arm:
    def __init__(self, name, policy_kind, seed=None):
        self.name = name
        self.policy_kind = policy_kind
        self.seed = seed
        self.calls = 0
        self.n_queries = 0
        self.rng = (np.random.default_rng(seed)
                    if policy_kind == "rand" else None)
        self.scorer = None
        self.timing = {"score_s": 0.0, "bisect_s": 0.0, "mesh_s": 0.0,
                       "solve_s": 0.0, "cache_s": 0.0}
        self.queried = {}     # key -> fe record (this arm's queries only)

    # -- FE layer -----------------------------------------------------------
    def fe_call(self, N, theta, shift, purpose):
        if self.calls >= CALL_BUDGET:
            raise RuntimeError(f"{self.name}: call budget {CALL_BUDGET} hit")
        self.calls += 1
        self.n_queries += 1
        rec = v2.fe_solve2(N, theta, shift, purpose)
        for k in ("cache_s", "mesh_s", "solve_s"):
            if k in rec:
                self.timing[k] += rec[k]
        self.queried[rec["key"]] = rec
        return rec

    def fe_endpoint_audit(self, N, theta, shift, purpose):
        """Calls OUTSIDE the 26-call budget (declared in the plan: DEM-only
        endpoint audits). Still counted in raw/unique/new totals."""
        self.n_queries += 1
        rec = v2.fe_solve2(N, theta, shift, purpose)
        self.queried.setdefault(rec["key"], rec)
        return rec

    # -- proposal functions (NO access to unqueried FE labels) ---------------
    def proposal_vgmm(self, theta, m):
        trials = []
        for cand in v2.GRID:
            tr = list(theta)
            tr[m] = float(cand)
            t0 = time.perf_counter()
            sh = v2.bisect_shift_discrete(64, tr)
            self.timing["bisect_s"] += time.perf_counter() - t0
            t0 = time.perf_counter()
            sc = self.scorer(tr, sh)
            self.timing["score_s"] += time.perf_counter() - t0
            trials.append((sc, float(cand), tr))
        trials.sort(key=lambda p: -p[0])
        top_sc, top_val, _ = trials[0]
        for sc, val, tr in trials:
            if val != theta[m]:
                return dict(value=val, theta=tr,
                            selected_dem_score=sc, top_dem_score=top_sc,
                            top_coeff=top_val,
                            incumbent_coeff=float(theta[m]))
        return None

    def proposal_rand(self, theta, m):
        pool = [float(c) for c in v2.GRID if float(c) != theta[m]]
        val = float(self.rng.choice(pool))
        tr = list(theta)
        tr[m] = val
        return dict(value=val, theta=tr, selected_dem_score=None,
                    top_dem_score=None, top_coeff=None,
                    incumbent_coeff=float(theta[m]))

    def proposal_det(self, theta, m, k):
        start = k % len(DET_ORDER)
        val = None
        for off in range(len(DET_ORDER)):
            cand = DET_ORDER[(start + off) % len(DET_ORDER)]
            if cand != theta[m]:
                val = cand
                break
        tr = list(theta)
        tr[m] = val
        return dict(value=val, theta=tr, selected_dem_score=None,
                    top_dem_score=None, top_coeff=None,
                    incumbent_coeff=float(theta[m]))

    def proposal_demonly(self, theta, m):
        """Faithful DEM-only greedy: argmax INCLUDES the incumbent; move only
        if strictly higher-scoring (never forces a lower-scoring move)."""
        incumbent_val = float(theta[m])
        incumbent_sc = None
        trials = []
        for cand in v2.GRID:
            tr = list(theta)
            tr[m] = float(cand)
            t0 = time.perf_counter()
            sh = v2.bisect_shift_discrete(64, tr)
            self.timing["bisect_s"] += time.perf_counter() - t0
            t0 = time.perf_counter()
            sc = self.scorer(tr, sh)
            self.timing["score_s"] += time.perf_counter() - t0
            if abs(float(cand) - incumbent_val) < 1e-9:
                incumbent_sc = sc
            trials.append((sc, float(cand), tr))
        trials.sort(key=lambda p: -p[0])
        top_sc, top_val, tr = trials[0]
        # Strict improvement requirement: stay on tie with incumbent
        if top_val != incumbent_val and incumbent_sc is not None and top_sc > incumbent_sc:
            return dict(value=top_val, theta=tr,
                        selected_dem_score=top_sc, top_dem_score=top_sc,
                        top_coeff=top_val,
                        incumbent_coeff=incumbent_val)
        return dict(value=incumbent_val, theta=list(theta),
                    selected_dem_score=top_sc, top_dem_score=top_sc,
                    top_coeff=top_val,
                    incumbent_coeff=incumbent_val, stay=True)


def run_arm(kind, seed):
    name = f"{kind}{'' if seed is None else seed}"
    out_path = os.path.join(ARMS_DIR, f"arm_{name}.json")
    if os.path.exists(out_path):
        raise SystemExit(f"refusing to overwrite existing {out_path}")
    arch = json.load(open(os.path.join(v2.N3, "e3_fe_baseline.json")))
    UNI64, UNI96 = v2.UNI_64, v2.UNI_96
    t_wall = time.time()
    arm = Arm(name, kind, seed)
    if kind in ("vgmm", "demonly"):
        t0 = time.perf_counter()
        arm.scorer = v2.make_scorer(cloud_seed=seed)
        arm.timing["scorer_init_s"] = time.perf_counter() - t0

    log = []
    theta = [0.0] * v2.N_MODES
    t0 = time.perf_counter()
    sh_inc = v2.bisect_shift_discrete(64, theta)
    arm.timing["bisect_s"] += time.perf_counter() - t0
    base = arm.fe_call(64, theta, sh_inc, "baseline_uniform")
    best_FE = base["value"]
    incumbent_FE = best_FE
    accepted = rejected = 0
    harmful_rejected = []

    if kind == "demonly":
        # DEM-only: no FE in loop; argmax includes incumbent; never forces
        for s in range(v2.SWEEPS):
            for m in range(v2.N_MODES):
                prop = arm.proposal_demonly(theta, m)
                rec = dict(sweep=s, mode=m,
                           dem_pick=prop["value"],
                           dem_score_selected=prop["selected_dem_score"],
                           action="STAY" if prop.get("stay") else "DEMMOVE")
                if not prop.get("stay"):
                    theta = prop["theta"]
                log.append(rec)
                print(f"s{s} m{m:2d}: dem {prop['value']:+.3f} "
                      f"({rec['action']})", flush=True)
    else:
        for s in range(v2.SWEEPS):
            for m in range(v2.N_MODES):
                k = s * v2.N_MODES + m
                if kind == "vgmm":
                    prop = arm.proposal_vgmm(theta, m)
                elif kind == "rand":
                    prop = arm.proposal_rand(theta, m)
                elif kind == "det":
                    prop = arm.proposal_det(theta, m, k)
                else:
                    raise SystemExit(f"unknown kind {kind}")
                rec = dict(sweep=s, mode=m, pick=prop["value"],
                           selected_dem_score=prop["selected_dem_score"],
                           top_dem_score=prop["top_dem_score"],
                           top_coeff=prop["top_coeff"],
                           incumbent_coeff=prop["incumbent_coeff"])
                r = arm.fe_call(64, prop["theta"],
                                v2.bisect_shift_discrete(64, prop["theta"]),
                                f"checkpoint_s{s}_m{m}")
                rec.update(fe_val=r["value"], fe_source=r["source"],
                           fe_newly_solved=r["newly_solved"],
                           incumbent_FE=incumbent_FE,
                           calls_after=arm.calls)
                if r["value"] > best_FE:
                    theta = prop["theta"]
                    best_FE = r["value"]
                    rec["action"] = "ACCEPT"
                    accepted += 1
                else:
                    rec["action"] = "REJECT"
                    rejected += 1
                    g = 100 * (r["value"] / UNI64 - 1)
                    if g < -5.0:
                        harmful_rejected.append(
                            dict(sweep=s, mode=m, gain_pct=g))
                incumbent_FE = best_FE
                log.append(rec)
                print(f"s{s} m{m:2d}: pick {prop['value']:+.3f} "
                      f"FE {r['value']:.6f} ({rec['action']}) "
                      f"best {best_FE:.6f} "
                      f"({time.time()-t_wall:.0f}s)", flush=True)

    # final incumbent: search-grid value + (in-budget) confirm at 96
    sh_w = v2.bisect_shift_discrete(64, theta)
    k64 = v2.cand_key(64, theta, sh_w)
    if k64 in arm.queried:
        c_win_64 = arm.queried[k64]["value"]
        r64 = dict(source=arm.queried[k64]["source"], newly_solved=False)
    else:
        r = arm.fe_call(64, theta, sh_w, "winner_64_read")
        c_win_64 = r["value"]
        r64 = dict(source=r["source"], newly_solved=r["newly_solved"])
    if kind == "demonly":
        # endpoint audits (outside budget, declared): 64 and 96
        r = arm.fe_endpoint_audit(64, theta, sh_w, "demonly_endpoint_64")
        c_win_64 = r["value"]
        r64 = dict(source=r["source"], newly_solved=r["newly_solved"])
        sh96 = v2.bisect_shift_discrete(96, theta)
        r96 = arm.fe_endpoint_audit(96, theta, sh96, "demonly_endpoint_96")
        c_win_96 = r96["value"]
        calls_in_budget = 0
    else:
        sh96 = v2.bisect_shift_discrete(96, theta)
        r = arm.fe_call(96, theta, sh96, "winner_confirm_96")
        c_win_96 = r["value"]
        r96 = dict(source=r["source"], newly_solved=r["newly_solved"])
        calls_in_budget = arm.calls

    unique_keys = set(arm.queried)
    new_solves = sum(1 for r_ in arm.queried.values() if r_["newly_solved"])
    out = dict(
        arm=name, policy=kind, seed=seed,
        plan="ROUND2_PLAN.md (frozen 2026-09-13T14:41:05Z sha256="
             "e56fdf7f882a45d39c57a921b2c1be6c8f3377dc55ee93eec5f15995947d9cb5)",
        theta_final=[float(x) for x in theta],
        C_final_64=c_win_64, C_final_96=c_win_96,
        G26_pct=100 * (c_win_64 / UNI64 - 1),
        G_confirm96_pct=100 * (c_win_96 / UNI96 - 1),
        calls_in_budget=calls_in_budget,
        raw_query_invocations=arm.n_queries,
        unique_problems_queried=len(unique_keys),
        new_solves=new_solves,
        accepted=accepted, rejected=rejected,
        harmful_rejected=harmful_rejected,
        timing_s={k: round(x, 2) for k, x in arm.timing.items()},
        wall_s=round(time.time() - t_wall, 1),
        calls=[r_ for r_ in arm.queried.values()],
        log=log,
    )
    v2.write_json_new(out_path, out)
    slim = {k: out[k] for k in out if k not in ("calls", "log")}
    print(json.dumps(slim, indent=2), flush=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    kind = sys.argv[1]
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else None
    run_arm(kind, seed)
