// Secondary motion (anim/secondary.h): spring chains layered after clips, life and constraints.
// Synthetic skeletons only (no character data): a head bone carrying a hanging chain; plus scene-level checks on the
// engineering toy fixture package (its tail), copied to a temporary folder with a "dynamics" block added.
#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>

#include "anim/secondary.h"
#include "scene/scene.h"
#include "scene/shot_bake.h"

using namespace plush;

namespace {
constexpr float kPi = 3.14159265f;

// root (0,0,0) -> head (0,1,0) -> c0 (0,1,-0.1) -> c1 -> c2 -> c3, tip below; the chain hangs behind the head.
Skeleton chainSkeleton() {
  Skeleton s;
  s.bones.push_back({"root", -1, vec3(0)});
  s.bones.push_back({"head", 0, vec3(0, 1, 0)});
  s.bones.push_back({"c0", 1, vec3(0, 1.0f, -0.10f)});
  s.bones.push_back({"c1", 2, vec3(0, 0.95f, -0.12f)});
  s.bones.push_back({"c2", 3, vec3(0, 0.90f, -0.12f)});
  s.bones.push_back({"c3", 4, vec3(0, 0.85f, -0.12f)});
  return s;
}

DynamicsSpec chainSpec(bool collider = false) {
  DynamicsSpec d;
  d.enabled = true;
  SpringChain ch;
  ch.name = "lock";
  ch.bones = {"c0", "c1", "c2", "c3"};
  ch.tip = vec3(0, 0.80f, -0.12f);
  ch.params.stiffness = 40;
  ch.params.damping = 3;
  ch.params.limitDeg = 120;
  ch.params.radius = 0.005f;
  d.chains.push_back(ch);
  if (collider) d.colliders.push_back({"skull", DynamicsCollider::Kind::Sphere, "head", vec3(0, 0.9f, -0.03f), vec3(0, 0.9f, -0.03f), 0.06f});
  return d;
}

// Head yaw (degrees) as a function of time: a quick turn and back, then still from 1.2 s on.
float headYaw(double t) {
  if (t <= 0) return 0;
  if (t < 0.25) return float(70.0 * t / 0.25);
  if (t < 0.6) return 70.0f;
  if (t < 0.85) return float(70.0 * (0.85 - t) / 0.25);
  return 0;
}

SpringChainSolver::Driver driverAt(const Skeleton& sk, double fps, double frameStart, float (*yaw)(double)) {
  return [&sk, fps, frameStart, yaw](double frame) {
    Pose p = restPose(sk);
    p.local[1] = glm::angleAxis(glm::radians(yaw((frame - frameStart) / fps)), vec3(0, 1, 0));
    return boneGlobals(sk, p, mat4(1));
  };
}

std::vector<mat4> solve(const SpringChainSolver& s, const SpringChainSolver::Driver& d, double frame, double fps) {
  auto g = d(frame);
  s.apply(frame, 1, fps, d, g);
  return g;
}

vec3 pivot(const std::vector<mat4>& g, size_t b) { return vec3(g[b][3]); }

// End point of chain bone `b` (rest offset to its child head / the tip).
vec3 tipOf(const std::vector<mat4>& g, const Skeleton& sk, size_t b, vec3 restEnd) {
  return vec3(g[b] * vec4(restEnd - sk.bones[b].head, 1));
}

std::filesystem::path toyPackageWithTail(const std::filesystem::path& dir) {
  const auto src = std::filesystem::path(PLUSH_SOURCE_DIR) / "tests/data/imported/toy_fixture";
  std::filesystem::create_directories(dir);
  std::filesystem::copy_file(src / "geometry.bin", dir / "geometry.bin", std::filesystem::copy_options::overwrite_existing);
  auto j = parseJsonFile(src / "character.json");
  REQUIRE(j.has_value());
  (*j)["dynamics"] = Json::parse(R"({"substep_hz": 240, "preroll_s": 0.5,
      "colliders": [{"name": "body", "type": "capsule", "bone": "spine", "a": [0, 0.22, 0], "b": [0, 0.34, 0], "radius": 0.035}],
      "chains": [{"name": "tail", "group": "tail", "bones": ["tail_1", "tail_2"], "tip": [0, 0.27, -0.18],
                  "stiffness": 50, "damping": 4, "gravity": 1, "drag": 0.4, "limit_deg": 70, "radius": 0.01}]})");
  std::ofstream(dir / "character.json") << j->dump(1);
  return dir;
}

std::unique_ptr<SceneEvaluator> toyScene(const std::string& folder, int fps, const Json& dynamics) {
  Scene s;
  s.path = std::filesystem::path(PLUSH_SOURCE_DIR) / "tests/data/imported/scene.json";
  s.rate = FrameRate{fps, 1};
  s.frameStart = 1;
  s.frameEnd = 1 + 2 * fps;
  CharacterDesc cd;
  cd.name = "who";
  cd.asset = folder + "/character.json";
  cd.dynamics = dynamics;
  s.characters.push_back(cd);
  // Hips swing (yaw) over the first second, keyed in seconds so the 24 and 48 fps scenes animate the same motion.
  const double keys[][2] = {{0.0, 0}, {0.3, 50}, {0.6, -30}, {0.9, 0}};
  for (auto& k : keys) s.animation.tracks["who/hips.rot"].setKey({1 + k[0] * fps, vec3(0, float(k[1]), 0)});
  auto ev = std::make_unique<SceneEvaluator>();
  auto r = ev->load(s, EvalOptions{2.5f, 1.0f, false, 0});
  REQUIRE_MESSAGE(r.has_value(), (r ? "" : r.error().message));
  return ev;
}
}  // namespace

