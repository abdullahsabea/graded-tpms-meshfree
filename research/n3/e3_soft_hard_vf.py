"""Q4 (TeX AAR ~550): quantify the soft--hard volume-fraction offset at tau=0.02.

The optimizer constrains the SMOOTHED volume
    Vf_soft = mean_x sigmoid((t(x) - |F(x)|) / tau),
while the audit and every FE comparison use the HARD indicator
    Vf_hard = mean_x [ |F(x)| < t(x) ]  (voxelized per grid in the FE chain).
This script measures the offset Vf_soft - Vf_hard for

  * the frozen printable optimum theta* + t0shift
    (e3_opt_result_printable.json), and
  * the uniform baseline theta = 0, t = 0.30

on three point sets: the optimizer's own fixed 50k cloud (generator seed
11), an independent 2M cloud (seed 77), and a dense 256^3 voxel grid
(chunked).  Writes research/n3/e3_soft_hard_vf.json.

Run: python e3_soft_hard_vf.py   (~10 s, no network weights required)
"""
import json
import os
import sys

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import e3_conditional as ec
from e3_optimize_printable import psi_and_grad, MODES, T0, T_MIN, T_MAX


def soft_hard(absF, t, tau):
    w = torch.sigmoid((t - absF) / tau)
    hard = (absF < t).float()
    return float(w.mean()), float(hard.mean())


def measure(points, theta, shift, tau):
    psiv, _ = psi_and_grad(points)
    t = (T0 + psiv @ theta + shift).clamp(T_MIN, T_MAX)
    absF = torch.abs(ec.Fval(points))
    return soft_hard(absF, t, tau)


def main():
    res = json.load(open(os.path.join(HERE, "e3_opt_result_printable.json")))
    theta = torch.tensor(res["theta"], dtype=torch.float64)
    shift = float(res["t0shift"])
    tau = float(res["tau"])
    print(f"frozen theta*: {len(theta)} coeffs, t0shift={shift:+.6f}, tau={tau}")

    out = {"tau": tau, "t0shift": shift, "designs": {}}

    designs = {
        "uniform_t0.30": (torch.zeros_like(theta), 0.0),
        "printable_opt_frozen": (theta, shift),
    }

    # 1) the optimizer's own fixed cloud (must reproduce stored Vf_final)
    g = torch.Generator().manual_seed(11)
    pts50k = torch.rand(50_000, 3, generator=g).double()
    # 2) independent dense cloud
    g2 = torch.Generator().manual_seed(77)
    pts2m = torch.rand(2_000_000, 3, generator=g2).double()

    for name, (th, sh) in designs.items():
        row = {}
        vs, vh = measure(pts50k, th, sh, tau)
        row["opt_cloud_50k"] = {"Vf_soft": vs, "Vf_hard": vh,
                                "offset_pp": 100.0 * (vs - vh)}
        se = 100.0 * np.sqrt(max(vh, 1 - vh) / len(pts50k))  # MC se (pp), worst of the two
        row["opt_cloud_50k"]["offset_mc_se_pp"] = float(se)
        vs2, vh2 = measure(pts2m, th, sh, tau)
        row["indep_cloud_2M"] = {"Vf_soft": vs2, "Vf_hard": vh2,
                                 "offset_pp": 100.0 * (vs2 - vh2)}
        out["designs"][name] = row
        print(f"{name}: soft={vs2:.6f} hard={vh2:.6f} "
              f"offset={100 * (vs2 - vh2):+.4f} pp (2M cloud; "
              f"50k cloud offset {100 * (vs - vh):+.4f} pp)")

    # 3) dense 256^3 voxel grid hard volume for the frozen optimum (chunked)
    n = 256
    g1d = torch.linspace(0.5 / n, 1 - 0.5 / n, n, dtype=torch.float64)
    hard_cnt, total, soft_sum = 0, 0, 0.0
    for i in range(n):
        grid = torch.stack(torch.meshgrid(g1d[i], g1d, g1d, indexing="ij"), -1).reshape(-1, 3)
        psiv, _ = psi_and_grad(grid)
        t = (T0 + psiv @ theta + shift).clamp(T_MIN, T_MAX)
        absF = torch.abs(ec.Fval(grid))
        hard_cnt += int((absF < t).sum())
        soft_sum += float(torch.sigmoid((t - absF) / tau).sum())
        total += grid.shape[0]
    vf_vox = hard_cnt / total
    vf_soft_vox = soft_sum / total
    out["designs"]["printable_opt_frozen"]["voxel_256"] = {
        "Vf_hard": vf_vox, "Vf_soft": vf_soft_vox,
        "offset_pp": 100.0 * (vf_soft_vox - vf_vox)}
    print(f"printable_opt_frozen on 256^3 voxel grid: hard Vf={vf_vox:.6f} "
          f"soft Vf={vf_soft_vox:.6f} offset={100 * (vf_soft_vox - vf_vox):+.4f} pp")

    path = os.path.join(HERE, "e3_soft_hard_vf.json")
    json.dump(out, open(path, "w"), indent=2)
    print("wrote", path)


if __name__ == "__main__":
    main()
