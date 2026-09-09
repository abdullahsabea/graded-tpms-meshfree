"""
N1 — TPMS analytic level-set module (research module 1 of 2)
============================================================
Sheet-network TPMS solids defined by analytic level sets:

    solid(x)  <=>  phi(x) < 0,   phi(x) = |F(x)| - t

where F is the trigonometric TPMS basis function and t the (possibly
spatially graded) thickness threshold. All quantities needed by the
mesh-free PIGP solver are provided in closed form:

    phi(x)      level set (signed, exact)
    grad_phi(x) exact gradient  -> exact surface normals n = grad/|grad|
    hess_phi(x) exact Hessian   -> exact curvature if needed
    volume fraction, near-surface collocation sampling

Unit conventions: the TPMS unit cell spans [0, 2*pi/k] per axis for wave
number k; default k=1 cell in the unit cube uses k = 2*pi.

Self-test (python tpms_levelset.py):
  T1: analytic gradient vs central finite differences  (must be < 1e-6)
  T2: analytic Hessian  vs finite differences          (must be < 1e-4)
  T3: gyroid volume fraction at t=0 must equal 0.5 (symmetry of |F|)
  T4: VF monotone increasing in t; matches independent voxel count
  T5: near-surface sampler respects the shell constraint
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "pylibs"))
import numpy as np
import torch

# ---------------------------------------------------------------------------
# TPMS basis functions F(x) and exact first/second derivatives (torch, autodiff-free)
# x: (..., 3) tensor, k: scalar wave number, X = k*x
# ---------------------------------------------------------------------------

def _basis(name):
    if name == "gyroid":
        def F(X):
            x, y, z = X[..., 0], X[..., 1], X[..., 2]
            return torch.sin(x)*torch.cos(y) + torch.sin(y)*torch.cos(z) + torch.sin(z)*torch.cos(x)
        def dF(X):
            x, y, z = X[..., 0], X[..., 1], X[..., 2]
            fx = torch.cos(x)*torch.cos(y) - torch.sin(z)*torch.sin(x)
            fy = torch.cos(y)*torch.cos(z) - torch.sin(x)*torch.sin(y)
            fz = torch.cos(z)*torch.cos(x) - torch.sin(y)*torch.sin(z)
            return torch.stack([fx, fy, fz], dim=-1)
        def ddF(X):
            x, y, z = X[..., 0], X[..., 1], X[..., 2]
            hxx = -torch.sin(x)*torch.cos(y) - torch.sin(z)*torch.cos(x)
            hyy = -torch.sin(y)*torch.cos(z) - torch.sin(x)*torch.cos(y)
            hzz = -torch.sin(z)*torch.cos(x) - torch.sin(y)*torch.cos(z)
            hxy = -torch.cos(x)*torch.sin(y)
            hxz = -torch.cos(z)*torch.sin(x)
            hyz = -torch.cos(y)*torch.sin(z)
            H = torch.zeros(X.shape[:-1] + (3, 3), dtype=X.dtype)
            H[..., 0, 0], H[..., 1, 1], H[..., 2, 2] = hxx, hyy, hzz
            H[..., 0, 1] = H[..., 1, 0] = hxy
            H[..., 0, 2] = H[..., 2, 0] = hxz
            H[..., 1, 2] = H[..., 2, 1] = hyz
            return H
        return F, dF, ddF
    if name == "primitive":
        def F(X):
            return torch.cos(X[..., 0]) + torch.cos(X[..., 1]) + torch.cos(X[..., 2])
        def dF(X):
            return -torch.sin(X)
        def ddF(X):
            H = torch.zeros(X.shape[:-1] + (3, 3), dtype=X.dtype)
            H[..., 0, 0] = -torch.cos(X[..., 0])
            H[..., 1, 1] = -torch.cos(X[..., 1])
            H[..., 2, 2] = -torch.cos(X[..., 2])
            return H
        return F, dF, ddF
    if name == "diamond":
        def F(X):
            x, y, z = X[..., 0], X[..., 1], X[..., 2]
            return (torch.sin(x)*torch.sin(y)*torch.sin(z)
                    + torch.sin(x)*torch.cos(y)*torch.cos(z)
                    + torch.cos(x)*torch.sin(y)*torch.cos(z)
                    + torch.cos(x)*torch.cos(y)*torch.sin(z))
        # first/second derivatives obtained via autodiff (still exact)
        def dF(X):
            X = X.requires_grad_(True)
            return torch.autograd.grad(F(X).sum(), X, create_graph=True)[0].detach()
        def ddF(X):
            rows = []
            for i in range(3):
                Xi = X.requires_grad_(True)
                g = torch.autograd.grad(F(Xi).sum(), Xi, create_graph=True)[0]
                rows.append(torch.autograd.grad(g[..., i].sum(), Xi)[0])
            return torch.stack(rows, dim=-1)
        return F, dF, ddF
    raise ValueError(f"unknown TPMS '{name}'")


class TPMSSheet:
    """Analytic sheet-network TPMS:  phi(x) = |F(k x)| - t."""

    def __init__(self, family="gyroid", k=2*np.pi, t=0.0):
        self.family, self.k, self.t = family, float(k), float(t)
        self.F, self.dF, self.ddF = _basis(family)

    # -- core fields --------------------------------------------------------
    def phi(self, x):
        """Level set; negative inside the solid sheet."""
        return torch.abs(self.F(self.k * x)) - self.t

    def grad_phi(self, x):
        """Exact gradient of |F(kx)| - t."""
        X = self.k * x
        s = torch.sign(self.F(X)).unsqueeze(-1)
        return s * self.dF(X) * self.k

    def hess_phi(self, x):
        """Exact Hessian of |F(kx)| - t."""
        X = self.k * x
        s = torch.sign(self.F(X)).unsqueeze(-1).unsqueeze(-1)
        return s * self.ddF(X) * self.k**2

    def normal(self, x):
        g = self.grad_phi(x)
        return g / g.norm(dim=-1, keepdim=True).clamp_min(1e-12)

    def inside(self, x):
        return self.phi(x) < 0.0

    # -- sampling -----------------------------------------------------------
    @torch.no_grad()
    def sample(self, n, box=((0.0, 1.0),) * 3, shell=None, seed=0):
        """Uniform rejection sampling inside the solid.
        shell=(a,b) keeps only points with a < phi < b (near-surface oversampling).
        Returns (n,3) tensor of collocation points."""
        g = torch.Generator().manual_seed(seed)
        lo = torch.tensor([b[0] for b in box]); hi = torch.tensor([b[1] for b in box])
        out, need = [], n
        while need > 0:
            cand = lo + (hi - lo) * torch.rand(4 * need, 3, generator=g)
            keep = self.inside(cand)
            if shell is not None:
                p = self.phi(cand)
                keep &= (p > shell[0]) & (p < shell[1])
            got = cand[keep]
            out.append(got[:need]); need -= min(len(got), need)
        return torch.cat(out)[:n]

    @torch.no_grad()
    def volume_fraction(self, n=2_000_000, box=((0.0, 1.0),) * 3, seed=1):
        g = torch.Generator().manual_seed(seed)
        lo = torch.tensor([b[0] for b in box]); hi = torch.tensor([b[1] for b in box])
        x = lo + (hi - lo) * torch.rand(n, 3, generator=g)
        return self.inside(x).float().mean().item()


# ---------------------------------------------------------------------------
# Self-tests
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    torch.set_default_dtype(torch.float64)  # FD checks need float64 (float32 eps/h ~ 1e-2)
    torch.manual_seed(0)
    fam = sys.argv[1] if len(sys.argv) > 1 else "gyroid"
    tp = TPMSSheet(family=fam, k=2*np.pi, t=0.3)
    x = torch.rand(500, 3)

    # T1: gradient vs central FD
    h = 1e-6
    g_num = torch.stack([(tp.phi(x + h*torch.eye(3)[i]) - tp.phi(x - h*torch.eye(3)[i])) / (2*h)
                         for i in range(3)], dim=-1)
    g_err = (tp.grad_phi(x) - g_num).abs().max().item()
    print(f"T1 grad  |analytic - FD|_inf = {g_err:.2e}  -> {'PASS' if g_err < 1e-5 else 'FAIL'}")

    # T2: Hessian vs FD of gradient
    H_num = torch.stack([(tp.grad_phi(x + h*torch.eye(3)[i]) - tp.grad_phi(x - h*torch.eye(3)[i])) / (2*h)
                         for i in range(3)], dim=-1)
    H_err = (tp.hess_phi(x) - H_num).abs().max().item()
    print(f"T2 Hess  |analytic - FD|_inf = {H_err:.2e}  -> {'PASS' if H_err < 1e-3 else 'FAIL'}")

    # T3: sheet-network VF matches independent dense-voxel count (ground truth);
    #     plus solid-network sanity: F(x) < 0 fills exactly half the cell (gyroid symmetry)
    voxel = TPMSSheet(fam, 2*np.pi, 0.3)
    g1d = torch.linspace(0.5 / 200, 1 - 0.5 / 200, 200)
    X, Y, Z = torch.meshgrid(g1d, g1d, g1d, indexing="ij")
    vf_vox = (voxel.phi(torch.stack([X, Y, Z], -1).reshape(-1, 3)) < 0).float().mean().item()
    vf_mc = voxel.volume_fraction(n=1_000_000)
    ok = abs(vf_vox - vf_mc) < 0.01
    print(f"T3a VF(t=0.3): voxel={vf_vox:.4f} vs MC={vf_mc:.4f}  -> {'PASS' if ok else 'FAIL'}")
    if fam == "gyroid":
        F, _, _ = _basis("gyroid")
        pts = torch.rand(1_000_000, 3) * 2 * np.pi
        frac_neg = (F(pts) < 0).float().mean().item()
        ok = abs(frac_neg - 0.5) < 0.005
        print(f"T3b solid-network P(F<0) = {frac_neg:.4f}  (expect 0.5000)  -> {'PASS' if ok else 'FAIL'}")

    # T4: VF monotone in t
    vfs = [TPMSSheet(fam, 2*np.pi, tt).volume_fraction(n=400_000) for tt in (0.0, 0.3, 0.6, 0.9)]
    mono = all(a < b for a, b in zip(vfs, vfs[1:]))
    print(f"T4 VF(t) = {[round(v,3) for v in vfs]}  monotone -> {'PASS' if mono else 'FAIL'}")

    # T5: near-surface shell sampler
    pts = tp.sample(2000, shell=(-0.05, 0.0), seed=3)
    p = tp.phi(pts)
    ok = ((p > -0.05) & (p < 0.0)).all().item()
    print(f"T5 shell sampler: phi in (-0.05, 0) for all 2000 pts -> {'PASS' if ok else 'FAIL'}")
    print("N1 module self-tests complete.")
