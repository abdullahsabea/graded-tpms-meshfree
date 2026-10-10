#!/usr/bin/env bash
# N3 cross-family gate: code_aster KUBC ground truth for gyroid / primitive / diamond
# at matched continuum volume fraction (VF = 0.1933), three voxel resolutions.
# Usage:  bash run_family_studies.sh
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
WIN="${PROJECT_ROOT:?set PROJECT_ROOT to the archive root}/research/n3"
IMG="simvia/code_aster:stable"

run_one () {   # $1 family  $2 t  $3 N
  fam=$1; t=$2; N=$3
  mail="${fam}_N${N}_t${t}.mail"
  exp="study_${fam}_N${N}.export"
  mess="out_${fam}_N${N}.mess"
  if [ "$N" -ge 96 ]; then mem=16000; tl=7200; else mem=6000; tl=1800; fi
  cat > "$HERE/$exp" <<EOF
P actions make_etude
P memory_limit $mem
P time_limit $tl
P mpi_nbcpu 1
F comm /shared/homog.comm D 1
F mail /shared/$mail D 20
F mess /shared/$mess R 6
EOF
  echo "=== $fam N=$N t=$t ==="
  docker run --rm -v "$WIN:/shared" "$IMG" \
    bash -c "source /opt/activate.sh; run_aster /shared/$exp" > "$HERE/log_${fam}_N${N}.txt" 2>&1
  grep -E "C1111_KUBC|DIAGNOSTIC" "$HERE/$mess" "$HERE/log_${fam}_N${N}.txt" 2>/dev/null | tail -3
}

run_one gyroid    0.3    96
for N in 48 64 96; do run_one primitive 0.3387 $N; done
for N in 48 64 96; do run_one diamond   0.236  $N; done
echo "ALL_DONE"
