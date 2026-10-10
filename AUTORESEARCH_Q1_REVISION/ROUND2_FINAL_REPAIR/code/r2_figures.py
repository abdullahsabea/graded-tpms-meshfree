"""r2_figures: regenerate ALL revised ROUND2 figures from machine-readable
sources. Replaces the defective round-1 fig11/fig12 and adds the displays
mandated by the revision brief (R1-R5).

Style rules (revision brief):
  * Okabe-Ito colorblind-safe palette, consistent method colors/markers
    across ALL figures (VG-MM vermillion, RANDOM blue, DET green, FULL-FE
    grey, DEM-ONLY purple);
  * line styles + markers redundant with color (grayscale-readable);
  * steps for discrete best-so-far trajectories; individual replicate
    paths, no decorative summary distributions;
  * honest axes (bars from zero; restricted ranges conspicuous);
  * vector PDF with fonts embedded (pdf.fonttype 42) + 300-dpi PNG preview;
  * every panel's exact plotted values saved to figures/data/*.csv.

Outputs: figures/R1_budget_steps.{pdf,png}, R2_parity.{pdf,png},
R3_policy_seeds.{pdf,png}, R4_method_diagram.{pdf,png},
R5_geometry.{pdf,png} (+ data CSVs).
"""
import glob
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vg2_common as v2  # noqa: E402

R2 = v2.R2
FIG = os.path.join(R2, "figures")
DATA = os.path.join(FIG, "data")
os.makedirs(DATA, exist_ok=True)

plt.rcParams.update({
    "font.size": 8.5, "axes.titlesize": 9, "axes.labelsize": 8.5,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 7.5,
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
    "axes.linewidth": 0.7, "figure.dpi": 300})

C = {"vgmm": "#D55E00", "rand": "#0072B2", "det": "#009E73",
     "fullfe": "#666666", "demonly": "#CC79A7", "uniform": "#000000",
     "band": "#56B4E9"}
M = {"vgmm": "o", "rand": "s", "det": "^", "demonly": "D", "fullfe": ""}

UNI64, UNI96 = v2.UNI_64, v2.UNI_96


