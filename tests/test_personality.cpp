// T-053: personality profiles (anim/personality.h). The reader (types, errors, limits, file lookup), the shipped
// profiles, and every layer that receives them: life (blinks, idle amplitude, head lag), face (rest offset,
// expression bias, mouth while watching), clip tempo with its speed limit, body mechanics, reach warnings; a
// character without a profile is unchanged.
#include <doctest/doctest.h>

#include <cmath>
#include <filesystem>
#include <fstream>
#include <memory>

#include "anim/personality.h"
#include "scene/scene.h"
#include "scene/shot_bake.h"

using namespace plush;
namespace fs = std::filesystem;

namespace {
const fs::path kRoot = PLUSH_SOURCE_DIR;
const char* const kBoy = "boy_yellow_hoodie_1.0.0/character.json";
const char* const kGirl = "girl_auburn_bun_glasses_m3/character.json";

Json profileJson(const char* body) {
  Json j = Json::parse(body);
  j["format"] = "plush.personality";
  j["version"] = 0;
  return j;
}
Scene baseScene(const fs::path& scenePath = kRoot / "tests/data/imported/scene.json", int end = 96) {
  Scene s;
  s.name = "personality test";
  s.path = scenePath;
  s.rate = FrameRate{24, 1};
  s.frameStart = 1;
  s.frameEnd = end;
  s.animPrinciples = false;
  return s;
}
CharacterDesc who(const std::string& asset, Json personality, bool life = false) {
  CharacterDesc c;
  c.name = "who";
  c.asset = asset;
  c.life.enabled = life;
  c.autoIdle = false;
  c.personality = std::move(personality);
  return c;
}
std::unique_ptr<SceneEvaluator> load(const Scene& scene) {
  auto ev = std::make_unique<SceneEvaluator>();
  auto r = ev->load(scene, EvalOptions{2.5f, 1.0f, false, 0});
  if (!r) FAIL(r.error().message);
  return ev;
}
std::unique_ptr<SceneEvaluator> one(const std::string& asset, Json personality, Json actions = Json::array(), bool life = false) {
  Scene s = baseScene();
  s.characters.push_back(who(asset, std::move(personality), life));
  s.actions = std::move(actions);
  return load(s);
}
bool hasWarning(const SceneEvaluator& ev, const char* text) {
  for (const auto& w : ev.warnings())
    if (w.find(text) != std::string::npos) return true;
  return false;
}
// A throw-away project: content/personality/<id>.json next to a scene whose characters point at the test packages.
struct TempProject {
  fs::path dir;
  explicit TempProject(const char* name) : dir(fs::temp_directory_path() / name) {
    fs::remove_all(dir);
    fs::create_directories(dir / "content/personality");
  }
  ~TempProject() { fs::remove_all(dir); }
  void write(const std::string& file, const Json& j) const { std::ofstream(dir / "content/personality" / file) << j.dump(1); }
  fs::path scene() const { return dir / "shot.scene.json"; }
  static std::string asset(const char* a) { return (kRoot / "tests/data/imported" / a).string(); }
};
}  // namespace

