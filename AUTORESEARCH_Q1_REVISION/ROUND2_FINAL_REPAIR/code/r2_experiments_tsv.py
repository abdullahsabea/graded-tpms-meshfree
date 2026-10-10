"""r2_experiments_tsv: build results/experiments_round2.tsv.

Contains (a) corrected-schema copies of the round-1 historical rows (the
two rows with 13 fields for 12 headers are repaired with a documented
mapping, marked schema_fix) and (b) one row per ROUND2 run (replay, arms,
audits). Historical VALUES are preserved verbatim; only the schema mapping
is corrected. The round-1 experiments.tsv file itself is never modified.

Idempotent rebuild from sources; append semantics for new arm rows are
achieved by reading the arm JSONs (source of truth).
"""
import csv
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vg2_common as v2  # noqa: E402

R2 = v2.R2
OUT = os.path.join(R2, "results", "experiments_round2.tsv")
HDR = ["id", "timestamp_iso", "hypothesis", "frozen_inputs_sha", "command",
       "environment", "primary_metric", "preregistered_threshold", "outcome",
       "runtime_s", "output_paths", "interpretation"]

R1_ENV = "Py3.11.9 torch2.5.1 docker simvia/code_aster:stable"
R2_ENV = ("Py3.11.9 torch2.5.1+cu121 scipy1.16.3 numpy2.3.5 "
          "docker simvia/code_aster@sha256:d8d19ea91989... (pinned)")


def rows_historical():
    """Round-1 rows, schema-corrected; values preserved."""
    return [
        ["EXP-01-PILOT", "2026-09-13",
         "Pilot: DEM Stage-2 scorer reproduces archived value; legacy cache "
         "hash path exact; fresh docker 64^3 solve",
         "code/pilot_exp01.py; e3_coord_search.json 5251b6f8; "
         "e3_fe_baseline.py 651e301f",
         "python AUTORESEARCH_Q1_REVISION/code/pilot_exp01.py", R1_ENV,
         "rel_diff of scorer vs archived soft C; new-solve success",
         "P1 rel_diff<1%; P2 |diff|<1e-9; P3 new solve with physical value",
         "PASS", "25", "results/pilot_exp01.json",
         "scorer validated to 6e-6 rel; uniform cache hit exact; new 64^3 "
         "solve 23.4s C1111=0.107442 [schema_fix: none needed]"],
        ["EXP-04-REPLAY", "2026-09-13",
         "Archived FE pool reconstructable from content-hash cache; "
         "DEM-vs-FE discordance quantifiable",
         "archived febase cache (195 solves); e3_fe_baseline.json 90ade00d; "
         "scorer as EXP-01",
         "python AUTORESEARCH_Q1_REVISION/code/replay_pool.py; "
         "code/regroup_exp04.py", R1_ENV,
         "reconstruction match; Spearman/Kendall; DEM-top1 discordance",
         "24/24 steps match; discordance reported (no pass/fail)",
         "PASS", "660", "results/pool_replay.json; results/pool_table.csv",
         "Pool=192 unique candidates; Spearman 0.664 Kendall 0.478; DEM "
         "best pool candidate +2.32% FE vs pool best +6.55%; DEM top-1 "
         "wrong in 21/24 scan groups [schema_fix: round-1 row had 13 "
         "fields; merged runtime/outputs columns; group stats were "
         "produced by the regroup patch, corrected in ROUND2]"],
        ["EXP-02-VGMM", "2026-09-13",
         "H1: DEM-ranked + per-move-FE-verified search beats band-"
         "restricted design (+1.58%) at <=30 FE calls",
         "04_preregistered_plan.md frozen; scorer EXP-01-validated; "
         "archived uniforms",
         "python AUTORESEARCH_Q1_REVISION/code/run_vgmm.py", R1_ENV,
         "G_confirm96_pct",
         "STRONG>=5.84 / PASS 1.58-5.84 / EQUIV 0.88-1.58 / FAIL<0.88",
         "PASS", "840", "results/vgmm_result.json; logs/exp02_vgmm_run.log",
         "G_confirm=+5.558% (64^3 +5.828%) at 26 FE calls (20 new); 6 "
         "accepts 18 rejects; zero negative acceptances; historical counts "
         "preserved verbatim (do not recompute new-solve status from the "
         "now-populated cache); the round-1 '20 new ... plus confirmation' "
         "phrasing double-counted nothing but omitted the available "
         "uniform96 from the 27-unique inclusive convention"],
        ["EXP-03-SEEDS", "2026-09-13",
         "DEM-only greedy path robustness to quadrature cloud seed "
         "(CONFOUNDED per PI finding 2: forced-move code, cross-algorithm "
         "comparison)",
         "04 plan (reduced scope); seeds 12/13",
         "python AUTORESEARCH_Q1_REVISION/code/seed_sensitivity.py", R1_ENV,
         "pick agreement rate; final-design change",
         "report (no threshold; robustness diagnostic)",
         "INCONCLUSIVE", "700", "results/seed_sensitivity.json",
         "pick agreement 8/24 both seeds; forced-move defect means "
         "endpoints are not ordinary greedy DEM optima; cross-seed "
         "inference WITHDRAWN in ROUND2; superseded by ROUND2 arms "
         "B-DEMONLY/B-VGMM and quadrature isolation"],
        ["EXP-03B-SEEDFE", "2026-09-13",
         "Exploratory: FE value of unverified seed-12/13 forced-move "
         "endpoint designs",
         "frozen allowance in 04 plan", "scalar fe_solve via vgmm_common",
         R1_ENV, "FE gain of unverified final designs (seed12 -6.50%; "
         "seed13 -5.37%)",
         "informational", "FAIL", "140", "results/seed_final_fe_check.json",
         "forced-move endpoints are FE-negative; valid observation but "
         "does NOT establish 'systematic across seeds' (PI finding 2) "
         "[schema_fix: round-1 row had 13 fields; extra field merged into "
         "primary_metric; outcome normalized to FAIL/informational]"],
        ["EXP-02B-GATE", "2026-09-13",
         "Preregistered branch label for EXP-02 (self-assigned thresholds; "
         "not external validation)",
         "frozen thresholds", "manual comparison", "vs frozen table",
         "G_confirm96_pct=+5.558%", "PASS (1.58<G<5.84)", "PASS", "0",
         "(none)",
         "label retained as historical; ROUND2 demotes these self-assigned "
         "thresholds to internal bookkeeping (PI further-qualification)"],
        ["EXP-00-ENV", "2026-09-13",
         "Environment reproduces archived DEM-side numbers",
         "paper_numbers.json 83978e64; e3_cond.pt 5749650a; "
         "e3_conditional.py d25c62d4",
         "python inline audit (state.md recipe)", R1_ENV,
         "C1111 audit at t=0.3 equals archived 0.11378", "exact match",
         "PASS", "60", "state.md",
         "conditional checkpoint loads; 0.11378 exact; system-torch "
         "workaround documented"],
        ["EXP-00-VERIFY", "2026-09-13",
         "Manuscript numerical claims match source-of-truth files",
         "manuscript.tex 4d846328; paper_numbers.json; "
         "e3_fe_baseline.json 90ade00d; audits",
         "manual cross-check in 01_baseline_editorial_audit.md section 8",
         "Crossref-free local check", "all spot-checked claims match SoT",
         "any mismatch = FAIL", "PASS", "30",
         "01_baseline_editorial_audit.md",
         "12 claim groups matched (grouped, not sentence-level; ROUND2 adds "
         "sentence-level changed-claim ledger)"],
    ]


