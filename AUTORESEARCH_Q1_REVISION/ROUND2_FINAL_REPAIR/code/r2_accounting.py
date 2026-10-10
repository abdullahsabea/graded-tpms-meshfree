"""r2_accounting: common-budget endpoint analysis with the FROZEN branch
rules of ROUND2_PLAN.md Section 4. Mechanical: no manual labels.

Primary endpoint G26 per arm; families:
  VG   = historical B-VGMM(11) + new B-VGMM(12,13)
  RAND = B-RAND(11,12,13)
  DET  = B-DET
  FULLFE26 = truncated archived search (no seeds)
Branch rules (frozen):
  B1  min(VG) >= max(RAND) + delta  AND  min(VG) >= DET + delta
  B2  all cross-family differences within delta
  B3  max(RAND or DET) >= min(VG) + delta
  B4  any family incomplete
delta = 1.0 pp. Mixed outcomes reported pairwise.
"""
import argparse
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vg2_common as v2  # noqa: E402

R2 = v2.R2
OUT = os.path.join(R2, "results", "r2_accounting.json")
DELTA = 1.0

INTERP = {
    "B1": "DEM ranking added value beyond FE acceptance on this problem "
          "(frozen criterion met).",
    "B2": "FE acceptance, not DEM ranking, drives the observed gains at "
          "this budget; differences within the predeclared practical "
          "margin.",
    "B3": "A cheaper rule matched or beat the learned ranking beyond the "
          "predeclared margin; DEM guidance not useful here.",
    "B4": "INCONCLUSIVE: budget exhaustion or harness failure.",
}


