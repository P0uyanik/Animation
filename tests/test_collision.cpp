// T-047: the collision system (scene/collision.h): one collision body per character, derived from the package (or
// read from its export/6 "collision" block), queried for clearance, and used by the arm planner (interaction.cpp) so
// that clip, hand-keyed and IK arms stay outside the body, smoothly, while contacts stay exact. T-082: the elbow
// swing limit (block field and scene override).
#include <doctest/doctest.h>

#include <filesystem>
#include <fstream>
#include <memory>
#include <set>

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

// ---------------------------------------------------------------------------------------------------------- T-096
// Head and hair volumes: opt-in (never derived or written unless asked), fitted to the head-carried vertices of every
// character source (packages and the engine character), covering every one of them and close to the surface.
TEST_CASE("head volumes: opt-in, cover the head-carried vertices closely, never in the package block (T-096)") {
  for (const char* asset : {kBoy, kGirl, kGirlM2, kSdf}) {
    auto ev = load(baseScene(asset));
    const auto& ci = ev->characters()[0];
    const Skeleton& sk = ci.asset.skeleton;
    CollisionBody body = bodyOf(*ev);
    CHECK(body.heads.empty());  // default: no head volumes
    const Json before = collisionBodyToJson(body, sk);
    addHeadVolumes(body, sk, ci.rig.meshes);
    REQUIRE(!body.heads.empty());
    CHECK(collisionBodyToJson(body, sk) == before);  // the block (export/6 parity) never carries them
    const int head = sk.find("head");
    std::vector<char> underHead(sk.bones.size(), 0);
    for (size_t b = 0; b < sk.bones.size(); ++b)
      for (int k = int(b); k >= 0; k = sk.bones[size_t(k)].parent) underHead[b] |= k == head;
    const std::vector<mat4> G = restGlobals(sk);
    const auto spheres = headSpheres(body, G);
    float rmax = 0;
    for (const auto& [c, r] : spheres) rmax = std::max(rmax, r);
    size_t n = 0, covered = 0;
    for (const SkinnedMesh& m : ci.rig.meshes)
      for (size_t v = 0; v < m.rest.positions.size(); v += 7) {
        float w = 0;
        for (int k = 0; k < 4; ++k)
          if (m.joints[v][k] >= 0 && underHead[size_t(m.joints[v][k])]) w += m.weights[v][k];
        if (w < 0.5f) continue;
        ++n;
        for (const auto& [c, r] : spheres)
          if (glm::distance(c, m.rest.positions[v]) <= r + 1e-5f) {
            ++covered;
            break;
          }
      }
    MESSAGE(asset << ": " << spheres.size() << " head volumes, largest radius " << rmax * 1000 << " mm, " << covered << "/" << n << " vertices covered");
    CHECK(covered == n);
    CHECK(rmax <= 0.5f * std::sqrt(3.0f) * kHeadCell + 1e-4f);  // a sphere per voxel: the surface within ~1 cm
  }
}

TEST_CASE("head volumes: the gap between two heads is signed and follows their distance (T-096)") {
  auto ev = load(baseScene(kBoy));
  const auto& ci = ev->characters()[0];
  CollisionBody body = bodyOf(*ev), none = bodyOf(*ev);
  addHeadVolumes(body, ci.asset.skeleton, ci.rig.meshes);
  const std::vector<mat4> G = restGlobals(ci.asset.skeleton);
  CHECK(headGap(body, G, none, G).gap > 1e8f);  // no head volumes: nothing to keep apart
  float last = -1e9f;
  for (float d : {0.5f, 0.6f, 0.8f, 1.0f}) {  // the same head shifted sideways by d: apart, the gap is exact
    std::vector<mat4> H = G;
    for (auto& m : H) m = glm::translate(mat4(1), vec3(d, 0, 0)) * m;
    const HeadGap g = headGap(body, H, body, G);
    MESSAGE("shift " << d << " m: gap " << g.gap * 1000 << " mm");
    CHECK(g.gap > 0.0f);
    if (last > -1e8f) CHECK(g.gap - last == doctest::Approx(0.2f).epsilon(0.1));  // follows the distance 1:1 sideways
    last = g.gap;
    CHECK(glm::distance(g.pointA - g.pointB, g.dir * g.gap) < 1e-4f);
    CHECK(g.dir.x > 0.9f);  // from b's head towards a's
  }
  for (float d : {0.0f, 0.1f, 0.25f}) {  // overlapping heads: negative (a shell: not a depth)
    std::vector<mat4> H = G;
    for (auto& m : H) m = glm::translate(mat4(1), vec3(d, 0, 0)) * m;
    CHECK(headGap(body, H, body, G).gap < 0.0f);
  }
}

