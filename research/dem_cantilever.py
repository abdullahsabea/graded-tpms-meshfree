"""
N2 — Deep Energy Method (DEM) elasticity solver, validated against FEM
======================================================================
Purpose: prove the physics engine BEFORE any TPMS coupling. If a mesh-free
energy-minimizing neural field cannot reproduce a cantilever to ~1%, nothing
downstream is defensible. This is the go/no-go gate of the methodology.

Problem (classical 2D cantilever, plane stress):
  domain  [0,L] x [0,H], L=2, H=1, E=1, nu=0.3
  clamped left edge x=0 (hard BC via distance function: u = x * N(x))
  parabolic shear traction on right edge x=L (resultant P=1 downward):
      t_y(y) = -P/(2I) * (H^2/4 - (y-H/2)^2),  I = H^3/12
  => exact traction-free top/bottom, well-posed for energy methods.

Method (DEM):
  u_w(x): Fourier-feature MLP, trained by minimizing
      Pi(u) = ∫_Ω 1/2 eps:C:eps dΩ - ∫_ΓN t·u dΓ
  with 2x2 Gauss quadrature on a structured integration grid.
  Adam pre-training + L-BFGS polish. NO finite differences anywhere.

Reference: Q4 plane-stress FEM on a fine mesh (160x80), plus Timoshenko
beam-theory tip deflection as an independent order-of-magnitude check.

Outputs: research/figures/dem_*.png, research/n2_metrics.json
Pass criteria (recorded in the verification report):
  |U_DEM - U_FEM| / U_FEM < 2 %
  displacement L2 relative error    < 5 %
"""
import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "pylibs"))
import numpy as np
import torch
import torch.nn as nn
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

torch.manual_seed(0)
torch.set_default_dtype(torch.float64)  # physics in double precision
DEV = "cpu"

# ---------------- problem data ----------------
L, H, E, NU, P = 2.0, 1.0, 1.0, 0.3, 1.0
I = H**3 / 12.0
C = E / (1 - NU**2) * torch.tensor([[1, NU, 0], [NU, 1, 0], [0, 0, (1 - NU) / 2]])

def traction_y(y):
    """Parabolic shear traction on x=L, resultant -P."""
    return -P / (2 * I) * (H**2 / 4 - (y - H / 2) ** 2)

