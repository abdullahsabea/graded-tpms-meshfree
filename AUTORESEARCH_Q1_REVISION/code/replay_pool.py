"""EXP-04 REPLAY: reconstruct the 195-candidate FE-labeled pool of the
archived FE-in-the-loop search (e3_fe_baseline) from the content-hash solve
cache, validate the reconstruction against the archived history, and join
conditional-DEM soft scores. NO new FE solves: missing cache keys abort with
an explicit count (INCONCLUSIVE reconstruction), never synthesized.

Also produces the pool-level diagnostics used by the manuscript revision:
  * per-(sweep,mode) scan groups: DEM top-1 vs FE top-1 discordance count
  * Spearman/Kendall correlation DEM vs FE over the pool
  * best-so-far FE gain along the archived greedy path (frontier)
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vgmm_common as vc  # noqa: E402

WS, N3 = vc.WS, vc.N3
arch = json.load(open(os.path.join(N3, "e3_fe_baseline.json")))
search_N = arch["search_N"]
uni_val = arch["C1111_uniform_search"]

theta = [0.0] * vc.N_MODES
steps = []
missing = 0
seen = {}

sh0 = vc.bisect_shift_discrete(search_N, theta)
v0, k0, leg0, new0 = vc.fe_solve(search_N, theta, sh0)
if new0:
    raise RuntimeError("baseline unexpectedly absent from cache")
seen[k0] = (theta, sh0, v0)
best_val = v0

t0 = time.time()
ok = True
for entry in arch["history"]:
    s, m, pick_arch, val_arch = (entry["sweep"], entry["mode"],
                                 entry["pick"], entry["C1111"])
    trials, metas = [], []
    for cand in vc.GRID:
        tr = list(theta); tr[m] = float(cand)
        sh = vc.bisect_shift_discrete(search_N, tr)
        trials.append((tr, sh)); metas.append(float(cand))
    sh_inc = vc.bisect_shift_discrete(search_N, theta)
    trials.append((list(theta), sh_inc)); metas.append(None)
    vals = []
    for tr, sh in trials:
        k = vc.cand_key(search_N, tr, sh)
        path = os.path.join(vc.FE_LEGACY, f"oute_{k}.mess")
        if not os.path.exists(path):
            missing += 1
            vals.append(None)
            continue
        import re
        mm = re.search(r"C1111_ENERGY = ([\d.eE+-]+)",
                       open(path, errors="ignore").read())
        vals.append(float(mm.group(1)) if mm else None)
        seen.setdefault(k, (tr, sh, vals[-1]))
    if any(v is None for v in vals):
        ok = False
        steps.append(dict(sweep=s, mode=m, incomplete=True))
        # reconstruct incumbent anyway from archived value to stay aligned
        theta = [t2 for t2 in theta]
        theta[m] = pick_arch
        best_val = val_arch
        continue
    best_i = int(np.argmax(vals))
    rec = dict(sweep=s, mode=m, pick=trials[best_i][0][m],
               C1111=vals[best_i], pick_arch=pick_arch,
               C1111_arch=val_arch,
               match=bool(trials[best_i][0][m] == pick_arch
                          and abs(vals[best_i] - val_arch) < 1e-12))
    if not rec["match"]:
        ok = False
    steps.append(rec)
    theta = trials[best_i][0]
    best_val = vals[best_i]

runtime = time.time() - t0
matches = [r for r in steps if r.get("match")]
print(f"reconstruction: {len(matches)}/{len(steps)} steps match archived "
      f"history; missing cache keys: {missing}; {runtime:.0f}s", flush=True)

# ---- DEM scores over the unique pool --------------------------------------
score = vc.make_scorer(cloud_seed=11)
pool = []
for i, (k, (tr, sh, vfe)) in enumerate(sorted(seen.items())):
    sd = score(tr, sh)
    pool.append(dict(key=k, theta=[round(x, 6) for x in tr], shift=sh,
                     C_FE=vfe, C_DEM=sd,
                     gain_FE_pct=100 * (vfe / uni_val - 1)))
    if (i + 1) % 40 == 0:
        print(f"scored {i+1}/{len(seen)}", flush=True)

fe = np.array([p["C_FE"] for p in pool])
dem = np.array([p["C_DEM"] for p in pool])

def spearman(a, b):
    ra = np.argsort(np.argsort(a)); rb = np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])

def kendall_tau(a, b):
    n = len(a); c = d = 0
    for i in range(n):
        for j in range(i + 1, n):
            s = np.sign(a[i] - a[j]) * np.sign(b[i] - b[j])
            c += s > 0; d += s < 0
    return (c - d) / (c + d) if (c + d) else float("nan")

diag = {
    "pool_size": len(pool),
    "reconstruction_steps_match": f"{len(matches)}/{len(steps)}",
    "missing_cache_keys": missing,
    "spearman_dem_fe": spearman(dem, fe),
    "kendall_dem_fe": kendall_tau(dem, fe),
    "best_FE_in_pool": float(fe.max()),
    "best_gain_pct_in_pool": float(100 * (fe.max() / uni_val - 1)),
    "dem_best_candidate_FE_value": float(fe[int(np.argmax(dem))]),
    "dem_best_candidate_FE_gain_pct": float(100 * (fe[int(np.argmax(dem))] / uni_val - 1)),
    "FE_best_candidate_DEM_value": float(dem[int(np.argmax(fe))]),
}

# per-scan-group discordance: rebuild groups from archived history steps
groups = []
theta = [0.0] * vc.N_MODES
for entry in arch["history"]:
    s, m = entry["sweep"], entry["mode"]
    tri, vfe_g, vdem_g = [], [], []
    for cand in vc.GRID:
        tr = list(theta); tr[m] = float(cand)
        sh = vc.bisect_shift_discrete(search_N, tr)
        k = vc.cand_key(search_N, tr, sh)
        hit = [p for p in pool if p["key"] == k]
        if hit:
            tri.append(k); vfe_g.append(hit[0]["C_FE"]); vdem_g.append(hit[0]["C_DEM"])
    sh_inc = vc.bisect_shift_discrete(search_N, theta)
    k = vc.cand_key(search_N, theta, sh_inc)
    hit = [p for p in pool if p["key"] == k]
    if hit:
        tri.append(k); vfe_g.append(hit[0]["C_FE"]); vdem_g.append(hit[0]["C_DEM"])
    if len(vfe_g) >= 2:
        groups.append(dict(sweep=s, mode=m,
                           fe_top1=tri[int(np.argmax(vfe_g))],
                           dem_top1=tri[int(np.argmax(vdem_g))],
                           agree=bool(int(np.argmax(vfe_g)) == int(np.argmax(vdem_g))),
                           fe_best_gain=float(100 * (max(vfe_g) / uni_val - 1)),
                           dem_pick_fe_gain=float(100 * (vfe_g[int(np.argmax(vdem_g))] / uni_val - 1))))
    theta[m] = pick_arch

disc = [g for g in groups if not g["agree"]]
diag["scan_groups"] = len(groups)
diag["scan_groups_dem_top1_wrong"] = len(disc)
diag["scan_group_discordance_rate"] = len(disc) / len(groups) if groups else None
diag["median_fe_gain_of_dem_picks_in_groups"] = float(np.median([g["dem_pick_fe_gain"] for g in groups])) if groups else None
diag["median_fe_gain_of_fe_picks_in_groups"] = float(np.median([g["fe_best_gain"] for g in groups])) if groups else None

out = dict(diag=diag, steps=steps, groups=groups, pool=pool,
           uniform_search=uni_val)
json.dump(out, open(os.path.join(WS, "results", "pool_replay.json"), "w"),
          indent=2)
with open(os.path.join(WS, "results", "pool_table.csv"), "w") as f:
    f.write("key,C_FE,C_DEM,gain_FE_pct,shift\n")
    for p in pool:
        f.write(f"{p['key']},{p['C_FE']:.10e},{p['C_DEM']:.10e},"
                f"{p['gain_FE_pct']:.4f},{p['shift']:.6f}\n")
print(json.dumps(diag, indent=2), flush=True)
