#!/usr/bin/env bash
# Energy-basis (Hill-Mandel) evaluation of the two remaining N3 thickness
# anchors (t=0.20, t=0.45) on their volume-calibrated ladders.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
WIN="${PROJECT_ROOT:?set PROJECT_ROOT to the archive root}/research/n3"
IMG="simvia/code_aster:stable"
cd "$HERE"

launch () {   # $1 tag  $2 mail
  tag=$1; mail=$2
  if [ ! -f "$HERE/$mail" ]; then echo "missing $mail"; return; fi
  if [ -f "$HERE/oute_${tag}.mess" ]; then echo "skip $tag"; return; fi
  if echo "$tag" | grep -qE "N(96|128)"; then mem=48000; else mem=8000; fi
  cat > "$HERE/study_e_${tag}.export" <<EOF
P actions make_etude
P memory_limit $mem
P time_limit 14400
P mpi_nbcpu 1
F comm /shared/homog2.comm D 1
F mail /shared/${mail} D 20
F mess /shared/oute_${tag}.mess R 6
EOF
  docker run --rm -m 40g -v "$WIN:/shared" "$IMG" \
    bash -c "source /opt/activate.sh; run_aster /shared/study_e_${tag}.export" \
    > "$HERE/loge_${tag}.txt" 2>&1
  echo "done ${tag}: $(grep -h 'C1111_ENERGY' "$HERE/oute_${tag}.mess" | tail -1)"
}

for N in 48 64 96 128; do
  launch "t020_N${N}" "gyroid_N${N}_vf0.128723.mail" &
  launch "t045_N${N}" "gyroid_N${N}_vf0.291115.mail" &
  wait
done
echo "ALL_DONE_ENERGY_ANCHORS"
