#!/usr/bin/env bash
# Volume-calibrated FE ladders for the two remaining N3 thickness anchors
# (t=0.20 and t=0.45), so every entry of the N3 table uses one protocol.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
WIN="${PROJECT_ROOT:?set PROJECT_ROOT to the archive root}/research/n3"
IMG="simvia/code_aster:stable"
cd "$HERE"

python make_mesh.py --vf 0.128723 48,64,96,128 gyroid
python make_mesh.py --vf 0.291115 48,64,96,128 gyroid

launch () {   # $1 vf_target  $2 tag  $3 N
  vft=$1; tag=$2; N=$3
  if [ -f "$HERE/outvf_${tag}_N${N}.mess" ]; then echo "skip ${tag} N=${N}"; return; fi
  if [ "$N" -ge 96 ]; then mem=48000; else mem=8000; fi
  cat > "$HERE/study_${tag}_vf_N${N}.export" <<EOF
P actions make_etude
P memory_limit $mem
P time_limit 14400
P mpi_nbcpu 1
F comm /shared/homog.comm D 1
F mail /shared/gyroid_N${N}_vf${vft}.mail D 20
F mess /shared/outvf_${tag}_N${N}.mess R 6
EOF
  docker run --rm -m 40g -v "$WIN:/shared" "$IMG" \
    bash -c "source /opt/activate.sh; run_aster /shared/study_${tag}_vf_N${N}.export" \
    > "$HERE/logvf_${tag}_N${N}.txt" 2>&1
  echo "done ${tag} N=${N}: $(grep -h C1111_KUBC "$HERE/outvf_${tag}_N${N}.mess" | tail -1)"
}

for N in 48 64 96 128; do
  launch 0.128723 t020 "$N" &
  launch 0.291115 t045 "$N" &
  wait
done
echo "ALL_DONE_THICKNESS_VF_LADDER"