def load_family():
    vg = {}
    hist = json.load(open(os.path.join(v2.WS, "results",
                                       "vgmm_result.json")))
    vg["11"] = dict(G26=100 * (hist["C_winner_search64"] / v2.UNI_64 - 1),
                    G96=hist["G_confirm96_pct"], historical=True,
                    calls=hist["fe_calls_total"],
                    new=hist["fe_calls_new_solves"],
                    accepts=hist["accept_events"],
                    rejects=hist["reject_events"],
                    theta=hist["theta_final"])
    rand, det, demonly = {}, {}, {}
    for f in sorted(glob.glob(os.path.join(R2, "results", "r2_arms",
                                           "arm_*.json"))):
        a = json.load(open(f))
        rec = dict(G26=a["G26_pct"], G96=a["G_confirm96_pct"],
                   historical=False, calls=a["calls_in_budget"],
                   new=a["new_solves"], accepts=a["accepted"],
                   rejects=a["rejected"],
                   harmful_rejected=a["harmful_rejected"],
                   theta=a["theta_final"], wall_s=a["wall_s"],
                   timing_s=a["timing_s"], arm=a["arm"])
        if a["policy"] == "vgmm":
            vg[str(a["seed"])] = rec
        elif a["policy"] == "rand":
            rand[str(a["seed"])] = rec
        elif a["policy"] == "det":
            det["det"] = rec
        elif a["policy"] == "demonly":
            demonly[str(a["seed"])] = rec
    return vg, rand, det, demonly


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()
    if os.path.exists(OUT):
        if not args.keep:
            raise SystemExit(f"refusing to overwrite existing {OUT}")
        os.remove(OUT)
    if os.path.exists(OUT) and not args.keep:
        raise SystemExit(f"refusing to overwrite existing {OUT} without --keep")
    vg, rand, det, demonly = load_family()
    rep = json.load(open(os.path.join(R2, "results", "r2_pool_replay.json")))
    ff = rep["fullfe_truncated"]

    complete = (len(vg) == 3 and len(rand) == 3 and len(det) == 1)
    gvg = [r["G26"] for r in vg.values()]
    grand = [r["G26"] for r in rand.values()]
    gdet = [r["Gdet"] if "Gdet" in r else r["G26"] for r in det.values()]

    pairwise = {}
    if complete:
        # All 9 pairwise cross-family differences (VG-MM minus RANDOM)
        cross_diffs = {}
        for vk, vr in sorted(vg.items()):
            for rk, rr in sorted(rand.items()):
                cross_diffs[f"vg{vk}_minus_rand{rk}"] = vr["G26"] - rr["G26"]
        all_diff_vals = list(cross_diffs.values())

        pairwise["vg_vs_rand"] = dict(
            all_pairwise_diffs_pp=cross_diffs,
            min_diff_pp=min(all_diff_vals),
            max_diff_pp=max(all_diff_vals),
            mean_diff_pp=float(np.mean(all_diff_vals)),
            min_vg=min(gvg), max_rand=max(grand),
            diff_pp=min(gvg) - max(grand),
            beyond_delta=bool(min(gvg) - max(grand) >= DELTA))
            worst_case_margin_pp=min(gvg) - max(grand),
            best_case_margin_pp=max(gvg) - min(grand),
            all_exceed_delta=bool(min(all_diff_vals) >= DELTA),
            all_within_delta=bool(max(abs(x) for x in all_diff_vals) < DELTA))

        pairwise["vg_vs_det"] = dict(
            min_vg=min(gvg), det=gdet[0],
            diff_pp=min(gvg) - gdet[0],
            beyond_delta=bool(min(gvg) - gdet[0] >= DELTA))
        b1 = pairwise["vg_vs_rand"]["beyond_delta"] and \
            pairwise["vg_vs_det"]["beyond_delta"]

        # Branch evaluation:
        # B1: VG-MM beats both controls by at least delta across all seeds
        b1 = pairwise["vg_vs_rand"]["all_exceed_delta"] and pairwise["vg_vs_det"]["beyond_delta"]
        # B3: Control beats VG-MM by at least delta
        b3 = (max(grand) - min(gvg) >= DELTA) or (gdet[0] - min(gvg) >= DELTA)
        max_cross = max(abs(min(gvg) - max(grand)),
                        abs(min(gvg) - gdet[0]))
        b2 = max_cross < DELTA
        # B2: All cross-family differences within delta (equivalence within margin)
        b2 = pairwise["vg_vs_rand"]["all_within_delta"] and (abs(min(gvg) - gdet[0]) < DELTA)

        if b1:
            branch = "B1"
        elif b3:
            branch = "B3"
        elif b2:
            branch = "B2"
        else:
            branch = "MIXED"
    else:
        branch = "B4"
    interp = INTERP.get(branch, "Mixed outcome: report each pairwise "
                                "comparison by its own branch.")
    interp = INTERP.get(branch, "Mixed outcome: report each pairwise comparison by its own branch; no causal equivalence or general superiority claim.")

    # full accounting table (shared + inclusive conventions)
    table = []
    for name, fam in (("VG-MM", vg), ("RAND", rand), ("DET", det)):
        for k, r in sorted(fam.items()):
            table.append(dict(arm=f"{name}({k})", G26=r["G26"],
                              G96=r["G96"], calls=r["calls"],
                              new_solves=r["new"],
                              accepts=r.get("accepts"),
                              rejects=r.get("rejects"),
                              harmful_rejected=len(r.get(
                                  "harmful_rejected", []))
                              if r.get("harmful_rejected") is not None
                              else None,
                              wall_s=r.get("wall_s")))
    for k, r in sorted(demonly.items()):
        table.append(dict(arm=f"DEMONLY({k})", G26=r["G26"], G96=r["G96"],
                          calls=0, new_solves=r["new"],
                          note="no FE in loop; endpoint audits only"))
    table.append(dict(
        arm="FULLFE-truncated", G26=ff["best_gain_at_26_unique_pct"],
        G96=None, calls=26,
        note=ff["batch_note"] + "; batch-complete frontier "
             f"{ff['batch_complete_frontier']['best_gain_pct']:.3f}% at "
             f"{ff['batch_complete_frontier']['unique_designs']} unique"))
    table.append(dict(arm="FULLFE-complete(archived)",
                      G26=100 * (0.1121774685 / v2.UNI_64 - 1),
                      G96=100 * (0.11242472831 / v2.UNI_96 - 1),
                      calls=194, new_solves=0,
                      note="194 unique problems (192 search incl uniform64 "
                           "+ uniform96 + winner96); 244 raw queries; "
                           "wall time NOT recoverable -> unavailable"))

    out = dict(
        delta_pp=DELTA,
        primary_endpoint="G26 = 100*(C_final_64/0.10528125601 - 1) at "
                         "exactly 26 counted calls per arm",
        families_complete=dict(vgmm=len(vg) == 3, rand=len(rand) == 3,
                               det=len(det) == 1,
                               demonly=len(demonly) == 3),
        branch_primary=branch,
        branch_interpretation=interp,
        pairwise=pairwise,
        family_values=dict(vgmm={k: r["G26"] for k, r in vg.items()},
                           rand={k: r["G26"] for k, r in rand.items()},
                           det={k: r["G26"] for k, r in det.items()},
                           demonly={k: r["G26"]
                                    for k, r in demonly.items()}),
        variability=dict(
            vgmm_range_pp=(max(gvg) - min(gvg)) if len(gvg) > 1 else None,
            rand_range_pp=(max(grand) - min(grand)) if len(grand) > 1
            else None),
        accounting_conventions=dict(
            shared_setup="every arm queries the SAME uniform64 baseline as "
                         "call 1 (cached value; counted identically)",
            inclusive="inclusive unique-problem count adds the archived "
                      "uniform96 (available to all arms externally): "
                      "VG-MM(11) historical = 27 unique; full-FE = 194",
            demonly="0 in-loop FE; 2 endpoint-audit solves outside the "
                    "26-call budget (declared in plan)"),
        table=table,
        scope_limits="monotonicity only for same-grid accepted FE "
                     "objective; no universal-safety claim; gain and cost "
                     "reported separately; lower-cost/lower-gain arms are "
                     "NOT called dominated",
    )
    v2.write_json_new(OUT, out)
    v2.write_json_versioned(OUT, out)
    print("wrote versioned", OUT)
    print(json.dumps({k: out[k] for k in
                      ("branch_primary", "branch_interpretation",
                       "family_values", "variability")}, indent=2))
    for t in table:
        print(t)


if __name__ == "__main__":
    main()
