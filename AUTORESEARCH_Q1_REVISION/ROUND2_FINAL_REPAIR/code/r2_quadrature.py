"""r2_quadrature: isolate quadrature (integration-cloud) effects from
trajectory effects, fixing PI finding 2's confound.

Method (frozen in ROUND2_PLAN.md Section 3):
  * frozen common state collection = the 192-design reconstructed pool
    (fixed theta/shift triples from results/r2_pool_replay.json) plus the
    24 archived per-scan candidate groups;
  * score EVERY state under clouds 11, 12, 13 (frozen scorer, fixed model
    checkpoint -- training seed NOT varied);
  * report cloud-vs-cloud Spearman/Kendall on the common collection,
    per-cloud group top-1 agreement, and each cloud's OWN uniform-design
    DEM denominator (implied DEM gains are normalized per cloud).

No FE calls. Output: results/r2_quadrature_isolation.json.
"""
import json
import os
import sys

import numpy as np
from scipy.stats import kendalltau, spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vg2_common as v2  # noqa: E402

R2 = v2.R2
OUT = os.path.join(R2, "results", "r2_quadrature_isolation.json")
CLOUDS = (11, 12, 13)


def main():
    rep = json.load(open(os.path.join(R2, "results", "r2_pool_replay.json")))
    pool = rep["pool"]
    arch = json.load(open(os.path.join(v2.N3, "e3_fe_baseline.json")))
    uni_val = rep["uniform_search"]

    scores = {}
    for c in CLOUDS:
        sc = v2.make_scorer(cloud_seed=c)
        scores[c] = np.array([sc(p["theta"], p["shift"]) for p in pool])
        print(f"cloud {c}: scored {len(pool)} states", flush=True)

    by_key = {p["key"]: p for p in pool}
    # uniform-design DEM denominator per cloud (theta=0 state is in the pool)
    k_uni = None
    theta0 = [0.0] * v2.N_MODES
    sh0 = v2.bisect_shift_discrete(64, theta0)
    k_uni = v2.cand_key(64, theta0, sh0)
    idx_uni = [p["key"] for p in pool].index(k_uni)
    denom = {c: float(scores[c][idx_uni]) for c in CLOUDS}

    pair_stats = {}
    for i, a in enumerate(CLOUDS):
        for b in CLOUDS[i + 1:]:
            sp = spearmanr(scores[a], scores[b])
            kt = kendalltau(scores[a], scores[b])
            pair_stats[f"cloud{a}_vs_cloud{b}"] = dict(
                spearman=float(sp.statistic),
                kendall=float(kt.statistic))

    # group top-1 agreement between clouds (walk with entry['pick'])
    group_rows = []
    agree = {f"{a}-{b}": 0 for a in CLOUDS for b in CLOUDS if a < b}
    n_groups = 0
    theta = [0.0] * v2.N_MODES
    for entry in arch["history"]:
        m = entry["mode"]
        keys = []
        for cand in v2.GRID:
            tr = list(theta)
            tr[m] = float(cand)
            sh = v2.bisect_shift_discrete(64, tr)
            k = v2.cand_key(64, tr, sh)
            if k in by_key:
                keys.append(k)
        sh = v2.bisect_shift_discrete(64, theta)
        k = v2.cand_key(64, theta, sh)
        if k in by_key and k not in keys:
            keys.append(k)
        if len(keys) < 2:
            theta[m] = entry["pick"]
            continue
        n_groups += 1
        idxs = [[p["key"] for p in pool].index(kk) for kk in keys]
        tops = {c: keys[int(np.argmax(scores[c][idxs]))] for c in CLOUDS}
        row = dict(sweep=entry["sweep"], mode=m,
                   **{f"top_cloud{c}": tops[c] for c in CLOUDS})
        for a in CLOUDS:
            for b in CLOUDS:
                if a < b:
                    ok = tops[a] == tops[b]
                    agree[f"{a}-{b}"] += int(ok)
        group_rows.append(row)
        theta[m] = entry["pick"]

    # cloud-11 vs FE on the same frozen collection (reference, tie-aware)
    fe = np.array([p["C_FE"] for p in pool])
    dem11 = scores[11]
    sp_fe = spearmanr(dem11, fe)
    kt_fe = kendalltau(dem11, fe)

    out = dict(
        definition="quadrature isolation on frozen common states; training "
                   "seed NOT varied (single frozen checkpoint e3_cond.pt); "
                   "no FE calls",
        n_states=len(pool),
        cloud_uniform_dem_denominator=denom,
        cloud_pair_rank_agreement=pair_stats,
        group_top1_agreement_counts={k: f"{v}/{n_groups}"
                                     for k, v in agree.items()},
        cloud11_vs_FE_spearman=float(sp_fe.statistic),
        cloud11_vs_FE_kendall=float(kt_fe.statistic),
        implied_dem_gain_normalization_note=(
            "implied DEM gain per cloud c = 100*(score_c(theta)/"
            "score_c(uniform) - 1); the round-1 script hardcoded the "
            "seed-11 denominator 0.11430107802152634 for every cloud -- "
            "corrected here"),
        per_state_scores={
            p["key"]: {f"cloud{c}": float(scores[c][i]) for c in CLOUDS}
            for i, p in enumerate(pool)},
        group_rows=group_rows,
    )
    v2.write_json_new(OUT, out)
    slim = {k: v for k, v in out.items()
            if k not in ("per_state_scores", "group_rows")}
    print(json.dumps(slim, indent=2))


if __name__ == "__main__":
    main()
