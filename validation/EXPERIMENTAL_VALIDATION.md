# Experimental validation plan: printed compression test of the optimized graded gyroid

Status: protocol v3, 2026-08-17. Companion files: `make_specimen_stl.py`,
`specimen_uniform_t0.30.stl`, `specimen_graded_opt.stl`.

> **Executed-protocol amendment (recorded 2026-08-25, post-execution).**
> The campaign below was drafted at 1 mm/min, but the raw exports show it
> was **executed at 3.00 mm/min on seven of the eight records and at
> ~1.0 mm/min on U1** (measured from the loading branches of
> `TO_AI-results_instron/TO_AI/U_1_Exports/*.csv`; per-specimen rates,
> window sample counts and peaks are tabulated in
> `validation/table8_results.json`, `per_specimen[*].executed_rate_mm_min`).
> U1's slower rate is also visible as its 2221 in-window samples against
> 736--823 on every other record. The loading was additionally executed
> monotonic to the displacement limit (no load--unload cycles), with E*
> taken from a 150--600 N loading-branch regression; the smartphone-video
> strain endpoint did not survive quality control and the delivered
> analysis is crosshead-based. All of these deviations are disclosed in
> the manuscript (Table `tab:deviations`); the reasons are not recorded
> in this repository. Nothing else in this plan-of-record document has
> been rewritten: the 1 mm/min and cyclic text below is the pre-execution
> plan, kept verbatim.

> **Protocol v3 change (2026-08-17).** The printed dog-bones do not fit the
> Instron E10000 grips. The test moves to the **Instron 8852**
> (servo-hydraulic axial-torsion frame, +/-100 kN, hydraulic wedge grips),
> and strain is measured by tracking the two horizontal witness grooves
> from **4K smartphone video** instead of a clip-on extensometer
> (procedure: `TEST_PROCEDURE.md`, tracker: `track_lines.py`). The
> manuscript Section 5 has been updated to match (v4), including the
> honest power statement: confirmatory = resolved-wall-vs-periodic;
> DEM-vs-FE is exploratory; raw R primary, mass-adjusted R a sensitivity
> analysis. Crosshead rate is 1 mm/min (lowered from the drafted 6 mm/min
> before the first specimen; R is a same-rate ratio, so the bands are
> unaffected).

> **Basis note (v2, 2026-08-03).** Every stiffness number in this document has
> been revised to the Hill-Mandel energy basis, C1111 = 2U/(V eps^2). Protocol
> v1 quoted the summed loaded-face reaction, which is exact only on homogeneous
> bodies and on these porous cells is wrong by +2.7% (uniform gyroid) and
> +15.4% (graded optimum) -- large enough that it **inverted the sign** of the
> headline result. All values below now come from
> `research/n3/paper_numbers.json` (`"basis": "hill-mandel-energy"`), generated
> by `research/n3/paper_numbers.py`. Do not reintroduce face-sum numbers, and
> do not quote a stiffness figure here that is not traceable to that file.

## 1. Objective and the key design of the experiment

The claim under test is a **ratio**, not an absolute number: at equal volume
fraction (Vf = 0.193), how does the optimized graded gyroid compare with the
uniform gyroid in the x1 direction? The experiment compares **two specimen
groups printed in the same build** and measures the stiffness ratio

    R = E*_graded / E*_uniform

Testing the ratio (instead of absolute stiffness) cancels the dominant
experimental unknowns: base material modulus, print-process softening,
layer anisotropy, and machine compliance all appear in both numerator and
denominator. This is the same logic the paper uses when it validates design
ranking rather than absolute values.

**The two models disagree in sign, and that is now the point of the
experiment.** For the Track A pair (`specimen_graded_opt.stl`, built from the
unconstrained coordinate-search optimum `e3_coord_search.json`, vs
`specimen_uniform_t0.30.stl`):

| | C1111 uniform | C1111 graded | predicted R |
|---|---|---|---|
| FE (voxel KUBC, energy basis) | 0.105542 | 0.100930 | **0.956** (-4.4%) |
| DEM (mesh-free surrogate) | 0.1139 | 0.1338 | **1.175** (+17.5%) |

The mesh-free surrogate predicts a large stiffness *gain*; FE verification of
the same geometry says it is *softer* than the uniform baseline. The models
differ by 21.8 percentage points and by sign, because the optimizer exploited
the surrogate's thin-wall bias in exactly the regions where that design
saturates at t_min. **A physical test that resolves a sign disagreement is a
much stronger result than one confirming a single-digit percentage**, and it
is the experiment this specimen pair is actually able to perform.

Expected outcome bands:
- R below 1.00: confirms FE, and confirms that mesh-free optimization *without*
  FE verification produced a design worse than its own baseline -- the
  manuscript's reframed headline.
