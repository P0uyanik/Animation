// Facial layer (T-046, scene/face_layer.h): the living face on both imported characters and the engine-built
// mannequin. Continuity per control, blink timing statistics, emotion transitions, eye darts, skipped controls, the
// life switch and the neck gaze assist.
#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <numeric>

#include "geom/json_io.h"
#include "scene/emotion.h"
#include "scene/face_layer.h"
#include "scene/scene.h"

using namespace plush;

namespace {
const char* const kGirl = "girl_auburn_bun_glasses_m3";
const char* const kBoy = "boy_yellow_hoodie_1.0.0";

// One character (imported package name, or "" for the engine-built mannequin) with life on, `actions`, frames 1..end.
std::unique_ptr<SceneEvaluator> faceScene(const std::string& package, const Json& actions, int end, bool life = true) {
  Scene s;
  s.rate = FrameRate{30, 1};
  s.frameStart = 1;
  s.frameEnd = end;
  CharacterDesc cd;
  cd.name = "who";
  if (package.empty()) {
    s.path = std::filesystem::path(PLUSH_SOURCE_DIR) / "content/scenes/unit_test.scene.json";
    cd.asset = "../characters/boy_dark_hair.character.json";
  } else {
    s.path = std::filesystem::path(PLUSH_SOURCE_DIR) / "tests/data/imported/scene.json";
    cd.asset = package + "/character.json";
  }
  cd.life.enabled = life;
  s.characters.push_back(cd);
  s.actions = actions;
  auto ev = std::make_unique<SceneEvaluator>();
  auto r = ev->load(s, EvalOptions{2.5f, 1.0f, false, 0});
  REQUIRE(r.has_value());
  return ev;
}

// idle -> happy -> surprised -> sad (each starts while the previous one releases) and a look in the middle.
Json actingActions() {
  return Json::parse(R"([
    {"type": "emotion", "character": "who", "name": "happy", "start": 30},
    {"type": "emotion", "character": "who", "name": "surprised", "start": 95},
    {"type": "look", "character": "who", "start": 120, "end": 200, "target": [0.6, 0.9, 1.5]},
    {"type": "emotion", "character": "who", "name": "sad", "start": 150}])");
}

std::vector<std::string> morphNames(const SceneEvaluator& ev) {
  std::vector<std::string> out;
  for (const auto& mt : ev.characters()[0].rig.morphs)
    if (std::find(out.begin(), out.end(), mt.name) == out.end() && mt.name.find('@') == std::string::npos) out.push_back(mt.name);
  return out;
}
std::string blinkControl(const SceneEvaluator& ev) {
  auto it = ev.characters()[0].asset.expressionMap.find("blink");
  return it == ev.characters()[0].asset.expressionMap.end() ? "" : it->second;
}
float angleDeg(const quat& a, const quat& b) {
  return glm::degrees(2.0f * std::acos(std::clamp(std::abs(glm::dot(glm::normalize(a), glm::normalize(b))), 0.0f, 1.0f)));
}
int bone(const SceneEvaluator& ev, const char* name) { return ev.characters()[0].asset.skeleton.find(name); }
quat eyeLocal(const SceneEvaluator& ev, double f) {
  Pose p;
  ev.characterGlobals(0, f, &p);
  const int e = bone(ev, "eye.L");
  return e >= 0 ? p.local[size_t(e)] : quat(1, 0, 0, 0);
}

// Blink onsets (closure crossing 0.9 upward) of a face layer over [a, b) frames.
std::vector<double> blinkOnsets(const FaceLayer& face, int a, int b) {
  std::vector<double> out;
  bool closed = false;
  for (int f = a; f < b; ++f) {
    const bool c = face.blink(f) > 0.9f;
    if (c && !closed) out.push_back(f);
    closed = c;
  }
  return out;
}
}  // namespace

