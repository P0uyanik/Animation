#!/bin/bash
# R3 stacking check: build the T-155 candidate (= current boy 2.3.0 / girl 0.14.0, published third 0.1.0), then add one
# override layer per step, the last step from the stacked R3 spec; strict-hash every master (T-158 mesh_hash_strict.py).
# Then base and R3 are built a second time (repeat_*) for the repeatability check.
# Usage (repo root): docs/evaluation/characters/R3/chain_build.sh <work dir> [character ...]
set -u
W=$1; shift
E=docs/evaluation/characters; A=assets/characters; O9=$E/T-159/overrides; O7=$E/T-167/overrides; O6=$E/T-156
export PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
step() {  # cid name spec [overrides...]
  local cid=$1 name=$2 spec=$3; shift 3
  local out=$W/$cid/$name; mkdir -p "$out"
  local ov=(); for o in "$@"; do ov+=(--override "$o"); done
  blender -b --factory-startup -t 1 -P pipeline/charsys/build_character.py -- --spec "$spec" --out "$out" \
    --no-glb --no-compare "${ov[@]}" > "$out/build.log" 2>&1
  local rc=$?
  blender -b --factory-startup -t 1 -P pipeline/charsys/tests/mesh_hash_strict.py -- "$out/${cid}_master.blend" \
    "$out/hash.json" > "$out/hash.log" 2>&1
  echo "$cid $name build rc=$rc hash rc=$? $(date -u +%H:%M)"
}
chars=("$@"); [ ${#chars[@]} -eq 0 ] && chars=(boy_yellow_hoodie girl_auburn_bun_glasses girl_white_hair_blue_dress)
for cid in "${chars[@]}"; do
  case $cid in
    boy_yellow_hoodie) v=2.3.0; L=("ears:$O9/boy_ears.json" "face_t168:$E/T-168/boy_yellow_hoodie.T-168.override.json") ;;
    girl_auburn_bun_glasses) v=0.14.0; L=("temple:$O9/girl_auburn_bun_glasses.temple.override.json" "ears:$O9/girl_ears.json" "glasses:$O9/girl_glasses.json" "hair_r7:$O7/girl_auburn_bun_glasses.hair_r7.override.json" "eyes_t156:$O6/auburn/girl_auburn_bun_glasses.eyes.override.json") ;;
    girl_white_hair_blue_dress) v=0.1.0; L=("temple:$O9/girl_white_hair_blue_dress.temple.override.json" "ears:$O9/third_ears.json" "hair_r7:$O7/girl_white_hair_blue_dress.hair_r7.override.json" "eyes_t156:$O6/third/girl_white_hair_blue_dress.eyes.override.json") ;;
  esac
  base=$A/$cid/spec/candidates/T-155/$cid.$v.spec.json
  step "$cid" 0_base "$base"
  acc=(); i=1
  for l in "${L[@]}"; do acc+=("${l#*:}"); step "$cid" "${i}_${l%%:*}" "$base" "${acc[@]}"; i=$((i+1)); done
  step "$cid" "${i}_R3_final" "$A/$cid/spec/candidates/R3/$cid.$v.spec.json"
  # repeatability (T-158 strict hashes): default path and R3 build a second time
  step "$cid" "repeat_base" "$base"
  step "$cid" "repeat_R3_final" "$A/$cid/spec/candidates/R3/$cid.$v.spec.json"
done
echo CHAINDONE