- R near 1.15-1.18: confirms DEM and impeaches the FE pipeline; would require
  re-examining the KUBC voxel protocol before anything else is published.
- R in 1.00-1.10: inconclusive between the two; fall back on the as-printed
  CT/FE comparison (Section 4.3) to apportion the gap between geometry error
  and model error.

Sample-size consequence: separating FE from DEM here (21.8 pp) is trivial and
needs only n = 1-2 per group. Establishing that R is *significantly below 1.00*
(a 4.4% effect) is much harder -- see Section 6.3. Protocol v1's "n = 5
detects the effect with power > 0.9" was computed against the erroneous +9.1%
and no longer holds.

## 2. Specimens

| | uniform | graded (optimized) |
|---|---|---|
| geometry | gyroid sheet, t = 0.30 | t(x) with theta* from E3, delta_t0 = -0.0094 |
| tessellation | 4 x 4 x 4 unit cells | same |
| cell size | 20 mm | same |
| bounding box | 80 x 80 x 80 mm | same |
| volume fraction | 0.1930 | 0.1929 (0.02% apart) |
| solid volume | 98.8 cm^3 | 98.8 cm^3 |
| wall thickness min/med/max | 1.12 / 1.30 / 1.39 mm | 0.44 / 1.04 / 2.70 mm |

Both STLs carry a 1.2 mm ridge along one edge parallel to **x1** (the
optimized loading direction). The ridge is identical on both specimens, adds
under 0.1% volume, and removes any ambiguity about orientation after
depowdering. The graded field is periodic, so the tessellation has no
thickness discontinuities at cell boundaries.

Replicates: **n = 5 per group, 10 specimens total**, all in a single build,
placement randomized across the platform (do not cluster one group in one
corner; thermal history varies across the bed). If build volume forces two
builds, put equal numbers of both groups in each build.

## 3. Printing

Recommended processes, in order of preference:

1. **MJF or SLS, PA12.** Self-supporting TPMS, no support removal, quasi-
   isotropic material. Minimum wall of the graded specimen is 0.44 mm, which
   is at the capability edge of powder-bed polymer processes (typical
   guideline 0.5 mm). Options: (a) accept and quantify (Section 4), or
   (b) regenerate at L_CELL = 25 mm (min wall 0.56 mm, 100 mm cube).
2. **SLA/DLP resin.** Resolves 0.44 mm walls comfortably; use a rigid resin
   and identical post-cure for all 10 specimens; drain holes are not needed
   (gyroid pores are fully interconnected).
3. Metal LPBF only if a metals lab is the target venue; not required for the
   validation logic.

Same build orientation for all specimens (x1 in-plane, recorded), same batch
of powder/resin, same slicer profile. The STL files are ~250 MB (5.2 M
triangles at 64 samples per cell); regenerate at other resolutions or cell
sizes by editing two constants in `make_specimen_stl.py`.

## 4. Metrology before testing (this is what reviewers will ask for)

1. **Mass** of every specimen (+/- 0.01 g). Iso-volume is the constraint of
   the whole optimization; demonstrate it experimentally:
   mass_graded / mass_uniform should be 1.000 +/- 0.01. Report the actual
   relative density vs the design value 0.193 (powder-bed prints typically
   come out a few percent heavy at thin walls).
2. **Outer dimensions** with calipers (shrinkage/scale factor).
3. **Wall thickness spot checks**: optical microscope or micro-CT on one
   sacrificial specimen per group. Critical for the graded specimen at the
   t_min = 0.12 regions; if printed walls there are systematically thicker
   than designed, the realized geometry is between "graded" and "uniform"
   and R will shrink accordingly. A micro-CT of one specimen per group,
   registered against the analytic level set, is the single highest-value
   measurement in this plan and directly reuses the paper's voxel pipeline
   (the CT voxel field can be run through the same code_aster KUBC analysis:
   as-printed FEM vs as-designed FEM separates geometry error from model
   error).

## 5. Mechanical test protocol

Standard: **ISO 13314** (compression of cellular materials) adapted to
polymer AM lattices; ASTM D1621 as the polymer-foam alternative.

- Quasi-static compression along **x1** (the marked axis), nominal strain
  rate 1e-3 /s (4.8 mm/min for the 80 mm specimen).
- Hardened, ground platens; thin PTFE film or grease at both interfaces to
  reduce friction confinement.
- **Strain from optics, not crosshead**: video
  extensometer between platen-adjacent gauge marks. Machine compliance is
  the classic artifact in lattice modulus data.
- Loading program per ISO 13314: preload to ~0.05 MPa nominal stress, then
  **three load-unload cycles** between approximately 20% and 70% of the
  expected proportional limit; take the **unloading modulus** of the final
  cycle as E*. Unloading modulus is far less sensitive to early local
  plasticity and seating than the initial loading slope.
