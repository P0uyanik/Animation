// T-045: shared body mechanics (anim/body_mechanics.h) on both imported skeletons, a rig without clavicles and an
// engine-built character: shoulder participation, torso follow with follow-through, head stabilisation, weight shift
// with planted feet, pivot carry, graceful degradation, personality tuning, contacts and determinism.
#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <memory>

#include "scene/asset_library.h"
#include "scene/scene.h"

using namespace plush;
namespace fs = std::filesystem;

namespace {
const fs::path kRoot = PLUSH_SOURCE_DIR;
const char* const kBoy = "boy_yellow_hoodie_1.0.0/character.json";
const char* const kGirl = "girl_auburn_bun_glasses_m3/character.json";
const char* const kToy = "toy_fixture/character.json";
const char* const kSdf = "../../../content/characters/girl_white_hair.character.json";

Scene baseScene(int end = 120) {
  Scene s;
  s.name = "body mechanics test";
  s.path = kRoot / "tests/data/imported/scene.json";
  s.rate = FrameRate{24, 1};
  s.frameStart = 1;
  s.frameEnd = end;
  return s;
}
CharacterDesc who(const char* asset, Json body, bool life = false) {
  CharacterDesc c;
  c.name = "who";
  c.asset = asset;
  c.life.enabled = life;
  c.bodyMechanics = std::move(body);
  return c;
}
std::unique_ptr<SceneEvaluator> load(const Scene& scene) {
  auto ev = std::make_unique<SceneEvaluator>();
  auto r = ev->load(scene, EvalOptions{2.5f, 1.0f, false, 0});
  if (!r) FAIL(r.error().message);
  return ev;
}
std::unique_ptr<SceneEvaluator> one(const char* asset, Json body, Json actions = Json::array(), bool life = false, int end = 120) {
  Scene s = baseScene(end);
  s.characters.push_back(who(asset, std::move(body), life));
  s.actions = std::move(actions);
  return load(s);
}
int boneOf(const SceneEvaluator& ev, const char* name) { return ev.characters()[0].asset.skeleton.find(name); }
vec3 at(const SceneEvaluator& ev, const char* bone, double f) {
  const int b = boneOf(ev, bone);
  REQUIRE(b >= 0);
  return vec3(ev.characterGlobals(0, f)[size_t(b)][3]);
}
quat rotAt(const SceneEvaluator& ev, const char* bone, double f) {
  const int b = boneOf(ev, bone);
  REQUIRE(b >= 0);
  return glm::normalize(glm::quat_cast(mat3(ev.characterGlobals(0, f)[size_t(b)])));
}
float angleDeg(const quat& a, const quat& b) {
  return glm::degrees(2.0f * std::acos(std::clamp(std::abs(glm::dot(glm::normalize(a), glm::normalize(b))), 0.0f, 1.0f)));
}
// Forward (+z) lean of a bone's up axis, degrees.
float pitchDeg(const quat& q) {
  const vec3 up = q * vec3(0, 1, 0);
  return glm::degrees(std::atan2(up.z, up.y));
}
float yawDeg(const quat& q) {
  const vec3 f = q * vec3(0, 0, 1);
  return glm::degrees(std::atan2(f.x, f.z));
}
bool finite(const std::vector<mat4>& g) {
  for (const auto& m : g)
    for (int i = 0; i < 4; ++i)
      for (int k = 0; k < 4; ++k)
        if (!std::isfinite(m[i][k])) return false;
  return true;
}
// A forward reach of the right hand driven by IK keys: rest, reach out (frames 20-30), hold, back (70-80).
void addForwardReach(Scene& s, const SceneEvaluator& probe) {
  const vec3 sh = at(probe, "upperArm.R", 1), el = at(probe, "forearm.R", 1), wr = at(probe, "hand.R", 1);
  const float arm = glm::distance(sh, el) + glm::distance(el, wr);
  const vec3 target = sh + vec3(-0.1f, -0.25f, 0.92f) * arm;
  Track ik, w;
  ik.setKey({1, wr});
  ik.setKey({20, wr});
  ik.setKey({30, target});
  ik.setKey({70, target});
  ik.setKey({80, wr});
  w.setKey({1, vec3(0)});
  w.setKey({20, vec3(0)});
  w.setKey({24, vec3(1)});
  w.setKey({76, vec3(1)});
  w.setKey({80, vec3(0)});
  s.animation.tracks["who/ik.hand.R"] = ik;
  s.animation.tracks["who/ik.hand.R.weight"] = w;
}
}  // namespace

