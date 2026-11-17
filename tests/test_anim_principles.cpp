// T-061: animation principles (anim/principles.h) in clip layers and IK gestures, and accessory spring chains
// (anim/secondary.h "attach" / presets). Engine test packages (boy 1.0.0, girl m3, toy fixture); no character names in
// the code under test.
#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <memory>

#include "anim/principles.h"
#include "anim/secondary.h"
#include "scene/scene.h"

using namespace plush;
namespace fs = std::filesystem;

namespace {
const fs::path kRoot = PLUSH_SOURCE_DIR;
const char* const kBoy = "boy_yellow_hoodie_1.0.0/character.json";
const char* const kGirl = "girl_auburn_bun_glasses_m3/character.json";
const char* const kToy = "toy_fixture/character.json";

Scene baseScene(int end, Json principles) {
  Scene s;
  s.name = "animation principles test";
  s.path = kRoot / "tests/data/imported/scene.json";
  s.rate = FrameRate{24, 1};
  s.frameStart = 1;
  s.frameEnd = end;
  s.animPrinciples = std::move(principles);
  return s;
}
std::unique_ptr<SceneEvaluator> load(const Scene& scene) {
  auto ev = std::make_unique<SceneEvaluator>();
  auto r = ev->load(scene, EvalOptions{2.5f, 1.0f, false, 0});
  if (!r) FAIL(r.error().message);
  return ev;
}
std::unique_ptr<SceneEvaluator> one(const char* asset, Json actions, Json principles = nullptr, int end = 120,
                                    Json dynamics = nullptr) {
  Scene s = baseScene(end, std::move(principles));
  CharacterDesc c;
  c.name = "who";
  c.asset = asset;
  c.dynamics = std::move(dynamics);
  s.characters.push_back(c);
  s.actions = std::move(actions);
  return load(s);
}
int boneOf(const SceneEvaluator& ev, const std::string& name) { return ev.characters()[0].asset.skeleton.find(name); }
vec3 at(const SceneEvaluator& ev, const std::string& bone, double f) {
  const int b = boneOf(ev, bone);
  REQUIRE(b >= 0);
  return vec3(ev.characterGlobals(0, f)[size_t(b)][3]);
}
float angleDeg(const quat& a, const quat& b) {
  return glm::degrees(2.0f * std::acos(std::clamp(std::abs(glm::dot(glm::normalize(a), glm::normalize(b))), 0.0f, 1.0f)));
}
quat localAt(const SceneEvaluator& ev, const std::string& bone, double f) {
  Pose p;
  ev.characterGlobals(0, f, &p);
  return p.local[size_t(boneOf(ev, bone))];
}
std::vector<float> wristSpeed(const SceneEvaluator& ev, const std::string& bone, int f0, int f1) {
  std::vector<float> s;
  vec3 prev = at(ev, bone, f0);
  for (int f = f0 + 1; f <= f1; ++f) {
    const vec3 p = at(ev, bone, f);
    s.push_back(glm::distance(p, prev));
    prev = p;
  }
  return s;
}
Json waveAction(double start, double blendIn, double speed = 1.5) {
  return Json{{"type", "clip"}, {"character", "who"}, {"clip", "wave"}, {"start", start}, {"speed", speed},
              {"blendIn", blendIn}, {"blendOut", 8}};
}
}  // namespace