- Continue the final loading to 10-20% strain to record the plateau; energy
  absorption is a free secondary result (TPMS literature values it), but it
  is not part of the validation claim.

## 6. Data analysis

1. E* per specimen from the unloading slope (stress = F/A0 with
   A0 = 80 x 80 mm nominal; consistent for both groups, so the ratio is
   unaffected by the area convention).
2. R = mean(E*_graded) / mean(E*_uniform) with a 95% CI via Welch's t /
   propagation, or bootstrap over the 5 x 5 specimen pairs.
3. Compare against three model values, all at Vf = 0.193:
   - FEM (as-designed, energy basis): R = 0.100930 / 0.105542 = **0.956**
   - DEM (mesh-free): R = 0.1338 / 0.1139 = **1.175**
   - FEM (as-printed CT geometry, if Section 4.3 is done): the tightest
     comparison, isolating solver error from print error.
4. Report absolute E* too (with the measured base-material modulus from
   printed dogbones if available), but frame the validation on R.

### 6.3 Power, recomputed on the energy basis

Minimum detectable difference in E*, two-sample, alpha = 0.05, power = 0.8:

| n per group | CV = 2% | CV = 3% | CV = 4% | CV = 5% |
|---|---|---|---|---|
| 3 | 4.6% | 6.9% | 9.1% | 11.4% |
| 4 | 4.0% | 5.9% | 7.9% | 9.9% |
| 5 | 3.5% | 5.3% | 7.1% | 8.9% |
| 8 | 2.8% | 4.2% | 5.6% | 7.0% |
| 13 | 2.2% | 3.3% | 4.4% | 5.5% |

Required n per group, by comparison:

| comparison | effect | CV 2% | CV 3% | CV 4% | CV 5% |
|---|---|---|---|---|---|
| Track A: FE vs DEM | 21.8 pp | 1 | 1 | 1 | 1 |
| Track A: FE vs null (R < 1) | 4.4% | 4 | 8 | 14 | 21 |
| Track B: FE vs DEM | 7.1 pp | 2 | 3 | 5 | 8 |
| Track B: FE vs null (R > 1) | 1.6% | 26 | 57 | 101 | 158 |

Read this before deciding what to claim. **Model discrimination is cheap;
proving the sign of the gain against zero is expensive.** Frame both tracks
as FE-vs-DEM adjudication, and treat "is the optimized design actually better
than uniform" as a question the FE answers and the experiment merely fails to
contradict. Measure CV from the first pair tested and re-enter this table
before committing to a specimen count.

## 7. Known gaps between model and experiment (state them, do not hide them)

- **Boundary conditions**: the paper's C1111 is a single-cell KUBC (affine
  displacement) bound; the experiment is a finite 4x4x4 array between
  platens (mixed conditions, free lateral faces). The comparison of ratios
  largely cancels this, but for the paper's discussion: KUBC is an upper
  bound, and the half-cell boundary layer at free faces softens both groups
  similarly. A finite-specimen FE model of the full 4x4x4 array (same voxel
  pipeline, platen-contact BCs) closes this gap completely if a reviewer
  presses; it is a large but tractable solve.
- **Linear vs real material**: E* is extracted in the small-strain elastic
  range precisely so the linear-elastic model applies.
- **Direction**: the gain is directional (C1111). Optionally test 3
  additional specimens per group along x2 to show the contrast between the
  optimized direction and a non-optimized one; a directional signature
  matching the model is stronger evidence than a single ratio.

## 8. Effort and cost estimate

10-13 polymer prints of ~100 g each, one build day on an MJF/SLS bureau or
two days on a desktop SLA, one micro-CT session (optional but recommended),
and one day on a universal testing machine with video extensometry. No custom fixtures.

## 9. Track B: FDM dog-bone demonstrators (accessible, desktop-printer route)

Companion files: `make_dogbone_stl.py`, `dogbone_uniform.stl`,
`dogbone_optimized.stl`, `dogbone_preview.png`.

Where Track A (compression cubes, Sections 2-6) is the rigorous
quantitative test, Track B is a demonstrator that any FDM printer can
produce and any tensile machine can pull, and it showcases a point the
paper can make in one sentence: the specimen itself is generated by the
paper's own thickness-grading mechanism, with no CAD. Ramping t(x) above
max|F| = 1.5 turns the level set solid, so the solid grip ends, the
filleted transition, and the TPMS gauge all come from the single analytic
equation phi = max(phi_outline, |F(kx)| - t_spec(x)).

Specimen pair (identical outline, gauge volume fractions 0.1926 vs 0.1929):

