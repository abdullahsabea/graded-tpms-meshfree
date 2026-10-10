"""FE-in-the-loop baseline for the 12-parameter thickness-grading problem.

Answers the reviewer's strongest strategic question directly: what would
the SAME coordinate search have found if every candidate had been scored
by voxel FE (code_aster, Hill-Mandel energy basis, discrete-volume
calibrated at the search grid) instead of the conditional DEM?

Protocol mirrors e3_optimize.py Stage 2 exactly:
  * 12 Fourier coefficients, trial grid linspace(-0.22, 0.22, 9)
  * 2 sweeps, greedy per-mode update
  * thickness bounds [0.12, 0.55], target Vf* = 0.19328
  * per-trial uniform offset re-solved by bisection so every candidate
    carries the SAME DISCRETE solid fraction at the search grid
    (discrete-volume calibration, as in the paper's FE references)

Search grid N=SEARCH_N (default 64). The winner is re-confirmed at
N=CONFIRM_N (default 96). Uniform baseline solved at both grids.

Resume-safe: every solve is cached by a content hash of (theta, shift, N).

Usage: python e3_fe_baseline.py [SEARCH_N [CONFIRM_N]]
Output: e3_fe_baseline.json, meshes/solves under febase/
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_mesh import gyroid_F, write_mail

WIN = os.environ["PROJECT_ROOT"] + "/research/n3"
IMG = "simvia/code_aster:stable"
WORK = os.path.join(HERE, "febase")
os.makedirs(WORK, exist_ok=True)

VF_TARGET = 0.19328
T_MIN, T_MAX = 0.12, 0.55
MODES = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, 0, 1), (0, 1, 1)]
N_MODES = 12
GRID = np.linspace(-0.22, 0.22, 9)
SWEEPS = 2
WORKERS = 6

# fixed coarse MC cloud for the CONTINUUM bisection seed (fast path only)
_rng = np.random.default_rng(11)
_CLOUD = _rng.random((50_000, 3))
_ABSF = np.abs(gyroid_F(_CLOUD[:, 0], _CLOUD[:, 1], _CLOUD[:, 2]))


def t_field(X, Y, Z, theta, shift):
    v = 0.30 + shift + 0 * X
    for i, (a, b, c) in enumerate(MODES):
        ph = 2 * np.pi * (a * X + b * Y + c * Z)
        v = v + theta[2 * i] * np.cos(ph) + theta[2 * i + 1] * np.sin(ph)
    return np.clip(v, T_MIN, T_MAX)


def discrete_mask(N, theta, shift):
    h = 1.0 / N
    c = (np.arange(N) + 0.5) * h
    X, Y, Z = np.meshgrid(c, c, c, indexing="ij")
    return (np.abs(gyroid_F(X, Y, Z)) - t_field(X, Y, Z, theta, shift)) < 0.0


def discrete_vf(N, theta, shift):
    return float(discrete_mask(N, theta, shift).mean())


def bisect_shift_discrete(N, theta):
    """Uniform offset so the DISCRETE solid fraction at grid N hits target."""
    lo, hi = -0.30, 0.30
    for _ in range(28):
        mid = 0.5 * (lo + hi)
        if discrete_vf(N, theta, mid) < VF_TARGET:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def build_mail(path, N, theta, shift):
    mask = discrete_mask(N, theta, shift)
    h = 1.0 / N
    ids = np.argwhere(mask)
    nmap, nodes, elems = {}, [], []
    for (i, j, k) in ids:
        corner = [(i, j, k), (i + 1, j, k), (i + 1, j + 1, k), (i, j + 1, k),
                  (i, j, k + 1), (i + 1, j, k + 1), (i + 1, j + 1, k + 1),
                  (i, j + 1, k + 1)]
        row = []
        for key in corner:
            if key not in nmap:
                nmap[key] = len(nodes) + 1
                nodes.append((key[0] * h, key[1] * h, key[2] * h))
            row.append(nmap[key])
        elems.append((len(elems) + 1, row))
    nodes = np.array(nodes)
    tol = 1e-9
    on_x0 = nodes[:, 0] < tol; on_x1 = nodes[:, 0] > 1 - tol
    on_y0 = nodes[:, 1] < tol; on_y1 = nodes[:, 1] > 1 - tol
    on_z0 = nodes[:, 2] < tol; on_z1 = nodes[:, 2] > 1 - tol
    groups = {"X0": np.where(on_x0)[0] + 1, "X1": np.where(on_x1)[0] + 1,
              "Y0": np.where(on_y0)[0] + 1, "Y1": np.where(on_y1)[0] + 1,
              "Z0": np.where(on_z0)[0] + 1, "Z1": np.where(on_z1)[0] + 1,
              "BOUND": np.where(on_x0 | on_x1 | on_y0 | on_y1 | on_z0 | on_z1)[0] + 1}
    write_mail(path, nodes, elems, groups, float(mask.mean()), N, -1)
    return int(mask.sum())


def fe_solve(N, theta, shift):
    """C1111_ENERGY for one candidate; cached by content hash."""
    key = hashlib.sha1(
        (f"{N}|{np.asarray(theta).round(6).tobytes()}|{shift:.6f}"
         ).encode()).hexdigest()[:16]
    mess = os.path.join(WORK, f"oute_{key}.mess")
    if os.path.exists(mess):
        m = re.search(r"C1111_ENERGY = ([\d.eE+-]+)",
                      open(mess, errors="ignore").read())
        if m:
            return float(m.group(1)), key, True
    mail = os.path.join(WORK, f"m_{key}.mail")
    n_elem = build_mail(mail, N, theta, shift)
    exp = os.path.join(WORK, f"s_{key}.export")
    with open(exp, "w") as f:
        f.write(f"P actions make_etude\nP memory_limit 8000\n"
                f"P time_limit 3600\nP mpi_nbcpu 1\n"
                f"F comm /shared/homog2.comm D 1\n"
                f"F mail /shared/febase/{os.path.basename(mail)} D 20\n"
                f"F mess /shared/febase/{os.path.basename(mess)} R 6\n")
    subprocess.run(["docker", "run", "--rm", "-m", "8g",
                    "-v", f"{WIN}:/shared", IMG, "bash", "-c",
                    f"source /opt/activate.sh; run_aster /shared/febase/"
                    f"{os.path.basename(exp)}"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   check=False)
    m = re.search(r"C1111_ENERGY = ([\d.eE+-]+)",
                  open(mess, errors="ignore").read()) if os.path.exists(mess) else None
    if not m:
        raise RuntimeError(f"FE solve failed for {key} (N={N})")
    return float(m.group(1)), key, False


def score_pool(ex, N, trials):
    """Evaluate a batch of (theta, shift) candidates in parallel workers."""
    return list(ex.map(lambda tr: fe_solve(N, tr[0], tr[1])[0], trials))


def main():
    search_n = int(sys.argv[1]) if len(sys.argv) > 1 else 64
    confirm_n = int(sys.argv[2]) if len(sys.argv) > 2 else 96

    # uniform baseline at both grids, discrete-calibrated identically
    s_uni = bisect_shift_discrete(search_n, np.zeros(N_MODES))
    c_uni, _, _ = fe_solve(search_n, np.zeros(N_MODES), s_uni)
    print(f"uniform @N{search_n}: shift={s_uni:+.4f}  C1111={c_uni:.5f}",
          flush=True)
    s_uni_c = bisect_shift_discrete(confirm_n, np.zeros(N_MODES))
    c_uni_c, _, _ = fe_solve(confirm_n, np.zeros(N_MODES), s_uni_c)
    print(f"uniform @N{confirm_n}: shift={s_uni_c:+.4f}  C1111={c_uni_c:.5f}",
          flush=True)

    theta = np.zeros(N_MODES)
    hist = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for sweep in range(SWEEPS):
            for m in range(N_MODES):
                trials, metas = [], []
                for cand in GRID:
                    tr = theta.copy(); tr[m] = float(cand)
                    sh = bisect_shift_discrete(search_n, tr)
                    trials.append((tr, sh))
                    metas.append(float(cand))
                # current point may be off-grid: include it via cache
                sh0 = bisect_shift_discrete(search_n, theta)
                vals = score_pool(ex, search_n, trials + [(theta, sh0)])
                best_i = int(np.argmax(vals))
                theta = trials[best_i][0].copy()
                shift_best = trials[best_i][1]
                hist.append(dict(sweep=sweep, mode=m,
                                 pick=float(trials[best_i][0][m]),
                                 C1111=vals[best_i]))
                print(f"sweep {sweep} mode {m:2d}: "
                      f"pick {trials[best_i][0][m]:+.3f} "
                      f"C1111={vals[best_i]:.5f}", flush=True)

    # confirm winner at the finer grid
    sh_c = bisect_shift_discrete(confirm_n, theta)
    c_win_c, _, _ = fe_solve(confirm_n, theta, sh_c)
    sh_s = bisect_shift_discrete(search_n, theta)
    c_win_s, _, _ = fe_solve(search_n, theta, sh_s)
    out = dict(search_N=search_n, confirm_N=confirm_n,
               VF_target=VF_TARGET, grid=GRID.tolist(), sweeps=SWEEPS,
               theta=theta.tolist(), shift_search=float(sh_s),
               C1111_uniform_search=c_uni, C1111_uniform_confirm=c_uni_c,
               C1111_winner_search=float(c_win_s),
               C1111_winner_confirm=float(c_win_c),
               gain_search_pct=100 * (c_win_s / c_uni - 1),
               gain_confirm_pct=100 * (c_win_c / c_uni_c - 1),
               history=hist)
    json.dump(out, open(os.path.join(HERE, "e3_fe_baseline.json"), "w"),
              indent=2)
    print(json.dumps({k: v for k, v in out.items() if k != "history"},
                     indent=2))


if __name__ == "__main__":
    main()
