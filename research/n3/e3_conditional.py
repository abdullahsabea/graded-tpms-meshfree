"""E3a: conditional DEM for gyroid sheet -- u(x, t) over t in [T_LO, T_HI].

Same energy-minimization principle as dem_gyroid.py, but the network is
conditioned on the sheet half-thickness t, so ONE model spans the whole
design range. Doubles as the generalization evidence for the paper:
audit C1111(t) against voxel FEM at t = 0.2 / 0.3 / 0.45.

Usage: python e3_conditional.py [iters]   (resumable; checkpoint e3_cond.pt)
"""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pylibs"))
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import torch
import torch.nn as nn
from torch.func import vmap, jacrev

from tpms_levelset import TPMSSheet

DEV = "cpu"
E0, NU, EPS = 1.0, 0.3, 1.0e-2
LAM = E0 * NU / ((1 + NU) * (1 - 2 * NU))
MU = E0 / (2 * (1 + NU))
HERE = os.path.dirname(__file__)
CKPT = os.path.join(HERE, "e3_cond.pt")
WARM = os.path.join(HERE, "dem_gyroid_t0.3.pt")  # unconditional model for warm-start
T_LO, T_HI = 0.15, 0.50
K = 2 * np.pi

# gyroid basis function F(kx), reused for sampling and Vf table
_probe = TPMSSheet("gyroid", k=K, t=0.3)

def Fval(x):
    return _probe.F(K * x)

# ---- volume-fraction table Vf(t): analytic MC, fixed point set ------------
VF_TAB = os.path.join(HERE, "e3_vf_table.json")
if os.path.exists(VF_TAB):
    _vf = json.load(open(VF_TAB))
    T_GRID = np.array(_vf["t"]); VF_GRID = np.array(_vf["vf"])
else:
    g = torch.Generator().manual_seed(7)
    pts = torch.rand(400_000, 3, generator=g)
    absF = torch.abs(Fval(pts)).numpy()
    T_GRID = np.linspace(T_LO, T_HI, 71)
    VF_GRID = np.array([np.mean(absF <= t) for t in T_GRID])
    json.dump({"t": T_GRID.tolist(), "vf": VF_GRID.tolist()}, open(VF_TAB, "w"))

def vf_of(t):
    return float(np.interp(t, T_GRID, VF_GRID))