TEST_CASE("secondary motion: package block and scene override parsing") {
  auto none = dynamicsFromJson(Json());
  REQUIRE(none.has_value());
  CHECK_FALSE(none->enabled);
  auto d = dynamicsFromJson(dynamicsToJson(chainSpec(true)));
  REQUIRE(d.has_value());
  CHECK(d->enabled);
  REQUIRE(d->chains.size() == 1);
  CHECK(d->chains[0].bones.size() == 4);
  CHECK(d->colliders.size() == 1);
  DynamicsSpec o = *d;
  REQUIRE(applyDynamicsOverride(o, Json::parse(R"({"chains": {"*": {"damping": 9}, "lock": {"stiffness": 12}}})")).has_value());
  CHECK(o.chains[0].params.stiffness == doctest::Approx(12));
  CHECK(o.chains[0].params.damping == doctest::Approx(9));
  CHECK_FALSE(applyDynamicsOverride(o, Json::parse(R"({"chains": {"nope": {}}})")).has_value());
  DynamicsSpec off = *d;
  REQUIRE(applyDynamicsOverride(off, Json(false)).has_value());
  CHECK_FALSE(off.enabled);
  DynamicsSpec on = *none;
  REQUIRE(applyDynamicsOverride(on, Json(true)).has_value());
  CHECK_FALSE(on.enabled);  // "true" cannot invent chains
  // anchor: one weight per joint, in [0, 1]
  Json withAnchor = dynamicsToJson(chainSpec());
  withAnchor["chains"][0]["anchor"] = {{"bone", "root"}, {"weights", {0, 0.2, 0.4, 0.6, 0.8}}};
  auto anchored = dynamicsFromJson(withAnchor);
  REQUIRE(anchored.has_value());
  CHECK(anchored->chains[0].anchorBone == "root");
  CHECK(SpringChainSolver::create(chainSkeleton(), *anchored).has_value());
  withAnchor["chains"][0]["anchor"]["weights"] = {0, 1};
  CHECK_FALSE(dynamicsFromJson(withAnchor).has_value());
  // invalid: a chain whose bones are not parent -> child
  DynamicsSpec bad = chainSpec();
  bad.chains[0].bones = {"c0", "c2"};
  CHECK_FALSE(SpringChainSolver::create(chainSkeleton(), bad).has_value());
}

TEST_CASE("secondary motion: deterministic and independent of evaluation order") {
  const Skeleton sk = chainSkeleton();
  const double fps = 24;
  auto drv = driverAt(sk, fps, 1, headYaw);
  auto a = SpringChainSolver::create(sk, chainSpec(true)), b = SpringChainSolver::create(sk, chainSpec(true));
  REQUIRE(a.has_value());
  REQUIRE(b.has_value());
  std::vector<std::vector<mat4>> forward;
  for (int f = 1; f <= 48; ++f) forward.push_back(solve(**a, drv, f, fps));
  // b: scattered order, repeated frames, a fractional frame in between
  std::vector<int> order = {37, 3, 48, 12, 12, 1, 30, 25, 2, 47};
  bool identical = true;
  for (int f : order) {
    solve(**b, drv, f + 0.5, fps);
    auto g = solve(**b, drv, f, fps);
    for (size_t k = 0; k < g.size(); ++k) identical = identical && g[k] == forward[size_t(f - 1)][k];
  }
  CHECK(identical);
  (*a)->reset();
  bool again = true;
  for (int f = 48; f >= 1; f -= 7) {
    auto g = solve(**a, drv, f, fps);
    for (size_t k = 0; k < g.size(); ++k) again = again && g[k] == forward[size_t(f - 1)][k];
  }
  CHECK(again);
  // The layer does something: during the turn the chain lags behind the head (not rigid).
  auto kin = drv(6);
  CHECK(glm::distance(pivot(forward[5], 5), pivot(kin, 5)) > 0.005f);
  // Frames before the first frame stay kinematic.
  auto before = drv(0);
  auto g0 = before;
  (*a)->apply(0, 1, fps, drv, g0);
  for (size_t k = 0; k < g0.size(); ++k) CHECK(g0[k] == before[k]);
}

TEST_CASE("secondary motion: frame-rate independent (24 vs 48 fps)") {
  const Skeleton sk = chainSkeleton();
  auto d24 = driverAt(sk, 24, 1, headYaw), d48 = driverAt(sk, 48, 1, headYaw);
  auto s24 = SpringChainSolver::create(sk, chainSpec(true)), s48 = SpringChainSolver::create(sk, chainSpec(true));
  float worst = 0;
  for (int f = 1; f <= 48; ++f) {
    auto a = solve(**s24, d24, f, 24), b = solve(**s48, d48, 2 * f - 1, 48);
    for (size_t k = 2; k < sk.bones.size(); ++k) worst = std::max(worst, glm::distance(pivot(a, k), pivot(b, k)));
  }
  MESSAGE("synthetic chain, 24 vs 48 fps: max joint difference " << worst * 1000 << " mm");
  CHECK(worst < 1e-4f);

  // Through the scene evaluator on a package: hips keyed in seconds, the tail chain compared at equal times.
  const auto dir = std::filesystem::path(PLUSH_SOURCE_DIR) / "build/test_tmp/toy_tail";
  toyPackageWithTail(dir);
  const std::string folder = std::filesystem::relative(dir, std::filesystem::path(PLUSH_SOURCE_DIR) / "tests/data/imported").string();
  auto e24 = toyScene(folder, 24, Json()), e48 = toyScene(folder, 48, Json());
  const auto& skel = e24->characters()[0].asset.skeleton;
  const size_t t2 = size_t(skel.find("tail_2"));
  float worstScene = 0, motion = 0;
  auto kin24 = toyScene(folder, 24, Json(false));
  for (int f = 1; f <= 48; ++f) {
    auto a = e24->characterGlobals(0, f), b = e48->characterGlobals(0, 2 * f - 1), k = kin24->characterGlobals(0, f);
    worstScene = std::max(worstScene, glm::distance(pivot(a, t2), pivot(b, t2)));
    motion = std::max(motion, glm::distance(pivot(a, t2), pivot(k, t2)));
  }
  MESSAGE("toy tail, 24 vs 48 fps: max difference " << worstScene * 1000 << " mm; max secondary offset " << motion * 1000 << " mm");
  CHECK(motion > 0.003f);
  CHECK(worstScene < 0.05f * motion);
}

TEST_CASE("secondary motion: overshoots, then settles to the rest shape") {
  const Skeleton sk = chainSkeleton();
  const double fps = 30;
  auto drv = driverAt(sk, fps, 1, headYaw);
  auto s = SpringChainSolver::create(sk, chainSpec(false));
  REQUIRE(s.has_value());
  // Signed lateral offset of the tip from its kinematic position, in the head's frame.
  std::vector<float> side;
  float lastDev = 1;
  for (int f = 1; f <= 1 + int(5 * fps); ++f) {
    auto g = solve(**s, drv, f, fps), k = drv(f);
    const vec3 tip = tipOf(g, sk, 5, vec3(0, 0.80f, -0.12f)), tipK = tipOf(k, sk, 5, vec3(0, 0.80f, -0.12f));
    const vec3 x = vec3(k[1][0]);  // head's lateral axis
    side.push_back(glm::dot(tip - tipK, x));
    lastDev = glm::distance(tip, tipK);
  }
  // overshoot: after the head stops (0.85 s) the tip swings past the rest shape to both sides
  float lo = 0, hi = 0;
  for (size_t f = size_t(0.9 * fps); f < size_t(2.5 * fps); ++f) lo = std::min(lo, side[f]), hi = std::max(hi, side[f]);
  MESSAGE("after the stop: tip swings " << lo * 1000 << " .. " << hi * 1000 << " mm; after 5 s: " << lastDev * 1000 << " mm");
  CHECK(lo < -0.002f);
  CHECK(hi > 0.002f);
  CHECK(lastDev < 0.0005f);
}

