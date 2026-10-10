"""v7 replacement for Fig. 12: score versus voxel FE on the 192-candidate
shared pool. Same data as the v6 figure (ROUND2_FINAL_REPAIR/figures/data);
labels use the paper's terms and colours avoid the per-design palette."""
import csv
import json

import numpy as np

import v7_style as S
import matplotlib.pyplot as plt

R2 = S.Q1 / "ROUND2_FINAL_REPAIR"
rd = lambda p: list(csv.DictReader(open(p, encoding="utf-8")))
pool = rd(R2 / "figures" / "data" / "R2_pool.csv")
groups = rd(R2 / "figures" / "data" / "R2_groups.csv")
diag = json.loads((R2 / "results" / "r2_pool_replay.json").read_text(encoding="utf-8"))["diag"]
sc = np.array([float(r["C_DEM"]) for r in pool])
fe = np.array([float(r["C_FE"]) for r in pool])
gs = np.array([float(r["gain_DEM_pct"]) for r in pool])
gf = np.array([float(r["gain_FE_pct"]) for r in pool])
i_s, i_f = int(np.argmax(sc)), int(np.argmax(fe))
C_FE, C_SC, C_PT = "#000000", "#8E44AD", "#9A9A9A"

fig, axs = plt.subplots(1, 3, figsize=(S.FULL_W, 2.45), gridspec_kw={"width_ratios": [1, 1, 1.25]})
a, b, c = axs
for ax in axs:
    S.grid_y(ax)
for ax, x, y, xl, yl in ((a, sc, fe, "score $C_{1111}$ (KUBC)", "voxel FE $C_{1111}$ (KUBC)"),
                         (b, gs, gf, "score gain over uniform [%]", "FE gain over uniform [%]")):
    ax.scatter(x, y, s=8, color=C_PT, alpha=0.6, lw=0, zorder=2)
    lo, hi = min(x.min(), y.min()), max(x.max(), y.max())
    pad = 0.04 * (hi - lo)
    ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], color="0.3", ls="--", lw=0.7, zorder=1)
    ax.plot(x[i_f], y[i_f], "^", ms=6.5, mfc="none", mec=C_FE, mew=1.1, zorder=4, label="FE-best candidate")
    ax.plot(x[i_s], y[i_s], "o", ms=6.5, mfc="none", mec=C_SC, mew=1.1, zorder=4, label="score-best candidate")
    ax.set_xlim(lo - pad, hi + pad)
    ax.set_ylim(lo - pad, hi + pad)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel(xl)
    ax.set_ylabel(yl)
a.set_title("(a) stiffness parity", loc="left", pad=4)
a.legend(loc="upper left", fontsize=6.4, handletextpad=0.3)
b.axhline(0, color="0.5", lw=0.5, ls=":")
b.axvline(0, color="0.5", lw=0.5, ls=":")
b.set_title(f"(b) gains; Spearman {diag['spearman_dem_fe_scipy_tie_aware']:.3f}, "
            f"Kendall {diag['kendall_dem_fe_scipy_tie_aware']:.3f}", loc="left", pad=4, fontsize=7.6)
x = np.arange(len(groups))
c.bar(x - 0.18, [float(g["fe_best_gain"]) for g in groups], 0.34, color=C_FE, label="FE-best trial", zorder=3)
c.bar(x + 0.18, [float(g["dem_pick_fe_gain"]) for g in groups], 0.34, color=C_SC,
      label="score's top trial (FE value)", zorder=3)
c.axhline(0, color="0.35", lw=0.6)
c.set_xticks([0, 5, 11, 17, 23])
c.set_xlabel("checkpoint (search order)")
c.set_ylabel("FE gain of the trial [%]")
c.set_title(f"(c) score's top trial is not FE-best in {diag['scan_groups_dem_top1_wrong']} of "
            f"{diag['scan_groups']} groups", loc="left", pad=4, fontsize=7.6)
c.legend(loc="lower right", fontsize=6.4)
fig.subplots_adjust(left=0.07, right=0.995, top=0.88, bottom=0.2, wspace=0.42)
S.save(fig, "fig_v7_pool")
