# Claim map: every reported stiffness → design, solver, boundary condition, mesh, volume target, seed

Paths are relative to the archive root. `reproduce/check_tables.py` recomputes every
table cell from the records named here; `reproduce/regenerate_figures.py` rebuilds
the data figures.

## Designs

The body-fitted mesh generator `research/n3/conforming/make_conforming_mesh.py` reads each design from the record named below.

| Design (article name) | Definition | Record |
|---|---|---|
| Uniform sheet | t = 0.30 everywhere, gyroid sheet \|F(kx)\| ≤ t | — |
| Unconstrained score design | coordinate search on the score, t ∈ [0.12, 0.55], 12 Fourier coefficients | `research/n3/e3_coord_search.json` (θ, shift) |
| Band-and-smoothness-restricted design (the printed graded coupon) | score optimization, t ∈ [0.20, 0.45], gradient penalty λ_g = 0.0012 | `research/n3/e3_opt_result_printable.json` (θ, shift) |
| Filtered search, seed 11 | score-proposed, FE-accepted coordinate search | `AUTORESEARCH_Q1_REVISION/results/vgmm_result.json` (`theta_final`) |
| Filtered search, seeds 12–20; random proposals 11–20; deterministic cyclic; score-only greedy 11–13 | same problem, protocol `ROUND2_FINAL_REPAIR/plans/ROUND2_PLAN.md` (SHA-256 e56fdf7f…, frozen 2026-09-13T14:41:05Z) | `AUTORESEARCH_Q1_REVISION/ROUND2_FINAL_REPAIR/results/r2_arms*/arm_<policy><seed>.json` |
| FE coordinate search | coordinate search scored by voxel FE | `research/n3/e3_fe_baseline.json` (`theta`) |
| 192-candidate pool | ranking study | `AUTORESEARCH_Q1_REVISION/results/pool_table.csv`, `ROUND2_FINAL_REPAIR/results/r2_pool_replay.json` |

Volume target for all searches: V_f* = 0.19328 (Monte Carlo estimate; analytic value at t = 0.3 is 0.19345). Each design's uniform shift δt₀ is found by bisection to this target and is stored with the design.

## Stiffness values

| Quantity (where reported) | Solver | Boundary condition | Mesh | Volume handling | Record |
|---|---|---|---|---|---|
| Score C1111 (Tables 1, 4; Fig. 5) | frozen conditional deep-energy network `research/n3/e3_cond.pt`, local thickness, float64 hard-domain audit | KUBC (affine displacement on the cell boundary) | 5×10⁴-point cloud, seed 11 (search); 2×10⁵ points for volume | design at V_f* | `_deep_review/wpa/a3_a4_score_audit*.json`, `research/n3/paper_numbers.json` (`e3.*.dem`) |
| Voxel C1111, ladders (Tables 3, 4, A1, S4; Figs. 5, S3, S4) | code_aster 17.4, `research/n3/homog2.comm`, Hill–Mandel energy basis | KUBC | voxel 48³, 64³, 96³, 128³; generators `make_mesh*.py` | each mesh volume-calibrated to its target | `research/n3/energy_ladder.json`, `paper_numbers.json`, logs `loge_*.txt` |
| Voxel C1111, searches (Tables S5, S6, S7; Figs. 6, S5, S6) | as above | KUBC | 64³ search, 96³ confirmation | calibrated to V_f* | arm records; all 598 cached solves in `fe_cache_summary.csv` |
| Body-fitted KUBC (Table 2) | code_aster, `research/n3/conforming/homog_conf.comm`, quadratic tetrahedra | KUBC | `make_conforming_mesh.py`, N = 48, M = 96 | raw meshed V_f, then C ∝ V_f^1.21 to 0.19328 | `research/n3/conforming/conf_summary.json` (`kubc`) |
| Body-fitted periodic (Tables 2, B1, B2; Fig. 3) | `homog_conf_pbc.comm` (LIAISON_MAIL ties, Lagrange multipliers, MUMPS RESI_RELA 1e-6) | periodic | N = 48 and N = 72, M = 96 | as above | `conf_summary.json` (`pbc`), `wpa1_N72_results.json`, logs `log_pbc_*.txt` |
| Periodicity residual (Table B1) | `homog_conf_pbc_resid.comm` (same solve + DEPL export), `periodicity_residual.py` | periodic | as above | — | `resid_*_residual.json`, `resid_*_report.txt` |
| Uniform at ν = 0.33 (App. B) | `homog_conf_pbc_nu033.comm` | periodic | N = 48 | raw | `wpa2_nu033.log` |
| External benchmarks (App. B) | Fisher et al. 2023 (voxel), Mele et al. 2025 (tetrahedral) | periodic | — | quadratic log–log interpolation to V_f = 0.19389 | `_deep_review/wpa/a2_external/a2_results.json` (source data not redistributed; see README) |
| Coupon E*, R (Tables 6, S8, S9; Figs. 8, S7) | crosshead slope, 150–600 N, L₀ = 100 mm, A₀ = 450 mm² | tensile test, one PETG build | — | mass adjustment E*/(m/m̄)² | raw `TO_AI-results_instron/TO_AI/U_1_Exports/*.csv`, `paper/verify_experiment_stats.py`, masses `reproduce/coupon_masses.csv` |

## Seeds

- Score cloud: seed 11 (fixed for every search and audit).
- Filtered and random searches: seeds 11–20 as named in the arm records; seed 11 of the filtered search is the round-1 run (`vgmm_result.json`).
- Deep-energy single-thickness training seeds 0–4: `research/n3/dem_gyroid_seed*.pt`, `n3_dem_seed*.json`.
- Bootstrap: NumPy `default_rng(2026)`, 20,000 resamples (`ROUND2_FINAL_REPAIR/code/r2_ext_stats.py`).
- Coupon bootstrap (supplementary interval): seed 0, 20,000 resamples (`paper/verify_experiment_stats.py`).