| | value |
|---|---|
| overall / thickness | 160 x 45 x 15 mm plate dog-bone |
| gauge section | 60 x 30 x 15 mm = 4 x 2 x 1 cells of 15 mm |
| fillet radius | 25 mm; t(x) ramps to solid over the 30-40 mm band |
| gauge lattice | uniform t = 0.30 vs optimized graded theta* |
| tensile axis | x1, the optimized C1111 direction |
| mass (PETG) | ~78 g each |

Printing (FDM, PETG, 0.4 mm nozzle): print flat, 0.15-0.2 mm layers,
100% infill with 2+ perimeters (the lattice walls themselves become
perimeter paths), no supports needed inside the gauge (the gyroid is
self-supporting; it is literally the geometry behind slicers' "gyroid
infill"). Same spool, same profile, same plate position class for both.
Caveat to record: the thinnest graded walls (t_min regions, ~0.34 mm
designed at this cell size) will print at nozzle width; weigh both parts
and report measured masses next to the designed 0.17% volume difference.

Marker placement: both STLs now carry a shallow witness groove
(0.8 mm wide, 0.4 mm deep, scribed across the full top-face width) at
x1 = 30 mm and x1 = 130 mm, i.e. 50 mm either side of the specimen
center, printed identically on both parts. These lines sit on the flat,
fully solid shoulder just past the lattice-to-solid transition and
fillet (which end by |x1-80| = 48 mm), so they are trackable,
non-porous surface -- unlike the lattice gauge itself, which is too
curved and open for reliable 2D marker tracking. Clip an extensometer
to these two lines, or paint a dot on each for video tracking; the
100 mm span between them is the reference gauge length for both
specimens.

Because this 100 mm span includes the graded transition and a few
millimetres of shoulder in addition to the 60 mm pure-lattice band, the
measured apparent modulus is diluted by the (identical, stiffer, fully
solid) shoulder material, which is common to both specimens. The
springs-in-series consequence is directional: **dilution compresses the
measured ratio toward 1.000 from whichever side the true ratio sits on.**
A true R > 1 is measured lower; a true R < 1 is measured higher. It does
not simply "reduce" R. Report the dilution explicitly and do not compare
the raw measured ratio to a bulk KUBC value of any kind -- the correct
comparison is a finite-specimen FE model of this exact dog-bone over this
exact 100 mm span (Section 9.2), which reproduces the dilution instead of
apologising for it.

That model has now been run, and the effect is **much smaller than this
section originally assumed: 94% of the bulk signal survives** (+1.58%
bulk becomes +1.48% as measured). Series compliance is dominated by the
compliant lattice, not by the stiff shoulder. See Section 9.2.

Test: tension at 1 mm/min (≈1.7e-4 /s over the 100 mm span; lowered from the drafted 6 mm/min before the first specimen, R unaffected as a same-rate ratio) on the
Instron 8852, with the two
witness lines tracked from 4K smartphone video (Section 12 and
`TEST_PROCEDURE.md`); three load-unload cycles in the elastic range; report
the gauge-section stiffness ratio graded/uniform, n >= 3 pairs.

Printing position: print flat with x1 (loading axis) and x2 (width) in
the bed plane, x3 (15 mm thickness) vertical, i.e. layers stack along
the thickness and each layer is a full x1-x2 slice. This keeps the
loading direction in-plane within every layer instead of across
interlayer bonds, which is the standard best-practice orientation for
FDM tensile coupons -- printing with x3 in-plane (layers perpendicular
to the pull direction) would test interlayer adhesion strength instead
of the material/lattice stiffness and must be avoided. No supports are
needed; the gyroid gauge and the fillets are self-supporting. Use the
identical orientation, plate location, and settings for both
specimens.
Expectations and caveats: the single-cell thickness and free lateral
surfaces make this a structural comparison rather than a homogenization
measurement, so the measured ratio is compressed toward 1.000 relative to
the bulk KUBC values (Section 9.1) and must not be compared to them
directly. The claim this track can demonstrate is **which model is right
about the size of the gain**, plus a visible, printable artifact of
mesh-free geometry-parameter optimization. It cannot, at any realistic
specimen count, establish that the graded design is significantly stiffer
than uniform (Section 6.3). For the journal-grade number, use Track A.

## 9.1 Third specimen: manufacturability-constrained gauge (recommended
for printing)

`dogbone_optimized.stl` uses the paper's headline theta* (t in
[0.12,0.55]), which pushes 32% of the gauge domain to t_min and 22% to
t_max (Table 4 in the manuscript). This creates locally steep
thickness gradients that override the base gyroid's self-supporting
property -- confirmed both by an overhang-area check (15.2% of gauge
surface >45 degrees from horizontal, vs 14.0% for the uniform design)
and by this design specifically triggering a slicer "floating
regions" warning that the uniform design does not.

