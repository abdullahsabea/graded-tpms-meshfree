#!/usr/bin/env bash
# Chunked DEM training driver: bash train_family.sh <family> <t> <total_iters> [chunk]
set -u
fam=$1; t=$2; total=$3; chunk=${4:-4000}
HERE="$(cd "$(dirname "$0")" && pwd)"
export OMP_NUM_THREADS=8
export MKL_NUM_THREADS=8
n=0
while [ $n -lt "$total" ]; do
  python "$HERE/dem_tpms.py" "$fam" "$t" "$chunk" 2>&1 | grep -Ev "^it .*  \(" | tail -6
  n=$((n + chunk))
  echo "--- $fam cumulative $n / $total ---"
done
echo "TRAIN_DONE $fam"
