// T-136 E2: blink scheduling (opt-in "blinkSchedule"): key beats keep the eyes open, blinks prefer gaze shifts and
// action changes, at most one blink per short beat, the personality rhythm stays; off = the face layer as before.
#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <filesystem>

#include "geom/json_io.h"
#include "scene/face_layer.h"
#include "scene/scene.h"

using namespace plush;

namespace {
const char* const kBoy = "boy_yellow_hoodie_1.0.0";

std::unique_ptr<SceneEvaluator> blinkScene(const Json& actions, const Json& schedule, int end) {
  Scene s;
  s.rate = FrameRate{24, 1};
  s.frameStart = 1;
  s.frameEnd = end;
  s.path = std::filesystem::path(PLUSH_SOURCE_DIR) / "tests/data/imported/scene.json";
  CharacterDesc cd;
  cd.name = "who";
  cd.asset = std::string(kBoy) + "/character.json";
  cd.life.enabled = true;
  s.characters.push_back(cd);
  s.actions = actions;
  s.blinkSchedule = schedule;
  auto ev = std::make_unique<SceneEvaluator>();
  auto r = ev->load(s, EvalOptions{2.5f, 1.0f, false, 0});
  REQUIRE(r.has_value());
  return ev;
}

// Looks every `every` frames (gaze shifts) and a pick-up-like action change list.
Json looks(int end, int every) {
  Json a = Json::array();
  for (int f = 1; f < end; f += every)
    a.push_back({{"type", "look"}, {"character", "who"}, {"start", f}, {"end", std::min(end, f + every - 1)},
                 {"target", Json::array({0.6 * ((f / every) % 2 ? 1 : -1), 0.9, 1.5})}});
  return a;
}

std::vector<int> onsets(const SceneEvaluator& ev, int a, int b) {
  std::vector<int> out;
  bool closed = false;
  for (int f = a; f <= b; ++f) {
    const bool c = ev.faceState(0, f).blink > 0.5f;
    if (c && !closed) out.push_back(f);
    closed = c;
  }
  return out;
}
}  // namespace

TEST_CASE("blink schedule: parsing") {
  CHECK(blinkScheduleFromJson(Json(), "a").value().enabled == false);
  CHECK(blinkScheduleFromJson(Json(true), "a").value().enabled);
  auto b = blinkScheduleFromJson(Json::parse(R"({"keyBeats": [{"start": 10, "end": 20},
      {"start": 30, "end": 40, "characters": ["b"]}], "shortBeatFrames": 12, "actionChanges": [5, 7]})"), "a");
  REQUIRE(b.has_value());
  CHECK(b->enabled);
  REQUIRE(b->keyBeats.size() == 1);  // the second beat is b's
  CHECK(b->keyBeats[0].first == 10);
  CHECK(b->shortBeatFrames == 12);
  CHECK(b->actionChanges.size() == 2);
  CHECK_FALSE(blinkScheduleFromJson(Json::parse(R"({"keyBeats": [{"start": 9, "end": 2}]})"), "a").has_value());
  CHECK_FALSE(blinkScheduleFromJson(Json::parse(R"({"bogus": 1})"), "a").has_value());
  CHECK_FALSE(blinkScheduleFromJson(Json(3), "a").has_value());
}

TEST_CASE("blink schedule: off is the face layer as before") {
  const Json acts = looks(480, 40);
  auto off = blinkScene(acts, nullptr, 480);
  auto offExplicit = blinkScene(acts, Json(false), 480);
  const FaceLayer* face = off->faceLayer(0);
  REQUIRE(face);
  for (int f = 1; f <= 480; ++f) {
    CHECK(off->faceState(0, f).blink == face->blink(f));
    CHECK(offExplicit->faceState(0, f).blink == face->blink(f));
  }
}

