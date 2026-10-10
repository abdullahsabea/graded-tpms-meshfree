"""v7 ranking-inversion figure (replaces fig4 panel c): hard-domain score audit
versus energy-basis voxel FE (KUBC) for the uniform, band-restricted and
unconstrained designs at the historical volume target."""
import json

import v7_style as S
import matplotlib.pyplot as plt

NUM = json.loads((S.HERE / "v7_numbers.json").read_text())
fig, ax = plt.subplots(figsize=(S.COL_W, 2.55))
S.grid_y(ax)
u_s, u_f = NUM["score_hard"]["uniform"], NUM["voxel_mean"]["uniform"]
dy = {"uniform": (0, -3), "band": (0, 5), "graded": (0, -2)}
for k in ("uniform", "band", "graded"):
    d = S.DES[k]
    s, f = NUM["score_hard"][k], NUM["voxel_mean"][k]
    se = NUM["score_se"][k] or 0.0
    fe_err = f * NUM["voxel_half_pct"][k] / 100
    ax.plot([0, 1], [s, f], "-", color=d["c"], lw=1.3, zorder=2)
    ax.errorbar(0, s, yerr=se, fmt=d["m"], color=d["c"], ms=5, mec="white", mew=0.6, capsize=2, elinewidth=0.8, zorder=3)
    ax.errorbar(1, f, yerr=fe_err, fmt=d["m"], color=d["c"], ms=5, mec="white", mew=0.6, capsize=2, elinewidth=0.8, zorder=3)
    gs = "reference" if k == "uniform" else f"${100 * (s / u_s - 1):+.1f}\\%$"
    gf = "reference" if k == "uniform" else f"${100 * (f / u_f - 1):+.1f}\\%$"
    ax.annotate(gs, (0, s), xytext=(-7, 0), textcoords="offset points", ha="right", va="center", fontsize=7, color=d["c"])
    ax.annotate(f"{d['short']} {gf}", (1, f), xytext=(7, dy[k][1]), textcoords="offset points",
                ha="left", va="center", fontsize=7, color=d["c"], linespacing=1.0)
ax.set_xticks([0, 1])
ax.set_xticklabels(["local-thickness score\n(hard-domain audit)", "voxel FE\n(energy basis)"])
ax.set_xlim(-0.72, 2.2)
ax.set_ylim(0.098, 0.137)
ax.set_ylabel("apparent $C_{1111}$ under KUBC")
ax.set_title("Same KUBC, matched volume", loc="left", pad=4)
fig.subplots_adjust(left=0.19, right=0.98, top=0.9, bottom=0.2)
S.save(fig, "fig_v7_ranking")
