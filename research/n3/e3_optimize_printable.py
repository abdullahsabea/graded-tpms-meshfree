"""E3c: manufacturability-constrained variant of the E3 grading optimization.

Same objective as e3_optimize.py (maximize C1111 at fixed Vf), but with two
changes aimed at preserving the gyroid's self-supporting property, which the
unconstrained design (t in [0.12,0.55]) forfeits locally:

1. Thickness bounds narrowed to [0.20, 0.45] -- both anchors already verified
   against voxel FEM in the N2/N3 gates (Table 3 of the paper), instead of
   the full [0.12,0.55] band.
2. An explicit smoothness penalty on the ANALYTIC spatial gradient of the
   unclipped thickness field, lambda_grad * mean(|grad_x t(x)|^2). The
   level-set gradient is grad(phi) = sign(F) k grad(F) - grad(t); a large
   |grad(t)| is exactly the mechanism that tilts the surface normal toward
   horizontal and creates local overhangs the base (ungraded) gyroid never
   has. grad(t) is linear in theta and closed-form in x (no autodiff
   needed), matching the paper's analytic-sensitivity approach.

Usage: python e3_optimize_printable.py [iters]
Outputs: e3_opt_result_printable.json, e3_opt_history_printable.json
"""
import json, os, sys, time
import numpy as np
import torch   # use the working system install; local pylibs/torch DLLs are stale
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import e3_conditional as ec

HERE = os.path.dirname(__file__)
T0 = 0.30
VF_TARGET = ec.vf_of(T0)
T_MIN, T_MAX = 0.20, 0.45        # narrowed: both anchors N2/N3-verified
TAU = 0.02
LAM_VF = 200.0
LAM_GRAD = 0.0012                # smoothness penalty weight (calibrated: costs
                                  # ~30% of the unconstrained gain at the
                                  # unconstrained solution's own smoothness scale)

MODES = [(1,0,0),(0,1,0),(0,0,1),(1,1,0),(1,0,1),(0,1,1)]
N_MODES = 2 * len(MODES)

def psi_and_grad(x):
    """psi_m(x) and its exact spatial gradient, closed form."""
    cols, grads = [], []
    for (a, b, c) in MODES:
        nvec = torch.tensor([a, b, c], dtype=x.dtype)
        ph = 2*np.pi*(a*x[:, 0] + b*x[:, 1] + c*x[:, 2])
        cols.append(torch.cos(ph))
        grads.append(-2*np.pi*torch.sin(ph).unsqueeze(-1) * nvec)
        cols.append(torch.sin(ph))
        grads.append(2*np.pi*torch.cos(ph).unsqueeze(-1) * nvec)
    return torch.stack(cols, dim=-1), torch.stack(grads, dim=1)  # (N,M), (N,M,3)

def t_field(x, theta):
    tx = T0 + psi_and_grad(x)[0] @ theta
    return tx.clamp(T_MIN, T_MAX)

