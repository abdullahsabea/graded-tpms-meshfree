#!/usr/bin/env bash
# PBC vs KUBC on the calibrated 64^3 meshes of the three designs.
set -u
WIN="${PROJECT_ROOT:?set PROJECT_ROOT to the archive root}"
for tag in "$@"; do
  cat > study_pbc_${tag}.export <<EOX
P actions make_etude
P memory_limit 12000
P time_limit 7200
P mpi_nbcpu 1
F comm /shared/research/n3/homog_pbc.comm D 1
F mail /shared/research/n3/${tag}.mail D 20
F mess /shared/research/n3/out_pbc_${tag}.mess R 6
EOX
  docker run --rm -m 16g -v "$WIN:/shared" simvia/code_aster:stable \
    bash -c "source /opt/activate.sh; run_aster /shared/research/n3/study_pbc_${tag}.export" > log_pbc_${tag}.txt 2>&1
  echo "${tag}: $(grep -h '^C1111_KUBC\|^C1111_PBC' log_pbc_${tag}.txt | tr '\n' ' ') $(grep -h 'DIAGNOSTIC JOB' log_pbc_${tag}.txt)"
done
