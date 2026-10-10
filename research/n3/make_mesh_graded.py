"""E3c — voxel mesh of the OPTIMIZED graded gyroid cell for code_aster validation.

t(x) = clip(0.30 + t0shift + sum_m theta_m psi_m(x), 0.12, 0.55)
with theta, t0shift from e3_coord_search.json (coordinate-search optimum).

Usage: python make_mesh_graded.py 64,96
"""
import numpy as np
import sys, os, json
from make_mesh import gyroid_F, write_mail

MODES = [(1,0,0),(0,1,0),(0,0,1),(1,1,0),(1,0,1),(0,1,1)]

def theta_field():
    res = json.load(open(os.path.join(os.path.dirname(__file__), "e3_coord_search.json")))
    return np.array(res["theta"]), float(res["t0shift"])

def t_of(X, Y, Z, theta, mid):
    val = 0.30 + mid
    for i, (a, b, c) in enumerate(MODES):
        ph = 2*np.pi*(a*X + b*Y + c*Z)
        val = val + theta[2*i]*np.cos(ph) + theta[2*i+1]*np.sin(ph)
    return np.clip(val, 0.12, 0.55)

def build_graded(N, theta, mid):
    h = 1.0 / N
    c = (np.arange(N) + 0.5) * h
    X, Y, Z = np.meshgrid(c, c, c, indexing="ij")
    tv = t_of(X, Y, Z, theta, mid)
    solid = (np.abs(gyroid_F(X, Y, Z)) - tv) < 0.0
    ids = np.argwhere(solid)
    eid = {tuple(v): n + 1 for n, v in enumerate(ids)}
    nmap, nodes, elems = {}, [], []
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
        "X0": np.where(on_x0)[0] + 1, "X1": np.where(on_x1)[0] + 1,
        "Y0": np.where(on_y0)[0] + 1, "Y1": np.where(on_y1)[0] + 1,
        "Z0": np.where(on_z0)[0] + 1, "Z1": np.where(on_z1)[0] + 1,
        "BOUND": np.where(bound)[0] + 1,
    }
    return nodes, elems, groups, solid.mean()

def solve_shift_for_vf(N, theta, vf_target, tol=1e-6):
    """Re-solve the uniform offset delta-t0 so the DISCRETE voxel volume
    fraction of the graded cell equals vf_target at resolution N. This is the
    same volume-compensation bisection the optimizer runs on the continuum
    volume; applying it per mesh makes the FE comparison against the uniform
    baseline exactly iso-volume at every resolution."""
    h = 1.0 / N
    c = (np.arange(N) + 0.5) * h
    X, Y, Z = np.meshgrid(c, c, c, indexing="ij")
    absF = np.abs(gyroid_F(X, Y, Z))
    lo, hi = -0.3, 0.3
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        vf = ((absF - t_of(X, Y, Z, theta, mid)) < 0).mean()
        if vf < vf_target:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)


if __name__ == "__main__":
    theta, mid = theta_field()
    print(f"theta={np.round(theta,3).tolist()}  t0shift={mid:+.4f}")
    if len(sys.argv) > 1 and sys.argv[1] == "--vf":
        # python make_mesh_graded.py --vf <vf_target> <N1,N2,...>
        vf_target = float(sys.argv[2])
        for N in [int(x) for x in sys.argv[3].split(",")]:
            shift = solve_shift_for_vf(N, theta, vf_target)
            nodes, elems, groups, vf = build_graded(N, theta, shift)
            write_mail(f"gyroid_graded_N{N}_vf{vf_target}.mail", nodes, elems,
                       groups, vf, N, -1)
            print(f"   calibrated t0shift={shift:+.6f} -> discrete VF={vf:.6f} "
                  f"(target {vf_target})")
        sys.exit(0)
    Ns = [int(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else [64, 96]
    for N in Ns:
        nodes, elems, groups, vf = build_graded(N, theta, mid)
        write_mail(f"gyroid_graded_N{N}.mail", nodes, elems, groups, vf, N, -1)
