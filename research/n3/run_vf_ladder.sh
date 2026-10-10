#!/usr/bin/env bash
# N3 cross-family gate, volume-calibrated mesh ladder.
# At each resolution the level-set threshold is re-solved so the DISCRETE voxel
# volume fraction equals the common target, so refinement measures staircase
# error alone rather than staircase error mixed with volume drift.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
WIN="${PROJECT_ROOT:?set PROJECT_ROOT to the archive root}/research/n3"
IMG="simvia/code_aster:stable"
VF=0.19328
cd "$HERE"

for fam in gyroid primitive diamond; do
  python make_mesh.py --vf $VF 48,64,96,128 "$fam"
done

launch () {   # $1 family  $2 N
  fam=$1; N=$2
  if [ -f "$HERE/outvf_${fam}_N${N}.mess" ]; then
    echo "skip ${fam} N=${N} (already computed)"; return
  fi
  if [ "$N" -ge 96 ]; then mem=48000; else mem=8000; fi
  cat > "$HERE/study_${fam}_vf_N${N}.export" <<EOF
P actions make_etude
P memory_limit $mem
P time_limit 14400
P mpi_nbcpu 1
F comm /shared/homog.comm D 1
F mail /shared/${fam}_N${N}_vf${VF}.mail D 20
F mess /shared/outvf_${fam}_N${N}.mess R 6
EOF
  docker run --rm -m 40g -v "$WIN:/shared" "$IMG" \
    bash -c "source /opt/activate.sh; run_aster /shared/study_${fam}_vf_N${N}.export" \
    > "$HERE/logvf_${fam}_N${N}.txt" 2>&1
  echo "done ${fam} N=${N}: $(grep -h C1111_KUBC "$HERE/outvf_${fam}_N${N}.mess" | tail -1)"
}

for N in 48 64 96; do
  for fam in gyroid primitive diamond; do launch "$fam" "$N" & done
  wait
done
for fam in gyroid primitive diamond; do launch "$fam" 128 & done
wait
echo "ALL_DONE_VF_LADDER"
