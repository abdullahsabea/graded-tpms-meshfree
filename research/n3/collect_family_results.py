"""Collect the N3 cross-family gate into one JSON:
   FE C1111 per (family, resolution) with the discrete voxel volume fraction,
   plus the mesh-free DEM audit for each family.

Writes research/n3/n3_family_summary.json
"""
import json, glob, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
FAMILIES = {"gyroid": 0.3, "primitive": 0.3387, "diamond": 0.236}
VF_TARGET = 0.19328          # continuum volume fraction, matched across families


def mesh_vf(family, t, N, calibrated=False):
    path = os.path.join(HERE, (f"{family}_N{N}_vf{VF_TARGET}.mail" if calibrated
                               else f"{family}_N{N}_t{t}.mail"))
    if not os.path.exists(path):
        return None
    with open(path) as f:
        head = f.readline()
    m = re.search(r"VF=([0-9.]+)", head)
    return float(m.group(1)) if m else None


def fe_values(family, calibrated=False):
    if calibrated:                      # volume-calibrated ladder (outvf_*)
        paths = glob.glob(os.path.join(HERE, f"outvf_{family}_N*.mess"))
    else:
        # gyroid t=0.3 was run before the family suffix existed: out_N48/N64.mess
        paths = glob.glob(os.path.join(HERE, f"out_{family}_N*.mess"))
        if family == "gyroid":
            paths += glob.glob(os.path.join(HERE, "out_N*.mess"))
    out = {}
    for path in paths:
        N = int(re.search(r"_N(\d+)\.mess$", path).group(1))
        with open(path, errors="ignore") as f:
            for line in f:
                if line.startswith("C1111_KUBC"):
                    out[N] = float(line.split("=")[1])
    return out


def main():
    summary = {"vf_target": VF_TARGET, "families": {}}
    for fam, t in FAMILIES.items():
        fe_fixed = fe_values(fam)
        fe_cal = fe_values(fam, calibrated=True)
        rows_fixed = [{"N": N, "C1111": fe_fixed[N], "vf_mesh": mesh_vf(fam, t, N)}
                      for N in sorted(fe_fixed)]
        rows = [{"N": N, "C1111": fe_cal[N],
                 "vf_mesh": mesh_vf(fam, t, N, calibrated=True)}
                for N in sorted(fe_cal)] or rows_fixed
        dem_path = os.path.join(HERE, f"n3_dem_metrics_{fam}.json")
        dem = json.load(open(dem_path)) if os.path.exists(dem_path) else None
        finest = rows[-1] if rows else None
        summary["families"][fam] = {
            "t": t,
            "fe": rows,                     # volume-calibrated ladder (reference)
            "fe_fixed_threshold": rows_fixed,
            "fe_reference": finest,
            "dem": (None if dem is None else
                    {"C1111": dem["C1111_dem"], "se": dem["C1111_se"],
                     "vf_continuum": dem["V_solid"], "iters": dem["iters_total"]}),
            "ratio": (None if (dem is None or finest is None) else
                      dem["C1111_dem"] / finest["C1111"]),
        }
    path = os.path.join(HERE, "n3_family_summary.json")
    json.dump(summary, open(path, "w"), indent=2)
    for fam, d in summary["families"].items():
        fe = "  ".join(f"N{r['N']}={r['C1111']:.5f}(vf {r['vf_mesh']:.4f})" for r in d["fe"])
        dem = "--" if d["dem"] is None else f"{d['dem']['C1111']:.4f}"
        rat = "--" if d["ratio"] is None else f"{d['ratio']:.4f}"
        print(f"{fam:10s} t={d['t']}  FE: {fe}\n{'':10s} DEM={dem}  DEM/FE={rat}")
    print("wrote", path)


if __name__ == "__main__":
    main()
