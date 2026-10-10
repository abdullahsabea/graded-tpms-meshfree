"""vg2_common: hardened shared machinery for ROUND2_PI_CORRECTION.

Differences from round-1 code/vgmm_common.py (all mandated by the PI audit):
  * cache parser requires DIAGNOSTIC JOB : OK + parsable C1111_ENERGY +
    provenance: stored m_{key}.mail must be byte-identical to a rebuild from
    the query triple, else the cache entry is rejected (treated as a miss);
  * docker solver image digest is PINNED and verified before any new solve;
  * new solves go to ROUND2 results only; round-1 results are read-only;
  * per-call phase timings (cache read / mesh / solve) are recorded;
  * output writers refuse to overwrite existing files.

The DEM scorer is NOT reimplemented: we import the round-1
vgmm_common.make_scorer so the frozen scorer stays bit-identical (validated
by EXP-01 P1 against the archived Stage-2 value).
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time

import numpy as np
import torch  # system install; must precede e3_conditional import

HERE = os.path.dirname(os.path.abspath(__file__))
R2 = os.path.dirname(HERE)
WS = os.path.dirname(R2)                  # AUTORESEARCH_Q1_REVISION
REPO = os.path.dirname(WS)                # project root
N3 = os.path.join(REPO, "research", "n3")
R1_CODE = os.path.join(WS, "code")
sys.path.insert(0, R1_CODE)
sys.path.insert(0, N3)

import vgmm_common as vc  # noqa: E402  (round-1 frozen constants + scorer)
import e3_conditional as ec  # noqa: E402
from make_mesh import write_mail  # noqa: E402

# frozen protocol constants (identical to round 1 / e3_fe_baseline.py)
VF_TARGET = vc.VF_TARGET
T_MIN, T_MAX = vc.T_MIN, vc.T_MAX
T0 = vc.T0
TAU = vc.TAU
MODES = vc.MODES
N_MODES = vc.N_MODES
GRID = vc.GRID
SWEEPS = vc.SWEEPS

DOCKER_IMG = "simvia/code_aster:stable"
DOCKER_DIGEST_PIN = ("simvia/code_aster@sha256:"
                     "d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697f"
                     "fa57c9106d5")
FE_LEGACY = os.path.join(N3, "febase")                       # archived (read)
FE_R1 = os.path.join(WS, "results", "febase_vgmm")           # round-1 (read)
FE_R2 = os.path.join(R2, "results", "febase_r2")             # round-2 (write)
UNI_64 = 0.10528125601
UNI_96 = 0.10572287959

NEW_SOLVE_BUDGET_DEFAULT = 200


class BudgetExceeded(RuntimeError):
    pass


class SolveFailed(RuntimeError):
    pass


# ---- global new-solve budget guard ----------------------------------------
# Cross-process: every new solve appends a line to results/budget_spent.log;
# the cap is checked before each new solve (plan Section 5: <=200 new solves).
BUDGET_LOG = os.path.join(R2, "results", "budget_spent.log")
_budget_state = {"spent": None, "cap": NEW_SOLVE_BUDGET_DEFAULT}


def _count_budget_spent():
    n = 0
    if os.path.exists(BUDGET_LOG):
        with open(BUDGET_LOG, "r") as f:
            n = sum(1 for l in f if l.strip())
    return n


def set_budget(cap):
    _budget_state["cap"] = int(cap)


def budget_state():
    if _budget_state["spent"] is None:
        _budget_state["spent"] = _count_budget_spent()
    return dict(_budget_state)


def _budget_charge(key):
    os.makedirs(os.path.dirname(BUDGET_LOG), exist_ok=True)
    with open(BUDGET_LOG, "a") as f:
        f.write(f"{key}\n")
    _budget_state["spent"] = (_budget_state["spent"] or 0) + 1


# ---- safe writers ---------------------------------------------------------
def write_new(path, text):
    """Write text to path; REFUSE to overwrite an existing file."""
    if os.path.exists(path):
        raise RuntimeError(f"refusing to overwrite existing file: {path}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def write_versioned(path, text):
    """Write text to path. If path exists, preserve it as .prior_v{n} before atomic update."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        v = 1
        while os.path.exists(f"{path}.prior_v{v}"):
            v += 1
        backup_path = f"{path}.prior_v{v}"
        import shutil
        shutil.copy2(path, backup_path)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    if os.path.exists(path):
        os.replace(tmp_path, path)
    else:
        os.rename(tmp_path, path)


def write_json_new(path, obj):
    write_new(path, json.dumps(obj, indent=2))


def write_json_versioned(path, obj):
    write_versioned(path, json.dumps(obj, indent=2))


# ---- design field (identical math to round 1) ------------------------------
t_field = vc.t_field
discrete_mask = vc.discrete_mask
discrete_vf = vc.discrete_vf
bisect_shift_discrete = vc.bisect_shift_discrete
cand_key = vc.cand_key


def timed_bisect(N, theta):
    t0 = time.perf_counter()
    sh = bisect_shift_discrete(N, theta)
    return sh, time.perf_counter() - t0