TEST_CASE("face library and emotion faceMotion sections parse") {
  const auto root = std::filesystem::path(PLUSH_SOURCE_DIR) / "content/emotions";
  auto j = parseJsonFile(root / "face_motion.json");
  REQUIRE(j.has_value());
  auto lib = faceLibraryFromJson(*j);
  REQUIRE(lib.has_value());
  for (const char* ch : {"browUp", "browSad", "eyeWide", "jawOpen", "mouthUp", "mouthDown"}) CHECK(lib->channels.count(ch));
  int withMotion = 0;
  for (const auto& e : std::filesystem::directory_iterator(root)) {
    const std::string n = e.path().filename().string();
    if (n.size() < 13 || n.substr(n.size() - 13) != ".emotion.json") continue;
    auto ej = parseJsonFile(e.path());
    REQUIRE(ej.has_value());
    auto def = emotionFromJson(*ej);
    REQUIRE_MESSAGE(def.has_value(), n);
    withMotion += def->hasFaceMotion ? 1 : 0;
    const Json variants = ej->value("variants", Json::object());
    for (const auto& [variant, patch] : variants.items()) {
      auto v = emotionFromJson(*ej, variant);
      REQUIRE_MESSAGE(v.has_value(), n << "/" << variant);
    }
  }
  CHECK(withMotion >= 8);
  // A variant patches the base section (laugh drops the squint channel, keeps the brows).
  auto happy = parseJsonFile(root / "happy.emotion.json");
  auto laugh = emotionFromJson(*happy, "laugh");
  REQUIRE(laugh.has_value());
  CHECK(laugh->faceMotion.channels.count("eyeSquint") == 0);
  CHECK(laugh->faceMotion.channels.at("browUp") == doctest::Approx(0.3f));
  // Malformed sections are rejected with a message.
  CHECK_FALSE(faceMotionFromJson(Json::parse(R"({"blinkRate": "fast"})")).has_value());
  CHECK_FALSE(faceMotionFromJson(Json::parse(R"({"gazeBiasDeg": [1]})")).has_value());
  CHECK_FALSE(faceLibraryFromJson(Json::parse(R"({"format": "plush.face_motion", "version": 2})")).has_value());
}

TEST_CASE("facial layer: per-control continuity on both characters and the mannequin") {
  for (const std::string& pkg : {std::string(kGirl), std::string(kBoy), std::string()}) {
    CAPTURE(pkg);
    auto ev = faceScene(pkg, actingActions(), 260);
    REQUIRE(ev->faceActive(0));
    const auto names = morphNames(*ev);
    const std::string blink = blinkControl(*ev);
    float maxStep = 0, maxBlinkStep = 0, maxEyeStep = 0;
    float lo = 1, hi = 0;
    std::string worst;
    std::vector<float> prev;
    quat prevEye = eyeLocal(*ev, 0);
    for (int f = 1; f <= 260; ++f) {
      std::vector<float> w;
      for (const auto& m : names) w.push_back(ev->morphControlWeight(0, m, f));
      for (size_t i = 0; i < w.size() && !prev.empty(); ++i) {
        const float d = std::abs(w[i] - prev[i]);
        const bool isBlink = names[i] == blink || names[i].rfind("Blink", 0) == 0;
        if (isBlink) maxBlinkStep = std::max(maxBlinkStep, d);
        else if (d > maxStep) maxStep = d, worst = names[i] + " @" + std::to_string(f);
      }
      for (float x : w) lo = std::min(lo, x), hi = std::max(hi, x);
      prev = std::move(w);
      const quat e = eyeLocal(*ev, f);
      if (f != 120)  // the look itself jumps the eyes to its target at its start (eyes lead; not a face pop)
        maxEyeStep = std::max(maxEyeStep, angleDeg(e, prevEye));
      prevEye = e;
    }
    MESSAGE("max change per frame: controls " << maxStep << " (" << worst << "), blink " << maxBlinkStep << ", eyes "
                                              << maxEyeStep << " deg; range [" << lo << ", " << hi << "]");
    CHECK(maxStep <= 0.15f);       // expressions ease in and out: no pops
    CHECK(maxBlinkStep <= 0.8f);   // a blink closes in ~2-3 frames (smooth)
    CHECK(maxEyeStep <= 8.0f);     // eye darts are fast but small
    CHECK(lo >= 0.0f);
    CHECK(hi <= 1.0f);
    if (!names.empty()) CHECK(hi > 0.5f);  // the face does act
  }
}

