#!/usr/bin/env bash
# Solve the body-fitted gyroid meshes with code_aster (one at a time).
#   ./run_conf.sh 24 48 72 96
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
REL="research/n3/conforming"
WIN="${PROJECT_ROOT:?set PROJECT_ROOT to the archive root}"
IMG="simvia/code_aster:stable"
cd "$HERE"
for N in "$@"; do
  cat > "study_conf_${N}.export" <<EOF
P actions make_etude
P memory_limit ${CONF_MEM:-40000}
P time_limit 20000
P mpi_nbcpu 1
F comm /shared/${REL}/homog_conf.comm D 1
F mail /shared/${REL}/gyroid_conf_${N}.mail D 20
F mess /shared/${REL}/out_conf_${N}.mess R 6
EOF
  # code_aster scratch on I:, not in Docker's virtual disk on C: (a disk
  # watchdog stops all code_aster containers when C: runs low)
  SCR="scratch_topo_aster/conf_${N}"
  mkdir -p "/i/${SCR}"
  docker run --rm -m $(( ${CONF_MEM:-40000} / 1000 + 8 ))g -v "$WIN:/shared" -v "I:/${SCR}:/tmp" "$IMG" \
    bash -c "source /opt/activate.sh; run_aster /shared/${REL}/study_conf_${N}.export" \
    > "log_conf_${N}.txt" 2>&1
  rm -rf "/i/${SCR}"
  echo "N=${N}: $(grep -h 'C1111_ENERGY\|SOLID_VOLUME' log_conf_${N}.txt | grep -v print | tr '\n' ' ') $(grep -h 'DIAGNOSTIC JOB' log_conf_${N}.txt)"
done
