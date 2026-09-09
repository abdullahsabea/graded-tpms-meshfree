# N3 VERIFICATION REPORT — First mesh-free TPMS homogenization (V1 gate)
Date: 2026-07-30 | Status: **V1 PASS** — mesh-free DEM matches code_aster within ~5%

## Problem
Sheet-network gyroid unit cell (t=0.3, k=2π, unit cube, E=1, ν=0.3, VF≈0.19),
KUBC (kinematic uniform boundary conditions), macro-strain ε_xx.
Effective C1111 — the canonical homogenization benchmark.

## Ground truth (code_aster 17.4, simvia/code_aster:stable, Docker)
Voxel HEXA8 meshes generated from the analytic level set (research/n3/make_mesh.py):

| Mesh | Elements | Nodes | C1111 (reaction on X1 / ε) |
|---|---|---|---|
| N48 | 21,152 | 33,427 | 0.10506 |
| N64 | 50,144 | 71,935 | 0.10725 |

Converging from below (voxel staircase softens walls); extrapolated limit ≈ 0.109–0.110.
Consistent with published sheet-gyroid stiffness fits at ρ≈0.19.

## Mesh-free DEM (research/n3/dem_gyroid.py)
- Multi-scale Fourier-feature MLP (σ = 1/4/12), hard KUBC via cube-distance function,
  energy-only loss (all-Dirichlet), MC collocation uniform in the analytic solid,
  Adam + deterministic LBFGS polish, float64 audit (120k points).
- Training convergence (audit C1111 after each chunk):
  0.431 → 0.156 → 0.151 → 0.130 → 0.120 → 0.116 → 0.114 → **0.1127 ± 0.0002**

## Result
**C1111_DEM = 0.1127 vs code_aster 0.1073 (N64) — 5.0% gap, still descending.**
vs the mesh-converged estimate (~0.109–0.110): ~3%. Rayleigh–Ritz consistent
(both are KUBC energy minimizations; DEM approaches the aster value from above).

## Bugs caught during this gate (the audit trail — why validation matters)
1. **V_macro vs V_solid normalization** (the big one): effective modulus is
   2U/(ε²·V_macro), not per-solid-volume. A 5.17× phantom "formulation error"
   was a normalization slip. Fixed and verified against Hill–Mandel.
2. code_aster FORMULE keyword args are not substituted — literal values required.
3. Overlapping face groups → duplicate Dirichlet constraints; solved with a
   single disjoint BOUND group (u = ε·x valid on every face).
4. POST_RELEVE_T 'EXTRACTION' returns per-node rows — reactions must be SUMMED.
5. .mail format: FINSF terminators, group names inline, '%' header comments.

## Gate decision
**V1 PASS (conditional margin small but real).** The mesh-free energy method
computes TPMS effective stiffness within ~5% of code_aster with no mesh, no
training data, and ~20k CPU iterations. Residual gap is training/expressivity,
not formulation — closable with more iterations, adaptive collocation, and
fully-periodic BCs (KUBC is itself an upper bound; the next methodological step
is periodic fluctuations, which also matches the paper's contribution list).

## Artifacts
- research/n3/make_mesh.py, gyroid_N48/N64_t0.3.mail
- research/n3/homog.comm, study_N48/N64.export, out_N48/N64.mess
- research/n3/dem_gyroid.py, dem_gyroid.pt, n3_dem_metrics.json
- research/N3_verification_report.md (this file)