TEST_CASE("facial layer: blink timing statistics and emotion-dependent rate") {
  for (const char* pkg : {kGirl, kBoy}) {
    CAPTURE(pkg);
    auto ev = faceScene(pkg, Json::array(), 3600);
    const FaceLayer* face = ev->faceLayer(0);
    REQUIRE(face);
    const LifeParams life = ev->lifeParams(0);
    const auto on = blinkOnsets(*face, 1, 3600);  // two minutes, neutral
    REQUIRE(on.size() > 10);
    std::vector<double> gaps;
    int doubles = 0;
    for (size_t i = 1; i < on.size(); ++i) {
      const double g = (on[i] - on[i - 1]) / 30.0;
      if (g < 0.6) ++doubles;  // the second blink of a double blink
      else gaps.push_back(g);
    }
    const double mean = std::accumulate(gaps.begin(), gaps.end(), 0.0) / double(gaps.size());
    double var = 0;
    for (double g : gaps) var += (g - mean) * (g - mean);
    const double cv = std::sqrt(var / double(gaps.size())) / mean;
    MESSAGE(on.size() << " blinks in 120 s, mean interval " << mean << " s (character " << life.blinkInterval << " s), cv " << cv
                      << ", double blinks " << doubles);
    CHECK(mean == doctest::Approx(life.blinkInterval).epsilon(0.25));
    CHECK(cv > 0.15);    // irregular rhythm
    CHECK(doubles >= 1); // variety: some double blinks
    // Deterministic, random access.
    for (int f = 1; f < 600; f += 7) CHECK(face->blink(f) == face->blink(f));
    // Neutral rhythm keeps the life layer's own blink schedule (double blinks only add).
    for (double f = 1; f < 900; f += 0.5)
      CHECK(face->blink(f) >= blinkAmount(f / 30.0, life.blinkInterval, life.seed, life.blinkClose, life.blinkHold, life.blinkOpen) - 1e-3f);
  }
  // Emotions change the rate: surprised (rate 0.25) blinks far less than afraid (1.5) over the same held minute.
  auto held = [](const char* name) {
    Json a = Json::array({{{"type", "emotion"}, {"character", "who"}, {"name", name}, {"start", 1}, {"end", 1900}}});
    auto ev = faceScene(kGirl, a, 1900);
    return blinkOnsets(*ev->faceLayer(0), 60, 1840).size();
  };
  const size_t surprised = held("surprised"), afraid = held("afraid");
  MESSAGE("blinks in 59 s: surprised " << surprised << ", afraid " << afraid);
  CHECK(afraid >= 3 * surprised);
  CHECK(surprised >= 1);
}

TEST_CASE("facial layer: emotion transitions drive brows, mouth corners and gaze") {
  auto ev = faceScene(kGirl, actingActions(), 260);
  const FaceLayer* face = ev->faceLayer(0);
  REQUIRE(face);
  auto ch = [&](const char* c) { return face->channels().at(c); };
  REQUIRE(ch("browUp") == std::vector<std::string>({"BrowUp.L", "BrowUp.R"}));
  REQUIRE(ch("browSad") == std::vector<std::string>({"BrowSad"}));
  REQUIRE(ch("mouthDown") == std::vector<std::string>({"MouthFrown"}));
  auto avg = [&](const std::string& morph, int a, int b) {
    double s = 0;
    for (int f = a; f < b; ++f) s += ev->morphControlWeight(0, morph, f);
    return s / (b - a);
  };
  auto eyePitch = [&](int a, int b) {
    double s = 0;
    for (int f = a; f < b; ++f) s += ev->faceState(0, f).eyeOffsetDeg.y;
    return s / (b - a);
  };
  // Windows in the hold of each emotion (happy 30.., surprised 95.., sad 150..; sad's onset is 0.8 s).
  const double idleBrow = avg("BrowUp.L", 2, 28), happyBrow = avg("BrowUp.L", 50, 80), surprisedBrow = avg("BrowUp.L", 115, 135);
  const double idleSad = avg("BrowSad", 2, 28), sadSad = avg("BrowSad", 200, 240);
  const double idleFrown = avg("MouthFrown", 2, 28), sadFrown = avg("MouthFrown", 200, 240);
  MESSAGE("BrowUp idle " << idleBrow << " happy " << happyBrow << " surprised " << surprisedBrow << "; BrowSad idle " << idleSad
                         << " sad " << sadSad << "; MouthFrown idle " << idleFrown << " sad " << sadFrown << "; eye pitch idle "
                         << eyePitch(2, 28) << " sad " << eyePitch(200, 240));
  CHECK(happyBrow > idleBrow + 0.1);
  CHECK(surprisedBrow > happyBrow + 0.2);
  CHECK(sadSad > idleSad + 0.4);
  CHECK(sadFrown > idleFrown + 0.2);
  CHECK(eyePitch(200, 240) < eyePitch(2, 28) - 5.0);  // sad looks down
  // Before the first emotion only the neutral living face plays (small values).
  CHECK(idleBrow < 0.1);
  CHECK(idleSad < 0.01);
}

