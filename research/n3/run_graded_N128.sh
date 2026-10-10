#!/usr/bin/env bash
# Iso-resolution check of the optimization case study: the optimized graded and
# manufacturability-constrained cells re-analyzed at 128^3, the same resolution
# as the uniform t=0.3 baseline (run_family_N128.sh).
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
WIN="${PROJECT_ROOT:?set PROJECT_ROOT to the archive root}/research/n3"
IMG="simvia/code_aster:stable"
cd "$HERE"

python make_mesh_graded.py 128
python make_mesh_printable.py 128

run_one () {   # $1 tag  ->  gyroid_<tag>_N128.mail
  tag=$1
  cat > "$HERE/study_${tag}_N128.export" <<EOF
P actions make_etude
P memory_limit 48000
P time_limit 14400
P mpi_nbcpu 1
F comm /shared/homog.comm D 1
F mail /shared/gyroid_${tag}_N128.mail D 20
F mess /shared/out_${tag}_N128.mess R 6
EOF
  echo "=== $tag N=128 ==="
  docker run --rm -m 56g -v "$WIN:/shared" "$IMG" \
    bash -c "source /opt/activate.sh; run_aster /shared/study_${tag}_N128.export" \
    > "$HERE/log_${tag}_N128.txt" 2>&1
  grep -E "C1111_KUBC|DIAGNOSTIC" "$HERE/log_${tag}_N128.txt" | tail -2
}

run_one graded
run_one printable
echo "ALL_DONE_GRADED_N128"
