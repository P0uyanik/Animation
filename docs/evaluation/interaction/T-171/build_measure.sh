#!/bin/sh
# T-171: builds the evidence tools (measure_t171, preview_t171) against an existing engine build (default
# build/fast-dev). Not part of the gate. Same flags as the engine (-O3 -DNDEBUG): a tool built without them makes the
# linker take its slow copies of the shared inline maths, and a scene load goes from 9 s to 70 s.
B=${1:-build/fast-dev}
for T in measure_t171 preview_t171; do
  g++ -std=c++23 -O3 -DNDEBUG -I engine docs/evaluation/interaction/T-171/$T.cpp \
    -L"$B/engine" -lplush_scene -lplush_model -lplush_fuzz -lplush_anim -lplush_geom -lplush_core -o "$B/$T" || exit 1
done
