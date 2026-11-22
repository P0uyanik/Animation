#!/bin/sh
# T-183 round 3, with the opt-in scene colliders (props, neighbours): derive + prepare + bake + measure one shot.
# Run from the repository root.
#   sh r4_run.sh <blender wrapper> <log dir> <tag> <source shot dir (.../shots/sNNN)> <character> [...]
# Steps: 1. the copy <shot>_t183 without neighbour colliders (derive_shot.py --props --no-neighbours), prepare, bake as
#           <tag>a (where the hair is without them; also the "without" time of the slowdown factor);
#        2. the copy with the neighbours fitted on that bake (--neighbours-from), bake as <tag>b;
#        3. per character measure_props.py (boxes, props, other characters; every frame) and measure_body.py (own body
#           and garments; every ${STEP:-1}st frame) on <tag>b.
# Output: <log dir>/{prep,bake,props,body}_<tag>_<key>[_<character>].{log,json}; bake seconds and a line per shot in
# <log dir>/r4_run.status.
bl=$1; S=$2; tag=$3; src=$(echo $4 | sed 's|/*$||'); shift 4
T=docs/evaluation/characters/T-183/tools
shot=${src}_t183
key=$(echo $shot | sed 's|episodes/||; s|/shots/|_|; s|_two_char_acting||; s|_paper_boat||')
E=build/apps/render-cli/plush-render
python3 $T/derive_shot.py $src/shot.scene.json --props --no-neighbours > $S/derive_${tag}_$key.log 2>&1
python3 pipeline/production/run_shot.py --shot $shot/shot.scene.json --blender $bl --stages prepare --run-dir ${tag}p > $S/prep_${tag}_$key.log 2>&1
t0=$(date +%s.%N)
python3 pipeline/production/run_shot.py --shot $shot/shot.scene.json --blender $bl --stages bake --bake-engine $E --run-dir ${tag}a > $S/bake_${tag}a_$key.log 2>&1
t1=$(date +%s.%N)
python3 $T/derive_shot.py $src/shot.scene.json --props --neighbours-from=$shot/build/runs/${tag}a/bake.json >> $S/derive_${tag}_$key.log 2>&1
python3 pipeline/production/run_shot.py --shot $shot/shot.scene.json --blender $bl --stages prepare --run-dir ${tag}q >> $S/prep_${tag}_$key.log 2>&1
t2=$(date +%s.%N)
python3 pipeline/production/run_shot.py --shot $shot/shot.scene.json --blender $bl --stages bake --bake-engine $E --run-dir ${tag}b > $S/bake_${tag}b_$key.log 2>&1
t3=$(date +%s.%N)
B=$shot/build/runs/${tag}b/bake.json
for c in "$@"; do
  python3 $T/measure_props.py $B --character=$c --others --out=$S/props_${tag}_${key}_$c.json > $S/props_${tag}_${key}_$c.log 2>&1
  python3 $T/measure_body.py $B --character=$c --step=${STEP:-1} --out=$S/body_${tag}_${key}_$c.json > $S/body_${tag}_${key}_$c.log 2>&1
done
echo "$tag $key done: bake without neighbours $(echo "$t1 - $t0" | bc) s, with $(echo "$t3 - $t2" | bc) s" >> $S/r4_run.status
