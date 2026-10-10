#!/usr/bin/env bash
# Periodicity-residual check: uniform and unconstrained designs, N48 meshes of Table 2
cd "$(dirname "$0")"
for S in gyroid_conf_N48_M96_rc gyroid_conf_N48_M96_graded_rc; do
  echo "[$(date +%T)] PBC + DEPL export $S"
  PBC_MEM=40000 ./run_pbc_conf_resid.sh "$S"
done
echo "[$(date +%T)] ALL DONE"
