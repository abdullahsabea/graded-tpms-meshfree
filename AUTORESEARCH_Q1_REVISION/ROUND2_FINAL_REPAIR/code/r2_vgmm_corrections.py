"""r2_vgmm_corrections: re-derive the historical VG-MM run's DEM-side
bookkeeping WITHOUT rerunning FE, fixing PI finding 4 (selected-candidate
scores).

The round-1 driver recorded dem_score = top-ranked score even when the
SELECTED candidate was a different (non-incumbent) trial. This script
replays the frozen scorer over the historical decision walk (acceptance
decisions taken from the recorded FE values) and records, per checkpoint:
top score+coeff, incumbent coeff, selected (non-incumbent) candidate and
its TRUE score. It also verifies that the replayed walk reproduces the
historical picks/acceptance 24/24 (determinism check of the frozen scorer).

No new FE solves. Output: results/r2_vgmm_historical_corrections.json.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vg2_common as v2  # noqa: E402

R2 = v2.R2
OUT = os.path.join(R2, "results", "r2_vgmm_historical_corrections.json")


def main():
    hist = json.load(open(os.path.join(v2.WS, "results",
                                       "vgmm_result.json")))
    UNI64 = hist["uniform_64"]
    score = v2.make_scorer(cloud_seed=11)
    theta = [0.0] * v2.N_MODES
    best_FE = hist["calls"][0]["value"]

    rows = []
    picks_ok = actions_ok = 0
    corrections = []
    for r in hist["log"]:
        if r.get("action") == "no_move_all_equal_incumbent":
            rows.append(dict(sweep=r["sweep"], mode=r["mode"],
                             action="no_move"))
            continue
        s, m = r["sweep"], r["mode"]
        trials = []
        for cand in v2.GRID:
            tr = list(theta)
            tr[m] = float(cand)
            sh = v2.bisect_shift_discrete(64, tr)
            trials.append((score(tr, sh), float(cand)))
        trials.sort(key=lambda p: -p[0])
        top_sc, top_val = trials[0]
        sel_sc, sel_val = next(
            ((sc, val) for sc, val in trials if val != theta[m]), (None, None))
        row = dict(sweep=s, mode=m,
                   incumbent_coeff=float(theta[m]),
                   top_dem_score=top_sc, top_coeff=top_val,
                   selected_coeff=sel_val, selected_dem_score=sel_sc,
                   historical_dem_score=r["dem_score"],
                   historical_pick=r["pick"])
        if sel_val is not None and abs(sel_val - r["pick"]) < 1e-12:
            picks_ok += 1
        else:
            row["pick_mismatch"] = True
        acc = "ACCEPT" if r["fe_val"] > best_FE else "REJECT"
        if acc == r["action"]:
            actions_ok += 1
        else:
            row["action_mismatch"] = True
        if (r["dem_score"] is not None and sel_sc is not None
                and abs(r["dem_score"] - sel_sc) > 1e-9):
            corrections.append(dict(
                checkpoint=f"s{s}_m{m}",
                historical_recorded_dem_score=r["dem_score"],
                corrected_selected_dem_score=sel_sc,
                overall_top_dem_score=top_sc,
                incumbent_coeff=float(theta[m])))
        if acc == "ACCEPT":
            theta[m] = sel_val
            best_FE = r["fe_val"]
        rows.append(row)

    out = dict(
        purpose="PI finding 4: historical dem_score field recorded the "
                "overall top score, not the score of the actually selected "
                "non-incumbent proposal; corrections below preserve the "
                "historical values and add the corrected ones",
        picks_reproduced=f"{picks_ok}/{sum(1 for r in hist['log'] if 'pick' in r)}",
        actions_reproduced=f"{actions_ok}/{len(hist['log'])}",
        checkpoints_with_wrong_recorded_dem_score=corrections,
        checkpoint_rows=rows,
        note="no FE calls; frozen scorer replay only",
    )
    v2.write_json_new(OUT, out)
    print(out["picks_reproduced"], out["actions_reproduced"])
    for c in corrections:
        print(c)


if __name__ == "__main__":
    main()
