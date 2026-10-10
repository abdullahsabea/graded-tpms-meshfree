#!/usr/bin/env bash
# Re-evaluate every volume-calibrated mesh with both definitions of the apparent
# modulus (loaded-face reaction and Hill-Mandel energy). The energy form is the
# one the mesh-free solver computes, so it is what the validation must use.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
WIN="${PROJECT_ROOT:?set PROJECT_ROOT to the archive root}/research/n3"
IMG="simvia/code_aster:stable"
VF=0.19328
cd "$HERE"

launch () {   # $1 tag  $2 mail
  tag=$1; mail=$2
  if [ ! -f "$HERE/$mail" ]; then echo "missing mesh $mail"; return; fi
  if [ -f "$HERE/oute_${tag}.mess" ]; then echo "skip $tag"; return; fi
  cat > "$HERE/study_e_${tag}.export" <<EOF
P actions make_etude
P memory_limit 48000
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
  launch "uniform_N${N}"   "gyroid_N${N}_vf${VF}.mail"            &
  launch "graded_N${N}"    "gyroid_graded_N${N}_vf${VF}.mail"     &
  launch "printable_N${N}" "gyroid_printable_N${N}_vf${VF}.mail"  &
  wait
done
for N in 48 64 96 128; do
  launch "primitive_N${N}" "primitive_N${N}_vf${VF}.mail" &
  launch "diamond_N${N}"   "diamond_N${N}_vf${VF}.mail"   &
  wait
done
echo "ALL_DONE_ENERGY_LADDER"
