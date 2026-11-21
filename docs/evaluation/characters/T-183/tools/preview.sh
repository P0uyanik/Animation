#!/bin/sh
# Cheap preview frames of a shot bake from a close-up view (T-183 round 2): one Blender run per frame, two at a time,
# then one strip image. About 47 s per frame at 640x360, 8 samples (4 cores).
#   preview.sh <blender wrapper> <out dir> <name> <bake.json> <cast.json> <view> <samples> <frame> [<frame> ...]
# <view>: side | back | shoulder | arm | side_l (tools/closeup.py). The cast.json is <shot>/build/cast.json; a bake of
# the same rig bones renders with any master that has them (a prototype bake with the candidate's master).
BL=$1; OUT=$2; n=$3; bake=$4; cast=$5; view=$6; spp=$7; shift 7
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/../../../../.." && pwd)
mkdir -p "$OUT"; cd "$ROOT" || exit 1
i=0
for f in "$@"; do
  ( python3 "$HERE/closeup.py" "$bake" "$OUT/${n}_${view}_$f.json" "$view" --frames=$f-$f && "$BL" -b --factory-startup -P pipeline/charsys/shot_render.py -- --bake "$OUT/${n}_${view}_$f.json" --cast "$cast" --out "$OUT/${n}_${view}_$f" --frames $f-$f --resolution 640 360 --samples "$spp" --profile review > "$OUT/${n}_${view}_$f.log" 2>&1 ) &
  i=$((i+1)); [ $((i%2)) -eq 0 ] && wait
done
wait
python3 - "$OUT" "$n" "$view" "$@" <<'PY'
import sys
from PIL import Image, ImageDraw
out, n, view, frames = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
cols = min(3, len(frames)); rows = (len(frames) + cols - 1) // cols
w = Image.new("RGB", (640 * cols, 360 * rows))
for i, f in enumerate(frames):
    im = Image.open(f"{out}/{n}_{view}_{f}/frame_{int(f):04d}.png").convert("RGB")
    ImageDraw.Draw(im).text((8, 6), f"{n} {view} f{f}", fill=(255, 255, 0))
    w.paste(im, (640 * (i % cols), 360 * (i // cols)))
w.save(f"{out}/strip_{n}_{view}.jpg", quality=88); print(f"{out}/strip_{n}_{view}.jpg")
PY
