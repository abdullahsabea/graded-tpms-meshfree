"""v7 headline figure: KUBC vs periodic-BC gains of the five designs on the
same body-fitted meshes, plus absolute stiffness with the external uniform-cell
periodic references.

Reads research/n3/conforming/conf_summary.json (summarize_conf.py). Resolutions
present in the file (N48 now; N72 once those solves are summarised) are all
plotted, finest as filled markers. Gains are volume-adjusted (C ~ V_f^1.21) as
in summarize_conf.py."""
import json

import numpy as np
from matplotlib.lines import Line2D

import v7_style as S
import matplotlib.pyplot as plt

CS = json.loads((S.ROOT / "research" / "n3" / "conforming" / "conf_summary.json").read_text())
NUM = json.loads((S.HERE / "v7_numbers.json").read_text())
SUF = {"uniform": "", "band": "_printable", "vgmm": "_vgmm", "fullfe": "_fullfe", "graded": "_graded"}


def key(N, d):
    return f"N{N}_M96{SUF[d]}_rc"


RES = [N for N in (48, 60, 72) if all(key(N, d) in CS.get("pbc", {}) for d in S.ORDER)]
FINE = RES[-1]


def vals(N, d):
    k = key(N, d)
    return (CS["kubc_gain_pct"].get(k, 0.0), CS["pbc_gain_pct"].get(k, 0.0),
            CS["kubc"][k]["C"], CS["pbc"][k]["C_stress"], CS["kubc"][k]["V"])


fig, (ax, ax2) = plt.subplots(1, 2, figsize=(S.FULL_W, 2.75), gridspec_kw={"width_ratios": [1.0, 1.15]})
S.grid_y(ax)
S.grid_y(ax2)
dy = {"vgmm": -0.55, "fullfe": 0.55}
for d in S.ORDER:
    c = S.DES[d]["c"]
    for N in RES:
        kg, pg, *_ = vals(N, d)
        fine = N == FINE
        ax.plot([0, 1], [kg, pg], "-", color=c, lw=1.5 if fine else 0.7, alpha=1 if fine else 0.5, zorder=2)
        ax.plot([0, 1], [kg, pg], S.DES[d]["m"], color=c, ms=4.6 if fine else 3.6,
                mfc=c if fine else "white", mec="white" if fine else c, mew=0.6, zorder=3)
    kg, pg, *_ = vals(FINE, d)
    ref = d == "uniform"
    ax.text(-0.06, kg + dy.get(d, 0), f"{S.DES[d]['short']}  " + ("(reference)" if ref else f"${kg:+.1f}\\%$"),
            ha="right", va="center", fontsize=7, color=c)
    if not ref:
        ax.text(1.21, pg, f"${pg:+.1f}\\%$", ha="left", va="center", fontsize=7, color=c)
N72 = S.ROOT / "research" / "n3" / "conforming" / "wpa1_N72_results.json"
if N72.exists():
    r72 = json.loads(N72.read_text())
    for d in S.ORDER:
        if d == "uniform":
            continue
        k72 = {"band": "band"}.get(d, d)
        ax.plot(1.1, r72[k72]["gain72"], S.DES[d]["m"], ms=4.2, mfc="white", mec=S.DES[d]["c"], mew=0.9, zorder=3)
    ax.text(1.1, 1.2, "$N{=}72$", ha="center", va="bottom", fontsize=6.4, color="0.3")
ax.set_xlim(-1.05, 1.5)
ax.set_xticks([0, 1])
ax.set_xticklabels(["KUBC (search)", "periodic (check)"])
ax.set_ylabel("$C_{1111}$ gain over uniform at equal $V_f$ [%]")
ax.set_title("(a) gains under the two boundary conditions", loc="left", pad=4)
if len(RES) > 1:
    ax.legend(handles=[Line2D([], [], color="0.3", marker="o", mfc="0.3", lw=1.5, label=f"$N={FINE}$"),
                       Line2D([], [], color="0.3", marker="o", mfc="white", lw=0.7, alpha=0.6,
                              label=", ".join(f"$N={n}$" for n in RES[:-1]))],
              loc="lower left", fontsize=6.6)

x = np.arange(len(S.ORDER))
for i, d in enumerate(S.ORDER):
    c = S.DES[d]["c"]
    _, _, ck, cp, _ = vals(FINE, d)
    ax2.bar(i - 0.19, ck, 0.36, color=c, alpha=0.28, edgecolor=c, lw=0.6, zorder=2)
    ax2.bar(i + 0.19, cp, 0.36, color=c, alpha=0.9, edgecolor="white", lw=0.4, zorder=2)
    ax2.text(i, ck + 0.0012, f"{cp / ck:.3f}", ha="center", va="bottom", fontsize=6.6, color="0.25")
ext = NUM["external_uniform_pbc"]
ax2.plot([0.19 - 0.24, 0.19 + 0.24], [ext["fisher2023_voxel_nu030_at_Vf_mesh"]] * 2, color="k", lw=1.1, ls=(0, (2, 1)), zorder=4)
ax2.set_xticks(x)
ax2.set_xticklabels(["Uniform", "Band-\nrestricted", "Filtered\ns11", "FE\nsearch", "Uncon-\nstrained"], fontsize=6.9)
ax2.set_ylim(0.075, 0.13)
ax2.set_ylabel("apparent $C_{1111}$ (meshed $V_f$)")
ax2.set_title("(b) stiffness on the same mesh", loc="left", pad=4)
ax2.legend(handles=[plt.Rectangle((0, 0), 1, 1, fc="0.6", alpha=0.3, ec="0.4", lw=0.6, label="KUBC"),
                    plt.Rectangle((0, 0), 1, 1, fc="0.3", label="periodic BC"),
                    Line2D([], [], color="k", lw=1.1, ls=(0, (2, 1)), label="external voxel PBC, uniform")],
           loc="upper right", fontsize=6.6, ncol=1)
fig.subplots_adjust(left=0.215, right=0.995, top=0.9, bottom=0.2, wspace=0.3)
S.save(fig, "fig_v7_pbc")
print("resolutions:", RES)
