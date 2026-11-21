#!/bin/sh
# T-171: bake a variant scene and build its shot.blend (no frames rendered). Usage: bake_blend.sh <scene.json> <out dir>
# FRAMES=A-B bakes a frame range only (the Blender scene build is slow: about 10 minutes and more for the whole shot).
# Needs run_shot's prepare stage (cast.json, packages) in the shot's build folder.
set -e
SCENE=$1; OUT=$2; BUILD=${BUILD:-episodes/e910_showcase/shots/s010/build}; ENGINE=${ENGINE:-build/fast-dev/apps/render-cli/plush-render}
mkdir -p "$OUT"
"$ENGINE" "$SCENE" --bake "$OUT/bake.json" ${FRAMES:+--frames $FRAMES}
sha256sum "$OUT/bake.json" > "$OUT/bake.sha256"
blender -b --factory-startup -P pipeline/charsys/shot_render.py -- --bake "$OUT/bake.json" --cast "$BUILD/cast.json" \
  --out "$OUT/render" --profile "${PROFILE:-final720}" --blend-only
