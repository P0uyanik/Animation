#!/bin/bash
# T-049 evidence renders for one study build: 3 fidelity views (tools/fidelity/run.py: Cycles, character_neutral/1,
# 16 samples + OIDN, 640 px) + 1 face close-up (groom_turnaround.py --closeup) = 4 Cycles stills.
#   render_evidence.sh <blender> <boy|girl> <A|B|C> <study_dir> <out_dir>
set -e
BL=$1; C=$2; AP=$3; ST=$4; OUT=$5
cd "$(dirname "$0")/../../../.."
if [ "$C" = boy ]; then ID=boy_yellow_hoodie; VIEWS=val27_front,val27_threequarter_right,val27_back; CU="closeup_face:-20:4:0,-0.02,0.82:0.46"
else ID=girl_auburn_bun_glasses; VIEWS=sheet30_front,sheet30_front_left,sheet30_back; CU="closeup_face:-20:4:0,-0.02,0.79:0.56"; fi
BLEND=$ST/${C}_${AP}/${ID}_study.blend
python3 tools/fidelity/run.py --character $ID --build $BLEND --blender $BL --out $OUT/${C}_${AP} --views $VIEWS --samples 16 --height 640 > $OUT/${C}_${AP}.fidelity.log 2>&1
$BL -b --factory-startup -P pipeline/charsys/tools/groom_turnaround.py -- $BLEND assets/characters/$ID/references/reference_index.json $OUT/${C}_${AP}/closeup --views none --samples 16 --height 640 --closeup "$CU" > $OUT/${C}_${AP}.closeup.log 2>&1
echo "$C $AP done"