TEST_CASE("facial layer: eye darts and gaze holds") {
  auto ev = faceScene(kBoy, Json::array(), 900);
  const FaceLayer* face = ev->faceLayer(0);
  std::vector<int> holds;
  int run = 0;
  vec2 prev = face->evaluate(1).eyeOffsetDeg;
  float maxAmp = 0;
  for (int f = 2; f < 900; ++f) {
    const vec2 o = face->evaluate(f).eyeOffsetDeg;
    maxAmp = std::max(maxAmp, glm::length(o));
    if (glm::length(o - prev) < 1e-4f) ++run;
    else {
      if (run > 0) holds.push_back(run);
      run = 0;
    }
    prev = o;
  }
  std::sort(holds.begin(), holds.end());
  REQUIRE(holds.size() >= 15);  // ~1 dart per second over 30 s
  MESSAGE(holds.size() << " gaze holds, shortest " << holds.front() << " frames, longest " << holds.back() << ", max offset " << maxAmp
                       << " deg");
  CHECK(holds.back() >= 2 * holds.front());  // varied holds
  CHECK(maxAmp > 0.5f);
  CHECK(maxAmp < 3.0f);  // neutral darts are small
}

TEST_CASE("facial layer: missing controls are skipped; life off and face:false keep the old behaviour") {
  // The boy exports Blink, BrowDown, JawOpen, Smile only: no brow raise, no mouth-corner controls -> skipped silently.
  auto boy = faceScene(kBoy, actingActions(), 200);
  CHECK(boy->faceLayer(0)->channels().at("browUp").empty());
  CHECK(boy->faceLayer(0)->channels().at("mouthDown").empty());
  CHECK(boy->faceLayer(0)->channels().at("jawOpen") == std::vector<std::string>({"JawOpen"}));
  for (const auto& w : boy->warnings()) CHECK(w.find("faceMotion") == std::string::npos);
  // ...but the eyes still dart and the jaw breathes.
  bool eyesMove = false;
  for (int f = 2; f < 120 && !eyesMove; ++f) eyesMove = angleDeg(eyeLocal(*boy, f), eyeLocal(*boy, 1)) > 0.3f;
  CHECK(eyesMove);
  // Life off: no facial layer, morphs exactly as animated.
  auto off = faceScene(kGirl, actingActions(), 200, false);
  CHECK_FALSE(off->faceActive(0));
  for (const auto& m : morphNames(*off))
    for (int f = 1; f < 200; f += 9) CHECK(off->morphControlWeight(0, m, f) == off->expressionWeight(0, m, f));
  // life "face": false: the life layer's original blinks, no face motion.
  auto ev = faceScene(kGirl, actingActions(), 200);
  ev->mutableScene().characters[0].life.face = false;
  const LifeParams life = ev->lifeParams(0);
  const std::string blink = blinkControl(*ev);
  for (int f = 1; f < 200; f += 3) {
    CHECK(ev->morphControlWeight(0, "BrowUp.L", f) == ev->expressionWeight(0, "BrowUp.L", f));
    CHECK(ev->morphControlWeight(0, blink, f) ==
          std::max(ev->expressionWeight(0, blink, f),
                   blinkAmount(f / 30.0, life.blinkInterval, life.seed, life.blinkClose, life.blinkHold, life.blinkOpen)));
  }
}

TEST_CASE("facial layer: the mannequin blinks its lid bones and darts its eyes") {
  auto ev = faceScene("", actingActions(), 400);
  REQUIRE(ev->faceActive(0));
  const FaceLayer* face = ev->faceLayer(0);
  const int lid = bone(*ev, "lid.L");
  REQUIRE(lid >= 0);
  int open = -1, closed = -1;
  for (int f = 2; f < 400 && (open < 0 || closed < 0); ++f) {
    const float b = face->blink(f);
    if (b == 0 && open < 0) open = f;
    if (b > 0.99f && closed < 0) closed = f;
  }
  REQUIRE(open > 0);
  REQUIRE(closed > 0);
  Pose po, pc;
  ev->characterGlobals(0, open, &po);
  ev->characterGlobals(0, closed, &pc);
  const float lidMove = angleDeg(po.local[size_t(lid)], pc.local[size_t(lid)]);
  MESSAGE("lid closes by " << lidMove << " deg (frames " << open << " -> " << closed << ")");
  CHECK(lidMove > 45.0f);
}

