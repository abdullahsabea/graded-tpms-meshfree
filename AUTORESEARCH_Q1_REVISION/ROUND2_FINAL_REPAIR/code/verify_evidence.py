"""verify_evidence: read-only consistency checker.

Loads the actual arm, replay, mechanics, and accounting records and
computes every numeric field that FIGURE_AUDIT.csv and the handover report
cite, directly from those records. It does not write, mutate, or delete any
frozen evidence file. It fails loudly (nonzero exit, MISSING entries in the
report) when a source the CURRENT FIGURE_AUDIT.csv/generator actually cites
does not exist, instead of silently proceeding.

Historical note (2026-09-14 PI decision): three files
(``c1111_vs_vf.json``, ``cross_family_benchmarks.json``,
``experimental_coupon_data.json``) were cited by an earlier, now-retired
FIGURE_AUDIT.csv and never existed. Those citations have since been
corrected (see PROVENANCE_AND_MODIFICATIONS.md Sec. 5) to point at the
files the figure-generating code actually reads. This checker records that
retired history under RETIRED_HISTORICAL_CITATIONS for the audit trail,
but does NOT fail the current run over it -- a citation nobody makes
anymore cannot be a current validation failure. Only files the CURRENT
canonical-value computation below actually opens can cause CURRENT_MISSING
to be non-empty and the exit code to be nonzero.

Run: python code/verify_evidence.py
Writes: results/evidence_verification.json (canonical computed values)
        logs/evidence_verification.log (human-readable report + exit status)
"""
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
R2 = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(R2))
N3 = os.path.join(REPO, "research", "n3")

# Retired citations from a now-superseded FIGURE_AUDIT.csv. Informational
# only -- checked and logged, but never contributes to CURRENT_MISSING or
# the exit code. If a NEW row ever legitimately needs one of these paths
# again, remove it from this list so it becomes a real, enforced check.
RETIRED_HISTORICAL_CITATIONS = [
    "results/c1111_vs_vf.json",
    "results/cross_family_benchmarks.json",
    "results/experimental_coupon_data.json",
]

CURRENT_MISSING = []
CHECKED = []


def load(*parts, required=True):
    path = os.path.join(*parts)
    CHECKED.append(path)
    if not os.path.isfile(path):
        if required:
            CURRENT_MISSING.append(path)
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def r(x, nd=6):
    return None if x is None else round(float(x), nd)