TEST_CASE("personality: the shipped profiles parse into typed parameters within their own limits") {
  const fs::path dir = kRoot / "content/personality";
  for (const char* id : {"boy_yellow_hoodie", "girl_auburn_bun_glasses", "girl_white_hair_blue_dress"}) {
    CAPTURE(id);
    CHECK_FALSE(fs::exists(dir / (std::string(id) + ".draft.json")));  // promoted
    auto p = loadPersonality(dir / (std::string(id) + ".json"));
    REQUIRE_MESSAGE(p.has_value(), (p ? "" : p.error().message));
    CHECK(p->id == id);
    CHECK(p->character == id);
    CHECK(p->profileVersion == "1.0.0");
    CHECK(p->limits.blinkIntervalFrames.has_value());
    CHECK(p->limits.blinkDurationFrames.has_value());
    CHECK(p->limits.reachFrames.has_value());
    CHECK(p->limits.holdFrames.has_value());
    CHECK(p->limits.actionSpeed.has_value());
    CHECK(p->limits.idleMotionMaxHPerFrame.has_value());
    CHECK(p->limits.gesturePeakSpeedMaxHPerFrame.has_value());
    CHECK(p->faceRestOffset.empty());  // every neutral cue is in the character models (owner decisions)
    PersonalityProfile copy = *p;
    CHECK(clampPersonalityToLimits(copy).empty());  // the data respects its own limits
  }
  auto boy = *loadPersonality(dir / "boy_yellow_hoodie.json");
  auto girl = *loadPersonality(dir / "girl_auburn_bun_glasses.json");
  auto third = *loadPersonality(dir / "girl_white_hair_blue_dress.json");
  // Boy: calm, low energy, heavy-lid long stares, never quicker than his base tempo.
  CHECK(*boy.blinkIntervalMean == doctest::Approx(30));
  CHECK(boy.limits.actionSpeed->hi == doctest::Approx(1.0f));
  CHECK(*boy.actionSpeed <= boy.limits.actionSpeed->hi);
  CHECK(boy.holdFrames->lo == doctest::Approx(24));
  CHECK(*boy.energyLevel < 0.5f);
  CHECK(*boy.lidRest == doctest::Approx(0.45f));
  CHECK_FALSE(boy.faceExpressionBias.count("Blink.L"));  // the heavy lid is modelled; surprise must open his eyes
  CHECK(boy.faceExpressionBias.at("MouthSmile") < 0);
  // Girl: brisk 8-10 f reaches, cheerful bias, hand to chin and pointing.
  CHECK(girl.reachFrames->lo == doctest::Approx(8));
  CHECK(girl.reachFrames->hi == doctest::Approx(10));
  CHECK(girl.faceExpressionBias.at("MouthSmile") > 0);
  CHECK(std::find(girl.gestures.begin(), girl.gestures.end(), "hand_to_chin_think") != girl.gestures.end());
  CHECK(girl.blinkOnActionChange);
  CHECK(*girl.longBlinkFrames == doctest::Approx(7));
  // Third: parted lips while watching, closed soft smile at rest, clasped hands.
  CHECK(third.faceWatching.at("JawOpen") > 0);
  CHECK(third.defaultMouth == "closed_soft_smile");
  CHECK(std::find(third.restHands.begin(), third.restHands.end(), "hands_clasped_under_chin") != third.restHands.end());
}

TEST_CASE("personality: reader errors, missing parameters and clamping into limits") {
  CHECK_FALSE(personalityFromJson(Json::parse(R"({"format": "plush.emotion", "version": 0})")).has_value());
  CHECK_FALSE(personalityFromJson(Json::parse(R"({"format": "plush.personality", "version": 1})")).has_value());
  CHECK_FALSE(personalityFromJson(profileJson(R"({"tempo": {"action_speed": {"value": "fast"}}})")).has_value());
  CHECK_FALSE(personalityFromJson(profileJson(R"({"tempo": {"action_speed": {"value": 0}}})")).has_value());
  CHECK_FALSE(personalityFromJson(profileJson(R"({"tempo": {"reach_frames": {"value": [12, 8]}}})")).has_value());
  CHECK_FALSE(personalityFromJson(profileJson(R"({"face": {"expression_bias": {"value": {"MouthSmile": 1.5}}}})")).has_value());
  CHECK_FALSE(personalityFromJson(profileJson(R"({"limits": {"action_speed": {"value": [0, 1]}}})")).has_value());
  // Missing = neutral (no optional set); plain values work as records.
  auto empty = personalityFromJson(profileJson("{}"));
  REQUIRE(empty.has_value());
  CHECK_FALSE(empty->actionSpeed.has_value());
  CHECK_FALSE(empty->blinkIntervalMean.has_value());
  CHECK(empty->faceExpressionBias.empty());
  auto plain = personalityFromJson(profileJson(R"({"tempo": {"action_speed": 1.2, "reach_frames": 9},
                                                   "blink": {"interval_frames": [40, 60]}})"));
  REQUIRE(plain.has_value());
  CHECK(*plain->actionSpeed == doctest::Approx(1.2f));
  CHECK(plain->reachFrames->lo == doctest::Approx(9));
  CHECK(*plain->blinkIntervalMean == doctest::Approx(50));
  // Limits clamp the profile's own values, one warning each.
  auto p = personalityFromJson(profileJson(R"({"tempo": {"action_speed": {"value": 2.0}, "reach_frames": {"value": [4, 30]}},
      "blink": {"interval_frames": {"value": {"mean": 200, "min": 20, "max": 300}}},
      "face": {"expression_bias": {"value": {"MouthSmile": 0.6}}},
      "limits": {"action_speed": {"value": [0.8, 1.0]}, "reach_frames": {"value": [8, 12]},
                 "blink_interval_frames": {"value": [20, 96]}, "face_offset_max": {"value": 0.3}}})"), "x");
  REQUIRE(p.has_value());
  auto w = clampPersonalityToLimits(*p);
  CHECK(w.size() == 5);  // speed, reach, blink mean, blink range, face offset
  CHECK(*p->actionSpeed == doctest::Approx(1.0f));
  CHECK(p->reachFrames->lo == doctest::Approx(8));
  CHECK(p->reachFrames->hi == doctest::Approx(12));
  CHECK(*p->blinkIntervalMean == doctest::Approx(96));
  CHECK(p->faceExpressionBias.at("MouthSmile") == doctest::Approx(0.3f));
}

