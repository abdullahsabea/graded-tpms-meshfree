# E3 — Optimization case study: thickness-graded gyroid, max C1111 at fixed Vf

Date: 2026-07-30. Status: **PASS** (headline result, FEM-confirmed).

## Setup
- Design variables: 12 coefficients of a first-harmonic Fourier grading field
  t(x) = clip(0.30 + δt₀ + Σ θ_m ψ_m(x), 0.12, 0.55), ψ = cos/sin of modes
  (1,0,0),(0,1,0),(0,0,1),(1,1,0),(1,0,1),(0,1,1).
- Constraint: Vf = Vf(uniform t=0.3) = 0.193 (enforced by bisection on δt₀).
- Physics model: conditional DEM u(x,t), trained over t∈[0.15,0.5]
  (`e3_conditional.py`, ckpt `e3_cond.pt`). Audit vs aster: +2–8% across range.
- Optimizer: Vf-compensated coordinate search (9-point scan per mode, 2 sweeps)
  after analytic-gradient Adam plateaued (+0.4%); gradient path kept for
  methodology, coordinate polish for the final design.
- Integration: fixed 50k MC cloud, smoothed membership sigmoid((t(x)-|F|)/τ), τ=0.02.

## Results

| quantity | uniform t=0.3 | optimized graded | gain |
|---|---|---|---|
| DEM C1111 (hard-domain audit) | 0.1139 | 0.1338 ± 0.0004 | **+17.5 %** |
| **aster C1111 (ground truth)** | **0.10725** (N64) | **0.11699** (N96; N64=0.11643) | **+9.1 %** |
| Volume fraction | 0.1935 | 0.1938 | iso-volume |

- Optimized θ*: [-0.06, -0.16, 0.16, -0.16, 0.16, 0.0, -0.14, -0.12, 0.14, 0.14, 0.04, -0.08], δt₀ = -0.0094.
- t(x) spans the full allowed band [0.12, 0.55] — the optimizer redistributes
  material into the stiffest load paths rather than nudging uniformity.
- DEM over-predicts the gain (17.5% vs 9.1%): its thin-wall over-stiffness
  bias (E2) is largest exactly where the optimizer pushes t → 0.12.
  Reported honestly as model-form error; the FEM-validated +9.1% stands.

## Files
- `e3_conditional.py`, `e3_cond.pt`, `e3_cond_audit.json`, `e3_vf_table.json`
- `e3_optimize.py`, `e3_opt_result.json`, `e3_opt_history.json`
- `e3_coord_search.json`, `e3_hard_audit.json`
- `make_mesh_graded.py`, `gyroid_graded_N{64,96}.mail`, `out_graded_N{64,96}.mess`
