// Gaze legibility (T-120, scene.h GazeLegibility): opt-in, default unchanged. The eyes lead and the head turns just
// enough, after them; the eyes stay inside the character's gaze range in every frame, blinks and eye darts included.
#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>

#include "geom/json_io.h"
#include "scene/scene.h"

using namespace plush;

namespace {
const vec2 kRange(16.0f, 8.0f);  // both current characters' spec face.eyes.gaze_range_deg

Skeleton headSkeleton() {
  Skeleton sk;
  sk.bones = {{"chest", -1, vec3(0, 1.0f, 0)}, {"neck", 0, vec3(0, 1.3f, 0)}, {"head", 1, vec3(0, 1.4f, 0)},
              {"eye.L", 2, vec3(0.03f, 1.45f, 0.08f)}, {"eye.R", 2, vec3(-0.03f, 1.45f, 0.08f)}};
  return sk;
}

// Yaw / pitch (degrees) of a bone's +Z relative to the head (bone 2 of headSkeleton, or `head`).
vec2 eyeAngles(const std::vector<mat4>& g, int eye, int head) {
  const vec3 d = glm::normalize(glm::transpose(mat3(g[size_t(head)])) * glm::normalize(vec3(g[size_t(eye)][2])));
  return vec2(glm::degrees(std::atan2(d.x, d.z)), glm::degrees(std::atan2(d.y, glm::length(vec2(d.x, d.z)))));
}
float turnDeg(const quat& q) { return glm::degrees(2.0f * std::acos(std::clamp(std::abs(q.w), 0.0f, 1.0f))); }

GazeLegibility legible(float headYaw = 70, float headPitch = 35) {
  GazeLegibility lg;
  lg.enabled = true;
  lg.rangeDeg = kRange;
  lg.headYawDeg = headYaw;
  lg.headPitchDeg = headPitch;
  return lg;
}
// What characterGlobals does for a legible character: the head's share, then the eyes inside the range.
Pose legiblePose(const Skeleton& sk, const Clip& clip, double frame, const GazeLegibility& lg, double fps = 24) {
  GazeLimits limits;
  limits.assistYawDeg = limits.assistPitchDeg = limits.assistBodyYawDeg = 0;
  limits.maxLeftDeg = limits.maxRightDeg = lg.rangeDeg.x;
  limits.maxUpDeg = limits.maxDownDeg = lg.rangeDeg.y;
  Pose pose = restPose(sk);
  turnHeadForGaze(sk, clip, "a/", frame, fps, mat4(1), pose, lg);
  applyConstraints(sk, clip, "a/", frame, mat4(1), pose, limits, fps);
  clampEyesToGazeRange(sk, mat4(1), pose, lg.rangeDeg);
  return pose;
}
float aimError(const Skeleton& sk, const Pose& pose, vec3 target) {
  const auto g = boneGlobals(sk, pose, mat4(1));
  float worst = 0;
  for (int e : {3, 4}) {
    const vec3 fwd = glm::normalize(vec3(g[size_t(e)][2])), to = glm::normalize(target - vec3(g[size_t(e)][3]));
    worst = std::max(worst, glm::degrees(std::acos(std::clamp(glm::dot(fwd, to), -1.0f, 1.0f))));
  }
  return worst;
}

std::unique_ptr<SceneEvaluator> girlScene(const Json& sceneFlag, const Json& characterFlag, int end = 400) {
  Scene s;
  s.rate = FrameRate{24, 1};
  s.frameStart = 1;
  s.frameEnd = end;
  s.path = std::filesystem::path(PLUSH_SOURCE_DIR) / "tests/data/imported/scene.json";
  CharacterDesc cd;
  cd.name = "who";
  cd.asset = "girl_auburn_bun_glasses_m3/character.json";
  cd.life.enabled = true;
  cd.life.blinkInterval = 1.2f;
  cd.life.blinkIntervalSet = true;
  cd.gazeLegibility = characterFlag;
  s.characters.push_back(cd);
  s.gazeLegibility = sceneFlag;
  // Down to a table edge beside her, then far to her side and up: both beyond 16 / 8 degrees of eye travel.
  s.actions = Json::parse(R"([
    {"type": "look", "character": "who", "start": 30, "end": 150, "target": [0.35, 0.35, 0.45]},
    {"type": "look", "character": "who", "start": 170, "end": 330, "target": [-1.2, 1.6, 0.6]}])");
  auto ev = std::make_unique<SceneEvaluator>();
  auto r = ev->load(s, EvalOptions{2.5f, 1.0f, false, 0});
  REQUIRE(r.has_value());
  return ev;
}
}  // namespace

