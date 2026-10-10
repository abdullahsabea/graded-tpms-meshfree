#!/usr/bin/env bash
# WP-A2: uniform PBC at nu=0.33 (Mele 2025 match), after the N72 chain finishes
cd "$(dirname "$0")"
while ps -ef | grep -q "[r]un_wpa1_N72.sh"; do sleep 120; done
echo "[$(date +%T)] PBC nu=0.33 uniform N48"
PBC_MEM=40000 ./run_pbc_conf_nu033.sh gyroid_conf_N48_M96_rc
echo "[$(date +%T)] done"