TEST_CASE("principles: ease curve, eased clock, blend length from amplitude, succession ranks, settings") {
  CHECK(easeInOut(0) == 0);
  CHECK(easeInOut(1) == doctest::Approx(1));
  CHECK(easeInOut(0.5) == doctest::Approx(0.5));
  // zero slope at both ends, peak slope 1.875 in the middle
  CHECK((easeInOut(0.01) - easeInOut(0)) / 0.01 < 0.01);
  CHECK((easeInOut(1) - easeInOut(0.99)) / 0.01 < 0.01);
  CHECK((easeInOut(0.501) - easeInOut(0.499)) / 0.002 == doctest::Approx(kEasePeakSlope).epsilon(1e-3));
  CHECK(easeInOutIntegral(1) == doctest::Approx(0.5));
  // eased clock: starts and stops with zero rate, covers the whole layer, monotonic
  const double L = 60, in = 12, out = 10;
  CHECK(easedClock(0, L, in, out) == doctest::Approx(0));
  CHECK(easedClock(L, L, in, out) == doctest::Approx(L));
  CHECK(easedClock(0.5, L, in, out) < 0.01);
  CHECK(L - easedClock(L - 0.5, L, in, out) < 0.01);
  for (double t = 0; t < L; t += 0.5) CHECK(easedClock(t + 0.5, L, in, out) >= easedClock(t, L, in, out));
  CHECK(easedClock(7, L, 0, 0) == doctest::Approx(7));
  // blend length: 1.875 A / maxBlendDegPerSec, clamped
  AnimPrinciples p;
  CHECK(minBlendFrames(0, 24, p) == doctest::Approx(p.minBlendSec * 24));
  CHECK(minBlendFrames(1000, 24, p) == doctest::Approx(p.maxBlendSec * 24));
  CHECK(minBlendFrames(48, 24, p) == doctest::Approx(1.875 * 48 / p.maxBlendDegPerSec * 24));
  // succession: trunk, upper limb, lower limb, extremity, fingers
  CHECK(successionRank("chest") == 0);
  CHECK(successionRank("upperArm.R") == 1);
  CHECK(successionRank("forearm.L") == 2);
  CHECK(successionRank("hand.R") == 3);
  CHECK(successionRank("f1b.L") == 4);
  CHECK(successionRank("thumbA.R") == 4);
  CHECK(successionRank("head") == 2);
  // settings
  CHECK(animPrinciplesFromJson(Json())->enabled);
  CHECK_FALSE(animPrinciplesFromJson(Json(false))->enabled);
  auto o = animPrinciplesFromJson(Json::parse(R"({"minArc": 0.2, "successionSec": 0.1})"));
  REQUIRE(o.has_value());
  CHECK(o->minArc == doctest::Approx(0.2));
  CHECK(o->successionSec == doctest::Approx(0.1));
  CHECK_FALSE(animPrinciplesFromJson(Json::parse(R"({"minArc": "x"})")).has_value());
  CHECK_FALSE(animPrinciplesFromJson(Json::parse(R"({"minBlendSec": 0.9, "maxBlendSec": 0.5})")).has_value());
  CHECK_FALSE(animPrinciplesFromJson(Json(3)).has_value());
}