TEST_CASE("secondary motion: collision keeps chain points outside a sphere") {
  const Skeleton sk = chainSkeleton();
  const double fps = 24;
  // The character moves fast to +X: the chain lags towards -X, where a sphere rides on the root bone beside it.
  auto drv = [&sk, fps](double frame) {
    const double t = (frame - 1) / fps;
    const float x = float(0.5 * std::clamp(t / 0.2, 0.0, 1.0));
    return boneGlobals(sk, restPose(sk), glm::translate(mat4(1), vec3(x, 0, 0)));
  };
  const vec3 centreRest(-0.1f, 0.86f, -0.12f);
  const float r = 0.06f, pr = 0.005f;
  float minWith = 1, minWithout = 1;
  for (bool col : {true, false}) {
    DynamicsSpec spec = chainSpec(false);
    spec.chains[0].params.stiffness = 4;  // floppy, so inertia carries it far
    spec.chains[0].params.damping = 0.5f;
    spec.colliders.push_back({"side", DynamicsCollider::Kind::Sphere, "root", centreRest, centreRest, r});
    if (!col) spec.colliders[0].a = spec.colliders[0].b = vec3(0, 5, 0);  // same set-up, collider out of reach
    auto s = SpringChainSolver::create(sk, spec);
    REQUIRE(s.has_value());
    for (int f = 1; f <= 48; ++f) {
      auto g = solve(**s, drv, f, fps);
      const vec3 c = vec3(g[0] * vec4(centreRest - sk.bones[0].head, 1));
      float& m = col ? minWith : minWithout;
      for (size_t b = 3; b < 6; ++b) m = std::min(m, glm::distance(pivot(g, b), c));
      m = std::min(m, glm::distance(tipOf(g, sk, 5, vec3(0, 0.80f, -0.12f)), c));
    }
  }
  MESSAGE("closest joint to the sphere centre: " << minWith * 1000 << " mm with collider, " << minWithout * 1000
                                                  << " mm without (radius + joint radius " << (r + pr) * 1000 << " mm)");
  CHECK(minWithout < r);           // the motion would enter the sphere
  CHECK(minWith >= r + pr - 1e-4f);  // the collider keeps every joint outside
}

TEST_CASE("secondary motion: a collider push keeps the chain joint-continuous (T-101)") {
  // As above, but the sphere sits beside the middle of the chain, so inner joints (bone heads) are pushed, not only
  // the tip. Blender connects the chain bones, so the end of each bone must stay on the head of the next.
  const Skeleton sk = chainSkeleton();
  const double fps = 24;
  auto drv = [&sk, fps](double frame) {
    const double t = (frame - 1) / fps;
    const float x = float(0.5 * std::clamp(t / 0.2, 0.0, 1.0));
    return boneGlobals(sk, restPose(sk), glm::translate(mat4(1), vec3(x, 0, 0)));
  };
  const vec3 centreRest(-0.09f, 0.96f, -0.12f);
  const float r = 0.06f, pr = 0.005f;
  DynamicsSpec spec = chainSpec(false);
  spec.chains[0].params.stiffness = 4;
  spec.chains[0].params.damping = 0.5f;
  spec.colliders.push_back({"side", DynamicsCollider::Kind::Sphere, "root", centreRest, centreRest, r});
  auto s = SpringChainSolver::create(sk, spec);
  REQUIRE(s.has_value());
  float gap = 0, minD = 1;
  for (int f = 1; f <= 48; ++f) {
    auto g = solve(**s, drv, f, fps);
    const vec3 c = vec3(g[0] * vec4(centreRest - sk.bones[0].head, 1));
    for (size_t b = 3; b < 6; ++b) minD = std::min(minD, glm::distance(pivot(g, b), c));
    for (size_t b = 2; b < 5; ++b) gap = std::max(gap, glm::distance(tipOf(g, sk, b, sk.bones[b + 1].head), pivot(g, b + 1)));
  }
  MESSAGE("largest joint gap: " << gap * 1000 << " mm; closest inner joint to the sphere centre: " << minD * 1000 << " mm");
  CHECK(minD < r + pr + 1e-3f);      // the sphere is in contact with an inner joint (the push is exercised)
  CHECK(minD >= r + pr - 1e-4f);     // and keeps it outside
  CHECK(gap < 1e-5f);                // 0.01 mm, the limit at which shot_render reproduces the baked bones
}

TEST_CASE("secondary motion: absent or disabled = bit-identical bake") {
  const auto dir = std::filesystem::path(PLUSH_SOURCE_DIR) / "build/test_tmp/toy_tail";
  toyPackageWithTail(dir);
  const std::string folder = std::filesystem::relative(dir, std::filesystem::path(PLUSH_SOURCE_DIR) / "tests/data/imported").string();
  auto plain = toyScene("toy_fixture", 24, Json());                // package without a dynamics block
  auto off = toyScene(folder, 24, Json(false));                   // with a block, switched off by the scene
  auto offObj = toyScene(folder, 24, Json::parse(R"({"enabled": false})"));
  auto on = toyScene(folder, 24, Json());
  Json bPlain = bakeShot(*plain, 1, 30), bOff = bakeShot(*off, 1, 30), bOffObj = bakeShot(*offObj, 1, 30), bOn = bakeShot(*on, 1, 30);
  CHECK(bPlain["frame_data"].dump() == bOff["frame_data"].dump());
  CHECK(bPlain["frame_data"].dump() == bOffObj["frame_data"].dump());
  CHECK(bPlain["frame_data"].dump() != bOn["frame_data"].dump());
  // The enabled bake changes only the chain bones (tail_1, tail_2); every other matrix is identical.
  const auto& sk = on->characters()[0].asset.skeleton;
  bool othersEqual = true, tailMoved = false;
  for (size_t f = 0; f < 30; ++f) {
    const Json& a = bPlain["frame_data"][f]["characters"]["who"]["skin"];
    const Json& b = bOn["frame_data"][f]["characters"]["who"]["skin"];
    for (size_t bone = 0; bone < sk.bones.size(); ++bone) {
      bool same = true;
      for (size_t k = 0; k < 16; ++k) same = same && a[bone * 16 + k] == b[bone * 16 + k];
      const bool tail = sk.bones[bone].name.rfind("tail_", 0) == 0;
      if (tail) tailMoved = tailMoved || !same;
      else othersEqual = othersEqual && same;
    }
  }
  CHECK(othersEqual);
  CHECK(tailMoved);
  // Scene save/load keeps the override.
  Json saved = sceneToJson(off->scene());
  CHECK(saved["characters"][0]["dynamics"] == Json(false));
  CHECK_FALSE(sceneToJson(plain->scene())["characters"][0].contains("dynamics"));
}

