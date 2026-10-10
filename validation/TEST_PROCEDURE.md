# Tensile test procedure, TPMS dog-bone pair (uniform vs constrained graded)

> **Executed-protocol amendment (recorded 2026-08-25, post-execution).**
> This procedure pre-registers 1 mm/min, three load--unload cycles and
> video-track strain. The executed campaign ran **monotonic to the
> displacement limit at 3.00 mm/min on seven of eight records (~1.0
> mm/min on U1)**, with E* taken from a 150--600 N loading-branch
> regression on the crosshead signal (the video endpoint failed quality
> control). Measured per-specimen rates: `validation/table8_results.json`.
> The pre-execution text below is the plan of record and is kept
> verbatim; the reasons for the deviations are not recorded in this
> repository.

**Machine: Instron 8852** (servo-hydraulic axial–torsion frame, ±100 kN,
hydraulic wedge grips), the E10000 grips did not fit the 160×45×15 mm
plate coupons. **Strain: smartphone video tracking of the two horizontal
witness grooves** (100 mm span). Companion tracker: `track_lines.py`.

Specimens: U1–U4 (uniform t = 0.30), O1–O4 (constrained graded), all
printed, weighed (EXPERIMENTAL_VALIDATION.md §11). Pre-registered bands:
R ≈ 1.08 (DEM) / 1.01 (FE periodic + effective-medium) / 0.86 ± 0.04
(resolved-wall). Confirmatory question: **resolved-wall vs periodic**.
DEM-vs-FE is exploratory at n = 4.

---

## A. Before test day (30 min)

1. Confirm data availability: ≥ 30 GB free on the phone (4K60, ~6 min
   per specimen at the slower rate ≈ 2-3 GB each × 8 + margin).
2. Charge phone to 100%; bring power bank, tripod, ruler, two lamps,
   white paper (diffusers), calipers, lab notebook.
3. Instron: request the **smallest calibrated load cell** available for
   the 8852. If only the standard high-capacity cell is installed,
   schedule a working-range verification (step C2).
4. Print this file and the per-specimen run sheet (§F); pre-label 8 data
   folders: `U1..U4`, `O1..O4`.

## B. Specimen prep (each of the 8, ~10 min total)

1. Weigh (± 0.01 g), already done for build 1; re-weigh if specimens
   were handled since; record.
2. Caliper the actual groove spacing: hook the caliper jaws into the two
   grooves, 3 readings, record mean as that specimen's **L0** (nominal
   100.0 mm). The tracker uses this value.
3. Photograph each face; confirm both grooves are visible over the full
   width and darker than the surrounding surface. If a groove segment is
   shiny/washed out on the camera test frame (step D), darken it with a
   fine permanent marker run along the groove, identical treatment on
   both grooves, both groups.
4. Check the orientation ridge is on the same edge for all specimens
   (the ridge marks x1; the loading axis).

## C. Machine setup (once)

1. **Grips.** Hydraulic wedge grips, flat faces. Set closing pressure to
   the low end of the face spec (plate coupons: moderate pressure only
   the shoulders are solid PETG, 45 mm wide; the goal is no slip without
   crushing). Record grip pressure used; keep it identical for all 8.
2. **Load channel verification at working range** (mandatory on a
   ±100 kN frame measuring hundreds of N):
   - With the lower grip stationary, hang a known mass (e.g., 2 × 5 kg
     calibrated masses = 98.1 N, then 4 × = 196.1 N) from the lower grip
     via a cord, record the reading at each; then verify at ~500 N with
     a calibrated proving ring or a spring of known stiffness if
     available.
   - Record readings in the notebook; require linearity within 1% at the
     two mass points. The R-ratio read-out cancels residual scale error
     between groups, but only if the channel is linear, that is what
     this check establishes.
3. **Control mode:** stroke (displacement) control. **Rate: 1 mm/min**
   (≈1.7×10⁻⁴ /s over the 100 mm span; lowered from the drafted 6 mm/min before the first specimen - safer in the elastic range; R is a same-rate ratio, so the choice does not affect the comparison).
4. **Protection limits:** load limit 3 kN (well above cycle peak,
   far below specimen damage threshold on yield), travel limits set so
   the actuator cannot drive the grips together.
5. **Data acquisition:** force + displacement + time at ≥ 10 Hz, CSV
   export per specimen.

## D. Camera setup (once, then verify per specimen)

