"""
N3a — TPMS unit-cell voxel mesh generator for code_aster (ASTER .mail format)
================================================================================
Voxel (HEXA8) mesh of a sheet-network TPMS solid at threshold t, unit cube.
Chosen deliberately: structured voxels give exact node sets on the six outer
faces (clean KUBC boundary imposition) and full reproducibility (no gmsh).
Staircase bias is quantified by mesh refinement (two resolutions).

Families: gyroid, primitive, diamond — the same basis functions F(kx) used by
the mesh-free kernel (research/tpms_levelset.py), restated in numpy so that
mesh generation carries no torch dependency.

Usage:  python make_mesh.py [t] [N1,N2,...] [family]
Output: {family}_N{N}_t{t}.mail with GROUP_NO X0,X1,Y0,Y1,Z0,Z1 + SOLID group_ma.
"""
import numpy as np
import sys, os

def tpms_F(name, x, y, z, k=2*np.pi):
    X, Y, Z = k*x, k*y, k*z
    if name == "gyroid":
        return np.sin(X)*np.cos(Y) + np.sin(Y)*np.cos(Z) + np.sin(Z)*np.cos(X)
    if name == "primitive":
        return np.cos(X) + np.cos(Y) + np.cos(Z)
    if name == "diamond":
        return (np.sin(X)*np.sin(Y)*np.sin(Z) + np.sin(X)*np.cos(Y)*np.cos(Z)
                + np.cos(X)*np.sin(Y)*np.cos(Z) + np.cos(X)*np.cos(Y)*np.sin(Z))
    raise ValueError(f"unknown TPMS '{name}'")

def gyroid_F(x, y, z, k=2*np.pi):   # backward-compatible alias
    return tpms_F("gyroid", x, y, z, k)

def build(N=48, t=0.3, family="gyroid"):
    h = 1.0 / N
    c = (np.arange(N) + 0.5) * h
    X, Y, Z = np.meshgrid(c, c, c, indexing="ij")
    solid = (np.abs(tpms_F(family, X, Y, Z)) - t) < 0.0
    ids = np.argwhere(solid)                      # element (i,j,k) list
    eid = {tuple(v): n + 1 for n, v in enumerate(ids)}

    # node map: only nodes touched by solid elements
    def node_key(i, j, k): return (i, j, k)
    nmap, nodes = {}, []
    elems = []
    for (i, j, k) in ids:
        corner = [(i, j, k), (i+1, j, k), (i+1, j+1, k), (i, j+1, k),
                  (i, j, k+1), (i+1, j, k+1), (i+1, j+1, k+1), (i, j+1, k+1)]
        row = []
        for key in corner:
            if key not in nmap:
                nmap[key] = len(nodes) + 1
                nodes.append((key[0]*h, key[1]*h, key[2]*h))
            row.append(nmap[key])
        elems.append((eid[tuple((i, j, k))], row))

    nodes = np.array(nodes)
    tol = 1e-9
    on_x0 = nodes[:, 0] < tol; on_x1 = nodes[:, 0] > 1 - tol
    on_y0 = nodes[:, 1] < tol; on_y1 = nodes[:, 1] > 1 - tol
    on_z0 = nodes[:, 2] < tol; on_z1 = nodes[:, 2] > 1 - tol
    bound = on_x0 | on_x1 | on_y0 | on_y1 | on_z0 | on_z1
    groups = {
        "X0": np.where(on_x0)[0] + 1,
        "X1": np.where(on_x1)[0] + 1,
        "Y0": np.where(on_y0)[0] + 1,
        "Y1": np.where(on_y1)[0] + 1,
        "Z0": np.where(on_z0)[0] + 1,
        "Z1": np.where(on_z1)[0] + 1,
        # disjoint boundary (single BC imposition: u = eps*X, v = w = 0 everywhere)
        "BOUND": np.where(bound)[0] + 1,
    }
    return nodes, elems, groups, solid.mean()

def write_mail(path, nodes, elems, groups, vf, N, t, family="gyroid"):
    def wrapped(f, name, items, prefix):
        line = "%s  " % name
        count = 0
        for q in items:
            line += "%s%d  " % (prefix, q)
            count += 1
            if count % 7 == 0:
                f.write(line.rstrip() + "\n")
                line = ""
        if line.strip():
            f.write(line.rstrip() + "\n")

    with open(path, "w") as f:
        f.write("%% %s sheet unit cell voxel mesh N=%d t=%.4f VF=%.4f\n" % (family, N, t, vf))
        f.write("TITRE\n%s N=%d T=%.4f\nFINSF\n\n" % (family.upper(), N, t))
        f.write("COOR_3D\n")
        for n, (x, y, z) in enumerate(nodes, 1):
            f.write("N%d  %.10e  %.10e  %.10e\n" % (n, x, y, z))
        f.write("FINSF\n\nHEXA8\n")
        for e, row in elems:
            f.write("M%d  %s\n" % (e, "  ".join("N%d" % q for q in row)))
        f.write("FINSF\n\n")
        for name, idx in groups.items():
            f.write("GROUP_NO\n")
            wrapped(f, name, idx, "N")
            f.write("FINSF\n\n")
        f.write("GROUP_MA\n")
        wrapped(f, "SOLID", [e for e, _ in elems], "M")
        f.write("FINSF\n\nFIN\n")
    print(f"wrote {path}: {len(nodes)} nodes, {len(elems)} HEXA8, VF={vf:.4f}")

def solve_t_for_vf(family, N, vf_target, tol=1e-5):
    """Threshold whose *discrete* (voxel-counted) volume fraction matches
    vf_target at resolution N. Removes the volume drift that otherwise
    contaminates a mesh-refinement sequence: with t held fixed, each
    refinement changes both the staircase boundary and the amount of solid,
    and the two effects are of the same order for walls a few voxels thick."""
    h = 1.0 / N
    c = (np.arange(N) + 0.5) * h
    X, Y, Z = np.meshgrid(c, c, c, indexing="ij")
    absF = np.abs(tpms_F(family, X, Y, Z))
    lo, hi = 0.0, float(absF.max())
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if (absF < mid).mean() < vf_target:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol * 1e-2:
            break
    t = 0.5 * (lo + hi)
    return t, float((absF < t).mean())


if __name__ == "__main__":
    os.makedirs("n3", exist_ok=True)
    if len(sys.argv) > 1 and sys.argv[1] == "--vf":
        # python make_mesh.py --vf <vf_target> <N1,N2,...> <family>
        vf_target = float(sys.argv[2])
        Ns = [int(x) for x in sys.argv[3].split(",")]
        family = sys.argv[4] if len(sys.argv) > 4 else "gyroid"
        for N in Ns:
            t, vf_disc = solve_t_for_vf(family, N, vf_target)
            nodes, elems, groups, vf = build(N=N, t=t, family=family)
            write_mail(f"{family}_N{N}_vf{vf_target}.mail", nodes, elems, groups,
                       vf, N, t, family)
            print(f"   calibrated t={t:.6f} -> discrete VF={vf:.6f} "
                  f"(target {vf_target})")
        sys.exit(0)
    t = float(sys.argv[1]) if len(sys.argv) > 1 else 0.3
    Ns = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [48, 64]
    family = sys.argv[3] if len(sys.argv) > 3 else "gyroid"
    for N in Ns:
        nodes, elems, groups, vf = build(N=N, t=t, family=family)
        write_mail(f"{family}_N{N}_t{t}.mail", nodes, elems, groups, vf, N, t, family)
