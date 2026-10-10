#!/usr/bin/env bash
# Chunked DEM training until the audited C1111 stops descending.
# Usage: bash train_until.sh <family> <t> <max_extra_iters> [chunk] [tol_pct]
# Stops when two consecutive chunks each move the audit by less than tol_pct.
set -u
fam=$1; t=$2; maxit=$3; chunk=${4:-4000}; tol=${5:-0.3}
HERE="$(cd "$(dirname "$0")" && pwd)"
export OMP_NUM_THREADS=8
export MKL_NUM_THREADS=8
prev=""; flat=0; n=0
while [ $n -lt "$maxit" ]; do
  out=$(python "$HERE/dem_tpms.py" "$fam" "$t" "$chunk" 2>&1)
  cur=$(echo "$out" | grep -oE "C1111_DEM = [0-9.]+" | tail -1 | awk '{print $3}')
  n=$((n + chunk))
  if [ -n "$prev" ]; then
    d=$(awk -v a="$prev" -v b="$cur" 'BEGIN{printf "%.3f", (a-b)/a*100}')
    echo "$fam +$n iters: C1111=$cur  (change ${d}%)"
    small=$(awk -v d="$d" -v t="$tol" 'BEGIN{print (d<t && d>-t) ? 1 : 0}')
    if [ "$small" = "1" ]; then flat=$((flat+1)); else flat=0; fi
    if [ $flat -ge 2 ]; then echo "CONVERGED $fam at C1111=$cur"; break; fi
  else
    echo "$fam +$n iters: C1111=$cur"
  fi
  prev=$cur
done
echo "TRAIN_UNTIL_DONE $fam C1111=$prev"