TEST_CASE("personality: profile files are found by walking up; drafts are a fallback; ids are names only") {
  TempProject t("plush_t053_lookup");
  t.write("a.draft.json", profileJson("{}"));
  t.write("b.json", profileJson("{}"));
  t.write("b.draft.json", profileJson(R"({"tempo": {"action_speed": 3}})"));
  fs::create_directories(t.dir / "shots/deep");
  CHECK(findPersonalityFile(t.dir / "shots/deep/x.scene.json", "a").filename() == "a.draft.json");
  CHECK(findPersonalityFile(t.dir / "shots/deep/x.scene.json", "b").filename() == "b.json");
  CHECK(findPersonalityFile(t.dir / "shots", "missing").empty());
  CHECK(findPersonalityFile(t.dir / "shots", "../b").empty());
  CHECK(findPersonalityFile({}, "b").empty());
  auto b = loadPersonality(findPersonalityFile(t.dir, "b"));
  REQUIRE(b.has_value());
  CHECK(b->id == "b");
  CHECK_FALSE(b->actionSpeed.has_value());
}

TEST_CASE("personality: absent or false keeps the character exactly as before; scene files round-trip it") {
  const Json actions = Json::parse(R"([{"type": "clip", "character": "who", "clip": "point", "start": 10},
                                       {"type": "expression", "character": "who", "name": "smile", "start": 20, "end": 50}])");
  auto none = one(kBoy, Json(), actions, true);
  auto off = one(kBoy, false, actions, true);
  CHECK(none->personality(0) == nullptr);
  CHECK(off->personality(0) == nullptr);
  CHECK(none->clipTempo(0) == 1.0);
  for (double f : {1.0, 15.0, 33.0, 70.0}) {
    auto a = none->characterGlobals(0, f), b = off->characterGlobals(0, f);
    REQUIRE(a.size() == b.size());
    for (size_t i = 0; i < a.size(); ++i) CHECK(a[i] == b[i]);
  }
  CHECK(bakeShot(*none, 1, 96) == bakeShot(*off, 1, 96));  // bones and morph weights, every frame
  Scene s = baseScene();
  s.characters.push_back(who(kBoy, "boy_yellow_hoodie"));
  Json saved = sceneToJson(s);
  CHECK(saved["characters"][0]["personality"] == "boy_yellow_hoodie");
  Scene noProfile = baseScene();
  noProfile.characters.push_back(who(kBoy, Json()));
  CHECK_FALSE(sceneToJson(noProfile)["characters"][0].contains("personality"));
}

