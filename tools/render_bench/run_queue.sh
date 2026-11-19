#!/usr/bin/env bash
# Runs bench.py once per queue line "<variant> <frames> [repeat] [run-name]" (sequentially; one render at a time so
# timings are not disturbed). Usage: run_queue.sh <blender> <shot.blend> <runs dir> <queue file>
set -u
blender="$1"; blend="$2"; runs="$3"; queue="$4"
here="$(cd "$(dirname "$0")" && pwd)"
while read -r variant frames repeat name extra; do
  [ -z "${variant:-}" ] && continue; case "$variant" in \#*) continue;; esac
  name="${name:-$variant}"
  [ -f "$runs/$name/bench.json" ] && { echo "[queue] skip $name (done)"; continue; }
  echo "[queue] start $name $(date -u +%H:%M:%S)"
  "$blender" -b -P "$here/bench.py" -- --blend "$blend" --frames "$frames" --repeat "${repeat:-1}" \
    --variant "$variant" --out "$runs/$name" --tag "$name" ${extra:-} > "$runs/$name.log" 2>&1
  echo "[queue] end $name rc=$? $(date -u +%H:%M:%S) $(grep -c '^\[bench\]' "$runs/$name.log") frames"
done < "$queue"
echo "[queue] all done"