TEST_CASE("principles: ease-preserving retiming keeps the spacing at the extremes") {
  // A synthetic clip: hold, a fast stroke with eased ends, hold, a second stroke (motion per clip frame).
  std::vector<double> motion;
  for (int k = 0; k < 6; ++k) motion.push_back(0.0);
  for (int k = 0; k < 20; ++k) motion.push_back(std::sin(3.14159265 * (k + 0.5) / 20.0));
  for (int k = 0; k < 6; ++k) motion.push_back(0.0);
  for (int k = 0; k < 20; ++k) motion.push_back(std::sin(3.14159265 * (k + 0.5) / 20.0));
  AnimPrinciples p;
  for (double speed : {1.5, 0.8}) {
    const TimeWarp lin = TimeWarp::linear(speed, 30, 24), w = TimeWarp::easePreserving(motion, speed, 30, 24, p);
    REQUIRE_FALSE(w.isLinear());
    const double len = double(motion.size()) / speed * 24 / 30;  // linear scene length
    CHECK(w.sceneLength() == doctest::Approx(len).epsilon(1e-9));
    CHECK(w.clipFrame(len, false) == doctest::Approx(double(motion.size())));
    CHECK(w.clipFrame(0, false) == doctest::Approx(0));
    double prev = -1;
    for (double t = 0; t <= len; t += 0.25) {
      const double c = w.clipFrame(t, false);
      CHECK(c >= prev);
      prev = c;
    }
    // scene time spent in the hold (clip frames 0..6) and in the stroke's middle vs the linear scale
    auto sceneTime = [&](const TimeWarp& tw, double c0, double c1) {
      double a = 0, b = len;  // invert by bisection
      auto inv = [&](double c) {
        double lo = 0, hi = len;
        for (int i = 0; i < 60; ++i) ((tw.clipFrame(0.5 * (lo + hi), false) < c) ? lo : hi) = 0.5 * (lo + hi);
        return hi;
      };
      a = inv(c0);
      b = inv(c1);
      return b - a;
    };
    const double holdW = sceneTime(w, 0, 6), holdL = sceneTime(lin, 0, 6);
    const double midW = sceneTime(w, 12, 20), midL = sceneTime(lin, 12, 20);
    MESSAGE("speed " << speed << ": hold " << holdW << " vs linear " << holdL << " frames; stroke middle " << midW
                     << " vs " << midL);
    const double authoredHold = 6 * 24.0 / 30;
    // the extremes stay closer to their authored spacing than a linear scale; the fast middle absorbs the change
    CHECK(std::abs(holdW - authoredHold) < std::abs(holdL - authoredHold));
    if (speed > 1) CHECK(midW < midL);
    else CHECK(midW > midL);
    // one constant rate inside a movement (its own ease shape is kept, only scaled): equal scene time for equal clip
    // spans in the stroke's first and second half
    CHECK(sceneTime(w, 9, 13) == doctest::Approx(sceneTime(w, 18, 22)).epsilon(1e-6));
    // the local rate stays within retimeMaxRate x the request
    for (double t = 0; t + 0.5 <= len; t += 0.5) {
      const double rate = (w.clipFrame(t + 0.5, false) - w.clipFrame(t, false)) / 0.5;
      CHECK(rate <= lin.clipFrame(1, false) * (speed > 1 ? p.retimeMaxRate : 1.0) * (30.0 / 24.0) * 1.0001 + 1.3);
    }
  }
  // looping: the warp repeats with the clip
  const TimeWarp w = TimeWarp::easePreserving(motion, 1.5, 30, 24, p);
  CHECK(w.clipFrame(w.sceneLength() + 3, true) == doctest::Approx(double(motion.size()) + w.clipFrame(3, true)));
  // speed 1 or a motionless clip: linear
  CHECK(TimeWarp::easePreserving(motion, 1.0, 30, 24, p).isLinear());
  CHECK(TimeWarp::easePreserving(std::vector<double>(10, 0.0), 1.5, 30, 24, p).isLinear());
}

TEST_CASE("principles: a clip blended in over 4 frames at speed 1.5 leaves and arrives with slow-in / slow-out") {
  for (const char* asset : {kBoy, kGirl}) {
    CAPTURE(asset);
    const Json acts = Json::array({waveAction(20, 4)});
    auto on = one(asset, acts), off = one(asset, acts, false);
    // the lift out of rest: speed of the wrist over the first frames of the blend, relative to the gesture's peak
    const auto sOn = wristSpeed(*on, "hand.R", 18, 60), sOff = wristSpeed(*off, "hand.R", 18, 60);
    const float pOn = *std::max_element(sOn.begin(), sOn.end()), pOff = *std::max_element(sOff.begin(), sOff.end());
    float firstOn = 0, firstOff = 0;
    for (int k = 2; k < 6; ++k) firstOn += sOn[size_t(k)] / 4, firstOff += sOff[size_t(k)] / 4;  // frames 20..24
    MESSAGE("first 4 frames / peak: on " << firstOn / pOn << ", off " << firstOff / pOff);
    CHECK(firstOn / pOn < 0.15f);
    CHECK(firstOn / pOn < 0.5f * firstOff / pOff);
    // monotonic acceleration out of rest (no burst-and-dip at the blend boundary)
    for (int k = 2; k < 5; ++k) CHECK(sOn[size_t(k + 1)] >= sOn[size_t(k)]);
    // nothing before the layer starts; the end of the clip is reached and the base returns afterwards
    CHECK(glm::distance(at(*on, "hand.R", 20), at(*off, "hand.R", 20)) < 1e-6f);
    auto none = one(asset, Json::array());
    CHECK(glm::distance(at(*on, "hand.R", 110), at(*none, "hand.R", 110)) < 1e-5f);
    // deterministic, any evaluation order
    const vec3 a = at(*on, "hand.R", 33);
    at(*on, "hand.R", 90);
    CHECK(glm::distance(a, at(*on, "hand.R", 33)) == 0.0f);
  }
}

