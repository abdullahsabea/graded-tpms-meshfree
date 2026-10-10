"""Least-squares Richardson extrapolation of a voxel-FE mesh ladder.

Fits  C(h) = C0 - A h^p  to the (h, C) pairs of a volume-calibrated ladder and
returns the continuum estimate C0 with the fitted order p. With four grids the
fit is over-determined, so the residual is a usable indicator of how well the
single-power model describes the sequence.
"""
import numpy as np


def fit(hs, cs, p_grid=np.linspace(0.3, 3.0, 541)):
    hs, cs = np.asarray(hs, float), np.asarray(cs, float)
    best = None
    for p in p_grid:
        # linear in (C0, A) for fixed p:  cs = C0 - A h^p
        M = np.column_stack([np.ones_like(hs), -hs**p])
        sol, *_ = np.linalg.lstsq(M, cs, rcond=None)
        res = float(np.sqrt(np.mean((M @ sol - cs) ** 2)))
        if best is None or res < best[0]:
            best = (res, float(p), float(sol[0]), float(sol[1]))
    res, p, C0, A = best
    return {"C0": C0, "p": p, "A": A, "rms_residual": res}


if __name__ == "__main__":
    import json, sys, os
    HERE = os.path.dirname(os.path.abspath(__file__))
    src = json.load(open(os.path.join(HERE, "e3_iso_resolution.json")))
    print("case          C0 (continuum)     p    rms      ladder")
    out = {}
    for case, rows in src["cases_vf_calibrated"].items():
        Ns = sorted(int(k) for k in rows)
        if len(Ns) < 3:
            continue
        hs = [1.0 / N for N in Ns]
        cs = [rows[str(N)]["C1111"] if str(N) in rows else rows[N]["C1111"] for N in Ns]
        f = fit(hs, cs)
        out[case] = f
        print(f"{case:12s} {f['C0']:.5f}   {f['p']:.2f}  {f['rms_residual']:.1e}  "
              + " ".join(f"{c:.5f}" for c in cs))
    if "uniform" in out:
        for case in ("graded", "printable"):
            if case in out:
                g = (out[case]["C0"] / out["uniform"]["C0"] - 1) * 100
                print(f"extrapolated gain {case:10s} = {g:+.2f}%")
                out.setdefault("gains_extrapolated", {})[case] = g
    json.dump(out, open(os.path.join(HERE, "e3_richardson.json"), "w"), indent=2)
