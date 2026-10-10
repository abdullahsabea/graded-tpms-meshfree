#!/usr/bin/env bash
# Re-run the KUBC solve on the volume-calibrated 96^3 meshes with field output,
# so DEM and FE can be compared field by field (not only through C1111).
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
WIN="${PROJECT_ROOT:?set PROJECT_ROOT to the archive root}/research/n3"
IMG="simvia/code_aster:stable"
VF=0.19328
cd "$HERE"

run_one () {   # $1 tag  $2 mail file
  tag=$1; mail=$2
  if [ -f "$HERE/fields_${tag}.rmed" ]; then echo "skip $tag"; return; fi
  cat > "$HERE/study_fields_${tag}.export" <<EOF
P actions make_etude
P memory_limit 48000
P time_limit 14400
P mpi_nbcpu 1
F comm /shared/homog_fields.comm D 1
F mail /shared/${mail} D 20
F mess /shared/outf_${tag}.mess R 6
F med /shared/fields_${tag}.rmed R 80
EOF
  echo "=== fields: $tag ==="
  docker run --rm -m 40g -v "$WIN:/shared" "$IMG" \
    bash -c "source /opt/activate.sh; run_aster /shared/study_fields_${tag}.export" \
    > "$HERE/logf_${tag}.txt" 2>&1
  grep -hE "C1111_KUBC" "$HERE/outf_${tag}.mess" | tail -1
}

run_one uniform   "gyroid_N96_vf${VF}.mail"          &
run_one graded    "gyroid_graded_N96_vf${VF}.mail"   &
wait
run_one primitive "primitive_N96_vf${VF}.mail"       &
run_one diamond   "diamond_N96_vf${VF}.mail"         &
wait
echo "ALL_DONE_FIELDS"