TEST_CASE("body mechanics: off by default; false and absent give identical poses") {
  const Json actions = Json::parse(R"([{"type": "clip", "character": "who", "clip": "wave", "start": 10}])");
  auto absent = one(kBoy, Json(), actions, true);
  auto off = one(kBoy, false, actions, true);
  CHECK_FALSE(absent->bodyMechanicsActive(0));
  CHECK_FALSE(off->bodyMechanicsActive(0));
  for (double f : {1.0, 17.5, 40.0, 90.0}) {
    Pose p;
    const auto a = absent->characterGlobals(0, f, &p), b = off->characterGlobals(0, f);
    CHECK(p.offset.empty());
    for (size_t i = 0; i < a.size(); ++i) CHECK(a[i] == b[i]);
  }
  // Round trip: the scene keeps the block as written.
  Scene s = baseScene();
  s.characters.push_back(who(kBoy, Json::parse(R"({"personality": "x", "torso": 0.5})")));
  const Json j = sceneToJson(s);
  CHECK(j["characters"][0]["bodyMechanics"]["torso"].get<float>() == doctest::Approx(0.5f));
  CHECK_FALSE(sceneToJson(baseScene()).dump().contains("bodyMechanics"));
}

TEST_CASE("body mechanics: clavicles shrug and protract with arm elevation and reach, within the rig limits") {
  for (const char* pkg : {kBoy, kGirl}) {
    CAPTURE(pkg);
    const Json actions = Json::parse(R"([{"type": "clip", "character": "who", "clip": "wave", "start": 10, "blendIn": 4}])");
    auto on = one(pkg, true, actions);
    auto off = one(pkg, false, actions);
    REQUIRE(on->bodyMechanicsActive(0));
    const BodyMechanicsRig& rig = *on->bodyMechanicsRig(0);
    REQUIRE(rig.clavicle[1] >= 0);
    const auto& params = *on->bodyMechanicsParams(0);
    const char* clav = on->characters()[0].asset.skeleton.bones[size_t(rig.clavicle[1])].name.c_str();
    // Find the frame of highest right-arm elevation in the wave.
    double peak = 10;
    float best = -1;
    for (double f = 10; f < 100; f += 1)
      if (float e = on->bodyDrivers(0, (long long)f).elev[1]; e > best) best = e, peak = f;
    MESSAGE(pkg << ": peak right-arm elevation above rest " << best << " deg at frame " << peak);
    CHECK(best > 60.0f);
    // Rest (before the wave): no shrug.
    const float restAngle = angleDeg(rotAt(*on, clav, 1), rotAt(*off, clav, 1));
    CHECK(restAngle < 1.0f);
    // Peak: the clavicle turns (shrug + protraction), bounded by the limits; the arm pivot rises.
    float maxAngle = 0, maxRise = 0;
    for (double f = 10; f < 100; f += 1) {
      maxAngle = std::max(maxAngle, angleDeg(rotAt(*on, clav, f), rotAt(*off, clav, f)));
      maxRise = std::max(maxRise, at(*on, "upperArm.R", f).y - at(*off, "upperArm.R", f).y);
    }
    MESSAGE(pkg << ": clavicle max " << maxAngle << " deg, arm pivot rise " << maxRise * 1000 << " mm");
    CHECK(maxAngle > 4.0f);
    CHECK(maxAngle <= params.shrugMaxDeg + params.protractMaxDeg + 0.5f);
    CHECK(maxRise > 0.003f);
    // The left (resting) clavicle stays (almost) where it was.
    // The left (resting) clavicle only rides on the chest (no shrug of its own).
    const char* clavL = on->characters()[0].asset.skeleton.bones[size_t(rig.clavicle[0])].name.c_str();
    CHECK(angleDeg(glm::inverse(rotAt(*on, "chest", peak)) * rotAt(*on, clavL, peak), quat(1, 0, 0, 0)) < 2.0f);
    // Proportional: a half-raised arm shrugs less than the peak.
    float half = 0;
    for (double f = 10; f < peak; f += 1)
      if (on->bodyDrivers(0, (long long)f).elev[1] < 0.5f * best) half = std::max(half, angleDeg(rotAt(*on, clav, f), rotAt(*off, clav, f)));
    CHECK(half < maxAngle);
  }
}