// ------------------------------------------------------------------------------------------- contact (T-183, opt-in)
namespace {

// chainSkeleton() plus an "arm" bone whose yaw swings a collider (rest centre 0.3 m in front of the arm pivot) to
// the point `target` on the hanging chain: yaw 0 = far away, yaw -90 degrees = centred on `target`.
Skeleton armSkeleton(vec3 target) {
  Skeleton s = chainSkeleton();
  s.bones.push_back({"arm", 0, target + vec3(0.3f, 0, 0)});
  return s;
}

vec3 armCentreRest(vec3 target) { return target + vec3(0.3f, 0, 0.3f); }

// The arm swings in over 0.5 s and stays.
SpringChainSolver::Driver armDriver(const Skeleton& sk, double fps) {
  return [&sk, fps](double frame) {
    Pose p = restPose(sk);
    const double t = std::clamp((frame - 1) / fps / 0.5, 0.0, 1.0);
    p.local[6] = glm::angleAxis(glm::radians(float(-90.0 * t)), vec3(0, 1, 0));
    return boneGlobals(sk, p, mat4(1));
  };
}

DynamicsSpec armSpec(vec3 target, float radius) {
  DynamicsSpec d = chainSpec(false);
  d.chains[0].params.damping = 12;  // calm: the test reads the settled pose
  d.colliders.push_back({"arm", DynamicsCollider::Kind::Sphere, "arm", armCentreRest(target), armCentreRest(target), radius});
  return d;
}

float pointSegment(vec3 p, vec3 a, vec3 b) {
  const vec3 ab = b - a;
  return glm::distance(p, a + ab * std::clamp(glm::dot(p - a, ab) / glm::dot(ab, ab), 0.0f, 1.0f));
}
}  // namespace

TEST_CASE("secondary contact: block parsing, round trip and errors") {
  Json j = {{"colliders", {{{"name", "hand"}, {"bone", "arm"}, {"type", "sphere"}, {"centre", {0.3, 0.9, 0.18}}, {"radius", 0.03}}}},
            {"chains", {{{"name", "lock"}, {"bones", {"c0", "c1", "c2", "c3"}}, {"tip", {0, 0.8, -0.12}},
                         {"contact", {{"solid", {"hand"}}, {"segments", true}, {"anchored_gravity", true}}}},
                        {{"name", "plain"}, {"bones", {"x"}}, {"tip", {0, 0, 0}}}}}};
  auto d = dynamicsFromJson(j);
  REQUIRE(d.has_value());
  CHECK(d->chains[0].contact.set);
  CHECK(d->chains[0].contact.solid == std::vector<std::string>{"hand"});
  CHECK(d->chains[0].contact.segments);
  CHECK(d->chains[0].contact.anchoredGravity);
  CHECK_FALSE(d->chains[1].contact.set);
  const Json back = dynamicsToJson(*d);
  CHECK(back["chains"][0]["contact"] == j["chains"][0]["contact"]);
  CHECK_FALSE(back["chains"][1].contains("contact"));  // a chain without the block is written as before
  Json bad = j;
  bad["chains"][0]["contact"]["bounce"] = 1;
  CHECK_FALSE(dynamicsFromJson(bad).has_value());
  bad = j;
  bad["chains"][0]["contact"]["solid"] = "hand";
  CHECK_FALSE(dynamicsFromJson(bad).has_value());
  // a solid name must be a collider of the block
  DynamicsSpec spec = armSpec(vec3(0, 0.9f, -0.12f), 0.03f);
  spec.chains[0].contact.set = true;
  spec.chains[0].contact.solid = {"nobody"};
  CHECK_FALSE(SpringChainSolver::create(armSkeleton(vec3(0, 0.9f, -0.12f)), spec).has_value());
}

TEST_CASE("secondary contact: an empty block changes nothing (bit-identical)") {
  const Skeleton sk = chainSkeleton();
  const double fps = 24;
  const auto drv = driverAt(sk, fps, 1, headYaw);
  DynamicsSpec plain = chainSpec(true), marked = chainSpec(true);
  marked.chains[0].contact.set = true;  // the block is there, every switch off
  auto a = SpringChainSolver::create(sk, plain), b = SpringChainSolver::create(sk, marked);
  REQUIRE(a.has_value());
  REQUIRE(b.has_value());
  bool same = true;
  for (int f = 1; f <= 40; ++f) same = same && solve(**a, drv, f, fps) == solve(**b, drv, f, fps);
  CHECK(same);
}

