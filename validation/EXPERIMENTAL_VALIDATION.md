# Experimental validation plan: printed compression test of the optimized graded gyroid

Status: protocol v1, 2026-07-31. Companion files: `make_specimen_stl.py`,
`specimen_uniform_t0.30.stl`, `specimen_graded_opt.stl`.

## 1. Objective and the key design of the experiment

The paper's headline claim is a **ratio**, not an absolute number: at equal
volume fraction (Vf = 0.193), the optimized graded gyroid is stiffer than the
uniform gyroid in the x1 direction by **+9.1%** (voxel FEM) with the mesh-free
model predicting +17.5%. The experiment therefore compares **two specimen
groups printed in the same build** and validates the stiffness ratio

    R = E*_graded / E*_uniform

Testing the ratio (instead of absolute stiffness) cancels the dominant
experimental unknowns: base material modulus, print-process softening,
layer anisotropy, and machine compliance all appear in both numerator and
denominator. This is the same logic the paper uses when it validates design
ranking rather than absolute values.

Expected outcome bands:
- R in 1.05-1.13: confirms the FEM-predicted gain (9.1% +/- realistic scatter).
- R near 1.00: gain not realized; investigate wall fidelity at t_min regions.
- R above 1.15: suggests the DEM prediction band; unlikely but informative.

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
- **Strain from optics, not crosshead**: DIC on one lateral face, or a video
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
3. Power check: with typical AM stiffness scatter of CV 3-5%, n = 5 per
   group detects a 9% mean difference at alpha = 0.05 with power > 0.9.
   If pilot scatter exceeds CV 6%, add specimens before concluding.
4. Compare against three model values, all at Vf = 0.193:
   - FEM (as-designed): R = 0.11699 / 0.10725 = **1.091**
   - DEM (mesh-free): R = 0.1338 / 0.1139 = 1.175
   - FEM (as-printed CT geometry, if Section 4.3 is done): the tightest
     comparison, isolating solver error from print error.
5. Report absolute E* too (with the measured base-material modulus from
   printed dogbones if available), but frame the validation on R.

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
and one day on a universal testing machine with DIC. No custom fixtures.

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
| mass (PLA) | ~77 g each |

Printing (FDM, PLA, 0.4 mm nozzle): print flat, 0.15-0.2 mm layers,
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
to these two lines, or paint a dot on each for video/DIC tracking; the
100 mm span between them is the reference gauge length for both
specimens.

Because this 100 mm span includes the graded transition and a few
millimetres of shoulder in addition to the 60 mm pure-lattice band, the
measured apparent modulus is diluted toward the (identical, stiffer)
shoulder material on both specimens. Expect the measured stiffness
ratio to sit below both the bulk KUBC ratio (1.091) and the
single-cell-through-thickness structural ratio discussed above --
report this dilution explicitly rather than compare directly to 1.091.

Test: tension at 2 mm/min with an extensometer or DIC on the two
witness lines; three load-unload cycles in the elastic range; report
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
measurement, so the measured ratio will sit below the bulk KUBC value of
1.091; the model claim being demonstrated is the *ranking* (graded
stiffer than uniform at equal mass) plus a visible, printable artifact
of mesh-free geometry-parameter optimization. For the journal-grade
number, use Track A.

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
paper (N64 and N96 voxel meshes, KUBC, identical boundary conditions):

| | DEM predicted | FEM confirmed (N96) |
|---|---|---|
| unconstrained (dogbone_optimized.stl) | +17.5% | +9.1% |
| constrained (dogbone_optimized_printable.stl) | +8.3% | **+9.7%** |

The constrained design's FE-confirmed gain matches the unconstrained
one within mesh noise, despite predicting under half the mesh-free
gain -- the unconstrained design's extra *predicted* stiffness was
mostly the DEM's own thin-wall bias (Section on N3 in the manuscript),
which is largest exactly where that design saturates at t_min, not a
real mechanical benefit. **Use `dogbone_optimized_printable.stl` as
the optimized specimen for printing**: same real-world stiffness gain,
self-supporting like the base gyroid, no support material needed.

## 10. What goes into the paper

A new "Experimental validation" subsection: specimen table (Section 2),
mass/iso-volume check, E* per group with CIs, measured R vs FEM 1.091 and
DEM 1.175, and the CT wall-fidelity figure. This elevates the work above the
entire physics-informed TO literature cited in the manuscript, none of which
reports a physical specimen.
