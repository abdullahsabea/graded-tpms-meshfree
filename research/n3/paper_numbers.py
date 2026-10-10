"""Single source of truth for every FE/DEM number quoted in the manuscript.

FE references are evaluated on volume-calibrated voxel meshes (threshold or
graded offset re-solved per resolution so the discrete solid fraction equals
the continuum target) and, decisively, on the HILL-MANDEL ENERGY BASIS:

    C1111 = 2 U / (V eps^2) = <sigma_11> / eps ,

which agree to machine precision (verified against POST_ELEM/INTEGRALE and,
on a homogeneous cube, against lambda+2mu exactly). The summed reaction on the
loaded face alone is NOT the apparent modulus of a heterogeneous cell: the
lateral faces of the KUBC cell carry a shear-traction moment that the
loaded-face sum omits, biasing it by +4.7% (uniform gyroid) to -11.3%
(primitive). Both are recorded; every reference below uses the energy value.
This is also the like-for-like comparison: the mesh-free DEM computes the same
functional 2U/(V eps^2).

Writes research/n3/paper_numbers.json
"""
import glob
import json
import os
import re

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(HERE, *a)
NS = (48, 64, 96, 128)
VF_TARGET = 0.19328


def read_mess(tag):
    """C1111_X1FACE / C1111_ENERGY from an oute_<tag>.mess file."""
    path = P(f"oute_{tag}.mess")
    if not os.path.exists(path):
        return None
    d = {}
    for line in open(path, errors="ignore"):
        for k in ("C1111_X1FACE", "C1111_ENERGY"):
            if line.startswith(k):
                d[k] = float(line.split("=")[1])
    return d if "C1111_ENERGY" in d else None


def ladder(case, skip=()):
    rows = []
    for N in NS:
        d = read_mess(f"{case}_N{N}")
        if d is None:
            continue
        rows.append({"N": N, "C1111": d["C1111_ENERGY"],
                     "C1111_face": d.get("C1111_X1FACE"),
                     "excluded": N in skip})
    used = [r["C1111"] for r in rows if not r["excluded"]]
    stat = {}
    if used:
        stat = {"mean": float(np.mean(used)), "min": min(used), "max": max(used)}
        stat["half_range"] = 0.5 * (stat["max"] - stat["min"])
        stat["scatter_pct"] = 100 * stat["half_range"] / stat["mean"]
    return {"rows": rows, "stats": stat}


# ---- converged mesh-free DEM audits (all are 2U/(V eps^2), float64) ---------
# single-thickness models, standard recipe (6000 collocation pts/iter)
DEM_STD = {"uniform": (0.1127, 20000), "primitive": (0.1048, 42000),
           "diamond": (0.1159, 42000)}
DEM_T = {"0.20": 0.0705, "0.30": 0.1127, "0.45": 0.1856}
# design-point audits of the optimization case study
DEM_E3 = {"uniform": 0.1139,            # hard-domain audit of the baseline
          "graded": 0.1338,             # hard-domain audit of the optimum
          "printable": 0.1238}          # conditional-model prediction
# control experiment: plateaued primitive resumed with 20k pts/iter
PRIMITIVE_NMC_CONTROL = {"n_mc": 20000, "extra_iters": 12000, "C1111": 0.1045}

FAM_CASE = {"gyroid": "uniform", "primitive": "primitive", "diamond": "diamond"}
FAM_T = {"gyroid": 0.3, "primitive": 0.3387, "diamond": 0.236}
SKIP = {"primitive": (64,)}   # 64^3 discrete Vf could not be matched (degenerate level set)


def main():
    out = {"vf_target": VF_TARGET, "basis": "hill-mandel-energy",
           "families": {}, "thickness": {}, "e3": {},
           "primitive_nmc_control": PRIMITIVE_NMC_CONTROL}

    for fam, case in FAM_CASE.items():
        lad = ladder(case, SKIP.get(fam, ()))
        c, it = DEM_STD[case] if case in DEM_STD else (None, None)
        lad["t"] = FAM_T[fam]
        lad["dem"] = {"C1111": c, "se": 0.0002, "iters": it}
        if lad["stats"]:
            lad["dem"]["dev_pct_vs_mean"] = 100 * (c / lad["stats"]["mean"] - 1)
            # face-basis bias of the old evaluation, for the record
            fv = [r["C1111_face"] for r in lad["rows"] if not r["excluded"]]
            lad["face_over_energy"] = float(np.mean(fv) / lad["stats"]["mean"])
        out["families"][fam] = lad

    for tag, key in (("t020", "0.20"), ("uniform", "0.30"), ("t045", "0.45")):
        lad = ladder(tag)
        lad["dem"] = {"C1111": DEM_T[key]}
        if lad["stats"]:
            lad["dem"]["dev_pct_vs_mean"] = 100 * (DEM_T[key] / lad["stats"]["mean"] - 1)
        out["thickness"][key] = lad

    for tag in ("uniform", "graded", "printable"):
        lad = ladder(tag)
        lad["dem"] = {"C1111": DEM_E3[tag]}
        if lad["stats"]:
            lad["dem"]["dev_pct_vs_mean"] = 100 * (DEM_E3[tag] / lad["stats"]["mean"] - 1)
        out["e3"][tag] = lad
    base = out["e3"]["uniform"]
    for tag in ("graded", "printable"):
        d = out["e3"][tag]
        per = {r["N"]: 100 * (r["C1111"] / b["C1111"] - 1)
               for r in d["rows"]
               for b in base["rows"] if b["N"] == r["N"]}
        d["gain_per_grid_pct"] = per
        d["gain_mean_pct"] = 100 * (d["stats"]["mean"] / base["stats"]["mean"] - 1)
        d["gain_min_pct"], d["gain_max_pct"] = min(per.values()), max(per.values())
        d["dem_gain_pct"] = 100 * (DEM_E3[tag] / DEM_E3["uniform"] - 1)

    json.dump(out, open(P("paper_numbers.json"), "w"), indent=2)

    print("== N3 thickness anchors, gyroid (energy basis) ==")
    for k, d in out["thickness"].items():
        s = d["stats"]
        if s:
            print(f"t={k}: FE {s['mean']:.5f} ±{s['scatter_pct']:.2f}%  "
                  f"DEM {d['dem']['C1111']:.4f} -> {d['dem']['dev_pct_vs_mean']:+.1f}%")
    print("\n== cross-family (energy basis) ==")
    for fam, d in out["families"].items():
        s = d["stats"]
        print(f"{fam:10s} FE {s['mean']:.5f} ±{s['scatter_pct']:.2f}%  "
              f"DEM {d['dem']['C1111']:.4f} -> {d['dem']['dev_pct_vs_mean']:+.1f}%  "
              f"[face/energy {d['face_over_energy']:.3f}]")
    print("\n== E3 (energy basis) ==")
    for tag, d in out["e3"].items():
        s = d["stats"]
        line = (f"{tag:10s} FE {s['mean']:.5f} ±{s['scatter_pct']:.2f}%  "
                f"DEM {d['dem']['C1111']:.4f} ({d['dem']['dev_pct_vs_mean']:+.1f}%)")
        if "gain_mean_pct" in d:
            line += (f"  gain {d['gain_mean_pct']:+.2f}% "
                     f"[{d['gain_min_pct']:+.2f}..{d['gain_max_pct']:+.2f}]"
                     f"  (DEM claimed {d['dem_gain_pct']:+.1f}%)")
        print(line)
    print("\nwrote", P("paper_numbers.json"))


if __name__ == "__main__":
    main()