TEST_CASE("secondary contact: a solid collider pushes hair out of a moving part, a plain collider does not") {
  // The arm's sphere ends centred on joint c2: the joint's kinematic target lies inside it.
  const vec3 target(0, 0.90f, -0.12f);
  const Skeleton sk = armSkeleton(target);
  const double fps = 24;
  const auto drv = armDriver(sk, fps);
  const float r = 0.03f, pr = 0.005f;
  float minD[2] = {1, 1}, gap = 0, far = 0;
  for (int solid = 0; solid < 2; ++solid) {
    DynamicsSpec spec = armSpec(target, r);
    if (solid) {
      spec.chains[0].contact.set = true;
      spec.chains[0].contact.solid = {"arm"};
    }
    auto s = SpringChainSolver::create(sk, spec);
    REQUIRE(s.has_value());
    for (int f = 1; f <= 60; ++f) {
      auto g = solve(**s, drv, f, fps);
      const vec3 c = vec3(g[6] * vec4(armCentreRest(target) - sk.bones[6].head, 1));
      for (size_t b = 3; b < 6; ++b) minD[solid] = std::min(minD[solid], glm::distance(pivot(g, b), c));
      const vec3 tip = tipOf(g, sk, 5, vec3(0, 0.80f, -0.12f));
      minD[solid] = std::min(minD[solid], glm::distance(tip, c));
      if (solid) {
        for (size_t b = 2; b < 5; ++b) gap = std::max(gap, glm::distance(tipOf(g, sk, b, sk.bones[b + 1].head), pivot(g, b + 1)));
        if (f > 30) far = std::max(far, glm::distance(pivot(g, 4), c));  // the arm has stopped: c2 rests on it
      }
    }
  }
  MESSAGE("closest joint to the sphere centre: plain " << minD[0] * 1000 << " mm, solid " << minD[1] * 1000
          << " mm (radius + joint radius " << (r + pr) * 1000 << " mm); joint gap " << gap * 1000
          << " mm; c2 from the centre once the arm rests " << far * 1000 << " mm");
  CHECK(minD[0] < 0.005f);            // plain: the kinematic target is inside, so the hair is not pushed
  CHECK(minD[1] >= r + pr - 1e-4f);   // solid: every joint stays outside
  CHECK(gap < 1e-5f);                 // and the chain stays joint-continuous
  CHECK(far < r + pr + 0.004f);       // inelastic: the pushed joint lies on the collider, it is not thrown off
}

TEST_CASE("secondary contact: segments collide between the joints") {
  // A small sphere ends centred on the middle of segment c1-c2 (joints 25 mm away on both sides): the joint test
  // alone does not see it.
  const vec3 target(0, 0.925f, -0.12f);
  const Skeleton sk = armSkeleton(target);
  const double fps = 24;
  const auto drv = armDriver(sk, fps);
  const float r = 0.012f, pr = 0.005f;
  float minSeg[2] = {1, 1};
  for (int seg = 0; seg < 2; ++seg) {
    DynamicsSpec spec = armSpec(target, r);
    spec.chains[0].contact.set = true;
    spec.chains[0].contact.solid = {"arm"};
    spec.chains[0].contact.segments = seg != 0;
    auto s = SpringChainSolver::create(sk, spec);
    REQUIRE(s.has_value());
    for (int f = 1; f <= 60; ++f) {
      auto g = solve(**s, drv, f, fps);
      const vec3 c = vec3(g[6] * vec4(armCentreRest(target) - sk.bones[6].head, 1));
      for (size_t b = 2; b < 5; ++b) minSeg[seg] = std::min(minSeg[seg], pointSegment(c, pivot(g, b), pivot(g, b + 1)));
    }
  }
  MESSAGE("closest segment to the sphere centre: joints only " << minSeg[0] * 1000 << " mm, with segments "
          << minSeg[1] * 1000 << " mm (radius + chain radius " << (r + pr) * 1000 << " mm)");
  CHECK(minSeg[0] < 0.005f);                 // joints only: the sphere passes through the segment
  CHECK(minSeg[1] >= r + pr - 5e-4f);        // segments: it is kept outside (0.5 mm tolerance of the lever push)
}

TEST_CASE("secondary contact: anchored gravity follows the anchor bone") {
  // The chain's joints are anchored to the root bone; the head tilts 30 degrees and stays. Gravity relative to the
  // head's tilt pulls the anchored joints off the place the anchor gives them unless anchored_gravity is set.
  const Skeleton sk = chainSkeleton();
  const double fps = 24;
  auto drv = [&sk, fps](double frame) {
    Pose p = restPose(sk);
    const double t = std::clamp((frame - 1) / fps / 0.4, 0.0, 1.0);
    p.local[1] = glm::angleAxis(glm::radians(float(30.0 * t)), vec3(1, 0, 0));
    return boneGlobals(sk, p, mat4(1));
  };
  float off[2] = {0, 0};
  for (int on = 0; on < 2; ++on) {
    DynamicsSpec spec = chainSpec(false);
    spec.chains[0].params.damping = 12;
    spec.chains[0].anchorBone = "root";
    spec.chains[0].anchorWeights = {0, 1, 1, 1, 1};
    spec.chains[0].contact.set = true;
    spec.chains[0].contact.anchoredGravity = on != 0;
    auto dyn = SpringChainSolver::create(sk, spec), still = SpringChainSolver::create(sk, spec, false);
    REQUIRE(dyn.has_value());
    REQUIRE(still.has_value());
    std::vector<mat4> g;
    for (int f = 1; f <= 96; ++f) g = solve(**dyn, drv, f, fps);  // settled: 3.6 s after the tilt
    auto gs = drv(96);
    (*still)->apply(96, 1, fps, drv, gs);
    off[on] = glm::distance(tipOf(g, sk, 5, vec3(0, 0.80f, -0.12f)), tipOf(gs, sk, 5, vec3(0, 0.80f, -0.12f)));
  }
  MESSAGE("settled tip off its anchored place: " << off[0] * 1000 << " mm without, " << off[1] * 1000 << " mm with anchored_gravity");
  CHECK(off[0] > 0.02f);
  CHECK(off[1] < 0.001f);
}

// ------------------------------------------------------------------- contact, round 2 keys: radii, rest, max_swing
namespace {

// The arm swings in over 0.5 s (as armDriver) and then keeps moving: +-`swingDeg` about its end place, period 2 s.
SpringChainSolver::Driver armCarryDriver(const Skeleton& sk, double fps, float swingDeg) {
  return [&sk, fps, swingDeg](double frame) {
    Pose p = restPose(sk);
    const double sec = (frame - 1) / fps, t = std::clamp(sec / 0.5, 0.0, 1.0);
    const double wobble = sec > 0.5 ? swingDeg * std::sin((sec - 0.5) * kPi) : 0.0;
    p.local[6] = glm::angleAxis(glm::radians(float(-90.0 * t + wobble)), vec3(0, 1, 0));
    return boneGlobals(sk, p, mat4(1));
  };
}

// A frame-to-frame reversal of a point's path: the smaller of two consecutive steps that point against each other.
float zigzag(vec3 a, vec3 b, vec3 c) {
  const vec3 d1 = b - a, d2 = c - b;
  return glm::dot(d1, d2) < 0 ? std::min(glm::length(d1), glm::length(d2)) : 0.0f;
}

const vec3 kTipRest(0, 0.80f, -0.12f);
}  // namespace

