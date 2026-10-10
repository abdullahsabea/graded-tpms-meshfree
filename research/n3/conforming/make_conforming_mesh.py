"""Body-fitted tetrahedral mesh of the uniform gyroid sheet cell (t = 0.30).

Quantifies the voxel-staircase part of the DEM-minus-FE deviation. The solid
boundary is the analytic level set |F| = t (marching-cubes facets at spacing
1/N, flat caps exactly on the cube faces), filled with TetGen linear tets; code_aster
upgrades them to quadratic TETRA10 (homog_conf.comm). Same KUBC energy-basis
problem as homog2.comm.

    python make_conforming_mesh.py <N>      surface spacing 1/N, e.g. 40, 60, 80
Writes gyroid_conf_N<N>.mail (ASTER text) and gyroid_conf_N<N>.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pyvista as pv
import tetgen

HERE = Path(__file__).parent
T = 0.30


def F(x, y, z):
    X, Y, Z = 2 * np.pi * x, 2 * np.pi * y, 2 * np.pi * z
    return np.sin(X) * np.cos(Y) + np.sin(Y) * np.cos(Z) + np.sin(Z) * np.cos(X)


MODES = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, 0, 1), (0, 1, 1)]


def t_field(design):
    """Analytic thickness field of each design (continuum volume shift)."""
    if design == "uniform":
        return lambda x, y, z: np.full_like(x, T)
    if design in ("vgmm", "fullfe"):
        # FE-searched winners (KUBC voxel FE): VG-MM seed-11 run and the full-FE
        # coordinate search. Their voxel shifts are grid-specific, so the continuum
        # shift is re-solved on the analytic level set for V_f = 0.19328.
        if design == "vgmm":
            src = HERE.parents[2] / "AUTORESEARCH_Q1_REVISION" / "results" / "vgmm_result.json"
            th = np.array(json.loads(src.read_text())["theta_final"])
        else:
            th = np.array(json.loads((HERE.parent / "e3_fe_baseline.json").read_text())["theta"])
        lo, hi = 0.12, 0.55

        def raw(x, y, z, sh):
            v = 0.30 + sh
            for i, (a, b, c) in enumerate(MODES):
                ph = 2 * np.pi * (a * x + b * y + c * z)
                v = v + th[2 * i] * np.cos(ph) + th[2 * i + 1] * np.sin(ph)
            return np.clip(v, lo, hi)
        n = 300
        g = (np.arange(n) + 0.5) / n
        X2, Y2 = np.meshgrid(g, g, indexing="ij")

        def vf(sh):
            return np.mean([np.mean(np.abs(F(X2, Y2, z + 0 * X2)) <= raw(X2, Y2, z + 0 * X2, sh)) for z in g])
        a_, b_ = -0.1, 0.1
        for _ in range(30):
            m_ = 0.5 * (a_ + b_)
            a_, b_ = (m_, b_) if vf(m_) < 0.19328 else (a_, m_)
        sh = 0.5 * (a_ + b_)
        print(f"{design}: continuum shift {sh:+.6f}, V_f {vf(sh):.5f}", flush=True)
        return lambda x, y, z: raw(x, y, z, sh)
    if design == "graded":
        d = json.loads((HERE.parent / "e3_coord_search.json").read_text())
        th, sh, lo, hi = np.array(d["theta"]), d["t0shift"], 0.12, 0.55
    else:
        d = json.loads((HERE.parent / "e3_opt_result_printable.json").read_text())
        th, sh, lo, hi = np.array(d["theta"]), d["t0shift"], d["t_min"], d["t_max"]

    def f(x, y, z):
        v = 0.30 + sh
        for i, (a, b, c) in enumerate(MODES):
            ph = 2 * np.pi * (a * x + b * y + c * z)
            v = v + th[2 * i] * np.cos(ph) + th[2 * i + 1] * np.sin(ph)
        return np.clip(v, lo, hi)
    return f


def surface(N, design="uniform"):
    # Closed sheet surface on an enlarged box, intersected exactly with the
    # unit cell (manifold3d Boolean), so the caps lie on the cell faces.
    import manifold3d as mf
    h = 1.0 / N
    ext = 0.15
    ax = np.arange(-ext - 2 * h, 1 + ext + 2.5 * h, h)
    X, Y, Z = np.meshgrid(ax, ax, ax, indexing="ij")
    box = np.maximum.reduce([-ext - X, X - 1 - ext, -ext - Y, Y - 1 - ext, -ext - Z, Z - 1 - ext])
    phi = np.maximum(np.abs(F(X, Y, Z)) - t_field(design)(X, Y, Z), 8.0 * box)
    g = pv.ImageData(dimensions=X.shape, spacing=(h, h, h), origin=(ax[0],) * 3)
    g["phi"] = phi.ravel(order="F")
    s = g.contour([0.0], scalars="phi").triangulate().clean()
    tri = np.ascontiguousarray(s.faces.reshape(-1, 4)[:, 1:][:, ::-1], dtype=np.uint32)
    m = mf.Manifold(mf.Mesh(vert_properties=np.asarray(s.points, np.float32), tri_verts=tri))
    r = (m ^ mf.Manifold.cube([1.0, 1.0, 1.0])).to_mesh()
    p = np.asarray(r.vert_properties, float)[:, :3]
    for k in range(3):
        for v in (0.0, 1.0):
            p[np.abs(p[:, k] - v) < 1e-6, k] = v
    faces = np.asarray(r.tri_verts, np.int64)
    out = pv.PolyData(p, np.hstack([np.full((len(faces), 1), 3), faces]).ravel())
    return out.clean(tolerance=1e-12).triangulate()


def refine_caps(s, h):
    """Re-triangulate the planar caps with quality triangles of size ~h.

    The Boolean leaves each cap as a few long, thin triangles; with TetGen's Y switch
    (surface preserved) these become flat sliver tets, fine under KUBC (cap nodes fixed)
    but a near-zero-stiffness mode under periodic BCs. Cap boundary edges are kept
    exactly (Triangle switch YY: no points inserted on segments), so the surface stays
    conforming with the curved sheet.
    """
    import triangle as tr
    P = np.asarray(s.points, float)
    Fc = s.faces.reshape(-1, 4)[:, 1:]
    keep = np.ones(len(Fc), bool)
    new_pts, new_tris = [P], []
    nP = len(P)
    for k in range(3):
        for v in (0.0, 1.0):
            on = np.all(np.abs(P[Fc][:, :, k] - v) < 1e-12, axis=1)
            if not on.any():
                continue
            cap = Fc[on]
            keep[on] = False
            e = np.sort(np.vstack([cap[:, [0, 1]], cap[:, [1, 2]], cap[:, [0, 2]]]), axis=1)
            ue, cnt = np.unique(e, axis=0, return_counts=True)
            seg = ue[cnt == 1]
            vid = np.unique(seg)
            loc = {g: i for i, g in enumerate(vid)}
            ax = [a for a in range(3) if a != k]
            V2 = P[vid][:, ax]
            S = np.vectorize(loc.get)(seg)
            out = tr.triangulate(dict(vertices=V2, segments=S), f"pYYq25a{0.5 * h * h:.3e}Q")
            W, Tn = out["vertices"], out["triangles"]
            # keep triangles whose centroid lies inside the original cap
            c = W[Tn].mean(1)
            A, B, C = (P[cap[:, j]][:, ax] for j in range(3))
            inside = np.zeros(len(c), bool)
            for i0 in range(0, len(c), 2000):
                q = c[i0:i0 + 2000, None, :]
                d = (B - A)[None] ; e2 = (C - A)[None]; w = q - A[None]
                den = d[..., 0] * e2[..., 1] - d[..., 1] * e2[..., 0]
                l1 = (w[..., 0] * e2[..., 1] - w[..., 1] * e2[..., 0]) / den
                l2 = (d[..., 0] * w[..., 1] - d[..., 1] * w[..., 0]) / den
                inside[i0:i0 + 2000] = np.any((l1 >= -1e-12) & (l2 >= -1e-12) & (l1 + l2 <= 1 + 1e-12), axis=1)
            Tn = Tn[inside]
            gid = np.empty(len(W), np.int64)
            gid[:len(vid)] = vid
            extra = W[len(vid):]
            X3 = np.zeros((len(extra), 3))
            X3[:, k] = v
            X3[:, ax[0]], X3[:, ax[1]] = extra[:, 0], extra[:, 1]
            gid[len(vid):] = np.arange(nP, nP + len(extra))
            nP += len(extra)
            new_pts.append(X3)
            new_tris.append(gid[Tn])
    P2 = np.vstack(new_pts)
    T2 = np.vstack([Fc[keep]] + new_tris)
    out = pv.PolyData(P2, np.hstack([np.full((len(T2), 1), 3), T2]).ravel())
    return out.clean(tolerance=1e-12)


def write_mail(path, nodes, tets, tris, groups):
    with open(path, "w") as f:
        f.write("TITRE\nGYROID CONFORMING\nFINSF\n\nCOOR_3D\n")
        for i, (x, y, z) in enumerate(nodes, 1):
            f.write(f"N{i} {x:.12e} {y:.12e} {z:.12e}\n")
        f.write("FINSF\n\nTETRA4\n")
        for i, t in enumerate(tets, 1):
            f.write(f"T{i} " + " ".join(f"N{j + 1}" for j in t) + "\n")
        f.write("FINSF\n\nTRIA3\n")
        for i, t in enumerate(tris, 1):
            f.write(f"F{i} " + " ".join(f"N{j + 1}" for j in t) + "\n")
        f.write("FINSF\n\n")
        f.write("GROUP_MA\nSOLID\n")
        for i in range(1, len(tets) + 1):
            f.write(f"T{i}\n")
        f.write("FINSF\n\n")
        for name, idx in groups.items():
            f.write(f"GROUP_MA\n{name}\n")
            for i in idx:
                f.write(f"F{i + 1}\n")
            f.write("FINSF\n\n")
        f.write("FIN\n")


def main(N, M=32, design="uniform", free_caps=False, caps=False):
    s = surface(N, design)
    if caps:
        s = refine_caps(s, 1.0 / M)
    tg = tetgen.TetGen(s)
    h = 1.0 / N
    vmax = 0.6 * (1.0 / M) ** 3
    # Y keeps the input surface triangles. The planar cube caps from the Boolean are
    # coarse polygons, so Y leaves flat sliver tets beneath them: harmless under KUBC
    # (cap nodes fixed), but a near-zero-stiffness mode under periodic BCs. free_caps
    # lets TetGen split boundary facets (all planar, so the geometry is unchanged).
    sw = f"pq1.6/12a{vmax:.3e}" + ("" if free_caps else "Y") + "Q"
    nodes, tets, *_ = tg.tetrahedralize(switches=sw)
    tets = np.asarray(tets)
    a, b, c, d = (nodes[tets[:, k]] for k in range(4))
    vol6 = np.einsum("ij,ij->i", np.cross(b - a, c - a), d - a)
    tets[vol6 < 0] = tets[vol6 < 0][:, [0, 2, 1, 3]]
    solid_volume = float(np.abs(vol6).sum() / 6)

    faces = np.sort(np.vstack([tets[:, [0, 1, 2]], tets[:, [0, 1, 3]],
                               tets[:, [0, 2, 3]], tets[:, [1, 2, 3]]]), axis=1)
    uniq, cnt = np.unique(faces, axis=0, return_counts=True)
    bnd = uniq[cnt == 1]
    tris, groups = [], {}
    for k, ax in enumerate("XYZ"):
        for v in (0, 1):
            on = np.all(np.abs(nodes[bnd][:, :, k] - v) < 1e-9, axis=1)
            groups[f"{ax}{v}"] = list(range(len(tris), len(tris) + int(on.sum())))
            tris.extend(bnd[on].tolist())
    for name, idx in groups.items():
        if not idx:
            raise SystemExit(f"empty cap group {name}")
    tag = (f"N{N}" if M == 32 else f"N{N}_M{M}") + ("" if design == "uniform" else f"_{design}") + ("_fc" if free_caps else "") + ("_rc" if caps else "")
    out = HERE / f"gyroid_conf_{tag}.mail"
    write_mail(out, nodes, tets, tris, groups)
    info = dict(design=design, N_surface=N, interior_M=M, free_caps=free_caps, refined_caps=caps, nodes=int(len(nodes)), tets=int(len(tets)),
                cap_triangles={k: len(v) for k, v in groups.items()},
                solid_volume=solid_volume, surface_triangles=int(s.n_cells))
    (HERE / f"gyroid_conf_{tag}.json").write_text(json.dumps(info, indent=1))
    print(json.dumps(info))


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 32,
         sys.argv[3] if len(sys.argv) > 3 else "uniform",
         len(sys.argv) > 4 and sys.argv[4] == "free_caps",
         len(sys.argv) > 4 and sys.argv[4] == "refine_caps")
