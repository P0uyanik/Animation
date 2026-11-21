#!/bin/sh
# T-171: renders evidence frames of one variant's shot.blend through fixed cameras (T-051 render_close.py):
#   shot  = the e910 s010 shot camera (1280x720, the hand is cropped from it at shot size by make_sheets.py)
#   close = a close camera on the cup, front
#   side  = a close camera from the boy's right (finger gaps against the cup wall)
# Usage: render_views.sh <variant dir with render/shot.blend> <frames, comma separated> [samples]
D=$1; FR=$2; SPP=${3:-24}
BLEND=$(find "$D" -name "*.blend" | head -1)
blender -b --factory-startup -P docs/evaluation/animation/T-051/render_close.py -- --blend "$BLEND" --frames "$FR" \
  --out "$D/views" --tag shot --samples "$SPP" --res 1280 720 --view shot 0.0 1.071 1.464 0.0 0.76 0.003 32
blender -b --factory-startup -P docs/evaluation/animation/T-051/render_close.py -- --blend "$BLEND" --frames "$FR" \
  --out "$D/views" --tag close --samples "$SPP" --res 640 480 \
  --view close 0.02 0.60 0.50 -0.02 0.54 0.0 60 --view side 0.42 0.62 0.22 -0.02 0.54 0.0 60
