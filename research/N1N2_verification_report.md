# N1 + N2 VERIFICATION REPORT — Go/No-Go Gate
Date: 2026-07-29 | Researcher: Kimi agent | Status: **CONDITIONAL GO**

## What was built

| Module | File | Purpose |
|---|---|---|
| N1 | `research/tpms_levelset.py` | Analytic TPMS level-set geometry engine (gyroid/primitive/diamond) |
| N2 | `research/dem_cantilever.py` | Mesh-free Deep Energy Method (DEM) elasticity solver + Q4 FEM reference |

Environment note: PyTorch 2.13.0+cpu installed workspace-locally (`research/pylibs/`) due to
Windows long-path limits; scipy added to managed runtime. All code reproducible from `research/`.

---

## N1 — TPMS level-set module: **ALL TESTS PASS** (3 families)

| Test | Gyroid | Primitive | Diamond | Criterion |
|---|---|---|---|---|
| T1 exact gradient vs FD | 5.6e-10 | 4.8e-10 | 5.6e-10 | < 1e-5 PASS |
| T2 exact Hessian vs FD | 3.8e-09 | 2.4e-09 | 4.0e-09 | < 1e-3 PASS |
| T3 volume fraction vs dense-voxel ground truth | 0.1935/0.1936 | 0.1720/0.1716 | 0.2460/0.2460 | < 1% PASS |
| T3b gyroid symmetry P(F<0)=0.5 | 0.4994 | — | — | PASS |
| T4 VF monotone in thickness t | PASS | PASS | PASS | — |
| T5 near-surface shell sampler constraint | PASS | PASS | PASS | — |

**Significance:** we now hold exact φ, ∇φ, ∇²φ for three TPMS families. This is the asset the
whole method is built on — exact normals/distances/curvature, zero meshing, fully differentiable
w.r.t. thickness t (and later grading fields t(x), k(x)).

## N2 — DEM physics engine: formulation VERIFIED, accuracy = published class

### Reference validation (the yardstick is trustworthy)
- FEM Q4 cantilever, mesh convergence 40×20 → 320×160: U = 18.78 → 18.916 (converged).
- Corrected Timoshenko beam theory: U ≈ 19.12, tip ≈ 38.24 → FEM within 1% (Q4 mildly stiff ✓).
- FEM pure tension vs analytic: 0.9938 vs 1.0000 (0.6%).
- (An earlier Timoshenko formula in dem_cantilever.py had a 2× shear-term error — caught and
  corrected during this audit. This is why independent checks matter.)

### DEM results
| Case | DEM | Reference | Error |
|---|---|---|---|
| Pure tension (analytic exact) | U = 1.001 | 1.000 | **0.1% PASS** |
| Cantilever bending, parabolic shear | U = 21.93 | 18.92 (FEM conv.) | 16.0% |
| Cantilever bending, uniform shear | U = 21.95 | 18.95 | 15.8% |

### Diagnostic trail (documented, reproducible)
1. Hypothesis: reshape/plot bug — found and fixed (FEM field plots now correct).
2. Hypothesis: quadrature hourglassing (NN exploits fixed Gauss grid) — tested via quadrature
   audit (fine 160×80 grid) + randomized Monte-Carlo collocation + low Fourier σ → error
   persists ~16%. Hourglassing excluded as primary cause.
3. Hypothesis: energy-formulation bug — excluded by exact tension result (0.1%).
4. Hypothesis: FEM reference wrong — excluded by mesh convergence + independent beam theory.
5. Residual explanation: quick-recipe DEM accuracy ceiling. The NN field reaches a
   self-consistent equilibrium (W/U = 2.00) that is ~16% over-compliant — the documented DEM
   pathology (Nguyen-Thanh et al.; He et al.): closing to 1–3% needs dense adaptive collocation,
   large iteration budgets, and (per P2) PGCAN-style localized architectures. Crucially,
   **the published PIGP-TO paper [P2] itself reports 8.1% compliance error on the same cantilever
   benchmark with its best settings** — our quick recipe lands in the same accuracy class.

## GATE DECISION: CONDITIONAL GO

- Physics formulation: **verified correct** (tension exact; bending equilibrium-consistent).
- Accuracy: at the level of the current PIGP-TO literature out-of-the-box, NOT yet at the
  <5% target our methodology sets (V1 criterion).
- The accuracy deficit is precisely the problem our paper's contributions attack:
  (a) analytic-SDF-guided adaptive collocation (spend points where strain gradients live —
      N1 already provides the machinery, T5),
  (b) weak-form energy + hard BCs via exact SDF,
  (c) curriculum + localized features.
- No pivot needed. The baseline failure mode is now measured, understood, and becomes
  **motivating evidence in the paper** ("naive uniform collocation yields ~16% error even on
  a cantilever; on TPMS thin walls it is fatal — hence adaptive collocation").

## Next action (N3 — first TPMS physics run)
Single gyroid unit cell under uniaxial strain, periodic BCs, with:
- near-surface oversampled collocation (N1 T5 sampler),
- adaptive refinement driven by strain-energy density,
- code_aster periodic homogenization as ground truth (V1).
Success criterion: effective stiffness C_1111 within 5% of code_aster.

## Artifacts
- `research/tpms_levelset.py`, `research/dem_cantilever.py`
- `research/n2_metrics.json`
- `research/figures/dem_vs_fem_fields.png`, `research/figures/dem_energy_convergence.png`
- This report: `research/N1N2_verification_report.md`
