"""Ablation for the +32.6% mechanism: retrain the conditional DEM over the
FULL optimization range t in [0.12, 0.55] (the published model was trained
on [0.15, 0.50], so the unconstrained optimum extrapolated at both
saturation bounds), then audit the same designs with both models.

If the graded-design deviation collapses toward the anchor-band deviation
(+6..16%), extrapolation dominated the +32.6%; if it persists, thin-wall
expressivity dominates. Either way the paper's mechanism attribution
becomes quantitative instead of confounded.

Same architecture, optimizer, lr, batch structure and scale balancing as
e3_conditional.py; warm-started from the published e3_cond.pt; runs on
GPU if available. Outputs: e3_cond_wide.pt, e3_wide_audit.json.

Usage: python e3_conditional_wide.py [iters]
"""
import json
import os
import sys
import time

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "pylibs"))

import e3_conditional as ec          # published model/recipe (T_LO/T_HI = 0.15/0.50)

import torch.nn as nn
from torch.func import vmap, jacrev
from tpms_levelset import TPMSSheet

E0, NU, EPS = ec.E0, ec.NU, ec.EPS
LAM, MU = ec.LAM, ec.MU
K = ec.K
T_LO, T_HI = 0.12, 0.55              # the actual optimization bounds
CKPT_PUB = os.path.join(HERE, "e3_cond.pt")
CKPT_WIDE = os.path.join(HERE, "e3_cond_wide.pt")
VF_TABLE_WIDE = os.path.join(HERE, "e3_vf_table_wide.json")

_probe = TPMSSheet("gyroid", k=K, t=0.3)
Fval = lambda x: _probe.F(K * x)

# ---- Vf(t) table over the WIDE range (analytic MC, fixed cloud) ----------
if os.path.exists(VF_TABLE_WIDE):
    _vf = json.load(open(VF_TABLE_WIDE))
    T_GRID = np.array(_vf["t"]); VF_GRID = np.array(_vf["vf"])
else:
    g = torch.Generator().manual_seed(7)
    pts = torch.rand(400_000, 3, generator=g)
    absF = torch.abs(Fval(pts)).numpy()
    T_GRID = np.linspace(T_LO, T_HI, 87)
    VF_GRID = np.array([np.mean(absF <= t) for t in T_GRID])
    json.dump({"t": T_GRID.tolist(), "vf": VF_GRID.tolist()},
              open(VF_TABLE_WIDE, "w"))

def vf_of(t):
    return float(np.interp(t, T_GRID, VF_GRID))

def d_cube(x):
    c = torch.cat([x, 1.0 - x], dim=-1)
    return c.min(dim=-1, keepdim=True).values

MODES = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, 0, 1), (0, 1, 1)]

def t_field(x, theta, t0, tmin, tmax):
    v = t0
    for i, (a, b, c) in enumerate(MODES):
        ph = 2 * np.pi * (a * x[..., 0] + b * x[..., 1] + c * x[..., 2])
        v = v + theta[2 * i] * torch.cos(ph) + theta[2 * i + 1] * torch.sin(ph)
    return v.clamp(tmin, tmax)

def sample_solid_uniform(n, t, seed):
    g = torch.Generator().manual_seed(seed)
    out, need = [], n
    while need > 0:
        cand = torch.rand(4 * need, 3, generator=g)
        keep = torch.abs(Fval(cand)) < t
        got = cand[keep]
        out.append(got[:need]); need -= min(len(got), need)
    return torch.cat(out)[:n]

def sample_solid_graded(n, theta, t0, tmin, tmax, seed):
    g = torch.Generator().manual_seed(seed)
    out, need = [], n
    while need > 0:
        cand = torch.rand(4 * need, 3, generator=g)
        keep = torch.abs(Fval(cand)) < t_field(cand, theta, t0, tmin, tmax)
        got = cand[keep]
        out.append(got[:need]); need -= min(len(got), need)
    return torch.cat(out)[:n]

def make_model():
    return ec.CondFourierMLP()   # identical architecture

def strain_energy_raw(model, pts, t_scalar):
    """u(x,t) with hard-BC ansatz, from raw net weights (avoids patched
    forward); pts/t on the model's device/dtype."""
    def full(p):
        x, tt = p[..., :3], p[..., 3:4]
        z = torch.cat([torch.sin(x @ model.B), torch.cos(x @ model.B), tt], dim=-1)
        u = model.net(z)
        d = d_cube(x)
        aff = torch.stack([EPS * x[..., 0],
                           torch.zeros_like(x[..., 0]),
                           torch.zeros_like(x[..., 0])], dim=-1)
        return d * u + aff
    xt = torch.cat([pts, torch.full_like(pts[..., :1], float(t_scalar))], dim=-1)
    du = vmap(jacrev(full))(xt)[:, :, :3]
    exx, eyy, ezz = du[:, 0, 0], du[:, 1, 1], du[:, 2, 2]
    exy = 0.5 * (du[:, 0, 1] + du[:, 1, 0])
    exz = 0.5 * (du[:, 0, 2] + du[:, 2, 0])
    eyz = 0.5 * (du[:, 1, 2] + du[:, 2, 1])
    tr = exx + eyy + ezz
    e2 = exx**2 + eyy**2 + ezz**2 + 2 * (exy**2 + exz**2 + eyz**2)
    return 0.5 * (LAM * tr**2 + 2 * MU * e2)

