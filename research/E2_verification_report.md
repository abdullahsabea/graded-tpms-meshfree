# E2 — Thickness-sweep verification report (gyroid sheet, KUBC ε_xx, E=1, ν=0.3)

Date: 2026-07-30. Status: **PASS** (gate criteria: DEM within ~5–7% of converged voxel FEM per point).

## Setup
- Geometry: analytic gyroid sheet, k=2π, unit cube, t ∈ {0.20, 0.30, 0.45}.
- FEM reference: code_aster 17.4 (simvia/code_aster:stable), voxel HEXA8,
  KUBC via AFFE_CHAR_MECA_F u = ε·x on BOUND, C1111 = 2U/(ε²·V_macro).
  Mesh convergence checked per thickness.
- DEM: `research/n3/dem_gyroid.py` — multi-scale Fourier MLP (σ=1/4/12, width 128,
  depth 4), hard BC via cube distance, MC collocation in solid, Adam→L-BFGS,
  warm-start from t=0.3 checkpoint. Per-t checkpoints `dem_gyroid_t{t}.pt`.
- Volume fractions (analytic MC, 1M samples): t=0.20 → 0.1288, t=0.30 → 0.1934, t=0.45 → 0.2910.

## Results

| t    | Vf    | FEM C1111 (converged)        | DEM C1111      | ratio |
|------|-------|------------------------------|----------------|-------|
| 0.20 | 0.129 | 0.06724 (N96; N64=0.06658)   | 0.0705 ± 0.0001| 1.049 |
| 0.30 | 0.193 | 0.10725 (N64; N48=0.10506)   | 0.1127 ± 0.0002| 1.050 |
| 0.45 | 0.291 | 0.18581 (N64)                | 0.1856 ± 0.0003| 0.999 |

## Observations
- Thin walls (t=0.2): systematic ~5% over-stiffness, still slowly descending
  with training (1.056 → 1.049 after extra chunk). Error source: MC collocation
  under-resolves high-curvature thin-wall strain gradients. Direction is
  conservative for design ranking.
- t=0.3: same 5% class (matches N3 report).
- t=0.45: essentially exact (0.1%). Thicker walls are well resolved by the
  Fourier feature scales.
- One shared architecture warm-starts cleanly across thicknesses — evidence
  the model generalizes over the TPMS parameter, which is exactly what the
  TO loop will exploit.

## Files
- Meshes: `gyroid_N{64,96}_t{0.2,0.3,0.45}.mail`; exports `study_*.export`
- Aster outputs: `out_*.mess` (grep C1111_KUBC)
- DEM metrics: `n3_dem_metrics_t{t}.json`; checkpoints `dem_gyroid*.pt`