TEST_CASE("body mechanics: torso leans and twists into a reach with follow-through; head stabilised; hand on target") {
  for (const char* pkg : {kBoy, kGirl}) {
    CAPTURE(pkg);
    Scene s = baseScene();
    s.characters.push_back(who(pkg, true));
    auto probe = load(s);
    addForwardReach(s, *probe);
    auto on = load(s);
    s.characters[0].bodyMechanics = false;
    auto off = load(s);
    std::vector<float> lean, twist;
    for (int f = 1; f <= 110; ++f) {
      const quat c1 = rotAt(*on, "chest", f), c0 = rotAt(*off, "chest", f);
      lean.push_back(pitchDeg(c1) - pitchDeg(c0));
      twist.push_back(yawDeg(c1) - yawDeg(c0));
    }
    auto L = [&](int f) { return lean[size_t(f - 1)]; };
    const float peak = *std::max_element(lean.begin(), lean.end());
    const float hold = L(68);
    MESSAGE(pkg << ": chest lean peak " << peak << " deg, hold " << hold << ", twist hold " << twist[67] << ", back " << L(110));
    CHECK(hold > 2.0f);                // leans into the reach
    CHECK(twist[67] > 1.0f);           // right-hand reach: right shoulder forward (+yaw)
    CHECK(peak <= hold * 1.2f + 0.2f);  // small overshoot only
    CHECK(std::abs(L(110)) < 0.4f);     // settles back after the reach
    // Follow-through: the torso lags the arm (the arm is out at 30; the torso is not yet at its hold value).
    CHECK(L(28) < 0.9f * hold);
    // Head stabilisation: the head turns less than the chest.
    const float chestTurn = angleDeg(rotAt(*on, "chest", 68), rotAt(*off, "chest", 68));
    const float headTurn = angleDeg(rotAt(*on, "head", 68), rotAt(*off, "head", 68));
    MESSAGE(pkg << ": chest turn " << chestTurn << " deg, head turn " << headTurn << " deg");
    CHECK(headTurn < 0.75f * chestTurn);
    // The IK still lands the wrist on its target.
    const vec3 target = s.animation.evaluate("who/ik.hand.R", 50, vec3(0));
    CHECK(glm::distance(at(*on, "hand.R", 50), target) < 0.001f);
  }
}

TEST_CASE("body mechanics: weight shift moves the pelvis over the support leg, bends the free knee, feet stay planted") {
  for (const char* pkg : {kBoy, kGirl}) {
    CAPTURE(pkg);
    auto on = one(pkg, Json::parse(R"({"weightShift": 1.0, "energy": 0.5})"), Json::array(), false, 400);
    auto off = one(pkg, false, Json::array(), false, 400);
    float minX = 1, maxX = -1, footErr = 0, footRot = 0;
    float kneeDiffAtLeft = 0, kneeDiffAtRight = 0;
    for (int f = 1; f <= 400; f += 3) {
      const float dx = at(*on, "hips", f).x - at(*off, "hips", f).x;
      minX = std::min(minX, dx);
      maxX = std::max(maxX, dx);
      for (const char* foot : {"foot.L", "foot.R"}) {
        footErr = std::max(footErr, glm::distance(at(*on, foot, f), at(*off, foot, f)));
        footRot = std::max(footRot, angleDeg(rotAt(*on, foot, f), rotAt(*off, foot, f)));
      }
      auto knee = [&](const SceneEvaluator& ev, char s) {
        const std::string x(1, s);
        const vec3 a = at(ev, ("thigh." + x).c_str(), f), b = at(ev, ("shin." + x).c_str(), f), c = at(ev, ("foot." + x).c_str(), f);
        return glm::degrees(std::acos(std::clamp(glm::dot(glm::normalize(b - a), glm::normalize(c - b)), -1.0f, 1.0f)));
      };
      const float bendDiff = knee(*on, 'R') - knee(*on, 'L');  // > 0: right knee bent more
      if (dx > 0.6f * maxX && maxX > 0) kneeDiffAtLeft = std::max(kneeDiffAtLeft, bendDiff);
      if (dx < 0.6f * minX && minX < 0) kneeDiffAtRight = std::max(kneeDiffAtRight, -bendDiff);
      // The bent knee points forward.
      const vec3 a = at(*on, "thigh.R", f), b = at(*on, "shin.R", f), c = at(*on, "foot.R", f);
      const vec3 mid = glm::mix(a, c, glm::dot(b - a, c - a) / glm::dot(c - a, c - a));
      if (glm::distance(b, mid) > 0.002f) CHECK(b.z > mid.z);
    }
    MESSAGE(pkg << ": pelvis shift " << minX * 1000 << " .. " << maxX * 1000 << " mm; feet " << footErr * 1000 << " mm, "
                << footRot << " deg; free-knee extra bend " << kneeDiffAtLeft << " / " << kneeDiffAtRight << " deg");
    CHECK(maxX > 0.006f);
    CHECK(minX < -0.006f);
    CHECK(footErr < 0.001f);
    CHECK(footRot < 0.5f);
    CHECK(kneeDiffAtLeft > 1.0f);   // weight on the left: the right knee bends
    CHECK(kneeDiffAtRight > 1.0f);  // and the other way round
  }
}

