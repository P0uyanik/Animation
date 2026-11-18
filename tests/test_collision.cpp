// T-047: the collision system (scene/collision.h): one collision body per character, derived from the package (or
// read from its export/6 "collision" block), queried for clearance, and used by the arm planner (interaction.cpp) so
// that clip, hand-keyed and IK arms stay outside the body, smoothly, while contacts stay exact. T-082: the elbow
// swing limit (block field and scene override).
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
// Imported test packages (read only) and the engine (SDF) character: the three skeleton / mesh sources.
const char* kBoy = "boy_yellow_hoodie_1.0.0/character.json";
const char* kGirl = "girl_auburn_bun_glasses_m3/character.json";
const char* kGirlM2 = "girl_auburn_bun_glasses_m2/character.json";
const char* kSdf = "../../../content/characters/girl_white_hair.character.json";

Scene baseScene(const char* asset, int frames = 40) {
  Scene s;
  s.name = "collision test";
  s.path = kRoot / "tests/data/imported/scene.json";
  s.rate = FrameRate{24, 1};
  s.frameStart = 1;
  s.frameEnd = frames;
  CharacterDesc c;
  c.name = "a";
  c.asset = asset;
  c.life.enabled = false;
  s.characters.push_back(c);
  return s;
}

std::unique_ptr<SceneEvaluator> load(const Scene& scene) {
  auto ev = std::make_unique<SceneEvaluator>();
  auto r = ev->load(scene, EvalOptions{2.5f, 1.0f, false, 0});
  if (!r) FAIL(r.error().message);
  return ev;
}

std::vector<mat4> restGlobals(const Skeleton& sk) {
  std::vector<mat4> G(sk.bones.size());
  for (size_t b = 0; b < sk.bones.size(); ++b) G[b] = glm::translate(mat4(1), sk.bones[b].head);
  return G;
}

// The collision body the evaluator built for character 0 (fresh copy: valid even when planning was switched off).
CollisionBody bodyOf(const SceneEvaluator& ev) {
  const auto& ci = ev.characters()[0];
  return collisionBodyFor(ci.asset.collisionBlock, ci.asset.skeleton, ci.rig.meshes);
}

// A hand key that turns the right upper arm 40 degrees about the character's forward axis, across the body: the
// forearm (boy) or hand (girl) ends up 2 to 4 cm inside the collision body without planning (measured below).
Scene keyedIntoBody(const char* asset, bool planning) {
  Scene s = baseScene(asset);
  Json actions = Json::array({{{"type", "look"}, {"character", "a"}, {"start", 1}, {"target", {0, 1, 2}}}});
  if (!planning) actions.push_back({{"type", "collision"}, {"character", "a"}, {"enabled", false}});
  s.actions = actions;
  auto& t = s.animation.tracks["a/upperArm.R.rot"];
  t.setKey({1, vec3(0)});
  t.setKey({20, vec3(0, 0, 40)});
  t.setKey({40, vec3(0, 0, 40)});
  return s;
}

float angleDeg(quat a, quat b) { return glm::degrees(2.0f * std::acos(std::min(1.0f, std::abs(glm::dot(glm::normalize(a), glm::normalize(b)))))); }

}  // namespace

TEST_CASE("collision body: derived for every character source, closed torso sections and limb capsules, rest pose clear") {
  for (const char* asset : {kBoy, kGirl, kGirlM2, kSdf}) {
    auto ev = load(baseScene(asset));
    const Skeleton& sk = ev->characters()[0].asset.skeleton;
    const CollisionBody B = bodyOf(*ev);
    REQUIRE(B.valid);
    CHECK(B.source == "derived");  // the test packages have no export/6 block
    CHECK(B.sections.size() == 7);
    CHECK(B.sections.front().cap0);
    CHECK(B.sections.back().cap1);
    for (const CollisionSection& s : B.sections) {
      CHECK(s.r1 >= 0.02f);
      CHECK(s.r1 < 0.3f);
      CHECK(s.r2 >= 0.02f);
      CHECK(s.r2 < 0.3f);
    }
    REQUIRE(B.limbs.size() == 4);
    for (const CollisionLimb& l : B.limbs) {
      CHECK(l.r > 0.005f);
      CHECK(l.r < 0.08f);
      CHECK(glm::length(l.b - l.a) > 0.005f);
      CHECK(l.allowance <= 0.0f);
      // the imported packages model their arms away from the body: no rest contact; the engine character hangs its
      // arms against its skirt and keeps that rest depth as the allowance
      if (asset != kSdf) CHECK(l.allowance == 0.0f);
      CHECK(sk.bones[size_t(l.bone)].name.substr(0, l.name.find('.')) == l.name.substr(0, l.name.find('.')));
    }
    // the rest pose keeps the margin (by construction)
    const auto rest = restGlobals(sk);
    for (char side : {'L', 'R'}) {
      const Clearance c = limbClearance(B, rest, side);
      MESSAGE(asset << " " << side << ": rest clearance " << c.gap * 1000 << " mm (" << c.part << " / " << c.against << ")");
      CHECK(c.gap >= B.margin - 1e-4f);
    }
    // the evaluator plans with the same body
    REQUIRE(ev->clearanceModel(0));
    CHECK(ev->clearanceModel(0)->collision.limbs.size() == B.limbs.size());
  }
}

