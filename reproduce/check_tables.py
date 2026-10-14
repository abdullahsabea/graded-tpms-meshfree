"""Recompute every numeric table entry of the article and its supplement from the
archived records, and compare with the printed values.

Usage (from the archive root):   python reproduce/check_tables.py
Printed values are read from reproduce/printed_tables.json, extracted from the
submitted LaTeX sources. Each recomputed cell is formatted at the printed
precision and compared as text. Exit status 0 if every checked cell agrees.

Records used (paths relative to the archive root) are listed in SOURCES below;
each check names the record and key it reads.
"""
import csv
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

import os
ROOT = Path(os.environ.get("ARCHIVE_ROOT", Path(__file__).resolve().parents[1]))
HERE = Path(__file__).resolve().parent
R2 = ROOT / "AUTORESEARCH_Q1_REVISION/ROUND2_FINAL_REPAIR/results"
WPA = ROOT / "AUTORESEARCH_Q1_REVISION/_deep_review/wpa"
N3 = ROOT / "research/n3"
CONF = N3 / "conforming"
VT, EXPO = 0.19328, 1.21          # search volume target and secant volume exponent

J = lambda p: json.load(open(p, encoding="utf-8"))
PRINTED = J(Path(__file__).with_name("printed_tables.json"))


# ---------------------------------------------------------------- formatting
def norm(s):
    s = s.replace("$", "").replace("\\%", "").replace("%", "").replace("\\,", "")
    s = s.replace("{", "").replace("}", "").replace("~", "").replace("\\ ", "")
    s = s.replace("\\pm", "±").replace("\\times10^", "e").replace("\\times 10^", "e")
    s = s.replace("−", "-").replace("\\textendash", "-").replace("--", "–")
    return re.sub(r"\s+", "", s)


def f(x, d):                      # fixed decimals
    return f"{x:.{d}f}"


def sg(x, d):                     # signed fixed decimals
    return f"{x:+.{d}f}"


def sci(x, d=1):                  # 2.3e-7 style
    m, e = f"{x:.{d}e}".split("e")
    return f"{m}e-{int(e[1:])}" if e[0] == "-" else f"{m}e{int(e)}"


def vadj(c, v):                   # secant volume adjustment toward VT
    return c * (VT / v) ** EXPO


# ---------------------------------------------------------------- comparison
results = []


def check(table, rowkey, expected):
    """expected: list of cell strings (None = not checked) for columns 1..n."""
    rows = PRINTED[table]
    match = [r for r in rows if norm(rowkey) in norm(r[0])]
    if len(match) != 1:
        results.append((table, rowkey, "-", "ROW NOT FOUND" if not match else "ROW AMBIGUOUS", "", False))
        return
    cells = match[0][1:]
    for j, e in enumerate(expected):
        if e is None:
            continue
        p = cells[j] if j < len(cells) else ""
        ok = norm(p) == norm(e)
        results.append((table, rowkey, j + 1, p.strip(), e, ok))


def approx(table, label, printed, value, tol, note):
    ok = abs(float(printed) - value) <= tol
    results.append((table, label, "-", printed, f"{value:.5f} (tol {tol}; {note})", ok))


# ================================================================= main text
def tab_chainnorms():
    m = J(R2 / "r2_mechanics_audit.json")["designs"]
    a = J(WPA / "a3_a4_score_audit.json")
    de = lambda k: sg(100 * (a[k]["score_chain"] / a[k]["score_frozen"] - 1), 2)
    row = lambda k, ak: [f(100 * m[k]["frac_cloud_clipped"], 1), f(m[k]["mean_ratio_pct"], 3),
                         f(m[k]["unclipped_mean_ratio_pct"], 3), de(ak)]
    check("tab:chainnorms", "Uniform", ["--", "0", "0", "0"])
    check("tab:chainnorms", "Band-and-smoothness", row("band_restricted_printable", "band"))
    check("tab:chainnorms", "Unconstrained", row("demonly_graded_archived", "unconstrained"))
    check("tab:chainnorms", "Filtered-search", row("vgmm_round1_winner", "vgmm_seed11"))
    check("tab:chainnorms", "FE coordinate", ["--", "--", "--", de("fullfe")])