def save(fig, name):
    fig.savefig(os.path.join(FIG, f"{name}.pdf"), bbox_inches="tight")
    fig.savefig(os.path.join(FIG, f"{name}.png"), dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {name}.pdf/.png", flush=True)


def dump_csv(name, header, rows):
    import csv
    with open(os.path.join(DATA, f"{name}.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


# ---------------------------------------------------------------- inputs
def load_inputs():
    rep = json.load(open(os.path.join(R2, "results", "r2_pool_replay.json")))
    hist = json.load(open(os.path.join(v2.WS, "results",
                                       "vgmm_result.json")))
    arms = {}
    for f in sorted(glob.glob(os.path.join(R2, "results", "r2_arms",
                                           "arm_*.json"))):
        a = json.load(open(f))
        arms[a["arm"]] = a
    acc = json.load(open(os.path.join(R2, "results", "r2_accounting.json")))
    quad = json.load(open(os.path.join(
        R2, "results", "r2_quadrature_isolation.json")))
    arch = json.load(open(os.path.join(v2.N3, "e3_fe_baseline.json")))
    paper = json.load(open(os.path.join(v2.N3, "paper_numbers.json")))
    return rep, hist, arms, acc, quad, arch, paper


def best_so_far_traj(arm_json):
    """Best-so-far VERIFIED search-grid gain over the arm's counted calls."""
    calls = 1
class TrajectoryReconstructionError(RuntimeError):
    """Raised when a search trajectory cannot be reconstructed and
    independently cross-validated. Callers must not substitute a guessed
    trajectory when this is raised -- the affected arm must be reported as
    unresolved instead (PI decision, 2026-09-14 recheck)."""


def reconstruct_search_trajectory(log, calls_list, pick_key="pick",
                                   theta_len=None, label=""):
    """Reconstruct the best-so-far VERIFIED $64^3$ search-grid trajectory by
    replaying the chronological ``log`` (one row per actual checkpoint
    request, in true execution order) and de-duplicating on the FULL
    candidate design (current incumbent theta with the log row's changed
    coordinate set to ``row[pick_key]``), not on call count or on raw
    request count. The $96^3$ confirmation call is excluded from this
    reconstruction entirely (it is a different grid resolution, handled
    separately in panel (b)/Table 2).

    This does NOT trust the ``calls`` list's list-order or field values
    blindly (a duplicate FE query overwrites that key's record in place,
    including its ``purpose`` string, without moving its list position --
    so ``calls[i]["purpose"]`` can show a LATER re-query than the one that
    actually first produced that list position). Instead ``calls_list`` is
    used only as an independent cross-check: this function counts the
    number of ``N == 64`` entries in it and raises
    ``TrajectoryReconstructionError`` if that count does not exactly match
    the log-replay's de-duplicated total, rather than silently plotting a
    trajectory that could not be corroborated two ways.

    Returns (xs, ys): unique-problem-indexed step points, xs[0] == 1 is
    always the $64^3$ uniform baseline (gain 0%).
    """
    theta_len = theta_len or v2.N_MODES
    theta = [0.0] * theta_len
    seen = {tuple(theta)}
    unique_count = 1
    best = 0.0
    xs, ys = [1], [0.0]
    for r in arm_json["log"]:
        if "fe_val" not in r:
    for row in log:
        if "fe_val" not in row or pick_key not in row:
            continue
        calls += 1
        best = max(best, 100 * (r["fe_val"] / UNI64 - 1))
        xs.append(calls)
        ys.append(best)
    if "calls_in_budget" in arm_json and calls < arm_json["calls_in_budget"]:
        xs.append(arm_json["calls_in_budget"])
        ys.append(best)
        m = row["mode"]
        cand = list(theta)
        cand[m] = row[pick_key]
        key = tuple(round(v, 9) for v in cand)
        if key not in seen:
            seen.add(key)
            unique_count += 1
            gain = 100 * (row["fe_val"] / UNI64 - 1)
            best = max(best, gain)
            xs.append(unique_count)
            ys.append(best)
        # else: duplicate of an already-seen $64^3$ design; the cached FE
        # value is identical to the first occurrence by construction (same
        # content-addressed problem), so best-so-far cannot change and no
        # new unique-problem step is plotted.
        if row.get("action") == "ACCEPT":
            theta = cand

    n64_independent = sum(1 for c in calls_list if c.get("N") == 64)
    if n64_independent != unique_count:
        raise TrajectoryReconstructionError(
            f"{label}: log-replay unique 64^3 count ({unique_count}) does "
            f"not match the independent calls-list N==64 count "
            f"({n64_independent}); refusing to plot an unvalidated "
            f"trajectory for this arm.")
    return xs, ys


def best_so_far_traj(arm_json):
    return reconstruct_search_trajectory(
        arm_json["log"], arm_json["calls"], pick_key="pick",
        label=arm_json.get("arm", "?"))


def hist_traj(hist):
    calls = 1
    best = 0.0
    xs, ys = [1], [0.0]
    for r in hist["log"]:
        if "fe_val" not in r:
            continue
        calls += 1
        best = max(best, r["gain_vs_uniform_pct"])
        xs.append(calls)
        ys.append(best)
    if "fe_calls_total" in hist and calls < hist["fe_calls_total"]:
        xs.append(hist["fe_calls_total"])
        ys.append(best)
    return xs, ys
    return reconstruct_search_trajectory(
        hist["log"], hist["calls"], pick_key="pick", label="vgmm11 (historical)")


# ---------------------------------------------------------------- R1
def fig_r1(rep, hist, arms, acc):
    fig, (ax, ax2) = plt.subplots(
        1, 2, figsize=(7.2, 3.4), gridspec_kw={"width_ratios": [2.5, 1.1]})
        1, 2, figsize=(8.8, 4.3), gridspec_kw={"width_ratios": [1.65, 1.25]})
    fig.subplots_adjust(top=0.74, bottom=0.20, left=0.08, right=0.96, wspace=0.32)

    # full-FE real cumulative unique curve
    cum = rep["best_so_far_trajectory"]
    ax.step(range(1, len(cum) + 1), cum, where="post", color=C["fullfe"],
            lw=1.3, ls="-", label="Full-FE search (archived; unique "
            "evaluations)")
            lw=1.3, ls="-", label="Full-FE search (archived unique)")
    batch_ends = rep["fullfe_truncated"]["cumulative_unique_per_completed_scan"]
    ax.plot(batch_ends, [cum[b - 1] for b in batch_ends], marker="",
            color=C["fullfe"], ls="none", mfc="white", mec=C["fullfe"],
            ms=4)
    for b in batch_ends[::6]:
        ax.plot([b], [cum[b - 1]], marker="o", mfc="white",
                mec=C["fullfe"], ms=3.5)
    ff26 = rep["fullfe_truncated"]
    ax.plot([26], [ff26["best_gain_at_26_unique_pct"]], marker="*",
    g26 = ff26["best_gain_at_26_unique_pct"]
    ax.plot([26], [g26], marker="*",
            mfc=C["fullfe"], mec=C["fullfe"], ms=9, ls="none",
            label="Full-FE truncated @26 unique (matched budget)")
            label=f"Full-FE trunc. @26u ({g26:+.2f}%)")
    bc = ff26["batch_complete_frontier"]
    ax.plot([bc["unique_designs"]], [bc["best_gain_pct"]], marker="o",
    u_bc = bc["unique_designs"]
    g_bc = bc["best_gain_pct"]
    ax.plot([u_bc], [g_bc], marker="o",
            mfc="none", mec=C["fullfe"], ms=6, ls="none", mew=1.2,
            label=f"Full-FE batch-complete @ {bc['unique_designs']} unique "
                  f"(scans run in parallel batches)")
            label=f"Full-FE batch @{u_bc}u ({g_bc:+.2f}%)")

    # VG-MM seed 11 historical + new replicates
    xs, ys = hist_traj(hist)
    ax.step(xs, ys, where="post", color=C["vgmm"], lw=1.6,
            label="VG-MM cloud s11 (historical run)")
            label="VG-MM cloud s11 (historical)")
    dump_csv("R1_vgmm11", ["call", "best_gain_pct"],
             list(zip(xs, ys)))
    seeds = {"12": (0, (1, 1)), "13": (0, (3, 1, 1, 1))}
    for arm_name, ls in (("vgmm12", (0, (1, 1))), ("vgmm13", (0, (5, 2)))):
        if arm_name in arms:
            xs, ys = best_so_far_traj(arms[arm_name])
            ax.step(xs, ys, where="post", color=C["vgmm"], lw=1.1,
                    ls=ls, alpha=0.85,
                    label=f"VG-MM cloud s{arm_name[-2:]}")
            dump_csv(f"R1_{arm_name}", ["call", "best_gain_pct"],
                     list(zip(xs, ys)))
    for arm_name in ("rand11", "rand12", "rand13"):
        if arm_name in arms:
            xs, ys = best_so_far_traj(arms[arm_name])
            ax.step(xs, ys, where="post", color=C["rand"], lw=1.1,
                    ls=(0, (3, 1, 1, 1)) if arm_name != "rand11" else "-",
                    alpha=0.85,
                    label=f"RANDOM proposals r{arm_name[-2:]}")
                    label=f"RANDOM r{arm_name[-2:]}")
            dump_csv(f"R1_{arm_name}", ["call", "best_gain_pct"],
                     list(zip(xs, ys)))
    if "det" in arms:
        xs, ys = best_so_far_traj(arms["det"])
        ax.step(xs, ys, where="post", color=C["det"], lw=1.4, ls=(0, (4, 2)),
                label="DETERMINISTIC cyclic rule")
                label="DETERMINISTIC cyclic")
        dump_csv("R1_det", ["call", "best_gain_pct"], list(zip(xs, ys)))

    ax.axhline(0, color="k", lw=0.6, ls=":")
    ax.set_xlabel("Counted FE calls (distinct problems; $64^3$ unless marked)", fontsize=8.5)
    ax.set_xlabel("Unique $64^3$ search-grid designs (first encounter, log-replay de-duplicated; $96^3$ confirmation excluded)", fontsize=7.8)
    ax.set_ylabel("FE-verified $C_{1111}$ gain vs uniform [%]", fontsize=8.5)
    ax.set_xlim(0, 200)
    ax.set_title("(a) Verified gain vs budget (search grid $64^3$)",
                 fontsize=9.0)
    ax.legend(loc="lower right", framealpha=0.95, handlelength=2.2, fontsize=7.2)
                 fontsize=9.0, pad=8)
    # Move legend completely outside data curves (above the axes)
    ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.08), ncol=3,
              framealpha=0.95, handlelength=1.8, fontsize=6.3, columnspacing=0.6)

    # right panel: finer-grid confirmation markers, separated from (a)
    ax2.axhline(0, color="k", lw=0.6, ls=":")
    rows = []
    pts = {}
    pts["VG-MM s11"] = (hist["G_search64_pct"], hist["G_confirm96_pct"], C["vgmm"], "o")
    for nm in ("vgmm12", "vgmm13"):
        if nm in arms:
            pts[f"VG-MM s{nm[-2:]}"] = (arms[nm]["G26_pct"], arms[nm]["G_confirm96_pct"], C["vgmm"], "o")
    for nm in ("rand11", "rand12", "rand13"):
        if nm in arms:
            pts[f"RAND r{nm[-2:]}"] = (arms[nm]["G26_pct"], arms[nm]["G_confirm96_pct"], C["rand"], "s")
    if "det" in arms:
        pts["DET"] = (arms["det"]["G26_pct"], arms["det"]["G_confirm96_pct"], C["det"], "^")
    for nm in ("demonly11", "demonly12", "demonly13"):
        if nm in arms:
            pts[f"DEM s{nm[-2:]}"] = (arms[nm]["G26_pct"], arms[nm]["G_confirm96_pct"], C["demonly"], "D")
    ff = rep["fullfe_truncated"]
    pts["Full-FE @26u"] = (ff["best_gain_at_26_unique_pct"], None, C["fullfe"], "*")
    pts["Full-FE 194u"] = (
        100 * (arch_val(rep, "C1111_winner_search") / UNI64 - 1),
        100 * (arch_val(rep, "C1111_winner_confirm") / UNI96 - 1),
        C["fullfe"], "o")

    for i, (lab, (g64, g96, col, mk)) in enumerate(pts.items()):
    labels = ["VG s11", "VG s12", "VG s13", "RAND r11", "RAND r12", "RAND r13",
              "DET", "DEM s11", "DEM s12", "DEM s13", "FFE @26u", "FFE 194u"]

    for i, ((lab, (g64, g96, col, mk)), short_lab) in enumerate(zip(pts.items(), labels)):
        x = i
        # Search grid 64^3: FILLED marker
        ax2.plot([x], [g64], mk, color=col, ms=5.5, ls="none",
                 mfc=col, mec=col, mew=1.0, zorder=4)
        # Finer-grid confirmation 96^3: OPEN marker (connected by dotted leader line)
        if g96 is not None:
            ax2.plot([x, x], [g64, g96], color=col, ls=":", lw=1.0, alpha=0.7, zorder=2)
            ax2.plot([x], [g96], mk, color=col, ms=6.5, ls="none",
                     mfc="white", mec=col, mew=1.4, zorder=5)
        rows.append([lab, g64, g96])

    ax2.set_xlim(-0.6, len(pts) - 0.4)
    ax2.set_xticks(range(len(pts)))
    ax2.set_xticklabels(list(pts.keys()), rotation=50, ha="right", fontsize=7.0)
    ax2.set_xticklabels(labels, rotation=60, ha="right", fontsize=6.8)
    ax2.set_ylabel("gain [%]", fontsize=8.5)
    ax2.set_title("(b) Endpoints: $64^3$ (filled)\nvs $96^3$ confirm (open)", fontsize=8.5)
    # Add compact legend handles for 64^3 filled vs 96^3 open
    h_search = Line2D([], [], marker="o", color="#555555", mfc="#555555", ls="none", ms=5, label="search $64^3$")
    h_confirm = Line2D([], [], marker="o", color="#555555", mfc="white", mec="#555555", mew=1.3, ls="none", ms=5.5, label="confirm $96^3$")
    ax2.legend(handles=[h_search, h_confirm], loc="lower left", fontsize=6.8, framealpha=0.9, handletextpad=0.2)
    ax2.set_title("(b) Endpoints: search ($64^3$) vs confirm ($96^3$)", fontsize=9.0, pad=8)
    # Add compact legend handles for 64^3 filled vs 96^3 open in open middle-left region
    h_search = Line2D([], [], marker="o", color="#555555", mfc="#555555", ls="none", ms=5, label="search $64^3$ (filled)")
    h_confirm = Line2D([], [], marker="o", color="#555555", mfc="white", mec="#555555", mew=1.3, ls="none", ms=5.5, label="confirm $96^3$ (open)")
    ax2.legend(handles=[h_search, h_confirm], loc="center left", bbox_to_anchor=(0.03, 0.45),
               fontsize=6.8, framealpha=0.9, handletextpad=0.2)

    dump_csv("R1_endpoints", ["arm", "G_search64_pct", "G_confirm96_pct"], rows)
    fig.tight_layout()
    save(fig, "R1_budget_steps")