TEST_CASE("body mechanics: arm and thigh pivots follow the torso and pelvis (pivot carry)") {
  Scene s = baseScene();
  s.characters.push_back(who(kBoy, Json::parse(R"({"weightShift": 0})")));
  Track bend;
  bend.setKey({1, vec3(15, 0, 0)});  // spine 15 degrees forward
  s.animation.tracks["who/spine.rot"] = bend;
  auto on = load(s);
  s.characters[0].bodyMechanics = false;
  auto off = load(s);
  const vec3 dOn = at(*on, "upperArm.L", 5) - at(*on, "chest", 5), dOff = at(*off, "upperArm.L", 5) - at(*off, "chest", 5);
  // Off: the unparented arm pivot stays at rest while the chest moves away; on: it rides on the chest.
  const BodyMechanicsRig& rig = *on->bodyMechanicsRig(0);
  const vec3 restRel = on->characters()[0].asset.skeleton.bones[size_t(rig.upper[0])].head -
                       on->characters()[0].asset.skeleton.bones[size_t(rig.chest)].head;
  const vec3 chestUp = rotAt(*on, "chest", 5) * vec3(0, 1, 0);
  MESSAGE("arm pivot relative to chest: on " << glm::length(dOn - rotAt(*on, "chest", 5) * restRel) * 1000 << " mm from carried, off "
                                              << glm::length(dOff - rotAt(*off, "chest", 5) * restRel) * 1000 << " mm");
  CHECK(glm::length(dOn - rotAt(*on, "chest", 5) * restRel) < 0.002f);
  CHECK(glm::length(dOff - rotAt(*off, "chest", 5) * restRel) > 0.01f);
  CHECK(chestUp.z > 0.2f);
  // The thighs ride on the pelvis: the hips' roll in a weight shift moves the thigh pivots (feet still planted).
  auto ws = one(kBoy, Json::parse(R"({"weightShift": 1})"), Json::array(), false, 300);
  float maxDy = 0;
  for (int f = 1; f < 300; f += 5) maxDy = std::max(maxDy, std::abs(at(*ws, "thigh.L", f).y - at(*ws, "thigh.R", f).y));
  CHECK(maxDy > 0.002f);
}

TEST_CASE("body mechanics: rigs without clavicles, spine segments or legs skip those parts without warnings") {
  for (const char* pkg : {kToy, kSdf}) {
    CAPTURE(pkg);
    const Json actions = Json::parse(R"([{"type": "clip", "character": "who", "clip": "wave", "start": 10}])");
    auto ev = one(pkg, true, actions, true);
    // (The toy hand has no finger roles: the clip itself reports those; the body layer adds nothing.)
    for (const auto& w : ev->warnings()) CHECK(w.find("body") == std::string::npos);
    REQUIRE(ev->bodyMechanicsActive(0));
    const BodyMechanicsRig& rig = *ev->bodyMechanicsRig(0);
    CHECK(rig.clavicle[0] < 0);
    CHECK(rig.clavicle[1] < 0);
    for (double f : {1.0, 20.5, 45.0, 90.0}) CHECK(finite(ev->characterGlobals(0, f)));
  }
  // A bare skeleton (no roles at all) is simply left alone.
  Skeleton sk;
  sk.bones.push_back({"root", -1, vec3(0)});
  sk.bones.push_back({"tip", 0, vec3(0, 1, 0)});
  BodyMechanicsParams p;
  p.enabled = true;
  Pose pose = restPose(sk);
  const BodyMechanicsRig rig = bindBodyMechanics(sk, BodyMechanicsRigProfile{});
  applyBodyMechanics(sk, rig, p, BodyMechanicsInput{}, pose);
  CHECK(pose.local[0] == quat(1, 0, 0, 0));
  CHECK(pose.local[1] == quat(1, 0, 0, 0));
  CHECK(pose.rootOffset == vec3(0));
}