`dogbone_optimized_printable.stl` (`research/n3/e3_optimize_printable.py`)
re-solves the same problem with the thickness bounds narrowed to
[0.20,0.45] (both anchors already FE-verified, Table 3) and an
explicit closed-form smoothness penalty lambda_g * mean(|grad_x
t(x)|^2) added to the objective -- grad(t) is exactly the term that
tilts the level-set surface normal toward horizontal
(grad(phi) = sign(F) k grad(F) - grad(t)), so penalizing it directly
targets the mechanism, not just a symptom. Result: overhang area drops
to 14.6% (uniform: 14.0%), essentially closing the gap.

Verified by the same code_aster protocol as everything else in the
paper (N48/N64/N96/N128 voxel meshes, KUBC, identical boundary
conditions), on the Hill-Mandel energy basis, averaged across grids:

| | C1111 | DEM predicted | **FE verified** |
|---|---|---|---|
| uniform t = 0.30 | 0.105542 | -- | -- |
| unconstrained (`dogbone_optimized.stl`) | 0.100930 | +17.5% | **-4.4%** |
| constrained (`dogbone_optimized_printable.stl`) | 0.107214 | +8.7% | **+1.6%** |

This table is the paper's central result and it says something quite
different from protocol v1. The mesh-free surrogate predicts a large gain
for both designs. FE verification finds that the unconstrained design --
the one the optimizer liked best -- is actually **softer than its own
baseline**, and that the manufacturability-constrained design delivers a
real but small gain of +1.6%.

The pattern is diagnostic, not noise: the DEM's overprediction scales with
how hard each design saturates at t_min (+21.8 pp of error for the
unconstrained design at t_min = 0.12, +7.1 pp for the constrained one at
t_min = 0.20), which is exactly where the mesh-free model's thin-wall bias
lives. The optimizer was not finding stiffness; it was finding the
surrogate's error term and driving the design into it. Narrowing the
thickness bounds and adding the gradient penalty removed most of the
exploitable region, which is why the constrained design both prints better
*and* verifies better.

**Use `dogbone_optimized_printable.stl` as the optimized specimen for
printing**: it is the only variant whose gain survives FE verification,
and it is self-supporting like the base gyroid, needing no support
material.

### 9.2 Finite-specimen model: RESULTS (`finite_specimen_fe.py`, 2026-08-03)

Neither number in the table above is directly comparable to what the Instron
measures: both are single-cell KUBC bounds, while the measurement spans 100 mm
of dog-bone including solid shoulder. `finite_specimen_fe.py` closes that gap
in two independent ways -- springs-in-series closed form, and 3D continuum FE
on the real outline (fillets, shoulders, clamped grips; voxel HEXA8 with
cut-cell area weighting, AMG-preconditioned CG). Results
(`finite_specimen_fe.json`):

| quantity | FE-based | DEM-based |
|---|---|---|
| R_bulk (single-cell KUBC, **not measurable**) | 1.0158 (+1.58%) | 1.0869 (+8.69%) |
| R_1D (springs in series, 100 mm span) | 1.0149 (+1.49%) | 1.0813 (+8.13%) |
| **R_3D (continuum FE, 100 mm span)** | **1.0148 (+1.48%)** | **1.0809 (+8.09%)** |
| R_3D (60 mm pure-lattice band only) | 1.0158 (+1.58%) | -- |

**Dilution is far weaker than Section 9 assumed: 94% of the bulk signal
survives**, not "well below the bulk ratio". The reason is springs in series --
the compliant lattice band dominates the span compliance, and the stiff solid
shoulder contributes very little of it. The measurement is therefore much more
faithful to the gauge than feared.

Verification performed:

- **Prismatic-bar exactness test**: constant-section solid bar, measured on an
  interior span, returns E_app = 0.99987 against an exact expected 1.0
  (0.013% error). This validates assembly, BCs, reaction sum and witness-plane
  averaging.
- **Mesh convergence**: E_uniform = 0.155807 / 0.155617 / 0.155597 / 0.155580
  at h = 2.5 / 1.25 / 1.0 / 0.625 mm (366k elements, 1.17M DOF at the finest),
  monotone. R is stable at 1.0148 across all four.
- **1D-vs-3D gap**: on the real outline the two differ by 1.1%, which is
  genuine fillet shear lag that beam theory cannot represent. It cancels in R.
- **Grip sensitivity**: R = 1.0148 to four decimals whether the grip is
  laterally clamped or free, and across grip positions from 2 mm to 15 mm
  clearance of the witness lines. E_app itself moves only 0.26%. **The
  St. Venant concern about the 5 mm grip clearance does not affect R** -- grip
  jigging need not be exotic, though it should still be consistent.
