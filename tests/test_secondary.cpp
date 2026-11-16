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