TEST_CASE("personality: the life layer receives blink rhythm and shape, idle amplitude and head lag") {
  auto plain = one(kBoy, Json(), Json::array(), true);
  auto boy = one(kBoy, "boy_yellow_hoodie", Json::array(), true);
  auto girl = one(kGirl, "girl_auburn_bun_glasses", Json::array(), true);
  CHECK(boy->warnings().empty());
  CHECK(girl->warnings().empty());
  const LifeParams base = plain->lifeParams(0), lb = boy->lifeParams(0), lg = girl->lifeParams(0);
  CHECK(lb.blinkInterval == doctest::Approx(30.0f / 24.0f));
  CHECK(lg.blinkInterval == doctest::Approx(33.0f / 24.0f));
  // Whole blink = middle of duration_frames, shut = middle of closed_frames, close faster than open.
  CHECK((lb.blinkClose + lb.blinkHold + lb.blinkOpen) * 24.0f == doctest::Approx(5.0f));
  CHECK(lb.blinkHold * 24.0f == doctest::Approx(2.5f));
  CHECK(lb.blinkClose < lb.blinkOpen);
  CHECK((lg.blinkClose + lg.blinkHold + lg.blinkOpen) * 24.0f == doctest::Approx(4.0f));
  // Idle amplitude relative to the shared neutral (0.004 H): boy 0.003 -> 0.75, girl 0.006 -> 1.5.
  CHECK(lb.sway == doctest::Approx(base.sway * 0.75f));
  CHECK(lb.headDrift == doctest::Approx(base.headDrift * 0.75f));
  CHECK(lb.breathing == doctest::Approx(base.breathing * std::sqrt(0.75f)));
  CHECK(lg.sway == doctest::Approx(base.sway * 1.5f));
  // Eyes lead the head by 2-4 f.
  CHECK(lb.headLagSec == doctest::Approx(3.0f / 24.0f));
  // The blinks follow: more blinks for the boy (mean 30 f) than with the shared 3.6 s interval.
  auto count = [](const SceneEvaluator& ev) {
    int n = 0;
    bool closed = false;
    for (int f = 1; f <= 96 * 3; ++f) {
      const float b = ev.morphControlWeight(0, "Blink", f);
      if (b > 0.5f && !closed) ++n;
      closed = b > 0.5f;
    }
    return n;
  };
  Scene longer = baseScene(kRoot / "tests/data/imported/scene.json", 96 * 3);
  longer.characters.push_back(who(kBoy, Json(), true));
  auto plainLong = load(longer);
  longer.characters[0].personality = "boy_yellow_hoodie";
  auto boyLong = load(longer);
  MESSAGE("blinks in 12 s: shared " << count(*plainLong) << ", boy profile " << count(*boyLong));
  CHECK(count(*boyLong) > count(*plainLong));
  // An explicit scene blink interval wins but is kept inside the profile's limits (with a warning).
  Scene slow = baseScene();
  slow.characters.push_back(who(kBoy, "boy_yellow_hoodie", true));
  slow.characters[0].life.blinkInterval = 10.0f;
  slow.characters[0].life.blinkIntervalSet = true;
  auto clamped = load(slow);
  CHECK(clamped->lifeParams(0).blinkInterval == doctest::Approx(96.0f / 24.0f));
  CHECK(hasWarning(*clamped, "blinkInterval"));
}

