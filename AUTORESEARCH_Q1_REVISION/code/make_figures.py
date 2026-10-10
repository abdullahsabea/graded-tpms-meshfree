"""Regenerate all new figures from machine-readable result files.

F1: verified FE gain vs FE-call budget for all arms (A-E) + pool frontier.
F2: DEM-vs-FE discordance over the reconstructed pool.
Inputs: results/pool_replay.json, results/vgmm_result.json,
        results/seed_final_fe_check.json, research/n3 SoT JSONs (read-only).
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.dirname(HERE)
N3 = os.path.join(os.path.dirname(WS), "research", "n3")
FIG = os.path.join(WS, "figures")
os.makedirs(FIG, exist_ok=True)

rep = json.load(open(os.path.join(WS, "results", "pool_replay.json")))
vg = json.load(open(os.path.join(WS, "results", "vgmm_result.json")))
seedfe = json.load(open(os.path.join(WS, "results", "seed_final_fe_check.json")))
febase = json.load(open(os.path.join(N3, "e3_fe_baseline.json")))
paper = json.load(open(os.path.join(N3, "paper_numbers.json")))
UNI64 = febase["C1111_uniform_search"]
UNI96 = febase["C1111_uniform_confirm"]

# ---------------- F1: verified gain vs FE-call budget ----------------------
fig, ax = plt.subplots(figsize=(7.2, 4.4))

# pool frontier: best-so-far along archived greedy path (195 calls)
hist = febase["history"]
best = -1e9
xs, ys = [], []
call_idx = 9  # baseline + first scan
best = max(best, 0.0)
xs.append(1); ys.append(0.0)
best = 0.0
for h in hist:
    best = max(best, 100 * (h["C1111"] / UNI64 - 1))
    call_idx += 1
    xs.append(call_idx); ys.append(best)
ax.plot(xs, ys, "-", color="#888", lw=1.4,
        label="Full FE-in-loop search (archived, 195 calls)")

# VG-MM trajectory: monotone best-so-far over its own calls
best = 0.0
xs, ys = [], []
xs.append(1); ys.append(0.0)
ci = 1
for r in vg["log"]:
    if r.get("fe_calls"):
        ci += 1
        best = max(best, max(0.0, r["gain_vs_uniform_pct"]))
        xs.append(ci); ys.append(best)
ax.step(xs, ys, where="post", color="#c0392b", lw=2.0,
        label="VG-MM (this work, 26 calls)")

# single-design arms
ax.plot([26], [vg["G_search64_pct"]], "o", color="#c0392b", ms=7)
ax.annotate(f"VG-MM winner\n+{vg['G_search64_pct']:.2f}% @64$^3$, "
            f"+{vg['G_confirm96_pct']:.2f}% @96$^3$",
            (26, vg["G_search64_pct"]), textcoords="offset points",
            xytext=(8, -4), fontsize=8)
g_print = 100 * (paper["e3"]["printable"]["stats"]["mean"] / UNI96 - 1)
ax.plot([2], [100 * (paper["e3"]["printable"]["rows"][1]["C1111"] / UNI64 - 1)],
        "s", color="#2c7fb8", ms=7)
ax.annotate("band-restricted DEM design\n(archived; +1.72% @64$^3$, "
            f"+{g_print:.2f}% @96$^3$)", (2, 1.72),
            textcoords="offset points", xytext=(8, 10), fontsize=8)
g_grad64 = 100 * (paper["e3"]["graded"]["rows"][1]["C1111"] / UNI64 - 1)
ax.plot([2], [g_grad64], "^", color="#7f2704", ms=7)
ax.annotate("DEM-only unconstrained design\n(archived; "
            f"{g_grad64:.2f}% @64$^3$, −4.37% ladder mean)", (2, g_grad64),
            textcoords="offset points", xytext=(8, -16), fontsize=8)
for seed, d in seedfe.items():
    ax.plot([2], [d["gain_pct"]], "x", color="#e6a100", ms=8)
ax.annotate("DEM-only, alt. quadrature seeds 12/13\n(−6.50% / −5.37%; this work)",
            (2, -6.50), textcoords="offset points", xytext=(8, -6), fontsize=8)

ax.axhline(0, color="k", lw=0.6, ls=":")
ax.set_xlabel("FE evaluations spent (64$^3$ discrete-Vf-calibrated solves)")
ax.set_ylabel("FE-verified stiffness gain vs uniform [%]")
ax.set_title("Verified gain vs FE budget, matched 12-coefficient design space")
ax.set_xlim(0, 200)
ax.legend(fontsize=8, loc="lower right")
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig_vgmm_budget.png"), dpi=200)
fig.savefig(os.path.join(FIG, "fig_vgmm_budget.pdf"))
print("F1 written")

# ---------------- F2: DEM-vs-FE discordance in the pool --------------------
pool = rep["pool"]
fe = np.array([p["C_FE"] for p in pool])
dem = np.array([p["C_DEM"] for p in pool])
gain = 100 * (fe / UNI64 - 1)
demgain = 100 * (dem / UNI64 - 1)

fig, axs = plt.subplots(1, 2, figsize=(9.6, 4.2))
a = axs[0]
a.scatter(demgain, gain, s=14, color="#2c7fb8", alpha=0.75)
lim = [min(demgain.min(), gain.min()) - 2, max(demgain.max(), gain.max()) + 2]
a.plot(lim, lim, "k--", lw=0.8)
a.axhline(0, color="k", lw=0.5, ls=":")
a.axvline(0, color="k", lw=0.5, ls=":")
a.set_xlabel("conditional-DEM predicted gain [%]")
a.set_ylabel("voxel-FE verified gain [%]")
a.set_title(f"(a) Shared candidate pool, N={len(pool)}\n"
            f"Spearman {rep['diag']['spearman_dem_fe']:.2f}, "
            f"Kendall {rep['diag']['kendall_dem_fe']:.2f}")
b = axs[1]
gg = rep["groups"]
x = np.arange(len(gg))
b.bar(x - 0.2, [g["fe_best_gain"] for g in gg], width=0.4,
      label="FE-argmax pick", color="#238b45")
b.bar(x + 0.2, [g["dem_pick_fe_gain"] for g in gg], width=0.4,
      label="DEM top-1 pick (FE score)", color="#c0392b")
b.axhline(0, color="k", lw=0.6)
b.set_xlabel("checkpoint (sweep × mode, in search order)")
b.set_ylabel("FE gain of pick [%]")
b.set_title(f"(b) Per-checkpoint top-1: DEM wrong in "
            f"{sum(1 for g in gg if not g['agree'])}/{len(gg)} groups")
b.legend(fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig_pool_discordance.png"), dpi=200)
fig.savefig(os.path.join(FIG, "fig_pool_discordance.pdf"))
print("F2 written")
