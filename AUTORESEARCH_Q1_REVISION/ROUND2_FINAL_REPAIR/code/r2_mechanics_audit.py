"""r2_mechanics_audit: audit the scorer's partial spatial derivatives at
fixed local thickness versus the total derivatives of u(x, t(x)).

PI qualification: "The new scorer takes the partial spatial derivative at
fixed local thickness. Audit explicitly whether omission of the chain-rule
term du/dt (x) grad(t) matches the declared local surrogate. It must not be
described as the strain energy of a fully coupled graded displacement
solution without that distinction."

Facts established by this audit (code references):
  * e3_conditional.py trains u(x,t) as the energy-minimizing KUBC solution
    family of the UNIFORM gyroid at thickness t; its strain_energy()
    (research/n3/e3_conditional.py:87-95) differentiates u w.r.t. x at FIXED
    t. Training never differentiates w.r.t. t.
  * vgmm_common.make_scorer -> strain_xt computes jacrev(full_xt)(xt)[:, :, :3]
    (code/vgmm_common.py:202-211): PARTIAL spatial derivatives at the local
    thickness value; the chain-rule term (du/dt) (x) grad t(x) is OMITTED.
  * The scorer therefore evaluates a locally-frozen-thickness surrogate:
    u of the uniform cell at the local t, weighted by a smoothed membership
    w = sigmoid((t(x) - |F|)/tau). It is NOT the strain energy of a coupled
    graded equilibrium solution u(x, t(x)) -- for that, the total derivative
    D u = du/dx + (du/dt) grad(t)^T would enter the strain and the
    equilibrium itself would differ.

This script QUANTIFIES the omitted term at representative designs:
uniform (theta=0), the VG-MM round-1 winner, the archived DEM-only graded
design (e3_coord_search.json), and the band-restricted printable design
(e3_opt_result_printable.json when loadable). For each, over the frozen
50k cloud it reports the pointwise Frobenius ratio
    r(x) = || (du/dt) (x) grad t(x)^T ||_F / || du/dx ||_F
plus the fraction of the cloud clipped to the thickness bounds (where
grad t is set to zero by np.clip semantics).

No FE solves; pure torch on the frozen checkpoint. Historical scorer is NOT
modified. Output: results/r2_mechanics_audit.json.
"""
import json
import os
import sys

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vg2_common as v2  # noqa: E402
import e3_conditional as ec  # noqa: E402

R2 = v2.R2
OUT = os.path.join(R2, "results", "r2_mechanics_audit.json")


def audit_design(model, theta, shift, cloud_seed=11, n_cloud=50_000):
    torch.set_default_dtype(torch.float32)
    g = torch.Generator().manual_seed(cloud_seed)
    pts = torch.rand(n_cloud, 3, generator=g)

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

    # local thickness field t(x) = clip(T0 + shift + sum theta_m psi_m(x))
    psi_cols = []
    for (a, b, c) in v2.MODES:
        ph = 2 * np.pi * (a * pts[:, 0] + b * pts[:, 1] + c * pts[:, 2])
        psi_cols += [torch.cos(ph), torch.sin(ph)]
    psiv = torch.stack(psi_cols, dim=-1)
    theta_t = torch.tensor(theta, dtype=torch.float32)
    t_raw = v2.T0 + float(shift) + psiv @ theta_t
    tx = t_raw.clamp(v2.T_MIN, v2.T_MAX)
    frac_clipped = float(((t_raw < v2.T_MIN) | (t_raw > v2.T_MAX))
                         .double().mean())

    xt = torch.cat([pts, tx.unsqueeze(-1)], dim=-1)
    J = torch.func.vmap(torch.func.jacrev(full_xt))(xt)  # (N,3,4): d/d(x,t)
    Jx = J[:, :, :3]                                     # du/dx (used)
    Jt = J[:, :, 3]                                      # du/dt (omitted)

    # analytic gradient of each basis column
    grads = []
    for (a, b, c) in v2.MODES:
        ph = 2 * np.pi * (a * pts[:, 0] + b * pts[:, 1] + c * pts[:, 2])
        sph = torch.sin(ph) * 2 * np.pi
        cph = torch.cos(ph) * 2 * np.pi
        grads += [torch.stack([cph * a, cph * b, cph * c], dim=-1),     # cos
                  torch.stack([sph * a, sph * b, sph * c], dim=-1)]     # sin
    G = torch.stack(grads, dim=-1)                      # (N,3,12)
    gt = G @ theta_t                                    # (N,3) grad t(x)
    inside = ((t_raw >= v2.T_MIN) & (t_raw <= v2.T_MAX)).unsqueeze(-1)
    gt = gt * inside                                    # clip => zero grad

    # omitted term: (du/dt) (x) grad t(x)^T  ->  (N,3,3)
    omit = Jt.unsqueeze(-1) * gt.unsqueeze(-2)
    num = omit.norm(dim=(1, 2))
    den = Jx.norm(dim=(1, 2))
    ratio = (num / den.clamp_min(1e-12))
    q = torch.quantile(ratio, torch.tensor([0.5, 0.9, 0.99]))

    inside_mask = inside.squeeze(-1)
    if inside_mask.any():
        r_unc = ratio[inside_mask]
        q_unc = torch.quantile(r_unc, torch.tensor([0.5, 0.9, 0.99]))
        unc_mean = float(100 * r_unc.mean())
        unc_q = [float(100 * x) for x in q_unc]
        unc_count = int(inside_mask.sum())
    else:
        unc_mean = 0.0
        unc_q = [0.0, 0.0, 0.0]
        unc_count = 0

    return dict(
        theta=[round(float(x), 6) for x in theta], shift=float(shift),
        frac_cloud_clipped=frac_clipped,
        ratio_omitted_over_used_F_norm_pct=[
            float(100 * x) for x in q],
        mean_ratio_pct=float(100 * ratio.mean()),
        unclipped_count=unc_count,
        unclipped_mean_ratio_pct=unc_mean,
        unclipped_ratio_quantiles_pct=unc_q,
        note="r(x)=||(du/dt)(x)grad t(x)^T||_F / ||du/dx||_F on the frozen "
             "cloud; the scorer uses only du/dx (partial at fixed local t)")