def arch_val(rep, key):
    a = json.load(open(os.path.join(v2.N3, "e3_fe_baseline.json")))
    return a[key]


# ---------------------------------------------------------------- R2
def fig_r2(rep, quad):
    d = rep["diag"]
    pool = rep["pool"]
    ff = rep["fullfe_truncated"]
    dem = [p["C_DEM"] for p in pool]
    fe = [p["C_FE"] for p in pool]
    gain_fe = [p["gain_FE_pct"] for p in pool]
    dem_uni = next(p["C_DEM"] for p in pool if all(abs(x) < 1e-6 for x in p["theta"]))
    gain_dem = [100.0 * (p["C_DEM"] / dem_uni - 1.0) for p in pool]

    fig, axs = plt.subplots(1, 3, figsize=(9.4, 3.4), gridspec_kw={"wspace": 0.36})

    # (a) raw parity
    a = axs[0]
    a.plot(dem, fe, "o", color=C["rand"], ms=3.0, alpha=0.75, mec="none")
    all_s = dem + fe
    lo, hi = min(all_s) * 0.98, max(all_s) * 1.02
    a.plot([lo, hi], [lo, hi], "k--", lw=0.9, alpha=0.7, label="identity parity ($y=x$)")
    a.set_xlim(lo, hi)
    a.set_ylim(lo, hi)
    a.set_aspect("equal")
    a.set_xlabel("conditional-DEM score $C_{\\mathrm{DEM}}$ (cloud 11) [-]", fontsize=8.0)
    a.set_ylabel("voxel-FE $C_{1111}$ [-]", fontsize=8.0)
    a.set_title("(a) Raw stiffness parity\n(identity line; DEM errs stiff)", fontsize=8.5)
    # mark best FE and best DEM
    b_fe = np.argmax(fe)
    b_dem = np.argmax(dem)
    a.plot(dem[b_fe], fe[b_fe], "^", color=C["det"], ms=7, mfc="none", mew=1.4)
    a.annotate("FE-best", (dem[b_fe], fe[b_fe]), textcoords="offset points",
               xytext=(-8, 8), fontsize=7.5, ha="right", va="bottom", color=C["det"], fontweight="bold")
    a.plot(dem[b_dem], fe[b_dem], "o", color=C["vgmm"], ms=7, mfc="none", mew=1.4)
    a.annotate("DEM-best", (dem[b_dem], fe[b_dem]), textcoords="offset points",
               xytext=(-10, -12), fontsize=7.5, ha="right", va="top", color=C["vgmm"], fontweight="bold")

    # (b) normalized gains
    b = axs[1]
    b.plot(gain_dem, gain_fe, "o", color=C["rand"], ms=3.0, alpha=0.75,
           mec="none")
    all_g = gain_dem + gain_fe
    glo, ghi = min(all_g) - 2, max(all_g) + 2
    b.plot([glo, ghi], [glo, ghi], "k--", lw=0.9, alpha=0.7)
    b.axhline(0, color="k", lw=0.5, ls=":")
    b.axvline(0, color="k", lw=0.5, ls=":")
    b.set_xlim(glo, ghi)
    b.set_ylim(glo, ghi)
    b.set_aspect("equal")
    b.set_xlabel("DEM gain [%] (recomputed denom.)", fontsize=8.0)
    b.set_ylabel("FE gain [%] vs uniform $64^3$", fontsize=8.0)
    b.set_title("(b) Normalized gains\n$\\rho=0.664$, $\\tau=0.478$ (tie-aware)", fontsize=8.5)
    b.plot(gain_dem[b_fe], gain_fe[b_fe], "^", color=C["det"], ms=7,
           mfc="none", mew=1.4)
    b.plot(gain_dem[b_dem], gain_fe[b_dem], "o", color=C["vgmm"], ms=7,
           mfc="none", mew=1.4)
    b.plot([ff["best_gain_at_26_unique_pct"]],
           [ff["best_gain_at_26_unique_pct"]], "*", color=C["fullfe"],
           mec=C["fullfe"], ms=10, mew=1.1)

    c = axs[2]
    gg = rep["groups"]
    x = np.arange(len(gg))
    mats = [g for g in gg if g.get("discordance_class") == "material_ranking_loss"]
    ids = [g for g in gg if g.get("discordance_class") == "different_id_only"]
    c.bar(x - 0.21, [g["fe_best_gain"] for g in gg], width=0.42,
          color=C["det"], label="FE-argmax pick", edgecolor="none")
    c.bar(x + 0.21, [g["dem_pick_fe_gain"] for g in gg], width=0.42,
          color=C["vgmm"], label="DEM top-1 pick (FE value)",
          edgecolor="none")
    for g in ids:
        c.text(g_idx(gg, g) + 0.21, g["dem_pick_fe_gain"] + 0.15, "id",
               fontsize=5.5, ha="center", color="#333333")
    c.axhline(0, color="k", lw=0.6)
    c.set_xlabel("checkpoint (sweep $\\times$ mode, search order)", fontsize=8.0)
    c.set_ylabel("FE gain of pick [%]", fontsize=8.0)
    c.set_title(f"(c) Scan groups: top-1 wrong in {d['scan_groups_dem_top1_wrong']}/{d['scan_groups']}\n"
                f"({d['of_which_different_id_only']} id-only, {d['of_which_material_ranking_loss']} material ranking loss)",
                fontsize=8.5)
    c.legend(loc="upper right", fontsize=7.0, framealpha=0.92)

    dump_csv("R2_pool", ["C_DEM", "C_FE", "gain_FE_pct", "gain_DEM_pct"],
             [[float(dd), float(f), float(gf), float(gd)]
              for dd, f, gf, gd in zip(dem, fe, gain_fe, gain_dem)])
    dump_csv("R2_groups",
             ["sweep", "mode", "fe_best_gain", "dem_pick_fe_gain", "agree",
              "discordance_class"],
             [[g["sweep"], g["mode"], g["fe_best_gain"],
               g["dem_pick_fe_gain"], g["agree"],
               g.get("discordance_class", "agree")] for g in gg])
    fig.tight_layout()
    save(fig, "R2_parity")