TEST_CASE("interaction options: the scene switch is checked, saved as written and off by default (T-096)") {
  CHECK(!interactionOptionsFromJson(Json(nullptr))->headVolumes);
  CHECK(interactionOptionsFromJson(Json{{"headVolumes", true}})->headClearance == doctest::Approx(0.03f));  // default
  auto o = interactionOptionsFromJson(Json{{"headVolumes", true}, {"headClearance", 0.02}, {"followSharedProp", true}, {"visibleGrip", true}});
  REQUIRE(o);
  CHECK(o->headVolumes);
  CHECK(o->headClearance == doctest::Approx(0.02f));
  CHECK(o->followSharedProp);
  CHECK(o->visibleGrip);
  CHECK(!interactionOptionsFromJson(Json::array()));
  CHECK(!interactionOptionsFromJson(Json{{"headVolume", true}}));  // a typo is an error, not silently off
  CHECK(!interactionOptionsFromJson(Json{{"headVolumes", 1}}));
  CHECK(!interactionOptionsFromJson(Json{{"headClearance", 0.5}}));
  CHECK(!interactionOptionsFromJson(Json{{"headClearance", -0.01}}));
  // Saved as written; a bad block is a load error.
  Scene s = baseScene(kBoy);
  s.interaction = Json{{"visibleGrip", true}};
  CHECK(sceneToJson(s)["interaction"] == s.interaction);
  CHECK(!sceneToJson(baseScene(kBoy)).contains("interaction"));
  const fs::path tmp = fs::temp_directory_path() / "t096_bad_interaction.scene.json";
  Json j = sceneToJson(s);
  j["interaction"] = {{"followSharedProp", "yes"}};
  { std::ofstream(tmp) << j.dump(); }
  CHECK(!loadScene(tmp));
  fs::remove(tmp);
}

// Zero change by default: an absent block, an empty one and one with every option off evaluate identically.
TEST_CASE("interaction options: every option off is exactly the behaviour before T-096") {
  Scene base = keyedIntoBody(kBoy, true);
  base.actions.push_back({{"type", "look"}, {"character", "a"}, {"start", 10}, {"target", {0.3, 0.6, 0.5}}});
  auto ref = load(base);
  for (const Json& block : {Json::object(), Json{{"headVolumes", false}, {"followSharedProp", false}, {"visibleGrip", false}}}) {
    Scene s = base;
    s.interaction = block;
    auto ev = load(s);
    CHECK(ev->warnings() == ref->warnings());
    for (int f = 1; f <= 40; ++f) {
      const auto A = ref->characterGlobals(0, f), B = ev->characterGlobals(0, f);
      for (size_t b = 0; b < A.size(); ++b) CHECK(A[b] == B[b]);
    }
  }
}

// ---------------------------------------------------------------------------------------------------------- T-191
// Body-part capsules (character-character contact): exact segment distance, a fit that covers every body role and
// most of each part's own rest vertices, and a signed gap whose sign, depth and direction follow the geometry.
TEST_CASE("body parts: segment distance is exact (T-191)") {
  vec3 ca, cb;
  CHECK(segmentSegment(vec3(0, 0, 0), vec3(1, 0, 0), vec3(0.5f, 1, -1), vec3(0.5f, 1, 1), ca, cb) == doctest::Approx(1.0f));
  CHECK(ca.x == doctest::Approx(0.5f));
  CHECK(cb.z == doctest::Approx(0.0f).epsilon(1e-5));
  // parallel, overlapping
  CHECK(segmentSegment(vec3(0, 0, 0), vec3(1, 0, 0), vec3(0.5f, 0.2f, 0), vec3(2, 0.2f, 0), ca, cb) == doctest::Approx(0.2f));
  // end to end, beyond the segments
  CHECK(segmentSegment(vec3(0, 0, 0), vec3(1, 0, 0), vec3(1.3f, 0, 0), vec3(2, 0, 0), ca, cb) == doctest::Approx(0.3f));
  // points (degenerate segments)
  CHECK(segmentSegment(vec3(0, 0, 0), vec3(0, 0, 0), vec3(0, 0.4f, 0), vec3(0, 0.4f, 0), ca, cb) == doctest::Approx(0.4f));
  // point against segment, clamped to its end
  CHECK(segmentSegment(vec3(3, 1, 0), vec3(3, 1, 0), vec3(0, 0, 0), vec3(2, 0, 0), ca, cb) == doctest::Approx(std::sqrt(2.0f)));
}