TEST_CASE("blink schedule: key beats, gaze shifts, short beats and the rhythm") {
  const int end = 24 * 120;
  auto free = blinkScene(Json::array(), nullptr, end);
  const std::vector<int> freeOn = onsets(*free, 1, end);
  REQUIRE(freeOn.size() > 10);
  // Key beats exactly where free blinks happen.
  Json beats = Json::array();
  for (size_t i = 0; i < freeOn.size(); i += 3) beats.push_back({{"start", freeOn[i] - 2}, {"end", freeOn[i] + 6}});
  auto keyed = blinkScene(Json::array(), Json{{"keyBeats", beats}}, end);
  for (const Json& b : beats)
    for (int f = b["start"].get<int>(); f <= b["end"].get<int>(); ++f) {
      CAPTURE(f);
      CHECK(keyed->faceState(0, f).blink == 0.0f);
    }
  // The rhythm stays: about as many blink events as without the schedule (doubles aside).
  const std::vector<int> keyedOn = onsets(*keyed, 1, end);
  CHECK(double(keyedOn.size()) >= 0.75 * double(freeOn.size()));

  // Gaze shifts every 40 frames (1.7 s): blinks land on them; short beats (12 frames, under 24) get one blink at most.
  Json acts = looks(end, 40);
  for (int f = 21; f < end; f += 40)  // a short beat: a gaze shift 12 frames after another
    acts.push_back({{"type", "look"}, {"character", "who"}, {"start", f + 9}, {"end", f + 18}, {"target", Json::array({0, 1.2, 1.5})}});
  auto shifts = blinkScene(acts, Json(true), end);
  const FaceLayer* face = shifts->faceLayer(0);
  BlinkSchedule bs;
  bs.enabled = true;
  const auto plan = face->blinkPlan(bs);
  REQUIRE(plan.size() > 10);
  size_t atShift = 0, rhythm = 0;
  for (const ScheduledBlink& b : plan) {
    if (b.kind == ScheduledBlink::Kind::Double) continue;
    (b.kind == ScheduledBlink::Kind::Shift ? atShift : rhythm) += 1;
  }
  MESSAGE("plan: " << plan.size() << " blinks, at shifts " << atShift << ", free rhythm " << rhythm);
  CHECK(atShift > 2 * rhythm);
  for (int f = 21; f + 18 < end; f += 40) {  // the short beat [f + 9, f + 18]
    int n = 0;
    for (const ScheduledBlink& b : plan) n += b.frame - 1 >= f + 9 && b.frame - 1 < f + 19;
    CAPTURE(f);
    CHECK(n <= 1);
  }
  // Deterministic and random access.
  for (int f = 1; f < 600; f += 7) CHECK(shifts->faceState(0, f).blink == shifts->faceState(0, f).blink);
}

// T-192: the automatic blink closes both eyes together. The face layer drives only the combined blink morph; the
// per-side lid controls (Blink.L / Blink.R, LeftEyeClosed / RightEyeClosed, EyeSquint.L / .R) stay equal on every
// frame unless an explicit track winks. A wink must still be possible.
namespace {
std::unique_ptr<SceneEvaluator> symmetryScene(const Json& actions, const Json& schedule, int end, bool wink) {
  Scene s;
  s.rate = FrameRate{24, 1};
  s.frameStart = 1;
  s.frameEnd = end;
  s.path = std::filesystem::path(PLUSH_SOURCE_DIR) / "tests/data/imported/scene.json";
  CharacterDesc cd;
  cd.name = "who";
  cd.asset = "girl_auburn_bun_glasses_m3/character.json";
  cd.life.enabled = true;
  s.characters.push_back(cd);
  s.actions = actions;
  s.blinkSchedule = schedule;
  if (wink) {  // an explicit wink: the right lid shut for frames 100-130, the left untouched
    s.animation.tracks["who/expr.Blink.R"].setKey({90, vec3(0), Interp::Linear});
    s.animation.tracks["who/expr.Blink.R"].setKey({100, vec3(1), Interp::Linear});
    s.animation.tracks["who/expr.Blink.R"].setKey({130, vec3(1), Interp::Linear});
    s.animation.tracks["who/expr.Blink.R"].setKey({140, vec3(0), Interp::Linear});
  }
  auto ev = std::make_unique<SceneEvaluator>();
  auto r = ev->load(s, EvalOptions{2.5f, 1.0f, false, 0});
  REQUIRE(r.has_value());
  return ev;
}

const char* const kSidePairs[][2] = {{"Blink.L", "Blink.R"}, {"LeftEyeClosed", "RightEyeClosed"}, {"EyeSquint.L", "EyeSquint.R"}};
}  // namespace

TEST_CASE("blink symmetry: automatic blinks close both eyes together (T-192)") {
  const int end = 24 * 60;
  const Json acts = looks(end, 40);
  for (const Json& schedule : {Json(), Json(true)}) {
    auto ev = symmetryScene(acts, schedule, end, false);
    int blinking = 0;
    for (int f = 1; f <= end; ++f) {
      CAPTURE(f);
      const float b = ev->morphControlWeight(0, "Blink", f);
      blinking += b > 0.5f;
      for (const auto& p : kSidePairs) CHECK(ev->morphControlWeight(0, p[0], f) == ev->morphControlWeight(0, p[1], f));
      // The automatic blink never leaks into one side only.
      CHECK(ev->morphControlWeight(0, "Blink.L", f) == doctest::Approx(0.0f));
      CHECK(ev->morphControlWeight(0, "Blink.R", f) == doctest::Approx(0.0f));
    }
    CHECK(blinking > 10);  // the scene does blink
  }
}

TEST_CASE("blink symmetry: a deliberate wink is still possible (T-192)") {
  const int end = 24 * 10;
  auto ev = symmetryScene(Json::array(), Json(), end, true);
  for (int f = 105; f <= 125; ++f) {
    CAPTURE(f);
    CHECK(ev->morphControlWeight(0, "Blink.R", f) > 0.99f);
    CHECK(ev->morphControlWeight(0, "Blink.L", f) == doctest::Approx(0.0f));
  }
}