TEST_CASE("secondary contact: radii, rest, friction and max_swing parse, round-trip and are checked") {
  // dyadic numbers: float and JSON double agree, so the round trip can be compared as written
  const Json contact = {{"solid", Json::array()}, {"segments", true}, {"anchored_gravity", false},
                        {"radii", {0.0, 0.015625, 0.03125, 0.03125, 0.0078125}}, {"rest", true}, {"friction", 24.0}, {"max_swing", 8.0}};
  Json j = {{"colliders", {{{"name", "hand"}, {"bone", "arm"}, {"type", "sphere"}, {"centre", {0.3, 0.9, 0.18}}, {"radius", 0.03}}}},
            {"chains", {{{"name", "lock"}, {"bones", {"c0", "c1", "c2", "c3"}}, {"tip", {0, 0.8, -0.12}}, {"contact", contact}},
                        {{"name", "old"}, {"bones", {"x"}}, {"tip", {0, 0, 0}}, {"contact", {{"segments", true}}}}}}};
  auto d = dynamicsFromJson(j);
  REQUIRE(d.has_value());
  const ChainContact& c = d->chains[0].contact;
  CHECK(c.radii == std::vector<float>{0.0f, 0.015625f, 0.03125f, 0.03125f, 0.0078125f});
  CHECK(c.rest);
  CHECK(c.friction == 24.0f);
  CHECK(c.maxSwing == 8.0f);
  // a round-1 block: the new keys are off, at their defaults, and are not written back
  const ChainContact& o = d->chains[1].contact;
  CHECK(o.radii.empty());
  CHECK_FALSE(o.rest);
  CHECK(o.friction == 40.0f);
  CHECK(o.maxSwing == 12.0f);
  const Json back = dynamicsToJson(*d);
  CHECK(back["chains"][0]["contact"] == contact);
  for (const char* key : {"radii", "rest", "friction", "max_swing"}) CHECK_FALSE(back["chains"][1]["contact"].contains(key));
  // "rest" alone: friction and max_swing take their defaults and are written with it
  Json plainRest = j;
  plainRest["chains"][0]["contact"] = {{"rest", true}};
  auto pr = dynamicsFromJson(plainRest);
  REQUIRE(pr.has_value());
  const Json prBack = dynamicsToJson(*pr)["chains"][0]["contact"];
  CHECK(prBack["friction"] == 40.0);
  CHECK(prBack["max_swing"] == 12.0);
  // malformed values are refused
  const std::pair<const char*, Json> wrong[] = {{"radii", 0.01}, {"radii", Json::array()}, {"radii", {0.01, -0.01}}, {"radii", {0.01, "wide"}},
                                                {"friction", -1.0}, {"friction", "high"}, {"max_swing", -2.0}, {"max_swing", true}};
  for (const auto& [key, value] : wrong) {
    Json bad = j;
    bad["chains"][0]["contact"][key] = value;
    CHECK_MESSAGE(!dynamicsFromJson(bad).has_value(), key << " = " << value.dump());
  }
  // one radius per joint (bones + 1): any other count is an error when the solver is built
  const vec3 target(0, 0.90f, -0.12f);
  DynamicsSpec spec = armSpec(target, 0.03f);
  spec.chains[0].contact.set = true;
  spec.chains[0].contact.radii = {0.0f, 0.01f, 0.01f, 0.01f};
  CHECK_FALSE(SpringChainSolver::create(armSkeleton(target), spec).has_value());
  spec.chains[0].contact.radii.push_back(0.01f);
  CHECK(SpringChainSolver::create(armSkeleton(target), spec).has_value());
}

TEST_CASE("secondary contact: radii give every joint its own collision radius, segments taper between them") {
  // The arm's sphere ends centred on joint c2. The lock is thick at c2 (30 mm), thin at its neighbours (10 mm).
  const vec3 target(0, 0.90f, -0.12f);
  const Skeleton sk = armSkeleton(target);
  const double fps = 24;
  const auto drv = armDriver(sk, fps);
  const float r = 0.02f;
  const std::vector<float> radii = {0.0f, 0.01f, 0.03f, 0.01f, 0.01f};
  float joint[2][5], mid[2] = {1, 1};
  for (int on = 0; on < 2; ++on) {
    DynamicsSpec spec = armSpec(target, r);
    spec.chains[0].contact.set = true;
    spec.chains[0].contact.solid = {"arm"};
    spec.chains[0].contact.segments = true;
    if (on) spec.chains[0].contact.radii = radii;
    auto s = SpringChainSolver::create(sk, spec);
    REQUIRE(s.has_value());
    for (float& v : joint[on]) v = 1;
    for (int f = 1; f <= 60; ++f) {
      auto g = solve(**s, drv, f, fps);
      const vec3 c = vec3(g[6] * vec4(armCentreRest(target) - sk.bones[6].head, 1));
      vec3 x[5];
      for (size_t k = 0; k < 4; ++k) x[k] = pivot(g, 2 + k);
      x[4] = tipOf(g, sk, 5, kTipRest);
      for (size_t k = 0; k < 5; ++k) joint[on][k] = std::min(joint[on][k], glm::distance(x[k], c));
      for (size_t k = 1; k <= 2; ++k) mid[on] = std::min(mid[on], glm::distance(0.5f * (x[k] + x[k + 1]), c));  // c1-c2, c2-c3
    }
  }
  MESSAGE("closest to the sphere centre (mm): c2 " << joint[0][2] * 1000 << " with the chain radius, " << joint[1][2] * 1000
          << " with radii (sphere " << r * 1000 << " + 30); middles of the segments at c2 " << mid[0] * 1000 << " / " << mid[1] * 1000);
  CHECK(joint[0][2] >= r + 0.005f - 1e-4f);  // without radii: the chain radius (5 mm)
  CHECK(joint[0][2] < r + 0.010f);
  for (size_t k = 1; k < 5; ++k) CHECK(joint[1][k] >= r + radii[k] - 1e-4f);  // with radii: each joint its own
  CHECK(mid[1] >= r + 0.02f - 5e-4f);  // a segment's middle: the mean of its two radii (0.5 mm lever tolerance)
}

