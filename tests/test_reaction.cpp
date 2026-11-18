// T-097-0 stub for T-097B (personality-driven reactions); T-097B replaces it with real tests.
#include <doctest/doctest.h>

#include "scene/acting.h"

TEST_CASE("acting interface defaults are neutral (T-097-0)") {
  plush::PersonalityModulation m;
  CHECK(m.intensityScale == doctest::Approx(1.0));
  CHECK(m.tempoScale == doctest::Approx(1.0));
  plush::ReactionPlan p;
  CHECK(p.noticeDelay == doctest::Approx(0.0));
  CHECK(p.target.weights.empty());
}
