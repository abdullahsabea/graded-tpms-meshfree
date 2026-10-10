# 04_preregistered_plan.md — VG-MM primary experiment (EXP-02)

**Frozen:** 2026-09-13, BEFORE any new FE solve or new DEM search run.
Any later change to this file must be logged in `decisions.log` as
exploratory and cannot alter the primary outcome label.

## Frozen hypotheses

- **H1 (primary):** DEM-ranked + per-move-FE-verified coordinate search
  (VG-MM) returns a design with FE-verified gain G_confirm > the existing
  verification-band-restricted design's +1.58% at ≤30 FE calls.
- **H0:** G_confirm ≤ +1.58% (equivalence within scatter) — VG-MM adds no
  verified value beyond the band restriction.
- **H2 (safety, by construction):** the returned design is never
  FE-negative vs uniform at the confirm grid; every accepted move is
  FE-confirmed at the search grid.

## Independent / dependent variables

- IVs: search policy (VG-MM; comparators use archived results), mode index
  m=0..11, sweep s=0..1, trial grid value; DEM scoring cloud seed
  (sensitivity only).
- DVs: C1111_ENERGY (64³/96³, discrete-Vf calibrated), gains in %, FE-call
  count, acceptance/rejection events, DEM rank vs FE verdict per checkpoint.

## Baselines and comparators (matched design space; archived evidence)

| Arm | Definition | FE calls | Verified result (existing SoT) |
|---|---|---|---|
| A. Uniform baseline | theta=0 | 1 per grid | 0.10528 (64³), 0.10572 (96³) |
| B. DEM-only | existing unconstrained design (Stage1+2, DEM ranking) | 0 in-loop (+4 ladder audit) | −4.37% mean per-grid (FE ladder) |
| C. Band-restricted DEM | existing printable design | 0 in-loop (+4 ladder audit) | +1.58% mean per-grid |
| D. FE-in-loop | 195-call coordinate search | 195 | +6.55% (64³), +6.34% (96³) |
| E. **VG-MM (new)** | this protocol | ≤30 | **to be measured** |

## Exact design bounds and shared candidate space (frozen)

- 12 Fourier coefficients; modes order `[(1,0,0),(0,1,0),(0,0,1),(1,1,0),(1,0,1),(0,1,1)]`
  (cos,sin pairs — identical to `e3_fe_baseline.py`).
- Trial grid `linspace(-0.22, 0.22, 9)`; sweeps=2; bounds t∈[0.12,0.55];
  Vf*=0.19328 discrete-calibrated per candidate by 28-iteration bisection
  of the uniform offset on [−0.30, 0.30] (identical implementation).
- KUBC uniaxial x1, EPS=1e-3 (FE), E=1, nu=0.3; energy basis
  (C1111_ENERGY from homog2.comm output) only.

## VG-MM protocol (frozen pseudo-code)

```
theta = zeros(12); FE-budget B = 30 calls
score(theta) = 2*mean(w*psi)/EPS^2 on fixed 50k cloud (seed 11),
               w = sigmoid((clip(0.30+shift+sum theta_m psi_m, bounds) - |F|)/0.02)
incumbent = theta; best_FE = FE(64, theta, bisect64(theta))        # call 1 (cached value OK)
for s in 0..1:
  for m in 0..11:
    trials = {theta with theta[m] = g, g in GRID}
    dem_rank = sort trials by score desc
    cand = first trial in dem_rank whose theta[m] differs from incumbent theta[m]
           (if all equal incumbent: record no-move, 0 FE calls)
    fe_val = FE(64, cand, bisect64(cand))                          # 1 call (cache counts as call)
    if fe_val > best_FE: incumbent = cand; best_FE = fe_val; log ACCEPT
    else: log REJECT (incumbent unchanged)
confirm: FE(96, incumbent, bisect96(incumbent)); uniform 96 already archived
G_confirm = 100*(C_inc/0.10572287959 - 1)
```

- Radius response: preregistered as *record-only* (accept rate per mode);
  no adaptive shrink in the primary (simplicity frozen before results).
- The "skip equal-to-incumbent" rule prevents wasted calls; fixed a priori.

## Primary and secondary metrics

- **Primary:** G_confirm (%) at 96³ vs archived uniform 96³.
- Secondary: FE-call count; gain-per-call = G_confirm / unique-64³-calls;
  DEM false-rejections (DEM top pick that FE would have accepted) count;
  acceptance trajectory monotonicity; regret vs best FE-verified design in
  the reconstructed 195-candidate pool (REPLAY join); sensitivity of DEM
  picks to cloud seeds {12,13} (pick-agreement %; no FE unless a pick
  change would alter the returned design, then ≤2 extra calls, logged as
  exploratory).

## Success / failure / equivalence / inconclusive thresholds (frozen)

| Branch | Criterion on G_confirm | Claim allowed |
|---|---|---|
| STRONG PASS | ≥ +5.84% (matches FE-in-loop 96³ 6.34% within 0.5%) | VG-MM reaches full-FE-search verified gain at ≤30 calls on this problem |
| PASS | > +1.58% and < +5.84% | VG-MM beats band-restricted DEM design at ≤30 calls; below full FE search |
| EQUIVALENCE | +0.88% ≤ G ≤ +1.58% | no verified advantage over band restriction |
| FAIL | < +0.88% | protocol adds nothing beyond band restriction here |
| INCONCLUSIVE | harness failure / budget exhaustion | preserve logs; BLOCKED row |
Safety claim (H2) evaluated independently: PASS iff zero FE-negative
accepted moves and G_confirm > 0.

## Seed plan

Canonical cloud seed 11 (identical to archived optimizer). Sensitivity:
seeds 12, 13 (DEM only). No training-seed reruns in EXP-02 (logged
limitation; MS-SEED reduced scope covers quadrature sensitivity).

## FE mesh/resolution and volume-calibration plan

Search/checkpoints 64³; confirm 96³; per-candidate discrete-Vf calibration
to 0.19328 by bisection (28 iters). No Richardson extrapolation; ladder
scatter treated as reported in the manuscript.

## Compute / time budget

≤ 40 new FE solves; wall clock ≤ 2 h; single desktop, docker code_aster,
6 workers max (checkpoint calls are sequential by algorithm; confirm batch
parallel ≤6).

## Exclusion rules (frozen in advance)

- Bisection failure or degenerate Vf → exclude candidate, log row.
- FE solve failure → 1 retry; second failure → INCONCLUSIVE branch.
- Cache .mess parse failure → treat as solve failure (above).
- No candidate or result may be excluded post hoc for its value.

## Planned tables and figures

- T1: comparator table A–E (calls, verified gains, primary metric).
- T2: VG-MM checkpoint log (sweep, mode, pick, DEM score, FE verdict).
- F1: verified-gain vs FE-call budget (A–E + pool frontier from REPLAY).
- F2: DEM-vs-FE discordance over the reconstructed pool.

## Claim changes allowed per branch (frozen)

- STRONG/PASS: manuscript gains a new method section (VG-MM) + new results;
  title may gain "verification-guided" justification it currently over-
  reaches for; abstract rewritten around the algorithm + budget evidence.
- EQUIVALENCE: report as honest negative; keep case-study framing; add
  protocol + frontier figure as methodological contribution; do NOT
  upgrade title claims.
- FAIL: keep title change modest; frame as "verification-guided
  acceptance prevents harm but does not beat restriction at this scale";
  preserve all negative detail.
- INCONCLUSIVE: no manuscript claim changes; document blocker.
