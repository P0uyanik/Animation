// T-191: character-character body clearance. Characters whose collision action sets "bodyClearance" lean their upper
// body away from other characters' body parts (interaction.cpp, finishInteractions; applyBodyLean in the pose path).
// Off (the default) nothing changes; on, the gap opens by a rate-limited lean within the limit, the hips and legs
// stay, IK-held wrists stay on their targets.
#include <doctest/doctest.h>

#include <filesystem>
#include <memory>

#include "scene/collision.h"
#include "scene/interaction.h"
#include "scene/scene.h"

using namespace plush;
namespace fs = std::filesystem;

namespace {

const fs::path kRoot = PLUSH_SOURCE_DIR;
const char* kBoy = "boy_yellow_hoodie_1.0.0/character.json";
const char* kGirl = "girl_auburn_bun_glasses_m3/character.json";
constexpr float kNear = 0.2f;  // half the distance between the two (their heads and shoulders meet when they bow in)

CharacterDesc character(const std::string& name, const char* asset, vec3 position, float yawDeg) {
  CharacterDesc c;
  c.name = name;
  c.asset = asset;
  c.position = position;
  c.yawDeg = yawDeg;
  c.life.enabled = false;
  return c;
}

// Two characters face to face, both looking down at a point between them: the heads bow in until they meet (the
// T-096 case), so their bodies pass through each other without clearance.
Scene leanIn(float halfDistance, const Json& extraActions = Json::array()) {
  Scene s;
  s.name = "body clearance test";
  s.path = kRoot / "tests/data/imported/scene.json";
  s.rate = FrameRate{24, 1};
  s.frameStart = 1;
  s.frameEnd = 48;
  s.characters.push_back(character("a", kBoy, vec3(-halfDistance, 0, 0), 90));
  s.characters.push_back(character("b", kGirl, vec3(halfDistance, 0, 0), -90));
  s.actions = Json::parse(R"([
      {"type": "look", "character": "a", "start": 1, "end": 48, "target": [0.0, 0.5, 0.0]},
      {"type": "look", "character": "b", "start": 1, "end": 48, "target": [0.0, 0.5, 0.0]}])");
  for (const auto& a : extraActions) s.actions.push_back(a);
  return s;
}

std::unique_ptr<SceneEvaluator> load(const Scene& scene) {
  auto ev = std::make_unique<SceneEvaluator>();
  auto r = ev->load(scene, EvalOptions{2.5f, 1.0f, false, 0});
  if (!r) FAIL(r.error().message);
  return ev;
}

float bodyGapAt(const SceneEvaluator& ev, double f) {
  static thread_local std::vector<BodyParts> parts;
  parts.clear();
  for (const auto& ci : ev.characters()) parts.push_back(deriveBodyParts(ci.asset.skeleton, ci.rig.meshes));
  return bodyGap(parts[0], ev.characterGlobals(0, f), parts[1], ev.characterGlobals(1, f),
                 [](const std::string& x, const std::string& y) { return x.rfind("hand", 0) == 0 && y.rfind("hand", 0) == 0; })
      .gap;
}

Json clearanceAction(const char* who, Json extra = Json::object()) {
  Json a = {{"type", "collision"}, {"character", who}, {"bodyClearance", true}};
  for (const auto& [k, v] : extra.items()) a[k] = v;
  return a;
}

}  // namespace

TEST_CASE("body clearance: off by default, and switched off it changes nothing (T-191)") {
  auto off = load(leanIn(0.28f));
  auto no = load(leanIn(0.28f, Json::array({Json{{"type", "collision"}, {"character", "a"}, {"bodyClearance", false}},
                                            Json{{"type", "collision"}, {"character", "b"}, {"bodyClearance", false}}})));
  CHECK(off->scene().animation.find("a/bodyLean") == nullptr);
  CHECK(no->scene().animation.find("a/bodyLean") == nullptr);
  CHECK(no->scene().animation.find("b/bodyLean") == nullptr);
  for (int f : {1, 12, 24, 36, 48})
    for (size_t c = 0; c < 2; ++c) {
      const auto G0 = off->characterGlobals(c, f), G1 = no->characterGlobals(c, f);
      for (size_t b = 0; b < G0.size(); ++b) CHECK(G0[b] == G1[b]);  // bit-identical
    }
}