class CondFourierMLP(nn.Module):
    def __init__(self, width=128, depth=4, sigmas=(1.0, 4.0, 12.0)):
        super().__init__()
        thirds = [width // 6] * 3
        B = torch.cat([torch.randn(3, t) * s for s, t in zip(sigmas, thirds)], dim=1)
        self.register_buffer("B", B)
        layers, d = [], 2 * B.shape[1] + 1   # +1 for the t condition
        for _ in range(depth):
            layers += [nn.Linear(d, width), nn.Tanh()]
            d = width
        layers += [nn.Linear(width, 3)]
        self.net = nn.Sequential(*layers)

    def forward(self, x, t):
        z = torch.cat([torch.sin(x @ self.B), torch.cos(x @ self.B),
                       t.expand(x.shape[:-1] + (1,))], dim=-1)
        return self.net(z)

def d_cube(x):
    c = torch.cat([x, 1.0 - x], dim=-1)
    return c.min(dim=-1, keepdim=True).values

def make_model():
    model = CondFourierMLP()
    raw = model.forward
    def full(x, t):
        u = raw(x, t)
        d = d_cube(x)
        aff = torch.stack([EPS * x[..., 0], torch.zeros_like(x[..., 0]),
                           torch.zeros_like(x[..., 0])], dim=-1)
        return d * u + aff
    model.forward = full
    return model

def strain_energy(model, pts, t):
    du = vmap(jacrev(lambda p: model(p, t)))(pts)     # (N,3,3)
    exx, eyy, ezz = du[:, 0, 0], du[:, 1, 1], du[:, 2, 2]
    exy = 0.5 * (du[:, 0, 1] + du[:, 1, 0])
    exz = 0.5 * (du[:, 0, 2] + du[:, 2, 0])
    eyz = 0.5 * (du[:, 1, 2] + du[:, 2, 1])
    tr = exx + eyy + ezz
    e2 = exx**2 + eyy**2 + ezz**2 + 2 * (exy**2 + exz**2 + eyz**2)
    return 0.5 * (LAM * tr**2 + 2 * MU * e2)

def sample_solid(n, t, seed):
    """Rejection-sample n points inside {|F(kx)| < t}."""
    g = torch.Generator().manual_seed(seed)
    out, need = [], n
    while need > 0:
        cand = torch.rand(4 * need, 3, generator=g)
        keep = torch.abs(Fval(cand)) < t
        got = cand[keep]
        out.append(got[:need]); need -= min(len(got), need)
    return torch.cat(out)[:n]

def main():
    iters = int(sys.argv[1]) if len(sys.argv) > 1 else 1200
    N_MC = 6000
    torch.set_default_dtype(torch.float32)
    torch.manual_seed(0)
    model = make_model()
    if os.path.exists(CKPT):
        model.load_state_dict(torch.load(CKPT, weights_only=True))
        print(f"resumed from {CKPT}")
    elif os.path.exists(WARM):
        sd = torch.load(WARM, weights_only=True)
        own = model.state_dict()
        hit = {k: v for k, v in sd.items() if k in own and own[k].shape == v.shape
               and k != "B"}
        own.update(hit)
        model.load_state_dict(own)
        print(f"warm-started {len(hit)}/{len(own)} tensors from {WARM}")
    opt = torch.optim.Adam(model.parameters(), lr=5e-4)
    t0 = time.time()
    T_PER_BATCH = 3
    for it in range(iters):
        opt.zero_grad()
        g = torch.Generator().manual_seed(it)
        ts = T_LO + (T_HI - T_LO) * torch.rand(T_PER_BATCH, generator=g)
        loss = 0.0
        for j, tj in enumerate(ts):
            t = float(tj)
            pts = sample_solid(N_MC // T_PER_BATCH, t, seed=10_000 * it + j)
            dens = strain_energy(model, pts, tj)
            U = dens.mean() * vf_of(t)
            loss = loss + U / U.detach()   # balance gradient scale across thicknesses
        loss.backward()
        opt.step()
        if it % 100 == 0 or it == iters - 1:
            print(f"it {it:5d}  loss={float(loss.detach()):.4f}  ({time.time()-t0:.0f}s)", flush=True)
    torch.save(model.state_dict(), CKPT)

    # ---- float64 audit across the design range ----
    torch.set_default_dtype(torch.float64)
    model64 = make_model()
    sd = {k: v.double() for k, v in model.state_dict().items()}
    model64.load_state_dict(sd)
    ASTER_REF = {0.2: 0.06724, 0.3: 0.10725, 0.45: 0.18114}
    audit = {}
    for t in (0.2, 0.25, 0.3, 0.35, 0.4, 0.45):
        ds = []
        for s in range(4):
            pts = sample_solid(20_000, t, seed=2000 + s).double()
            ds.append(strain_energy(model64, pts, torch.tensor(t, dtype=torch.float64)))
        d = torch.cat(ds)
        U64 = d.mean().item() * vf_of(t)
        c = 2 * U64 / (EPS**2)
        ref = ASTER_REF.get(round(t, 2))
        ratio = c / ref if ref else None
        audit[f"{t:.2f}"] = dict(C1111=c, aster=ref, ratio=ratio)
        tag = f"  aster={ref:.5f}  ratio={ratio:.4f}" if ref else ""
        print(f"AUDIT t={t:.2f}: C1111 = {c:.4f}{tag}")
    json.dump(audit, open(os.path.join(HERE, "e3_cond_audit.json"), "w"), indent=2)

if __name__ == "__main__":
    main()