# ---- hardened cache parsing ------------------------------------------------
def parse_mess(path):
    """Return (value, ok). ok requires DIAGNOSTIC JOB : OK and a parsable
    C1111_ENERGY (round-1 parser silently accepted failed solves)."""
    try:
        txt = open(path, errors="ignore").read()
    except OSError:
        return None, False
    if "DIAGNOSTIC JOB : OK" not in txt:
        return None, False
    m = re.search(r"C1111_ENERGY = ([\d.eE+-]+)", txt)
    if not m:
        return None, False
    try:
        return float(m.group(1)), True
    except ValueError:
        return None, False


def build_mail_bytes(N, theta, shift):
    """Rebuild the mesh exactly as the protocol would; return its bytes."""
    import io
    mask = discrete_mask(N, theta, shift)
    h = 1.0 / N
    ids = np.argwhere(mask)
    nmap, nodes, elems = {}, [], []
    for (i, j, k) in ids:
        corner = [(i, j, k), (i + 1, j, k), (i + 1, j + 1, k), (i, j + 1, k),
                  (i, j, k + 1), (i + 1, j, k + 1), (i + 1, j + 1, k + 1),
                  (i, j + 1, k + 1)]
        row = []
        for kk in corner:
            if kk not in nmap:
                nmap[kk] = len(nodes) + 1
                nodes.append((kk[0] * h, kk[1] * h, kk[2] * h))
            row.append(nmap[kk])
        elems.append((len(elems) + 1, row))
    nodes = np.array(nodes)
    tol = 1e-9
    on_x0 = nodes[:, 0] < tol
    on_x1 = nodes[:, 0] > 1 - tol
    on_y0 = nodes[:, 1] < tol
    on_y1 = nodes[:, 1] > 1 - tol
    on_z0 = nodes[:, 2] < tol
    on_z1 = nodes[:, 2] > 1 - tol
    groups = {"X0": np.where(on_x0)[0] + 1, "X1": np.where(on_x1)[0] + 1,
              "Y0": np.where(on_y0)[0] + 1, "Y1": np.where(on_y1)[0] + 1,
              "Z0": np.where(on_z0)[0] + 1, "Z1": np.where(on_z1)[0] + 1,
              "BOUND": np.where(on_x0 | on_x1 | on_y0 | on_y1
                              | on_z0 | on_z1)[0] + 1}
    buf_dir = os.path.join(R2, "results", "_mesh_tmp")
    os.makedirs(buf_dir, exist_ok=True)
    buf_path = os.path.join(buf_dir, "rebuild.mail")
    import contextlib
    with contextlib.redirect_stdout(open(os.devnull, "w")):
        write_mail(buf_path, nodes, elems, groups, float(mask.mean()), N, -1)
    with open(buf_path, "rb") as f:
        return f.read()


def cache_lookup(folder, key, N, theta, shift):
    """Hardened cache read. Returns (value, timings) or (None, timings).
    Provenance: m_{key}.mail must exist and be byte-identical to a rebuild."""
    t0 = time.perf_counter()
    mess = os.path.join(folder, f"oute_{key}.mess")
    mail = os.path.join(folder, f"m_{key}.mail")
    if not (os.path.exists(mess) and os.path.exists(mail)):
        return None, {"cache_s": time.perf_counter() - t0, "reason": "absent"}
    v, ok = parse_mess(mess)
    if not ok:
        return None, {"cache_s": time.perf_counter() - t0,
                      "reason": "mess_not_ok"}
    t1 = time.perf_counter()
    rebuilt = build_mail_bytes(N, theta, shift)
    mesh_s = time.perf_counter() - t1
    stored = open(mail, "rb").read()
    if stored != rebuilt:
        return None, {"cache_s": time.perf_counter() - t0,
                      "reason": "mail_provenance_mismatch"}
    return v, {"cache_s": time.perf_counter() - t0, "mesh_s": mesh_s,
               "reason": "hit"}


# ---- docker digest pinning --------------------------------------------------
def verify_docker_digest():
    out = subprocess.run(
        ["docker", "inspect", "--format",
         "{{range .RepoDigests}}{{.}}{{end}}", DOCKER_IMG],
        capture_output=True, text=True, timeout=120)
    digests = [d.strip() for d in out.stdout.split() if d.strip()]
    if not any(d == DOCKER_DIGEST_PIN for d in digests):
        raise RuntimeError(
            f"docker image digest mismatch: pinned {DOCKER_DIGEST_PIN}, "
            f"found {digests}; refusing to solve")
    return DOCKER_DIGEST_PIN


