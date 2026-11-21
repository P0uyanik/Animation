#!/bin/sh
# T-185: evidence frames of one shot.blend (bake_blend.sh of T-171, FRAMES=58-86) through fixed cameras
# (T-051 render_close.py; engine coordinates, +Y up). Frames that exist are skipped. One Blender at a time (~5 GB).
#   shotz = the e910 s010 shot camera's own position (0, 1.071, 1.464), aimed at the cup with lens 128 instead of 32:
#           the shot's view of the hand, enlarged 4x (a quarter-width box of the 1280x720 frame). Clip frames A..B.
#   shot  = the shot camera itself, 960x540 (shot size), f84.
#   hi    = T-171's strict camera above the boy's right side (r3_strict_pickup.jpg), sheet frames.
#   HI_CAM / HI_FRAMES / SHOT_FRAME override the strict camera, its frames and the shot-size frame (e909: the girl's
#   left side, the strict camera mirrored about the cup).
# Usage: render_views.sh <dir with render/shot.blend> <clip from> <clip to> [samples]
D=$1; A=$2; B=$3; SPP=${4:-12}
BLEND=$(find "$D" -name "*.blend" | head -1)
RC=docs/evaluation/animation/T-051/render_close.py
view() {  # name, frames (comma separated), resolution, camera (cx cy cz tx ty tz lens)
  NAME=$1; FR=$2; RES=$3; CAM=$4
  TODO=$(python3 -c "
import os
print(','.join(f for f in '$FR'.split(',') if not os.path.exists('$D/views/v_${NAME}_f%04d.png' % int(f))))")
  [ -z "$TODO" ] && return 0
  blender -b --factory-startup -P $RC -- --blend "$BLEND" --frames "$TODO" --out "$D/views" --tag v --samples "$SPP" \
    --res $RES --view "$NAME" $CAM
}
CLIP=$(python3 -c "print(','.join(str(f) for f in range($A, $B + 1)))")
view shotz "$CLIP" "480 270" "0.0 1.071 1.464 -0.04 0.53 0.01 128"
view hi "${HI_FRAMES:-64,70,74,76,80,84}" "400 300" "${HI_CAM:-0.16 0.90 0.30 -0.01 0.53 0.0 85}"
view shot "${SHOT_FRAME:-84}" "960 540" "0.0 1.071 1.464 0.0 0.76 0.003 32"
