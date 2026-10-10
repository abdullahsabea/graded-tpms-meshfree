"""r2_manifest_figures: generate figures/figure_manifest.csv mapping every panel
to its input files/hashes, plotting script, execution command, output file,
manuscript label, and retained/changed status.
"""
import csv
import hashlib
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
R2 = os.path.dirname(HERE)
FIG = os.path.join(R2, "figures")
MAN_FIG = os.path.join(R2, "manuscript", "figures")
OUT_CSV = os.path.join(FIG, "figure_manifest.csv")

def sha256(path):
    if not os.path.exists(path):
        return "missing"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()[:16]

def main():
    # Copy R1-R5 to manuscript/figures
    shutil.copy2(os.path.join(FIG, "R1_budget_steps.pdf"), os.path.join(MAN_FIG, "fig11_vgmm_budget.pdf"))
    shutil.copy2(os.path.join(FIG, "R1_budget_steps.png"), os.path.join(MAN_FIG, "fig11_vgmm_budget.png"))
    shutil.copy2(os.path.join(FIG, "R2_parity.pdf"), os.path.join(MAN_FIG, "fig12_pool_discordance.pdf"))
    shutil.copy2(os.path.join(FIG, "R2_parity.png"), os.path.join(MAN_FIG, "fig12_pool_discordance.png"))
    shutil.copy2(os.path.join(FIG, "R3_policy_seeds.pdf"), os.path.join(MAN_FIG, "fig13_policy_seeds.pdf"))
    shutil.copy2(os.path.join(FIG, "R3_policy_seeds.png"), os.path.join(MAN_FIG, "fig13_policy_seeds.png"))
    shutil.copy2(os.path.join(FIG, "R4_method_diagram.pdf"), os.path.join(MAN_FIG, "fig14_method_diagram.pdf"))
    shutil.copy2(os.path.join(FIG, "R4_method_diagram.png"), os.path.join(MAN_FIG, "fig14_method_diagram.png"))
    shutil.copy2(os.path.join(FIG, "R5_geometry.pdf"), os.path.join(MAN_FIG, "fig15_geometry.pdf"))
    shutil.copy2(os.path.join(FIG, "R5_geometry.png"), os.path.join(MAN_FIG, "fig15_geometry.png"))
    print("Copied R1-R5 to manuscript/figures/")

    records = [
        {
            "panel_id": "R1_budget_steps",
            "manuscript_label": "Figure 11",
            "manuscript_label": "Figure 10 (file fig11_vgmm_budget.pdf)",
            "status": "REPLACED",
            "reason_for_change": "Replaces round-1 scan-index x-axis with true unique FE evaluation steps; separates search-grid trajectories (64^3) from finer-grid confirmation (96^3); includes matched-budget controls and batch-complete frontier",
            "plotting_script": "code/r2_figures.py",
            "command": "python code/r2_figures.py",
            "primary_inputs": "results/r2_pool_replay.json, results/vgmm_result.json, results/r2_arms/*.json, results/r2_accounting.json",
            "input_hashes": f"r2_pool={sha256(os.path.join(R2, 'results', 'r2_pool_replay.json'))}, r2_acc={sha256(os.path.join(R2, 'results', 'r2_accounting.json'))}",
            "output_pdf": "figures/R1_budget_steps.pdf",
            "output_png": "figures/R1_budget_steps.png",
            "data_csv": "figures/data/R1_endpoints.csv"
        },
        {
            "panel_id": "R2_parity",
            "manuscript_label": "Figure 12",
            "manuscript_label": "Figure 11 (file fig12_pool_discordance.pdf)",
            "status": "REPLACED",
            "reason_for_change": "Replaces misleading DEM/FE-baseline ratio with like-for-like parity and cloud-specific normalized DEM gain; includes tie-aware library Spearman (0.6644) and Kendall (0.4781); splits discordance into ID-only (0) vs material ranking loss (21/24)",
            "plotting_script": "code/r2_figures.py",
            "command": "python code/r2_figures.py",
            "primary_inputs": "results/r2_pool_replay.json, results/r2_quadrature_isolation.json",
            "input_hashes": f"r2_pool={sha256(os.path.join(R2, 'results', 'r2_pool_replay.json'))}, quad={sha256(os.path.join(R2, 'results', 'r2_quadrature_isolation.json'))}",
            "output_pdf": "figures/R2_parity.pdf",
            "output_png": "figures/R2_parity.png",
            "data_csv": "figures/data/R2_pool.csv, figures/data/R2_groups.csv"
        },
        {
            "panel_id": "R3_policy_seeds",
            "manuscript_label": "Figure 13",
            "manuscript_label": "Figure 12 (file fig13_policy_seeds.pdf)",
            "status": "NEW",
            "reason_for_change": "Controlled comparison across seeds and policy families at matched budget (26 calls); isolates quadrature seeds from policy rules; shows individual endpoints without decorative violins or unsupported population bands",
            "plotting_script": "code/r2_figures.py",
            "command": "python code/r2_figures.py",
            "primary_inputs": "results/r2_accounting.json, results/r2_arms/*.json",
            "input_hashes": f"r2_acc={sha256(os.path.join(R2, 'results', 'r2_accounting.json'))}",
            "output_pdf": "figures/R3_policy_seeds.pdf",
            "output_png": "figures/R3_policy_seeds.png",
            "data_csv": "figures/data/R3_family_endpoints.csv"
        },
        {
            "panel_id": "R4_method_diagram",
            "manuscript_label": "Figure 14",
            "manuscript_label": "Figure 13 (file fig14_method_diagram.pdf)",
            "status": "NEW",
            "reason_for_change": "Clear workflow diagram distinguishing operations performed by the frozen conditional DEM surrogate (vermillion) from operations performed by volume-calibrated voxel-FE (blue/grey); strictly reflects actual code without imaginary components",
            "plotting_script": "code/r2_figures.py",
            "command": "python code/r2_figures.py",
            "primary_inputs": "code/r2_arms.py, plans/ROUND2_PLAN.md",
            "input_hashes": f"arms_code={sha256(os.path.join(R2, 'code', 'r2_arms.py'))}",
            "output_pdf": "figures/R4_method_diagram.pdf",
            "output_png": "figures/R4_method_diagram.png",
            "data_csv": "n/a (diagram)"
        },
        {
            "panel_id": "R5_geometry",
            "manuscript_label": "Figure 15",
            "manuscript_label": "Figure 14 (file fig15_geometry.pdf)",
            "status": "NEW",
            "reason_for_change": "Matched-view midplane geometry and solid mask comparison of Uniform, VG-MM winner, and Full-FE winner under identical scale, view, thickness color limits [0.12, 0.55], and loading orientation; verified discrete VF = 0.19328",
            "plotting_script": "code/r2_figures.py",
            "command": "python code/r2_figures.py",
            "primary_inputs": "results/r2_pool_replay.json, results/vgmm_result.json, results/r2_arms/arm_vgmm12.json",
            "input_hashes": f"r2_pool={sha256(os.path.join(R2, 'results', 'r2_pool_replay.json'))}",
            "output_pdf": "figures/R5_geometry.pdf",
            "output_png": "figures/R5_geometry.png",
            "data_csv": "figures/data/R5_midplane_0.csv, figures/data/R5_midplane_1.csv, figures/data/R5_midplane_2.csv"
        },
        {
            "panel_id": "MATLAB_parity_check",
            "manuscript_label": "QC supplementary",
            "status": "NEW",
            "reason_for_change": "Cross-environment validation executed directly in MATLAB R2026a via MATLAB MCP, confirming tie-aware Spearman rank correlation rho=0.664443 matches Python SciPy to 1e-6",
            "plotting_script": "code/verify_figures_matlab.m",
            "command": "evaluate_matlab_code(verify_figures_matlab())",
            "primary_inputs": "figures/data/R1_endpoints.csv, figures/data/R2_pool.csv",
            "input_hashes": f"r2_pool_csv={sha256(os.path.join(FIG, 'data', 'R2_pool.csv'))}",
            "output_pdf": "n/a",
            "output_png": "figures/matlab_parity_check.png",
            "data_csv": "figures/data/R2_pool.csv"
        }
    ]

    fieldnames = ["panel_id", "manuscript_label", "status", "reason_for_change",
                  "plotting_script", "command", "primary_inputs", "input_hashes",
                  "output_pdf", "output_png", "data_csv"]

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in records:
            w.writerow(r)
    print(f"Wrote {OUT_CSV} with {len(records)} entries")

if __name__ == "__main__":
    main()