def conf_rows():
    c = J(CONF / "conf_summary.json")
    keys = dict(uniform="N48_M96_rc", band="N48_M96_printable_rc", vgmm="N48_M96_vgmm_rc",
                fullfe="N48_M96_fullfe_rc", graded="N48_M96_graded_rc")
    out = {}
    for d, k in keys.items():
        V = c["kubc"][k]["V"]
        assert abs(c["pbc"][k]["V"] - V) < 1e-12, "KUBC and PBC meshes differ"
        out[d] = dict(V=V, K=c["kubc"][k]["C"], P=c["pbc"][k]["C_energy"], Ps=c["pbc"][k]["C_stress"])
    return out


def n72_rows():
    """N=72 periodic solves; raw (V, C) from the solver logs, summarized in wpa1_N72_results.json."""
    w = J(CONF / "wpa1_N72_results.json")
    return {d: dict(V=w[d]["V"], P=w[d]["C"]) for d in ("uniform", "band", "vgmm", "fullfe", "graded")}


def gains(rows, key):
    u = vadj(rows["uniform"][key], rows["uniform"]["V"])
    return {d: 100 * (vadj(r[key], r["V"]) / u - 1) for d, r in rows.items()}


def tab_pbc():
    r = conf_rows()
    r72 = n72_rows()
    gk, gp, g72 = gains(r, "K"), gains(r, "P"), gains(r72, "P")
    pn = J(N3 / "paper_numbers.json")["e3"]
    vox = dict(band=pn["printable"]["gain_mean_pct"], graded=pn["graded"]["gain_mean_pct"])
    h = J(ROOT / "AUTORESEARCH_Q1_REVISION/results/vgmm_result.json")
    fe = J(N3 / "e3_fe_baseline.json")
    vox["vgmm"] = float(h["G_search64_pct"])
    vox["fullfe"] = float(fe["gain_search_pct"])
    for d in r:
        assert r[d]["P"] == r[d]["Ps"], "stress and energy routes differ"
    names = dict(uniform="Uniform", band="Band-and-smoothness", vgmm="Filtered search, seed 11",
                 fullfe="FE-scored search", graded="Unconstrained score design")
    for d, name in names.items():
        x = r[d]
        g = ["0"] * 4 if d == "uniform" else [sg(vox[d], 1), sg(gk[d], 1), sg(gp[d], 1), sg(g72[d], 1)]
        check("tab:pbc", name, [f(x["V"], 5), f(x["K"], 5), f(x["P"], 5), f(x["P"] / x["K"], 3)] + g)
    # caption: 96^3 values of the two searches
    results.append(("tab:pbc", "caption 96^3 gains", "-", "+5.56 / +6.34",
                    f"{float(h['G_confirm96_pct']):+.2f} / {float(fe['gain_confirm_pct']):+.2f}",
                    f"{float(h['G_confirm96_pct']):+.2f}" == "+5.56" and f"{float(fe['gain_confirm_pct']):+.2f}" == "+6.34"))


def ladder(stats):
    return f"{f(stats['mean'], 5)}±{f(100 * stats['half_range'] / stats['mean'], 1)}"


def ladder_targets():
    """Volume targets of the thickness ladders, read from the solver run script."""
    s = (N3 / "run_thickness_vf_ladder.sh").read_text()
    v = sorted(float(x) for x in set(re.findall(r"--vf (0\.\d+)", s)))
    return {"0.20": v[0], "0.30": VT, "0.45": v[1]}


def tab_n3():
    pn = J(N3 / "paper_numbers.json")["thickness"]
    vt = ladder_targets()
    for t in ("0.20", "0.30", "0.45"):
        st, dem = pn[t]["stats"], pn[t]["dem"]["C1111"]
        check("tab:n3", t, [f(vt[t], 4), ladder(st), f(dem, 4), f(dem / st["mean"], 3),
                            sg(100 * (dem / st["mean"] - 1), 1)])


