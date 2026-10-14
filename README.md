# Replication archive

**Surrogate and boundary-condition errors in graded gyroid-sheet optimization: an independent verification study**
A. El Sabea, K. Moj, A. Kurek (Opole University of Technology). Submitted to *Structural and Multidisciplinary Optimization*.

This archive holds the code, solver inputs, search records, solver result summaries and raw coupon
records behind every number in the article and its supplement. Files keep the relative paths they had
in the project, so each script runs unchanged from the archive root.

## Two checks to run first

```bash
pip install -r requirements.txt       # versions used for the paper; see ENVIRONMENT.md
python reproduce/check_tables.py        # recomputes every table entry from the records: 500/500 cells
python reproduce/regenerate_figures.py  # rebuilds the 9 data figures, compares pixel by pixel
```

`check_tables.py` reads the printed values from `reproduce/printed_tables.json` (extracted from the
submitted LaTeX by `reproduce/extract_printed.py`), recomputes each from the records listed in
`CLAIM_MAP.md`, formats it at the printed precision and compares. It covers every data table: Tables 1–4 and A1 of the article and Tables S1, S2, S4–S7, S9–S11 and S13 of
the supplement, plus the benchmark numbers of Appendix A. (Table S12 compares published methods; Tables S3 and
S8 list settings and protocol deviations; their specimen counts are checked through Table S9.) It runs in under a minute.

`regenerate_figures.py` reruns the scripts of Figs. 1–5, S1, S5, S11 and S12 and compares the output with the
files in `reference_figures/` (the files used in the submitted article). All nine are pixel-identical
with the software of `ENVIRONMENT.md`.

## Where things are

| What | Where |
|---|---|
| Analytic geometry kernel (gyroid, primitive, diamond), self-tests | `research/tpms_levelset.py` (`python tpms_levelset.py gyroid`; outputs in `reproduce/n1_selftest_*.txt`) |
| Classical deep-energy checks (cantilever) | `research/dem_cantilever.py`, `research/n2_metrics.json` |
| Deep-energy models: single-thickness, five training seeds, families, conditional network | `research/n3/dem_*.py`, `e3_conditional.py`; checkpoints `research/n3/*.pt` |
| **The frozen conditional network used by every search and audit** | `research/n3/e3_cond.pt` |
| Score, filtered search, random and score-only policies | `AUTORESEARCH_Q1_REVISION/code/vgmm_common.py`, `run_vgmm.py`; `ROUND2_FINAL_REPAIR/code/r2_arms*.py` |
| Search protocol (frozen before the first run) | `ROUND2_FINAL_REPAIR/plans/ROUND2_PLAN.md` (SHA-256 e56fdf7f…), `AUTORESEARCH_Q1_REVISION/04_preregistered_plan.md` |
| Search records, every seed (each FE call, proposal, accept/reject) | `ROUND2_FINAL_REPAIR/results/r2_arms*/arm_*.json`, `AUTORESEARCH_Q1_REVISION/results/vgmm_result.json`, logs in `ROUND2_FINAL_REPAIR/logs/` |
| 192-candidate pool | `AUTORESEARCH_Q1_REVISION/results/pool_table.csv`, `ROUND2_FINAL_REPAIR/results/r2_pool_replay.json` |
| FE coordinate search | `research/n3/e3_fe_baseline.py`, `.json` |
| Voxel FE (KUBC, energy basis): mesh generators, code_aster input, run scripts, logs | `research/n3/make_mesh*.py`, `homog2.comm`, `run_*.sh`, `study_*.export`, `loge_*.txt` |
| Every cached voxel FE solve of the searches (598) | `fe_cache_summary.csv` (key, C1111, solver diagnostic, design θ and shift where a search record names it) |
| Body-fitted KUBC and periodic models | `research/n3/conforming/`: `make_conforming_mesh.py`, `homog_conf.comm` (KUBC), `homog_conf_pbc.comm` (periodic), `homog_conf_pbc_resid.comm` (periodic + displacement export), `periodicity_residual.py`, `mesh_quality.py`, `corner_pieces.py`, logs `log_*.txt`, summaries `conf_summary.json`, `wpa1_N72_results.json` |
| Score audits, thickness profiles, window sensitivity, external benchmarks | `AUTORESEARCH_Q1_REVISION/_deep_review/wpa/` |
| Coupons: eight raw Instron exports, analysis | `TO_AI-results_instron/TO_AI/U_1_Exports/*.csv`, `paper/verify_experiment_stats.py`, masses `reproduce/coupon_masses.csv` |
| Coupon geometry (printed STL files) and the protocol working documents | `validation/make_dogbone_stl.py`, `make_dogbone_printable.py`; `validation/TEST_PROCEDURE.md`, `EXPERIMENTAL_VALIDATION.md` (kept as written at the time; Table S8 lists the deviations) |
| Figure scripts | `AUTORESEARCH_Q1_REVISION/code/fig_v7_*.py` (style `v7_style.py`), `_deep_review/wpa/a9_*.py`, `a10_*.py` |
| Map from each reported stiffness to design, solver, boundary condition, mesh, volume target, seed | `CLAIM_MAP.md` |
| Checksums of every file | `MANIFEST.sha256` |

## Re-running the solvers

Finite-element solves use code_aster 17.4.0 from the public Docker image
`simvia/code_aster@sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5`.
The run scripts mount the archive root into the container; set `PROJECT_ROOT` to the archive root
(a path Docker can mount) before running them. Meshes are not included: the generators rebuild them
(voxel meshes in seconds; body-fitted meshes need PyVista and TetGen, minutes each).
Voxel solves take minutes. A body-fitted periodic solve at N = 72 has about 3.6 million unknowns and
took about 2.5 h with 70 GB of memory, MUMPS out-of-core.
Deep-energy retraining runs on CPU in float32 and is not bit-reproducible; every reported score uses
the archived checkpoint `research/n3/e3_cond.pt`.

## Not included, and why

- **Meshes, solver scratch and displacement fields** (several GB): regenerated by the archived generators and inputs.
- **Third-party benchmark data** (Appendix A): Fisher et al. (2023), GitHub `jwf23/Equation-Based-Lattice-Structure-Dataset`
  (file `Gyroid_homogenization_data.mat`); Mele et al. (2025), OSF data set doi:10.17605/OSF.IO/C2HR4 (file `homogenization_results.csv`).
  `_deep_review/wpa/a2_external/a2_fisher_mele.py` reads both files from that folder once downloaded; its output is archived
  (`a2_results.json`).
- **Legacy supplementary figures** (Figs. S2–S4, S6–S10) were produced in earlier stages of the project; their files are in
  `reference_figures/`, and their label edits are scripted (`MATERIALS_DESIGN_TRANSFER/manuscript/figures/relabel_*.py`).
  The values printed in Figs. S3 and S7 are checked by `check_tables.py` through Tables S4 and 4; Figs. S4 and S6
  plot the data of Tables S13 and S7.
  Fig. 6 combines renders and a photograph.
- **The printed coupons** themselves; their raw force–displacement records are included.

## Changes made for the archive

Records (JSON, CSV, logs, solver messages) are copied unchanged; `MANIFEST.sha256` lists their hashes.
In the copied run scripts, the absolute project path of the authors' computer was replaced by `${PROJECT_ROOT}`
so that they run elsewhere; no other line was changed. Logs still show the original paths.

## Licences

Code: MIT (`LICENSE`). Data and records produced by the authors, including the coupon exports: CC BY 4.0 (`LICENSE_DATA`).
