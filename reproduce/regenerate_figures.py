"""Regenerate the article's data figures from the archived records and compare
each with the figure file used in the submitted article (reference_figures/).

Usage (from the archive root):   python reproduce/regenerate_figures.py
Figures are written to AUTORESEARCH_Q1_REVISION/MATERIALS_DESIGN_TRANSFER/manuscript/figures/.
Comparison is on the PNG companions, pixel by pixel. Exit status 0 if all match.
"""
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "AUTORESEARCH_Q1_REVISION/code"
WPA = ROOT / "AUTORESEARCH_Q1_REVISION/_deep_review/wpa"
FIG = ROOT / "AUTORESEARCH_Q1_REVISION/MATERIALS_DESIGN_TRANSFER/manuscript/figures"
REF = ROOT / "reference_figures"

# (working directory, script, figure stem, where it appears)
JOBS = [
    (CODE, "fig_v7_network.py", "fig_v7_network", "Fig. 1"),
    (CODE, "fig_v7_designs.py", "fig_v7_designs", "Fig. 2"),
    (CODE, "fig_v7_pbc.py", "fig_v7_pbc", "Fig. 3"),
    (WPA, "a9_thickness_profiles.py", "fig_wpa_thickness_profiles", "Fig. S11"),
    (CODE, "fig_v7_ranking.py", "fig_v7_ranking", "Fig. 4"),
    (CODE, "fig_v7_policy_seeds.py", "fig_v7_policy_seeds", "Fig. 5"),
    (WPA, "a10_window_sensitivity.py", "fig_wpa_window_sensitivity", "Fig. S12"),
    (CODE, "fig_v7_method.py", "fig_v7_method", "Fig. S1"),
    (CODE, "fig_v7_pool.py", "fig_v7_pool", "Fig. S5"),
]

ok_all = True
for wd, script, stem, where in JOBS:
    r = subprocess.run([sys.executable, script], cwd=wd, capture_output=True, text=True)
    if r.returncode:
        print(f"FAIL {where:8s} {script}: {r.stderr.strip().splitlines()[-1]}")
        ok_all = False
        continue
    new, ref = FIG / f"{stem}.png", REF / f"{stem}.png"
    a, b = Image.open(new).convert("RGB"), Image.open(ref).convert("RGB")
    same = a.size == b.size and ImageChops.difference(a, b).getbbox() is None
    ok_all &= same
    print(f"{'OK  ' if same else 'DIFF'} {where:8s} {stem}")
print("all figures identical" if ok_all else "some figures differ")
sys.exit(0 if ok_all else 1)