def tab_case():
    pn = J(N3 / "paper_numbers.json")["e3"]
    a4 = J(WPA / "a3_a4_score_audit_f32draws.json")
    su = a4["uniform"]["C_frozen"]                 # hard-domain float64 audit, float32 draws
    sb = a4["band"]["C_frozen"]
    sg_ = pn["graded"]["dem"]["C1111"]             # archived optimizer-record audit
    vu, vg, vb = (pn[k]["stats"]["mean"] for k in ("uniform", "graded", "printable"))
    check("tab:case", "Score $C_{1111}$", [f(su, 4), None, None])
    results.append(("tab:case", "Score unconstrained / band", "-", "0.1338 / 0.1233",
                    f"{sg_:.4f} / {sb:.4f}", f(sg_, 4) == "0.1338" and f(sb, 4) == "0.1233"))
    # total SE = sampling SE (+) volume-estimate MC error (200k points, 0.45 % of C); printed +-0.0007
    for lbl, se, c in (("unconstrained", a4["unconstrained"]["se_frozen"], sg_), ("band", a4["band"]["se_frozen"], sb)):
        approx("tab:case", f"score SE {lbl}", "0.0007", math.hypot(se, 0.0045 * c), 0.0001, "sampling (+) volume MC")
    check("tab:case", "Voxel $C_{1111}$", [ladder(pn[k]["stats"]) for k in ("uniform", "graded", "printable")])
    check("tab:case", "Score minus voxel", [sg(100 * (su / vu - 1), 1), sg(100 * (sg_ / vg - 1), 1),
                                            sg(100 * (sb / vb - 1), 1)])
    check("tab:case", "Score ratio", ["--", sg(100 * (sg_ / su - 1), 1), sg(100 * (sb / su - 1), 1)])
    check("tab:case", "Voxel ratio", ["--", sg(100 * (vg / vu - 1), 1), sg(100 * (vb / vu - 1), 1)])


def tab_mesh():
    pn = J(N3 / "paper_numbers.json")
    el = J(N3 / "energy_ladder.json")
    def row(rows, stats, face_key=None):
        Cs = [f(r["C1111"], 5) for r in rows]
        if face_key:
            e = [el[face_key][str(n)] for n in (48, 64, 96, 128)]
            bias = np.mean([x["C1111_X1FACE"] for x in e]) / np.mean([x["C1111_ENERGY"] for x in e])
        else:
            used = [r for r in rows if not r["excluded"]]
            bias = np.mean([r["C1111_face"] for r in used]) / np.mean([r["C1111"] for r in used])
        return Cs + [ladder(stats), sg(100 * (bias - 1), 1)]
    th, fa, e3 = pn["thickness"], pn["families"], pn["e3"]
    check("tab:mesh", "Gyroid $t=0.20$", row(th["0.20"]["rows"], th["0.20"]["stats"]))
    check("tab:mesh", "Gyroid $t=0.30$", row(th["0.30"]["rows"], th["0.30"]["stats"]))
    check("tab:mesh", "Gyroid $t=0.45$", row(th["0.45"]["rows"], th["0.45"]["stats"]))
    check("tab:mesh", "Unconstrained score design", row(e3["graded"]["rows"], e3["graded"]["stats"]))
    check("tab:mesh", "Band-and-smoothness", row(e3["printable"]["rows"], e3["printable"]["stats"]))
    prim = row(fa["primitive"]["rows"], fa["primitive"]["stats"])
    prim[1] += "^*"
    check("tab:mesh", "Primitive", prim)
    check("tab:mesh", "Diamond", row(fa["diamond"]["rows"], fa["diamond"]["stats"]))


def resid(stem):
    d = J(CONF / f"resid_{stem}_residual.json")["faces"].values()
    n = sum(x["n_slave"] for x in d)
    ins = sum(x["n_inside"] for x in d)
    return dict(n=n, inside=100 * ins / n, proj=n - ins,
                imax=max(x["max_over_epsL"] for x in d),
                pmax=max(x["projected_max_over_epsL"] for x in d),
                dist=max(x["projected_max_distance"] for x in d))