TEST_CASE("collision body: package block round trip, precedence over the derivation, bad blocks fall back") {
  auto ev = load(baseScene(kBoy));
  const auto& ci = ev->characters()[0];
  const Skeleton& sk = ci.asset.skeleton;
  const CollisionBody D = deriveCollisionBody(sk, ci.rig.meshes);
  Json block = collisionBodyToJson(D, sk);
  CHECK(block["format"] == "plush.collision_body");
  auto R = collisionBodyFromJson(block, sk);
  REQUIRE(R);
  CHECK(R->source == "package");
  REQUIRE(R->sections.size() == D.sections.size());
  REQUIRE(R->limbs.size() == D.limbs.size());
  for (size_t i = 0; i < D.sections.size(); ++i) {
    CHECK(R->sections[i].bone == D.sections[i].bone);
    CHECK(glm::distance(R->sections[i].p1, D.sections[i].p1) < 1e-6f);
    CHECK(R->sections[i].r1 == doctest::Approx(D.sections[i].r1));
  }
  for (size_t i = 0; i < D.limbs.size(); ++i) {
    CHECK(R->limbs[i].name == D.limbs[i].name);
    CHECK(R->limbs[i].side == D.limbs[i].side);
    CHECK(glm::distance(R->limbs[i].b, D.limbs[i].b) < 1e-6f);
    CHECK(R->limbs[i].allowance == doctest::Approx(D.limbs[i].allowance));
  }
  // the block wins over the derivation (a thicker hand is used as given)
  block["limbs"][1]["r"] = 0.05;
  const CollisionBody P = collisionBodyFor(block, sk, ci.rig.meshes);
  CHECK(P.source == "package");
  CHECK(P.limbs[1].r == doctest::Approx(0.05f));
  // a block that does not fit the skeleton is refused; the evaluator then derives the body and says so
  Json bad = collisionBodyToJson(D, sk);
  bad["sections"][0]["bone"] = "no_such_bone";
  CHECK_FALSE(collisionBodyFromJson(bad, sk));
  CHECK(collisionBodyFor(bad, sk, ci.rig.meshes).source == "derived");
  Json neg = collisionBodyToJson(D, sk);
  neg["limbs"][0]["r"] = -1;
  CHECK_FALSE(collisionBodyFromJson(neg, sk));
  CHECK_FALSE(collisionBodyFromJson(Json{{"format", "other"}}, sk));
}