TEST_CASE("gaze legibility: the eyes lead, the head starts leadFrames later and eases over turnFrames") {
  const Skeleton sk = headSkeleton();
  const vec3 ahead(0, 1.45f, 3), side(2.0f, 1.45f, 1.5f);  // ~53 degrees to the character's left
  Clip jump;
  jump.tracks["a/lookAt"].setKey({0, ahead, Interp::Step});
  jump.tracks["a/lookAt"].setKey({10, side, Interp::Step});
  const GazeLegibility lg = legible();  // leadFrames 3, turnFrames 8
  auto neckTurn = [&](double f) { return turnDeg(legiblePose(sk, jump, f, lg).local[1]); };
  auto eyeYaw = [&](double f) { return eyeAngles(boneGlobals(sk, legiblePose(sk, jump, f, lg), mat4(1)), 3, 2).x; };
  // The eyes are at their range at once; the head has not moved until the lead is over.
  CHECK(std::abs(eyeYaw(9)) < 1.0f);
  CHECK(eyeYaw(10) > kRange.x - 0.5f);
  for (double f : {10.0, 11.0, 12.0, 13.0}) CHECK(neckTurn(f) < 1e-3f);
  // Then it turns, never back, slowly at both ends (at first the eyes still cover the eased target), and is there
  // after lead + turn.
  float previous = 0, firstStep = 0, largestStep = 0, lastStep = 0;
  for (int f = 14; f <= 21; ++f) {
    const float now = neckTurn(f), step = now - previous;
    CHECK(step >= 0.0f);
    if (f == 14) firstStep = step;
    if (f == 21) lastStep = step;
    largestStep = std::max(largestStep, step);
    previous = now;
  }
  MESSAGE("head turn " << previous << " deg; steps first " << firstStep << ", largest " << largestStep << ", last " << lastStep);
  CHECK(firstStep < 0.5f * largestStep);
  CHECK(lastStep < 0.5f * largestStep);
  CHECK(neckTurn(21) == doctest::Approx(neckTurn(40)).epsilon(1e-4));
  CHECK(neckTurn(40) > 30.0f);
  // Frames are counted at 24 fps: at 48 fps the same lead takes twice as many frames.
  CHECK(turnDeg(legiblePose(sk, jump, 16, lg, 48).local[1]) < 1e-3f);
  CHECK(turnDeg(legiblePose(sk, jump, 24, lg, 48).local[1]) == doctest::Approx(neckTurn(17)).epsilon(1e-3));
  // Longer lead, later head.
  GazeLegibility slow = lg;
  slow.leadFrames = 6;
  CHECK(turnDeg(legiblePose(sk, jump, 16, slow).local[1]) < 1e-3f);
  CHECK(turnDeg(legiblePose(sk, jump, 17, lg).local[1]) > 5.0f);
}