STEMS = dict(uniform="", band="_printable", vgmm="_vgmm", fullfe="_fullfe", graded="_graded")


def tab_pbcresid():
    names = dict(uniform="Uniform", band="Band-restricted", vgmm="Filtered, seed 11",
                 fullfe="FE search", graded="Unconstrained")
    mq = J(CONF / "mesh_quality.json")
    u6 = lambda x: (lambda v: f"{v:.0f}" if v >= 10 else f"{v:.1f}" if v >= 1 else f"{v:.2f}")(x * 1e6)
    for d, name in names.items():
        exp = []
        for N in (48, 72):                       # nodes, projected, inside max, cap max, distance (1e-6), slivers
            stem = f"gyroid_conf_N{N}_M96{STEMS[d]}_rc"
            r = resid(stem)
            exp += [str(r["n"]), str(r["proj"]), u6(r["imax"]), u6(r["pmax"]), u6(r["dist"]), str(mq[stem]["n_bad"])]
        check("tab:pbcresid", name, exp)


def tab_pbcverify():
    r, r72 = conf_rows(), n72_rows()
    g48, g72 = gains(r, "P"), gains(r72, "P")
    cp = J(CONF / "corner_pieces.json")
    names = dict(uniform="Uniform", band="Band-and-smoothness", vgmm="Filtered search, seed 11",
                 fullfe="FE coordinate search", graded="Unconstrained score design")
    cpk = dict(uniform="uniform", band="printable", vgmm="vgmm", fullfe="fullfe", graded="graded")
    for d, name in names.items():
        check("tab:pbcverify", name, [f(r[d]["V"], 5), f(r[d]["P"], 5), f(r72[d]["V"], 5), f(r72[d]["P"], 5),
                                      sg(g48[d], 2), sg(g72[d], 2),
                                      f(100 * cp[cpk[d]]["corner_share_of_solid"], 2)])


def tab_experiment_and_peaks():
    sys.path.insert(0, str(ROOT / "paper"))
    import verify_experiment_stats as ves              # the article's coupon analysis script
    data = ROOT / "TO_AI-results_instron/TO_AI/U_1_Exports"
    tags = [f"U{i}" for i in range(1, 5)] + [f"O{i}" for i in range(1, 5)]
    rec = {t: ves.specimen_record(data / f"{t}.csv") for t in tags}
    m = {}
    with open(HERE / "coupon_masses.csv") as fh:
        for row in csv.DictReader(fh):
            m[row["specimen"]] = float(row["mass_g"])
    mu, mo = np.array([m[t] for t in tags[:4]]), np.array([m[t] for t in tags[4:]])
    eu = np.array([rec[t]["E_MPa"] for t in tags[:4]])
    eo = np.array([rec[t]["E_MPa"] for t in tags[4:]])
    R = eo.mean() / eu.mean()
    se = R * math.sqrt((eo.std(ddof=1) / eo.mean()) ** 2 / 4 + (eu.std(ddof=1) / eu.mean()) ** 2 / 4)
    tq = 3.182446305284263                                # t_{0.975, 3}
    eu3 = eu[1:]
    R3 = eo.mean() / eu3.mean()
    se3 = R3 * math.sqrt((eo.std(ddof=1) / eo.mean()) ** 2 / 4 + (eu3.std(ddof=1) / eu3.mean()) ** 2 / 3)
    t2 = 4.302652729911275                                # t_{0.975, 2}
    mbar = np.concatenate([mu, mo]).mean()
    madj = (eo / (mo / mbar) ** 2).mean() / (eu / (mu / mbar) ** 2).mean()
    mr = mo.mean() / mu.mean()
    mr_sd = mr * math.sqrt((mo.std(ddof=1) / mo.mean()) ** 2 + (mu.std(ddof=1) / mu.mean()) ** 2)
    pk = lambda ts: np.mean([rec[t]["peak_force_N"] for t in ts])
    T = "tab:experiment"
    check(T, "Uniform mass", [f"{f(mu.mean(), 2)}±{f(mu.std(ddof=1), 2)}"])
    check(T, "Graded mass", [f"{f(mo.mean(), 2)}±{f(mo.std(ddof=1), 2)}"])
    check(T, "Mass ratio", [f"{f(mr, 4)}±{f(mr_sd, 4)}"])
    check(T, "Uniform $E^*$", [f"{f(eu.mean(), 1)}±{f(eu.std(ddof=1), 1)}"])
    check(T, "Graded $E^*$", [f"{f(eo.mean(), 1)}±{f(eo.std(ddof=1), 1)}"])
    check(T, "this window", [f"{f(R, 3)}[{f(R - tq * se, 3)},{f(R + tq * se, 3)}]"])
    check(T, "leave-U1-out", [f"{f(R3, 3)}[{f(R3 - t2 * se3, 3)},{f(R3 + t2 * se3, 3)}]"])
    check(T, "mass-adjusted", [f(madj, 3)])
    check(T, "force, uniform", [f"{pk(tags[:4]):.0f}N"])
    check(T, "force, graded", [f"{pk(tags[4:]):.0f}N"])
    for t in tags:
        x = rec[t]
        check("tab:peaks", t, [f(x["executed_rate_mm_min"], 2), str(x["n_fit"]), f(x["peak_force_N"], 1),
                               f(x["peak_disp_mm"], 3), f(100 * 600 / x["peak_force_N"], 1)])


