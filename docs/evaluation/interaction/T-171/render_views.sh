#!/bin/sh
# T-171: renders evidence frames of one variant's shot.blend through fixed cameras (T-051 render_close.py), 480x360:
#   left  = close, from the front-left: the fingers on the cup wall. Every frame of the clip range A..B.
#   close = close, from the front: the back of the hand. Sheet frames.
#   rest  = the hanging right hand before the reach (f44).
#   shot  = the e910 s010 shot camera at 1280x720 (make_sheets.py crops the hand from it at shot size).
# Usage: render_views.sh <variant dir with render/shot.blend> <clip from> <clip to> [samples]
# About 45 s per frame on 4 CPU cores (the scene evaluation dominates), so the frame lists are short.
D=$1; A=$2; B=$3; SPP=${4:-12}
BLEND=$(find "$D" -name "*.blend" | head -1)
RC=docs/evaluation/animation/T-051/render_close.py
CLIP=$(python3 -c "print(','.join(str(f) for f in range($A, $B + 1)))")
blender -b --factory-startup -P $RC -- --blend "$BLEND" --frames "$CLIP" --out "$D/views" --tag v --samples "$SPP" \
  --res 480 360 --view left -0.32 0.60 0.36 -0.02 0.53 0.01 85
blender -b --factory-startup -P $RC -- --blend "$BLEND" --frames 70,76,78,81 --out "$D/views" --tag v --samples "$SPP" \
  --res 480 360 --view close 0.0 0.60 0.50 -0.02 0.53 0.01 85
blender -b --factory-startup -P $RC -- --blend "$BLEND" --frames 44 --out "$D/views" --tag v --samples "$SPP" \
  --res 480 360 --view rest 0.14 0.42 0.42 0.05 0.37 -0.03 85
blender -b --factory-startup -P $RC -- --blend "$BLEND" --frames 44,70,76,81 --out "$D/views" --tag v --samples "$SPP" \
  --res 1280 720 --view shot 0.0 1.071 1.464 0.0 0.76 0.003 32
