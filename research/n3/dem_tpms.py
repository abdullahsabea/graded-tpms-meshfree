"""
N3c — Mesh-free DEM homogenization across TPMS families (KUBC, eps_xx)
==============================================================================
Family-generic version of dem_gyroid.py: identical network, hard-BC ansatz,
energy functional, optimizer schedule and float64 audit, with the only change
being the analytic level set that defines the collocation domain.

Same problem as the code_aster ground truth (study_{family}_N{48,64,96}):
  sheet TPMS, k=2*pi, unit cube, E=1, nu=0.3, KUBC eps_xx=1e-2,
  C1111 = 2U / (eps^2 * V_macro),  V_macro = 1.

Thresholds are matched on continuum volume fraction VF=0.1933:
  gyroid t=0.3      primitive t=0.3387      diamond t=0.2360

Hard BC:  u = d_cube(x) * N(x) + (eps*x, 0, 0),  d_cube = min distance to the
six cube faces -> u equals the imposed affine field exactly on the boundary.
Interior TPMS surface is traction-free (natural BC — nothing to enforce).

Training is chunked across invocations: each run resumes from its checkpoint.

Usage:  python dem_tpms.py <family> <t> [iters_per_chunk]
"""
import sys, os, json, time, glob, re
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
HERE = os.path.dirname(os.path.abspath(__file__))

FAMILY = sys.argv[1] if len(sys.argv) > 1 else "gyroid"
T_PARAM = float(sys.argv[2]) if len(sys.argv) > 2 else 0.3
CKPT = os.path.join(HERE, f"dem_{FAMILY}_t{T_PARAM}.pt")

tpms = TPMSSheet(FAMILY, k=2 * np.pi, t=T_PARAM)
V_SOLID = tpms.volume_fraction(n=1_000_000)  # analytic MC estimate


def aster_reference(family):
    """Read C1111 from the code_aster .mess files of this family (finest N)."""
    out = {}
    for path in glob.glob(os.path.join(HERE, f"out_{family}_N*.mess")):
        N = int(re.search(r"_N(\d+)\.mess$", path).group(1))
        with open(path, errors="ignore") as f:
            for line in f:
                if line.startswith("C1111_KUBC"):
                    out[N] = float(line.split("=")[1])
    return out


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


def main():
    iters = int(sys.argv[3]) if len(sys.argv) > 3 else 700
    # collocation points per iteration; the N2 gate identifies Monte Carlo
    # under-resolution of sharp strain gradients as the solver's error
    # mechanism, so this is the knob that tests it
    N_MC = int(os.environ.get("DEM_NMC", 6000))
    torch.set_default_dtype(torch.float32)   # train fast; audit in float64
    torch.manual_seed(0)
    model = make_model()
    it0 = 0
    if os.path.exists(CKPT):
        blob = torch.load(CKPT, weights_only=True)
        sd = blob.get("state", blob) if isinstance(blob, dict) and "state" in blob else blob
        it0 = blob.get("iters", 0) if isinstance(blob, dict) and "iters" in blob else 0
        model.load_state_dict(sd)
        print(f"resumed from {CKPT} (cumulative iters={it0})")
    print(f"family={FAMILY}  t={T_PARAM}  V_solid={V_SOLID:.5f}")
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    t0 = time.time()
    for it in range(iters):
        opt.zero_grad()
        pts = tpms.sample(N_MC, seed=it0 + it)
        dens = strain_energy(model, pts)
        U = dens.mean() * V_SOLID
        U.backward()
        opt.step()
        if it % 100 == 0 or it == iters - 1:
            c = 2 * float(U.detach()) / (EPS**2 * 1.0)
            print(f"it {it0+it:6d}  U={float(U):.4e}  C1111={c:.4f}  ({time.time()-t0:.0f}s)", flush=True)

    # deterministic LBFGS polish on a large fixed collocation set
    fixed = tpms.sample(60_000, seed=999)
    opt2 = torch.optim.LBFGS(model.parameters(), max_iter=80, tolerance_grad=1e-10,
                             tolerance_change=1e-13, history_size=10, line_search_fn="strong_wolfe")
    state = [0]

    def closure():
        opt2.zero_grad()
        dens = strain_energy(model, fixed)
        U = dens.mean() * V_SOLID
        U.backward()
        if state[0] % 20 == 0:
            c = 2 * float(U.detach()) / (EPS**2 * 1.0)
            print(f"  LBFGS {state[0]:3d}  U={float(U):.4e}  C1111={c:.4f}", flush=True)
        state[0] += 1
        return U

    opt2.step(closure)
    torch.save({"state": model.state_dict(), "iters": it0 + iters}, CKPT)

    # --- float64 audit on large MC set ---
    torch.set_default_dtype(torch.float64)
    model64 = make_model()
    model64.load_state_dict({k: v.double() for k, v in model.state_dict().items()})
    ds = []
    for s in range(6):
        ds.append(strain_energy(model64, tpms.sample(20_000, seed=1000 + s).double()))
    d = torch.cat(ds)
    U64 = d.mean().item() * V_SOLID
    se = (d.std().item() / np.sqrt(len(d))) * V_SOLID
    c1111 = 2 * U64 / (EPS**2 * 1.0)
    c_se = 2 * se / (EPS**2 * 1.0)
    ref = aster_reference(FAMILY)
    finest = ref.get(max(ref)) if ref else None
    print(f"AUDIT: U={U64:.5e} ± {se:.2e}  ->  C1111_DEM = {c1111:.4f} ± {c_se:.4f}")
    if finest:
        print(f"REFERENCE: aster {sorted(ref.items())}  (DEM/aster_finest = {c1111/finest:.4f})")
    json.dump(dict(family=FAMILY, t=T_PARAM, C1111_dem=c1111, C1111_se=c_se, U=U64,
                   V_solid=V_SOLID, aster=ref, ratio=(c1111 / finest if finest else None),
                   iters_total=it0 + iters, n_mc=N_MC),
              open(os.path.join(HERE, f"n3_dem_metrics_{FAMILY}.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
