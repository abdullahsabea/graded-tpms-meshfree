"""Manuscript Figure 16 — physical adjudication (file fig10_experimental).

Curves from archived Instron CSVs; E* and R asserted against table8_results.json.
Layout: full-width loading records over a two-column elastic-window +
estimation-style E* panel. No manufactured distributions.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from scipy.stats import t as t_dist

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pubstyle import (  # noqa: E402
    C, INSTRON, TABLE8, apply_style, style_ax, save_figure, read_json,
)

OUT = Path(__file__).resolve().parent / "figures"
SPAN_MM, AREA, WINDOW = 100.0, 450.0, (150.0, 600.0)
TAGS = [f"{g}{i}" for g in "UO" for i in range(1, 5)]


def load_csv(path: Path):
    rows = []
    text = path.read_bytes().decode("latin-1")
    for line in text.strip().splitlines()[2:]:
        parts = line.strip().replace('"', "").replace(",", ".").split(";")
        try:
            rows.append((float(parts[0]), float(parts[1]),
                         1000.0 * float(parts[2])))
        except (ValueError, IndexError):
            continue
    return np.asarray(rows, dtype=float)


def add_specimen_key(ax, bounds, c_uniform, c_graded):
    """Add compact schematic U/O coupon keys without altering plotted data."""
    key = ax.inset_axes(bounds)
    key.set_xlim(0, 1)
    key.set_ylim(0, 1)
    key.set_axis_off()
    key.add_patch(FancyBboxPatch(
        (0.0, 0.0), 1.0, 1.0, boxstyle="round,pad=0.025,rounding_size=0.04",
        fc="white", ec="0.78", lw=0.45, alpha=0.96, zorder=0,
    ))
    key.text(0.50, 0.93, "specimen key (schematic)", ha="center", va="top",
             fontsize=5.6, color="0.30")

    def coupon(y, color, code, label, graded):
        # Dog-bone outline: solid grips and a narrowed, lattice-like gauge.
        x = np.array([0.06, 0.19, 0.27, 0.73, 0.81, 0.94])
        top = y + np.array([0.095, 0.095, 0.052, 0.052, 0.095, 0.095])
        bot = y - np.array([0.095, 0.095, 0.052, 0.052, 0.095, 0.095])
        key.fill(np.r_[x, x[::-1]], np.r_[top, bot[::-1]],
                 fc="white", ec=color, lw=0.85, zorder=2)
        xx = np.linspace(0.30, 0.70, 100)
        amp = 0.028 if not graded else 0.020 + 0.015 * (xx - 0.30) / 0.40
        for offset in (-0.025, 0.025):
            yy = y + offset + amp * np.sin(10 * np.pi * (xx - 0.30) / 0.40)
            key.plot(xx, yy, color=color, lw=0.65, alpha=0.90, zorder=3)
        key.text(0.015, y, code, ha="left", va="center", fontsize=6.6,
                 fontweight="bold", color=color)
        key.text(0.98, y, label, ha="right", va="center", fontsize=5.9,
                 color="0.18")

    coupon(0.62, c_uniform, "U", r"uniform $t=0.30$", graded=False)
    coupon(0.29, c_graded, "O", "constrained graded", graded=True)


def plot():
    apply_style()
    results = read_json(TABLE8)
    c_u, c_o = C["fem"], C["graded"]
    curves, fits = {}, {}
    for tag in TAGS:
        data = load_csv(INSTRON / f"{tag}.csv")
        peak = int(np.argmax(data[:, 2]))
        d, f = data[:peak, 1], data[:peak, 2]
        curves[tag] = (d, f)
        mask = (f >= WINDOW[0]) & (f <= WINDOW[1])
        strain = d[mask] / SPAN_MM
        stress = f[mask] / AREA
        slope, intercept = np.polyfit(strain, stress, 1)
        pred = slope * strain + intercept
        ss_res = np.sum((stress - pred) ** 2)
        n = int(mask.sum())
        dof = n - 2
        mse = ss_res / dof
        se = np.sqrt(mse / np.sum((strain - strain.mean()) ** 2))
        tcrit = t_dist.ppf(0.975, df=dof)
        ci = (slope - tcrit * se, slope + tcrit * se)
        slope_fd, intercept_fd = np.polyfit(d[mask], f[mask], 1)
        r2 = 1.0 - ss_res / np.sum((stress - stress.mean()) ** 2)
        fits[tag] = dict(E=slope, r2=r2, slope_fd=slope_fd,
                         intercept_fd=intercept_fd, ci=ci, mask=mask)
        e_json = results["per_specimen"][tag]["E_MPa"]
        assert abs(slope - e_json) < 1e-6, f"{tag}: {slope} vs {e_json}"

    r_auth = results["groups"]["ratio"]["R"]
    ci_auth = results["groups"]["ratio"]["t_95pct_CI_df3"]
    eu = np.array([fits[f"U{i}"]["E"] for i in range(1, 5)])
    eo = np.array([fits[f"O{i}"]["E"] for i in range(1, 5)])
    r2min = min(fits[t]["r2"] for t in TAGS)

    fig = plt.figure(figsize=(7.20, 5.15))
    gs = fig.add_gridspec(
        2, 2, height_ratios=[1.12, 1.00], width_ratios=[1.12, 1.00],
        hspace=0.42, wspace=0.32,
    )
    axa = fig.add_subplot(gs[0, :])
    axb = fig.add_subplot(gs[1, 0])
    axc = fig.add_subplot(gs[1, 1])
    for a in (axa, axb, axc):
        style_ax(a)

    axa.axhspan(WINDOW[0], WINDOW[1], color="#efefef", zorder=0, lw=0)
    axa.axhline(WINDOW[0], color="0.55", lw=0.55, ls=":", zorder=1)
    axa.axhline(WINDOW[1], color="0.55", lw=0.55, ls=":", zorder=1)
    for tag in TAGS:
        d, f = curves[tag]
        col = c_u if tag.startswith("U") else c_o
        axa.plot(d, f, color=col, lw=1.00, alpha=0.55, zorder=2)
        ff = fits[tag]
        mask = ff["mask"]
        dd = np.linspace(d[mask].min(), d[mask].max(), 40)
        axa.plot(dd, ff["slope_fd"] * dd + ff["intercept_fd"], "-",
                 color=col, lw=1.65, zorder=3)
    axa.set_xlabel("crosshead displacement [mm]")
    axa.set_ylabel("force [N]")
    axa.set_xlim(0, 4.55)
    axa.set_ylim(0, None)
    # The key occupies only the data-free upper-left region: its right edge
    # stays left of the first high-load curves, and its lower edge stays above
    # the initial loading traces.
    add_specimen_key(axa, [0.018, 0.75, 0.27, 0.20], c_u, c_o)
    axa.text(
        4.42, 0.5 * (WINDOW[0] + WINDOW[1]), "150–600 N",
        fontsize=7.5, color="0.35", va="center", ha="right",
    )

    for tag in TAGS:
        d, f = curves[tag]
        col = c_u if tag.startswith("U") else c_o
        mask = fits[tag]["mask"]
        axb.plot(d[mask], f[mask], "-", color=col, lw=1.05, alpha=0.55, zorder=2)
        ff = fits[tag]
        dd = np.linspace(d[mask].min(), d[mask].max(), 40)
        axb.plot(dd, ff["slope_fd"] * dd + ff["intercept_fd"], "-",
                 color=col, lw=1.9, zorder=3)
    axb.set_xlabel("crosshead displacement [mm]")
    axb.set_ylabel("force [N]")
    axb.set_ylim(WINDOW[0] - 18, WINDOW[1] + 18)
    axb.text(
        0.04, 0.96, rf"$R^2>{r2min:.4f}$ every specimen",
        transform=axb.transAxes, ha="left", va="top", fontsize=7.5,
        bbox=dict(boxstyle="round,pad=0.22", fc="white", ec="0.85",
                  lw=0.5, alpha=0.92),
    )

    xu = np.array([-0.18, -0.06, 0.06, 0.18])
    xo = 1.0 + xu
    axc.scatter(xu, eu, s=38, color=c_u, zorder=4, edgecolors="white",
                linewidths=0.55)
    axc.scatter(xo, eo, s=38, color=c_o, zorder=4, edgecolors="white",
                linewidths=0.55)
    for x, e, tag in zip(xu, eu, ["U1", "U2", "U3", "U4"]):
        lo, hi = fits[tag]["ci"]
        axc.plot([x, x], [lo, hi], color=c_u, lw=0.8, zorder=3)
    for x, e, tag in zip(xo, eo, ["O1", "O2", "O3", "O4"]):
        lo, hi = fits[tag]["ci"]
        axc.plot([x, x], [lo, hi], color=c_o, lw=0.8, zorder=3)
    axc.hlines(eu.mean(), -0.32, 0.32, color=c_u, lw=2.0, zorder=3)
    axc.hlines(eo.mean(), 0.68, 1.32, color=c_o, lw=2.0, zorder=3)
    axc.plot([-0.32, 0.32], [eu.mean(), eu.mean()], color=c_u, lw=0)
    mean_u = results["groups"]["uniform"]["mean_E_MPa"]
    mean_o = results["groups"]["graded"]["mean_E_MPa"]
    sd_u = results["groups"]["uniform"]["sd_E_MPa"]
    sd_o = results["groups"]["graded"]["sd_E_MPa"]
    axc.set_xticks([0.0, 1.0])
    axc.set_xticklabels([
        r"uniform $t{=}0.30$" + "\n" + rf"{mean_u:.1f}$\pm${sd_u:.1f} MPa",
        "constrained graded\n" + rf"{mean_o:.1f}$\pm${sd_o:.1f} MPa",
    ])

    ytop = max(eu.max(), eo.max()) + 6.5
    axc.plot([-0.0, -0.0, 1.0, 1.0], [ytop - 1.4, ytop, ytop, ytop - 1.4],
             color="0.25", lw=0.85, clip_on=False)
    axc.text(
        0.50, ytop + 0.55,
        rf"$R={r_auth:.3f}$  [{ci_auth[0]:.3f}, {ci_auth[1]:.3f}]",
        ha="center", va="bottom", fontsize=8.5,
    )
    axc.set_xlim(-0.55, 1.55)
    axc.set_ylabel(r"$E^*$ over 100 mm span [MPa]")
    lo = min(eu.min(), eo.min()) - 5
    axc.set_ylim(lo, ytop + 5.2)

    fig.subplots_adjust(left=0.09, right=0.99, top=0.93, bottom=0.16)
    axa.set_title("(a)  Monotonic loading, Instron 8852", loc="left",
                  fontsize=9.5, pad=6)
    axb.set_title("(b)  Elastic-window fits", loc="left", fontsize=9.5, pad=6)
    axc.set_title(r"(c)  Per-specimen $E^*$ and ratio $R$", loc="left",
                  fontsize=9.5, pad=6)

    assert abs(r_auth - 0.918) < 0.001
    assert abs(mean_u - 135.0) < 0.1
    assert abs(mean_o - 124.0) < 0.1
    save_figure(fig, OUT, "fig16_experimental")
    print("Fig 16 OK  R", r_auth, "CI", ci_auth, "Eu", mean_u, "Eo", mean_o,
          "r2min", r2min)
    return results, eu, eo


if __name__ == "__main__":
    plot()
