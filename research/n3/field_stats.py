"""Distributional statistics of the FE strain-energy density field.

Answers, with the field rather than by assertion, what the optimizer did to the
cell. Writes research/n3/field_stats.json (Lorenz curve of strain energy against
material, plus concentration measures) for the manuscript and its figures.

The volume-mean of the nodal field is cross-checked against C1111/(2 Vf), the
same quantity computed from the reaction sum, as a consistency test on the
export. Nodal averaging is a biased estimator of the volume mean (nodes are not
distributed uniformly through the solid), so the concentration measures are used
only to compare designs built on the same family and mesh topology -- uniform
versus graded gyroid, whose node counts agree to 0.4% -- where the bias cancels.
"""
import json
import os

import numpy as np

_trapz = getattr(np, "trapezoid", None) or np.trapz

HERE = os.path.dirname(os.path.abspath(__file__))
VF = 0.19328
C1111 = {"uniform": 0.11066567250, "graded": 0.11666919308,
         "primitive": 0.090745156217, "diamond": 0.11514476608}


def stats(tag):
    d = np.load(os.path.join(HERE, f"fields_{tag}.npz"))
    e = d["ENEL"] / 1e-6                      # unit-strain energy density
    e = e[np.isfinite(e)]
    s = np.sort(e)                            # least loaded first
    cum = np.cumsum(s) / s.sum()
    m = np.arange(1, len(s) + 1) / len(s)
    k = max(1, len(s) // 200)                 # thin the curve for plotting
    out = {
        "n_nodes": int(len(e)),
        "mean": float(e.mean()),
        "mean_from_C1111": float(C1111[tag] / 2.0 / VF),
        "cv": float(e.std() / e.mean()),
        "median_over_mean": float(np.median(e) / e.mean()),
        "frac_below_20pct_of_mean": float((e < 0.2 * e.mean()).mean()),
        "p90_over_p10": float(np.percentile(e, 90) / np.percentile(e, 10)),
        "top20_energy_pct": float(100 * s[-len(s) // 5:].sum() / s.sum()),
        "gini": float(1 - 2 * _trapz(cum, m)),
        "lorenz": {"material": m[::k].tolist(), "energy": cum[::k].tolist()},
    }
    return out


def main():
    out = {t: stats(t) for t in ("uniform", "graded", "primitive", "diamond")}
    json.dump(out, open(os.path.join(HERE, "field_stats.json"), "w"), indent=2)
    print(f"{'case':10s} {'mean':>8s} {'vs C1111':>9s} {'CV':>6s} "
          f"{'<20%':>6s} {'top20%E':>8s} {'Gini':>6s}")
    for t, s in out.items():
        print(f"{t:10s} {s['mean']:8.4f} {s['mean_from_C1111']:9.4f} {s['cv']:6.2f} "
              f"{100*s['frac_below_20pct_of_mean']:5.1f}% {s['top20_energy_pct']:7.1f}% "
              f"{s['gini']:6.3f}")
    print("wrote", os.path.join(HERE, "field_stats.json"))


if __name__ == "__main__":
    main()
