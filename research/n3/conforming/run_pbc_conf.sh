#!/usr/bin/env bash
# Periodic-BC solves on body-fitted meshes: ./run_pbc_conf.sh <meshstem> ...
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
REL="research/n3/conforming"
WIN="${PROJECT_ROOT:?set PROJECT_ROOT to the archive root}"
IMG="simvia/code_aster:stable"
cd "$HERE"
for N in "$@"; do
  cat > "study_pbc_${N}.export" <<EOF
P actions make_etude
P memory_limit ${PBC_MEM:-40000}
P time_limit 20000
P mpi_nbcpu 1
F comm /shared/${REL}/homog_conf_pbc.comm D 1
F mail /shared/${REL}/${N}.mail D 20
F mess /shared/${REL}/out_pbc_${N}.mess R 6
EOF
  # code_aster scratch on I:, not in Docker's virtual disk on C: (a disk
  # watchdog stops all code_aster containers when C: runs low)
  SCR="scratch_topo_aster/pbc_${N}"
  mkdir -p "/i/${SCR}"
  docker run --rm -m $(( ${PBC_MEM:-40000} / 1000 + 8 ))g -v "$WIN:/shared" -v "I:/${SCR}:/tmp" "$IMG" \
    bash -c "source /opt/activate.sh; run_aster /shared/${REL}/study_pbc_${N}.export" \
    > "log_pbc_${N}.txt" 2>&1
  rm -rf "/i/${SCR}"
  echo "${N}: $(grep -h '^C1111_PBC\|^SOLID_VOLUME' log_pbc_${N}.txt | tr '\n' ' ') $(grep -h 'DIAGNOSTIC JOB' log_pbc_${N}.txt)"
done
