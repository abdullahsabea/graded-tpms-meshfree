"""
N3b — Mesh-free DEM homogenization of a gyroid sheet unit cell (KUBC, eps_xx)
==============================================================================
Same problem as the code_aster ground truth (study_N48/N64):
  gyroid sheet, t=0.3, k=2*pi, unit cube, E=1, nu=0.3, KUBC eps_xx=1e-3.
  C1111 = 2U / (eps^2 * V_solid).

Hard BC:  u = d_cube(x) * N(x) + (eps*x, 0, 0),  d_cube = min distance to the
six cube faces -> u equals the imposed affine field exactly on the boundary.
Interior TPMS surface is traction-free (natural BC — nothing to enforce).

Training is chunked across invocations (300 s shell limit): each run resumes
from n3/dem_gyroid.pt. MC collocation uniform in the solid (rejection sampling
from the analytic level set) — unbiased; weights = V_solid/N.

Usage:  python dem_gyroid.py [iters_per_chunk]
"""
import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pylibs"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
import torch
import torch.nn as nn
from torch.func import jacrev, vmap
from tpms_levelset import TPMSSheet

DEV = "cpu"
E0, NU, EPS = 1.0, 0.3, 1.0e-2  # eps scaled 10x: identical C1111 (linear), beats float32 noise floor
LAM = E0 * NU / ((1 + NU) * (1 - 2 * NU))
MU = E0 / (2 * (1 + NU))
HERE = os.path.dirname(__file__)
T_PARAM = float(sys.argv[2]) if len(sys.argv) > 2 else 0.3
CKPT = os.path.join(HERE, f"dem_gyroid_t{T_PARAM}.pt")
WARM = os.path.join(HERE, "dem_gyroid.pt")  # t=0.3 baseline for warm-start

tpms = TPMSSheet("gyroid", k=2 * np.pi, t=T_PARAM)
V_SOLID = tpms.volume_fraction(n=1_000_000)  # analytic MC estimate per thickness

