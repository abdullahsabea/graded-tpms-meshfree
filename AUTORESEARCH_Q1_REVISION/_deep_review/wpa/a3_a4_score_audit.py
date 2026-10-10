"""WP-A3 (D5) and WP-A4 (G20).
A4: hard-domain float64 audit (rejection-sampled solid points, frozen local t),
    procedure of e3_optimize.py lines 118-140; validated by reproducing the
    archived e3_hard_audit.json (unconstrained 0.1338 +- 0.0004) and uniform 0.1139.
A3: frozen-t score (production scorer: seed-11 cloud, 50k, sigmoid membership)
    vs the energy of the composed field u(x, t(x)) with the chain-rule term
    (du/dt) grad t included, on the same cloud; plus the hard-domain variant.
    The composed field is KUBC-admissible, so its hard-domain energy is a Ritz
    upper bound for the graded continuum problem (up to quadrature error)."""
import json, os, sys
import numpy as np
import torch
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "AUTORESEARCH_Q1_REVISION", "code"))
sys.path.insert(0, os.path.join(ROOT, "research", "n3"))
import vgmm_common as vc
import e3_conditional as ec
torch.set_default_dtype(torch.float64)
model = ec.make_model()
model.load_state_dict(torch.load(ec.CKPT, weights_only=True))
model = model.double()
for p in model.parameters(): p.requires_grad_(False)
EPS, LAM, MU = ec.EPS, ec.LAM, ec.MU
MODES = vc.MODES
def raw_net(x, t):
    z = torch.cat([torch.sin(x @ model.B), torch.cos(x @ model.B), t.expand(x.shape[:-1] + (1,))], dim=-1)
    return model.net(z)
def full_xt(xt):
    x, t = xt[..., :3], xt[..., 3:4]
    d = ec.d_cube(x)
    aff = torch.stack([EPS * x[..., 0], torch.zeros_like(x[..., 0]), torch.zeros_like(x[..., 0])], dim=-1)
    return d * raw_net(x, t) + aff
def psi(x):
    c = []
    for (a, b, cc) in MODES:
        ph = 2 * np.pi * (a * x[:, 0] + b * x[:, 1] + cc * x[:, 2]); c += [torch.cos(ph), torch.sin(ph)]
    return torch.stack(c, -1)
def gradpsi(x):
    g = []
    for (a, b, cc) in MODES:
        ph = 2 * np.pi * (a * x[:, 0] + b * x[:, 1] + cc * x[:, 2])
        s, c = torch.sin(ph) * 2 * np.pi, torch.cos(ph) * 2 * np.pi
        g += [torch.stack([-s * a, -s * b, -s * cc], -1), torch.stack([c * a, c * b, c * cc], -1)]
    return torch.stack(g, -1)   # d/dx of [cos, sin]
def tfield(x, th, sh, lo, hi):
    raw = vc.T0 + sh + psi(x) @ th
    return raw.clamp(lo, hi), (raw >= lo) & (raw <= hi)
def dens_of(D):
    e = 0.5 * (D + D.transpose(1, 2))
    tr = e.diagonal(dim1=1, dim2=2).sum(-1)
    return 0.5 * (LAM * tr ** 2 + 2 * MU * (e ** 2).sum((1, 2)))
def densities(x, th, sh, lo, hi, bs=20000):
    fz, fl = [], []
    for i in range(0, len(x), bs):
        xb = x[i:i + bs]
        t, inside = tfield(xb, th, sh, lo, hi)
        J = torch.func.vmap(torch.func.jacrev(full_xt))(torch.cat([xb, t[:, None]], -1))
        Jx, Jt = J[:, :, :3], J[:, :, 3]
        gt = (gradpsi(xb) @ th) * inside[:, None]
        fz.append(dens_of(Jx)); fl.append(dens_of(Jx + Jt[:, :, None] * gt[:, None, :]))
    return torch.cat(fz), torch.cat(fl)
def hard_audit(th, sh, lo, hi, n=40000):
    g = torch.Generator().manual_seed(99); out, need = [], n
    while need > 0:
        c = torch.rand(4 * need, 3, generator=g)
        got = c[torch.abs(ec.Fval(c)) < tfield(c, th, sh, lo, hi)[0]]
        out.append(got[:need]); need -= min(len(got), need)
    pts = torch.cat(out)[:n]
    g2 = torch.Generator().manual_seed(5); c = torch.rand(200000, 3, generator=g2)
    vf = (torch.abs(ec.Fval(c)) < tfield(c, th, sh, lo, hi)[0]).double().mean().item()
    fz, fl = densities(pts, th, sh, lo, hi)
    k = 2 / EPS ** 2 * vf
    return dict(vf=vf, C_frozen=k * fz.mean().item(), se_frozen=k * fz.std().item() / np.sqrt(n),
                C_chain=k * fl.mean().item(), se_chain=k * fl.std().item() / np.sqrt(n))
def cloud_scores(th, sh, lo, hi):
    g = torch.Generator().manual_seed(11); pts = torch.rand(50000, 3, generator=g)
    t, _ = tfield(pts, th, sh, lo, hi)
    w = torch.sigmoid((t - torch.abs(ec.Fval(pts))) / vc.TAU)
    fz, fl = densities(pts, th, sh, lo, hi)
    return dict(score_frozen=2 * (w * fz).mean().item() / EPS ** 2, score_chain=2 * (w * fl).mean().item() / EPS ** 2)
J = lambda p: json.load(open(p))
N3 = os.path.join(ROOT, "research", "n3")
cs, pr = J(os.path.join(N3, "e3_coord_search.json")), J(os.path.join(N3, "e3_opt_result_printable.json"))
vg = J(os.path.join(ROOT, "AUTORESEARCH_Q1_REVISION", "results", "vgmm_result.json"))
fe = J(os.path.join(N3, "e3_fe_baseline.json"))
D = {"uniform": ([0.0] * 12, 0.30 - 0.30, 0.12, 0.55),
     "band": (pr["theta"], pr["t0shift"], pr["t_min"], pr["t_max"]),
     "unconstrained": (cs["theta"], cs["t0shift"], 0.12, 0.55),
     "vgmm_seed11": (vg["theta_final"], None, 0.12, 0.55),
     "fullfe": (fe["theta"], None, 0.12, 0.55)}
res = {}
# validation of the re-implemented hard audit against the archive
th = torch.tensor(cs["theta"])
res["validation_unconstrained_noshift"] = hard_audit(th, 0.0, 0.12, 0.55)
print("VALIDATION unconstrained (no shift):", res["validation_unconstrained_noshift"], flush=True)
for name, (t_, sh, lo, hi) in D.items():
    th = torch.tensor(t_, dtype=torch.float64)
    if sh is None: sh = vc.bisect_shift_discrete(64, t_)
    r = dict(shift=sh, lo=lo, hi=hi)
    r.update(hard_audit(th, sh, lo, hi)); r.update(cloud_scores(th, sh, lo, hi))
    res[name] = r
    print(name, {k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
json.dump(res, open("a3_a4_score_audit.json", "w"), indent=2)
