// T-104: calibrated timing profile (anim/personality.h TimingProfile, content/timing/*.timing.json), its per-character
// scaling from the personality profiles, the scene's opt-in "timing" key and the interaction defaults it sets.
#include <doctest/doctest.h>

#include <filesystem>
#include <fstream>
#include <memory>

#include "anim/personality.h"
#include "scene/asset_library.h"
#include "scene/scene.h"
#include "scene/shot_bake.h"

using namespace plush;
namespace fs = std::filesystem;

namespace {

const fs::path kRoot = PLUSH_SOURCE_DIR;
const char* kBoy = "boy_yellow_hoodie_1.0.0/character.json";

TimingProfile calibrated() {
  auto t = loadTimingProfile(kRoot / "content/timing/calibrated.timing.json");
  if (!t) FAIL(t.error().message);
  return *t;
}

PersonalityProfile profileOf(const char* id) {
  auto p = loadPersonality(kRoot / "content/personality" / (std::string(id) + ".json"));
  if (!p) FAIL(p.error().message);
  return *p;
}

// One character picking up a felt cup in front of its right shoulder (as tests/test_interaction.cpp), the grasp
// written without its contact frame, so the default applies.
std::unique_ptr<SceneEvaluator> pickUp(const Json& timing, int contact = 0) {
  Scene s;
  s.name = "timing test";
  s.path = kRoot / "tests/data/imported/scene.json";
  s.rate = FrameRate{24, 1};
  s.frameStart = 1;
  s.frameEnd = 48;
  s.timing = timing;
  CharacterDesc c;
  c.name = "actor";
  c.asset = kBoy;
  s.characters.push_back(c);
  auto probe = std::make_unique<SceneEvaluator>();
  if (auto r = probe->load(s, EvalOptions{2.5f, 1.0f, false, 0}); !r) FAIL(r.error().message);
  auto bone = [&](const char* name) {
    const int b = probe->characters()[0].asset.skeleton.find(name);
    REQUIRE(b >= 0);
    return vec3(probe->characterGlobals(0, 1)[size_t(b)][3]);
  };
  const vec3 shoulder = bone("upperArm.R"), elbow = bone("forearm.R");
  const float arm = glm::distance(shoulder, elbow) + glm::distance(elbow, bone("hand.R"));
  const PropAsset asset = loadAsset(kRoot / "content/assets/felt_cup.asset.json").value();
  const mat4 rot = assetTransformMatrix({vec3(0), vec3(0, 180, 0), vec3(1)});
  PropDesc cup;
  cup.name = "cup";
  cup.id = "prop.felt_cup";
  cup.transform.translation = shoulder + vec3(0.04f, -0.45f, 0.85f) * arm - vec3(rot * vec4(asset.sockets.at("grip").translation, 0));
  cup.transform.rotationDeg = {0, 180, 0};
  s.props.push_back(cup);
  s.actions = Json::parse(R"([{"type": "grasp", "character": "actor", "hand": "R", "prop": "cup", "start": 5}])");
  if (contact) s.actions[0]["contact"] = contact;
  auto ev = std::make_unique<SceneEvaluator>();
  if (auto r = ev->load(s, EvalOptions{2.5f, 1.0f, false, 0}); !r) FAIL(r.error().message);
  return ev;
}

}  // namespace

TEST_CASE("timing profile: the calibrated profile loads its beats and travel from the reference table") {
  const TimingProfile t = calibrated();
  CHECK(t.name == "calibrated");
  for (const char* b : {"reach", "anticipation", "settle", "hold", "shared_hold", "place", "release", "return", "reaction_delay"})
    CHECK(t.beats.count(b) == 1);
  // Every calibrated beat is inside its reference range (content/timing/reference_timing.json).
  auto ref = parseJsonFile(kRoot / "content/timing/reference_timing.json");
  REQUIRE(ref);
  for (const auto& [beat, frames] : t.beats) {
    INFO(beat);
    REQUIRE((*ref)["beats"].contains(beat));
    const auto& r = (*ref)["beats"][beat]["frames"];
    CHECK(frames >= r[0].get<float>());
    CHECK(frames <= r[1].get<float>());
  }
  CHECK(t.frames("reach", 14) == 16);
  CHECK(t.frames("no_such_beat", 14) == 14);  // fallback: the shared default
  // Scale-aware travel: the same distance takes longer for a shorter arm, inside [min, max].
  CHECK(t.travelFrames(0.2057, 0.18) == 26);  // e907: her reach to the cup (18 cm arm)
  CHECK(t.travelFrames(0.2057, 0.27) == 17);  // the same distance with his 27 cm arm
  CHECK(t.travelFrames(0.01, 0.27) == 10);    // a tiny carry still takes the minimum
  CHECK(t.travelFrames(2.0, 0.18) == 28);     // and a long one the maximum
  CHECK(findTimingProfileFile(kRoot / "episodes/e907_exchange/shots/s010/shot.scene.json", "calibrated") ==
        kRoot / "content/timing/calibrated.timing.json");
  CHECK(findTimingProfileFile(kRoot, "../calibrated").empty());
  CHECK(findTimingProfileFile(kRoot, "nonexistent").empty());
}

