#!/usr/bin/env bash
# Periodicity-residual check, remaining three designs at N48 (final review round 2)
cd "$(dirname "$0")"
for S in gyroid_conf_N48_M96_printable_rc gyroid_conf_N48_M96_vgmm_rc gyroid_conf_N48_M96_fullfe_rc; do
  echo "[$(date +%T)] PBC + DEPL export $S"
  PBC_MEM=40000 ./run_pbc_conf_resid.sh "$S"
  python periodicity_residual.py "resid_${S}.med" 1e-3 > "resid_${S}_report.txt" 2>&1 && rm -f "resid_${S}.med"
done
echo "[$(date +%T)] ALL DONE"