TEST_CASE("body clearance: the options are checked (T-191)") {
  for (const Json& bad : {Json{{"bodyClearance", "yes"}}, Json{{"bodyClearanceMm", 80}}, Json{{"bodyLeanMaxDeg", 45}},
                          Json{{"bodyClearanceMm", "ten"}}}) {
    CAPTURE(bad.dump());
    Json a = {{"type", "collision"}, {"character", "a"}};
    for (const auto& [k, v] : bad.items()) a[k] = v;
    SceneEvaluator ev;
    CHECK(!ev.load(leanIn(0.28f, Json::array({a})), EvalOptions{2.5f, 1.0f, false, 0}));
  }
}

TEST_CASE("body clearance: leaning in characters lean away, rate limited, within the limit; hips and legs stay (T-191)") {
  auto off = load(leanIn(kNear));
  float offGap = 1e9f;
  for (int f = 1; f <= 48; ++f) offGap = std::min(offGap, bodyGapAt(*off, f));
  MESSAGE("without body clearance: closest body parts " << offGap * 1000 << " mm");
  REQUIRE(offGap < 0.0f);  // the case is real

  auto on = load(leanIn(kNear, Json::array({clearanceAction("a", {{"bodyLeanMaxDeg", 20}}), clearanceAction("b", {{"bodyLeanMaxDeg", 20}})})));
  for (const auto& w : on->warnings()) MESSAGE(w);
  const Clip& clip = on->scene().animation;
  REQUIRE(clip.find("a/bodyLean") != nullptr);
  REQUIRE(clip.find("b/bodyLean") != nullptr);
  float onGap = 1e9f, lean = 0, rate = 0;
  for (int f = 1; f <= 48; ++f) {
    onGap = std::min(onGap, bodyGapAt(*on, f));
    for (const char* t : {"a/collision.bodyLean.b", "b/collision.bodyLean.a"}) {
      lean = std::max(lean, clip.evaluate(t, f, vec3(0)).x);
      if (f > 1) rate = std::max(rate, std::abs(clip.evaluate(t, f, vec3(0)).x - clip.evaluate(t, f - 1, vec3(0)).x));
    }
    for (size_t c = 0; c < 2; ++c) {  // hips and legs where they were
      const auto G0 = off->characterGlobals(c, f), G1 = on->characterGlobals(c, f);
      const Skeleton& sk = on->characters()[c].asset.skeleton;
      for (const char* b : {"hips", "thigh.L", "shin.R", "foot.L"}) {
        const int i = sk.find(b);
        REQUIRE(i >= 0);
        CHECK(glm::distance(vec3(G0[size_t(i)][3]), vec3(G1[size_t(i)][3])) < 1e-4f);
      }
    }
  }
  MESSAGE("with body clearance: closest " << onGap * 1000 << " mm, lean up to " << lean << " deg, rate " << rate << " deg/frame");
  CHECK(lean > 0.5f);
  CHECK(lean <= 20.0f + 1e-3f);
  CHECK(rate <= 0.6f + 1e-3f);
  CHECK(onGap > offGap + 0.02f);  // clearly opened
  if (onGap < kBodyClearance - 0.0005f) {  // what the limit leaves is said
    bool said = false;
    for (const auto& w : on->warnings()) said = said || w.find("the bodies of 'a' and 'b'") != std::string::npos;
    CHECK(said);
  }
}

TEST_CASE("body clearance: only the characters that opted in lean (T-191)") {
  auto on = load(leanIn(kNear, Json::array({clearanceAction("b")})));
  const Clip& clip = on->scene().animation;
  CHECK(clip.find("a/bodyLean") == nullptr);
  CHECK(clip.find("b/bodyLean") != nullptr);
  CHECK(clip.find("b/collision.bodyLean.a") != nullptr);
  CHECK(clip.find("a/collision.bodyLean.b") == nullptr);
}

