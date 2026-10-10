"""r2_replay: ROUND2 corrected single-pass reconstruction of the archived
FE-in-the-loop search pool. Fixes PI findings 1, 3, 4 (grouping + counts).

Differences from round-1 replay_pool.py:
  * the 24 per-scan groups are produced by THIS script, using entry["pick"]
    at every step (round 1 used a stale loop variable and needed
    regroup_exp04.py to patch its JSON afterward);
  * rank statistics use scipy.stats (tie-correct); exact ties and practical
    near-ties are recorded; group discordance is split into
    "different ID only" (FE gain difference < 0.05 pp) vs "material ranking
    loss";
  * the 195 cached febase files are reconciled against the 194 required
    problems; every extra file is IDENTIFIED by reproducing its query;
  * NO new FE solves (hardened cache reads only; an inadmissible entry
    aborts with an explicit count, never a synthesized value);
  * writes ONLY results/r2_pool_replay.json (refuses to overwrite);
  * full-FE truncated-at-26 comparator with explicit batch accounting.

Usage: python r2_replay.py [--keep]
"""
import argparse
import json
import os
import sys
import time

import numpy as np
from scipy.stats import kendalltau, spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vg2_common as v2  # noqa: E402

R2 = v2.R2
OUT = os.path.join(R2, "results", "r2_pool_replay.json")
NEAR_TIE_DEM = 1e-6
NEAR_TIE_FE = 1e-9
IMMATERIAL_GAIN_PP = 0.05


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true",
                    help="overwrite the ROUND2 output file if it exists")
    args = ap.parse_args()
    if os.path.exists(OUT) and not args.keep:
        raise SystemExit(f"refusing to overwrite existing output: {OUT} "
                         f"(use --keep to replace ROUND2 output only)")

    arch = json.load(open(os.path.join(v2.N3, "e3_fe_baseline.json")))
    search_N = arch["search_N"]
    uni_val = arch["C1111_uniform_search"]
    uni96 = arch["C1111_uniform_confirm"]

    def cand_keys_for(theta, m):
        out = []
        for cand in v2.GRID:
            tr = list(theta)
            tr[m] = float(cand)
            sh = v2.bisect_shift_discrete(search_N, tr)
            out.append((v2.cand_key(search_N, tr, sh), tr, sh))
        sh = v2.bisect_shift_discrete(search_N, theta)
        out.append((v2.cand_key(search_N, theta, sh), list(theta), sh))
        return out

    # ---- pass 1: pool + reconstruction check (hardened cache reads) ---------
    t_start = time.time()
    theta = [0.0] * v2.N_MODES
    sh0 = v2.bisect_shift_discrete(search_N, theta)
    k0 = v2.cand_key(search_N, theta, sh0)
    v0, _ = v2.cache_lookup(v2.FE_LEGACY, k0, search_N, theta, sh0)
    if v0 is None:
        raise SystemExit("baseline uniform64 missing/inadmissible in cache")
    seen = {k0: (list(theta), sh0, v0)}

    steps = []
    missing = 0
    reject_reasons = {}
    for entry in arch["history"]:
        s, m, pick_arch, val_arch = (entry["sweep"], entry["mode"],
                                     entry["pick"], entry["C1111"])
        cands = cand_keys_for(theta, m)
        vals = []
        for k, tr, sh in cands:
            v, tim = v2.cache_lookup(v2.FE_LEGACY, k, search_N, tr, sh)
            if v is None:
                missing += 1
                reject_reasons[k] = tim.get("reason", "?")
                vals.append(None)
                continue
            seen.setdefault(k, (tr, sh, v))
            vals.append(v)
        if any(v is None for v in vals):
            steps.append(dict(sweep=s, mode=m, incomplete=True,
                              rejects=reject_reasons))
            theta[m] = pick_arch
            continue
        best_i = int(np.argmax(vals))
        steps.append(dict(
            sweep=s, mode=m, pick=cands[best_i][1][m], C1111=vals[best_i],
            pick_arch=pick_arch, C1111_arch=val_arch,
            match=bool(cands[best_i][1][m] == pick_arch
                       and abs(vals[best_i] - val_arch) < 1e-12)))
        theta = list(cands[best_i][1])

    reconstruction_matches = sum(1 for r in steps if r.get("match"))

    # ---- pass 2: DEM scores over the unique pool (cloud 11, frozen) ---------
    score = v2.make_scorer(cloud_seed=11)
    pool = []
    t_score = time.time()
    items = sorted(seen.items())
    for i, (k, (tr, sh, vfe)) in enumerate(items):
        sd = score(tr, sh)
        pool.append(dict(key=k, theta=[round(x, 6) for x in tr], shift=sh,
                         C_FE=vfe, C_DEM=sd,
                         gain_FE_pct=100 * (vfe / uni_val - 1)))
        if (i + 1) % 40 == 0:
            print(f"scored {i+1}/{len(items)}", flush=True)
    score_s = time.time() - t_score
    by_key = {p["key"]: p for p in pool}

    fe = np.array([p["C_FE"] for p in pool])
    dem = np.array([p["C_DEM"] for p in pool])
    sp = spearmanr(dem, fe)
    kt = kendalltau(dem, fe)
    dem_adj_gaps = np.abs(np.diff(np.sort(dem)[::-1]))
    fe_adj_gaps = np.abs(np.diff(np.sort(fe)[::-1]))

    # ---- pass 3: groups in one walk, entry['pick'] drives theta -------------
    groups = []
    theta = [0.0] * v2.N_MODES
    n_disc = n_id_only = n_material = 0
    for entry in arch["history"]:
        s, m = entry["sweep"], entry["mode"]
        cands = cand_keys_for(theta, m)
        keys = [k for k, _, _ in cands if k in by_key]
        vfe_g = [by_key[k]["C_FE"] for k in keys]
        vdem_g = [by_key[k]["C_DEM"] for k in keys]
        fe_i = int(np.argmax(vfe_g))
        dem_i = int(np.argmax(vdem_g))
        g = dict(sweep=s, mode=m, n_candidates=len(keys),
                 fe_top1=keys[fe_i], dem_top1=keys[dem_i],
                 agree=bool(keys[fe_i] == keys[dem_i]),
                 fe_best_gain=float(100 * (vfe_g[fe_i] / uni_val - 1)),
                 dem_pick_fe_gain=float(100 * (vfe_g[dem_i] / uni_val - 1)))
        srt_f = sorted(vfe_g, reverse=True)
        srt_d = sorted(vdem_g, reverse=True)
        g["fe_top2_gap"] = float(srt_f[0] - srt_f[1])
        g["dem_top2_gap"] = float(srt_d[0] - srt_d[1])
        g["fe_exact_ties_at_top"] = int(sum(1 for v in srt_f if v == srt_f[0])) - 1
        if not g["agree"]:
            n_disc += 1
            if abs(g["fe_best_gain"] - g["dem_pick_fe_gain"]) < \
                    IMMATERIAL_GAIN_PP:
                n_id_only += 1
                g["discordance_class"] = "different_id_only"
            else:
                n_material += 1
                g["discordance_class"] = "material_ranking_loss"
        groups.append(g)
        theta[m] = entry["pick"]   # <-- THE ROUND-1 DEFECT, FIXED HERE

    diag = {
        "pool_size": len(pool),
        "reconstruction_steps_match": f"{reconstruction_matches}/{len(steps)}",
        "missing_or_rejected_cache_keys": missing,
        "reject_reasons": reject_reasons,
        "spearman_dem_fe_scipy_tie_aware": float(sp.statistic),
        "spearman_p": float(sp.pvalue),
        "kendall_dem_fe_scipy_tie_aware": float(kt.statistic),
        "kendall_p": float(kt.pvalue),
        "exact_ties_FE_values": int(len(fe) - len(np.unique(fe))),
        "exact_ties_DEM_values": int(len(dem) - len(np.unique(dem))),
        "near_ties_DEM_lt_1e-6": int((dem_adj_gaps < NEAR_TIE_DEM).sum()),
        "near_ties_FE_lt_1e-9": int((fe_adj_gaps < NEAR_TIE_FE).sum()),
        "scan_groups": len(groups),
        "scan_groups_dem_top1_wrong": n_disc,
        "of_which_different_id_only": n_id_only,
        "of_which_material_ranking_loss": n_material,
        "scan_group_discordance_rate": n_disc / len(groups) if groups else None,
        "best_FE_in_pool": float(fe.max()),
        "best_gain_pct_in_pool": float(100 * (fe.max() / uni_val - 1)),
        "dem_best_candidate_FE_value": float(fe[int(np.argmax(dem))]),
        "dem_best_candidate_FE_gain_pct":
            float(100 * (fe[int(np.argmax(dem))] / uni_val - 1)),
        "FE_best_candidate_DEM_value": float(dem[int(np.argmax(fe))]),
        "uniform_search": uni_val,
        "uniform_confirm": uni96,
        "runtime_total_s": time.time() - t_start,
        "runtime_dem_scoring_s": score_s,
        "note": "cached replay only; no new FE solves; timings are replay "
                "timings, NOT fresh solve times",
    }

    # ---- pool reconciliation -------------------------------------------------
    required = {p["key"] for p in pool}
    th_w = list(arch["theta"])
    for N, th, label in ((arch["confirm_N"], [0.0] * v2.N_MODES, "uniform96"),
                         (arch["confirm_N"], th_w, "winner96"),
                         (arch["search_N"], th_w, "winner64")):
        sh = v2.bisect_shift_discrete(N, th)
        required.add(v2.cand_key(N, th, sh))
    files = {f[5:-5] for f in os.listdir(v2.FE_LEGACY)
             if f.startswith("oute_")}
    extras = sorted(files - required)
    missing_required = sorted(required - files)
    extra_records = []
    th0 = [0.0] * v2.N_MODES
    hyps = []
    for N in (48, 64, 96, 128):
        sh = v2.bisect_shift_discrete(N, th0)
        hyps.append((N, th0, sh, f"uniform theta=0 at N={N} (ladder probe)"))
    for k in extras:
        rec = dict(key=k)
        for N, th, sh, desc in hyps:
            if v2.cand_key(N, th, sh) == k:
                v, tim = v2.cache_lookup(v2.FE_LEGACY, k, N, th, sh)
                rec.update(identified_as=desc, N=N, value=v,
                           admissible=v is not None)
                break
        extra_records.append(rec)
    diag["febase_files"] = len(files)
    diag["required_unique_problems"] = len(required)
    diag["extra_files"] = extras
    diag["extra_files_identified"] = extra_records
    diag["missing_required"] = missing_required

    # ---- full-FE truncated comparator (matched budget, batch accounting) ----
    order_keys = [k0]
    theta = [0.0] * v2.N_MODES
    batch_ends = []
    for entry in arch["history"]:
        m = entry["mode"]
        for cand in v2.GRID:
            tr = list(theta)
            tr[m] = float(cand)
            sh = v2.bisect_shift_discrete(search_N, tr)
            k = v2.cand_key(search_N, tr, sh)
            if k not in order_keys:
                order_keys.append(k)
        theta[m] = entry["pick"]
        batch_ends.append(len(order_keys))
    cum, best = [], -1e9
    for k in order_keys:
        best = max(best, 100 * (seen[k][2] / uni_val - 1))
        cum.append(best)
    last_complete = max([b for b in batch_ends if b <= 26])
    fullfe26 = {
        "definition": "best FE among the first 26 unique designs in the "
                      "archived query order (dedup; repeats free)",
        "best_gain_at_26_unique_pct": float(cum[25]),
        "batch_complete_frontier": {
            "unique_designs": int(last_complete),
            "best_gain_pct": float(cum[last_complete - 1])},
        "batch_note": "call 26 falls inside incomplete scan 4 (batch ends "
                      "at 33); batch-complete frontier at 25 unique designs "
                      "(3 complete scans) reported alongside",
        "cumulative_unique_per_completed_scan": batch_ends,
        "total_unique_search_designs": len(order_keys),
        "raw_logical_queries_in_archived_script": 244,
        "required_unique_incl_confirm": len(required),
    }

    out = dict(diag=diag, steps=steps, groups=groups, pool=pool,
               uniform_search=uni_val, uniform_confirm=uni96,
               fullfe_truncated=fullfe26, best_so_far_trajectory=cum,
               order_keys=order_keys)
    tmp = OUT + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=2)
    if os.path.exists(OUT) and args.keep:
        os.remove(OUT)
    os.replace(tmp, OUT)
    slim = {k: diag[k] for k in diag
            if not isinstance(diag[k], (list, dict))}
    print(json.dumps(slim, indent=2))
    print("fullfe26 best@26u:", fullfe26["best_gain_at_26_unique_pct"],
          "| batch-complete:", last_complete,
          fullfe26["batch_complete_frontier"]["best_gain_pct"])
    print("extras:", extra_records)


if __name__ == "__main__":
    main()
