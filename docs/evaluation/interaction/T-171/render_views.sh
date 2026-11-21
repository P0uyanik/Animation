#!/bin/sh
# T-171: renders evidence frames of one variant's shot.blend through fixed cameras (T-051 render_close.py):
#   close = a close camera on the cup, front: every frame of the clip range and the sheet frames
#   side  = a close camera from the boy's right (finger gaps against the cup wall): sheet frames
#   shot  = the e910 s010 shot camera at 1280x720 (make_sheets.py crops the hand from it at shot size): sheet frames
# Usage: render_views.sh <variant dir with render/shot.blend> <sheet frames, comma separated> <clip from> <clip to> [samples]
D=$1; FR=$2; A=$3; B=$4; SPP=${5:-16}
BLEND=$(find "$D" -name "*.blend" | head -1)
RC=docs/evaluation/animation/T-051/render_close.py
ALL=$(python3 -c "print(','.join(str(f) for f in sorted(set(range($A, $B + 1)) | {int(x) for x in '$FR'.split(',')})))")
blender -b --factory-startup -P $RC -- --blend "$BLEND" --frames "$ALL" --out "$D/views" --tag close --samples "$SPP" \
  --res 480 360 --view close 0.02 0.60 0.50 -0.02 0.54 0.0 60
blender -b --factory-startup -P $RC -- --blend "$BLEND" --frames "$FR" --out "$D/views" --tag close --samples "$SPP" \
  --res 480 360 --view side 0.42 0.62 0.22 -0.02 0.54 0.0 60
blender -b --factory-startup -P $RC -- --blend "$BLEND" --frames "$FR" --out "$D/views" --tag shot --samples "$SPP" \
  --res 1280 720 --view shot 0.0 1.071 1.464 0.0 0.76 0.003 32