def main():
    iters = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    torch.set_default_dtype(torch.float32)
    torch.manual_seed(3)

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

    def strain_xt(xt):
        from torch.func import vmap, jacrev
        du = vmap(jacrev(full_xt))(xt)[:, :, :3]
        exx, eyy, ezz = du[:, 0, 0], du[:, 1, 1], du[:, 2, 2]
        exy = 0.5 * (du[:, 0, 1] + du[:, 1, 0])
        exz = 0.5 * (du[:, 0, 2] + du[:, 2, 0])
        eyz = 0.5 * (du[:, 1, 2] + du[:, 2, 1])
        tr = exx + eyy + ezz
        e2 = exx**2 + eyy**2 + ezz**2 + 2*(exy**2 + exz**2 + eyz**2)
        return 0.5 * (ec.LAM * tr**2 + 2*ec.MU * e2)

    g = torch.Generator().manual_seed(11)
    pts = torch.rand(50_000, 3, generator=g)
    absF = torch.abs(ec.Fval(pts))
    psiv, gpsiv = psi_and_grad(pts)             # (N,12), (N,12,3) -- fixed, reused every eval

    theta = torch.zeros(N_MODES, requires_grad=True)
    opt = torch.optim.Adam([theta], lr=3e-3)

    def objective(theta):
        tx_raw = T0 + psiv @ theta
        tx = tx_raw.clamp(T_MIN, T_MAX)
        w = torch.sigmoid((tx - absF) / TAU)
        xt = torch.cat([pts, tx.unsqueeze(-1)], dim=-1)
        dens = strain_xt(xt)
        U = (w * dens).mean()
        vf = w.mean()
        c = 2 * U / ec.EPS**2
        grad_t = torch.einsum('m,nmc->nc', theta, gpsiv)   # (N,3), linear in theta
        smooth_pen = (grad_t**2).sum(dim=-1).mean()
        loss = -U + LAM_VF*(vf - VF_TARGET)**2 + LAM_GRAD*smooth_pen
        return loss, c, vf, U, smooth_pen

    with torch.no_grad():
        _, c0, vf0, _, s0 = objective(torch.zeros(N_MODES))
    print(f"BASELINE uniform t={T0}: C1111={float(c0):.4f}  Vf={float(vf0):.4f}  "
          f"(target {VF_TARGET:.4f})")

    hist = []
    t0time = time.time()
    for it in range(iters):
        opt.zero_grad()
        loss, c, vf, U, sp = objective(theta)
        loss.backward()
        opt.step()
        if it % 10 == 0 or it == iters - 1:
            hist.append(dict(it=it, C1111=float(c), Vf=float(vf), loss=float(loss),
                             smooth=float(sp)))
            print(f"it {it:4d}  C1111={float(c):.4f}  Vf={float(vf):.4f}  "
                  f"smooth={float(sp):.4f}  ({time.time()-t0time:.0f}s)", flush=True)

    # gradient-free coordinate polish, same protocol as e3_optimize.py, now
    # scoring candidates on C1111 penalized by the smoothness term so the
    # polish cannot re-introduce steep local grading
    theta_np = theta.detach().clone()
    grid = torch.linspace(-0.22, 0.22, 9)
    for sweep in range(2):
        for m in range(N_MODES):
            best_val, best_score = float(theta_np[m]), -1e9
            for cand in grid:
                trial = theta_np.clone(); trial[m] = cand
                with torch.no_grad():
                    tx_raw = T0 + psiv @ trial
                    # bisection on a uniform shift to hit VF_TARGET exactly
                    lo, hi = -0.3, 0.3
                    for _ in range(30):
                        mid = 0.5*(lo+hi)
                        vf_mid = torch.sigmoid(((tx_raw+mid).clamp(T_MIN,T_MAX)-absF)/TAU).mean()
                        if vf_mid < VF_TARGET: lo = mid
                        else: hi = mid
                    shift = 0.5*(lo+hi)
                    tx = (tx_raw + shift).clamp(T_MIN, T_MAX)
                    w = torch.sigmoid((tx - absF)/TAU)
                    xt = torch.cat([pts, tx.unsqueeze(-1)], dim=-1)
                    U = (w * strain_xt(xt)).mean()
                    c = 2*U/ec.EPS**2
                    grad_t = torch.einsum('m,nmc->nc', trial, gpsiv)
                    sp = (grad_t**2).sum(dim=-1).mean()
                    score = float(c) - LAM_GRAD*float(sp)
                if score > best_score:
                    best_score, best_val, best_shift = score, float(cand), float(shift)
            theta_np[m] = best_val
        print(f"sweep {sweep} done", flush=True)

    with torch.no_grad():
        tx_raw = T0 + psiv @ theta_np
        lo, hi = -0.3, 0.3
        for _ in range(40):
            mid = 0.5*(lo+hi)
            vf_mid = torch.sigmoid(((tx_raw+mid).clamp(T_MIN,T_MAX)-absF)/TAU).mean()
            if vf_mid < VF_TARGET: lo = mid
            else: hi = mid
        shift = 0.5*(lo+hi)
        tx = (tx_raw + shift).clamp(T_MIN, T_MAX)
        w = torch.sigmoid((tx - absF)/TAU)
        xt = torch.cat([pts, tx.unsqueeze(-1)], dim=-1)
        U = (w * strain_xt(xt)).mean()
        c_final = float(2*U/ec.EPS**2)
        vf_final = float(w.mean())
        grad_t = torch.einsum('m,nmc->nc', theta_np, gpsiv)
        sp_final = float((grad_t**2).sum(dim=-1).mean())

    print(f"FINAL: C1111={c_final:.4f}  Vf={vf_final:.4f}  smooth_pen={sp_final:.4f}  "
          f"gain={100*(c_final/float(c0)-1):.1f}%")

    result = dict(C1111_baseline=float(c0), Vf_target=VF_TARGET, C1111_final=c_final,
                  Vf_final=vf_final, smooth_pen=sp_final, theta=theta_np.tolist(),
                  modes=MODES, t0=T0, t_min=T_MIN, t_max=T_MAX, tau=TAU,
                  t0shift=shift, lam_grad=LAM_GRAD)
    json.dump(result, open(os.path.join(HERE, "e3_opt_result_printable.json"), "w"), indent=2)
    json.dump(hist, open(os.path.join(HERE, "e3_opt_history_printable.json"), "w"), indent=2)
    print("saved e3_opt_result_printable.json")

if __name__ == "__main__":
    main()
