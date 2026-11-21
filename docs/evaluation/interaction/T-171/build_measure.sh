#!/bin/sh
# T-171: builds the evidence tool against an existing engine build (default build/fast-dev). Not part of the gate.
B=${1:-build/fast-dev}
g++ -std=c++23 -O2 -I engine docs/evaluation/interaction/T-171/measure_t171.cpp \
  -L"$B/engine" -lplush_scene -lplush_model -lplush_fuzz -lplush_anim -lplush_geom -lplush_core -o "$B/measure_t171"
