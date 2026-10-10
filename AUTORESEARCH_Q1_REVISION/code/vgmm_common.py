"""Shared machinery for the VG-MM experiment (AUTORESEARCH_Q1_REVISION).

Reuses, without duplication:
  * conditional DEM surrogate  : research/n3/e3_conditional.py + e3_cond.pt
  * voxel mesh writer          : research/n3/make_mesh.py (write_mail)
  * code_aster KUBC energy job : research/n3/homog2.comm (C1111_ENERGY basis)
  * FE-in-loop protocol/layout : research/n3/e3_fe_baseline.py (grid, modes,
                                 bisection, content-hash keys, docker runner)

Environment notes (frozen):
  * system torch must be imported BEFORE e3_conditional (repo workaround;
    research/pylibs torch DLLs are stale on this machine).
  * docker image simvia/code_aster:stable; repo root mounted at /shared.
  * legacy solve cache research/n3/febase is READ for reuse; new solves are
    written to AUTORESEARCH_Q1_REVISION/results/febase_vgmm. Budget
    accounting counts every distinct candidate query as one FE call whether
    or not it hits a cache (no free information).
"""
import hashlib
import json
import os
import re
import subprocess
import sys

import numpy as np
import torch  # system install, see module docstring

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.dirname(HERE)
REPO = os.path.dirname(WS)
N3 = os.path.join(REPO, "research", "n3")
sys.path.insert(0, REPO)
sys.path.insert(0, N3)

import e3_conditional as ec  # noqa: E402  (torch already imported)
from make_mesh import write_mail  # noqa: E402

# ---- frozen protocol constants (identical to e3_fe_baseline.py) ----------
VF_TARGET = 0.19328
T_MIN, T_MAX = 0.12, 0.55
T0 = 0.30
TAU = 0.02
MODES = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, 0, 1), (0, 1, 1)]
N_MODES = 12
GRID = np.linspace(-0.22, 0.22, 9)
SWEEPS = 2

DOCKER_IMG = "simvia/code_aster:stable"
FE_LEGACY = os.path.join(N3, "febase")
FE_NEW = os.path.join(WS, "results", "febase_vgmm")
os.makedirs(FE_NEW, exist_ok=True)


# ---- design field ---------------------------------------------------------
def t_field(X, Y, Z, theta, shift):
    v = T0 + shift + 0.0 * X
    for i, (a, b, c) in enumerate(MODES):
        ph = 2 * np.pi * (a * X + b * Y + c * Z)
        v = v + theta[2 * i] * np.cos(ph) + theta[2 * i + 1] * np.sin(ph)
    return np.clip(v, T_MIN, T_MAX)


def discrete_mask(N, theta, shift):
    h = 1.0 / N
    c = (np.arange(N) + 0.5) * h
    X, Y, Z = np.meshgrid(c, c, c, indexing="ij")
    absF = np.abs(_gyroid_F_np(X, Y, Z))
    return (absF - t_field(X, Y, Z, theta, shift)) < 0.0


def _gyroid_F_np(x, y, z, k=2 * np.pi):
    X, Y, Z = k * x, k * y, k * z
    return (np.sin(X) * np.cos(Y) + np.sin(Y) * np.cos(Z)
            + np.sin(Z) * np.cos(X))


def discrete_vf(N, theta, shift):
    return float(discrete_mask(N, theta, shift).mean())


def bisect_shift_discrete(N, theta):
    lo, hi = -0.30, 0.30
    for _ in range(28):
        mid = 0.5 * (lo + hi)
        if discrete_vf(N, theta, mid) < VF_TARGET:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def cand_key(N, theta, shift):
    return hashlib.sha1(
        (f"{N}|{np.asarray(theta).round(6).tobytes()}|{shift:.6f}"
         ).encode()).hexdigest()[:16]