TEST_CASE("collision queries: signed, 1-Lipschitz along a path, gradient points out of the body") {
  for (const char* asset : {kBoy, kGirl}) {
    auto ev = load(baseScene(asset));
    const Skeleton& sk = ev->characters()[0].asset.skeleton;
    const CollisionBody B = bodyOf(*ev);
    const auto rest = restGlobals(sk);
    const int hips = sk.find("hips"), chest = sk.find("chest");
    const vec3 belly = 0.5f * (sk.bones[size_t(hips)].head + sk.bones[size_t(chest)].head);
    // a point walked from the body's axis straight forward: inside, then crossing the surface once, then outside;
    // the gap never changes faster than the point moves (a distance), and its gradient points forward
    float prev = -1e9f;
    int crossings = 0;
    for (int i = 0; i <= 60; ++i) {
      const vec3 p = belly + vec3(0, 0, 0.005f * float(i));
      const Clearance c = segmentClearance(B, rest, p, p, 0.0f, 'R');
      if (i > 0) {
        CHECK(c.gap - prev <= 0.005f + 1e-5f);
        CHECK(c.gap >= prev - 1e-5f);  // moving out never gets deeper
        crossings += (prev < 0) != (c.gap < 0);
      }
      if (c.gap < 0 && i > 2) CHECK(c.push.z > 0.5f);
      prev = c.gap;
    }
    CHECK(crossings == 1);
    // a hand pushed into the belly is inside, and the push leads out (forward)
    std::vector<mat4> G = rest;
    const int hand = sk.find("hand.R");
    G[size_t(hand)] = glm::translate(mat4(1), belly + vec3(0, 0, 0.03f));
    const Clearance in = limbClearance(B, G, 'R');
    MESSAGE(asset << ": hand in the belly " << in.gap * 1000 << " mm, push " << in.push.x << " " << in.push.y << " " << in.push.z);
    CHECK(in.gap < -0.02f);
    CHECK(in.part == "hand.R");
    CHECK(in.push.z > 0.5f);
    // the swung clearance never reads worse than the unswung one (a swing of 0 is always a candidate)
    const BodyClearanceModel* M = ev->clearanceModel(0);
    REQUIRE(M);
    CHECK(swungArmGap(*M, G, 'R') >= armClearance(*M, G, 'R').gap - 1e-6f);
    CHECK(clearingSwing([](float t) { return t; }, 0.1f, 1.0f) == doctest::Approx(0.1309f).epsilon(0.01));  // first step >= need
    CHECK(clearingSwing([](float t) { return -t; }, 0.1f, 1.0f) < 0.0f);  // the other way round
  }
}

TEST_CASE("collision planning: a hand-keyed arm driven into the body is lifted out of it, smoothly; clear arms stay") {
  for (const char* asset : {kBoy, kGirl}) {
    auto off = load(keyedIntoBody(asset, false));
    auto on = load(keyedIntoBody(asset, true));
    for (const auto& w : on->warnings()) MESSAGE(w);
    const CollisionBody B = bodyOf(*on);
    const Skeleton& sk = on->characters()[0].asset.skeleton;
    float worstOff = 1e9f, worstOn = 1e9f;
    for (int f = 1; f <= 40; ++f) {
      worstOff = std::min(worstOff, limbClearance(B, off->characterGlobals(0, f), 'R').gap);
      worstOn = std::min(worstOn, limbClearance(B, on->characterGlobals(0, f), 'R').gap);
    }
    MESSAGE(asset << ": smallest right-arm clearance without planning " << worstOff * 1000 << " mm, with " << worstOn * 1000 << " mm");
    CHECK(worstOff < -0.015f);  // the case is real
    CHECK(worstOn >= 0.0f);     // touching at most, never inside
    // the lift is a generated track whose size changes by at most 1.5 degrees per frame (its direction may turn a
    // little as well): below the 2 degrees per frame the task allows
    const Track* lift = on->scene().animation.find("a/abduct.hand.R");
    REQUIRE(lift);
    float rate = 0;
    for (int f = 2; f <= 40; ++f) rate = std::max(rate, glm::length(lift->evaluate(f) - lift->evaluate(f - 1)));
    MESSAGE(asset << ": largest lift change " << glm::degrees(rate) << " deg/frame");
    CHECK(glm::degrees(rate) <= 2.0f);
    // the clear left arm is untouched: no lift track, the same bone rotations as without planning
    CHECK_FALSE(on->scene().animation.find("a/abduct.hand.L"));
    const int ul = sk.find("upperArm.L"), hl = sk.find("hand.L");
    for (int f : {1, 20, 40}) {
      const auto a = on->characterGlobals(0, f), b = off->characterGlobals(0, f);
      CHECK(angleDeg(glm::quat_cast(mat3(a[size_t(ul)])), glm::quat_cast(mat3(b[size_t(ul)]))) < 1e-3f);
      CHECK(glm::distance(vec3(a[size_t(hl)][3]), vec3(b[size_t(hl)][3])) < 1e-6f);
    }
  }
}