def g_idx(gg, g):
    return gg.index(g)


# ---------------------------------------------------------------- R3
def fig_r3(acc, arms, hist, rep):
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    fams = acc["family_values"]
    ax.axhline(0, color="k", lw=0.6, ls=":")

    # Predeclared practical margin shaded band relative to minimum VG-MM outcome
    min_vgmm = min(fams["vgmm"].values())
    ax.axhspan(min_vgmm - 1.0, min_vgmm, color=C["vgmm"], alpha=0.12, zorder=0,
    ax.axhspan(min_vgmm - 1.0, min_vgmm, color=C["vgmm"], alpha=0.15, zorder=0,
               label=f"Practical margin $\\delta=1.0$ pp ({min_vgmm-1.0:.2f}–{min_vgmm:.2f}%)")
    ax.axhline(min_vgmm - 1.0, color=C["vgmm"], ls="--", lw=0.8, alpha=0.6, zorder=1)
    ax.axhline(min_vgmm, color=C["vgmm"], ls="--", lw=0.8, alpha=0.6, zorder=1)

    specs = [
        ("VG-MM\n(cloud seeds)", fams.get("vgmm", {}), C["vgmm"], "o", "s"),
        ("RANDOM\n(RNG seeds)", fams.get("rand", {}), C["rand"], "s", "r"),
        ("DETERM.\n(no seed)", fams.get("det", {}), C["det"], "^", ""),
        ("DEM-only\n(cloud seeds)", fams.get("demonly", {}), C["demonly"], "D", "s"),
    ]
    rows = []
    spread = 0.22  # Wide spread to completely prevent text annotation collisions
    spread = 0.25  # Wide spread to completely prevent text annotation collisions

    for i, (lab, vals, col, mk, seed_pfx) in enumerate(specs):
        n_items = len(vals)
        offsets = [-spread, 0.0, spread] if n_items == 3 else [0.0] * n_items
        for (k, v), dx in zip(sorted(vals.items()), offsets):
            x = i + dx
            # Find 96^3 confirmation value if available
            g96 = None
            if seed_pfx == "s" and lab.startswith("VG-MM"):
                arm_id = f"vgmm{k}"
                if arm_id in arms:
                    g96 = arms[arm_id]["G_confirm96_pct"]
                elif k == "11":
                    g96 = hist["G_confirm96_pct"]
            elif seed_pfx == "r":
                arm_id = f"rand{k}"
                if arm_id in arms:
                    g96 = arms[arm_id]["G_confirm96_pct"]
            elif lab.startswith("DETERM"):
                if "det" in arms:
                    g96 = arms["det"]["G_confirm96_pct"]
            elif lab.startswith("DEM-only"):
                arm_id = f"demonly{k}"
                if arm_id in arms:
                    g96 = arms[arm_id]["G_confirm96_pct"]

            # Plot search grid 64^3: FILLED marker
            ax.plot([x], [v], mk, color=col, ms=6.5, ls="none", mfc=col, mec=col, zorder=4)
            # Plot confirm grid 96^3: OPEN marker with connecting dotted line
            if g96 is not None:
                ax.plot([x, x], [v, g96], color=col, ls=":", lw=1.0, alpha=0.7, zorder=2)
                ax.plot([x], [g96], mk, color=col, ms=7.0, ls="none", mfc="white", mec=col, mew=1.4, zorder=5)

            # Annotation for seed ID
            # Annotation for seed ID with staggered clearance
            if seed_pfx:
                tag = f"{seed_pfx}{k}"
                # Place tag with clear vertical clearance
                y_tag = max(v, g96 if g96 is not None else v)
                ax.annotate(tag, (x, y_tag), textcoords="offset points",
                            xytext=(0, 7), fontsize=7.2, ha="center", color=col, fontweight="bold")
                if lab.startswith("DEM-only") and k == "12":
                    # Place s12 tag below marker to avoid vertical range line
                    y_tag = min(v, g96 if g96 is not None else v)
                    ax.annotate(tag, (x, y_tag), textcoords="offset points",
                                xytext=(0, -12), fontsize=7.0, ha="center", va="top",
                                color=col, fontweight="bold")
                else:
                    y_tag = max(v, g96 if g96 is not None else v)
                    x_off = -2 if dx < -0.05 else (2 if dx > 0.05 else 0)
                    y_off = 8
                    ax.annotate(tag, (x, y_tag), textcoords="offset points",
                                xytext=(x_off, y_off), fontsize=7.0, ha="center", va="bottom",
                                color=col, fontweight="bold")

            rows.append([lab.replace("\n", " "), f"{seed_pfx}{k}" if seed_pfx else "none", v, g96])

        # Vertical range line across seeds
        ys_ = list(vals.values())
        if len(ys_) > 1:
            ax.plot([i, i], [min(ys_), max(ys_)], color=col, lw=0.8, ls=(0, (2, 2)), alpha=0.6)

    # Full-FE truncated comparator
    ff = rep["fullfe_truncated"]
    ff_val = ff["best_gain_at_26_unique_pct"]
    ax.plot([4], [ff_val], "*", color=C["fullfe"], ms=11, ls="none", zorder=4)
    # Center label above star marker to stay safely within axis bounds
    ax.annotate("Full-FE @26 unique\n(+4.93%)", (4, ff_val),
                textcoords="offset points", xytext=(-8, 8), fontsize=6.8, ha="right", color=C["fullfe"])
                textcoords="offset points", xytext=(0, 9), fontsize=7.0, ha="center", va="bottom", color=C["fullfe"])
    rows.append(["Full-FE truncated", "26u", ff_val, None])

    ax.set_xlim(-0.6, 4.8)
    ax.set_xticks(range(5))
    ax.set_xticklabels(["VG-MM\n(seeds 11–13)", "RANDOM\n(seeds 11–13)",
                        "DETERM.\n(no seed)", "DEM-only\n(seeds 11–13)",
                        "FULL-FE\ntruncated"], fontsize=7.8)
    ax.set_ylabel("Verified gain $G_{26}$ [%] (common 26-call budget)", fontsize=8.5)
    ax.set_title("Controlled seed/policy endpoints at common budget (26 calls)\n"
                 "Filled markers: search grid $64^3$; open markers: confirm grid $96^3$",
                 fontsize=8.5)
    ax.set_ylim(-8.2, 7.8)

    # Custom legend for markers and shaded band
    h_s = Line2D([], [], marker="o", color="#555555", mfc="#555555", ls="none", ms=5.5, label="search $64^3$")
    h_c = Line2D([], [], marker="o", color="#555555", mfc="white", mec="#555555", mew=1.3, ls="none", ms=6.0, label="confirm $96^3$")
    h_b = mpatches.Patch(fc=C["vgmm"], alpha=0.15, label=r"Practical margin ($\delta = 1.0$ pp)")
    h_s = Line2D([], [], marker="o", color="#555555", mfc="#555555", ls="none", ms=5.5, label="search $64^3$ (filled)")
    h_c = Line2D([], [], marker="o", color="#555555", mfc="white", mec="#555555", mew=1.3, ls="none", ms=6.0, label="confirm $96^3$ (open)")
    h_b = mpatches.Patch(fc=C["vgmm"], alpha=0.15, label=r"Practical margin ($\delta = 1.0$ pp: 4.55%–5.55%)")
    ax.legend(handles=[h_s, h_c, h_b], loc="lower left", fontsize=7.2, framealpha=0.92)

    dump_csv("R3_family_endpoints", ["family", "seed", "G26_search_pct", "G_confirm96_pct"], rows)
    fig.tight_layout()
    save(fig, "R3_policy_seeds")


