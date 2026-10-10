#!/usr/bin/env bash
# WP-A1: body-fitted PBC at N=72 (M=96, refined caps) for the 5 designs, sequential, in-core.
set -u
cd "$(dirname "$0")"
for D in uniform printable vgmm fullfe graded; do
  STEM="gyroid_conf_N72_M96$([ $D = uniform ] || echo _$D)_rc"
  if [ ! -f "$STEM.mail" ]; then
    echo "[$(date +%T)] mesh $D"; python make_conforming_mesh.py 72 96 $D refine_caps > "log_mesh_${STEM}.txt" 2>&1 || { echo "MESH FAIL $D"; tail -5 "log_mesh_${STEM}.txt"; continue; }
  fi
  echo "[$(date +%T)] PBC $STEM"; PBC_MEM=70000 ./run_pbc_conf.sh "$STEM"
done
echo "[$(date +%T)] ALL DONE"