TEST_CASE("principles: successive breaking in clip blends (shoulder leads, elbow and wrist follow)") {
  for (const char* asset : {kBoy, kGirl}) {
    CAPTURE(asset);
    auto on = one(asset, Json::array({waveAction(20, 12, 1.0)}));
    auto none = one(asset, Json::array());
    auto full = one(asset, Json::array({waveAction(20, 0, 1.0)}));  // a cut: the clip at full weight from its start
    auto progress = [&](const std::string& bone, double f) {
      const float total = angleDeg(localAt(*none, bone, f), localAt(*full, bone, f));
      return total > 0.5f ? angleDeg(localAt(*none, bone, f), localAt(*on, bone, f)) / total : -1.0f;
    };
    bool checked = false, handChecked = false;
    for (double f : {23.0, 25.0, 27.0}) {
      const float u = progress("upperArm.R", f), fa = progress("forearm.R", f), h = progress("hand.R", f);
      MESSAGE("frame " << f << ": upperArm " << u << ", forearm " << fa << ", hand " << h);
      if (u < 0 || fa < 0) continue;
      CHECK(u > fa);
      checked = true;
      if (h >= 0 && fa > 0) {
        CHECK(fa > h);
        handChecked = true;
      }
    }
    CHECK(checked);
    CHECK(handChecked);
    // a cut (blendIn 0) has no offsets: every bone is at the clip pose from the first frame
    CHECK(angleDeg(localAt(*full, "hand.R", 21), localAt(*one(asset, Json::array({waveAction(20, 0, 1.0)}), false), "hand.R", 21)) < 1e-3f);
  }
}

TEST_CASE("principles: automatic breakdowns make a near-linear blend path travel on an arc") {
  // The library point clip blended in from the idle stance: without breakdowns (minArc 0) the wrist path of the
  // blend is close to a straight line; with them (a high minArc so the search runs on both packages) it bulges away
  // from its chord. After the blend the poses are identical.
  const Json acts = Json::array({Json{{"type", "clip"}, {"character", "who"}, {"clip", "point"}, {"start", 20}}});
  int applied = 0;
  for (const char* asset : {kBoy, kGirl}) {
    CAPTURE(asset);
    auto with = one(asset, acts, Json::parse(R"({"minArc": 0.6})")), without = one(asset, acts, Json::parse(R"({"minArc": 0})"));
    const auto plans = with->clipLayerPlans(0), plain = without->clipLayerPlans(0);
    REQUIRE(plans.size() == 1);
    REQUIRE(plain.size() == 1);
    const auto& P = plans[0];
    CHECK(P.principles);
    CHECK(P.blendIn >= 6.0);  // never shorter than authored (default 6)
    CHECK(plain[0].breakIn[1] == 0.0f);
    // the planner's window: the blend in plus the succession offsets
    auto arcOf = [&](const SceneEvaluator& ev) {
      std::vector<vec3> path;
      for (double f = std::floor(P.start); f <= std::ceil(P.start + P.blendIn + 4 * P.succession); f += 1) path.push_back(at(ev, "hand.R", f));
      return arcDeviation(path);
    };
    const float a1 = arcOf(*with), a0 = arcOf(*without);
    MESSAGE("blend-in wrist arc: breakdown " << P.breakIn[1] << " deg -> " << a1 << ", without " << a0);
    if (P.breakIn[1] != 0.0f) {
      CHECK(a1 > a0 + 0.005f);
      CHECK(std::abs(P.breakIn[1]) <= 35.0f);
      ++applied;
    } else {
      CHECK(a1 == doctest::Approx(a0));
    }
    // outside the blends nothing changes
    CHECK(glm::distance(at(*with, "hand.R", P.start + P.blendIn + 6), at(*without, "hand.R", P.start + P.blendIn + 6)) < 1e-5f);
  }
  CHECK(applied >= 1);
  // arcDeviation: straight line 0, half circle 0.5
  std::vector<vec3> line{{0, 0, 0}, {0.5f, 0, 0}, {1, 0, 0}}, half;
  for (int k = 0; k <= 32; ++k) half.push_back(vec3(std::cos(3.14159265f * k / 32), std::sin(3.14159265f * k / 32), 0));
  CHECK(arcDeviation(line) == doctest::Approx(0));
  CHECK(arcDeviation(half) == doctest::Approx(0.5).epsilon(1e-3));
}