# ---------------- FEM reference (Q4 plane stress) ----------------
def fem_reference(nelx=160, nely=80):
    hx, hy = L / nelx, H / nely
    nnx, nny = nelx + 1, nely + 1
    ndof = 2 * nnx * nny
    # Q4 stiffness (plane stress), standard 2x2 Gauss integration
    gp = 1 / np.sqrt(3)
    KE = np.zeros((8, 8))
    Cn = C.numpy()
    for xi, eta in [(a, b) for a in (-gp, gp) for b in (-gp, gp)]:
        dN = 0.25 * np.array([
            [-(1 - eta), (1 - eta), (1 + eta), -(1 + eta)],
            [-(1 - xi), -(1 + xi), (1 + xi), (1 - xi)]])
        J = np.array([[hx / 2, 0], [0, hy / 2]])
        dNdx = np.linalg.inv(J) @ dN
        B = np.zeros((3, 8))
        B[0, 0::2] = dNdx[0]; B[1, 1::2] = dNdx[1]
        B[2, 0::2] = dNdx[1]; B[2, 1::2] = dNdx[0]
        KE += B.T @ Cn @ B * np.linalg.det(J)
    # assembly
    node = lambda i, j: j * nnx + i
    rows, cols, vals = [], [], []
    for i in range(nelx):
        for j in range(nely):
            n = [node(i, j), node(i + 1, j), node(i + 1, j + 1), node(i, j + 1)]
            ed = np.array([[2 * q, 2 * q + 1] for q in n]).flatten()
            for a in range(8):
                for b in range(8):
                    rows.append(ed[a]); cols.append(ed[b]); vals.append(KE[a, b])
    from scipy.sparse import coo_matrix
    from scipy.sparse.linalg import spsolve
    K = coo_matrix((vals, (rows, cols)), shape=(ndof, ndof)).tocsc()
    # load: parabolic traction on right edge via consistent nodal loads
    F = np.zeros(ndof)
    ys = np.linspace(0, H, nny)
    fy = traction_y(ys) * hy
    for j in range(nny):
        w = 0.5 if j in (0, nny - 1) else 1.0
        F[2 * node(nelx, j) + 1] += fy[j] * w
    # clamp left edge
    fixed = np.array([[2 * node(0, j), 2 * node(0, j) + 1] for j in range(nny)]).flatten()
    free = np.setdiff1d(np.arange(ndof), fixed)
    U = np.zeros(ndof)
    U[free] = spsolve(K[free][:, free].tocsc(), F[free])
    Ue = U.reshape(-1, 2)
    energy = 0.5 * U @ (K @ U)
    tip = Ue[node(nelx, nny // 2), 1]
    xs = np.linspace(0, L, nnx); ysg = np.linspace(0, H, nny)
    return dict(U=Ue, xs=xs, ys=ysg, energy=float(energy), tip=float(tip), nelx=nelx, nely=nely)

# ---------------- DEM model ----------------
class FourierMLP(nn.Module):
    def __init__(self, width=128, depth=4, sigma=3.0):
        super().__init__()
        B = torch.randn(2, width // 2) * sigma
        self.register_buffer("B", B)
        layers, d = [], width
        for _ in range(depth):
            layers += [nn.Linear(d, width), nn.Tanh()]
            d = width
        layers += [nn.Linear(width, 2)]
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        z = torch.cat([torch.sin(x @ self.B), torch.cos(x @ self.B)], dim=-1)
        return self.net(z)

def build_integration_grid(nx=48, ny=24):
    """2x2 Gauss points/weights per cell on a structured grid (for energy)."""
    gp = 1 / np.sqrt(3)
    gx = (np.arange(nx) + 0.5) / nx * L
    gy = (np.arange(ny) + 0.5) / ny * H
    ox = np.array([-gp, gp]) * L / nx / 2
    oy = np.array([-gp, gp]) * H / ny / 2
    pts, wts = [], []
    for i in range(nx):
        for j in range(ny):
            for a in range(2):
                for b in range(2):
                    pts.append([gx[i] + ox[a], gy[j] + oy[b]])
                    wts.append((L / nx / 2) * (H / ny / 2))
    return torch.tensor(pts), torch.tensor(wts)

def boundary_quad(nq=100):
    """Gauss-Legendre points on the loaded edge x=L (for external work)."""
    xg, wg = np.polynomial.legendre.leggauss(nq)
    ys = (xg + 1) / 2 * H
    return torch.tensor(np.column_stack([np.full(nq, L), ys])), torch.tensor(wg * H / 2)

from torch.func import jacrev, vmap

def energy_loss(model, pts, wts, bpts, bwts):
    du = vmap(jacrev(model))(pts)  # (N, 2, 2) per-point displacement Jacobian
    exx = du[:, 0, 0]; eyy = du[:, 1, 1]
    exy = 0.5 * (du[:, 0, 1] + du[:, 1, 0])
    sxx = C[0, 0] * exx + C[0, 1] * eyy
    syy = C[1, 0] * exx + C[1, 1] * eyy
    sxy = C[2, 2] * exy
    dens = 0.5 * (sxx * exx + syy * eyy + 2 * sxy * exy)
    internal = (dens * wts).sum()
    ub = model(bpts)
    external = (traction_y(bpts[:, 1]) * ub[:, 1] * bwts).sum()
    return internal - external, internal, external

def main():
    t0 = time.time()
    print("FEM reference (160x80 Q4)...")
    fem = fem_reference()
    d_beam = P * L**3 / (3 * E * I) + 6 * P * L * (1 + NU) / (5 * E * H)  # Timoshenko
    print(f"  FEM strain energy U = {fem['energy']:.6f}   tip uy = {fem['tip']:.6f}")
    print(f"  Timoshenko beam tip = {-d_beam:.6f} (order check only)")

    model = FourierMLP(sigma=1.0).to(DEV)  # low sigma: smooth field, no hourglassable modes
    hard = lambda x, u: torch.stack([x[..., 0] * u[..., 0], x[..., 0] * u[..., 1]], dim=-1)  # u=0 at x=0
    raw_forward = model.forward
    model.forward = lambda x: hard(x, raw_forward(x))

    AREA = L * H
    N_MC, NB_MC = 6000, 200

    def mc_loss():
        """Randomized (Monte-Carlo) energy: fresh points each call -> unbiased,
        prevents the NN from exploiting a fixed quadrature (hourglassing)."""
        pts = torch.rand(N_MC, 2) * torch.tensor([L, H])
        wts = torch.full((N_MC,), AREA / N_MC)
        bpts = torch.cat([torch.full((NB_MC, 1), L), torch.rand(NB_MC, 1) * H], dim=1)
        bwts = torch.full((NB_MC,), H / NB_MC)
        return energy_loss(model, pts, wts, bpts, bwts)

    hist = []
    opt = torch.optim.Adam(model.parameters(), lr=2e-3)
    ADAM_IT, LBFGS_IT = 2200, 80
    for it in range(ADAM_IT):
        opt.zero_grad()
        loss, internal, external = mc_loss()
        loss.backward(); opt.step()
        if it % 500 == 0 or it == ADAM_IT - 1:
            hist.append((it, float(internal.detach())))
            print(f"  Adam {it:5d}  Pi={float(loss): .5f}  U={float(internal): .5f}  W={float(external): .5f}", flush=True)

    # fixed dense grid for the deterministic LBFGS polish
    pts, wts = build_integration_grid(64, 32)
    bpts, bwts = boundary_quad()
    opt2 = torch.optim.LBFGS(model.parameters(), max_iter=LBFGS_IT, tolerance_grad=1e-9,
                             tolerance_change=1e-12, history_size=20, line_search_fn="strong_wolfe")
    it_state = [0]
    def closure():
        opt2.zero_grad()
        loss, internal, _ = energy_loss(model, pts, wts, bpts, bwts)
        loss.backward()
        if it_state[0] % 50 == 0:
            print(f"  LBFGS {it_state[0]:4d}  Pi={float(loss): .5f}  U={float(internal): .5f}", flush=True)
        it_state[0] += 1
        return loss
    opt2.step(closure)

    # --- final energy (training quadrature AND fine independent quadrature) ---
    with torch.enable_grad():
        _, U_dem, _ = energy_loss(model, pts, wts, bpts, bwts)
    U_dem = float(U_dem)
    fpts, fwts = build_integration_grid(160, 80)
    with torch.enable_grad():
        _, U_dem_fine, _ = energy_loss(model, fpts, fwts, bpts, bwts)
    U_dem_fine = float(U_dem_fine)
    print(f"  quadrature audit: U(train grid 48x24) = {U_dem:.4f} | U(fine grid 160x80) = {U_dem_fine:.4f}")

    # --- field comparison on FEM nodes (node n = j*nnx+i => reshape (nny,nnx).T) ---
    nnx, nny = fem["nelx"] + 1, fem["nely"] + 1
    Xg, Yg = np.meshgrid(fem["xs"], fem["ys"], indexing="ij")
    xy = torch.tensor(np.column_stack([Xg.ravel(), Yg.ravel()]))
    with torch.no_grad():
        u_dem = model(xy).numpy().reshape(nnx, nny, 2)
    u_fem = fem["U"].reshape(nny, nnx, 2).transpose(1, 0, 2)
    num = np.sqrt(((u_dem - u_fem) ** 2).sum())
    den = np.sqrt((u_fem ** 2).sum())
    l2_rel = float(num / den)

    e_err = abs(U_dem - fem["energy"]) / fem["energy"]
    print(f"\nRESULTS ({time.time()-t0:.0f}s)")
    print(f"  U_DEM = {U_dem:.6f}  vs U_FEM = {fem['energy']:.6f}  rel.err = {100*e_err:.2f}%")
    print(f"  displacement L2 rel.err = {100*l2_rel:.2f}%")

    metrics = dict(U_fem=fem["energy"], U_dem=U_dem, U_dem_fine_quad=U_dem_fine,
                   energy_rel_err=e_err,
                   l2_rel=l2_rel, tip_fem=fem["tip"], tip_beam=-d_beam,
                   adam_iters=ADAM_IT, lbfgs_iters=LBFGS_IT,
                   grid=[80, 40], fourier_sigma=3.0, width=128, depth=4,
                   pass_energy=bool(e_err < 0.02), pass_l2=bool(l2_rel < 0.05))
    json.dump(metrics, open("n2_metrics.json", "w"), indent=2)

    # --- figures ---
    os.makedirs("figures", exist_ok=True)
    fig, axes = plt.subplots(2, 3, figsize=(15, 7))
    for row, (d, name) in enumerate([(1, "u_y"), (0, "u_x")]):
        a, b, c = axes[row]
        im0 = a.pcolormesh(Xg, Yg, u_fem[:, :, d], shading="auto", cmap="RdBu_r"); a.set_title(f"FEM {name}")
        im1 = b.pcolormesh(Xg, Yg, u_dem[:, :, d], shading="auto", cmap="RdBu_r"); b.set_title(f"DEM {name}")
        im2 = c.pcolormesh(Xg, Yg, np.abs(u_dem - u_fem)[:, :, d], shading="auto", cmap="viridis"); c.set_title("|err|")
        for ax, im in zip((a, b, c), (im0, im1, im2)):
            ax.set_aspect("equal"); plt.colorbar(im, ax=ax, fraction=0.046)
    fig.suptitle(f"N2 gate: DEM vs FEM cantilever — energy err {100*e_err:.2f}%, L2 err {100*l2_rel:.2f}%")
    fig.tight_layout(); fig.savefig("figures/dem_vs_fem_fields.png", dpi=150)

    fig2, ax2 = plt.subplots(figsize=(7, 4))
    its, us = zip(*hist)
    ax2.plot(its, us, label="DEM strain energy (Adam)")
    ax2.axhline(fem["energy"], color="r", ls="--", label="FEM reference")
    ax2.set_xlabel("iteration"); ax2.set_ylabel("U"); ax2.legend(); ax2.grid(alpha=0.3)
    fig2.tight_layout(); fig2.savefig("figures/dem_energy_convergence.png", dpi=150)
    print("Saved figures/dem_vs_fem_fields.png, figures/dem_energy_convergence.png, n2_metrics.json")

if __name__ == "__main__":
    main()
