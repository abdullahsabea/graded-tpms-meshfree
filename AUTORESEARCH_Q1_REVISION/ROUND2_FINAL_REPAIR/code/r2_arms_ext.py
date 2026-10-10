"""Seed extension of the VG-MM vs RANDOM comparison (post-plan, declared 2026-09-26).

Runs the unchanged r2_arms protocol for additional seeds so that each policy has
n = 10 (seeds 11-20). Outputs go to results/r2_arms_ext/ so the prospective
arms of ROUND2_PLAN.md stay separate. The plan's 200-new-solve cap is raised
explicitly for this extension only.

    python r2_arms_ext.py vgmm 14 15 16 17 18 19 20
    python r2_arms_ext.py rand 14 15 16 17 18 19 20
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vg2_common as v2  # noqa: E402
import r2_arms  # noqa: E402

EXT_DIR = os.path.join(v2.R2, "results", "r2_arms_ext")
os.makedirs(EXT_DIR, exist_ok=True)
r2_arms.ARMS_DIR = EXT_DIR
v2.set_budget(v2.budget_state()["spent"] + 600)

if __name__ == "__main__":
    kind = sys.argv[1]
    for s in sys.argv[2:]:
        if os.path.exists(os.path.join(EXT_DIR, f"arm_{kind}{s}.json")):
            print(f"skip {kind}{s} (exists)", flush=True)
            continue
        print(f"=== {kind} seed {s} ===", flush=True)
        r2_arms.run_arm(kind, int(s))
