#!/usr/bin/env bash
# Periodicity-residual check at N72 for all five designs (final review round 3).
# Same solve as run_wpa1_N72.sh (homog_conf_pbc_resid.comm differs only by the DEPL export).
cd "$(dirname "$0")"
for D in uniform printable vgmm fullfe graded; do
  S="gyroid_conf_N72_M96$([ $D = uniform ] || echo _$D)_rc"
  echo "[$(date +%T)] PBC + DEPL export $S"
  PBC_MEM=70000 ./run_pbc_conf_resid.sh "$S"
  python periodicity_residual.py "resid_${S}.med" 1e-3 > "resid_${S}_report.txt" 2>&1 && rm -f "resid_${S}.med"
  echo "[$(date +%T)] residual done $S: $(tail -3 resid_${S}_report.txt | tr '\n' ' ')"
done
echo "[$(date +%T)] ALL DONE"