def main():
    model = ec.make_model()
    model.load_state_dict(torch.load(ec.CKPT, weights_only=True))
    for p in model.parameters():
        p.requires_grad_(False)

    designs = {}
    theta0 = [0.0] * v2.N_MODES
    designs["uniform"] = (theta0, v2.bisect_shift_discrete(64, theta0))
    vg = json.load(open(os.path.join(v2.WS, "results", "vgmm_result.json")))
    designs["vgmm_round1_winner"] = (vg["theta_final"],
                                     v2.bisect_shift_discrete(
                                         64, vg["theta_final"]))
    cs = json.load(open(os.path.join(v2.N3, "e3_coord_search.json")))
    designs["demonly_graded_archived"] = (cs["theta"], cs["t0shift"])
    pr = os.path.join(v2.N3, "e3_opt_result_printable.json")
    if os.path.exists(pr):
        pj = json.load(open(pr))
        th = pj.get("theta")
        if th is not None:
            designs["band_restricted_printable"] = (
                th, v2.bisect_shift_discrete(64, th))

    out = dict(
        summary=(
            "The scorer differentiates u(x,t) with respect to x at fixed "
            "local thickness t(x) and omits the chain-rule term "
            "(du/dt)(grad t)^T. It is an approximate LOCAL score -- the "
            "locally-frozen uniform-cell solution family weighted by "
            "smoothed membership -- not the strain energy of a coupled "
            "graded equilibrium solution. The historical scorer is "
            "unchanged; this audit quantifies the omitted term only."),
        code_references=dict(
            training_fixed_t="research/n3/e3_conditional.py:87-95 "
                             "(strain_energy differentiates x at fixed t)",
            scorer_partial="AUTORESEARCH_Q1_REVISION/code/vgmm_common.py: "
                           "strain_xt -> jacrev(full_xt)(xt)[:, :, :3]",
            membership="vgmm_common.make_scorer: w=sigmoid((t-|F|)/0.02)"),
        constants=dict(EPS=ec.EPS, LAM=ec.LAM, MU=ec.MU,
                       T_MIN=v2.T_MIN, T_MAX=v2.T_MAX, T0=v2.T0, TAU=v2.TAU),
        designs={},
    )
    for name, (th, sh) in designs.items():
        out["designs"][name] = audit_design(model, th, sh)
        print(name, json.dumps(out["designs"][name]["ratio_omitted_over_"
                                                     "used_F_norm_pct"]))
    v2.write_json_new(OUT, out)
    print("wrote", OUT)
    v2.write_json_versioned(OUT, out)
    print("wrote versioned", OUT)


if __name__ == "__main__":
    main()
