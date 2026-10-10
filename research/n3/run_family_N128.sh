#!/usr/bin/env bash
# N3 cross-family gate, finest resolution: 128^3 voxel FE per family.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
WIN="${PROJECT_ROOT:?set PROJECT_ROOT to the archive root}/research/n3"
IMG="simvia/code_aster:stable"

run_one () {
  fam=$1; t=$2; N=128
  python "$HERE/make_mesh.py" "$t" "$N" "$fam"
  cat > "$HERE/study_${fam}_N${N}.export" <<EOF
P actions make_etude
P memory_limit 48000
P time_limit 14400
P mpi_nbcpu 1
F comm /shared/homog.comm D 1
F mail /shared/${fam}_N${N}_t${t}.mail D 20
F mess /shared/out_${fam}_N${N}.mess R 6
EOF
  echo "=== $fam N=$N t=$t ==="
  docker run --rm -m 56g -v "$WIN:/shared" "$IMG" \
    bash -c "source /opt/activate.sh; run_aster /shared/study_${fam}_N${N}.export" \
    > "$HERE/log_${fam}_N${N}.txt" 2>&1
  grep -E "C1111_KUBC|DIAGNOSTIC" "$HERE/log_${fam}_N${N}.txt" | tail -2
}

cd "$HERE"
run_one gyroid    0.3
run_one primitive 0.3387
run_one diamond   0.236
echo "ALL_DONE_N128"
