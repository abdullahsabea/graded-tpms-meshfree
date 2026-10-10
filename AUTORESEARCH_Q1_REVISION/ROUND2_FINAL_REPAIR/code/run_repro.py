"""run_repro: single documented entry point for ROUND2 reproduction.

Modes:
  audit-only   re-run the read-only PI diagnostic + all defect tests; no FE,
               no artifact changes outside ROUND2 results (idempotent-safe)
  replay       corrected Stage-A reconstructions (pool replay, VG-MM
               historical corrections, seed endpoint check, quadrature
               isolation, mechanics audit, accounting tables). NO new FE
               solves; uses only cached solves (r2_replay uses --keep to
               stay idempotent for reruns)
  new          outcome arms of the frozen ROUND2 plan (B-VGMM 12/13,
               B-RAND 11/12/13, B-DET, B-DEMONLY 11/12/13), then figures and
               the corrected manuscript build

Usage:
  python run_repro.py audit-only
  python run_repro.py replay
  python run_repro.py new [--arm ARM]      (default: all missing arms)
  python run_repro.py figures
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
R2 = os.path.dirname(HERE)
WS = os.path.dirname(R2)
PY = sys.executable


def run(cmd, log_name):
    log = os.path.join(R2, "logs", log_name)
    print(f"== {' '.join(cmd)}  (log: {os.path.basename(log)})", flush=True)
    with open(log, "a") as f:
        r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=WS)
    if r.returncode != 0:
        print(f"   FAILED (see {log})", flush=True)
        return False
    return True


def mode_audit_only():
    ok = run([PY, os.path.join(WS, "PI_AUDIT", "check_existing_evidence.py")],
             "repro_audit_only.log")
    ok &= run([PY, "-m", "pytest", os.path.join(R2, "tests"), "-q"],
              "repro_tests.log")
    return ok


def mode_replay():
    ok = run([PY, os.path.join(HERE, "r2_replay.py"), "--keep"],
             "repro_replay.log")
    ok &= run([PY, os.path.join(HERE, "r2_vgmm_corrections.py")],
              "repro_vgmm_corrections.log")
    ok &= run([PY, os.path.join(HERE, "r2_seed_endpoint_check.py"), "--keep"],
              "repro_seed_endpoint.log")
    ok &= run([PY, os.path.join(HERE, "r2_quadrature.py")],
              "repro_quadrature.log")
    ok &= run([PY, os.path.join(HERE, "r2_mechanics_audit.py")],
              "repro_mechanics.log")
    ok &= run([PY, os.path.join(HERE, "r2_accounting.py"), "--keep"],
              "repro_accounting.log")
    return ok


ARMS = [("demonly", 11), ("demonly", 12), ("demonly", 13),
        ("rand", 11), ("rand", 12), ("rand", 13),
        ("det", None), ("vgmm", 12), ("vgmm", 13)]


def mode_new(only=None):
    ok = True
    for kind, seed in ARMS:
        name = f"{kind}{'' if seed is None else seed}"
        if only and only != name:
            continue
        out = os.path.join(R2, "results", "r2_arms", f"arm_{name}.json")
        if os.path.exists(out):
            print(f"== arm {name} already present, preserving (no rerun)",
                  flush=True)
            continue
        cmd = [PY, os.path.join(HERE, "r2_arms.py"), kind]
        if seed is not None:
            cmd.append(str(seed))
        ok &= run(cmd, f"arm_{name}.log")
    ok &= run([PY, os.path.join(HERE, "r2_seed_endpoint_check.py"), "--keep"],
              "repro_seed_endpoint.log")
    return ok


def mode_figures():
    ok = run([PY, os.path.join(HERE, "r2_figures.py")], "repro_figures.log")
    ok &= run([PY, os.path.join(HERE, "figure_checks.py")],
              "repro_figure_checks.log")
    return ok


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    mode = sys.argv[1]
    if mode == "audit-only":
        sys.exit(0 if mode_audit_only() else 1)
    if mode == "replay":
        sys.exit(0 if mode_replay() else 1)
    if mode == "new":
        only = None
        if len(sys.argv) >= 4 and sys.argv[2] == "--arm":
            only = sys.argv[3]
        sys.exit(0 if mode_new(only) else 1)
    if mode == "figures":
        sys.exit(0 if mode_figures() else 1)
    raise SystemExit(__doc__)