TEST_CASE("body clearance: the lean turns the torso, an IK-held wrist stays, a clip arm rides along (T-191)") {
  auto ev = load(leanIn(0.5f));
  const Skeleton& sk = ev->characters()[0].asset.skeleton;
  const int head = sk.find("head"), hl = sk.find("hand.L"), hr = sk.find("hand.R"), hips = sk.find("hips");
  REQUIRE(head >= 0);
  REQUIRE(hl >= 0);
  Clip clip;
  // ~11.5 deg towards the left hand (+x): the hanging left arm can still reach its wrist from the moved shoulder
  clip.tracks["x/bodyLean"].keys = {{1.0, vec3(0, 0, -0.2f), Interp::Linear}};
  clip.tracks["x/ik.hand.L"].keys = {{1.0, vec3(0), Interp::Linear}};
  const mat4 world(1);
  const Pose rest = restPose(sk);
  const std::vector<mat4> G0 = boneGlobals(sk, rest, world);
  Pose p = rest;
  applyBodyLean(sk, clip, "x/", 1.0, world, p);
  const std::vector<mat4> G1 = boneGlobals(sk, p, world);
  CHECK(glm::distance(vec3(G0[size_t(head)][3]), vec3(G1[size_t(head)][3])) > 0.03f);  // the upper body leans
  CHECK(glm::distance(vec3(G0[size_t(hips)][3]), vec3(G1[size_t(hips)][3])) < 1e-5f);
  CHECK(glm::distance(vec3(G0[size_t(hl)][3]), vec3(G1[size_t(hl)][3])) < 0.002f);  // IK wrist stays
  CHECK(glm::distance(vec3(G0[size_t(hr)][3]), vec3(G1[size_t(hr)][3])) > 0.02f);   // clip arm rides along
  // no track: nothing changes
  Pose q = rest;
  applyBodyLean(sk, Clip{}, "x/", 1.0, world, q);
  for (size_t b = 0; b < q.local.size(); ++b) CHECK(q.local[b] == rest.local[b]);
}

TEST_CASE("body clearance: the arm yield turns only that arm about its shoulder (T-191)") {
  auto ev = load(leanIn(0.5f));
  const Skeleton& sk = ev->characters()[0].asset.skeleton;
  const int hl = sk.find("hand.L"), hr = sk.find("hand.R"), ul = sk.find("upperArm.L"), head = sk.find("head");
  REQUIRE(hl >= 0);
  REQUIRE(ul >= 0);
  Clip clip;
  clip.tracks["x/armYield.hand.L"].keys = {{1.0, vec3(0, 0, 0.3f), Interp::Linear}};
  const mat4 world(1);
  const Pose rest = restPose(sk);
  const std::vector<mat4> G0 = boneGlobals(sk, rest, world);
  Pose p = rest;
  applyArmYield(sk, clip, "x/", 1.0, world, p);
  const std::vector<mat4> G1 = boneGlobals(sk, p, world);
  CHECK(glm::distance(vec3(G0[size_t(ul)][3]), vec3(G1[size_t(ul)][3])) < 1e-5f);  // the shoulder joint stays
  CHECK(glm::distance(vec3(G0[size_t(hl)][3]), vec3(G1[size_t(hl)][3])) > 0.02f);  // the arm swings
  CHECK(glm::distance(vec3(G0[size_t(hr)][3]), vec3(G1[size_t(hr)][3])) < 1e-5f);  // the other arm and the head stay
  CHECK(glm::distance(vec3(G0[size_t(head)][3]), vec3(G1[size_t(head)][3])) < 1e-5f);
  Pose q = rest;
  applyArmYield(sk, Clip{}, "x/", 1.0, world, q);
  for (size_t b = 0; b < q.local.size(); ++b) CHECK(q.local[b] == rest.local[b]);
}
