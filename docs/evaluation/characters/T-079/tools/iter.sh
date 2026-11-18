#!/bin/bash
# T-079 iteration helper (not evidence): rebuild one candidate and render a low-sample 5-view strip.
# iter.sh <key> <tag> ; needs $B (blender), $W (work dir with base/<key>/*_master.blend)
set -e
K=$1; TAG=$2; R=$(cd "$(dirname "$0")/../../../../.." && pwd); T=$R/docs/evaluation/characters/T-079
python3 $T/tools/make_candidates.py $K >/dev/null
BASE=$(ls $W/base/$K/*_master.blend)
$B -b --factory-startup -P $T/tools/build_candidate.py -- --base $BASE --candidate $T/candidates/$K.hair_v3.json --out $W/it/$K 2>&1 | grep -o "keepout.*"
BL=$(ls $W/it/$K/*_hairv3.blend)
case $K in
 boy) A="0,0.01,0.87 0.56 0,-45,60,-120,180";;
 girl) A="0,0,0.72 0.9 0,-150,-90,60,180 --tall 1.7";;
 third) A="0,0,0.75 0.85 0,30,-100,95,180 --tall 1.7";;
esac
$B -b --factory-startup -P $T/tools/preview.py -- $BL $W/it/${K}_$TAG.png $A --px ${PX:-260} --spp 6 >/dev/null 2>&1
echo $W/it/${K}_$TAG.png