TEST_CASE("principles: IK gestures ease with the elbow trailing; contacts stay exact") {
  // reachable spots in front of the right hand (the T-045 evidence shot's touch targets, character space)
  auto targetFor = [](const char* asset) { return asset == kBoy ? vec3(-0.17f, 0.46f, 0.18f) : vec3(-0.16f, 0.43f, 0.165f); };
  for (const char* asset : {kBoy, kGirl}) {
    CAPTURE(asset);
    const vec3 T = targetFor(asset);
    const Json touch = Json::array({Json{{"type", "touch"}, {"character", "who"}, {"hand", "R"}, {"start", 20}, {"contact", 36},
                                         {"end", 58}, {"target", {T.x, T.y, T.z}}}});
    auto on = one(asset, touch), off = one(asset, touch, false);
    // fingertip on the target at contact (the index tip, as the action measures it)
    for (auto* ev : {on.get(), off.get()}) {
      Pose p;
      ev->characterGlobals(0, 36, &p);
      auto tips = fingertips(ev->characters()[0].asset.skeleton, p, mat4(1), 'R');
      REQUIRE(tips.size() >= 5);
      CHECK(glm::distance(tips[4], T) <= 0.005f);
    }
    // the elbow trails the shoulder early in the ramp
    auto none = one(asset, Json::array());
    auto progress = [&](const std::string& bone, double f) {
      const float total = angleDeg(localAt(*none, bone, f), localAt(*on, bone, 30));
      return total > 0.5f ? angleDeg(localAt(*none, bone, f), localAt(*on, bone, f)) / total : -1.0f;
    };
    const float u = progress("upperArm.R", 22), fa = progress("forearm.R", 22);
    MESSAGE("touch ramp at frame 22: upperArm " << u << ", forearm " << fa);
    if (u >= 0 && fa >= 0) CHECK(u > fa);
    // the ramp may start earlier than authored for a large arm move, but at most half its authored length
    CHECK(glm::distance(at(*on, "hand.R", 12), at(*none, "hand.R", 12)) < 1e-6f);
    // after the gesture the arm is back where it would be without it
    CHECK(glm::distance(at(*on, "hand.R", 60), at(*none, "hand.R", 60)) < 1e-4f);
  }
  // reach (object): the hand reaches the same grip at contact with and without the principles (<= 5 mm)
  for (const char* asset : {kBoy, kGirl}) {
    CAPTURE(asset);
    Scene s[2] = {baseScene(100, nullptr), baseScene(100, false)};
    std::unique_ptr<SceneEvaluator> ev[2];
    for (int k = 0; k < 2; ++k) {
      CharacterDesc c;
      c.name = "who";
      c.asset = asset;
      s[k].characters.push_back(c);
      ObjectDesc o;
      o.name = "cup";
      o.kind = ObjectDesc::Kind::Box;
      const vec3 T = targetFor(asset) + vec3(0, -0.03f, 0);
      o.boxMin = T - vec3(0.02f);
      o.boxMax = T + vec3(0.02f);
      s[k].objects.push_back(o);
      s[k].actions = Json::array({Json{{"type", "reach"}, {"character", "who"}, {"hand", "R"}, {"object", "cup"}, {"start", 20},
                                       {"contact", 36}, {"liftEnd", 46}, {"place", 64}, {"release", 67}, {"end", 82}}});
      ev[k] = load(s[k]);
    }
    for (double f : {36.0, 64.0})
      CHECK(glm::distance(at(*ev[0], "hand.R", f), at(*ev[1], "hand.R", f)) <= 0.005f);
  }
}