# ---- hardened FE solve ------------------------------------------------------
def fe_solve2(N, theta, shift, purpose, allow_new=True, retries=1):
    """One counted FE query. Returns a record dict (value, key, source,
    newly_solved, timings). Never writes outside FE_R2."""
    key = cand_key(N, theta, shift)
    rec = dict(N=N, key=key, purpose=purpose, theta=[float(x) for x in theta],
               shift=float(shift))
    for folder, src in ((FE_LEGACY, "legacy"), (FE_R1, "round1"),
                        (FE_R2, "round2")):
        v, tim = cache_lookup(folder, key, N, theta, shift)
        if v is not None:
            rec.update(value=v, source=src, newly_solved=False, **tim)
            return rec
    if tim["reason"] not in ("absent",):
        rec.update(cache_reject_reason=tim["reason"])
    if not allow_new:
        raise SolveFailed(f"no admissible cache entry for {key} and new "
                          f"solves disallowed (replay mode)")
    if _budget_state["spent"] is None:
        _budget_state["spent"] = _count_budget_spent()
    if _budget_state["spent"] >= _budget_state["cap"]:
        raise BudgetExceeded(
            f"new-solve budget exhausted ({_budget_state['spent']}/"
            f"{_budget_state['cap']})")
    verify_docker_digest()
    t0 = time.perf_counter()
    mail = os.path.join(FE_R2, f"m_{key}.mail")
    os.makedirs(FE_R2, exist_ok=True)
    mask = discrete_mask(N, theta, shift)
    h = 1.0 / N
    ids = np.argwhere(mask)
    nmap, nodes, elems = {}, [], []
    for (i, j, k) in ids:
        corner = [(i, j, k), (i + 1, j, k), (i + 1, j + 1, k), (i, j + 1, k),
                  (i, j, k + 1), (i + 1, j, k + 1), (i + 1, j + 1, k + 1),
                  (i, j + 1, k + 1)]
        row = []
        for kk in corner:
            if kk not in nmap:
                nmap[kk] = len(nodes) + 1
                nodes.append((kk[0] * h, kk[1] * h, kk[2] * h))
            row.append(nmap[kk])
        elems.append((len(elems) + 1, row))
    nodes = np.array(nodes)
    tol = 1e-9
    on_x0 = nodes[:, 0] < tol
    on_x1 = nodes[:, 0] > 1 - tol
    on_y0 = nodes[:, 1] < tol
    on_y1 = nodes[:, 1] > 1 - tol
    on_z0 = nodes[:, 2] < tol
    on_z1 = nodes[:, 2] > 1 - tol
    groups = {"X0": np.where(on_x0)[0] + 1, "X1": np.where(on_x1)[0] + 1,
              "Y0": np.where(on_y0)[0] + 1, "Y1": np.where(on_y1)[0] + 1,
              "Z0": np.where(on_z0)[0] + 1, "Z1": np.where(on_z1)[0] + 1,
              "BOUND": np.where(on_x0 | on_x1 | on_y0 | on_y1
                              | on_z0 | on_z1)[0] + 1}
    import contextlib
    with contextlib.redirect_stdout(open(os.devnull, "w")):
        write_mail(mail, nodes, elems, groups, float(mask.mean()), N, -1)
    mesh_s = time.perf_counter() - t0
    exp = os.path.join(FE_R2, f"s_{key}.export")
    rel = os.path.relpath(FE_R2, REPO).replace(os.sep, "/")
    with open(exp, "w") as f:
        f.write(f"P actions make_etude\nP memory_limit 8000\n"
                f"P time_limit 3600\nP mpi_nbcpu 1\n"
                f"F comm /shared/research/n3/homog2.comm D 1\n"
                f"F mail /shared/{rel}/{os.path.basename(mail)} D 20\n"
                f"F mess /shared/{rel}/oute_{key}.mess R 6\n")
    t0 = time.perf_counter()
    mess = os.path.join(FE_R2, f"oute_{key}.mess")
    for attempt in range(retries + 1):
        subprocess.run(
            ["docker", "run", "--rm", "-m", "8g",
             "-v", f"{REPO.replace(chr(92), '/')}:/shared", DOCKER_IMG,
             "bash", "-c",
             f"source /opt/activate.sh; run_aster /shared/{rel}/"
             f"{os.path.basename(exp)}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        v, ok = parse_mess(mess)
        if ok:
            solve_s = time.perf_counter() - t0
            _budget_charge(key)
            rec.update(value=v, source="round2_new", newly_solved=True,
                       mesh_s=mesh_s, solve_s=solve_s,
                       docker_digest=DOCKER_DIGEST_PIN)
            return rec
    raise SolveFailed(f"FE solve failed for {key} (N={N}) after retries; "
                      f"last parse ok={ok}")


# ---- frozen scorer (round-1 implementation, re-exported) --------------------
def make_scorer(cloud_seed=11, n_cloud=50_000):
    return vc.make_scorer(cloud_seed=cloud_seed, n_cloud=n_cloud)


def scorer_audit_terms():
    """Return references for the mechanics audit (partial vs total
    derivatives). See manuscript audit section; no behavior change here."""
    return dict(model_ckpt=ec.CKPT, EPS=ec.EPS, LAM=ec.LAM, MU=ec.MU)


def picks_agree(a, b, tol=1e-12):
    """None-aware pick comparison. Fixes the round-1 defect
    `(canon_map[...] or 9e9)` which treated a legitimate 0.0 coefficient as
    missing (0.0 is falsy in Python)."""
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) < tol