class FourierMLP(nn.Module):
    def __init__(self, width=128, depth=4, sigmas=(1.0, 4.0, 12.0)):
        super().__init__()
        # multi-scale random Fourier features: coarse (macro bending) + fine (wall-thickness gradients)
        thirds = [width // 6] * 3
        B = torch.cat([torch.randn(3, t) * s for s, t in zip(sigmas, thirds)], dim=1)
        self.register_buffer("B", B)
        layers, d = [], 2 * B.shape[1]
        for _ in range(depth):
            layers += [nn.Linear(d, width), nn.Tanh()]
            d = width
        layers += [nn.Linear(width, 3)]
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        z = torch.cat([torch.sin(x @ self.B), torch.cos(x @ self.B)], dim=-1)
        return self.net(z)

def d_cube(x):
    c = torch.cat([x, 1.0 - x], dim=-1)
    return c.min(dim=-1, keepdim=True).values

def make_model():
    model = FourierMLP()
    raw = model.forward
    def full(x):
        u = raw(x)
        d = d_cube(x)
        out = d * u
        out = out.clone() if hasattr(out, "clone") else out
        # impose affine KUBC field: (eps*x, 0, 0)
        aff = torch.stack([EPS * x[..., 0], torch.zeros_like(x[..., 0]), torch.zeros_like(x[..., 0])], dim=-1)
        return d * u + aff
    model.forward = full
    return model

def strain_energy(model, pts):
    du = vmap(jacrev(model))(pts)          # (N,3,3)
    exx, eyy, ezz = du[:, 0, 0], du[:, 1, 1], du[:, 2, 2]
    exy = 0.5 * (du[:, 0, 1] + du[:, 1, 0])
    exz = 0.5 * (du[:, 0, 2] + du[:, 2, 0])
    eyz = 0.5 * (du[:, 1, 2] + du[:, 2, 1])
    tr = exx + eyy + ezz
    e2 = exx**2 + eyy**2 + ezz**2 + 2 * (exy**2 + exz**2 + eyz**2)
    return 0.5 * (LAM * tr**2 + 2 * MU * e2)

def sample_solid(n, seed):
    return tpms.sample(n, seed=seed)

def main():
    iters = int(sys.argv[1]) if len(sys.argv) > 1 else 700
    N_MC = 6000
    torch.set_default_dtype(torch.float32)   # train fast; audit in float64
    torch.manual_seed(0)
    model = make_model()
    if os.path.exists(CKPT):
        model.load_state_dict(torch.load(CKPT, weights_only=True))
        print(f"resumed from {CKPT}")
    elif os.path.exists(WARM) and abs(T_PARAM - 0.3) > 1e-9:
        model.load_state_dict(torch.load(WARM, weights_only=True))
        print(f"warm-started from {WARM} (t=0.3)")
    print(f"t={T_PARAM}  V_solid={V_SOLID:.5f}")
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    t0 = time.time()
    for it in range(iters):
        opt.zero_grad()
        pts = sample_solid(N_MC, seed=it)
        dens = strain_energy(model, pts)
        U = dens.mean() * V_SOLID
        U.backward()
        opt.step()
        if it % 100 == 0 or it == iters - 1:
            c = 2 * float(U.detach()) / (EPS**2 * 1.0)
            print(f"it {it:5d}  U={float(U):.4e}  C1111={c:.4f}  ({time.time()-t0:.0f}s)", flush=True)

    # deterministic LBFGS polish on a large fixed collocation set
    fixed = sample_solid(60_000, seed=999)
    opt2 = torch.optim.LBFGS(model.parameters(), max_iter=80, tolerance_grad=1e-10,
                             tolerance_change=1e-13, history_size=10, line_search_fn="strong_wolfe")
    state = [0]
    def closure():
        opt2.zero_grad()
        dens = strain_energy(model, fixed)
        U = dens.mean() * V_SOLID
        U.backward()
        if state[0] % 10 == 0:
            c = 2 * float(U.detach()) / (EPS**2 * 1.0)
            print(f"  LBFGS {state[0]:3d}  U={float(U):.4e}  C1111={c:.4f}", flush=True)
        state[0] += 1
        return U
    opt2.step(closure)
    torch.save(model.state_dict(), CKPT)

    # --- float64 audit on large MC set ---
    torch.set_default_dtype(torch.float64)
    model64 = make_model()
    sd = {k: v.double() for k, v in model.state_dict().items()}
    model64.load_state_dict(sd)
    ds = []
    for s in range(6):
        pts = sample_solid(20_000, seed=1000 + s).double()
        ds.append(strain_energy(model64, pts))
    d = torch.cat(ds)
    U64 = d.mean().item() * V_SOLID
    se = (d.std().item() / np.sqrt(len(d))) * V_SOLID
    c1111 = 2 * U64 / (EPS**2 * 1.0)
    c_se = 2 * se / (EPS**2 * 1.0)
    ASTER_REF = {0.2: 0.06724, 0.3: 0.10725, 0.45: 0.18114}  # converged KUBC values
    ref = ASTER_REF.get(T_PARAM)
    print(f"AUDIT: U={U64:.5e} ± {se:.2e}  ->  C1111_DEM = {c1111:.4f} ± {c_se:.4f}")
    if ref:
        print(f"REFERENCE: aster C1111 = {ref:.5f}  (DEM/aster = {c1111/ref:.4f})")
    meta = dict(t=T_PARAM, C1111_dem=c1111, C1111_se=c_se, U=U64, V_solid=V_SOLID,
                aster_ref=ref, ratio=(c1111 / ref if ref else None), iters_chunk=iters)
    json.dump(meta, open(os.path.join(HERE, f"n3_dem_metrics_t{T_PARAM}.json"), "w"), indent=2)

if __name__ == "__main__":
    main()
