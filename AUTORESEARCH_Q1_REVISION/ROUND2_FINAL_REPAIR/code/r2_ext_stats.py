"""Statistics for the n = 10 per-policy VG-MM vs RANDOM comparison (seeds 11-20).

Seeds 11-13 come from the prospective arms (results/r2_arms; VG-MM seed 11 is the
historical run in round1 vgmm_result.json), seeds 14-20 from results/r2_arms_ext.
"""
import glob
import json
import os

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
R2 = os.path.dirname(HERE)
WS = os.path.dirname(R2)
U64, U96 = 0.10528125601, 0.10572287959
DELTA = 1.0
rng = np.random.default_rng(2026)


def load():
    g = {"vgmm": {}, "rand": {}}
    for f in glob.glob(os.path.join(R2, "results", "r2_arms", "arm_*.json")) + \
            glob.glob(os.path.join(R2, "results", "r2_arms_ext", "arm_*.json")):
        d = json.load(open(f))
        if d["policy"] in g:
            g[d["policy"]][d["seed"]] = (d["G26_pct"], d["G_confirm96_pct"])
    h = json.load(open(os.path.join(WS, "results", "vgmm_result.json")))
    g["vgmm"][11] = (100 * (h["C_winner_search64"] / U64 - 1), 100 * (h["C_winner_confirm96"] / U96 - 1))
    return g


def summarize(v, r, grid):
    diff = v.mean() - r.mean()
    boot = [rng.choice(v, len(v)).mean() - rng.choice(r, len(r)).mean() for _ in range(20000)]
    lo, hi = np.percentile(boot, [2.5, 97.5])
    mw = stats.mannwhitneyu(v, r, alternative="greater")
    wt = stats.ttest_ind(v, r, equal_var=False)
    # TOST equivalence at +/- DELTA (Welch)
    se = np.sqrt(v.var(ddof=1) / len(v) + r.var(ddof=1) / len(r))
    dof = se**4 / ((v.var(ddof=1) / len(v))**2 / (len(v) - 1) + (r.var(ddof=1) / len(r))**2 / (len(r) - 1))
    p_tost = max(1 - stats.t.cdf((diff + DELTA) / se, dof), stats.t.cdf((diff - DELTA) / se, dof))
    lev = stats.levene(v, r, center="median")
    return dict(grid=grid, n=[len(v), len(r)],
                vgmm=dict(mean=v.mean(), sd=v.std(ddof=1), min=v.min(), max=v.max(), median=np.median(v)),
                rand=dict(mean=r.mean(), sd=r.std(ddof=1), min=r.min(), max=r.max(), median=np.median(r)),
                mean_diff=diff, boot95=[lo, hi], mannwhitney_greater_p=mw.pvalue,
                welch_t=wt.statistic, welch_p_two_sided=wt.pvalue, tost_p_delta1=p_tost,
                levene_brown_forsythe_p=lev.pvalue,
                frac_rand_below_min_vgmm=float((r < v.min()).mean()))


if __name__ == "__main__":
    g = load()
    seeds_v, seeds_r = sorted(g["vgmm"]), sorted(g["rand"])
    print("VG-MM seeds", seeds_v, "\nRAND seeds", seeds_r)
    out = {}
    for i, grid in enumerate(("64^3 search", "96^3 confirm")):
        v = np.array([g["vgmm"][s][i] for s in seeds_v])
        r = np.array([g["rand"][s][i] for s in seeds_r])
        out[grid] = summarize(v, r, grid)
        o = out[grid]
        print(f"\n== {grid} ==")
        print(f"VG-MM mean {o['vgmm']['mean']:.3f} sd {o['vgmm']['sd']:.3f} range [{o['vgmm']['min']:.2f}, {o['vgmm']['max']:.2f}]")
        print(f"RAND  mean {o['rand']['mean']:.3f} sd {o['rand']['sd']:.3f} range [{o['rand']['min']:.2f}, {o['rand']['max']:.2f}]")
        print(f"diff {o['mean_diff']:.3f} pp, bootstrap95 [{o['boot95'][0]:.3f}, {o['boot95'][1]:.3f}]")
        print(f"Mann-Whitney (VG-MM > RAND) p={o['mannwhitney_greater_p']:.4f}; Welch p={o['welch_p_two_sided']:.4f}; "
              f"TOST(+/-1pp) p={o['tost_p_delta1']:.4f}; Brown-Forsythe spread p={o['levene_brown_forsythe_p']:.4f}")
    out["per_seed"] = {k: {str(s): list(v) for s, v in d.items()} for k, d in g.items()}
    json.dump(out, open(os.path.join(R2, "results", "r2_ext_stats.json"), "w"), indent=1, default=float)
