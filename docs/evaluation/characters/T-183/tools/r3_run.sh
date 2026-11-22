#!/bin/sh
# T-183 round 3: prepare + bake + measure one shot (run from the repository root).
#   sh r3_run.sh <blender wrapper> <log dir> <tag> <shot dir> <character> [...]
# Runs: prepare as <tag>, bake as <tag>b (<shot dir>/build/runs/<tag>b/bake.json); per character measure_props.py
# (boxes, props, other characters; every frame) and measure_body.py (own body and garments; every ${STEP:-2}nd frame).
# Output: <log dir>/{prep,bake,props,body}_<tag>_<key>[_<character>].{log,json}; a line in <log dir>/r3_run.status.
bl=$1; S=$2; tag=$3; shot=$4; shift 4
T=docs/evaluation/characters/T-183/tools
key=$(echo $shot | sed 's|/*$||; s|episodes/||; s|/shots/|_|; s|_two_char_acting||; s|_paper_boat||')
python3 pipeline/production/run_shot.py --shot $shot/shot.scene.json --blender $bl --stages prepare --run-dir $tag > $S/prep_${tag}_$key.log 2>&1
python3 pipeline/production/run_shot.py --shot $shot/shot.scene.json --blender $bl --stages bake --bake-engine build/apps/render-cli/plush-render --run-dir ${tag}b > $S/bake_${tag}_$key.log 2>&1
B=$shot/build/runs/${tag}b/bake.json
for c in "$@"; do
  python3 $T/measure_props.py $B --character=$c --others --out=$S/props_${tag}_${key}_$c.json > $S/props_${tag}_${key}_$c.log 2>&1
  python3 $T/measure_body.py $B --character=$c --step=${STEP:-2} --out=$S/body_${tag}_${key}_$c.json > $S/body_${tag}_${key}_$c.log 2>&1
done
echo "$tag $key done" >> $S/r3_run.status
