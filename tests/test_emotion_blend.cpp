// T-097-0 stub for T-097A (emotion blending); T-097A replaces it with real transition tests.
#include <doctest/doctest.h>

#include "scene/acting.h"

TEST_CASE("emotion state defaults are neutral (T-097-0)") {
  plush::EmotionState s;
  CHECK(s.weights.empty());
  CHECK(s.pleasantness == doctest::Approx(0.0));
  CHECK(s.energy == doctest::Approx(0.0));
}
