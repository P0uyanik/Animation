#!/bin/bash
# T-207 sheet renders (repository root): builds current / V1 / V2 / V3 / D for one character and renders 4 views.
#   docs/evaluation/characters/T-207/sheets.sh <boy|girl|third> <work dir> [px] [spp]
set -e
K=$1; W=$2; PX=${3:-768}; SPP=${4:-16}
T=docs/evaluation/characters/T-207; A=assets/characters
case $K in
  boy)   M=$A/boy_yellow_hoodie/versions/2.3.0/boy_yellow_hoodie_master.blend; TG=0,0,0.91; FH=0.58; V=0:6,-35:6,-90:6,180:6;;
  girl)  M=$A/girl_auburn_bun_glasses/versions/0.14.0/girl_auburn_bun_glasses_master.blend; TG=0,0,0.84; FH=0.66; V=0:5,-45:5,90:5,180:5;;
  third) M=$A/girl_white_hair_blue_dress/versions/0.1.0/girl_white_hair_blue_dress_master.blend; TG=0,0,0.79; FH=0.56; V=0:5,-30:5,-90:5,180:5;;
esac
B="blender -b --factory-startup"
mkdir -p $W/$K
for L in V1 V2 V3; do
  [ -f $W/$K/$L.blend ] || $B -P pipeline/charsys/groom/flock.py -- --blend $M --out $W/$K/$L.blend \
      --options $T/options/$L.json --report $W/$K/$L.build.json | grep FLOCK
done
if [ ! -f $W/$K/D.blend ]; then
  $B -P pipeline/charsys/groom/hair_curves.py -- --blend $M --out $W/$K/D_combed.blend \
      --options $T/options/hair_curves/D_combed.json --report $W/$K/D_combed.build.json | tail -1
  $B -P pipeline/charsys/groom/flock.py -- --blend $W/$K/D_combed.blend --out $W/$K/D.blend \
      --options $T/options/D.json --report $W/$K/D.build.json | grep FLOCK
  rm -f $W/$K/D_combed.blend
fi
for L in current V1 V2 V3 D; do
  F=$W/$K/$L.blend; [ $L = current ] && F=$M
  [ -f $W/$K/r/$L.json ] || $B -P $T/render_views.py -- $W/$K/r $F $L $TG $FH $V --samples $SPP --px $PX | grep '^T207'
done