TEST_CASE("principles: off restores the plain ramps; the setting is saved as written") {
  const Json acts = Json::array({waveAction(20, 6)});
  auto on = one(kBoy, acts), off = one(kBoy, acts, false), offObj = one(kBoy, acts, Json::parse(R"({"enabled": false})"));
  CHECK(glm::distance(at(*on, "hand.R", 23), at(*off, "hand.R", 23)) > 1e-3f);
  for (double f : {21.0, 23.0, 40.0, 70.0}) CHECK(glm::distance(at(*off, "hand.R", f), at(*offObj, "hand.R", f)) == 0.0f);
  // legacy ramp (smoothstep over blendIn, no offsets): the wrist moves on the first frame after the start
  CHECK(glm::distance(at(*off, "hand.R", 21), at(*off, "hand.R", 20)) > glm::distance(at(*on, "hand.R", 21), at(*on, "hand.R", 20)));
  Scene s = baseScene(60, Json::parse(R"({"successionSec": 0.08})"));
  const fs::path tmp = kRoot / "build/test_tmp/principles_roundtrip.scene.json";
  fs::create_directories(tmp.parent_path());
  REQUIRE(saveScene(s, tmp).has_value());
  auto back = loadScene(tmp);
  REQUIRE(back.has_value());
  CHECK(back->animPrinciples == Json::parse(R"({"successionSec": 0.08})"));
  Json bad = sceneToJson(s);
  bad["animPrinciples"] = Json::parse(R"({"maxBlendDegPerSec": -3})");
  {
    std::ofstream(tmp) << bad.dump();
  }
  CHECK_FALSE(loadScene(tmp).has_value());
}

