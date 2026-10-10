"""r2_seed_endpoint_check: STANDALONE exact verification command for seed
endpoint FE values (PI finding 4: 'Seed endpoint FE checks lack a
standalone exact command').

Verifies, from RAW .mess evidence only (hardened parser; no solving):
  1. the round-1 seed-12/13 endpoint designs (results/seed_final_fe_check.json)
     -- key exists, solver OK, value matches, gain recomputed with explicit
     denominator;
  2. any ROUND2 B-DEMONLY endpoint designs recorded in results/r2_arms/.

Usage: python r2_seed_endpoint_check.py
Output: results/r2_seed_endpoint_check.json (fails if it exists; --keep to
replace the ROUND2 output only).
"""
import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vg2_common as v2  # noqa: E402

R2 = v2.R2
OUT = os.path.join(R2, "results", "r2_seed_endpoint_check.json")


def verify_key(key, N, theta, claimed, shift=None,
               folder_guess=(v2.FE_R1, v2.FE_R2, v2.FE_LEGACY)):
    if shift is None:
        shift = v2.bisect_shift_discrete(N, theta)
    for folder in folder_guess:
        v, tim = v2.cache_lookup(folder, key, N, theta, shift)
        if v is not None:
            return dict(source=folder, value=v,
                        matches_claim=bool(claimed is None
                                           or abs(v - claimed) < 1e-12))
    # fall back: raw parse without provenance rebuild (report reason)
    for folder in folder_guess:
        p = os.path.join(folder, f"oute_{key}.mess")
        if os.path.exists(p):
            val, ok = v2.parse_mess(p)
            return dict(source=folder, value=val, mess_ok=ok,
                        matches_claim=bool(val is not None and claimed
                                           is not None
                                           and abs(val - claimed) < 1e-12),
                        note="mail file missing; provenance rebuild "
                             "unavailable")
    return dict(source=None, value=None, matches_claim=False,
                note="no mess file found")


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

    out = {"uniform_64": v2.UNI_64, "uniform_96": v2.UNI_96}

    # 1) round-1 seed endpoints
    r1 = json.load(open(os.path.join(v2.WS, "results",
                                     "seed_final_fe_check.json")))
    r1v = {}
    for seed, d in r1.items():
        theta = json.load(open(os.path.join(
            v2.WS, "results", "seed_sensitivity.json")))["seeds"][seed][
                "final_theta"]
        ver = verify_key(d["key"], 64, theta, d["C1111"])
        r1v[seed] = dict(
            key=d["key"], claimed_value=d["C1111"],
            verified=ver,
            gain_vs_uniform64_pct=100 * (ver["value"] / v2.UNI_64 - 1)
            if ver["value"] else None,
            historical_gain_pct=d["gain_pct"],
            denominator="uniform64 C1111 = 0.10528125601 (archived)")
    out["round1_seed_endpoints"] = r1v

    # 2) ROUND2 demonly endpoints
    # 2) ROUND2 demonly endpoints (verifies both 64^3 and 96^3 endpoints)
    r2d = {}
    for f in sorted(glob.glob(os.path.join(R2, "results", "r2_arms",
                                           "arm_demonly*.json"))):
        a = json.load(open(f))
        theta = a["theta_final"]
        calls = {c["key"]: c for c in a["calls"]}
        ent = {}
        for c in a["calls"]:
            if "endpoint" in c.get("purpose", ""):
            if "endpoint" in c.get("purpose", "") or c.get("purpose") == "winner_64_read":
                ver = verify_key(c["key"], c["N"], c["theta"], c["value"])
                ent[c["purpose"]] = dict(
                    key=c["key"], N=c["N"], claimed_value=c["value"],
                    verified=ver,
                    gain_pct=(100 * (ver["value"] /
                                     (v2.UNI_64 if c["N"] == 64
                                      else v2.UNI_96) - 1))
                    if ver["value"] else None)
        r2d[a["arm"]] = ent
    out["round2_demonly_endpoints"] = r2d

    v2.write_json_new(OUT, out)
    v2.write_json_versioned(OUT, out)
    print(json.dumps(out, indent=2)[:4000])


if __name__ == "__main__":
    main()