# ---------------------------------------------------------------- R4
def fig_r4():
    fig, ax = plt.subplots(figsize=(7.4, 3.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.35, 4.6)
    ax.axis("off")

    def box(x, y, w, h, text, fc, ec, fs=7.2, rounded=True):
        sty = "round,pad=0.06,rounding_size=0.12" if rounded else "square,pad=0.06"
        ax.add_patch(mpatches.FancyBboxPatch((x, y), w, h, boxstyle=sty, fc=fc, ec=ec, lw=1.2))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)

    def arrow(x1, y1, x2, y2, style="-|>", col="k", ls="-", lab=None, lx=0, ly=0):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle=style, color=col, lw=1.2,
                                    linestyle=ls, connectionstyle="arc3,rad=0"))
        if lab:
            ax.text((x1 + x2) / 2 + lx, (y1 + y2) / 2 + ly, lab, fontsize=6.8,
                    ha="center", color=col, fontweight="bold")

    # Consistent Okabe-Ito colors agreeing with caption and manuscript:
    # Frozen DEM surrogate = vermillion (#D55E00)
    # Voxel FE operations = blue (#0072B2)
    # Bookkeeping = neutral grey (#555555)
    DEM_FC, DEM_EC = "#FDE3D0", "#D55E00"      # frozen neural model (vermillion)
    FE_FC, FE_EC = "#DCEEF7", "#0072B2"        # FE evaluations (blue)
    ST_FC, ST_EC = "#EAEAEA", "#555555"        # bookkeeping (grey)

    # Top row (proposal generation)
    box(0.15, 3.35, 2.30, 0.85, "incumbent $\\theta$\n(12 coefficients, $t\\in[0.12,0.55]$,\n$V_f$ fixed by bisection)", ST_FC, ST_EC)
    box(2.85, 3.35, 2.70, 0.85, "frozen conditional DEM\nscores 9 grid trials\n(fixed 50k cloud, seed $c$)", DEM_FC, DEM_EC)
    box(5.95, 3.35, 2.30, 0.85, "propose top-scored\nNON-incumbent trial", ST_FC, ST_EC)
    box(0.15, 3.30, 2.35, 0.90, "incumbent $\\theta$\n(12 coefficients, $t\\in[0.12,0.55]$,\n$V_f$ fixed by bisection)", ST_FC, ST_EC, fs=6.8)
    box(2.80, 3.30, 2.75, 0.90, "frozen conditional DEM\nscores 9 grid trials\n(fixed 50k cloud, seed $c$)", DEM_FC, DEM_EC, fs=6.8)
    box(5.85, 3.30, 2.35, 0.90, "propose top-scored\nNON-incumbent trial", ST_FC, ST_EC, fs=6.8)

    # Middle row (in-loop FE acceptance filter)
    box(7.85, 1.85, 1.95, 0.85, "voxel FE solve\n$64^3$ (code_aster,\npinned digest)", FE_FC, FE_EC)
    box(5.15, 1.85, 2.30, 0.85, "accept IFF strictly\n$C_{FE} > $ incumbent\nbest (else reject)", ST_FC, ST_EC)
    box(2.15, 1.85, 2.45, 0.85, "next checkpoint\n(2 sweeps $\\times$ 12 modes)", ST_FC, ST_EC)
    box(7.60, 1.80, 2.25, 0.90, "voxel FE solve\n$64^3$ (code_aster,\npinned digest)", FE_FC, FE_EC, fs=6.8)
    box(4.90, 1.80, 2.40, 0.90, "accept IFF strictly\n$C_{FE} > $ incumbent\nbest (else reject)", ST_FC, ST_EC, fs=6.8)
    box(2.00, 1.80, 2.60, 0.90, "next checkpoint\n(2 sweeps $\\times$ 12 modes)", ST_FC, ST_EC, fs=6.8)

    # Bottom row (budget stop & confirmation)
    box(0.20, 0.40, 3.40, 0.85, "budget stop: 26 counted calls\n(1 baseline + 24 proposals + 1 confirm)", ST_FC, ST_EC)
    box(4.00, 0.40, 2.70, 0.85, "final confirmation\nFE $96^3$ of incumbent", FE_FC, FE_EC)
    box(7.10, 0.40, 2.70, 0.85, "return design + verified\n$G_{64}$, $G_{96}$ vs uniform", ST_FC, ST_EC)
    box(0.15, 0.35, 3.45, 0.90, "budget stop: 26 counted calls\n(1 baseline + 24 proposals + 1 confirm)", ST_FC, ST_EC, fs=6.8)
    box(3.90, 0.35, 2.80, 0.90, "final confirmation\nFE $96^3$ of incumbent", FE_FC, FE_EC, fs=6.8)
    box(7.00, 0.35, 2.80, 0.90, "return design + verified\n$G_{64}$, $G_{96}$ vs uniform", ST_FC, ST_EC, fs=6.8)

    # Top row connections
    arrow(2.45, 3.77, 2.85, 3.77)
    arrow(5.55, 3.77, 5.95, 3.77)
    arrow(2.50, 3.75, 2.80, 3.75)
    arrow(5.55, 3.75, 5.85, 3.75)

    # Transition to FE solve
    arrow(8.25, 3.35, 8.80, 2.70)
    arrow(8.20, 3.30, 8.65, 2.70)

    # Middle row connections
    arrow(7.85, 2.27, 7.45, 2.27)
    arrow(5.15, 2.27, 4.60, 2.27)
    arrow(7.60, 2.25, 7.30, 2.25)
    arrow(4.90, 2.25, 4.60, 2.25)

    # Accept update loop: routed cleanly back to incumbent box on left
    arrow(6.30, 2.70, 6.30, 3.02, col="#D55E00", ls=(0, (3, 2)))
    arrow(6.30, 3.02, 1.30, 3.02, col="#D55E00", ls=(0, (3, 2)))
    arrow(1.30, 3.02, 1.30, 3.35, col="#D55E00", ls=(0, (3, 2)))
    ax.text(3.80, 2.86, "accept: update incumbent", fontsize=6.8, ha="center", va="center", color="#D55E00", fontweight="bold")
    arrow(6.10, 2.70, 6.10, 3.02, col="#D55E00", ls=(0, (3, 2)))
    arrow(6.10, 3.02, 1.30, 3.02, col="#D55E00", ls=(0, (3, 2)))
    arrow(1.30, 3.02, 1.30, 3.30, col="#D55E00", ls=(0, (3, 2)))
    ax.text(3.70, 2.86, "accept: update incumbent", fontsize=6.8, ha="center", va="center", color="#D55E00", fontweight="bold")

    # Reject / next step loop
    arrow(2.15, 2.27, 1.40, 1.25, col="#888888", ls=(0, (3, 2)), lab="loop", lx=-0.35, ly=0.15)
    arrow(2.00, 2.25, 1.40, 1.25, col="#888888", ls=(0, (3, 2)), lab="loop", lx=-0.35, ly=0.15)

    # Bottom row connections
    arrow(3.60, 0.82, 4.00, 0.82)
    arrow(6.70, 0.82, 7.10, 0.82)
    arrow(3.60, 0.80, 3.90, 0.80)
    arrow(6.70, 0.80, 7.00, 0.80)

    leg = [
        mpatches.Patch(fc=DEM_FC, ec=DEM_EC, label="frozen conditional DEM surrogate (vermillion)"),
        mpatches.Patch(fc=FE_FC, ec=FE_EC, label="volume-calibrated voxel-FE (blue)"),
        mpatches.Patch(fc=ST_FC, ec=ST_EC, label="bookkeeping / control logic (grey)")
    ]
    ax.legend(handles=leg, loc="lower center", bbox_to_anchor=(0.5, -0.06),
              ncol=3, fontsize=7.4, frameon=False)
    ax.set_title("Implemented verification-guided model management (VG-MM) workflow\n"
                 "No adaptive trust-region radii; no discrepancy learning models", fontsize=8.5)
    save(fig, "R4_method_diagram")