TEST_CASE("secondary contact: rest keeps a chain outside a collider that holds its kinematic target, and still") {
  // The arm's sphere ends centred on joint c2 and stays: the joint's kinematic target is at the sphere's centre. A
  // plain collider leaves the joint there; "rest" pushes to the full radius, and the chain lies on the sphere quietly.
  const vec3 target(0, 0.90f, -0.12f);
  const Skeleton sk = armSkeleton(target);
  const double fps = 24;
  const auto drv = armDriver(sk, fps);
  const float r = 0.03f;
  const std::vector<float> radii = {0.0f, 0.008f, 0.012f, 0.012f, 0.010f};
  DynamicsSpec spec = armSpec(target, r);
  spec.chains[0].contact.set = true;
  spec.chains[0].contact.segments = true;
  spec.chains[0].contact.radii = radii;
  spec.chains[0].contact.rest = true;
  auto s = SpringChainSolver::create(sk, spec);
  REQUIRE(s.has_value());
  float inside = 0, step = 0, gap = 1, arrival = 0;
  vec3 last(0);
  for (int f = 1; f <= 120; ++f) {
    auto g = solve(**s, drv, f, fps);
    const vec3 c = vec3(g[6] * vec4(armCentreRest(target) - sk.bones[6].head, 1));
    vec3 x[5];
    for (size_t k = 0; k < 4; ++k) x[k] = pivot(g, 2 + k);
    x[4] = tipOf(g, sk, 5, kTipRest);
    float in = 0, clear = 1;  // deepest and nearest joint or segment middle of this frame
    for (size_t k = 1; k < 5; ++k) {
      const float dj = glm::distance(x[k], c) - (r + radii[k]);
      const float dm = k < 4 ? glm::distance(0.5f * (x[k] + x[k + 1]), c) - (r + 0.5f * (radii[k] + radii[k + 1])) : 1.0f;
      in = std::max(in, -std::min(dj, dm));
      clear = std::min(clear, std::min(dj, dm));
    }
    if (f <= 14) arrival = std::max(arrival, in);  // the arm arrives at 0.9 m/s and stops at frame 13
    if (f > 14) inside = std::max(inside, in);
    if (f > 60) step = std::max(step, glm::distance(x[4], last));
    if (f == 120) gap = clear;
    last = x[4];
  }
  MESSAGE("joint or segment middle inside the sphere: " << arrival * 1000 << " mm while the arm arrives (max_swing), " << inside * 1000
          << " mm from frame 15 on; largest tip step per frame after frame 60 " << step * 1000 << " mm; nearest joint or middle above the sphere at the end "
          << gap * 1000 << " mm");
  CHECK(inside < 5e-4f);  // outside once the arm rests: joints exactly, segment middles within the lever tolerance
  CHECK(step < 1e-4f);    // still: under 0.1 mm per frame
  CHECK(gap < 5e-4f);     // it lies on the sphere, not thrown off
}

TEST_CASE("secondary contact: a collider that moves under a resting chain carries it") {
  // As above, but the arm keeps moving slowly (+-4 degrees: the sphere travels +-21 mm, up to 66 mm/s). The joint on
  // the sphere takes the sphere's velocity: the chain stays on the surface and its path is as smooth as the sphere's.
  const vec3 target(0, 0.90f, -0.12f);
  const Skeleton sk = armSkeleton(target);
  const double fps = 24;
  const auto drv = armCarryDriver(sk, fps, 4.0f);
  const float r = 0.03f;
  const std::vector<float> radii = {0.0f, 0.008f, 0.012f, 0.012f, 0.010f};
  DynamicsSpec spec = armSpec(target, r);
  spec.chains[0].contact.set = true;
  spec.chains[0].contact.segments = true;
  spec.chains[0].contact.radii = radii;
  spec.chains[0].contact.rest = true;
  auto s = SpringChainSolver::create(sk, spec);
  REQUIRE(s.has_value());
  float inside = 0, lift = 0, bend = 0, colliderBend = 0, travel = 0, zig = 0;
  vec3 t1(0), t2(0), c1(0), c2(0), first(0);
  for (int f = 1; f <= 132; ++f) {
    auto g = solve(**s, drv, f, fps);
    const vec3 c = vec3(g[6] * vec4(armCentreRest(target) - sk.bones[6].head, 1));
    vec3 x[5];
    for (size_t k = 0; k < 4; ++k) x[k] = pivot(g, 2 + k);
    x[4] = tipOf(g, sk, 5, kTipRest);
    if (f > 36) {
      float clear = 1;
      for (size_t k = 1; k < 5; ++k) {
        const float dj = glm::distance(x[k], c) - (r + radii[k]);
        const float dm = k < 4 ? glm::distance(0.5f * (x[k] + x[k + 1]), c) - (r + 0.5f * (radii[k] + radii[k + 1])) : 1.0f;
        inside = std::max(inside, -std::min(dj, dm));
        clear = std::min(clear, std::min(dj, dm));
      }
      lift = std::max(lift, clear);
      if (f > 38) {  // second difference: what the path of c2 bends by from one frame to the next
        bend = std::max(bend, glm::length(x[2] - 2.0f * t1 + t2));
        colliderBend = std::max(colliderBend, glm::length(c - 2.0f * c1 + c2));
        if (glm::dot(c1 - c2, c - c1) > 0) zig = std::max(zig, zigzag(t2, t1, x[2]));  // not where the sphere itself turns back
      }
      if (f == 37) first = x[2];
      travel = std::max(travel, glm::distance(x[2], first));
    }
    t2 = t1;
    t1 = x[2];
    c2 = c1;
    c1 = c;
  }
  MESSAGE("moving sphere: deepest joint or segment middle " << inside * 1000 << " mm; the chain lifts off by at most " << lift * 1000
          << " mm; c2 travels " << travel * 1000 << " mm; its path bends by at most " << bend * 1000 << " mm per frame (the sphere's own: "
          << colliderBend * 1000 << " mm); largest frame-to-frame reversal " << zig * 1000 << " mm");
  CHECK(inside < 5e-4f);
  CHECK(travel > 0.010f);  // it is carried along
  CHECK(lift < 5e-4f);     // and stays on the surface
  CHECK(zig < 1e-4f);      // without jitter: no frame-to-frame reversal of its path
  CHECK(bend < 1.5e-3f);   // and no jump (it moves up to 2.7 mm per frame; the contact changes from joint to segment)
}