# ---- FE solve (docker code_aster, energy basis) ---------------------------
def fe_solve(N, theta, shift, retries=1):
    """C1111_ENERGY for one candidate. Returns (value, key, from_legacy_cache,
    newly_solved). Raises RuntimeError after retries on failure."""
    key = cand_key(N, theta, shift)
    legacy = os.path.join(FE_LEGACY, f"oute_{key}.mess")
    fresh = os.path.join(FE_NEW, f"oute_{key}.mess")

    def parse(path):
        m = re.search(r"C1111_ENERGY = ([\d.eE+-]+)",
                      open(path, errors="ignore").read())
        return float(m.group(1)) if m else None

    if os.path.exists(legacy):
        v = parse(legacy)
        if v is not None:
            return v, key, True, False
    if os.path.exists(fresh):
        v = parse(fresh)
        if v is not None:
            return v, key, False, False

    mail = os.path.join(FE_NEW, f"m_{key}.mail")
    _build_mail(mail, N, theta, shift)
    exp = os.path.join(FE_NEW, f"s_{key}.export")
    with open(exp, "w") as f:
        f.write(f"P actions make_etude\nP memory_limit 8000\n"
                f"P time_limit 3600\nP mpi_nbcpu 1\n"
                f"F comm /shared/research/n3/homog2.comm D 1\n"
                f"F mail /shared/AUTORESEARCH_Q1_REVISION/results/febase_vgmm/"
                f"{os.path.basename(mail)} D 20\n"
                f"F mess /shared/AUTORESEARCH_Q1_REVISION/results/febase_vgmm/"
                f"{os.path.basename(fresh)} R 6\n")
    for attempt in range(retries + 1):
        subprocess.run(
            ["docker", "run", "--rm", "-m", "8g",
             "-v", f"{REPO.replace(chr(92), '/')}:/shared", DOCKER_IMG,
             "bash", "-c",
             f"source /opt/activate.sh; run_aster /shared/"
             f"AUTORESEARCH_Q1_REVISION/results/febase_vgmm/"
             f"{os.path.basename(exp)}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        if os.path.exists(fresh):
            v = parse(fresh)
            if v is not None:
                return v, key, False, True
    raise RuntimeError(f"FE solve failed for {key} (N={N}) after retries")


def _build_mail(path, N, theta, shift):
    mask = discrete_mask(N, theta, shift)
    h = 1.0 / N
    ids = np.argwhere(mask)
    nmap, nodes, elems = {}, [], []
    for (i, j, k) in ids:
        corner = [(i, j, k), (i + 1, j, k), (i + 1, j + 1, k), (i, j + 1, k),
                  (i, j, k + 1), (i + 1, j, k + 1), (i + 1, j + 1, k + 1),
                  (i, j + 1, k + 1)]
        row = []
        for key in corner:
            if key not in nmap:
                nmap[key] = len(nodes) + 1
                nodes.append((key[0] * h, key[1] * h, key[2] * h))
            row.append(nmap[key])
        elems.append((len(elems) + 1, row))
    nodes = np.array(nodes)
    tol = 1e-9
    on_x0 = nodes[:, 0] < tol; on_x1 = nodes[:, 0] > 1 - tol
    on_y0 = nodes[:, 1] < tol; on_y1 = nodes[:, 1] > 1 - tol
    on_z0 = nodes[:, 2] < tol; on_z1 = nodes[:, 2] > 1 - tol
    groups = {"X0": np.where(on_x0)[0] + 1, "X1": np.where(on_x1)[0] + 1,
              "Y0": np.where(on_y0)[0] + 1, "Y1": np.where(on_y1)[0] + 1,
              "Z0": np.where(on_z0)[0] + 1, "Z1": np.where(on_z1)[0] + 1,
              "BOUND": np.where(on_x0 | on_x1 | on_y0 | on_y1 | on_z0 | on_z1)[0] + 1}
    write_mail(path, nodes, elems, groups, float(mask.mean()), N, -1)


# ---- conditional-DEM soft scorer (fixed cloud, frozen recipe) -------------
def make_scorer(cloud_seed=11, n_cloud=50_000):
    """Frozen DEM ranking score: smoothed-membership C1111 on a fixed cloud,
    the objective of e3_optimize.py Stage 1 evaluated at enforced volume
    (shift supplied by bisection). float32; deterministic."""
    torch.set_default_dtype(torch.float32)
    model = ec.make_model()
    model.load_state_dict(torch.load(ec.CKPT, weights_only=True))
    for p in model.parameters():
        p.requires_grad_(False)

    def raw_net(x, t):
        z = torch.cat([torch.sin(x @ model.B), torch.cos(x @ model.B),
                       t.expand(x.shape[:-1] + (1,))], dim=-1)
        return model.net(z)

    def full_xt(xt):
        x, t = xt[..., :3], xt[..., 3:4]
        u = raw_net(x, t)
        d = ec.d_cube(x)
        aff = torch.stack([ec.EPS * x[..., 0], torch.zeros_like(x[..., 0]),
                           torch.zeros_like(x[..., 0])], dim=-1)
        return d * u + aff

    from torch.func import vmap, jacrev

    def strain_xt(xt):
        du = vmap(jacrev(full_xt))(xt)[:, :, :3]
        exx, eyy, ezz = du[:, 0, 0], du[:, 1, 1], du[:, 2, 2]
        exy = 0.5 * (du[:, 0, 1] + du[:, 1, 0])
        exz = 0.5 * (du[:, 0, 2] + du[:, 2, 0])
        eyz = 0.5 * (du[:, 1, 2] + du[:, 2, 1])
        tr = exx + eyy + ezz
        e2 = (exx**2 + eyy**2 + ezz**2
              + 2 * (exy**2 + exz**2 + eyz**2))
        return 0.5 * (ec.LAM * tr**2 + 2 * ec.MU * e2)

    g = torch.Generator().manual_seed(cloud_seed)
    pts = torch.rand(n_cloud, 3, generator=g)
    absF = torch.abs(ec.Fval(pts))
    psi_cols = []
    for (a, b, c) in MODES:
        ph = 2 * np.pi * (a * pts[:, 0] + b * pts[:, 1] + c * pts[:, 2])
        psi_cols += [torch.cos(ph), torch.sin(ph)]
    psiv = torch.stack(psi_cols, dim=-1)

    def score(theta, shift):
        theta_t = torch.tensor(theta, dtype=torch.float32)
        tx = (T0 + float(shift) + psiv @ theta_t).clamp(T_MIN, T_MAX)
        w = torch.sigmoid((tx - absF) / TAU)
        xt = torch.cat([pts, tx.unsqueeze(-1)], dim=-1)
        with torch.no_grad():
            dens = strain_xt(xt)
        U = (w * dens).mean().item()
        return 2.0 * U / ec.EPS**2

    return score
