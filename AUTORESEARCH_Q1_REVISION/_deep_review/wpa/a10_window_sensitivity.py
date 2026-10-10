"""WP-A10 (G15, G17, D6): per-specimen crosshead slopes, window sensitivity
of R = mean(E*_graded)/mean(E*_uniform), and maximum recorded force.
Reuses fit()/specimen_record() of the archived verify_experiment_stats.py
(same raw CSVs, same estimator)."""
import json
import sys
from pathlib import Path

import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))
import v7_style as VS
import matplotlib.pyplot as plt
sys.path.insert(0, str(ROOT.parent / "paper"))  # authoritative coupon analysis script
import verify_experiment_stats as ves  # noqa: E402
from scipy.stats import t as t_dist  # noqa: E402

D = ves.DATA
TAGS_U = [f"U{i}" for i in range(1, 5)]
TAGS_O = [f"O{i}" for i in range(1, 5)]

res = {"per_specimen": {}, "windows": {}}
for tag in TAGS_U + TAGS_O:
    rec = ves.specimen_record(D / f"{tag}.csv")
    res["per_specimen"][tag] = {k: rec[k] for k in ("E_MPa", "r2", "n_fit", "peak_force_N", "executed_rate_mm_min")}

tcrit = float(t_dist.ppf(0.975, df=3))
for name, w in ves.window_families():
    eu = np.array([ves.fit(D / f"{s}.csv", w)[0] for s in TAGS_U])
    eo = np.array([ves.fit(D / f"{s}.csv", w)[0] for s in TAGS_O])
    nmin = min(ves.fit(D / f"{s}.csv", w)[2] for s in TAGS_U + TAGS_O)
    r, se = ves.group_ratio(eo, eu)
    res["windows"][name] = dict(lo=w[0], hi=w[1], R=r, se=se, t_ci=[r - tcrit * se, r + tcrit * se],
                                n_min=int(nmin), E_u=eu.tolist(), E_o=eo.tolist())

pf_u = np.array([res["per_specimen"][s]["peak_force_N"] for s in TAGS_U])
pf_o = np.array([res["per_specimen"][s]["peak_force_N"] for s in TAGS_O])
res["max_force"] = dict(mean_u=pf_u.mean(), sd_u=pf_u.std(ddof=1), mean_o=pf_o.mean(), sd_o=pf_o.std(ddof=1),
                        ratio=pf_o.mean() / pf_u.mean(), range_u=[pf_u.min(), pf_u.max()], range_o=[pf_o.min(), pf_o.max()])
out = Path(__file__).with_suffix(".json")
json.dump(res, open(out, "w"), indent=2, default=float)

print("per-specimen E* [MPa] (150-600 N):")
for s in TAGS_U + TAGS_O:
    p = res["per_specimen"][s]
    print(f"  {s}: E*={p['E_MPa']:.1f}  R2={p['r2']:.5f}  n={p['n_fit']}  peak={p['peak_force_N']:.1f} N  rate={p['executed_rate_mm_min']:.2f}")
print("windows (450 N family, then 100 N sliding):")
for k, v in res["windows"].items():
    print(f"  {k:>9s} N: R={v['R']:.3f}  SE={v['se']:.3f}  t-CI=[{v['t_ci'][0]:.3f},{v['t_ci'][1]:.3f}]  n_min={v['n_min']}")
print("max force:", {k: (np.round(v, 1) if not isinstance(v, list) else np.round(v, 1).tolist()) for k, v in res["max_force"].items()})

# ---- figure ---------------------------------------------------------------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(VS.FULL_W, 2.6), gridspec_kw=dict(width_ratios=[1.35, 1]))
for fam, mk, col, lab in (("450", "o", "k", "450 N-wide windows"), ("100", "s", VS.DES["band"]["c"], "100 N-wide windows")):
    ks = [k for k, v in res["windows"].items() if abs((v["hi"] - v["lo"]) - float(fam)) < 1]
    xc = np.array([0.5 * (res["windows"][k]["lo"] + res["windows"][k]["hi"]) for k in ks])
    R = np.array([res["windows"][k]["R"] for k in ks])
    lo = np.array([res["windows"][k]["t_ci"][0] for k in ks]); hi = np.array([res["windows"][k]["t_ci"][1] for k in ks])
    a1.plot(xc, R, marker=mk, color=col, ms=4, lw=1.2, label=lab)
    a1.fill_between(xc, lo, hi, color=col, alpha=0.12, lw=0)
prim = res["windows"]["150-600"]
a1.plot([375], [prim["R"]], marker="*", color="#D55E00", ms=9, ls="none", label="150–600 N (reported)")
a1.axhline(1.0, color="0.5", lw=0.8, ls=":")
a1.set_xlabel("window centre force [N]")
a1.set_ylabel("$R=\\overline{E^*}_{\\rm graded}/\\overline{E^*}_{\\rm uniform}$")
a1.legend(fontsize=8, frameon=False, loc="lower left")
a1.set_title("(a) stiffness ratio vs force window (95% t-interval)", fontsize=8)
for gx, tags, col, lab in ((0, TAGS_U, "0.35", "uniform"), (1, TAGS_O, VS.DES["band"]["c"], "graded")):
    e = np.array([res["per_specimen"][s]["E_MPa"] for s in tags])
    jit = np.linspace(-0.12, 0.12, len(e))
    a2.plot(gx + jit, e, "o", color=col, ms=6)
    for xj, ej, s in zip(jit, e, tags):
        a2.annotate(s, (gx + xj, ej), xytext=(5, -3), textcoords="offset points", fontsize=7, color=col)
    a2.hlines(e.mean(), gx - 0.25, gx + 0.25, color=col, lw=2)
a2.set_xticks([0, 1], ["uniform", "graded"]); a2.set_xlim(-0.6, 1.6)
a2.set_ylabel("$E^*$ (150–600 N) [MPa]")
a2.set_title("(b) per-specimen crosshead slopes", fontsize=8)
fig.tight_layout()
fo = ROOT / "MATERIALS_DESIGN_TRANSFER" / "manuscript" / "figures" / "fig_wpa_window_sensitivity"
fig.savefig(str(fo) + ".pdf"); fig.savefig(str(fo) + ".png", dpi=200)
