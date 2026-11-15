// T-003: emotion format plush.emotion/1 (scene/emotion.h) and the shared library content/emotions.
#include <doctest/doctest.h>

#include <filesystem>

#include "scene/emotion.h"

using namespace plush;

TEST_CASE("emotion: format, variants as merge patch, unknown fields kept") {
  Json j = Json::parse(R"({"format": "plush.emotion", "version": 1, "name": "x", "x_future": {"a": 1},
    "face": {"sad": 0.8, "frown": 0.2}, "body": {"clip": "p", "loop": true, "mask": ["head"]},
    "gesture": {"clip": "g", "offset": 0.5, "face": {"jawOpen": 0.7}},
    "timing": {"onset": 0.2, "hold": 1, "release": 0.3, "curve": "linear"},
    "variants": {"v": {"face": {"frown": null, "squint": 0.5}, "body": {"clip": "q"}}}})");
  auto e = emotionFromJson(j);
  REQUIRE(e);
  CHECK(e->face.size() == 2);
  CHECK(e->bodyClip == "p");
  CHECK(e->bodyLoop == 1);
  CHECK(e->bodyMask == std::vector<std::string>{"head"});
  CHECK(e->hasGesture);
  CHECK(e->gesture.offset == doctest::Approx(0.5));
  CHECK(e->gesture.face.size() == 1);
  CHECK(e->linear);
  CHECK(e->raw.contains("x_future"));
  auto v = emotionFromJson(j, "v");
  REQUIRE(v);
  CHECK(v->bodyClip == "q");
  CHECK(v->bodyLoop == 1);  // kept from the base
  std::map<std::string, float> f(v->face.begin(), v->face.end());
  CHECK(f.size() == 2);
  CHECK(f.count("sad") == 1);
  CHECK(f.count("squint") == 1);
  CHECK_FALSE(emotionFromJson(j, "missing"));
  j["version"] = 2;
  CHECK_FALSE(emotionFromJson(j));
}

TEST_CASE("emotion library: every file parses, names its clips, and its variants parse") {
  const auto dir = std::filesystem::path(PLUSH_SOURCE_DIR) / "content" / "emotions";
  int n = 0;
  for (const auto& entry : std::filesystem::directory_iterator(dir)) {
    auto j = parseJsonFile(entry.path());
    REQUIRE(j);
    auto e = emotionFromJson(*j);
    INFO(entry.path().string());
    REQUIRE(e);
    CHECK(!e->face.empty());
    CHECK(std::filesystem::exists(dir.parent_path() / "clips" / (e->bodyClip + ".clip.json")));
    if (e->hasGesture) CHECK(std::filesystem::exists(dir.parent_path() / "clips" / (e->gesture.clip + ".clip.json")));
    const Json variants = j->value("variants", Json::object());
    for (auto& [name, patch] : variants.items()) CHECK(emotionFromJson(*j, name));
    ++n;
  }
  CHECK(n == 8);
}