TEST_CASE("accessory chains: presets and chains attached by bone name (package block and scene)") {
  // resolution on a synthetic skeleton: a drawstring hanging from the chest, bones "DYN-string.L.<n>"
  Skeleton sk;
  sk.bones.push_back({"hips", -1, vec3(0, 0.3f, 0)});
  sk.bones.push_back({"chest", 0, vec3(0, 0.5f, 0)});
  sk.bones.push_back({"DYN-string.L.0", 1, vec3(0.03f, 0.48f, 0.08f)});
  sk.bones.push_back({"DYN-string.L.1", 2, vec3(0.03f, 0.44f, 0.08f)});
  sk.bones.push_back({"DYN-string.L.2", 3, vec3(0.03f, 0.40f, 0.08f)});
  sk.bones.push_back({"DYN-string.L.10", 4, vec3(0.03f, 0.36f, 0.08f)});  // numeric, not lexical, order
  auto spec = dynamicsFromJson(Json::parse(R"({"presets": {"drawstring": {"damping": 2.5}, "cord": {"stiffness": 33}},
      "attach": [{"name": "string.L", "prefix": "DYN-string.L", "preset": "drawstring"}]})"));
  REQUIRE(spec.has_value());
  CHECK(spec->chains.empty());
  REQUIRE(resolveAccessoryChains(*spec, sk).has_value());
  REQUIRE(spec->chains.size() == 1);
  const SpringChain& ch = spec->chains[0];
  CHECK(ch.bones == std::vector<std::string>{"DYN-string.L.0", "DYN-string.L.1", "DYN-string.L.2", "DYN-string.L.10"});
  CHECK(ch.group == "drawstring");
  CHECK(ch.params.damping == doctest::Approx(2.5));  // the block's preset override
  CHECK(ch.params.stiffness == doctest::Approx(builtinSpringPresets().at("drawstring").stiffness));
  CHECK(glm::distance(ch.tip, vec3(0.03f, 0.32f, 0.08f)) < 1e-6f);  // last segment extended
  CHECK(spec->attach.empty());
  // a chain in the package block may name a preset too; explicit keys win
  auto pk = dynamicsFromJson(Json::parse(R"({"chains": [{"name": "s", "bones": ["DYN-string.L.0"], "tip": [0, 0.4, 0],
      "preset": "strap", "gravity": 0.2}]})"));
  REQUIRE(pk.has_value());
  CHECK(pk->chains[0].params.stiffness == doctest::Approx(builtinSpringPresets().at("strap").stiffness));
  CHECK(pk->chains[0].params.gravity == doctest::Approx(0.2));
  CHECK(dynamicsFromJson(dynamicsToJson(*pk))->chains[0].preset == "strap");
  // errors
  for (const char* bad : {R"({"attach": [{"name": "x", "prefix": "nope"}]})", R"({"attach": [{"name": "x", "bones": ["missing"]}]})",
                          R"({"attach": [{"name": "x", "prefix": "DYN-string.L", "preset": "unknown"}]})", R"({"attach": [{"prefix": ""}]})"}) {
    CAPTURE(bad);
    auto d = dynamicsFromJson(Json::parse(bad));
    REQUIRE(d.has_value());
    CHECK_FALSE(resolveAccessoryChains(*d, sk).has_value());
  }
  CHECK_FALSE(dynamicsFromJson(Json::parse(R"({"chains": [{"name": "s", "bones": ["a"], "preset": "unknown"}]})")).has_value());

  // scene level: the toy fixture (no dynamics block) gets a strap on its tail bones ("tail_<n>") from the scene
  auto swing = [](Scene& s) {
    const double keys[][2] = {{0.0, 0}, {0.3, 50}, {0.6, -30}, {0.9, 0}};
    for (auto& k : keys) s.animation.tracks["who/hips.rot"].setKey({1 + k[0] * 24, vec3(0, float(k[1]), 0)});
  };
  auto toy = [&](Json dynamics) {
    Scene s = baseScene(73, nullptr);
    CharacterDesc c;
    c.name = "who";
    c.asset = kToy;
    c.dynamics = std::move(dynamics);
    s.characters.push_back(c);
    swing(s);
    return load(s);
  };
  auto plain = toy(nullptr);
  auto strap = toy(Json::parse(R"({"attach": [{"name": "tail", "prefix": "tail", "preset": "drawstring"}]})"));
  auto offAttach = toy(Json::parse(R"({"enabled": false, "attach": [{"name": "tail", "prefix": "tail", "preset": "drawstring"}]})"));
  float lag = 0, offDiff = 0;
  for (int f = 2; f <= 30; ++f) {
    lag = std::max(lag, glm::distance(at(*plain, "tail_2", f), at(*strap, "tail_2", f)));
    offDiff = std::max(offDiff, glm::distance(at(*plain, "tail_2", f), at(*offAttach, "tail_2", f)));
  }
  MESSAGE("attached tail: max offset from the kinematic pose " << lag * 1000 << " mm");
  CHECK(lag > 0.005f);    // it swings behind the hips
  CHECK(offDiff == 0.0f);  // "enabled": false keeps it kinematic
  // settles back to the rest shape once the hips stop (frame 73 = 3 s)
  CHECK(glm::distance(at(*plain, "tail_2", 73), at(*strap, "tail_2", 73)) < 0.002f);
  // bad attach in a scene fails the load with a message
  Scene s = baseScene(30, nullptr);
  CharacterDesc c;
  c.name = "who";
  c.asset = kToy;
  c.dynamics = Json::parse(R"({"attach": [{"name": "x", "prefix": "nothing"}]})");
  s.characters.push_back(c);
  SceneEvaluator ev;
  CHECK_FALSE(ev.load(s, EvalOptions{2.5f, 1.0f, false, 0}).has_value());
}