TEST_CASE("collision planning: the elbow swing turns the elbow about the shoulder-wrist axis, wrist and hand stay") {
  auto ev = load(baseScene(kBoy));
  const Skeleton& sk = ev->characters()[0].asset.skeleton;
  const int upper = sk.find("upperArm.R"), fore = sk.find("forearm.R"), hand = sk.find("hand.R");
  Pose pose = restPose(sk);
  Clip ik;
  const vec3 target = vec3(boneGlobals(sk, pose, mat4(1))[size_t(upper)][3]) + vec3(0.02f, -0.1f, 0.14f);
  ik.tracks["a/ik.hand.R"].setKey({0, target, Interp::Linear});
  applyConstraints(sk, ik, "a/", 0, mat4(1), pose, GazeLimits{});
  const auto G0 = boneGlobals(sk, pose, mat4(1));
  for (float theta : {0.3f, -0.6f}) {
    Pose p = pose;
    Clip c;
    c.tracks["a/swing.hand.R"].setKey({0, vec3(theta, 0, 0), Interp::Linear});
    applyArmPoles(sk, c, "a/", 0, mat4(1), p);
    const auto G1 = boneGlobals(sk, p, mat4(1));
    CHECK(glm::distance(vec3(G1[size_t(hand)][3]), vec3(G0[size_t(hand)][3])) < 1e-5f);
    CHECK(angleDeg(glm::quat_cast(mat3(G1[size_t(hand)])), glm::quat_cast(mat3(G0[size_t(hand)]))) < 0.01f);
    // the elbow turned by theta about the shoulder -> wrist axis
    const vec3 a(G0[size_t(upper)][3]), w(G0[size_t(hand)][3]), u = glm::normalize(w - a);
    auto perp = [&](vec3 e) { return glm::normalize((e - a) - u * glm::dot(e - a, u)); };
    const vec3 e0 = perp(vec3(G0[size_t(fore)][3])), e1 = perp(vec3(G1[size_t(fore)][3]));
    const float turned = std::atan2(glm::dot(glm::cross(e0, e1), u), glm::dot(e0, e1));
    CHECK(turned == doctest::Approx(theta).epsilon(1e-3));
  }
}

TEST_CASE("collision planning: the collision action is checked like any action") {
  Scene s = baseScene(kBoy);
  s.actions = Json::parse(R"([{"type": "collision", "character": "ghost", "enabled": false}])");
  SceneEvaluator ev;
  auto r = ev.load(s, EvalOptions{2.5f, 1.0f, false, 0});
  REQUIRE_FALSE(r);
  CHECK(r.error().message.find("ghost") != std::string::npos);
}

TEST_CASE("collision body: the elbow swing limit (T-082) is block data with a shared default and a scene override") {
  auto ev = load(baseScene(kBoy));
  const auto& ci = ev->characters()[0];
  const Skeleton& sk = ci.asset.skeleton;
  const CollisionBody D = deriveCollisionBody(sk, ci.rig.meshes);
  CHECK(glm::degrees(D.maxElbowSwing) == doctest::Approx(kDefaultMaxElbowSwingDeg));
  Json block = collisionBodyToJson(D, sk);
  CHECK(block["max_elbow_swing_deg"].get<float>() == doctest::Approx(kDefaultMaxElbowSwingDeg));
  block["max_elbow_swing_deg"] = 45;
  auto R = collisionBodyFromJson(block, sk);
  REQUIRE(R);
  CHECK(glm::degrees(R->maxElbowSwing) == doctest::Approx(45.0f));
  block.erase("max_elbow_swing_deg");  // optional: a T-047 block gets the shared default
  R = collisionBodyFromJson(block, sk);
  REQUIRE(R);
  CHECK(glm::degrees(R->maxElbowSwing) == doctest::Approx(kDefaultMaxElbowSwingDeg));
  for (float bad : {-1.0f, 150.0f}) {
    block["max_elbow_swing_deg"] = bad;
    CHECK_FALSE(collisionBodyFromJson(block, sk));
  }
  // the scene's collision action overrides it per character for the shot; a bad value is a load error
  Scene s = baseScene(kBoy);
  s.actions = Json::parse(R"([{"type": "collision", "character": "a", "maxElbowSwingDeg": 12}])");
  auto o = load(s);
  REQUIRE(o->clearanceModel(0));
  CHECK(glm::degrees(o->clearanceModel(0)->collision.maxElbowSwing) == doctest::Approx(12.0f));
  for (const char* bad : {R"([{"type": "collision", "character": "a", "maxElbowSwingDeg": 200}])",
                          R"([{"type": "collision", "character": "a", "maxElbowSwingDeg": "wide"}])"}) {
    Scene b = baseScene(kBoy);
    b.actions = Json::parse(bad);
    SceneEvaluator e;
    auto r = e.load(b, EvalOptions{2.5f, 1.0f, false, 0});
    REQUIRE_FALSE(r);
    CHECK(r.error().message.find("maxElbowSwingDeg") != std::string::npos);
  }
  // a limited swing never clears more than the full range
  const auto rest = restGlobals(sk);
  CHECK(swungArmGap(*o->clearanceModel(0), rest, 'R', glm::radians(5.0f)) <= swungArmGap(*o->clearanceModel(0), rest, 'R') + 1e-6f);
}
