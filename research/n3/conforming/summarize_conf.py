"""Body-fitted (TetGen, TETRA10) KUBC and PBC results, volume-corrected to V_f = 0.19328.

C(V_T) = C (V_T / V)^a with a = d ln C / d ln V_f = 1.21 (Table 3 anchors).
Writes conf_summary.json.
"""
import glob
import json
import re

VT, A = 0.19328, 1.21
d, p = {}, {}
for f in glob.glob("log_conf_*.txt"):
    t = open(f, encoding="utf-8", errors="replace").read()
    v = re.search(r"^SOLID_VOLUME = (\S+)", t, re.M)
    c = re.search(r"^C1111_ENERGY = (\S+)", t, re.M)
    if v and c:
        d[f[9:-4]] = (float(v.group(1)), float(c.group(1)))
for f in glob.glob("log_pbc_gyroid_conf_*.txt"):
    t = open(f, encoding="utf-8", errors="replace").read()
    mess = "out_pbc_" + f[len("log_pbc_"):-4] + ".mess"
    try:  # the .mess file survives a wrapper timeout that truncates the log
        t += open(mess, encoding="utf-8", errors="replace").read()
    except OSError:
        pass
    v = re.search(r"^SOLID_VOLUME\s*=\s*(\S+)", t, re.M)
    cs = re.search(r"^C1111_PBC\s+=\s*(\S+)", t, re.M)
    ce = re.search(r"^C1111_PBC_EN\s*=\s*(\S+)", t, re.M)
    if v and (cs or ce):
        p[f[len("log_pbc_gyroid_conf_"):-4]] = (float(v.group(1)),
                                                 float(cs.group(1)) if cs else None,
                                                 float(ce.group(1)) if ce else None)


def cor(v, c):
    return c * (VT / v) ** A


out = {"kubc": {}, "kubc_gain_pct": {}, "pbc": {}, "pbc_gain_pct": {}}
for k in sorted(d):
    v, c = d[k]
    out["kubc"][k] = dict(V=v, C=c, C_at_VT=cor(v, c))
    print(f"KUBC {k:24s} V={v:.5f} C={c:.6f} C@VT={cor(v, c):.6f}")
for N in ("N48", "N60", "N72"):
    u = f"{N}_M96"
    for s in ("graded", "printable"):
        k = f"{N}_M96_{s}"
        if k in d and u in d:
            g = 100 * (cor(*d[k]) / cor(*d[u]) - 1)
            out["kubc_gain_pct"][k] = g
            print(f"  KUBC gain {k}: {g:+.2f}%")
if "N66_M96_printable" in d:
    um = (cor(*d["N60_M96"]) + cor(*d["N72_M96"])) / 2
    g = 100 * (cor(*d["N66_M96_printable"]) / um - 1)
    out["kubc_gain_pct"]["N66_M96_printable_vs_meanN60N72"] = g
    print(f"  KUBC gain N66 printable vs mean(N60,N72) uniform: {g:+.2f}%")
for s in ("graded", "printable", "vgmm", "fullfe"):  # cap-refined meshes (refine_caps), used for the PBC check
    k, u = f"N48_M96_{s}_rc", "N48_M96_rc"
    if k in d and u in d:
        g = 100 * (cor(*d[k]) / cor(*d[u]) - 1)
        out["kubc_gain_pct"][k] = g
        print(f"  KUBC gain {k}: {g:+.2f}%")
for k in sorted(p):
    v, cs, ce = p[k]
    out["pbc"][k] = dict(V=v, C_stress=cs, C_energy=ce, C_at_VT=cor(v, cs or ce))
    print(f"PBC  {k:24s} V={v:.5f} C_stress={cs} C_energy={ce}")
    if k in d:
        print(f"     PBC/KUBC (same mesh) = {(cs or ce) / d[k][1]:.4f}")
u = "N48_M96_rc"
for s in ("graded", "printable", "vgmm", "fullfe"):
    k = f"N48_M96_{s}_rc"
    if k in p and u in p:
        g = 100 * (cor(p[k][0], p[k][1]) / cor(p[u][0], p[u][1]) - 1)
        out["pbc_gain_pct"][k] = g
        print(f"  PBC gain {k}: {g:+.2f}%")
json.dump(out, open("conf_summary.json", "w"), indent=1)
