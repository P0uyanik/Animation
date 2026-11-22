#!/bin/sh
# T-190: builds the evidence tool measure_t190 against an existing engine build (default build/fast-dev). Not part of
# the gate. Same flags as the engine (see T-171/build_measure.sh).
B=${1:-build/fast-dev}
g++ -std=c++23 -O3 -DNDEBUG -I engine docs/evaluation/interaction/T-190/measure_t190.cpp \
  -L"$B/engine" -lplush_scene -lplush_model -lplush_fuzz -lplush_anim -lplush_geom -lplush_core -o "$B/measure_t190"