TEST_CASE("personality: face rest offset, expression bias and the mouth while watching") {
  // Shipped profile on the girl package: the cheerful bias lifts her smile while an expression plays, nothing at rest.
  const Json frown = Json::parse(R"([{"type": "expression", "character": "who", "name": "frown", "start": 20, "end": 60}])");
  auto plain = one(kGirl, Json(), frown);
  auto girl = one(kGirl, "girl_auburn_bun_glasses", frown);
  for (double f : {1.0, 5.0})
    for (const char* m : {"MouthSmile", "Frown", "BrowDown"})
      CHECK(girl->morphControlWeight(0, m, f) == plain->morphControlWeight(0, m, f));
  CHECK(girl->morphControlWeight(0, "MouthSmile", 40) == doctest::Approx(plain->morphControlWeight(0, "MouthSmile", 40) + 0.2f));
  // MouthFrown -0.2 lands on her MouthFrown control (the first alias she has), not on the "frown" expression's morph.
  CHECK(girl->morphControlWeight(0, "Frown", 40) == plain->morphControlWeight(0, "Frown", 40));
  CHECK(girl->morphControlWeight(0, "MouthFrown", 40) == doctest::Approx(0.0f));
  // The bake (what Blender renders) carries the same weights.
  const Json bake = bakeShot(*girl, 40, 40);
  const auto& names = bake["characters"][0]["morphs"];
  size_t k = 0;
  while (k < names.size() && names[k] != "MouthSmile") ++k;
  REQUIRE(k < names.size());
  const Json& ch = bake["frame_data"][0]["characters"];
  CHECK(ch.begin()->at("morphs")[k].get<float>() == doctest::Approx(girl->morphControlWeight(0, "MouthSmile", 40)));

  // Synthetic profile: a rest offset (aliases: BrowDown) and the mouth while watching (look action).
  TempProject t("plush_t053_face");
  t.write("synthetic.json", profileJson(R"({"face": {"rest_offset": {"value": {"BrowDown": 0.25}},
      "watching_mouth": {"value": {"JawOpen": 0.3}}}, "limits": {"face_offset_max": {"value": 0.3}}})"));
  Scene s = baseScene(t.scene());
  s.characters.push_back(who(TempProject::asset(kGirl), "synthetic"));
  s.actions = Json::parse(R"([{"type": "look", "character": "who", "start": 30, "end": 60, "target": [0, 1.0, 1.0]}])");
  auto syn = load(s);
  REQUIRE(syn->personality(0) != nullptr);
  CHECK(syn->morphControlWeight(0, "BrowDown", 1) == doctest::Approx(0.25f));
  CHECK(syn->morphControlWeight(0, "JawOpen", 10) == doctest::Approx(0.0f));
  CHECK(syn->morphControlWeight(0, "JawOpen", 45) == doctest::Approx(0.3f));
  CHECK(syn->morphControlWeight(0, "JawOpen", 27) == doctest::Approx(0.15f));  // 6-frame ramp in
  CHECK(syn->morphControlWeight(0, "JawOpen", 80) == doctest::Approx(0.0f));
}

TEST_CASE("personality: clip tempo for gestures, kept inside the profile's speed limits") {
  // The girl's gestures play 1.1 x faster (brisk); the boy's never faster than his base tempo (limit 1.0).
  auto girl = one(kGirl, "girl_auburn_bun_glasses");
  auto boy = one(kBoy, "boy_yellow_hoodie");
  CHECK(girl->clipTempo(0) == doctest::Approx(1.1));
  CHECK(boy->clipTempo(0) == doctest::Approx(1.0));
  auto clip = [](double speed) {
    return Json::array({{{"type", "clip"}, {"character", "who"}, {"clip", "wave"}, {"start", 10}, {"end", 70}, {"speed", speed},
                         {"blendIn", 6}, {"blendOut", 6}}});
  };
  // Boy: a wave authored at speed 1.5 plays at 1.0 (the limit), the pose of the same clip at speed 1.0.
  auto boyFast = one(kBoy, "boy_yellow_hoodie", clip(1.5));
  auto plain10 = one(kBoy, Json(), clip(1.0));
  auto plain15 = one(kBoy, Json(), clip(1.5));
  float diff15 = 0;
  for (double f : {14.0, 25.0, 40.0}) {
    auto a = boyFast->characterGlobals(0, f), b = plain10->characterGlobals(0, f), c = plain15->characterGlobals(0, f);
    for (size_t i = 0; i < a.size(); ++i) {
      CHECK(glm::distance(vec3(a[i][3]), vec3(b[i][3])) < 1e-5f);
      diff15 = std::max(diff15, glm::distance(vec3(a[i][3]), vec3(c[i][3])));
    }
  }
  CHECK(diff15 > 1e-3f);
  // Girl: speed 1.0 authored plays like speed 1.1 (her tempo).
  auto girl10 = one(kGirl, "girl_auburn_bun_glasses", clip(1.0));
  auto plain11 = one(kGirl, Json(), clip(1.1));
  for (double f : {14.0, 30.0, 45.0}) {
    auto a = girl10->characterGlobals(0, f), b = plain11->characterGlobals(0, f);
    for (size_t i = 0; i < a.size(); ++i) CHECK(glm::distance(vec3(a[i][3]), vec3(b[i][3])) < 1e-5f);
  }
}