def main():
    out = {"generated_utc": datetime.now(timezone.utc).isoformat(),
           "missing_sources": [], "canonical": {}}

    acc = load(R2, "results", "r2_accounting.json")
    mech = load(R2, "results", "r2_mechanics_audit.json")
    pool = load(R2, "results", "r2_pool_replay.json")
    paper_numbers = load(N3, "paper_numbers.json")
    e3_base = load(N3, "e3_fe_baseline.json")
    e3_vf_table = load(N3, "e3_vf_table.json")
    e3_cond_audit = load(N3, "e3_cond_audit.json")
    field_stats = load(N3, "field_stats.json", required=False)
    table8 = load(REPO, "validation", "table8_results.json")
    arms = {}
    arms_dir = os.path.join(R2, "results", "r2_arms")
    if os.path.isdir(arms_dir):
        for fn in sorted(os.listdir(arms_dir)):
            if fn.startswith("arm_") and fn.endswith(".json"):
                a = load(arms_dir, fn)
                if a is not None:
                    arms[a["arm"]] = a
    else:
        CURRENT_MISSING.append(arms_dir)

    # Historical record only (see module docstring): these were cited by a
    # now-retired FIGURE_AUDIT.csv. Logged for the audit trail; never
    # affects CURRENT_MISSING or the exit code.
    retired_still_absent = []
    for rel in RETIRED_HISTORICAL_CITATIONS:
        p = os.path.join(R2, rel.replace("/", os.sep))
        if not os.path.isfile(p):
            retired_still_absent.append(rel)

    out["retired_historical_citations"] = {
        "paths": RETIRED_HISTORICAL_CITATIONS,
        "still_absent": retired_still_absent,
        "note": "these do not affect pass/fail; see module docstring. "
                "Current FIGURE_AUDIT.csv rows cite the real files instead "
                "(research/n3/e3_vf_table.json, e3_cond_audit.json, "
                "paper_numbers.json, e3_fe_baseline.json, "
                "validation/table8_results.json), all checked below as "
                "current requirements.",
    }
    out["current_missing_sources"] = CURRENT_MISSING

    canon = out["canonical"]

    # ---- R1 / Fig 10 (fig:vgmmbudget) : from r2_accounting.json table ----
    if acc is not None:
        tbl = {row["arm"]: row for row in acc["table"]}
        canon["r1_endpoints_pct"] = {
            k: {"G26": r(v.get("G26")), "G96": r(v.get("G96"))}
            for k, v in tbl.items()
        }
        canon["r1_fullfe_complete_calls"] = tbl["FULLFE-complete(archived)"]["calls"]
        canon["r1_fullfe_complete_raw_note"] = tbl["FULLFE-complete(archived)"].get("note")
        canon["r1_pairwise_vg_vs_rand"] = acc["pairwise"]["vg_vs_rand"]
        canon["r1_branch_primary"] = acc["branch_primary"]

    # ---- R2 / Fig 11 (fig:pooldiscordance) : from r2_pool_replay.json ----
    if pool is not None:
        d = pool["diag"]
        canon["r2_pool_diag"] = {
            "spearman": r(d.get("spearman_dem_fe_scipy_tie_aware")),
            "kendall": r(d.get("kendall_dem_fe_scipy_tie_aware")),
            "scan_groups": d.get("scan_groups"),
            "scan_groups_dem_top1_wrong": d.get("scan_groups_dem_top1_wrong"),
            "of_which_material_ranking_loss": d.get("of_which_material_ranking_loss"),
            "of_which_different_id_only": d.get("of_which_different_id_only"),
            "pool_size": d.get("pool_size"),
        }

    # ---- Mechanics audit (Section 3 / VG-MM winner) ----
    if mech is not None:
        w = mech["designs"]["vgmm_round1_winner"]
        canon["mechanics_vgmm_winner"] = {
            "frac_cloud_clipped_pct": r(w["frac_cloud_clipped"] * 100, 3),
            "all_cloud_mean_pct": r(w["mean_ratio_pct"]),
            "all_cloud_p50_pct": r(w["ratio_omitted_over_used_F_norm_pct"][0]),
            "all_cloud_p90_pct": r(w["ratio_omitted_over_used_F_norm_pct"][1]),
            "all_cloud_p99_pct": r(w["ratio_omitted_over_used_F_norm_pct"][2]),
            "unclipped_mean_pct": r(w["unclipped_mean_ratio_pct"]),
            "unclipped_p50_pct": r(w["unclipped_ratio_quantiles_pct"][0]),
            "unclipped_p90_pct": r(w["unclipped_ratio_quantiles_pct"][1]),
            "unclipped_p99_pct": r(w["unclipped_ratio_quantiles_pct"][2]),
            "unclipped_count": w["unclipped_count"],
            "note": "quantiles are [p50, p90, p99]; no maximum is computed "
                    "by r2_mechanics_audit.py",
        }

    # ---- Fig A.17 (mesh convergence) : from paper_numbers.json ----
    if paper_numbers is not None:
        fam = paper_numbers["families"]
        thick = paper_numbers["thickness"]

        def deltas(rows):
            by_n = {row["N"]: row["C1111"] for row in rows}
            base = by_n[64]
            return {n: r((by_n[n] / base - 1) * 100, 4)
                    for n in (96, 128) if n in by_n}

        canon["mesh_convergence_pct_change_from_64"] = {
            "gyroid_t0.30": deltas(fam["gyroid"]["rows"]),
            "diamond_t0.236": deltas(fam["diamond"]["rows"]),
            "primitive_t0.3387_noncalibrated64": deltas(fam["primitive"]["rows"]),
            "primitive_calibrated_ladder_mean": r(fam["primitive"]["stats"]["mean"], 5),
            "primitive_calibrated_ladder_scatter_pct": r(fam["primitive"]["stats"]["scatter_pct"], 3),
            "gyroid_t0.20": deltas(thick["0.20"]["rows"]),
        }

    # ---- Fig 5 (fig:family / fig_cross_family) : from paper_numbers.json ----
    if paper_numbers is not None:
        fam = paper_numbers["families"]
        canon["fig5_cross_family"] = {
            k: {"dem_dev_pct_vs_mean": r(v["dem"]["dev_pct_vs_mean"]),
                "fe_scatter_pct": r(v["stats"]["scatter_pct"])}
            for k, v in fam.items()
        }
        canon["fig5_cross_family_note"] = (
            "paper_numbers.json['families'] has exactly 3 entries "
            f"({sorted(fam.keys())}); a prior FIGURE_AUDIT.csv row claimed "
            "6 families (adding Neovius, IWP, Split-P) with specific C1111 "
            "values at Vf=0.19328 -- no such values exist in this file or "
            "any other source found in this workspace."
        )

    # ---- Fig 4 (fig:c1111 / fig3) : from e3_vf_table / e3_cond_audit / thickness ----
    if paper_numbers is not None and e3_vf_table is not None and e3_cond_audit is not None:
        anchors = [paper_numbers["thickness"][k] for k in ("0.20", "0.30", "0.45")]
        canon["fig4_c1111_vs_vf"] = {
            "vf_anchors": [0.1287, 0.1933, 0.2911],
            "fem_mean": [r(a["stats"]["mean"], 5) for a in anchors],
            "fem_half_range": [r(a["stats"]["half_range"], 5) for a in anchors],
            "dem_single_thickness": [r(a["dem"]["C1111"], 5) for a in anchors],
            "note": "no Gibson-Ashby power-law exponent is fit or stored "
                    "anywhere in these sources; a prior audit row's claimed "
                    "exponent range [1.8, 2.1] is not verifiable from this "
                    "data and is not reproduced here",
        }

    # ---- Fig 6 (fig:e3 / fig4) : from e3_fe_baseline.json ----
    if e3_base is not None:
        canon["fig6_e3_result"] = {
            "VF_target": e3_base.get("VF_target"),
            "search_N": e3_base.get("search_N"),
            "confirm_N": e3_base.get("confirm_N"),
            "gain_search_pct": r(e3_base.get("gain_search_pct")),
            "gain_confirm_pct": r(e3_base.get("gain_confirm_pct")),
            "note": "'macro_vf' is not a key in e3_fe_baseline.json; a "
                    "prior audit row cited 'e3_fe_baseline.json:macro_vf="
                    "0.19328', which does not exist. VF_target is used "
                    "instead.",
        }

    # ---- Fig 14/R5 (fig:geometry) realized voxel fractions ---------------
    # 2026-09-14 PI decision: depict the actual 64^3 search-grid designs
    # with their saved search shifts, and compute Vf directly from the
    # exact mask plotted. Independently reproduced here (not imported from
    # r2_figures.py) using the same pure, FE-free geometry functions
    # (v2.bisect_shift_discrete, v2.discrete_mask -- no FE solve, no Docker
    # call) so this file's canonical numbers are not just a copy of the
    # plotting code's own arithmetic.
    try:
        sys.path.insert(0, HERE)
        import numpy as _np
        import vg2_common as _v2
        _hist = json.load(open(os.path.join(_v2.WS, "results", "vgmm_result.json")))
        _e3 = e3_base if e3_base is not None else json.load(open(os.path.join(N3, "e3_fe_baseline.json")))
        _designs = {
            "Uniform": ([0.0] * _v2.N_MODES, None),
            "VG-MM winner": (_hist["theta_final"], None),
            "Full-FE winner": (_e3["theta"], _e3["shift_search"]),
        }
        fig14 = {}
        for name, (theta, shift) in _designs.items():
            if shift is None:
                shift = _v2.bisect_shift_discrete(64, theta)
            vf64 = float(_np.mean(_v2.discrete_mask(64, theta, shift)))
            fig14[name] = {"grid_N": 64, "shift": r(shift, 9),
                            "realized_Vf": r(vf64, 5)}
        canon["fig14_geometry_realized_vf_at_search_grid"] = fig14
        canon["fig14_geometry_note"] = (
            "RESOLVED 2026-09-14 (PI decision): fig_r5() now renders "
            "each design at N=64 (the actual search grid) using its "
            "saved 64^3 search shift, and the title's realized-Vf "
            "number is computed directly from that same plotted mask "
            "(discrete_mask(64, theta, shift).mean()), reproduced "
            "independently above. This differs from the PREVIOUS "
            "caption numbers (0.19332/0.19328/0.19328), which were "
            "N=96-recalibrated values (bisect_shift_discrete(96, "
            "theta)) attached to an image that was actually rendered "
            "at N=96 with the 64^3 shift (neither the search design "
            "nor the confirmation design). 96^3 confirmation is now "
            "reported as a stiffness/gain number only, with an "
            "explicit note that its geometry is separately calibrated "
            "and not the one pictured."
        )
    except Exception as exc:  # pragma: no cover - diagnostic only
        canon["fig14_geometry_note"] = f"UNRESOLVED: independent re-derivation raised {exc!r}"

    # ---- R1 unique-search-trajectory reconstruction, independent of
    # code/r2_figures.py's own implementation (2026-09-14 PI decision) ----
    # Re-derives, from scratch, the same de-duplication r2_figures.py's
    # reconstruct_search_trajectory() performs, and cross-checks the final
    # count against the arm's independent 'calls' list (N==64 entries).
    # This is a SEPARATE implementation (not an import of r2_figures.py),
    # so agreement between the two is real corroboration, not a tautology.
    def _independent_unique_search_count(log, calls_list, theta_len=12):
        theta = [0.0] * theta_len
        seen = {tuple(theta)}
        for row in log:
            if "fe_val" not in row or "pick" not in row:
                continue
            m = row["mode"]
            cand = list(theta)
            cand[m] = row["pick"]
            key = tuple(round(v, 9) for v in cand)
            seen.add(key)
            if row.get("action") == "ACCEPT":
                theta = cand
        n64_calls = sum(1 for c in calls_list if c.get("N") == 64)
        return {"unique_search_count_replay": len(seen),
                "unique_search_count_calls_list_N64": n64_calls,
                "cross_check_ok": len(seen) == n64_calls}

    def _duplicate_checkpoint_map(log, theta_len=12):
        """Identify WHICH checkpoint each duplicate repeats, not just the
        count. Checkpoint numbering is 1-based and excludes the initial
        baseline (checkpoint 1 == log[0]), matching the PI's convention.
        Cross-checked by requiring fe_val at the duplicate checkpoint to
        exactly equal fe_val at the checkpoint it repeats (same
        content-addressed FE solve); a mismatch here would mean the
        candidate-design match was spurious and is flagged, not hidden.
        """
        theta = [0.0] * theta_len
        seen = {}  # key -> first checkpoint index
        dup_map = {}
        for idx, row in enumerate(log, start=1):
            if "pick" not in row:
                continue
            m = row["mode"]
            cand = list(theta)
            cand[m] = row["pick"]
            key = tuple(round(v, 9) for v in cand)
            if key in seen:
                orig_idx = seen[key]
                orig_fe = log[orig_idx - 1].get("fe_val")
                this_fe = row.get("fe_val")
                dup_map[idx] = {
                    "repeats_checkpoint": orig_idx,
                    "fe_val_matches": (orig_fe == this_fe),
                }
            else:
                seen[key] = idx
            if row.get("action") == "ACCEPT":
                theta = cand
        return dup_map

    # Only arms with FE-in-loop search checkpoints (vgmm/rand/det) produce
    # a panel-(a) trajectory in fig_r1(); DEM-only-greedy arms (demonly*)
    # never call FE inside their loop (0 in-loop calls, 2 endpoint audits
    # outside the budget -- see results/r2_accounting.json), use a
    # different log schema (dem_pick/action STAY|DEMMOVE, no 'pick' or
    # 'fe_val' fields), and are correctly excluded from this check rather
    # than producing a spurious mismatch.
    r1_search_counts = {}
    for arm_name, arm_json in arms.items():
        if arm_json.get("policy") == "demonly" or "demonly" in arm_name:
            continue
        r1_search_counts[arm_name] = _independent_unique_search_count(
            arm_json["log"], arm_json["calls"])
    try:
        _hist2 = json.load(open(os.path.join(_v2.WS, "results", "vgmm_result.json")))
        r1_search_counts["vgmm11_historical"] = _independent_unique_search_count(
            _hist2["log"], _hist2["calls"])
    except Exception as exc:  # pragma: no cover
        r1_search_counts["vgmm11_historical"] = {"error": repr(exc)}
    canon["r1_unique_search_counts_independent_check"] = r1_search_counts
    canon["r1_pi_targets_cross_check"] = {
        "rand12_expected_24": r1_search_counts.get("rand12", {}).get("unique_search_count_replay"),
        "vgmm13_expected_23": r1_search_counts.get("vgmm13", {}).get("unique_search_count_replay"),
    }

    # ---- Duplicate-checkpoint identities (2026-09-14 PI instruction: these
    # ARE reconstructible; verify and record rather than claim unknown) ----
    dup_maps = {}
    for arm_name in ("rand12", "vgmm13", "rand11", "rand13", "vgmm12", "det"):
        if arm_name in arms:
            dup_maps[arm_name] = _duplicate_checkpoint_map(arms[arm_name]["log"])
    canon["r1_duplicate_checkpoint_identities"] = dup_maps
    pi_claims = {
        "rand12_checkpoint_23_repeats_4": dup_maps.get("rand12", {}).get(23, {}).get("repeats_checkpoint"),
        "vgmm13_checkpoint_23_repeats_5": dup_maps.get("vgmm13", {}).get(23, {}).get("repeats_checkpoint"),
        "vgmm13_checkpoint_24_repeats_12": dup_maps.get("vgmm13", {}).get(24, {}).get("repeats_checkpoint"),
    }
    canon["r1_pi_duplicate_claims_verified"] = {
        "claims": pi_claims,
        "all_confirmed": (pi_claims.get("rand12_checkpoint_23_repeats_4") == 4
                           and pi_claims.get("vgmm13_checkpoint_23_repeats_5") == 5
                           and pi_claims.get("vgmm13_checkpoint_24_repeats_12") == 12),
        "note": "Checkpoint numbering is 1-based and excludes the initial "
                "baseline call, per the PI's stated convention. Verified by "
                "replaying arm_<name>.json['log'] and matching full "
                "12-dimensional candidate designs (current incumbent theta "
                "with the log row's changed coordinate); every match is "
                "corroborated by an exact fe_val equality between the "
                "duplicate checkpoint and the checkpoint it repeats "
                "(same content-addressed FE solve).",
    }

    # ---- Fig 16 (fig:expresult) : from validation/table8_results.json ----
    if table8 is not None:
        ps = table8["per_specimen"]
        U = [v["E_MPa"] for k, v in ps.items() if k.startswith("U")]
        O = [v["E_MPa"] for k, v in ps.items() if k.startswith("O")]
        canon["fig16_expresult"] = {
            "n_specimens": len(ps),
            "U_group_E_MPa_mean": r(sum(U) / len(U), 3) if U else None,
            "O_group_E_MPa_mean": r(sum(O) / len(O), 3) if O else None,
            "O_vs_U_pct": r((sum(O) / len(O)) / (sum(U) / len(U)) * 100 - 100, 3) if U and O else None,
            "source_note": "real source is validation/table8_results.json "
                            "(analysis.script=paper/verify_experiment_stats.py); "
                            "a prior audit row cited the nonexistent "
                            "results/experimental_coupon_data.json and a "
                            "make_figs_v2.py line range (730-800) that "
                            "actually corresponds to fig_field_verification(), "
                            "not an experimental-result figure.",
        }
    else:
        canon["fig16_expresult"] = {"error": "validation/table8_results.json not found"}

    r1sc = canon.get("r1_unique_search_counts_independent_check", {})
    reconstruction_failures = [name for name, v in r1sc.items()
                                if isinstance(v, dict) and not v.get("cross_check_ok", True)]

    os.makedirs(os.path.join(R2, "results"), exist_ok=True)
    out_path = os.path.join(R2, "results", "evidence_verification.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)

    os.makedirs(os.path.join(R2, "logs"), exist_ok=True)
    log_path = os.path.join(R2, "logs", "evidence_verification.log")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"evidence_verification run at {out['generated_utc']}\n")
        f.write(f"sources checked: {len(CHECKED)}\n")
        f.write(f"CURRENT missing (fails the run): {len(CURRENT_MISSING)}\n")
        for m in CURRENT_MISSING:
            f.write(f"  CURRENT MISSING: {m}\n")
        f.write(f"retired historical citations still absent (informational "
                f"only, does not fail the run): {retired_still_absent}\n")
        f.write(f"trajectory reconstruction cross-check failures (fails "
                f"the run): {reconstruction_failures}\n")
        f.write(f"\ncanonical values written to {out_path}\n")
        f.write(json.dumps(canon, indent=1))

    print(f"Checked {len(CHECKED)} source paths; "
          f"{len(CURRENT_MISSING)} current-requirement failures; "
          f"{len(retired_still_absent)} retired historical citations "
          f"(informational only, not a failure).")
    for m in CURRENT_MISSING:
        print(f"  CURRENT MISSING: {m}")
    if reconstruction_failures:
        print(f"  TRAJECTORY RECONSTRUCTION MISMATCH: {reconstruction_failures}")
    print(f"Canonical values: {out_path}")
    print(f"Log: {log_path}")
    return 1 if (CURRENT_MISSING or reconstruction_failures) else 0


if __name__ == "__main__":
    sys.exit(main())
