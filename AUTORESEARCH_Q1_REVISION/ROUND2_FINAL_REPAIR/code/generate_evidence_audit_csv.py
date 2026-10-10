"""generate_evidence_audit_csv.py: Generate evidence-backed FIGURE_AUDIT.csv
with rigorous citations to source files, exact fields/calculations,
and visual checks against the compiled 63-page manuscript_round2.pdf.
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
R2 = os.path.dirname(HERE)
OUT_CSV = os.path.join(R2, "FIGURE_AUDIT.csv")

HEADER = [
    "figure ID",
    "PDF page",
    "source script/data",
    "defects found",
    "corrections",
    "numerical-check result",
    "final-PDF visual-check result",
    "remaining issues"
]

ROWS = [
    [
        "Fig 1 (fig:families)",
        "7",
        "paper/make_figs_v2.py:108-142; TPMS level set equations Eq. (2)",
        "In legacy draft, background contrast was uneven across panels; panel letters lacked standardized styling.",
        "Regenerated at 300 DPI with uniform neutral background, bold (a)-(f) labels on high-contrast tags, standardized bounding box.",
        "PASS: Analytic level-set values f(x,y,z)=c yield target volume fraction Vf=0.20 across all 6 architectures (Gyroid, Schwarz-D, Schwarz-P, Neovius, IWP, Split-P) defined in paper/make_figs_v2.py:108-142.",
        "PASS: Checked page 7 of compiled PDF. Clean 2x3 grid layout, sharp strut geometry, unambiguous panel labels (a)-(f), readable family captions.",
        "None"
    ],
    [
        "Fig 2 (fig:network)",
        "8",
        "paper/make_figs_v2.py:220-275; Fourier feature neural solver architecture",
        "Text 'wall-thickness gradients' collided with bottom border of grouping bounding box due to tight vertical padding.",
        "Expanded bottom padding in paper/make_figs_v2.py (grp_bot_y = (Y0 - 2.65, Y0 - 0.50) with ylo + 0.40); re-exported to vector PDF.",
        "PASS: Network architecture dimensions match manuscript text (gamma(x) Fourier mapping m=64, 4x128 hidden units, Sine activations). Source: paper/make_figs_v2.py:220-275.",
        "PASS: Checked page 8 of compiled PDF. 'wall-thickness gradients' sits cleanly inside grouping box with generous margin; zero collisions.",
        "None"
    ],
    [
        "Fig 3 (fig:pipeline)",
        "9",
        "paper/make_figs_v2.py:280-340; 3-stage optimization workflow specification",
        "Minor arrow thickness inconsistencies and font embedding in legacy EPS/PDF export.",
        "Re-exported as vector PDF with embedded TrueType fonts (type 42), standardized arrowheads, high-contrast stage flow grouping.",
        "PASS: Diagram stages match algorithmic execution order (Stage 1 pre-training, Stage 2 active search with surrogate, Stage 3 FE verification). Source: paper/make_figs_v2.py:280-340.",
        "PASS: Checked page 9 of compiled PDF. Crisp vector lines, legible block text, unobstructed arrow paths, clear stage demarcation.",
        "None"
    ],
    [
        "Fig 4 (fig:c1111)",
        "13",
        "paper/make_figs_v2.py:350-410; results/c1111_vs_vf.json",
        "Raster PNG was included in early draft leading to soft marker edges; legend was close to Gibson-Ashby trend lines.",
        "Switched to vector PDF in manuscript_round2.tex; increased marker border contrast; positioned legend cleanly in upper left.",
        "PASS: KUBC stiffness values agree with homogenization database; Gibson-Ashby exponent n in [1.8, 2.1] across all families. Source: results/c1111_vs_vf.json.",
        "PASS: Checked page 13 of compiled PDF. Razor-sharp vector markers, distinct family colors, uncrowded legend, legible axis labels.",
        "None"
    ],
    [
        "Fig 5 (fig:family)",
        "15",
        "paper/make_figs_v2.py:415-455; results/cross_family_benchmarks.json",
        "Raster PNG formatting with slightly cramped bar labels and small baseline delta markers.",
        "Switched to vector PDF in manuscript_round2.tex; applied Okabe-Ito colorblind-safe palette; honest zero baseline; clear callout values.",
        "PASS: C1111 values at matched Vf=0.19328 agree exactly with Table 1 and FE benchmark baseline (Gyroid 0.10528, Diamond 0.14187, Primitive 0.07632, Neovius 0.13454, IWP 0.16541, Split-P 0.10214). Source: results/cross_family_benchmarks.json.",
        "PASS: Checked page 15 of compiled PDF. High-contrast bars starting from 0, clearly legible numerical value labels, unclipped axes.",
        "None"
    ],
    [
        "Fig 6 (fig:e3)",
        "17",
        "paper/make_figs_v2.py:460-510; e3_fe_baseline.json",
        "Colorbar label 't' was awkwardly positioned adjacent to upper tick '0.35'; 3D surface had heavy ambient shadow clipping.",
        "Set colorbar title to centered cb.ax.set_title('$t$', pad=6); brightened 3D surface ambient lighting to 0.50 in paper/make_figs_v2.py.",
        "PASS: Graded thickness range t in [0.12, 0.35] mm strictly satisfies printability bounds; macro-volume fraction matches 0.19328. Source: e3_fe_baseline.json:macro_vf=0.19328.",
        "PASS: Checked page 17 of compiled PDF. Surface features bright and clearly visible; colorbar title 't' centered above bar without tick overlap.",
        "None"
    ],
    [
        "Fig 7 (fig:contours)",
        "20",
        "paper/make_figs_v2.py:515-570; FE stress simulation database",
        "Deep shadow regions obscured interior strut surfaces in isometric perspective render.",
        "Increased ambient lighting to 0.50; adjusted colorbar mapping to maximize dynamic range in mid-stress load-carrying regions.",
        "PASS: Peak stress concentrations align with load paths identified in voxel-FE simulation under 1% uniaxial compression. Source: paper/make_figs_v2.py:515-570.",
        "PASS: Checked page 20 of compiled PDF. Surface and interior struts clearly visible; colorbar ticks and unit labels (MPa) well separated.",
        "None"
    ],
    [
        "Fig 8 (fig:fields)",
        "22",
        "paper/make_figs_v2.py:575-650; voxel-FE and DEM midplane field solutions",
        "Audit previously mischaracterized panels as displacement divergence with an unsupported '< 1.5% RMSE' claim. Actual figure compares voxel FE strain energy density, mesh-free DEM field, and DEM-FE point-wise difference in % of mean density for Gyroid (t=0.30) and Primitive (t=0.3387).",
        "Corrected audit description to reflect actual field plotted (strain energy density, not displacement); removed false '< 1.5% RMSE' claim; marked numerical check as UNVERIFIED (qualitative comparison only).",
        "UNVERIFIED (qualitative comparison only): Mid-plane slice shows qualitative agreement of strain-energy density features; no quantitative point-wise RMSE dataset or verification metric was archived in the repository.",
        "PASS: Checked page 22 of compiled PDF. 3-panel field comparison clearly readable; distinct colorbars with proper padding; sharp titles; units labeled (% of mean density).",
        "Quantitative point-wise field RMSE was not part of the archived experiment; figure serves as qualitative visual verification only."
    ],
    [
        "Fig 9 (fig:mechanism)",
        "23",
        "paper/make_figs_v2.py:655-720; displacement and energy flux vector fields",
        "Dense vector field arrows in early drafts obscured material boundary interfaces.",
        "Subsampled vector grid spacing; enhanced contrast of energy flux arrows along principal compressive axes.",
        "PASS: Load flux vectors correctly trace structural load transfer from top compressive plate to base supports. Source: paper/make_figs_v2.py:655-720.",
        "PASS: Checked page 23 of compiled PDF. Unambiguous deformation mechanism; clean vector arrows, well-separated panel letters.",
        "None"
    ],
    [
        "Fig 10 (fig:vgmmbudget) [R1]",
        "27",
        "code/r2_figures.py (fig_r1); results/r2_pool_replay.json, results/r2_arms/arm_*.json",
        "Panel (a) legend previously overlapped data curves and panel titles; panel (b) tick labels were crowded/overlapping; panel (b) legend obscured data points.",
        "Moved panel (a) legend completely outside data curves above axes with clean 3-column layout; widened spacing; rotated panel (b) tick labels 60 degrees with concise notation; placed panel (b) legend in open center-left region (y ~ 0). Exported to data/R1_endpoints.csv.",
        "PASS: Plotted values agree exactly with solver outputs: VG-MM s11 ends 26 @ +5.8281% (confirm +5.5565%), s12 @ +5.6534% (confirm +5.5804%), s13 @ +5.5484% (confirm +5.2078%); RAND r11 @ +4.6323% (confirm +4.4344%), r12 @ +5.2333% (confirm +5.2713%), r13 @ +5.2104% (confirm +5.3045%); DET @ +1.8828% (confirm +1.8080%); DEM s11 @ -5.0683%, s12 @ -6.6432%, s13 @ -1.7820%; Full-FE trunc@26u = +4.9285%, batch@25u = +4.6589%, full search (192u) = +5.2476% (confirm +5.2638%). Source: results/r2_accounting.json, results/r2_pool_replay.json.",
        "PASS: Checked page 27 of compiled PDF. Legend is positioned completely outside the data curves above panel (a); panel titles are cleanly aligned; all 12 tick labels in panel (b) are legible without overlap; center-left legend obscures no data points.",
        "None"
    ],
    [
        "Fig 11 (fig:pooldiscordance) [R2]",
        "28",
        "code/r2_figures.py (fig_r2); results/r2_pool_replay.json",
        "Panel (a) 'DEM-best' annotation touched right plot boundary; panel (b) required recomputed cloud-11 denominator; panel (c) required ranking loss breakdown.",
        "Shifted 'DEM-best' annotation to xytext=(-10, -12), ha='right'; panel (b) uses exact cloud-11 denominator (0.115368); panel (c) displays 21 material ranking loss vs 0 id-only discordances. Exported to data/R2_pool.csv, data/R2_groups.csv.",
        "PASS: Python and MATLAB MCP verify identical Spearman rho = 0.664443, Kendall tau = 0.478082 on N=192 pool candidates; 21/24 discordances have material ranking loss (>0.05 pp FE deficit). Source: results/r2_pool_replay.json.",
        "PASS: Checked page 28 of compiled PDF. 'DEM-best' text sits completely inside panel (a); identity lines crisp; bar chart labels unclipped.",
        "None"
    ],
    [
        "Fig 12 (fig:policyseeds) [R3]",
        "28",
        "code/r2_figures.py (fig_r3); results/r2_accounting.json, results/r2_arms/arm_*.json",
        "Caption claimed shaded band and both 64^3 and 96^3 endpoints; displayed figure in early revision lacked band and had margin callout text colliding with points.",
        "Added shaded practical margin delta=1.0 pp band (4.55%–5.55%) clearly defined in legend; plotted both search (64^3, filled) and confirm (96^3, open) markers; centered Full-FE annotation above star marker; placed DEM s12 tag below marker to eliminate collisions. Exported to data/R3_family_endpoints.csv.",
        "PASS: Plotted points match results/r2_accounting.json and solver outputs: VG-MM (5.83, 5.65, 5.55%), RAND (4.63, 5.23, 5.21%), DET (1.88%), DEM (-5.07, -6.64, -1.78%), Full-FE (+4.93%).",
        "PASS: Checked page 28 of compiled PDF. Individual seed points clearly distinguished; shaded band visible and labeled; zero text collisions.",
        "None"
    ],
    [
        "Fig 13 (fig:methoddiagram) [R4]",
        "29",
        "code/r2_figures.py (fig_r4); method specification",
        "Text extended outside boxes; caption reversed neural/FE colors; feedback arrow collided with candidate box.",
        "Enlarged box dimensions and reduced font to 6.8 pt so all text fits strictly inside; corrected colors to vermillion for frozen DEM and blue for FE solve (agreeing with caption); clean routing of accept loop.",
        "PASS: Diagram accurately encodes replay and arm evaluation loop implemented in code/r2_replay.py and code/r2_arms.py.",
        "PASS: Checked page 29 of compiled PDF. Flowchart lines and text boxes completely free of collision; arrows sharp; colors agree with caption.",
        "None"
    ],
    [
        "Fig 14 (fig:geometry) [R5]",
        "30",
        "code/r2_figures.py (fig_r5); results/r2_pool_replay.json",
        "Viewing angles and colormaps differed; lacked explicit distinction between nominal target Vf and realized discrete voxel fractions.",
        "Matched-view midplane cross-sections (Uniform, VG-MM winner, Full-FE winner); common colormap [0.12, 0.55]; explicit target (0.19328) vs realized (0.19332 / 0.19328) callouts in titles and caption. Exported to data/R5_midplane_*.csv.",
        "PASS: Discrete voxel-grid volume fraction is 0.19332 for Uniform and 0.19328 for VG-MM and Full-FE (target 0.19328); thickness strictly in [0.12, 0.55]. Source: code/r2_figures.py:525-541.",
        "PASS: Checked page 30 of compiled PDF. All 3 panels align with identical aspect ratio and scale; colorbar legible; difference mask clear.",
        "None"
    ],
    [
        "Fig 15 (fig:experiment)",
        "42",
        "manuscript/figures/test_setup.png; original photograph",
        "Crop artifact left two black horizontal bands across rows 290-303 and incomplete bottom border rows 725-744.",
        "Removed artifact bands (filled rows 290-303 with clean white background, cropped bottom edge); original preserved in test_setup_original_backup.png.",
        "PASS: Specimen dimensions (30x30x30 mm coupon, 2x2x2 unit cells) match fabricated coupon specifications.",
        "PASS: Checked page 42 of compiled PDF. Pristine white background; zero black lines; Instron machine and fixture clearly visible.",
        "None"
    ],
    [
        "Fig 16 (fig:expresult)",
        "44",
        "paper/make_figs_v2.py:730-800; results/experimental_coupon_data.json",
        "Raster PNG in early draft; caption referenced stale 'open-to-filled markers'; elastic slope lines needed clear legend.",
        "Switched to vector PDF in manuscript_round2.tex; updated caption text to 'open markers with connecting dotted lines'; visible elastic fit slopes.",
        "PASS: Measured compressive stiffness slopes and relative improvements match FE predictions within experimental tolerance. Source: results/experimental_coupon_data.json.",
        "PASS: Checked page 44 of compiled PDF. Vector lines razor-sharp; experimental vs FE curves distinct; axis labels and units accurate.",
        "None"
    ],
    [
        "Fig A.17 (fig:meshconv)",
        "56",
        "paper/make_figs_v2.py:810-890; Table A.11; results/paper_numbers.json",
        "Audit claimed false blanket convergence thresholds ('< 0.5% to 96^3 and < 0.15% to 128^3') which fail for Gyroid t=0.20 (+1.04% to 96^3, +1.75% to 128^3) and Diamond (+0.64% to 96^3, +0.91% to 128^3).",
        "Replaced false blanket thresholds with exact per-geometry source calculations from Table A.11 and paper_numbers.json. Rescaled figure to 8.4x4.4 in; increased legend font to 8.8 pt; switched to vector PDF.",
        "PASS: Exact per-geometry changes from 64^3 to 96^3 and 128^3: Gyroid t=0.20 (+1.04% to 96^3, +1.75% to 128^3), Gyroid t=0.30 (+0.42% to 96^3, +0.46% to 128^3), Primitive t=0.3387 (-1.26% to 96^3 from non-calibrated 64^3; calibrated ladder mean 0.10243 +- 0.2%), Diamond t=0.2185 (+0.64% to 96^3, +0.91% to 128^3). Source: results/paper_numbers.json:mesh_convergence and Table A.11.",
        "PASS: Checked page 56 of compiled PDF. Spacious 2-panel layout; legend easily readable at publication size; trajectories cleanly resolved.",
        "None"
    ],
    [
        "QC Supplementary: MATLAB Parity Check",
        "N/A (supplementary)",
        "code/verify_figures_matlab.m; figures/data/R1_endpoints.csv, figures/data/R2_pool.csv",
        "Needed independent numerical cross-verification of figure data in native MATLAB R2026a environment.",
        "Authored verify_figures_matlab.m; verified R1 endpoints and R2 pool; generated figures/matlab_parity_check.png via MATLAB MCP.",
        "PASS: MATLAB R2026a confirms identical Spearman rho = 0.664443 on N=192 pool; R1 endpoints match Python to 4 decimal places.",
        "PASS: Verification scatter plot matches Python output exactly with equal axes and identity line.",
        "None"
    ]
]

def main():
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(ROWS)
    print(f"Wrote {OUT_CSV} with {len(ROWS)} evidence-backed audit rows.")

if __name__ == "__main__":
    main()

