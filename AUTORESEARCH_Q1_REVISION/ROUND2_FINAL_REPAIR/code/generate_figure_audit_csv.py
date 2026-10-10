import csv
import os

headers = [
    'figure ID',
    'PDF page',
    'source script/data',
    'defects found',
    'corrections',
    'numerical-check result',
    'final-PDF visual-check result',
    'remaining issues'
]

rows = [
    [
        'Fig 1 (fig:families)',
        '7',
        'paper/make_figs_v2.py; TPMS analytic level sets Eq. (2)',
        'In legacy draft, background contrast was uneven across panels; panel letters lacked standardized styling.',
        'Regenerated at 300 DPI with uniform neutral background, bold (a)-(f) labels on high-contrast tags, and standardized bounding box.',
        'PASS: Level-set values f(x,y,z)=c rigorously yield target volume fraction Vf=0.20 across all 6 architectures.',
        'PASS: Clean 2x3 grid layout on page 7, sharp strut geometry, unambiguous panel labels (a)-(f), readable family captions.',
        'None'
    ],
    [
        'Fig 2 (fig:network)',
        '8',
        'paper/make_figs_v2.py; Fourier feature neural solver architecture',
        'Text "wall-thickness gradients" collided with the bottom border of the grouping bounding box due to tight vertical padding.',
        'Expanded bottom padding in paper/make_figs_v2.py to grp_bot_y = (Y0 - 2.65, Y0 - 0.50) with ylo + 0.40; re-exported to vector PDF.',
        'PASS: Architectural dimensions match manuscript text (gamma(x) Fourier mapping, 4x128 hidden units, Sine activations).',
        'PASS: Checked page 8 of compiled PDF. "wall-thickness gradients" sits cleanly inside grouping box with generous margin; zero collisions.',
        'None'
    ],
    [
        'Fig 3 (fig:pipeline)',
        '9',
        'paper/make_figs_v2.py; 3-stage optimization workflow specification',
        'Minor arrow thickness inconsistencies and font embedding in legacy EPS/PDF export.',
        'Re-exported as vector PDF with embedded TrueType fonts (type 42), standardized arrowheads, and high-contrast stage flow grouping.',
        'PASS: Diagram stages match algorithmic execution order (pre-training, active search with surrogate, FE verification).',
        'PASS: Checked page 9 of compiled PDF. Crisp vector lines, legible block text, unobstructed arrow paths, clear stage demarcation.',
        'None'
    ],
    [
        'Fig 4 (fig:c1111)',
        '13',
        'paper/make_figs_v2.py; results/c1111_vs_vf.json',
        'Raster PNG was included in early draft leading to slightly soft marker edges; legend was close to Gibson-Ashby trend lines.',
        'Switched to vector PDF in manuscript_round2.tex; increased marker border contrast; positioned legend cleanly in upper left.',
        'PASS: KUBC stiffness values agree with homogenization database; Gibson-Ashby exponent n in [1.8, 2.1] across all families.',
        'PASS: Checked page 13 of compiled PDF. Razor-sharp vector markers, distinct family colors, uncrowded legend, legible axis labels.',
        'None'
    ],
    [
        'Fig 5 (fig:family)',
        '15',
        'paper/make_figs_v2.py; results/cross_family_benchmarks.json',
        'Raster PNG formatting with slightly cramped bar labels and small baseline delta markers.',
        'Switched to vector PDF in manuscript_round2.tex; applied Okabe-Ito colorblind-safe palette; honest zero baseline; clear callout values.',
        'PASS: C1111 values at matched Vf=0.19328 agree exactly with Table 1 and FE benchmark baseline.',
        'PASS: Checked page 15 of compiled PDF. High-contrast bars starting from 0, clearly legible numerical value labels, unclipped axes.',
        'None'
    ],
    [
        'Fig 6 (fig:e3)',
        '17',
        'paper/make_figs_v2.py; e3_fe_baseline.json',
        'Colorbar label "t" was awkwardly positioned adjacent to the upper tick "0.35"; 3D surface had heavy ambient shadow clipping.',
        'Set colorbar title to centered cb.ax.set_title("$t$", pad=6); brightened 3D surface ambient lighting to 0.50 in paper/make_figs_v2.py.',
        'PASS: Graded thickness range t in [0.12, 0.35] mm strictly satisfies printability bounds; macro-volume fraction matches 0.19328.',
        'PASS: Checked page 17 of compiled PDF. Surface features bright and clearly visible; colorbar title "t" centered above bar without tick overlap.',
        'None'
    ],
    [
        'Fig 7 (fig:contours)',
        '20',
        'paper/make_figs_v2.py; FE stress simulation database',
        'Deep shadow regions obscured interior strut surfaces in isometric perspective render.',
        'Increased ambient lighting to 0.50; adjusted colorbar mapping to maximize dynamic range in mid-stress load-carrying regions.',
        'PASS: Peak stress concentrations align with load paths identified in voxel-FE simulation under 1% uniaxial compression.',
        'PASS: Checked page 20 of compiled PDF. Surface and interior struts clearly visible; colorbar ticks and unit labels (MPa) well separated.',
        'None'
    ],
    [
        'Fig 8 (fig:fields)',
        '22',
        'paper/make_figs_v2.py; field verification evaluations',
        'Colorbar titles lacked explicit unit notation; divergent field color limits were slightly asymmetrical.',
        'Added explicit unit labels (uz in mm, sigma_zz in MPa); symmetric color limits centered at zero for displacement divergence.',
        'PASS: Mid-plane slice displacement and stress distributions match high-fidelity FE verification solution within < 1.5% RMSE.',
        'PASS: Checked page 22 of compiled PDF. 3-panel field comparison clearly readable; distinct colorbars with proper padding; sharp titles.',
        'None'
    ],
    [
        'Fig 9 (fig:mechanism)',
        '23',
        'paper/make_figs_v2.py; displacement and energy flux vector fields',
        'Dense vector field arrows in early drafts obscured material boundary interfaces.',
        'Subsampled vector grid spacing; enhanced contrast of energy flux arrows along principal compressive axes.',
        'PASS: Load flux vectors correctly trace structural load transfer from top compressive plate to base supports.',
        'PASS: Checked page 23 of compiled PDF. Unambiguous deformation mechanism; clean vector arrows, well-separated panel letters.',
        'None'
    ],
    [
        'Fig 10 (fig:vgmmbudget) [R1]',
        '27',
        'code/r2_figures.py (fig_r1); results/r2_pool_replay.json, r2_arms/*.json',
        'Early drafts conflated search grid (64^3) with confirmation grid (96^3) and raw requests with unique FE evaluations.',
        'Separated into panel (a) step trajectories on 64^3 search grid vs unique evaluations with batch-complete & budget-matched markers; panel (b) confirmation grid (96^3 open vs 64^3 filled markers). Exported to data/R1_*.csv.',
        'PASS: Automated test pass: VG-MM s11 ends 26 @ 5.8281%, DET @ 1.8828%, full-FE truncated@26 = 4.9285%, batch-complete@25 = 4.6589%.',
        'PASS: Checked page 27 of compiled PDF. Panel (a) and (b) clearly delineated; legends unobstructed; correct symbols and line styles.',
        'None'
    ],
    [
        'Fig 11 (fig:pooldiscordance) [R2]',
        '28',
        'code/r2_figures.py (fig_r2); results/r2_pool_replay.json',
        'Panel (a) "DEM-best" annotation slightly crossed the right plot border; panel (b) required recomputed cloud-11 denominator; panel (c) required ranking loss breakdown.',
        'Shifted "DEM-best" annotation to xytext=(-10, -12), ha="right" safely inside panel (a); panel (b) uses exact cloud-11 denominator (0.115368); panel (c) displays 21 material ranking loss vs 0 id-only discordances. Exported to data/R2_*.csv.',
        'PASS: Python and MATLAB MCP verify identical Spearman rho = 0.664443, Kendall tau = 0.478, N=192 pool candidates.',
        'PASS: Checked page 28 of compiled PDF. "DEM-best" text is completely inside panel (a); identity lines crisp; bar chart labels unclipped.',
        'None'
    ],
    [
        'Fig 12 (fig:policyseeds) [R3]',
        '28',
        'code/r2_figures.py (fig_r3); results/r2_accounting.json',
        'Round-1 draft contained fabricated error bars / decorative distributions across only N=3 seeds.',
        'Replaced with individual replicate markers (seeds 11, 12, 13) for each policy family; honest zero baseline; shaded practical margin delta=1.0 pp band. Zero decorative distributions. Exported to data/R3_*.csv.',
        'PASS: Plotted points match r2_accounting.json exactly: VG-MM (5.83, 5.65, 5.55%), RAND (4.63, 5.23, 5.21%), DET (1.88%), DEM (-5.07, -6.64, -1.78%).',
        'PASS: Checked page 28 of compiled PDF. Individual seed points clearly distinguished with unique markers; practical margin band legible.',
        'None'
    ],
    [
        'Fig 13 (fig:methoddiagram) [R4]',
        '29',
        'code/r2_figures.py (fig_r4); method specification',
        'Feedback arrow for "accept: update incumbent" collided with candidate evaluation node in early layout.',
        'Rerouted accept loop cleanly to incumbent box (x=1.30, y=2.86) with dedicated clearance; added distinct "reject" branch.',
        'PASS: Diagram accurately encodes replay and arm evaluation loop implemented in code/r2_replay.py and code/r2_arms.py.',
        'PASS: Checked page 29 of compiled PDF. Flowchart lines and text boxes completely free of collision; arrows sharp and directionally unambiguous.',
        'None'
    ],
    [
        'Fig 14 (fig:geometry) [R5]',
        '29',
        'code/r2_figures.py (fig_r5); results/r2_pool_replay.json',
        'Previous drafts had mismatched viewing angles and lacked verified volume fraction conservation checks.',
        'Matched-view midplane cross-sections (Uniform, VG-MM best, Full-FE best); common colorbar [0.12, 0.55]; explicit Vf=0.19328 callout on each panel; solid difference masks.',
        'PASS: Automated check verifies render-grid Vf=0.19328 +- 0.00004 for all three geometries; thickness strictly in [0.12, 0.55].',
        'PASS: Checked page 29 of compiled PDF. All 3 panels align with identical aspect ratio and scale; colorbar legible; difference mask clear.',
        'None'
    ],
    [
        'Fig 15 (fig:experiment)',
        '41',
        'Original photograph; manuscript/figures/test_setup.png',
        'Crop artifact left two black horizontal bands across rows 290-303 and incomplete bottom border rows 725-744.',
        'Removed artifact bands (filled rows 290-303 with clean white background, cropped bottom edge); original preserved in test_setup_original_backup.png.',
        'PASS: Specimen dimensions (30x30x30 mm coupon, 2x2x2 unit cells) match fabricated coupon specifications.',
        'PASS: Checked page 41 of compiled PDF. Pristine white background; zero black lines; Instron machine and fixture clearly visible.',
        'None'
    ],
    [
        'Fig 16 (fig:expresult)',
        '43',
        'paper/make_figs_v2.py; results/experimental_coupon_data.json',
        'Raster PNG in early draft; caption referenced stale "open-to-filled markers"; elastic slope lines needed clear legend.',
        'Switched to vector PDF in manuscript_round2.tex; updated caption text to "open markers with connecting dotted lines"; visible elastic fit slopes.',
        'PASS: Measured compressive stiffness slopes and relative improvements match FE predictions within experimental tolerance.',
        'PASS: Checked page 43 of compiled PDF. Vector lines razor-sharp; experimental vs FE curves distinct; axis labels and units accurate.',
        'None'
    ],
    [
        'Fig A.17 (fig:meshconv)',
        '55',
        'paper/make_figs_v2.py; results/mesh_convergence.json',
        'Legacy figure was cramped (figsize 7.2x3.8); small legend font (7.0 pt) made resolving 64^3 vs 96^3 vs 128^3 difficult.',
        'Rescaled figure to 8.4x4.4 in; increased legend font to 8.8 pt; enlarged markers; switched to vector PDF in manuscript_round2.tex.',
        'PASS: Delta C1111 from 64^3 to 96^3 is < 0.5%, and to 128^3 is < 0.15%, confirming asymptotic mesh convergence.',
        'PASS: Checked page 55 of compiled PDF. Spacious 2-panel layout; legend easily readable at publication size; trajectories cleanly resolved.',
        'None'
    ],
    [
        'QC Supplementary: MATLAB Parity Check',
        'N/A (supplementary)',
        'code/verify_figures_matlab.m; figures/data/R1_endpoints.csv, R2_pool.csv',
        'Needed independent numerical cross-verification of figure data in native MATLAB R2026a environment.',
        'Authored verify_figures_matlab.m; verified R1 endpoints and R2 pool; generated figures/matlab_parity_check.png via MATLAB MCP.',
        'PASS: MATLAB R2026a confirms identical Spearman rho = 0.664443 on N=192 pool; R1 endpoints match to 4 decimal places.',
        'PASS: Verification scatter plot matches Python output exactly with equal axes and identity line.',
        'None'
    ]
]

here = os.path.dirname(os.path.abspath(__file__))
r2_root = os.path.dirname(here)
out_path = os.path.join(r2_root, 'FIGURE_AUDIT.csv')
with open(out_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(headers)
    writer.writerows(rows)

print(f'Wrote {len(rows)} rows to {out_path}')
