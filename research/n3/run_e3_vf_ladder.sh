#!/usr/bin/env bash
# Optimization case study, volume-calibrated and iso-resolution.
# Uniform baseline meshes come from run_vf_ladder.sh (gyroid_N*_vf<VF>.mail);
# here the graded and manufacturability-constrained designs are voxelized at the
# same resolutions with delta-t0 re-solved so every mesh carries the same
# discrete volume fraction.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
WIN="${PROJECT_ROOT:?set PROJECT_ROOT to the archive root}/research/n3"
IMG="simvia/code_aster:stable"
VF=0.19328
cd "$HERE"

python make_mesh_graded.py    --vf $VF 48,64,96,128
python make_mesh_printable.py --vf $VF 48,64,96,128

launch () {   # $1 tag (graded|printable)  $2 N
  tag=$1; N=$2
  if [ -f "$HERE/outvf_${tag}_N${N}.mess" ]; then echo "skip ${tag} N=${N}"; return; fi
  if [ "$N" -ge 96 ]; then mem=48000; else mem=8000; fi
  cat > "$HERE/study_${tag}_vf_N${N}.export" <<EOF
P actions make_etude
P memory_limit $mem
P time_limit 14400
P mpi_nbcpu 1
F comm /shared/homog.comm D 1
F mail /shared/gyroid_${tag}_N${N}_vf${VF}.mail D 20
F mess /shared/outvf_${tag}_N${N}.mess R 6
EOF
  docker run --rm -m 40g -v "$WIN:/shared" "$IMG" \
    bash -c "source /opt/activate.sh; run_aster /shared/study_${tag}_vf_N${N}.export" \
    > "$HERE/logvf_${tag}_N${N}.txt" 2>&1
  echo "done ${tag} N=${N}: $(grep -h C1111_KUBC "$HERE/outvf_${tag}_N${N}.mess" | tail -1)"
}

for N in 48 64 96 128; do
  for tag in graded printable; do launch "$tag" "$N" & done
  wait
done
echo "ALL_DONE_E3_VF_LADDER"