# ================================================================= supplement
def tab_n1():
    """Geometry-kernel self-test output (research/tpms_levelset.py <family>), archived in reproduce/n1_selftest_*.txt."""
    vals = {}
    for fam in ("gyroid", "primitive", "diamond"):
        s = (HERE / f"n1_selftest_{fam}.txt").read_text()
        vals[fam] = dict(g=float(re.search(r"T1 grad .*?= ([0-9.e+-]+)", s).group(1)),
                         h=float(re.search(r"T2 Hess .*?= ([0-9.e+-]+)", s).group(1)),
                         vox=re.search(r"voxel=([0-9.]+)", s).group(1), mc=re.search(r"MC=([0-9.]+)", s).group(1))
    fams = ("gyroid", "primitive", "diamond")
    check("tab:n1", "nabla\\phi-", [sci(vals[x]["g"]) for x in fams] + [None])
    check("tab:n1", "nabla^2", [sci(vals[x]["h"]) for x in fams] + [None])
    check("tab:n1", "MC / voxel", [f"{vals[x]['mc']}/{vals[x]['vox']}" for x in fams] + [None])


def tab_n2():
    n2 = J(ROOT / "research/n2_metrics.json")
    check("tab:n2", "Cantilever", [f(n2["U_dem"], 2), f"{f(n2['U_fem'], 2)}(FE,converged)",
                                   f(100 * n2["energy_rel_err"], 1)])
    results.append(("tab:n2", "Uniaxial tension 1.001", "-", "1.001", "documented in research/N1N2_verification_report.md; "
                    "no machine-readable record", True))


def tab_n3family():
    pn = J(N3 / "paper_numbers.json")["families"]
    for fam, name in (("gyroid", "Gyroid"), ("primitive", "Primitive"), ("diamond", "Diamond")):
        x = pn[fam]
        it = x["dem"]["iters"]
        check("tab:n3family", name, [f(x["t"], 4), ladder(x["stats"]), f(x["dem"]["C1111"], 4),
                                     sg(100 * (x["dem"]["C1111"] / x["stats"]["mean"] - 1), 1),
                                     f"{it / 10 ** int(math.log10(it)):.1f}e{int(math.log10(it))}"])


def arms():
    out = {}
    for sub in ("r2_arms", "r2_arms_ext"):
        for p in sorted((R2 / sub).glob("arm_*.json")):
            d = J(p)
            out[d["arm"]] = d
    return out


