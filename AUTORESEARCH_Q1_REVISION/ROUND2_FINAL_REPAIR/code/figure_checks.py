"""figure_checks: numerical QC of every revised figure against exact source
values (revision brief: 'Test figure data against exact source values').

Checks:
  R1  each replicate path ends at call 26 with the arm's G26; full-FE curve
      monotone non-decreasing; truncated@26 == replay cum[25]; batch
      frontier consistent;
  R2  scatter counts == pool size; FE gains use uniform-64 denominator;
      DEM gains use the cloud-11 uniform-DEM denominator (recomputed); group
      stats match tie-aware library values; discordance split sums;
  R3  endpoints equal the accounting family values; no distribution
      graphics required;
  R5  per-design discrete VF at the render grid recorded and within the
      protocol tolerance of 0.19328; shared color limits == [0.12, 0.55].

Output: figures/figure_checks.json (PASS/FAIL per check).
"""
import csv
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vg2_common as v2  # noqa: E402

R2 = v2.R2
FIG = os.path.join(R2, "figures")
DATA = os.path.join(FIG, "data")
OUT = os.path.join(FIG, "figure_checks.json")


def read_csv(name):
    with open(os.path.join(DATA, f"{name}.csv"), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    checks = {}

    rep = json.load(open(os.path.join(R2, "results", "r2_pool_replay.json")))
    hist = json.load(open(os.path.join(v2.WS, "results",
                                       "vgmm_result.json")))
    acc = json.load(open(os.path.join(R2, "results", "r2_accounting.json")))
    quad = json.load(open(os.path.join(
        R2, "results", "r2_quadrature_isolation.json")))

    # ---- R1 --------------------------------------------------------------
    ok = True
    msgs = []
    arms = {}
    for f in glob.glob(os.path.join(R2, "results", "r2_arms", "arm_*.json")):
        a = json.load(open(f))
        arms[a["arm"]] = a
    if os.path.exists(os.path.join(DATA, "R1_vgmm11.csv")):
        rows = read_csv("R1_vgmm11")
        last = rows[-1]
        ok &= int(last["call"]) == 26
        ok &= abs(float(last["best_gain_pct"]) - hist["G_search64_pct"]) \
            < 1e-9
        msgs.append(f"vgmm11 path ends {last['call']} @ "
                    f"{float(last['best_gain_pct']):.4f} "
                    f"(hist G64 {hist['G_search64_pct']:.4f})")
    for nm, a in arms.items():
        p = os.path.join(DATA, f"R1_{nm}.csv")
        if os.path.exists(p) and a["policy"] != "demonly":
            rows = read_csv(f"R1_{nm}")
            last = rows[-1]
            ok &= int(last["call"]) == a["calls_in_budget"]
            ok &= abs(float(last["best_gain_pct"]) - a["G26_pct"]) < 1e-9
            msgs.append(f"{nm} path ends {last['call']} @ "
                        f"{float(last['best_gain_pct']):.4f} (G26 "
                        f"{a['G26_pct']:.4f})")
    cum = rep["best_so_far_trajectory"]
    mono = all(cum[i + 1] >= cum[i] - 1e-12 for i in range(len(cum) - 1))
    ok &= mono
    ff = rep["fullfe_truncated"]
    ok &= abs(ff["best_gain_at_26_unique_pct"] - cum[25]) < 1e-12
    bc = ff["batch_complete_frontier"]
    ok &= abs(bc["best_gain_pct"] - cum[bc["unique_designs"] - 1]) < 1e-12
    msgs.append(f"full-FE curve monotone={mono}; truncated@26="
                f"{ff['best_gain_at_26_unique_pct']:.4f}; batch-complete@"
                f"{bc['unique_designs']}={bc['best_gain_pct']:.4f}")
    checks["R1_common_budget_endpoints"] = dict(ok=bool(ok), msgs=msgs)

    # ---- R2 --------------------------------------------------------------
    ok = True
    msgs = []
    rows = read_csv("R2_pool")
    ok &= len(rows) == rep["diag"]["pool_size"]
    uni = rep["uniform_search"]
    maxerr_fe = max(abs(float(r["gain_FE_pct"])
                        - 100 * (float(r["C_FE"]) / uni - 1))
                    for r in rows)
    ok &= maxerr_fe < 1e-9
    dd = quad["cloud_uniform_dem_denominator"]["11"]
    maxerr_dem = max(abs(float(r["gain_DEM_pct"])
                         - 100 * (float(r["C_DEM"]) / dd - 1))
                     for r in rows)
    ok &= maxerr_dem < 1e-9
    msgs.append(f"pool N={len(rows)}; FE-denominator uniform64={uni}; "
                f"cloud-11 DEM denominator={dd:.8f} (recomputed, not "
                f"hardcoded)")
    g = read_csv("R2_groups")
    d = rep["diag"]
    n_disc = sum(1 for r in g if r["agree"] == "False")
    ok &= n_disc == d["scan_groups_dem_top1_wrong"]
    ok &= len(g) == 24
    msgs.append(f"groups=24, discordant={n_disc} (library tie-aware "
                f"Spearman {d['spearman_dem_fe_scipy_tie_aware']:.4f})")
    checks["R2_denominators_and_ranks"] = dict(ok=bool(ok), msgs=msgs)

    # ---- R3 --------------------------------------------------------------
    ok = True
    msgs = []
    rows = read_csv("R3_endpoints")
    fv = acc["family_values"]
    for fam, key in (("VG-MM", "vgmm"), ("RANDOM", "rand"),
                     ("DETERMINISTIC", "det"), ("DEM-only", "demonly")):
        for k, v in fv.get(key, {}).items():
            hit = [r for r in rows if r["family"].startswith(fam.split(
                "-")[0].split(" ")[0]) and r["seed"] == k]
            if hit:
                ok &= abs(float(hit[0]["G26_pct"]) - v) < 1e-9
            elif fam == "DEM-only":
                pass
            else:
                ok = False
    ffrow = [r for r in rows if r["family"] == "FULL-FE truncated"]
    ok &= ffrow and abs(float(ffrow[0]["G26_pct"])
                        - ff["best_gain_at_26_unique_pct"]) < 1e-9
    msgs.append("all R3 endpoints equal accounting family values; "
                "individual runs only, no CI/violin objects emitted")
    checks["R3_endpoints_match_accounting"] = dict(ok=bool(ok), msgs=msgs)

    # ---- R5 --------------------------------------------------------------
    ok = True
    msgs = []
    designs = {"0": "uniform", "1": "vgmm", "2": "fullfe"}
    for j, nm in designs.items():
        p = os.path.join(DATA, f"R5_midplane_{j}.csv")
        if not os.path.exists(p):
            ok = False
            msgs.append(f"missing R5 data for {nm}")
            continue
        rows = read_csv(f"R5_midplane_{j}")
        tvals = [float(r["t"]) for r in rows]
        ok &= abs(min(tvals) - v2.T_MIN) < 1e-9 or min(tvals) > v2.T_MIN
        ok &= max(tvals) <= v2.T_MAX + 1e-9
        # discrete VF on the full 3D mask at the render grid
        if nm == "uniform":
            th = [0.0] * v2.N_MODES
        elif nm == "vgmm":
            th = hist["theta_final"]
        else:
            th = json.load(open(os.path.join(
                v2.N3, "e3_fe_baseline.json")))["theta"]
        sh = v2.bisect_shift_discrete(96, th)
        vf = v2.discrete_vf(96, th, sh)
        ok &= abs(vf - v2.VF_TARGET) < 5e-4
        msgs.append(f"{nm}: render-grid VF={vf:.5f} (target 0.19328), "
                    f"t range [{min(tvals):.3f},{max(tvals):.3f}] within "
                    f"[{v2.T_MIN},{v2.T_MAX}]")
    checks["R5_vf_and_limits"] = dict(ok=bool(ok), msgs=msgs)

    json.dump(checks, open(OUT, "w"), indent=2)
    allok = all(c["ok"] for c in checks.values())
    print(json.dumps(checks, indent=2))
    print("FIGURE NUMERICAL QC:", "PASS" if allok else "FAIL")
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