TEST_CASE("body mechanics: personality profiles tune the layer; missing fields stay neutral") {
  auto boy = one(kBoy, Json::parse(R"({"personality": "boy_yellow_hoodie"})"));
  auto girl = one(kGirl, Json::parse(R"({"personality": "girl_auburn_bun_glasses"})"));
  CHECK(boy->warnings().empty());
  CHECK(girl->warnings().empty());
  const auto& b = *boy->bodyMechanicsParams(0);
  const auto& g = *girl->bodyMechanicsParams(0);
  CHECK(b.slouch == doctest::Approx(0.4f));
  CHECK(b.shouldersForward == doctest::Approx(0.4f));
  CHECK(b.headPitchDeg == doctest::Approx(12.0f));
  CHECK(b.energy == doctest::Approx(0.3f));
  CHECK(b.settleFrames == doctest::Approx(10.0f));
  CHECK(g.slouch == doctest::Approx(0.0f));
  CHECK(g.energy == doctest::Approx(0.65f));
  CHECK(g.settleFrames == doctest::Approx(13.0f));
  CHECK(g.weightShift == doctest::Approx(0.2f));
  // Boy: chest pitched forward at rest (slouch); girl: upright.
  auto boyOff = one(kBoy, false), girlOff = one(kGirl, false);
  const float boySlouch = pitchDeg(rotAt(*boy, "chest", 1)) - pitchDeg(rotAt(*boyOff, "chest", 1));
  const float girlSlouch = pitchDeg(rotAt(*girl, "chest", 1)) - pitchDeg(rotAt(*girlOff, "chest", 1));
  MESSAGE("rest chest pitch: boy " << boySlouch << " deg, girl " << girlSlouch << " deg");
  CHECK(boySlouch > 3.0f);
  CHECK(std::abs(girlSlouch) < 0.5f);
  // Scene overrides win over the profile.
  auto over = one(kBoy, Json::parse(R"({"personality": "boy_yellow_hoodie", "slouch": 0.1})"));
  CHECK(over->bodyMechanicsParams(0)->slouch == doctest::Approx(0.1f));
  // An unknown profile: one warning, neutral tuning.
  auto missing = one(kBoy, Json::parse(R"({"personality": "no_such_profile"})"));
  CHECK(missing->warnings().size() == 1);
  CHECK(missing->bodyMechanicsParams(0)->slouch == 0.0f);
  // Neutral params: a profile without the sections changes nothing.
  BodyMechanicsParams neutral, mapped;
  applyPersonalityToBodyMechanics(mapped, Json::object());
  CHECK(mapped.slouch == neutral.slouch);
  CHECK(mapped.settleFrames == neutral.settleFrames);
}

TEST_CASE("body mechanics: follow kernel and idle weight shift are well formed") {
  for (float os : {0.0f, 0.04f, 0.08f}) {
    const auto k = followKernel(2.0f, 12.0f, os);
    float sum = 0;
    for (float x : k) sum += x;
    CHECK(sum == doctest::Approx(1.0f));
    CHECK(k[0] == 0.0f);  // delayed
    // Step response overshoot close to the requested one.
    float acc = 0, peak = 0;
    for (float x : k) acc += x, peak = std::max(peak, acc);
    CHECK(peak - 1.0f <= os + 0.03f);
  }
  BodyMechanicsParams p;
  p.weightShift = 1;
  float prev = idleWeightShift(0, p), maxStep = 0, lo = 1, hi = -1;
  for (double t = 0.01; t < 60; t += 0.01) {
    const float v = idleWeightShift(t, p);
    maxStep = std::max(maxStep, std::abs(v - prev));
    lo = std::min(lo, v), hi = std::max(hi, v);
    prev = v;
  }
  CHECK(maxStep < 0.03f);  // continuous
  CHECK(lo < -0.5f);
  CHECK(hi > 0.5f);
  p.weightShift = 0;
  CHECK(idleWeightShift(3.0, p) == 0.0f);
}