TEST_CASE("gaze legibility: the head turns just enough for the near eye, up to its caps; a keyed neck wins") {
  const Skeleton sk = headSkeleton();
  auto look = [](vec3 target) {
    Clip clip;
    clip.tracks["a/lookAt"].setKey({0, target, Interp::Linear});
    return clip;
  };
  // A target the eyes reach comfortably: the head stays.
  const vec3 nearAhead(0.15f, 1.42f, 1.5f);
  Pose p = legiblePose(sk, look(nearAhead), 30, legible());
  CHECK(turnDeg(p.local[1]) < 1e-3f);
  CHECK(aimError(sk, p, nearAhead) < 0.2f);
  // Far to the side and down: the eyes reach it, and the worse-placed eye sits at the edge of its comfortable range
  // (16 -> 11.75, 8 -> 5.75 degrees), not beyond and not well inside: the head did not turn more than needed.
  const vec3 cup(0.5f, 1.1f, 0.5f);
  p = legiblePose(sk, look(cup), 30, legible());
  CHECK(aimError(sk, p, cup) < 0.2f);
  auto g = boneGlobals(sk, p, mat4(1));
  const vec2 l = glm::abs(eyeAngles(g, 3, 2)), r = glm::abs(eyeAngles(g, 4, 2));
  MESSAGE("eyes vs head: L " << l.x << " / " << l.y << ", R " << r.x << " / " << r.y << " deg; head " << turnDeg(p.local[1]));
  CHECK(std::max(l.x, r.x) == doctest::Approx(11.75f).epsilon(0.01));
  CHECK(std::max(l.y, r.y) == doctest::Approx(5.75f).epsilon(0.02));
  CHECK(std::min(l.x, r.x) < std::max(l.x, r.x));  // the near eye decides
  // Capped head: it stops at the cap and the eyes stop at the range (they no longer reach the target).
  p = legiblePose(sk, look(cup), 30, legible(15, 10));
  g = boneGlobals(sk, p, mat4(1));
  const vec3 headForward = glm::normalize(vec3(g[2][2]));
  CHECK(glm::degrees(std::atan2(headForward.x, headForward.z)) == doctest::Approx(15.0f).epsilon(0.02));
  for (int e : {3, 4}) {
    const vec2 a = glm::abs(eyeAngles(g, e, 2));
    CHECK(a.x <= kRange.x + 1e-3f);
    CHECK(a.y <= kRange.y + 1e-3f);
  }
  CHECK(aimError(sk, p, cup) > 5.0f);
  // A hand-keyed neck is left alone.
  Clip keyed = look(cup);
  keyed.tracks["a/neck.rot"].setKey({0, vec3(0), Interp::Linear});
  CHECK(turnDeg(legiblePose(sk, keyed, 30, legible()).local[1]) < 1e-3f);
}

TEST_CASE("gaze legibility: the clamp brings an eye back to the range and leaves an eye inside it alone") {
  const Skeleton sk = headSkeleton();
  Pose pose = restPose(sk);
  pose.local[1] = glm::angleAxis(glm::radians(20.0f), vec3(0, 1, 0));  // the range is relative to the turned head
  pose.local[3] = glm::angleAxis(glm::radians(30.0f), vec3(0, 1, 0)) * glm::angleAxis(glm::radians(25.0f), vec3(1, 0, 0));
  pose.local[4] = glm::angleAxis(glm::radians(-10.0f), vec3(0, 1, 0)) * glm::angleAxis(glm::radians(-5.0f), vec3(1, 0, 0));
  const quat inside = pose.local[4];
  clampEyesToGazeRange(sk, mat4(1), pose, kRange);
  const auto g = boneGlobals(sk, pose, mat4(1));
  const vec2 a = eyeAngles(g, 3, 2);
  CHECK(a.x == doctest::Approx(16.0f).epsilon(1e-3));
  CHECK(a.y == doctest::Approx(-8.0f).epsilon(1e-3));  // +X rotation looks down
  CHECK(pose.local[4] == inside);
}

