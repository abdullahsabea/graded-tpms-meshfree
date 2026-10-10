"""Verify the analytic design sensitivities of the soft objective
Eq. (12) of the manuscript: dU/dtheta_m and dVf/dtheta_m by autodiff
through the frozen conditional network + smoothed membership, against
central finite differences on the SAME fixed Monte Carlo cloud (so the
comparison is a pure calculus check, free of sampling noise).

Runs in float64. Tests theta = 0 (uniform, clamp inactive), a moderate
interior point, and the saved unconstrained optimum theta* (clamp
active on part of the domain).

Usage: python verify_gradients.py [N_points]
"""
import json
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pylibs"))

import e3_conditional as ec
import e3_optimize as eo

HERE = os.path.dirname(os.path.abspath(__file__))


def build(N):
    torch.set_default_dtype(torch.float64)
    model = ec.make_model()
    model.load_state_dict(
        torch.load(ec.CKPT, weights_only=True, map_location="cpu"))
    model.double()
    for p in model.parameters():
        p.requires_grad_(False)

    def full_xt(xt):
        x, t = xt[..., :3], xt[..., 3:4]
        z = torch.cat([torch.sin(x @ model.B), torch.cos(x @ model.B), t], dim=-1)
        u = model.net(z)
        d = ec.d_cube(x)
        aff = torch.stack([ec.EPS * x[..., 0],
                           torch.zeros_like(x[..., 0]),
                           torch.zeros_like(x[..., 0])], dim=-1)
        return d * u + aff

    from torch.func import vmap, jacrev

    def strain_energy_density(xt):
        du = vmap(jacrev(full_xt))(xt)[:, :, :3]
        exx, eyy, ezz = du[:, 0, 0], du[:, 1, 1], du[:, 2, 2]
        exy = 0.5 * (du[:, 0, 1] + du[:, 1, 0])
        exz = 0.5 * (du[:, 0, 2] + du[:, 2, 0])
        eyz = 0.5 * (du[:, 1, 2] + du[:, 2, 1])
        tr = exx + eyy + ezz
        e2 = exx**2 + eyy**2 + ezz**2 + 2 * (exy**2 + exz**2 + eyz**2)
        return 0.5 * (ec.LAM * tr**2 + 2 * ec.MU * e2)

    g = torch.Generator().manual_seed(11)          # same cloud/seed as e3_optimize
    pts = torch.rand(N, 3, generator=g)
    absF = torch.abs(ec.Fval(pts))
    psiv = eo.psi(pts)

    def U_vf(theta):
        tx = (eo.T0 + psiv @ theta).clamp(eo.T_MIN, eo.T_MAX)
        w = torch.sigmoid((tx - absF) / eo.TAU)
        xt = torch.cat([pts, tx.unsqueeze(-1)], dim=-1)
        dens = strain_energy_density(xt)
        return (w * dens).mean(), w.mean()

    return U_vf


def check(name, theta0, U_vf, hs=(1e-3, 1e-4)):
    theta0 = torch.as_tensor(theta0, dtype=torch.float64)
    print(f"\n=== {name} ===")
    for label, fn in (("dU/dtheta", 0), ("dVf/dtheta", 1)):
        th = theta0.clone().requires_grad_(True)
        out = U_vf(th)
        out[fn].backward()
        g_analytic = th.grad.clone()
        for h in hs:
            g_fd = torch.zeros_like(theta0)
            for m in range(len(theta0)):
                e = torch.zeros_like(theta0); e[m] = h
                up, vp = U_vf(theta0 + e)
                um, vm = U_vf(theta0 - e)
                g_fd[m] = ((up - um) if fn == 0 else (vp - vm)) / (2 * h)
            err = (g_analytic - g_fd).abs()
            scale = g_fd.abs().max().item() + 1e-30
            print(f"  {label}  h={h:.0e}: max|analytic-FD| = {err.max().item():.3e}"
                  f"   max rel (vs max|FD|) = {err.max().item()/scale:.3e}")
        print(f"  {label}  analytic range: [{g_analytic.min().item():+.4e}, "
              f"{g_analytic.max().item():+.4e}]")


def main():
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 20_000
    U_vf = build(N)

    theta_star = torch.tensor(
        json.load(open(os.path.join(HERE, "e3_opt_result.json")))["theta"])

    with torch.no_grad():
        u0, v0 = U_vf(torch.zeros(eo.N_MODES, dtype=torch.float64))
    print(f"cloud N={N}  uniform baseline: U={float(u0):.6f}  Vf={float(v0):.5f}")

    check("theta = 0 (uniform t=0.30, clamp inactive)",
          torch.zeros(eo.N_MODES), U_vf)
    check("theta = 0.01*ones (interior, clamp inactive)",
          0.01 * torch.ones(eo.N_MODES), U_vf)
    check("theta = theta* (unconstrained optimum, clamp active)",
          theta_star, U_vf, hs=(1e-4,))


if __name__ == "__main__":
    main()