# ---------------------------------------------------------------- R5
def fig_r5(hist, arms, rep):
    """Depict each design on the grid it was actually searched on ($64^3$),
    using its saved SEARCH shift (the shift value ``bisect_shift_discrete``
    computed for that theta at $N=64$, the same pure geometric calibration
    the original FE search used -- not a re-run of FE). The realized $V_f$
    reported in each title is computed directly from the SAME mask array
    plotted (``discrete_mask(64, theta, shift).mean()``), not a separately
    hard-coded number, so caption and figure cannot drift apart again.

    $96^3$ values are reported as confirmation STIFFNESS numbers only
    (already-archived ``C1111_winner_confirm`` / ``C1111_uniform_confirm``
    values); no $96^3$ mask is rendered, because the archived confirmation
    step re-calibrates its shift separately at $N=96$
    (``bisect_shift_discrete(96, theta)`` inside ``r2_arms.py``'s
    ``winner_confirm_96`` call) rather than reusing the $64^3$ search
    shift, so a $96^3$ image would depict a different geometry realization
    than the $64^3$ image in the same row -- that distinction is stated in
    the title rather than papered over by rendering it at $N=96$ anyway.
    """
    e3 = json.load(open(os.path.join(v2.N3, "e3_fe_baseline.json")))
    N = 64  # depict the actual search grid; do not upsample to 96^3
    designs = [
        ("Uniform", [0.0] * v2.N_MODES, v2.bisect_shift_discrete(
            64, [0.0] * v2.N_MODES), UNI64, UNI96, "$C_{1111}$=0.10528 "
            f"($64^3$) / 0.10572 ($96^3$)", C["uniform"]),
        ("Uniform", [0.0] * v2.N_MODES,
         v2.bisect_shift_discrete(64, [0.0] * v2.N_MODES),
         UNI64, UNI96, C["uniform"]),
        ("VG-MM winner", hist["theta_final"],
          v2.bisect_shift_discrete(64, hist["theta_final"]),
          hist["C_winner_search64"], hist["C_winner_confirm96"],
          f"grid $64^3$, VF=0.1933\n$G$=+{hist['G_search64_pct']:.2f}% "
          f"($64^3$), +{hist['G_confirm96_pct']:.2f}% ($96^3$)", C["vgmm"]),
        ("Full-FE winner", json.load(open(os.path.join(
            v2.N3, "e3_fe_baseline.json")))["theta"],
          json.load(open(os.path.join(v2.N3, "e3_fe_baseline.json")))
          ["shift_search"],
          0.1121774685, 0.11242472831,
          "grid $64^3$, VF=0.1933\n$G$=+6.55% ($64^3$), +6.34% ($96^3$)",
          C["fullfe"]),
         v2.bisect_shift_discrete(64, hist["theta_final"]),
         hist["C_winner_search64"], hist["C_winner_confirm96"], C["vgmm"]),
        ("Full-FE winner", e3["theta"], e3["shift_search"],
         e3["C1111_winner_search"], e3["C1111_winner_confirm"], C["fullfe"]),
    ]
    N = 96
    c = (np.arange(N) + 0.5) / N
    X, Y, Z = np.meshgrid(c, c, c, indexing="ij")
    fig, axs = plt.subplots(2, 3, figsize=(7.5, 4.2))
    fig.subplots_adjust(left=0.10, right=0.88, top=0.88, bottom=0.08, wspace=0.28, hspace=0.30)
    fig, axs = plt.subplots(2, 3, figsize=(7.5, 4.6))
    fig.subplots_adjust(left=0.10, right=0.88, top=0.80, bottom=0.10, wspace=0.32, hspace=0.32)
    tmin, tmax = v2.T_MIN, v2.T_MAX
    for j, (name, theta, shift, c64, c96, note, col) in enumerate(designs):
    r5_rows = []
    for j, (name, theta, shift, c64, c96, col) in enumerate(designs):
        tf = v2.t_field(X[:, :, N // 2], Y[:, :, N // 2], Z[:, :, N // 2],
                        theta, shift)
        msk = v2.discrete_mask(N, theta, shift)[:, :, N // 2]
        # Realized Vf computed on the FULL 3D mask at this grid (not just
        # the plotted mid-plane slice), matching the definition used
        # elsewhere (discrete_vf = discrete_mask(...).mean()).
        vf_full3d = float(v2.discrete_mask(N, theta, shift).mean())
        gain64 = 100 * (c64 / UNI64 - 1)
        gain96 = 100 * (c96 / UNI96 - 1)
        # Short per-panel title: name, grid, and the realized Vf computed
        # from THIS exact plotted mask. Gain numbers and the 96^3-geometry
        # caveat move to a single compact figure-level annotation below
        # (fig.text) instead of being repeated verbatim in all 3 titles,
        # which previously overflowed panel width and bled into neighbors.
        note = f"$64^3$, real. $V_f={vf_full3d:.5f}$"
        a = axs[0, j]
        im = a.pcolormesh(X[:, :, N // 2], Y[:, :, N // 2], tf,
                          cmap="viridis", vmin=tmin, vmax=tmax,
                          shading="auto")
        a.set_title(f"{name}\n{note}", fontsize=7.2)
        a.set_title(f"{name}\n{note}\n$G_{{64}}$={gain64:+.2f}%  $G_{{96}}$={gain96:+.2f}%*",
                     fontsize=7.0)
        a.set_aspect("equal")
        if j == 0:
            a.set_ylabel("thickness field $t(\\cdot,\\cdot,0.5)$\n(shared color scale)", fontsize=8.0)
            a.set_ylabel("thickness field $t(\\cdot,\\cdot,0.5)$\n(shared color scale, $64^3$ grid)", fontsize=8.0)
        a.set_xticks([0, 0.5, 1])
        a.set_yticks([0, 0.5, 1])
        b = axs[1, j]
        msk = v2.discrete_mask(N, theta, shift)[:, :, N // 2]
        # vmin=0, vmax=1.0 ensures solid material is rendered solid black on white
        b.pcolormesh(X[:, :, N // 2], Y[:, :, N // 2], msk.astype(float),
                     cmap="Greys", vmin=0, vmax=1.0, shading="auto")
        b.set_aspect("equal")
        b.set_xticks([0, 0.5, 1])
        b.set_yticks([0, 0.5, 1])
        if j == 0:
            b.set_ylabel("solid mask (mid-plane,\nblack = material)", fontsize=8.0)
            b.set_ylabel("solid mask (mid-plane, $64^3$ grid,\nblack = material)", fontsize=8.0)
        # loading orientation marker (KUBC macro strain eps11, x-direction)
        b.annotate("", xy=(0.95, 0.08), xytext=(0.55, 0.08),
                   arrowprops=dict(arrowstyle="-|>", color=col, lw=1.6),
                   xycoords="axes fraction")
        b.text(0.75, 0.12, "$\\varepsilon_{11}$", color=col, fontsize=7.5,
               ha="center", transform=b.transAxes, fontweight="bold")
        dump_csv(f"R5_midplane_{j}",
                 ["i", "j", "t", "mask"],
                 [[int(i), int(k), float(tf[i, k]),
                   int(msk[i, k])]
                  for i in range(0, N, 2) for k in range(0, N, 2)])
        r5_rows.append([name, N, shift, vf_full3d, c64, c96, gain64, gain96])
    dump_csv("R5_realized_vf",
             ["design", "grid_N", "shift", "realized_Vf_full3D",
              "C1111_64", "C1111_96", "gain64_pct", "gain96_pct"],
             r5_rows)
    cax = fig.add_axes([0.90, 0.53, 0.02, 0.35])
    cb = fig.colorbar(im, cax=cax)
    cb.set_label("local thickness $t$ [-]", fontsize=8.5)
    fig.text(0.5, 0.015,
             "*$G_{96}$ (96$^3$ confirmation gain) uses a separately "
             "96$^3$-calibrated shift; the geometry pictured above is the "
             "64$^3$ search-grid design, not the 96$^3$-confirmed one.",
             ha="center", fontsize=6.6, color="0.25")
    save(fig, "R5_geometry")


def main():
    rep, hist, arms, acc, quad, arch, paper = load_inputs()
    fig_r1(rep, hist, arms, acc)
    fig_r2(rep, quad)
    fig_r3(acc, arms, hist, rep)
    fig_r4()
    fig_r5(hist, arms, rep)


if __name__ == "__main__":
    main()
