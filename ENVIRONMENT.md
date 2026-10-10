# Software environment

Versions used for every result in the article (checked on the authors' machine, October 2026).

| Component | Version |
|---|---|
| Python | 3.11.9 |
| PyTorch | 2.5.1 (CPU arithmetic used for all deep-energy work) |
| NumPy | 2.3.5 |
| SciPy | 1.16.3 |
| Matplotlib, Pillow | for figures |
| PyVista | 0.46.4 |
| TetGen (Python) | 0.8.3 |
| code_aster | 17.4.0, Docker image `simvia/code_aster@sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5` |
| Linear solver | MUMPS (as shipped in the image); periodic solves `GESTION_MEMOIRE='AUTO'`, `RESI_RELA=1e-6` |

Note: the geometry self-test (`research/tpms_levelset.py`) reports finite-difference residuals near
1e-9; their last digit depends on the PyTorch build. Supplementary Table S1 prints the values obtained
with the versions above (`reproduce/n1_selftest_*.txt`).