def rows_round2():
    rows = []
    man = os.path.join(R2, "results", "MANIFEST_ROUND2.json")
    rows.append(["R2-MANIFEST", "2026-09-13",
                 "Source manifest of every artifact ROUND2 reads",
                 "34 source files", "python .../code/r2_manifest.py", R2_ENV,
                 "files hashed", "n/a", "PASS", "1",
                 "results/MANIFEST_ROUND2.json",
                 "docker digest pinned; all historical artifacts read-only"])
    pl = os.path.join(R2, "plans", "ROUND2_PLAN.md")
    rows.append(["R2-PLAN-FROST", "2026-09-13",
                 "Prospective local plan frozen before outcome runs",
                 "sha256 e56fdf7f882a45d39c57a921b2c1be6c8f3377dc55ee93ee"
                 "c5f15995947d9cb5",
                 "ledger entry PLAN-FROST-2A", R2_ENV,
                 "plan hash recorded with real UTC timestamp",
                 "any later edit invalidates", "PASS", "0",
                 "plans/ROUND2_PLAN.md; results/decisions_round2.log",
                 "local prospective plan, NOT external registration"])
    rp = os.path.join(R2, "results", "r2_pool_replay.json")
    if os.path.exists(rp):
        d = json.load(open(rp))["diag"]
        rows.append(["R2-REPLAY", "2026-09-13",
                     "Single-producer pool reconstruction + tie-aware stats "
                     "+ 195-vs-194 reconciliation + truncated comparator",
                     "archived febase; ROUND2_PLAN.md",
                     "python .../code/r2_replay.py", R2_ENV,
                     f"match {d['reconstruction_steps_match']}; spearman "
                     f"{d['spearman_dem_fe_scipy_tie_aware']:.4f}",
                     "24/24 match required", "PASS"
                     if d["reconstruction_steps_match"] == "24/24" and
                     d["missing_or_rejected_cache_keys"] == 0 else "FAIL",
                     f"{d['runtime_total_s']:.0f}",
                     "results/r2_pool_replay.json",
                     f"discordant groups {d['scan_groups_dem_top1_wrong']}"
                     f"/{d['scan_groups']} (id-only "
                     f"{d['of_which_different_id_only']}, material "
                     f"{d['of_which_material_ranking_loss']}); extras "
                     f"identified: "
                     f"{[e.get('identified_as') for e in d['extra_files_identified']]}"])
    corr = os.path.join(R2, "results", "r2_vgmm_historical_corrections.json")
    if os.path.exists(corr):
        c = json.load(open(corr))
        rows.append(["R2-VGMM-CORR", "2026-09-13",
                     "Corrected selected-proposal DEM scores for the "
                     "historical VG-MM log",
                     "vgmm_result.json + frozen scorer",
                     "python .../code/r2_vgmm_corrections.py", R2_ENV,
                     f"picks {c['picks_reproduced']}, actions "
                     f"{c['actions_reproduced']}",
                     "24/24 picks required", "PASS"
                     if c["picks_reproduced"].startswith("24/24") else
                     "FAIL", "0",
                     "results/r2_vgmm_historical_corrections.json",
                     f"{len(c['checkpoints_with_wrong_recorded_dem_score'])} "
                     f"checkpoints had wrong recorded dem_score; corrections "
                     f"preserved alongside historical values"])
    quad = os.path.join(R2, "results", "r2_quadrature_isolation.json")
    if os.path.exists(quad):
        q = json.load(open(quad))
        rows.append(["R2-QUADRATURE", "2026-09-13",
                     "Quadrature isolation on frozen common states "
                     "(clouds 11/12/13)",
                     "r2_pool_replay.json states",
                     "python .../code/r2_quadrature.py", R2_ENV,
                     "cloud-vs-cloud Spearman on 192 states",
                     "descriptive (no threshold)", "PASS", "0",
                     "results/r2_quadrature_isolation.json",
                     f"agreement {q['group_top1_agreement_counts']}; "
                     f"per-cloud denominators recomputed"])
    mech = os.path.join(R2, "results", "r2_mechanics_audit.json")
    if os.path.exists(mech):
        rows.append(["R2-MECH-AUDIT", "2026-09-13",
                     "Scorer partial-vs-total derivative audit (omitted "
                     "chain-rule term quantified)",
                     "e3_cond.pt; scorer math unchanged",
                     "python .../code/r2_mechanics_audit.py", R2_ENV,
                     "p50/p90/p99 of ||omitted||/||used||",
                     "descriptive", "PASS", "0",
                     "results/r2_mechanics_audit.json",
                     "scorer documented as approximate LOCAL score; "
                     "historical scorer not modified"])
    for f in sorted(glob.glob(os.path.join(R2, "results", "r2_arms",
                                           "arm_*.json"))):
        a = json.load(open(f))
        rows.append([f"R2-ARM-{a['arm'].upper()}", "2026-09-13",
                     f"Controlled arm {a['policy']} seed={a['seed']} per "
                     f"frozen ROUND2 plan",
                     "ROUND2_PLAN.md sha256 e56fdf7f...",
                     f"python .../code/r2_arms.py {a['policy']} "
                     f"{a['seed'] or ''}", R2_ENV,
                     f"G26={a['G26_pct']:+.3f}%",
                     "26-call budget; acceptance rule frozen",
                     "COMPLETED", f"{a['wall_s']:.0f}",
                     f"results/r2_arms/arm_{a['arm']}.json",
                     f"new solves {a['new_solves']}; accepts "
                     f"{a['accepted']}; rejects {a['rejected']}; "
                     f"harmful rejected {len(a['harmful_rejected'])}"])
    acc = os.path.join(R2, "results", "r2_accounting.json")
    if os.path.exists(acc):
        ac = json.load(open(acc))
        rows.append(["R2-ACCOUNTING", "2026-09-13",
                     "Common-budget endpoint analysis and frozen branch "
                     "assignment",
                     "ROUND2_PLAN.md delta=1.0pp",
                     "python .../code/r2_accounting.py", R2_ENV,
                     ac.get("branch_primary", "n/a"),
                     "B1/B2/B3/B4 frozen", ac.get("branch_primary", "n/a"),
                     "0", "results/r2_accounting.json",
                     ac.get("branch_interpretation", "")])
    return rows


def main():
    rows = rows_historical() + rows_round2()
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n",
                       quoting=csv.QUOTE_NONE, escapechar=None)
        w.writerow(HDR)
        for r in rows:
            assert len(r) == 12, f"row {r[0]} has {len(r)} fields"
            assert not any(("\t" in x) or ("\n" in x) for x in r), r[0]
            w.writerow(r)
    print(f"wrote {OUT} with {len(rows)} data rows")


if __name__ == "__main__":
    main()