TEST_CASE("secondary contact: max_swing bounds how fast a pushed segment turns") {
  // The arm's sphere arrives within one frame (0.4 m in 1/24 s). Without the cap the projection moves the lock out
  // at once; with max_swing each segment turns at most that much faster than its kinematic direction (which stands
  // still here), and the lock still ends outside the sphere.
  const vec3 target(0, 0.90f, -0.12f);
  const Skeleton sk = armSkeleton(target);
  const double fps = 24;
  auto drv = [&sk, fps](double frame) {
    Pose p = restPose(sk);
    p.local[6] = glm::angleAxis(glm::radians(float(-90.0 * std::clamp((frame - 12.0), 0.0, 1.0))), vec3(0, 1, 0));
    return boneGlobals(sk, p, mat4(1));
  };
  const float r = 0.03f, pr = 0.005f, cap = 3.0f;
  float turn[2] = {0, 0}, end[2] = {0, 0};
  for (int capped = 0; capped < 2; ++capped) {
    DynamicsSpec spec = armSpec(target, r);
    spec.chains[0].contact.set = true;
    spec.chains[0].contact.segments = true;
    spec.chains[0].contact.rest = true;
    spec.chains[0].contact.maxSwing = capped ? cap : 0.0f;
    auto s = SpringChainSolver::create(sk, spec);
    REQUIRE(s.has_value());
    vec3 prev[5];
    for (int f = 1; f <= 72; ++f) {
      auto g = solve(**s, drv, f, fps);
      const vec3 c = vec3(g[6] * vec4(armCentreRest(target) - sk.bones[6].head, 1));
      vec3 x[5];
      for (size_t k = 0; k < 4; ++k) x[k] = pivot(g, 2 + k);
      x[4] = tipOf(g, sk, 5, kTipRest);
      for (size_t k = 1; k < 5 && f > 1; ++k) {
        const vec3 a = glm::normalize(prev[k] - prev[k - 1]), b = glm::normalize(x[k] - x[k - 1]);
        turn[capped] = std::max(turn[capped], std::atan2(glm::length(glm::cross(a, b)), glm::dot(a, b)));
      }
      for (size_t k = 0; k < 5; ++k) prev[k] = x[k];
      if (f == 72) {
        end[capped] = 1;
        for (size_t k = 1; k < 5; ++k) end[capped] = std::min(end[capped], glm::distance(x[k], c));
      }
    }
  }
  MESSAGE("largest turn of a segment in one frame: " << turn[0] << " rad without the cap, " << turn[1] << " rad with max_swing "
          << cap << " rad/s (" << cap / fps << " per frame); closest joint at the end " << end[0] * 1000 << " / " << end[1] * 1000 << " mm");
  CHECK(turn[0] > 2.0f * cap / float(fps));     // uncapped: much faster than the cap would allow
  CHECK(turn[1] <= cap / float(fps) + 1e-3f);   // capped
  CHECK(end[0] >= r + pr - 1e-4f);              // both end outside
  CHECK(end[1] >= r + pr - 1e-4f);
}

TEST_CASE("secondary contact: rest lets a collider hold a joint beyond the angular limit, quietly, and it returns steadily") {
  // The chain may bend 30 degrees per segment (c2 can leave its place by 26 mm), but the sphere that ends centred on
  // c2 needs it 35 mm away. Limit and collider cannot both be met: the collider wins and the chain lies still (a
  // clamp to the limit every step would make the joint creep round the limit cone). When the arm swings away the
  // joint comes back within the limit steadily, not in one step.
  const vec3 target(0, 0.90f, -0.12f);
  const Skeleton sk = armSkeleton(target);
  const double fps = 24;
  auto drv = [&sk, fps](double frame) {  // in over 0.5 s, held until 2 s, out over 0.5 s
    Pose p = restPose(sk);
    const double sec = (frame - 1) / fps;
    const double t = sec < 2.0 ? std::clamp(sec / 0.5, 0.0, 1.0) : std::clamp(1.0 - (sec - 2.0) / 0.5, 0.0, 1.0);
    p.local[6] = glm::angleAxis(glm::radians(float(-90.0 * t)), vec3(0, 1, 0));
    return boneGlobals(sk, p, mat4(1));
  };
  const float r = 0.03f, pr = 0.005f, limit = glm::radians(30.0f);
  DynamicsSpec spec = armSpec(target, r);
  spec.chains[0].params.limitDeg = 30;
  spec.chains[0].contact.set = true;
  spec.chains[0].contact.segments = true;
  spec.chains[0].contact.rest = true;
  auto s = SpringChainSolver::create(sk, spec);
  REQUIRE(s.has_value());
  float held = 0, inside = 0, still = 0, jump = 0, zig = 0, end = 0;
  vec3 t1(0), t2(0);
  for (int f = 1; f <= 120; ++f) {
    auto g = solve(**s, drv, f, fps);
    const vec3 c = vec3(g[6] * vec4(armCentreRest(target) - sk.bones[6].head, 1));
    vec3 x[5];
    for (size_t k = 0; k < 4; ++k) x[k] = pivot(g, 2 + k);
    x[4] = tipOf(g, sk, 5, kTipRest);
    float bend = 0;  // the largest angle of a segment against its kinematic direction (straight down from c1 on)
    for (size_t k = 2; k < 5; ++k) {
      const vec3 d = glm::normalize(x[k] - x[k - 1]);
      bend = std::max(bend, std::atan2(glm::length(glm::cross(d, vec3(0, -1, 0))), glm::dot(d, vec3(0, -1, 0))));
    }
    if (f > 30 && f <= 48) {  // the arm rests (frames 13 to 49)
      held = std::max(held, bend);
      for (size_t k = 1; k < 5; ++k) inside = std::max(inside, r + pr - glm::distance(x[k], c));
      if (f > 40) still = std::max(still, glm::distance(x[4], t1));
    }
    if (f > 49) {  // the arm leaves
      jump = std::max(jump, glm::distance(x[4], t1));
      if (f > 51) zig = std::max(zig, zigzag(t2, t1, x[4]));
    }
    if (f == 120) end = bend;
    t2 = t1;
    t1 = x[4];
  }
  MESSAGE("held: largest segment angle " << glm::degrees(held) << " deg (limit 30), deepest joint " << inside * 1000 << " mm, tip step "
          << still * 1000 << " mm per frame; released: largest tip step " << jump * 1000 << " mm per frame, largest reversal "
          << zig * 1000 << " mm, angle at the end " << glm::degrees(end) << " deg");
  CHECK(held > limit + glm::radians(5.0f));  // the collider holds it beyond the limit
  CHECK(inside < 1e-4f);
  CHECK(still < 1e-4f);
  CHECK(jump < 0.008f);   // the way back: under 8 mm per frame at the tip, and no zigzag
  CHECK(zig < 5e-4f);
  CHECK(end <= limit + 1e-3f);
}