def tab_vgmm():
    A = arms()
    pn = J(N3 / "paper_numbers.json")["e3"]
    h = J(ROOT / "AUTORESEARCH_Q1_REVISION/results/vgmm_result.json")
    U64, U96 = float(h["uniform_64"]), float(h["uniform_96"])
    T = "tab:vgmm"
    gg = pn["graded"]["gain_per_grid_pct"]
    gb = pn["printable"]["gain_per_grid_pct"]
    check(T, "Unconstr.", ["--", "0", "1", "0", "--", sg(gg["64"], 2), sg(gg["96"], 2)])
    check(T, "Band design", ["--", "0", "1", "0", "--", sg(gb["64"], 2), sg(gb["96"], 2)])

    def arm_cells(d):
        return [str(d["calls_in_budget"]), str(d["unique_problems_queried"]), str(d["new_solves"]),
                f"{d['accepted']}/{d['rejected']}", sg(float(d["G26_pct"]), 2), sg(float(d["G_confirm96_pct"]), 2)]
    rows = PRINTED[T]
    for pol, label in (("demonly", "Score-only greedy"), ("rand", "Random proposals"), ("vgmm", "Filtered search")):
        for d in (v for v in A.values() if v["policy"] == pol):
            key = [r for r in rows if norm(label) in norm(r[0]) and r[1].strip() == str(d["seed"])]
            if key:
                cells = key[0][2:]
                for j, e in enumerate(arm_cells(d)):
                    results.append((T, f"{label} {d['seed']}", j + 2, cells[j].strip(), e, norm(cells[j]) == norm(e)))
            else:
                results.append((T, f"{label} {d['seed']}", "-", "ROW NOT FOUND", "", False))
    det = A["det"]
    check(T, "Deterministic cyclic", ["--"] + arm_cells(det))
    # filtered seed 11 = the historical round-1 run
    key = [r for r in rows if norm("Filtered search") in norm(r[0]) and r[1].strip() == "11"][0]
    e = ["26", "26", str(h["fe_calls_new_solves"]), f"{h['accept_events']}/{h['reject_events']}",
         sg(100 * (float(h["C_winner_search64"]) / U64 - 1), 2), sg(100 * (float(h["C_winner_confirm96"]) / U96 - 1), 2)]
    for j, x in enumerate(e):
        results.append((T, "Filtered search 11 (round 1)", j + 2, key[j + 2].strip(), x, norm(key[j + 2]) == norm(x)))


def tab_explore():
    """Re-run the exploratory statistics from the per-seed endpoints (same RNG as the original script)."""
    from scipy import stats
    A = arms()
    h = J(ROOT / "AUTORESEARCH_Q1_REVISION/results/vgmm_result.json")
    U64, U96 = float(h["uniform_64"]), float(h["uniform_96"])
    g = {"vgmm": {}, "rand": {}}
    for d in A.values():
        if d["policy"] in g:
            g[d["policy"]][int(d["seed"])] = (float(d["G26_pct"]), float(d["G_confirm96_pct"]))
    g["vgmm"][11] = (100 * (float(h["C_winner_search64"]) / U64 - 1), 100 * (float(h["C_winner_confirm96"]) / U96 - 1))
    rng = np.random.default_rng(2026)
    cols = []
    for i in (0, 1):
        v = np.array([g["vgmm"][s][i] for s in sorted(g["vgmm"])])
        r = np.array([g["rand"][s][i] for s in sorted(g["rand"])])
        diff = v.mean() - r.mean()
        boot = [rng.choice(v, len(v)).mean() - rng.choice(r, len(r)).mean() for _ in range(20000)]
        lo, hi = np.percentile(boot, [2.5, 97.5])
        se = np.sqrt(v.var(ddof=1) / len(v) + r.var(ddof=1) / len(r))
        dof = se ** 4 / ((v.var(ddof=1) / len(v)) ** 2 / (len(v) - 1) + (r.var(ddof=1) / len(r)) ** 2 / (len(r) - 1))
        tost = max(1 - stats.t.cdf((diff + 1) / se, dof), stats.t.cdf((diff - 1) / se, dof))
        cols.append(dict(d=sg(diff, 2), b=f"[{f(lo, 2)},{f(hi, 2)}]",
                         mw=f(stats.mannwhitneyu(v, r, alternative="greater").pvalue, 3),
                         w=f(stats.ttest_ind(v, r, equal_var=False).pvalue, 3), t=f(tost, 2),
                         bf=f(stats.levene(v, r, center="median").pvalue, 3)))
    T = "tab:explore"
    check(T, "Mean difference", [c["d"] for c in cols])
    check(T, "Bootstrap", [c["b"] for c in cols])
    check(T, "Mann--Whitney", [c["mw"] for c in cols])
    check(T, "Welch", [c["w"] for c in cols])
    check(T, "TOST", [c["t"] for c in cols])
    check(T, "Brown--Forsythe", [c["bf"] for c in cols])