TEST_CASE("personality: body mechanics take the character's profile unless they name their own") {
  Scene s = baseScene();
  s.characters.push_back(who(kBoy, "boy_yellow_hoodie"));
  s.characters[0].bodyMechanics = true;
  auto viaCharacter = load(s);
  s.characters[0].personality = Json();
  s.characters[0].bodyMechanics = Json::parse(R"({"personality": "boy_yellow_hoodie"})");
  auto viaBody = load(s);
  const auto& a = *viaCharacter->bodyMechanicsParams(0);
  const auto& b = *viaBody->bodyMechanicsParams(0);
  CHECK(a.slouch == b.slouch);
  CHECK(a.settleFrames == b.settleFrames);
  CHECK(a.lagFrames == b.lagFrames);
  CHECK(a.energy == b.energy);
  CHECK(a.slouch == doctest::Approx(0.4f));
  // The body mechanics' own profile wins over the character's.
  s.characters[0].personality = "boy_yellow_hoodie";
  s.characters[0].bodyMechanics = Json::parse(R"({"personality": "girl_auburn_bun_glasses"})");
  auto own = load(s);
  CHECK(own->bodyMechanicsParams(0)->slouch == doctest::Approx(0.0f));
  // The JSON entry point reads through the same reader (section-only objects accepted).
  BodyMechanicsParams p;
  applyPersonalityToBodyMechanics(p, Json::parse(R"({"posture": {"slouch": {"value": 0.3}}})"));
  CHECK(p.slouch == doctest::Approx(0.3f));
}

TEST_CASE("personality: reach timing outside the limits, bad values and unknown profiles are reported") {
  // Boy reach limits 10-16 f: a 6-frame reach is flagged (actions keep their timing), a 12-frame one is not.
  auto quick = one(kBoy, "boy_yellow_hoodie",
                   Json::parse(R"([{"type": "touch", "character": "who", "hand": "R", "start": 20, "contact": 26, "end": 40,
                                    "target": [0.1, 0.8, 0.3]}])"));
  CHECK(hasWarning(*quick, "reach limits"));
  auto calm = one(kBoy, "boy_yellow_hoodie",
                  Json::parse(R"([{"type": "touch", "character": "who", "hand": "R", "start": 20, "contact": 32, "end": 50,
                                   "target": [0.1, 0.8, 0.3]}])"));
  CHECK_FALSE(hasWarning(*calm, "reach limits"));
  // Unknown profile: one warning, no profile.
  auto missing = one(kBoy, "no_such_profile");
  CHECK(missing->personality(0) == nullptr);
  CHECK(hasWarning(*missing, "no_such_profile"));
  // A profile whose values exceed its own limits is clamped with a warning.
  TempProject t("plush_t053_limits");
  t.write("wild.json", profileJson(R"({"tempo": {"action_speed": {"value": 1.8}},
                                       "limits": {"action_speed": {"value": [0.8, 1.2]}}})"));
  Scene s = baseScene(t.scene());
  s.characters.push_back(who(TempProject::asset(kBoy), "wild"));
  auto wild = load(s);
  CHECK(wild->clipTempo(0) == doctest::Approx(1.2));
  CHECK(hasWarning(*wild, "clamped"));
  // Scene files: the personality must be an id or false.
  const fs::path bad = t.dir / "bad.scene.json";
  std::ofstream(bad) << R"({"name": "x", "frameStart": 1, "frameEnd": 2, "characters": [{"name": "a", "asset": "a.json", "personality": 3}]})";
  CHECK_FALSE(loadScene(bad).has_value());
}