TEST_CASE("body parts: every role gets a capsule fitted to its own rest vertices (T-191)") {
  for (const char* asset : {kBoy, kGirl, kSdf}) {
    const std::string name = asset;
    CAPTURE(name);
    auto ev = load(baseScene(asset, 2));
    const auto& ci = ev->characters()[0];
    const BodyParts P = deriveBodyParts(ci.asset.skeleton, ci.rig.meshes);
    REQUIRE(P.valid);
    std::set<std::string> roles;
    for (const auto& c : P.capsules) {
      roles.insert(c.part);
      CHECK(c.bone == ci.asset.skeleton.find(c.part));
      CHECK(c.r >= kBodyPartMinRadius);
      CHECK(c.r < 0.25f);
    }
    for (const char* r : {"hips", "chest", "neck", "head", "hand.L", "hand.R", "thigh.L", "thigh.R", "shin.L", "shin.R", "foot.L", "foot.R"})
      CHECK(roles.count(r) == 1);
    // Arm roles where the rig weights the arms to them (the 1.0.0 test boy weights his sleeves to an unparented
    // DEF-shoulder helper, which is no body role: those vertices belong to no part)
    if (name == kGirl || name == kSdf)
      for (const char* r : {"upperArm.L", "upperArm.R", "forearm.L", "forearm.R"}) CHECK(roles.count(r) == 1);
    // Rest pose: the capsules stay within the character's extent (a fitted axis may tilt a capsule's end a little past
    // a flat sole or a crown: at most 2 cm).
    const std::vector<mat4> G = restGlobals(ci.asset.skeleton);
    float top = -1e9f, bottom = 1e9f, capTop = -1e9f, capBottom = 1e9f;
    for (const auto& m : ci.rig.meshes)
      for (const vec3& p : m.rest.positions) top = std::max(top, p.y), bottom = std::min(bottom, p.y);
    for (const auto& c : P.capsules) {
      vec3 a, b;
      bodyPartSegment(c, G, a, b);
      capTop = std::max(capTop, std::max(a.y, b.y) + c.r);
      capBottom = std::min(capBottom, std::min(a.y, b.y) - c.r);
    }
    MESSAGE("top " << (capTop - top) * 1000 << " mm, bottom " << (bottom - capBottom) * 1000 << " mm past the mesh");
    CHECK(capTop <= top + 0.02f);
    CHECK(capBottom >= bottom - 0.02f);
    // and covers most of the character (90th-percentile radii, garments and hair flaps outside): rest vertices inside
    // or within 1 cm of the capsules
    size_t inside = 0, total = 0;
    for (const auto& m : ci.rig.meshes)
      for (size_t v = 0; v < m.rest.positions.size(); v += 7, ++total)
        inside += pointBodyGap(P, G, m.rest.positions[v]) < 0.01f;
    std::string all;
    for (const auto& r : roles) all += r + " ";
    MESSAGE(name << ": " << P.capsules.size() << " capsules (" << all << "), " << 100.0 * double(inside) / double(total) << " % of rest vertices within 1 cm");
    CHECK(double(inside) > 0.6 * double(total));
  }
}

TEST_CASE("body parts: the gap between two characters is signed, a depth, and points from b to a (T-191)") {
  auto ev = load(baseScene(kBoy, 2));
  const auto& ci = ev->characters()[0];
  const BodyParts P = deriveBodyParts(ci.asset.skeleton, ci.rig.meshes);
  const std::vector<mat4> G = restGlobals(ci.asset.skeleton);
  auto shifted = [&](float dx) {
    std::vector<mat4> H = G;
    for (mat4& M : H) M = glm::translate(mat4(1), vec3(dx, 0, 0)) * M;
    return H;
  };
  float width = 0;  // the widest body extent along x (both sides)
  for (const auto& c : P.capsules) {
    vec3 a, b;
    bodyPartSegment(c, G, a, b);
    width = std::max({width, std::abs(a.x) + c.r, std::abs(b.x) + c.r});
  }
  CHECK(bodyGap(P, G, BodyParts{}, G).gap > 1e8f);  // no capsules: nothing to keep apart
  const BodyGap far = bodyGap(P, shifted(2 * width + 0.1f), P, G);
  CHECK(far.gap >= 0.1f - 1e-4f);  // never closer than the widest extents allow
  CHECK(far.gap < 0.15f);
  CHECK(far.dir.x > 0.99f);  // a is to the right of b: moving a along +x opens the gap
  float last = 1e9f;
  for (float dx = 2 * width + 0.1f; dx >= 2 * width - 0.02f; dx -= 0.01f) {  // closing in: the gap falls with the distance
    const BodyGap g = bodyGap(P, shifted(dx), P, G);
    CHECK(g.gap < last);
    CHECK(g.gap >= dx - 2 * width - 1e-4f);  // the widest parts meet first: the gap is at most that deep
    CHECK(g.gap < dx - 2 * width + 0.05f);
    last = g.gap;
  }
  // skip: excluding the meeting pair leaves a larger gap
  const BodyGap g = bodyGap(P, shifted(2 * width - 0.05f), P, G);
  REQUIRE(g.gap < 0);
  static std::string skipA, skipB;
  skipA = g.partA, skipB = g.partB;
  const BodyGap s = bodyGap(P, shifted(2 * width - 0.05f), P, G, [](const std::string& x, const std::string& y) { return x == skipA && y == skipB; });
  CHECK(s.gap > g.gap);
}
