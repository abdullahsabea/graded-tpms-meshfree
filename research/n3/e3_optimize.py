"""E3b: mesh-free topology optimization of the gyroid thickness field t(x).

Objective: maximize directional stiffness C1111 (KUBC eps_xx) at FIXED volume
fraction Vf* = Vf(t=0.3 uniform) = 0.1934.
Design variables: coefficients theta of a low-frequency Fourier grading field
    t(x) = clip( t0 + sum_m theta_m psi_m(x),  T_MIN, T_MAX )
Physics: conditional DEM u(x,t) from e3_conditional.py (checkpoint e3_cond.pt).
Domain integration: fixed MC point cloud over the cube with smoothed
membership w = sigmoid((t(x)-|F(kx)|)/tau)  -> analytic d()/dtheta.

Usage: python e3_optimize.py [iters]
Outputs: e3_opt_result.json, e3_opt_history.json, e3_opt_theta.pt
"""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pylibs"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import torch

import e3_conditional as ec   # model builders, physics constants

HERE = os.path.dirname(__file__)
T0 = 0.30
VF_TARGET = ec.vf_of(T0)          # 0.1934
T_MIN, T_MAX = 0.12, 0.55
TAU = 0.02                        # sigmoid sharpness in |F| units
LAM_VF = 200.0                    # volume-constraint penalty

# Fourier grading basis psi_m(x): first harmonics, period 1
MODES = [(1,0,0),(0,1,0),(0,0,1),(1,1,0),(1,0,1),(0,1,1)]
N_MODES = 2 * len(MODES)          # cos+sin per mode

def psi(x):
    cols = []
    for (a,b,c) in MODES:
        ph = 2*np.pi*(a*x[...,0] + b*x[...,1] + c*x[...,2])
        cols += [torch.cos(ph), torch.sin(ph)]
    return torch.stack(cols, dim=-1)          # (N, M)

def t_field(x, theta):
    tx = T0 + psi(x) @ theta
    return tx.clamp(T_MIN, T_MAX)

def main():
    iters = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    torch.set_default_dtype(torch.float32)
    torch.manual_seed(3)

    # physics model (frozen)
    model = ec.make_model()
    model.load_state_dict(torch.load(ec.CKPT, weights_only=True))
    for p in model.parameters():
        p.requires_grad_(False)
    rawfwd = model.forward
    def raw_net(x, t):
        # bypass the patched forward: raw MLP output only (no BC wrapper)
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
    def strain_xt(xt):
        from torch.func import vmap, jacrev
        du = vmap(jacrev(full_xt))(xt)[:, :, :3]
        exx, eyy, ezz = du[:, 0, 0], du[:, 1, 1], du[:, 2, 2]
        exy = 0.5 * (du[:, 0, 1] + du[:, 1, 0])
        exz = 0.5 * (du[:, 0, 2] + du[:, 2, 0])
        eyz = 0.5 * (du[:, 1, 2] + du[:, 2, 1])
        tr = exx + eyy + ezz
        e2 = exx**2 + eyy**2 + ezz**2 + 2 * (exy**2 + exz**2 + eyz**2)
        return 0.5 * (ec.LAM * tr**2 + 2 * ec.MU * e2)

    # fixed MC cloud + |F| values
    g = torch.Generator().manual_seed(11)
    pts = torch.rand(50_000, 3, generator=g)
    absF = torch.abs(ec.Fval(pts))
    psiv = psi(pts)

    theta = torch.zeros(N_MODES, requires_grad=True)
    opt = torch.optim.Adam([theta], lr=3e-3)

    def objective(theta):
        tx = (T0 + psiv @ theta).clamp(T_MIN, T_MAX)
        w = torch.sigmoid((tx - absF) / TAU)
        xt = torch.cat([pts, tx.unsqueeze(-1)], dim=-1)
        dens = strain_xt(xt)
        U = (w * dens).mean()
        vf = w.mean()
        c = 2 * U / ec.EPS**2
        loss = -U + LAM_VF * (vf - VF_TARGET)**2
        return loss, c, vf, U

    # baseline
    with torch.no_grad():
        _, c0, vf0, _ = objective(torch.zeros(N_MODES))
    print(f"BASELINE uniform t={T0}: C1111={float(c0):.4f}  Vf={float(vf0):.4f} (target {VF_TARGET:.4f})")

    hist = []
    t0time = time.time()
    for it in range(iters):
        opt.zero_grad()
        loss, c, vf, U = objective(theta)
        loss.backward()
        opt.step()
        if it % 10 == 0 or it == iters - 1:
            hist.append(dict(it=it, C1111=float(c), Vf=float(vf), loss=float(loss)))
            print(f"it {it:4d}  C1111={float(c):.4f}  Vf={float(vf):.4f}  ({time.time()-t0time:.0f}s)", flush=True)

    theta_opt = theta.detach()
    torch.save(theta_opt, os.path.join(HERE, "e3_opt_theta.pt"))
    json.dump(hist, open(os.path.join(HERE, "e3_opt_history.json"), "w"), indent=2)

    # --- hard-domain audit of the optimized graded cell ---
    def sample_graded(n, theta, seed):
        g2 = torch.Generator().manual_seed(seed)
        out, need = [], n
        while need > 0:
            cand = torch.rand(4 * need, 3, generator=g2)
            keep = torch.abs(ec.Fval(cand)) < t_field(cand, theta)
            got = cand[keep]
            out.append(got[:need]); need -= min(len(got), need)
        return torch.cat(out)[:n]

    with torch.no_grad():
        for name, th in (("uniform", torch.zeros(N_MODES)), ("optimized", theta_opt)):
            pts_h = sample_graded(40_000, th, seed=99)
            tx = t_field(pts_h, th)
            xt = torch.cat([pts_h, tx.unsqueeze(-1)], dim=-1)
            dens = strain_xt(xt)
            vf_est = len(pts_h) / (4 * 40_000) * (4 * 40_000)  # placeholder, recompute below
            # acceptance-based Vf:
            g2 = torch.Generator().manual_seed(5)
            cand = torch.rand(200_000, 3, generator=g2)
            vf_acc = (torch.abs(ec.Fval(cand)) < t_field(cand, th)).float().mean().item()
            U = dens.mean().item() * vf_acc
            c = 2 * U / ec.EPS**2
            print(f"HARD AUDIT {name}: C1111={c:.4f}  Vf={vf_acc:.4f}")

    result = dict(C1111_baseline=float(c0), Vf_target=VF_TARGET,
                  theta=theta_opt.tolist(), modes=MODES, t0=T0,
                  t_min=T_MIN, t_max=T_MAX, tau=TAU)
    json.dump(result, open(os.path.join(HERE, "e3_opt_result.json"), "w"), indent=2)
    print("saved e3_opt_result.json / e3_opt_history.json / e3_opt_theta.pt")

if __name__ == "__main__":
    main()