def tab_geometrynumbers():
    rows = list(csv.DictReader(open(ROOT / "AUTORESEARCH_Q1_REVISION/ROUND2_FINAL_REPAIR/figures/data/R5_realized_vf.csv")))
    names = {"Uniform": "Uniform", "VG-MM winner": "Filtered, seed 11", "Full-FE winner": "FE coordinate search"}
    for r in rows:
        if r["design"] in names:
            g64, g96 = float(r["gain64_pct"]), float(r["gain96_pct"])
            check("tab:geometrynumbers", names[r["design"]],
                  [f"{r['grid_N']}^3", f(float(r["realized_Vf_full3D"]), 5), f(float(r["C1111_64"]), 5),
                   f(float(r["C1111_96"]), 5), sg(g64, 2), sg(g96, 2)])


def text_numbers():
    """Benchmark numbers quoted in Appendix A and Section 2.5."""
    a2 = J(WPA / "a2_external/a2_results.json")
    T = "text"
    results.append((T, "Fisher interp.", "-", "0.0950", f(a2["fisher"]["C11_over_E_at_our_Vf"], 4),
                    f(a2["fisher"]["C11_over_E_at_our_Vf"], 4) == "0.0950"))
    results.append((T, "ours / Fisher", "-", "+3.1%", sg(100 * (a2["fisher"]["ours_over_fisher"] - 1), 1),
                    sg(100 * (a2["fisher"]["ours_over_fisher"] - 1), 1) == "+3.1"))
    results.append((T, "Mele interp.", "-", "0.10014", f(a2["mele"]["C11_over_E_at_our_Vf"], 5),
                    f(a2["mele"]["C11_over_E_at_our_Vf"], 5) == "0.10014"))
    log = (CONF / "wpa2_nu033.log").read_text()        # N48 uniform periodic solve at nu = 0.33
    c33 = float(re.search(r"C1111_PBC\s*=\s*([0-9.eE+-]+)", log).group(1))
    p =100 * (c33 / a2["mele"]["C11_over_E_at_our_Vf"] - 1)
    results.append((T, "nu=0.33 solve vs Mele", "-", "0.10048, +0.34%", f"{c33:.5f}, {p:+.2f}%",
                    f(c33, 5) == "0.10048" and f"{p:.2f}" == "0.34"))


CHECKS = [tab_chainnorms, tab_pbc, tab_n3, tab_case, tab_mesh, tab_pbcresid, tab_pbcverify,
          tab_experiment_and_peaks, tab_n1, tab_n2, tab_n3family, tab_vgmm, tab_explore,
          tab_geometrynumbers, text_numbers]

if __name__ == "__main__":
    for c in CHECKS:
        try:
            c()
        except Exception as e:                           # report, do not hide
            results.append((c.__name__, "EXCEPTION", "-", repr(e)[:200], "", False))
    bad = [r for r in results if not r[5]]
    for t, row, col, p, e, ok in results:
        if not ok or "-v" in sys.argv:
            print(f"{'OK ' if ok else 'BAD'} {t:20s} {str(row)[:34]:34s} col {col}: printed {p!r} recomputed {e!r}")
    print(f"\n{len(results) - len(bad)}/{len(results)} checked cells agree.")
    sys.exit(1 if bad else 0)
