"""Recompute the eight-specimen elastic statistics directly from Instron CSVs.

This is the single authoritative generator of ``validation/table8_results.json``
(the JSON's ``analysis.script`` field names this file).  It supersedes:

* ``testdata/results_table8.json`` -- an earlier analysis whose writing
  script is not preserved in the repository (its ``n_fitted`` key is
  corrupted); retained untouched as a historical artifact, and
* ``validation/fill_table8.py`` -- the pre-registered optical-tracking
  pipeline (video strain, final-unloading branch), which does not match the
  executed monotonic crosshead protocol.

Conventions (fixed by the executed protocol, see
``validation/EXPERIMENTAL_VALIDATION.md``):
  * loading branch only (samples up to peak force);
  * linear regression of stress vs crosshead strain over 150--600 N,
    A_ref = 450 mm^2, L0 = 100 mm witness-span convention;
  * R = mean(E*_graded) / mean(E*_uniform), n = 4 per group; and a
    transparent post hoc leave-U1-out sensitivity because U1 was run at a
    materially lower crosshead rate than the remaining specimens.

Statistics reported for R:
  * normal (delta-method) 95% CI -- primary in the pre-registered analysis;
  * t-based 95% CI with df = 3 (the smaller group n minus one; quoted in
    the manuscript because n = 4 per group makes the normal approximation
    optimistic);
  * percentile bootstrap CI (20000 resamples, seed 0, group resampling of
    specimen means -- the fill_table8.py scheme);
  * mass-adjusted sensitivity R: E* corrected to the pooled mean mass by
    E*/(m/m_bar)^k for k = 1 (linear material scaling), k = 2 (bending-type
    lattice scaling; gives the manuscript's quoted 0.914), and the
    within-group-fitted exponent (group-demeaned pooled regression, which
    avoids the between-group confound that makes a naive pooled fit return
    a negative exponent).

Window stability: the fitted slope is re-evaluated over two explicit
families of regression windows spanning 100--800 N (a 450 N-wide family
matching the primary window's width, and 100 N-wide sliding windows),
recording the minimum per-specimen sample count per window.  NOTE: R
declines monotonically as the window slides to higher force (graded group
softening approaching its lower peak force); the primary 150--600 N window
keeps every graded specimen below ~70% of its peak force.

Executed crosshead rate: computed per specimen from the loading branch as
(displacement at peak force - displacement at start) / elapsed time; the
protocol was amended to 1 mm/min and executed at 3 mm/min (U1 ran at
approximately 1 mm/min), which is disclosed in the manuscript.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "validation" / "experimental_data"
OUT = ROOT / "validation" / "table8_results.json"
SPAN_MM = 100.0
AREA_MM2 = 450.0
FIT_FORCE_N = (150.0, 600.0)
SWEEP_SPAN_N = (100.0, 800.0)
PRIMARY_WIDTH_N = FIT_FORCE_N[1] - FIT_FORCE_N[0]  # 450 N
SLIDING_WIDTH_N = 100.0
N_BOOT = 20000
BOOT_SEED = 0

# specimen masses in grams (measured, validation/EXPERIMENTAL_VALIDATION.md)
MASS_G = {
    "U1": 77.9880, "U2": 78.0985, "U3": 78.0820, "U4": 77.8811,
    "O1": 78.3900, "O2": 78.0271, "O3": 78.1880, "O4": 78.2517,
}


def read_csv(path: Path) -> np.ndarray:
    rows = []
    text = path.read_bytes().decode("latin-1")
    for line in text.strip().splitlines()[2:]:
        parts = line.strip().replace('"', "").replace(",", ".").split(";")
        try:
            rows.append((float(parts[0]), float(parts[1]), 1000.0 * float(parts[2])))
        except (ValueError, IndexError):
            continue
    return np.asarray(rows, dtype=float)


def fit(path: Path, window: tuple[float, float] = FIT_FORCE_N) -> tuple[float, float, int]:
    """Loading-branch slope of stress vs crosshead strain inside ``window``."""
    data = read_csv(path)
    peak = int(np.argmax(data[:, 2]))
    displacement = data[:peak, 1]
    force = data[:peak, 2]
    mask = (force >= window[0]) & (force <= window[1])
    strain = displacement[mask] / SPAN_MM
    stress = force[mask] / AREA_MM2
    slope, intercept = np.polyfit(strain, stress, 1)
    predicted = slope * strain + intercept
    ss_res = float(np.sum((stress - predicted) ** 2))
    ss_tot = float(np.sum((stress - np.mean(stress)) ** 2))
    r2 = 1.0 - ss_res / ss_tot
    return float(slope), r2, int(mask.sum())


def specimen_record(path: Path) -> dict:
    """Per-specimen E*, fit quality, window size, peaks, executed rate."""
    data = read_csv(path)
    peak = int(np.argmax(data[:, 2]))
    modulus, r2, count = fit(path)
    t0, t1 = data[0, 0], data[peak, 0]
    d0, d1 = data[0, 1], data[peak, 1]
    rate = (d1 - d0) / (t1 - t0) * 60.0 if t1 > t0 else float("nan")
    return {
        "E_MPa": modulus,
        "r2": r2,
        "n_fit": count,
        "peak_force_N": float(data[peak, 2]),
        "peak_disp_mm": float(d1),
        "executed_rate_mm_min": rate,
    }


def window_families() -> list[tuple[str, tuple[float, float]]]:
    """Two explicit regression-window families spanning 100--800 N."""
    family = []
    lo = SWEEP_SPAN_N[0]
    while lo + PRIMARY_WIDTH_N <= SWEEP_SPAN_N[1] + 1e-9:
        family.append((f"{lo:.0f}-{lo + PRIMARY_WIDTH_N:.0f}", (lo, lo + PRIMARY_WIDTH_N)))
        lo += 50.0
    lo = SWEEP_SPAN_N[0]
    while lo + SLIDING_WIDTH_N <= SWEEP_SPAN_N[1] + 1e-9:
        family.append((f"{lo:.0f}-{lo + SLIDING_WIDTH_N:.0f}", (lo, lo + SLIDING_WIDTH_N)))
        lo += 50.0
    return family


def group_ratio(graded: np.ndarray, uniform: np.ndarray) -> tuple[float, float]:
    ratio = float(np.mean(graded) / np.mean(uniform))
    ratio_se = ratio * np.sqrt(
        (np.std(graded, ddof=1) / np.sqrt(len(graded)) / np.mean(graded)) ** 2
        + (np.std(uniform, ddof=1) / np.sqrt(len(uniform)) / np.mean(uniform)) ** 2
    )
    return ratio, float(ratio_se)


def main() -> None:
    tags = [f"{g}{i}" for g in "UO" for i in range(1, 5)]
    per: dict[str, dict] = {}
    for tag in tags:
        rec = specimen_record(DATA / f"{tag}.csv")
        rec["mass_g"] = MASS_G[tag]
        per[tag] = rec
        print(f"{tag}: E*={rec['E_MPa']:.6f} MPa, R2={rec['r2']:.8f}, "
              f"n={rec['n_fit']}, rate={rec['executed_rate_mm_min']:.2f} mm/min, "
              f"peak={rec['peak_force_N']:.0f} N")

    uniform = np.asarray([per[f"U{i}"]["E_MPa"] for i in range(1, 5)])
    graded = np.asarray([per[f"O{i}"]["E_MPa"] for i in range(1, 5)])
    ratio, ratio_se = group_ratio(graded, uniform)
    z_ci = (ratio - 1.96 * ratio_se, ratio + 1.96 * ratio_se)

    from scipy.stats import t as t_dist
    t_crit = float(t_dist.ppf(0.975, df=3))  # smaller group n minus one
    t_ci = (ratio - t_crit * ratio_se, ratio + t_crit * ratio_se)

    # U1 ran at approximately 1 mm/min while all other records ran at
    # approximately 3 mm/min.  This sensitivity does not repair that protocol
    # deviation; it shows whether the directional result depends on U1.
    uniform_without_u1 = uniform[1:]
    ratio_no_u1, ratio_no_u1_se = group_ratio(graded, uniform_without_u1)
    t_no_u1 = float(t_dist.ppf(0.975, df=2))
    t_no_u1_ci = (
        ratio_no_u1 - t_no_u1 * ratio_no_u1_se,
        ratio_no_u1 + t_no_u1 * ratio_no_u1_se,
    )

    rng = np.random.default_rng(BOOT_SEED)
    draws = np.asarray([
        np.mean(rng.choice(graded, 4)) / np.mean(rng.choice(uniform, 4))
        for _ in range(N_BOOT)
    ])
    boot_ci = tuple(float(x) for x in np.percentile(draws, [2.5, 97.5]))

    # mass-adjusted sensitivity: E*/(m/m_bar)^k for three documented k
    masses = np.asarray([per[tag]["mass_g"] for tag in tags])
    mods = np.asarray([per[tag]["E_MPa"] for tag in tags])
    m_bar = masses.mean()
    dev_m = np.concatenate([masses[:4] - masses[:4].mean(), masses[4:] - masses[4:].mean()])
    dev_e = np.concatenate([uniform - uniform.mean(), graded - graded.mean()])
    k_within = float((dev_m @ dev_e) / (dev_m @ dev_m) * m_bar / mods.mean())
    mass_adj = {}
    for label, k in (("k1_linear", 1.0), ("k2_bending", 2.0),
                     ("within_group", k_within)):
        adjusted = mods / (masses / m_bar) ** k
        r_adj, _ = group_ratio(adjusted[4:], adjusted[:4])
        mass_adj[label] = {"exponent": float(k), "R": float(r_adj)}
    ratio_adj = mass_adj["k2_bending"]["R"]  # manuscript's quoted sensitivity

    print(f"uniform={np.mean(uniform):.6f} +/- {np.std(uniform, ddof=1):.6f} MPa")
    print(f"graded={np.mean(graded):.6f} +/- {np.std(graded, ddof=1):.6f} MPa")
    print(f"R={ratio:.9f}; normal 95% CI=[{z_ci[0]:.9f}, {z_ci[1]:.9f}]")
    print(f"  t-based 95% CI (df=3, t={t_crit:.4f})=[{t_ci[0]:.9f}, {t_ci[1]:.9f}]")
    print(f"  leave-U1-out sensitivity, t-based 95% CI (df=2, t={t_no_u1:.4f})="
          f"[{t_no_u1_ci[0]:.9f}, {t_no_u1_ci[1]:.9f}]")
    print(f"  bootstrap 95% CI={boot_ci[0]:.9f}, {boot_ci[1]:.9f}")
    print(f"  mass-adjusted R: " + ", ".join(
        f"{lbl}={d['R']:.6f} (k={d['exponent']:.3f})" for lbl, d in mass_adj.items()))

    sweep = {}
    for name, window in window_families():
        ru = np.asarray([fit(DATA / f"U{i}.csv", window)[0] for i in range(1, 5)])
        ro = np.asarray([fit(DATA / f"O{i}.csv", window)[0] for i in range(1, 5)])
        r_w, _ = group_ratio(ro, ru)
        n_min = min(fit(DATA / f"{g}{i}.csv", window)[2] for g in "UO" for i in range(1, 5))
        sweep[name] = {"R": round(r_w, 6), "n_min": n_min}
    wide = {k: v for k, v in sweep.items() if float(k.split("-")[1]) - float(k.split("-")[0]) > 200}
    r_lo = min(v["R"] for v in wide.values())
    r_hi = max(v["R"] for v in wide.values())
    print(f"  window sweep 100-800 N (450 N-wide family): R in [{r_lo:.6f}, {r_hi:.6f}]")

    out = {
        "analysis": {
            "source": "validation/experimental_data/*.csv",
            "script": "validation/verify_experiment_stats.py",
            "loading_branch_only": True,
            "fit_force_window_N": list(FIT_FORCE_N),
            "reference_span_mm": SPAN_MM,
            "reference_area_mm2": AREA_MM2,
            "note": "Supersedes the stale one-specimen optical-tracking intermediate preserved as table8_results_stale_optical_intermediate.json and the orphaned testdata/results_table8.json (whose writing script is not preserved).",
        },
        "per_specimen": per,
        "groups": {
            "uniform": {"mean_E_MPa": float(np.mean(uniform)),
                        "sd_E_MPa": float(np.std(uniform, ddof=1)), "n": 4},
            "graded": {"mean_E_MPa": float(np.mean(graded)),
                       "sd_E_MPa": float(np.std(graded, ddof=1)), "n": 4},
            "ratio": {
                "R": ratio,
                "normal_95pct_CI": list(z_ci),
                "t_95pct_CI_df3": list(t_ci),
                "bootstrap_95pct_CI": list(boot_ci),
                "leave_U1_out_rate_mismatch_sensitivity": {
                    "R": ratio_no_u1,
                    "t_95pct_CI_df2": list(t_no_u1_ci),
                    "n_uniform": 3,
                    "n_graded": 4,
                    "note": "Post hoc sensitivity only; excluding U1 does not "
                            "remove the rate mismatch, single-build limitation, "
                            "or other experimental limitations.",
                },
                "mass_adjusted_R": ratio_adj,
                "mass_adjustment": {
                    "method": "E*/(m/m_bar)^k quoted for k=1, k=2 (primary, "
                              "bending-type lattice scaling), and the "
                              "within-group-fitted exponent",
                    "variants": mass_adj,
                },
                "window_sweep_100_800N": sweep,
                "window_sweep_R_range_450N_family": [r_lo, r_hi],
            },
        },
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