TEST_CASE("body mechanics: random access is deterministic") {
  const Json actions = Json::parse(R"([{"type": "clip", "character": "who", "clip": "wave", "start": 10}])");
  auto a = one(kGirl, true, actions, true);
  auto b = one(kGirl, true, actions, true);
  const auto g40 = a->characterGlobals(0, 40.5);
  a->characterGlobals(0, 10);
  a->characterGlobals(0, 80);
  const auto again = a->characterGlobals(0, 40.5);
  const auto fresh = b->characterGlobals(0, 40.5);
  for (size_t i = 0; i < g40.size(); ++i) {
    CHECK(g40[i] == again[i]);
    CHECK(g40[i] == fresh[i]);
  }
}

namespace {
PropDesc cupFor(const SceneEvaluator& probe, float yawCupDeg, vec3 offsetFromShoulder) {
  PropDesc cup;
  cup.name = "cup";
  cup.id = "prop.felt_cup";
  const vec3 shoulder = at(probe, "upperArm.R", 1), elbow = at(probe, "forearm.R", 1);
  const float arm = glm::distance(shoulder, elbow) + glm::distance(elbow, at(probe, "hand.R", 1));
  const vec3 grip = shoulder + offsetFromShoulder * arm;
  const mat4 rot = assetTransformMatrix({vec3(0), vec3(0, yawCupDeg, 0), vec3(1)});
  const PropAsset asset = loadAsset(kRoot / "content/assets/felt_cup.asset.json").value();
  cup.transform.translation = grip - vec3(rot * vec4(asset.sockets.at("grip").translation, 0));
  cup.transform.rotationDeg = {0, yawCupDeg, 0};
  return cup;
}
vec3 socketWorld(const SceneEvaluator& ev, const std::string& socket, double f) {
  const PropAsset asset = loadAsset(kRoot / "content/assets/felt_cup.asset.json").value();
  return vec3((ev.propWorld(0, f) * assetTransformMatrix(asset.sockets.at(socket)))[3]);
}
}  // namespace

TEST_CASE("body mechanics: hand contacts in interaction actions stay within 5 mm with the layer on") {
  for (const char* pkg : {kBoy, kGirl}) {
    CAPTURE(pkg);
    for (const char* body : {"true", R"({"personality": "boy_yellow_hoodie"})", R"({"personality": "girl_auburn_bun_glasses"})"}) {
      CAPTURE(body);
      Scene scene = baseScene(96);
      scene.characters.push_back(who(pkg, Json::parse(body), true));
      auto probe = load(scene);
      scene.props.push_back(cupFor(*probe, 180, vec3(0.04f, -0.45f, 0.85f)));
      const vec3 place0 = scene.props[0].transform.translation;
      scene.actions = Json::parse(R"([
          {"type": "grasp", "character": "who", "hand": "R", "prop": "cup", "start": 5, "contact": 20},
          {"type": "hold", "character": "who", "hand": "R", "start": 22, "end": 36, "by": [0, 0.06, 0.02]},
          {"type": "place", "character": "who", "hand": "R", "start": 40, "contact": 54, "end": 68, "at": [0, 0, 0]}])");
      scene.actions[2]["at"] = {place0.x + 0.02f, place0.y, place0.z + 0.01f};
      auto ev = load(scene);
      const float d = glm::distance(ev->handGripPoint(0, 'R', 20), socketWorld(*ev, "grip", 20));
      const vec3 target(place0.x + 0.02f, place0.y, place0.z + 0.01f);
      const float dp = glm::distance(socketWorld(*ev, "place", 54), target);
      MESSAGE(pkg << " " << body << ": palm to grip at contact " << d * 1000 << " mm, place " << dp * 1000 << " mm");
      CHECK(d < 0.005f);
      CHECK(dp < 0.005f);
      CHECK(glm::distance(vec3(ev->propWorld(0, 19)[3]), place0) < 1e-5f);
    }
  }
}