1. Tripod ~**25–35 cm** from the coupon face, lens at mid-gauge height,
   optical axis normal to the face (check: both grooves and the ruler
   stay sharp; no keystone, the coupon's left and right edges vertical).
2. **Ruler** taped to a stand in the specimen plane (same distance to
   camera as the coupon surface), inside the frame beside the coupon.
3. Lighting: two lamps bounced off white paper from left and right
   (~45°); no direct reflection on the PETG. If bands flicker in the
   viewfinder, move to DC/undimmed lamps.
4. Phone settings: **4K / 60 fps, rear (wide, 1×) camera**, airplane
   mode, screen locked against accidental touch, **AE/AF locked**
   (tap-hold on the coupon until the banner), no timer, no HDR video
   extras if selectable.
5. Field check: record 5 s, inspect one frame, both grooves fully
   visible, ≥ 4 px wide each (they will be ~5 px at this geometry),
   ruler readable. Expected scale ≈ 6–7 px/mm → strain resolution
   ≈ 1 × 10⁻⁴ over the span.

## E. Per-specimen procedure (≈ 6 min each at 1 mm/min; cycles alone ~3 min)

Run order: **interleaved, U1, O1, U2, O2, …, U4, O4** (decorrelates any
drift in machine, lighting, or camera position between groups).

1. Mount the coupon: shoulders fully inside the grips by ~20 mm, the two
   witness grooves between the grips, orientation ridge aligned with the
   loading axis, gauge centered side-to-side. Same grip insertion depth
   for all 8 (mark the insertion line with tape on the grip faces).
2. Close grips (pressure from C1), then apply and release a 5 N preload
   twice to seat; zero force and stroke.
3. Start the video, **wave a hand across the frame once** (sync trigger),
   then start the test program.
4. **Seating ramp:** ramp to 150 N at 1 mm/min, hold 10 s, unload to
   5 N. Inspect the video strain vs force slope, if it changed during
   the ramp (seating), it will not affect E*, which uses the final cycle.
5. **Cycles:** three load–unload cycles in displacement control between
   fixed stroke limits corresponding to roughly 0.05 % and 0.45 % span
   strain (≈ 0.05–0.45 mm crosshead travel; at the expected span
   stiffness this is ≈ 50–650 N on the uniform group, ≈ 5 % lower force
   on the graded group at the same stroke). Identical limits for all 8
   specimens. If the force–video-strain curve departs from linearity
   (> 2 % local slope change) below the upper limit on the first uniform
   specimen, drop the upper limit to 70 % of the nonlinearity onset and
   restart that specimen (note it; keep the reduced window for **all**
   specimens from then on).
6. **Final unload** to 5 N, hold 10 s, stop the test program, stop the
   video.
7. Photograph the specimen in the grips (grip depth, alignment record),
   then release and remove.
8. Copy video + CSV into the specimen folder before the next mount.
   Confirm video length ≈ test length.

## F. Per-specimen run sheet (copy per specimen)

```
Specimen: __   Group: U / O   Date/time: __________
Mass [g]: ______ (re-weighed? Y/N)   L0 calipered [mm]: __.__ (3 readings)
Grip pressure [bar]: ____   Grip insertion [mm]: ____
Stroke cycle limits [mm]: ____ – ____   Rate [mm/min]: 1
Cycle peak forces [N]: 1) __ 2) __ 3) __
Video file: _________   CSV file: _________
Hand trigger visible at frame: ____ (approx.)
Notes (slip, marker touch-up, restarts): ________________________
```

## G. Analysis (after all 8)

1. **Scale calibration** (per camera position; once if the tripod is
   untouched, else per specimen): `python track_lines.py calibrate
   <video> --click`, click the ruler's 0 and 100 mm marks; the script
   stores px/mm.
2. **Tracking**: `python track_lines.py track <video> --l0 <calipered
   L0 mm> --out U1.csv`, click once near each groove on the first
   frame; the tracker follows both lines with sub-pixel template
   matching and writes frame, time, span[mm], strain. Sanity-check the
   strain trace (monotone ramps, flat holds, no jumps).
3. **Sync**: the hand trigger marks video time ≈ test start; align video
   strain(t) with force(t) by matching the seating ramp onset (first
   departure from 5 N). Cross-check the final unloading slope against
   the same slope from crosshead displacement, machine compliance makes
   the crosshead slope systematically softer; only the video slope is
   used for E*.
4. **E\*** per specimen: linear regression of force vs video strain over
   40–90 % of the final unloading branch; E* = slope × L0 / A_ref with
   A_ref the gauge cross-section (30 × 15 mm) used identically for both
   groups (the ratio R is insensitive to the area convention).
5. **R**: mean(E*_O)/mean(E*_U), 95 % CI by Welch t and by bootstrap
   over the 4 × 4 pairs; report both.
6. **Mass sensitivity** (secondary): regress E* on mass over the pooled
   8 points; report the mass-adjusted R with the regression uncertainty
   propagated, labelled sensitivity analysis, the between-group mass
   contrast (0.26 %) is near the within-group scatter, so the adjustment
   is weakly identified; never let it replace the raw value.
7. **Verdict rule (pre-registered, do not modify post hoc)**:
   - R CI excludes 1.08 and overlaps neither band → report against the
     nearest pre-registered band.
   - R significantly < 0.95 → supports resolved-wall; the periodic
     +1.6 % survives only as a homogenization-level statement.
   - R ≈ 1.0 (CI within ±5 points of 1.01) → supports FE periodic/EM;
     DEM band excluded if CI excludes 1.08.
   - R between 1.05 and 1.12 or CI spans both 1.01 and 1.08 →
     **inconclusive between DEM and FE**; report exactly that. The
     confirmatory resolved-wall-vs-periodic question stands on its own.
8. Fill Table 8 of the manuscript; rerun `paper/check_consistency.py`;
   rebuild.

## H. Troubleshooting

| Symptom | Fix |
|---|---|
| Groove fades at one end (lighting) | Re-aim diffusers; if needed, marker the groove (both grooves, all specimens identically from then on, note the change) |
| Tracker loses a line mid-video | Re-run `track` with a click restart at the loss frame (script supports `--start-frame`); or darken groove and reshoot only if the specimen has not been cycled |
| Slip (force drop at constant stroke) | Increase grip pressure one step for ALL remaining specimens, note it, restart current specimen from seating ramp |
| Video corrupt / phone storage full mid-test | Stop test, keep specimen unloaded; if cycles were incomplete, re-run the full program on that specimen after freeing space (elastic protocol permits re-tests; note re-test in the sheet) |
| Force reading non-linear at verification masses | Do not test; recalibrate / swap load cell first |
| Parallax doubt (camera not normal) | Re-check by sliding a ruler along the face: its image must translate without the groove positions changing |