TEST_CASE("timing profile: personality tempo scales beats (boy slower, girl quicker with longer holds)") {
  const TimingProfile t = calibrated();
  const PersonalityProfile boy = profileOf("boy_yellow_hoodie"), girl = profileOf("girl_auburn_bun_glasses");
  REQUIRE(boy.beatScale);
  REQUIRE(girl.holdScale);
  CHECK(*boy.beatScale > 1.0f);
  CHECK(*girl.beatScale < 1.0f);
  CHECK(*girl.holdScale > 1.0f);
  CHECK(t.frames("reach", 14, &boy) == 19);    // 16 x 1.2
  CHECK(t.frames("reach", 14, &girl) == 14);   // 16 x 0.85
  CHECK(t.frames("hold", 16, &boy) == 16);     // holds: x hold_scale 1.0
  CHECK(t.frames("hold", 16, &girl) == 20);    // 16 x 1.25
  CHECK(t.frames("release", 12, &boy) == 17);  // 14 x 1.2
  CHECK(t.travelFrames(0.2057, 0.18, &girl) == 22);  // 26 x 0.85: still clear of her vest (T-104 sweep)
  CHECK(t.travelFrames(0.01, 0.27, &girl) == 10);    // the minimum holds after scaling
  // The new tempo fields do not change anything else the profile resolves to.
  CHECK(boy.reachFrames.has_value());
  PersonalityProfile copy = boy;
  CHECK(clampPersonalityToLimits(copy).empty());
}

TEST_CASE("timing profile: reader errors") {
  CHECK_FALSE(timingProfileFromJson(Json::parse(R"({"format": "plush.personality", "version": 1})")));
  CHECK_FALSE(timingProfileFromJson(Json::parse(R"({"format": "plush.timing_profile", "version": 2})")));
  CHECK_FALSE(timingProfileFromJson(Json::parse(R"({"format": "plush.timing_profile", "version": 1, "beats": {"reach": 0}})")));
  CHECK_FALSE(timingProfileFromJson(Json::parse(R"({"format": "plush.timing_profile", "version": 1, "beats": {"reach": "x"}})")));
  CHECK_FALSE(timingProfileFromJson(
      Json::parse(R"({"format": "plush.timing_profile", "version": 1, "travel": {"min_frames": 30, "max_frames": 20}})")));
  auto ok = timingProfileFromJson(
      Json::parse(R"({"format": "plush.timing_profile", "version": 1, "beats": {"reach": 12, "hold": {"value": 20}}})"), "t");
  REQUIRE(ok);
  CHECK(ok->frames("hold", 1) == 20);
  CHECK(ok->armLengthsPerFrame == doctest::Approx(0.06f));  // built-in travel defaults
  auto bad = personalityFromJson(Json::parse(R"({"format": "plush.personality", "version": 0, "tempo": {"beat_scale": 0}})"));
  CHECK_FALSE(bad);
}

TEST_CASE("timing profile: the scene key is opt-in, checked and saved as written") {
  const fs::path dir = fs::temp_directory_path() / "plush_t104_timing";
  fs::create_directories(dir);
  auto write = [&](const char* name, const std::string& text) {
    std::ofstream(dir / name) << text;
    return dir / name;
  };
  const std::string head = R"({"format": "plush.scene", "version": 1, "frameRate": [24, 1], "frameStart": 1, "frameEnd": 10)";
  CHECK_FALSE(loadScene(write("bad.scene.json", head + R"(, "timing": 3})")));
  CHECK_FALSE(loadScene(write("empty.scene.json", head + R"(, "timing": ""})")));
  auto none = loadScene(write("none.scene.json", head + "}"));
  REQUIRE(none);
  CHECK(none->timing.is_null());
  CHECK_FALSE(sceneToJson(*none).contains("timing"));
  auto on = loadScene(write("on.scene.json", head + R"(, "timing": "calibrated"})"));
  REQUIRE(on);
  CHECK(sceneToJson(*on)["timing"] == "calibrated");
  fs::remove_all(dir);
}

TEST_CASE("timing profile: interaction defaults follow the profile; without it the shot is bit for bit as before") {
  auto shared = pickUp(Json());
  auto timed = pickUp("calibrated");
  for (const auto& w : timed->warnings()) MESSAGE(w);
  CHECK(timed->warnings().empty());
  const Clip& a = shared->scene().animation;
  const Clip& b = timed->scene().animation;
  // Shared default: contact at start + 14 (f19); calibrated: start + 16 (f21).
  CHECK(a.evaluate("actor/hand.R.grasp.weight", 19, vec3(0)).x == doctest::Approx(1.0f));
  CHECK(b.evaluate("actor/hand.R.grasp.weight", 19, vec3(0)).x < 0.999f);
  CHECK(b.evaluate("actor/hand.R.grasp.weight", 21, vec3(0)).x == doctest::Approx(1.0f));
  // Frames written in the action win over the profile: the same bake with and without it.
  CHECK(bakeShot(*pickUp("calibrated", 19), 1, 48)["frame_data"] == bakeShot(*pickUp(Json(), 19), 1, 48)["frame_data"]);
  // An unknown profile is a load error (the scene asked for it explicitly).
  Scene missing = shared->scene();
  missing.timing = "no_such_profile";
  for (auto& p : missing.props) p.parentSwitch.clear();  // as authored (the evaluator added the grasp's switch)
  SceneEvaluator ev;
  auto r = ev.load(missing, EvalOptions{2.5f, 1.0f, false, 0});
  REQUIRE_FALSE(r);
  CHECK(r.error().message.find("no_such_profile") != std::string::npos);
}