- **Poisson sensitivity**: R unchanged at nu = 0.30 / 0.35 / 0.40.

A voxel-quantization trap is documented in the script and is worth knowing
before anyone reuses it: binary voxel occupancy discretizes the 30 mm gauge
width to a multiple of h (at h = 1.0 mm it lands on 31 mm, +3.3% area), so
absolute stiffness jumps around non-monotonically with mesh refinement instead
of converging. Boundary elements must be area-weighted.

**Consequence for the test.** The two models are separated by 6.6 percentage
points *as measured over the witness span* (1.0148 vs 1.0809). Against the
Section 6.3 table at n = 4 per group, that is detectable if CV <= 3% and
marginal at CV 4%. **Measure CV on the first pair and decide the final
specimen count from it.**

### 9.3 Stage 3: resolved-wall model -- RESULTS (2026-08-03)

Stage 2 assigns the gauge an effective modulus calibrated to the KUBC C1111,
baking in the periodic-medium assumption. Stage 3 drops it: the full dog-bone
is meshed with **every gyroid wall resolved** and solved in code_aster
(`simvia/code_aster:stable`, voxel HEXA8, `AFFE_CHAR_CINE` grips, PETSc/GAMG).
Files: `make_mesh_dogbone.py`, `dogbone_tension.comm`, `run_dogbone_fe.sh`,
`summarize_dogbone_fe.py`, `npz_to_med.py`.

| N | h (mm) | elements | E_uniform | E_optimized | R |
|---|---|---|---|---|---|
| 24 | 0.625 | 261k | 0.064442 | 0.055224 | 0.8570 (-14.3%) |
| 36 | 0.417 | 884k | 0.066357 | 0.054671 | 0.8239 (-17.6%) |
| 48 | 0.313 | 2.09M | 0.063793 | 0.056056 | 0.8787 (-12.1%) |
| 72 | 0.208 | 7.05M | 0.063368 | 0.056909 | 0.8981 (-10.2%) |

**The chain is validated.** A solid dog-bone (t > max|F|, so the level set
reduces to the outline) run through the identical code_aster path returns
E_app = **1.0480**, against **1.049428** from the wholly independent Python
continuum solver in `finite_specimen_fe.py` -- agreement to **0.13%** between
two separate implementations. Mesh generation, node groups, boundary
conditions, reaction sum and witness-plane averaging are therefore correct,
and the lattice result below is not a pipeline defect.

**What is established.** All four resolutions put R in 0.82-0.90, i.e. the
optimized specimen is **10-18% softer** than uniform in a finite specimen.
The N=72 run (7.05M elements, added 2026-08-18) shows the sequence drifting
upward with refinement (0.879 -> 0.898 from N=48 to N=72) as the graded
walls thicken in voxel terms; the sign and order of magnitude are robust.
The disagreement with the KUBC-based stage-2 prediction (1.0148) is 0.14-0.19
in R, three to seven times larger than the 0.055 spread across meshes. The
sign and rough magnitude are robust; every independent mesh agrees.

**What is NOT established.** R does not converge -- it spans
(0.857 / 0.824 / 0.879 / 0.898) with an upward drift at the top end.
**Do not quote a stage-3 number to more than "about 0.86 +- 0.04"
(band updated from 0.85 +- 0.03 after the N=72 run, before testing).** The cause is thin-wall
voxel discretization: gauge walls are only 1.8-2.7 voxels thick even at
N = 48, and the staircase approximation changes wall connectivity
qualitatively with h rather than converging smoothly. Note this does not
afflict the solid case (a fat block voxelizes cleanly, hence the 0.13%
agreement above), nor the single-cell KUBC studies (periodic BCs suppress
surface effects, and N48-128 scatter there is 0.545%).

To converge it properly, either go to N >= 72 (7M+ elements, MED route
mandatory) or abandon voxels for a conforming tetrahedral mesh generated from
the existing STL surfaces. The latter is the better instrument for thin
shells and is the recommended route if a publication-grade number is needed.

**Physical reading.** A 2 x 1 cell gauge with free lateral surfaces is not a
periodic medium. KUBC is a strict upper bound assuming infinite periodicity;
severing the sheet at a free surface removes load paths, and a graded design
optimized under the periodic assumption has no reason to retain its advantage
once that assumption is withdrawn. If this holds, the optimizer's gain
evaporates twice: once when FE verification replaced the mesh-free surrogate
(+17.5% -> +1.6%), and again when a finite specimen replaced the periodic
cell (+1.6% -> about -15%).

### 9.4 Consequence: the experiment is now the decisive instrument

This inverts the power problem in Section 6.3. The comparison is no longer
FE-vs-DEM separated by 6.6 pp, but three mutually incompatible predictions:

| model | predicted R |
|---|---|
| DEM (mesh-free surrogate), diluted | 1.0809 |
| FE via KUBC + finite-specimen continuum (stage 2) | 1.0148 |
| FE with resolved walls, finite specimen (stage 3) | ~0.86 +- 0.04 |

(Stage-3 band corrected 2026-08-25: this table had carried the pre-N72
value ~0.85 +- 0.03 after Section 9.3 updated the band to 0.86 +- 0.04
upon the N=72 run, before testing. The corrected band is the one
pre-registered for the test and quoted in the manuscript; see Section
9.3 for the four ladder values 0.857/0.824/0.879/0.898.)

Stage 2 and stage 3 differ by roughly **15 percentage points**. Against the
Section 6.3 table, n = 4 per group detects a 16-point difference at CV up to
5% with power to spare -- where the original +1.48% signal was hopeless at any
printable specimen count. **The eight specimens already printed are sufficient
to decide this**, and the physical test now resolves a question the simulation
cannot settle cheaply. That is a much stronger position than the experiment
was in this morning.

## 10. What goes into the paper

A new "Experimental validation" subsection: specimen table (Section 2),
mass/iso-volume check (Section 11), E* per group with CIs, measured R against
the finite-specimen FE prediction (Section 9.2) with the bulk FE 0.956 and
DEM 1.175 as context, and the CT wall-fidelity figure. This elevates the work
above the entire physics-informed TO literature cited in the manuscript, none
of which reports a physical specimen.

The framing is no longer "our optimized design is stiffer and here is the
proof". It is: **a mesh-free surrogate confidently proposed a design that FE
verification showed to be softer than its own baseline, and a physical
specimen adjudicates.** That is a more useful contribution and a much harder
one to dismiss.

## 11. Results: as-printed mass, Track B build 1 (2026-08-02)

First physical data for this project. Four `dogbone_optimized_printable.stl`
(O1-O4) and four `dogbone_uniform.stl` (U1-U4), FDM PETG (Bambu Lab H2S,
0.4 mm nozzle), single build, weighed after printing. (Earlier draft said
PLA in error; material is PETG per the manuscript.)

| specimen | mass (g) | | specimen | mass (g) |
|---|---|---|---|---|
| O1 | 78.3900 | | U1 | 77.9880 |
| O2 | 78.0271 | | U2 | 78.0985 |
| O3 | 78.1880 | | U3 | 78.0820 |
| O4 | 78.2517 | | U4 | 77.8811 |

| | mean | SD | CV | range |
|---|---|---|---|---|
| optimized (printable) | 78.2142 g | 0.1506 | 0.192% | 0.363 g |
| uniform | 78.0124 g | 0.1002 | 0.128% | 0.217 g |

### 11.1 Print repeatability

CV below 0.2% within both groups. For FDM this is tight and is the first
evidence that the lattice geometry is being reproduced consistently across
the build. Apparent density (mass / designed STL volume) is 1.2275 g/cm^3
(optimized) and 1.2246 g/cm^3 (uniform), i.e. **96.4-96.7% of nominal PETG
(1.27 g/cm^3)**, roughly 3-4% void/under-extrusion, normal for FDM lattice
work but not "fully dense" as an earlier PLA-based reading claimed. Note this
bounds mass fidelity, not wall-thickness fidelity: a specimen can hit the
right mass with systematically fat thin-walls and thin fat-walls.
Section 4.3 (micro-CT or sectioned spot checks) is still required.

### 11.2 Iso-volume check

Designed solid volumes, computed directly from the printed STLs:

| | designed volume | measured mass |
|---|---|---|
| optimized (printable) | 63.718 cm^3 | 78.2142 g |
| uniform | 63.706 cm^3 | 78.0124 g |
| **ratio O/U** | **1.00019 (+0.019%)** | **1.00259 (+0.259%)** |

The iso-volume constraint holds to a quarter of a percent, which is the
headline check for the whole optimization. But the optimized group came out
**+0.240 pp heavier than design parity** (+0.202 g, Welch t = 2.23, p = 0.074,
n = 4). The direction is exactly what Section 9 predicted: sub-nozzle-width
walls in the graded design get fattened to nozzle width. At n = 4 this is a
hint, not a finding -- but it must not be ignored, for the reason below.

### 11.3 Why the mass excess now matters (it did not under protocol v1)

With lattice modulus scaling as E ~ rho^1.5-2, a +0.24 pp mass excess buys
roughly **+0.4 to +0.5% of spurious stiffness** in the optimized group.

Under protocol v1 that was negligible against an expected +9.1% gain. Against
the corrected FE prediction of **+1.6%** it is roughly **one third of the
entire signal**, and it biases in the flattering direction. Consequences:

1. Record each specimen's mass alongside its E*. Do not pool the groups
   without it.
2. Report a **mass-adjusted ratio** as the primary result: regress E* on
   measured mass across all specimens, or normalise each E* by
   (m_i / m_mean)^n with n from the fitted density exponent, and state n.
3. State the raw and adjusted R side by side. A reviewer who spots a 0.26%
   mass difference behind a 1.6% claimed stiffness gain, and does not find it
   already addressed here, will reject the result outright.

### 11.4 Open items before testing

- ~~Finite-specimen FE model of the dog-bone over the 30-130 mm span~~
  **DONE**, Sections 9.2 and 9.3. Three comparison targets, mutually
  incompatible: **DEM 1.0809, stage-2 FE 1.0148, stage-3 resolved-wall
  ~0.85.** The test discriminates all three at n = 4 (Section 9.4).
- Pilot pair (O1/U1) to measure CV. Still worth doing, but the specimen count
  is no longer the binding constraint now that the candidate predictions are
  16 pp apart rather than 6.6.
- ~~Stage 3 resolved-wall run~~ **DONE but not converged** (oscillates +-5 pp,
  Section 9.3). Converging it -- N >= 72, or conforming tets from the STLs --
  is required before a stage-3 number appears in the manuscript, though not
  before testing.
- **Watch the sign.** Stage 3 predicts the optimized specimen is *softer*.
  If the Instron agrees, the mass confound in Section 11.3 works against that
  finding rather than for it (the optimized group is 0.24 pp heavy, which
  should make it look stiffer), so it strengthens rather than threatens the
  result. Report it either way.
- Caliper the actual witness-line spacing on every specimen; use the measured
  value as L0 per specimen, not the nominal 100 mm.

## 12. Protocol v3: Instron 8852 + smartphone-video strain tracking (2026-08-17)

**Why the change.** The 160 x 45 x 15 mm plate dog-bones do not fit the
grips of the Instron E10000 the protocol was written against. The test
moves to the **Instron 8852** servo-hydraulic axial-torsion frame
(+/-100 kN axial, hydraulic wedge grips with interchangeable flat faces),
which clamps the 45 x 15 mm solid shoulders directly. Two consequences
are addressed explicitly:

1. **Load range vs. frame capacity.** Peak cycle forces are tens to
   hundreds of newtons (elastic protocol; gauge section 30 x 15 mm at an
   effective lattice modulus of a few hundred MPa implies ~0.5 kN at
   0.5-1% strain). That is ~0.5% of the 8852's capacity, where load-cell
   accuracy class matters. Mitigation: verify the load channel at the
   working range (calibrated proving ring / known mass hung from the
   lower grip) before the campaign, record the verification, and rely on
   the R-ratio read-out (same machine, same channel, interleaved groups)
   to cancel residual load-path bias. If a smaller calibrated load cell
   is available for the frame, use it.
2. **Displacement control at low rate.** 1 mm/min crosshead rate is well
   within the 8852's servo range; run in stroke control with the
   specimen seated under a small preload (5-10 N) before zeroing.

**Strain measurement (replaces clip-on extensometry).** Each coupon carries
two printed witness grooves across the full face width at x1 = 30 and
130 mm (100 mm span). When mounted with x1 vertical these are two
horizontal dark lines on the lit coupon face, and the span is recovered
per frame by tracking their vertical positions:

- iPhone rear camera, 4K (3840 x 2160) at 60 fps, tripod, airplane mode,
  screen locked; optical axis normal to the coupon face (check for
  parallax by confirming the two grooves stay in the frame thirds).
- Diffuse side lighting (two desk lamps bounced off white paper), no
  direct reflections on the PETG; lock focus and exposure on the coupon
  before starting (tap-hold until AE/AF Lock banner).
- A steel ruler is taped in the specimen plane (same distance from the
  camera) for pixel-mm scale; per-specimen groove spacing measured with
  calipers (nominal 100.0 mm) and recorded as that specimen's L0.
- Record the whole test including the hand-wave trigger (see
  `TEST_PROCEDURE.md`), then extract the two groove positions per frame
  with `track_lines.py` (sub-pixel edge template matching); expected
  strain resolution ~1e-4 over the span.

**Sync.** Video and Instron data streams are synchronized by the hand
trigger (visible in frame, force nonzero a moment later); the tracker
and the CSV are time-aligned by matching the preload seating step in
both signals.

**Analysis changes only in labeling, not in math**: raw R (primary),
mass-adjusted R (sensitivity analysis, weakly identified at n = 8 --
state it), DEM-vs-FE comparison exploratory, resolved-wall-vs-periodic
confirmatory. All pre-registered bands unchanged (Section 9.4).