TEST_CASE("facial layer: clip face curves play with the clip layer") {
  Json a = Json::parse(R"([{"type": "clip", "character": "who", "clip": "wave", "start": 20}])");
  auto ev = faceScene(kGirl, a, 140);
  auto none = faceScene(kGirl, Json::array(), 140);
  const double during = ev->morphControlWeight(0, "MouthSmile", 60) - none->morphControlWeight(0, "MouthSmile", 60);
  const double after = ev->morphControlWeight(0, "MouthSmile", 135) - none->morphControlWeight(0, "MouthSmile", 135);
  MESSAGE("wave: MouthSmile +" << during << " during, +" << after << " after");
  CHECK(during > 0.15);
  CHECK(std::abs(after) < 1e-4);
}

TEST_CASE("gaze assist: the neck takes what the eyes cannot reach, eyes lead, a hand-keyed neck wins") {
  Skeleton sk;
  sk.bones = {{"chest", -1, vec3(0, 1.0f, 0)}, {"neck", 0, vec3(0, 1.3f, 0)}, {"head", 1, vec3(0, 1.4f, 0)},
              {"eye.L", 2, vec3(0.03f, 1.45f, 0.08f)}, {"eye.R", 2, vec3(-0.03f, 1.45f, 0.08f)}};
  auto aimError = [&](const Pose& pose, vec3 target) {
    const auto g = boneGlobals(sk, pose, mat4(1));
    float worst = 0;
    for (int e : {3, 4}) {
      const vec3 fwd = glm::normalize(vec3(g[size_t(e)][2])), to = glm::normalize(target - vec3(g[size_t(e)][3]));
      worst = std::max(worst, glm::degrees(std::acos(std::clamp(glm::dot(fwd, to), -1.0f, 1.0f))));
    }
    return worst;
  };
  const vec3 side(3.0f, 1.45f, 0.5f);  // ~80 degrees to the character's left
  Clip clip;
  clip.tracks["a/lookAt"].setKey({0, side, Interp::Linear});
  Pose pose = restPose(sk);
  applyConstraints(sk, clip, "a/", 20, mat4(1), pose, GazeLimits{}, 30);
  const float err = aimError(pose, side);
  MESSAGE("aim error with assist " << err << " deg");
  CHECK(err < 0.2f);
  // Without the assist the eyes stop at their limit.
  GazeLimits noAssist;
  noAssist.assistYawDeg = noAssist.assistPitchDeg = noAssist.assistBodyYawDeg = 0;
  Pose p2 = restPose(sk);
  applyConstraints(sk, clip, "a/", 20, mat4(1), p2, noAssist, 30);
  CHECK(aimError(p2, side) > 40.0f);
  // Eyes lead: right after the target jumps, the neck has barely moved.
  Clip jump;
  jump.tracks["a/lookAt"].setKey({0, vec3(0, 1.45f, 3), Interp::Step});
  jump.tracks["a/lookAt"].setKey({10, side, Interp::Step});
  Pose early = restPose(sk), late = restPose(sk);
  applyConstraints(sk, jump, "a/", 11, mat4(1), early, GazeLimits{}, 30);
  applyConstraints(sk, jump, "a/", 22, mat4(1), late, GazeLimits{}, 30);
  CHECK(angleDeg(early.local[1], quat(1, 0, 0, 0)) < 1.0f);
  CHECK(angleDeg(late.local[1], quat(1, 0, 0, 0)) > 20.0f);
  // A hand-keyed neck is left alone.
  Clip keyed = clip;
  keyed.tracks["a/neck.rot"].setKey({0, vec3(0), Interp::Linear});
  Pose p3 = restPose(sk);
  applyConstraints(sk, keyed, "a/", 20, mat4(1), p3, GazeLimits{}, 30);
  CHECK(angleDeg(p3.local[1], quat(1, 0, 0, 0)) < 1e-3f);
}