def audit_uniform(model64, t):
    ds = [strain_energy_raw(model64,
                            sample_solid_uniform(20_000, t, seed=3000 + s).double(),
                            t) for s in range(4)]
    U = torch.cat(ds).mean().item() * vf_of(t)
    return 2 * U / EPS**2

def audit_graded(model64, theta, t0, tmin, tmax, seeds=4):
    pts = sample_solid_graded(20_000, theta, t0, tmin, tmax, seed=5000).double()
    tx = t_field(pts, theta, t0, tmin, tmax)
    # energy at each point with its own local t
    def full_p(p):
        x, tt = p[..., :3], p[..., 3:4]
        z = torch.cat([torch.sin(x @ model64.B), torch.cos(x @ model64.B), tt], dim=-1)
        u = model64.net(z)
        d = d_cube(x)
        aff = torch.stack([EPS * x[..., 0],
                           torch.zeros_like(x[..., 0]),
                           torch.zeros_like(x[..., 0])], dim=-1)
        return d * u + aff
    xt = torch.cat([pts, tx.unsqueeze(-1)], dim=-1)
    du = vmap(jacrev(full_p))(xt)[:, :, :3]
    exx, eyy, ezz = du[:, 0, 0], du[:, 1, 1], du[:, 2, 2]
    exy = 0.5 * (du[:, 0, 1] + du[:, 1, 0])
    exz = 0.5 * (du[:, 0, 2] + du[:, 2, 0])
    eyz = 0.5 * (du[:, 1, 2] + du[:, 2, 1])
    tr = exx + eyy + ezz
    e2 = exx**2 + eyy**2 + ezz**2 + 2 * (exy**2 + exz**2 + eyz**2)
    dens = 0.5 * (LAM * tr**2 + 2 * MU * e2)
    g = torch.Generator().manual_seed(9)
    cand = torch.rand(200_000, 3, generator=g)
    vf_acc = (torch.abs(Fval(cand)) < t_field(cand, theta, t0, tmin, tmax)).float().mean().item()
    U = dens.mean().item() * vf_acc
    return 2 * U / EPS**2, vf_acc

def main():
    iters = int(sys.argv[1]) if len(sys.argv) > 1 else 20_000
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device: {dev}")
    torch.set_default_dtype(torch.float32)
    torch.manual_seed(0)
    model = make_model()
    model.load_state_dict(torch.load(CKPT_PUB, weights_only=True))
    print(f"warm-started from published {os.path.basename(CKPT_PUB)}")
    model.to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=5e-4)
    N_MC, T_PER_BATCH = 6000, 3
    t0 = time.time()
    for it in range(iters):
        opt.zero_grad()
        g = torch.Generator().manual_seed(it)
        ts = T_LO + (T_HI - T_LO) * torch.rand(T_PER_BATCH, generator=g)
        loss = 0.0
        for j, tj in enumerate(ts):
            t = float(tj)
            pts = sample_solid_uniform(N_MC // T_PER_BATCH, t,
                                       seed=10_000 * it + j).to(dev)
            dens = strain_energy_raw(model, pts, t)
            U = dens.mean() * vf_of(t)
            loss = loss + U / U.detach()
        loss.backward()
        opt.step()
        if it % 200 == 0 or it == iters - 1:
            print(f"it {it:6d}  loss={float(loss.detach()):.4f}  "
                  f"({time.time()-t0:.0f}s)", flush=True)
    torch.save(model.state_dict(), CKPT_WIDE)
    print(f"saved {CKPT_WIDE}")

    # ---- float64 audits: anchors + both optima, wide model ----
    torch.set_default_dtype(torch.float64)
    m64 = make_model()
    sd = {k: v.double() for k, v in model.state_dict().items()}
    m64.load_state_dict(sd)

    FE = {0.20: 0.06526, 0.30: 0.10554, 0.45: 0.17515,
          "graded": 0.10093, "printable": 0.10721}
    out = {"range": [T_LO, T_HI], "iters": iters,
           "warm_start": "e3_cond.pt", "uniform": {}, "designs": {}}
    for t in (0.12, 0.15, 0.20, 0.30, 0.45, 0.50, 0.55):
        c = audit_uniform(m64, t)
        ref = FE.get(round(t, 2))
        out["uniform"][f"{t:.2f}"] = {
            "C1111": c, "FE": ref,
            "dev_pct": (c / ref - 1) * 100 if ref else None}
        print(f"WIDE  t={t:.2f}: C1111={c:.4f}"
              + (f"  dev={100*(c/ref-1):+.1f}%" if ref else ""))

    cs = json.load(open(os.path.join(HERE, "e3_coord_search.json")))
    cp = json.load(open(os.path.join(HERE, "e3_opt_result_printable.json")))
    for name, res, tmin, tmax, ref in (
            ("graded", cs, 0.12, 0.55, FE["graded"]),
            ("printable", cp, cp.get("t_min", 0.20),
             cp.get("t_max", 0.45), FE["printable"])):
        theta = res["theta"]
        base = res.get("t0", 0.30) + res["t0shift"]   # full offset, as in fig4/e3_optimize
        c, vf = audit_graded(m64, theta, base, tmin, tmax)
        out["designs"][name] = {"C1111_wide": c, "FE": ref,
                                "dev_wide_pct": (c / ref - 1) * 100, "vf": vf}
        print(f"WIDE  {name}: C1111={c:.4f}  dev={100*(c/ref-1):+.1f}%  vf={vf:.5f}")

    json.dump(out, open(os.path.join(HERE, "e3_wide_audit.json"), "w"), indent=2)
    print("wrote e3_wide_audit.json")

if __name__ == "__main__":
    main()
