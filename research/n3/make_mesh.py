"""
N3a — Gyroid unit-cell voxel mesh generator for code_aster (ASTER .mail format)
================================================================================
Voxel (HEXA8) mesh of the sheet-network gyroid solid at threshold t, unit cube.
Chosen deliberately: structured voxels give exact node sets on the six outer
faces (clean KUBC boundary imposition) and full reproducibility (no gmsh).
Staircase bias is quantified by mesh refinement (two resolutions).

Output: gyroid_N{N}_t{t}.mail with GROUP_NO X0,X1,Y0,Y1,Z0,Z1 + SOLID group_ma.
"""
import numpy as np
import sys, os

def gyroid_F(x, y, z, k=2*np.pi):
    X, Y, Z = k*x, k*y, k*z
    return np.sin(X)*np.cos(Y) + np.sin(Y)*np.cos(Z) + np.sin(Z)*np.cos(X)

def build(N=48, t=0.3):
    h = 1.0 / N
    c = (np.arange(N) + 0.5) * h
    X, Y, Z = np.meshgrid(c, c, c, indexing="ij")
    solid = (np.abs(gyroid_F(X, Y, Z)) - t) < 0.0
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

def write_mail(path, nodes, elems, groups, vf, N, t):
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
        f.write("%% gyroid sheet unit cell voxel mesh N=%d t=%.3f VF=%.4f\n" % (N, t, vf))
        f.write("TITRE\nGYROID N=%d T=%.3f\nFINSF\n\n" % (N, t))
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

if __name__ == "__main__":
    os.makedirs("n3", exist_ok=True)
    t = float(sys.argv[1]) if len(sys.argv) > 1 else 0.3
    Ns = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [48, 64]
    for N in Ns:
        nodes, elems, groups, vf = build(N=N, t=t)
        write_mail(f"gyroid_N{N}_t{t}.mail", nodes, elems, groups, vf, N, t)
