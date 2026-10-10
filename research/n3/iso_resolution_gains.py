"""Iso-resolution audit of the optimization case study.

The FE-confirmed stiffness gain must compare designs voxelized at the SAME
resolution: the uniform baseline and the optimized cells have different
staircase errors and different discrete volume fractions at coarse grids, so
mixing resolutions biases the reported gain.

Basis (2026-08 repair, defect D2): all PRIMARY numbers are read from the
`oute_*.mess` logs on the Hill--Mandel energy basis (`C1111_ENERGY` =
2U/(V eps^2)), which is the paper's canonical basis (paper_numbers.json,
basis "hill-mandel-energy").  The legacy `outvf_*.mess` / `out_*.mess` logs
print `C1111_KUBC`, a loaded-face reaction average that differs from the
energy basis by -11..+15% and inverts the sign of the graded gain; those
tables are kept below as explicitly-labelled LEGACY diagnostics only.
Expected energy-basis gains (paper_numbers.json): graded -4.37%,
printable +1.58%.

Writes research/n3/e3_iso_resolution.json
(the pre-repair face-basis JSON is preserved as
e3_iso_resolution_legacy_face_basis.json).
"""
import json, os, re, shutil

HERE = os.path.dirname(os.path.abspath(__file__))


def read_c1111(path, tag):
    if not os.path.exists(path):
        return None
    with open(path, errors="ignore") as f:
        for line in f:
            if line.startswith(tag):
                return float(line.split("=")[1])
    return None


def vf(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        m = re.search(r"VF=([0-9.]+)", f.readline())
    return float(m.group(1)) if m else None


P = lambda *a: os.path.join(HERE, *a)

VF = 0.19328
NS = (48, 64, 96, 128)

# PRIMARY: energy-basis logs (oute_*), volume-calibrated meshes -- the same
# runs paper_numbers.py reads.  richardson.py consumes cases_vf_calibrated.
CASES_ENERGY = {
    "uniform":   {N: (P(f"oute_uniform_N{N}.mess"), P(f"gyroid_N{N}_vf{VF}.mail"))
                  for N in NS},
    "graded":    {N: (P(f"oute_graded_N{N}.mess"), P(f"gyroid_graded_N{N}_vf{VF}.mail"))
                  for N in NS},
    "printable": {N: (P(f"oute_printable_N{N}.mess"), P(f"gyroid_printable_N{N}_vf{VF}.mail"))
                  for N in NS},
}

# LEGACY: loaded-face reaction basis (C1111_KUBC).  Same volume-calibrated
# meshes, older solver stage (homog.comm); kept for the record, NOT citable.
CASES_LEGACY_VF = {
    "uniform":   {N: (P(f"outvf_gyroid_N{N}.mess"), P(f"gyroid_N{N}_vf{VF}.mail"))
                  for N in NS},
    "graded":    {N: (P(f"outvf_graded_N{N}.mess"), P(f"gyroid_graded_N{N}_vf{VF}.mail"))
                  for N in NS},
    "printable": {N: (P(f"outvf_printable_N{N}.mess"), P(f"gyroid_printable_N{N}_vf{VF}.mail"))
                  for N in NS},
}


def table(grids_by_case, title, tag):
    data = {}
    for case, grids in grids_by_case.items():
        data[case] = {}
        for N, (mess, mail) in grids.items():
            c, v = read_c1111(mess, tag), vf(mail)
            if c is not None:
                data[case][N] = {"C1111": c, "vf_mesh": v}
    gains = {}
    print(f"\n## {title}")
    print(f"{'case':10s} {'N':>5s} {'C1111':>9s} {'vf_mesh':>8s}  gain vs uniform (same N)")
    for case in ("uniform", "graded", "printable"):
        for N in sorted(data.get(case, {})):
            row = data[case][N]
            base = data["uniform"].get(N)
            g = (row["C1111"] / base["C1111"] - 1) * 100 if (base and case != "uniform") else None
            if g is not None:
                gains.setdefault(case, {})[N] = g
            gs = "--" if g is None else f"{g:+.2f}%"
            vfs = "--" if row["vf_mesh"] is None else f"{row['vf_mesh']:8.4f}"
            print(f"{case:10s} {N:5d} {row['C1111']:9.5f} {vfs}  {gs}")
    return data, gains


def main():
    # preserve the pre-repair face-basis JSON once, for provenance
    legacy_json, live_json = P("e3_iso_resolution_legacy_face_basis.json"), P("e3_iso_resolution.json")
    if not os.path.exists(legacy_json) and os.path.exists(live_json):
        shutil.copyfile(live_json, legacy_json)
        print("preserved legacy face-basis JSON as", legacy_json)

    data_vf, gains_vf = table(CASES_ENERGY,
                              "energy basis (C1111_ENERGY, oute_* logs), volume-calibrated",
                              "C1111_ENERGY")
    data_legacy, gains_legacy = table(CASES_LEGACY_VF,
                                      "LEGACY loaded-face basis (C1111_KUBC, outvf_* logs)",
                                      "C1111_KUBC")
    out = {"basis": "hill-mandel-energy",
           "cases_vf_calibrated": data_vf, "gains_vf_calibrated": gains_vf,
           "legacy_face_basis_cases": data_legacy,
           "legacy_face_basis_gains": gains_legacy,
           "note": "cases_vf_calibrated/gains_vf_calibrated are energy-basis "
                   "(C1111_ENERGY from oute_* logs) since the 2026-08 repair (D2); "
                   "the legacy_* keys retain the loaded-face reaction basis for the "
                   "record and must not be cited."}

    path = P("e3_iso_resolution.json")
    json.dump(out, open(path, "w"), indent=2)
    print("wrote", path)


if __name__ == "__main__":
    main()