TEST_CASE("gaze legibility: off by default (identical poses); on, the eyes stay in the range through blinks and darts") {
  auto plain = girlScene(nullptr, nullptr), off = girlScene(false, nullptr), on = girlScene(Json{{"rangeDeg", {16, 8}}}, nullptr);
  auto perCharacter = girlScene(nullptr, Json{{"rangeDeg", {16, 8}}}), optedOut = girlScene(true, false);
  const Skeleton& sk = plain->characters()[0].asset.skeleton;
  const int head = sk.find("head");
  std::vector<int> eyes;
  for (size_t i = 0; i < sk.bones.size(); ++i)
    if (sk.bones[i].name.rfind("eye.", 0) == 0) eyes.push_back(int(i));
  REQUIRE(head >= 0);
  REQUIRE(eyes.size() == 2);
  const std::string blink = "Blink";
  vec2 worstOn(0), worstOff(0), worstOnBlink(0), worstOffBlink(0);
  int blinkFrames = 0;
  bool same = true, sameCharacter = true, differs = false;
  for (int f = 1; f <= 400; ++f) {
    Pose a, b, c, d, e;
    const auto gPlain = plain->characterGlobals(0, f, &a);
    off->characterGlobals(0, f, &b);
    const auto gOn = on->characterGlobals(0, f, &c);
    perCharacter->characterGlobals(0, f, &d);
    optedOut->characterGlobals(0, f, &e);
    same = same && a.local == b.local && a.local == e.local;
    sameCharacter = sameCharacter && c.local == d.local;
    differs = differs || !(a.local == c.local);
    const bool blinking = on->morphControlWeight(0, blink, f) > 0.05f;
    blinkFrames += blinking;
    for (int eye : eyes) {
      const vec2 o = glm::abs(eyeAngles(gOn, eye, head)), p = glm::abs(eyeAngles(gPlain, eye, head));
      worstOn = glm::max(worstOn, o);
      worstOff = glm::max(worstOff, p);
      if (blinking) worstOnBlink = glm::max(worstOnBlink, o);
      if (plain->morphControlWeight(0, blink, f) > 0.05f) worstOffBlink = glm::max(worstOffBlink, p);
    }
  }
  MESSAGE("eye travel vs head, yaw / pitch deg: default " << worstOff.x << " / " << worstOff.y << " (in blinks " << worstOffBlink.x
          << " / " << worstOffBlink.y << "), legible " << worstOn.x << " / " << worstOn.y << " (in blinks " << worstOnBlink.x
          << " / " << worstOnBlink.y << ", " << blinkFrames << " blink frames)");
  CHECK(same);            // absent = false = a character's own false under a scene true
  CHECK(sameCharacter);   // the scene key and the character key do the same
  CHECK(differs);
  CHECK(blinkFrames > 20);
  CHECK(worstOn.x <= kRange.x + 0.01f);
  CHECK(worstOn.y <= kRange.y + 0.01f);
  CHECK(worstOnBlink.x <= kRange.x + 0.01f);
  CHECK(worstOnBlink.y <= kRange.y + 0.01f);
  CHECK(worstOff.x > kRange.x + 2.0f);  // what T-113 open point 3 saw: the default look goes past the lids' range
  CHECK(worstOff.y > kRange.y + 2.0f);
}

TEST_CASE("gaze legibility: scene key round trip and checks") {
  CHECK(!gazeLegibilityFromJson(Json()).value().enabled);
  CHECK(gazeLegibilityFromJson(true).value().enabled);
  const GazeLegibility g = gazeLegibilityFromJson(Json::parse(R"({"rangeDeg": [16, 8], "leadFrames": 4, "headPitchDeg": 12})")).value();
  CHECK(g.enabled);
  CHECK(g.rangeDeg == vec2(16, 8));
  CHECK(g.leadFrames == 4.0f);
  CHECK(g.turnFrames == 8.0f);
  CHECK(g.headPitchDeg == 12.0f);
  CHECK(g.headYawDeg < 0);  // the character's life.gaze.assistYawDeg
  // A character's key on top of the scene's: its fields win, the rest stays.
  const GazeLegibility c = gazeLegibilityFromJson(Json::parse(R"({"turnFrames": 5})"), g).value();
  CHECK(c.rangeDeg == vec2(16, 8));
  CHECK(c.turnFrames == 5.0f);
  CHECK(!gazeLegibilityFromJson(false, g).value().enabled);
  for (const char* bad : {R"("yes")", R"({"rangeDeg": [16]})", R"({"rangeDeg": [0, 8]})", R"({"leadFrames": -1})", R"({"range": [16, 8]})"})
    CHECK(!gazeLegibilityFromJson(Json::parse(bad)).has_value());

  Scene s;
  s.gazeLegibility = Json::parse(R"({"rangeDeg": [16, 8]})");
  CharacterDesc cd;
  cd.name = "who";
  cd.asset = "x.character.json";
  cd.gazeLegibility = false;
  s.characters.push_back(cd);
  const std::filesystem::path path = std::filesystem::temp_directory_path() / "t120_gaze_legibility.scene.json";
  REQUIRE(saveScene(s, path).has_value());
  auto back = loadScene(path);
  REQUIRE(back.has_value());
  CHECK(back->gazeLegibility == s.gazeLegibility);
  CHECK(back->characters[0].gazeLegibility == Json(false));
  Json j = sceneToJson(s);
  CHECK(!sceneToJson(Scene{}).contains("gazeLegibility"));  // an absent key stays absent
  j["gazeLegibility"] = Json::parse(R"({"rangeDeg": "wide"})");
  std::ofstream(path) << j.dump();
  CHECK(!loadScene(path).has_value());
  std::filesystem::remove(path);
}
