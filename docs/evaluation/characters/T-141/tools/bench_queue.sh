#!/bin/sh
# T-141 cost + flicker queue on the T-124 benchmark shot (e907 s010_verbs, 1280x720). Run alone on the machine.
#   sh bench_queue.sh <run dir with blend/ blend_add/ blend_replace/ shot.blend and bake.json> <blender>
# 1. frame 65 with the T-124 review settings (16 spp, adaptive 0.05)   2. frame 65 with the production final settings
# 3. frames 60-66 with the T-125 passes (16 spp) and the motion_checks flicker check
set -e
RUN=$1; BL=${2:-blender}; ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
for v in base add replace; do
  B=$RUN/blend$( [ $v = base ] || echo _$v )/shot.blend
  $BL -b --factory-startup -P $ROOT/tools/render_bench/bench.py -- --blend $B --frames 65 --variant review16 --out $RUN/bench/review_$v > $RUN/bench_review_$v.log 2>&1
done
for v in base add replace; do
  B=$RUN/blend$( [ $v = base ] || echo _$v )/shot.blend
  $BL -b --factory-startup -P $ROOT/tools/render_bench/bench.py -- --blend $B --frames 65 --variant baseline --out $RUN/bench/final_$v > $RUN/bench_final_$v.log 2>&1
done
for v in base add replace; do
  B=$RUN/blend$( [ $v = base ] || echo _$v )/shot.blend
  $BL -b --factory-startup -P $ROOT/tools/motion_checks/render_passes.py -- --blend $B --out $RUN/passes_$v --frames 60-66 --samples 16 > $RUN/passes_$v.log 2>&1
  python3 $ROOT/tools/motion_checks/run.py --bake $RUN/bake.json --frames $RUN/passes_$v --out $RUN/motion_$v --strips 2 > $RUN/motion_$v.log 2>&1 || true
done
echo QUEUE_DONE
