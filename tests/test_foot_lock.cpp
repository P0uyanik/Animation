// Locomotion layer (T-175, anim/foot_lock.h + scene/clip_layers.cpp): the clip "style" block (lean with thigh
// compensation, arm swing, stride, tempo), foot_plant lookup (loop seam, release), the two-bone foot pin, and scene
// playback of the CMU mocap clips on two characters: planted feet slide <= 3 mm with the foot-lock (and visibly more
// without it), no popping, and a clip without a style block is left alone.
#include <doctest/doctest.h>

#include <cmath>
#include <fstream>

#include "anim/foot_lock.h"
#include "model/clip.h"
#include "scene/scene.h"

using namespace plush;
namespace fs = std::filesystem;

namespace {
const fs::path kRoot = PLUSH_SOURCE_DIR;
const quat kNoRot(1, 0, 0, 0);
quat rot(float deg, vec3 axis) { return glm::angleAxis(glm::radians(deg), glm::normalize(axis)); }
float quatAngle(quat a, quat b) {
  glm::dquat x = glm::normalize(glm::dquat(a)), y = glm::normalize(glm::dquat(b));
  return float(glm::degrees(2.0 * std::acos(std::min(1.0, std::abs(glm::dot(x, y))))));
}
Skeleton legSkeleton() {
  Skeleton s;
  s.bones.push_back({"hips", -1, {0, 0.30f, 0}});
  s.bones.push_back({"thigh.L", 0, {0.05f, 0.28f, 0}});
  s.bones.push_back({"shin.L", 1, {0.05f, 0.16f, 0.004f}});
  s.bones.push_back({"foot.L", 2, {0.05f, 0.04f, 0}});
  return s;
}
std::unique_ptr<SceneEvaluator> sceneWith(const char* pkg, const Json& actions, int frameEnd = 120) {
  Scene s;
  s.path = kRoot / "tests/data/imported/scene.json";
  s.rate = FrameRate{24, 1};
  s.frameStart = 1;
  s.frameEnd = frameEnd;
  CharacterDesc cd;
  cd.name = "who";
  cd.asset = std::string(pkg) + "/character.json";
  cd.autoIdle = false;
  s.characters.push_back(cd);
  s.actions = actions;
  auto ev = std::make_unique<SceneEvaluator>();
  auto r = ev->load(s, EvalOptions{2.5f, 1.0f, false, 0});
  REQUIRE(r.has_value());
  return ev;
}
fs::path tempClip(const std::string& name, const Json& j) {
  fs::path d = fs::temp_directory_path() / "plush_foot_lock";
  fs::create_directories(d);
  std::ofstream(d / name) << j.dump();
  return d / name;
}
struct Slide {
  float planted = 0;   // worst horizontal drift of an ankle from where its plant began (m)
  float vertical = 0;  // worst vertical drift (m)
  float lowest = 1e9f, highest = -1e9f;  // planted ankle height relative to its rest height (m)
  float pop = 0;       // worst second difference of an ankle position (m / frame^2)
  int pops = 0;        // frames that pop by the motion_checks rule (|a| >= 8 mm and |a| >= 0.45 x the local peak speed)
  int frames = 0;
};
// Plays `file` from frame 1 at 24 fps and measures the ankles on the clip's own foot_plant frames.
Slide measure(const char* pkg, const fs::path& file, int frames, double tempo) {
  Json acts = Json::array({{{"type", "clip"}, {"character", "who"}, {"file", file.string()}, {"start", 1}, {"blendIn", 0}, {"blendOut", 0},
                            {"end", 1 + frames}}});
  auto ev = sceneWith(pkg, acts, frames + 2);
  const ClipData clip = loadClip(file).value();
  const auto plants = footPlants(clip.raw);
  const Skeleton& sk = ev->characters()[0].asset.skeleton;
  Slide out;
  for (const char* role : {"foot.L", "foot.R"}) {
    const int b = sk.find(role);
    REQUIRE(b >= 0);
    const float rest = sk.bones[size_t(b)].head.y;
    double start = -1;
    vec3 p0(0);
    std::vector<vec3> ps_;
    for (int f = 1; f <= frames; ++f) ps_.push_back(vec3(ev->characterGlobals(0, f)[size_t(b)][3]));
    for (int t = 1; t + 1 < frames; ++t) {
      const float a = glm::length(ps_[size_t(t + 1)] - 2.0f * ps_[size_t(t)] + ps_[size_t(t - 1)]);
      float v = 0;
      for (int k = std::max(1, t - 2); k <= std::min(frames - 1, t + 3); ++k) v = std::max(v, glm::length(ps_[size_t(k)] - ps_[size_t(k - 1)]));
      out.pop = std::max(out.pop, a);
      if (a >= 0.008f && a >= 0.45f * v) ++out.pops;
    }
    for (int f = 1; f <= frames; ++f) {
      const vec3 p = ps_[size_t(f - 1)];
      const PlantState ps = plantAt(plants, role, (f - 1) * tempo, clip.frameCount, clip.loop, 0.0, 2.0, 3.0);
      if (!ps.active || ps.weight < 1.0f) {
        start = -1;
        continue;
      }
      if (ps.start != start) {
        start = ps.start;
        p0 = p;
      }
      out.planted = std::max(out.planted, glm::length(vec2(p.x - p0.x, p.z - p0.z)));
      out.vertical = std::max(out.vertical, std::abs(p.y - p0.y));
      out.lowest = std::min(out.lowest, p.y - rest);
      out.highest = std::max(out.highest, p.y - rest);
      ++out.frames;
    }
  }
  return out;
}
}  // namespace

TEST_CASE("foot lock: style block parsing, neutral without a block") {
  CHECK_FALSE(locomotionStyle(Json::object()).enabled);
  CHECK(locomotionTempo(Json::object()) == 1.0);
  CHECK(locomotionTempo(Json{{"style", "walk"}}) == 1.0);
  Json clip{{"style", {{"lean", 0.5}, {"stride", 0.9}, {"arm_swing", 0.8}, {"tempo", 1.2}, {"foot_lock", true},
                       {"arm_center", {{"upperArm.L", {1, 0, 0, 0}}, {"bad", {1, 2}}}}}}};
  const LocomotionStyle s = locomotionStyle(clip);
  CHECK(s.enabled);
  CHECK(s.lean == doctest::Approx(0.5));
  CHECK(s.stride == doctest::Approx(0.9));
  CHECK(s.armSwing == doctest::Approx(0.8));
  CHECK(s.tempo == doctest::Approx(1.2));
  CHECK(s.footLock);
  CHECK(s.armCenter.size() == 1);
  CHECK(locomotionTempo(clip) == doctest::Approx(1.2));
  // a disabled style changes nothing
  std::map<std::string, quat> local{{"hips", rot(30, {1, 0, 0})}};
  vec3 root(1, 2, 3);
  applyLocomotionStyle(LocomotionStyle{}, local, root, false);
  CHECK(quatAngle(local["hips"], rot(30, {1, 0, 0})) < 1e-4f);
  CHECK(root == vec3(1, 2, 3));
}

TEST_CASE("foot lock: lean keeps the yaw and the leg directions, arm swing and stride scale") {
  LocomotionStyle st;
  st.enabled = true;
  st.lean = 0.5f;
  st.stride = 0.8f;
  st.armSwing = 0.5f;
  st.armCenter["upperArm.L"] = rot(-70, {0, 0, 1});
  const quat yaw = rot(25, {0, 1, 0}), lean = rot(40, {1, 0, 0});
  std::map<std::string, quat> local{{"hips", yaw * lean}, {"thigh.L", rot(-50, {1, 0, 0})}, {"thigh.R", rot(10, {0, 0, 1})},
                                    {"spine", rot(20, {1, 0, 0})}, {"upperArm.L", rot(-70, {0, 0, 1}) * rot(30, {1, 0, 0})}};
  const quat thighL = local["hips"] * local["thigh.L"], thighR = local["hips"] * local["thigh.R"];
  vec3 root(0.5f, -0.2f, 1.0f);
  applyLocomotionStyle(st, local, root, false);
  CHECK(quatAngle(local["hips"], yaw * rot(20, {1, 0, 0})) < 0.01f);  // half the lean, the whole yaw
  CHECK(quatAngle(local["hips"] * local["thigh.L"], thighL) < 0.01f);  // the legs keep their directions
  CHECK(quatAngle(local["hips"] * local["thigh.R"], thighR) < 0.01f);
  CHECK(quatAngle(local["spine"], rot(10, {1, 0, 0})) < 0.01f);
  CHECK(quatAngle(local["upperArm.L"], rot(-70, {0, 0, 1}) * rot(15, {1, 0, 0})) < 0.01f);
  CHECK(root.x == doctest::Approx(0.4f));
  CHECK(root.y == doctest::Approx(-0.2f));
  CHECK(root.z == doctest::Approx(0.8f));
  // head_level: with the full share the head keeps the global orientation it would have on an upright trunk
  LocomotionStyle hl;
  hl.enabled = true;
  hl.headLevel = 1.0f;
  const quat nod = rot(10, {1, 0, 0});
  std::map<std::string, quat> h{{"hips", yaw * lean}, {"spine", rot(15, {1, 0, 0})}, {"head", nod}};
  vec3 r1(0);
  applyLocomotionStyle(hl, h, r1, false);
  CHECK(quatAngle(h["hips"] * h["spine"] * h["head"], yaw * nod) < 0.01f);
  hl.headLevel = 0.5f;
  std::map<std::string, quat> h2{{"hips", lean}, {"head", kNoRot}};
  applyLocomotionStyle(hl, h2, r1, false);
  CHECK(quatAngle(h2["hips"] * h2["head"], rot(20, {1, 0, 0})) < 0.01f);  // half of the 40 degree lean is left
  // mirrored sample: the centre applies to the other side, reflected
  std::map<std::string, quat> m{{"upperArm.R", rot(70, {0, 0, 1}) * rot(30, {1, 0, 0})}};
  vec3 r0(0);
  applyLocomotionStyle(st, m, r0, true);
  CHECK(quatAngle(m["upperArm.R"], rot(70, {0, 0, 1}) * rot(15, {1, 0, 0})) < 0.01f);
}

TEST_CASE("foot lock: plants, loop seam and release") {
  Json clip{{"contacts", Json::array({{{"type", "foot_plant"}, {"role", "foot.L"}, {"frames", {3, 13}}},
                                      {{"type", "foot_plant"}, {"role", "foot.R"}, {"frames", {16, 27}}},
                                      {{"type", "seat"}, {"frames", {0, 5}}, {"height_ratio", 0.4}},
                                      {{"type", "foot_plant"}, {"role", "foot.L"}, {"frames", {9}}}})}};
  const auto plants = footPlants(clip);
  REQUIRE(plants.size() == 2);
  const int N = 26;
  CHECK_FALSE(plantAt(plants, "foot.L", 2.0, N, true, 3).active);
  PlantState p = plantAt(plants, "foot.L", 8.0, N, true, 3);
  CHECK(p.active);
  CHECK(p.start == 3.0);
  CHECK(p.weight == 1.0f);
  p = plantAt(plants, "foot.L", 14.5, N, true, 3);  // releasing
  CHECK(p.active);
  CHECK(p.weight == doctest::Approx(0.5f));
  CHECK_FALSE(plantAt(plants, "foot.L", 16.5, N, true, 3).active);
  p = plantAt(plants, "foot.L", 2 * N + 8.0, N, true, 3);  // third cycle
  CHECK(p.start == 2 * N + 3.0);
  p = plantAt(plants, "foot.R", N + 1.0, N, true, 3);  // the plant that began in the previous cycle (frames 16..27)
  CHECK(p.active);
  CHECK(p.start == 16.0);
  CHECK(p.weight == 1.0f);
  p = plantAt(plants, "foot.R", 0.5, N, true, 3);  // first cycle: the wrapped plant has no earlier start than 0
  CHECK(p.active);
  CHECK(p.start == 0.0);
  // one-shot: the last frame is held, so a plant that reaches it stays
  // ease-in: the pin position is taken foot_in frames into the plant and the weight ramps up to it
  p = plantAt(plants, "foot.L", 4.0, N, true, 3, 2);
  CHECK(p.active);
  CHECK(p.start == 5.0);
  CHECK(p.weight == doctest::Approx(0.5f));
  CHECK(plantAt(plants, "foot.L", 5.0, N, true, 3, 2).weight == 1.0f);
  CHECK(plantAt(plants, "foot.R", 0.0, N, true, 3, 2).weight == 1.0f);  // there from frame 0: holds at once
  p = plantAt(plants, "foot.L", N + 1.0, N, true, 3, 2, 3);  // lead: easing in 2 frames before the plant at N + 3
  CHECK(p.active);
  CHECK(p.start == N + 5.0);
  CHECK(p.weight > 0.0f);
  CHECK(p.weight < 0.5f);
  p = plantAt(plants, "foot.R", 500.0, 28, false, 3);
  CHECK(p.active);
  CHECK(p.weight == 1.0f);
}

TEST_CASE("foot lock: pinFoot reaches the target and keeps the foot's orientation") {
  const Skeleton sk = legSkeleton();
  Pose pose = restPose(sk);
  pose.local[1] = rot(-25, {1, 0, 0});
  pose.local[2] = rot(30, {1, 0, 0});
  pose.local[3] = rot(-5, {1, 0, 0});
  pose.rootOffset = vec3(0.02f, -0.01f, 0.1f);
  const quat footBefore = pose.local[0] * pose.local[1] * pose.local[2] * pose.local[3];
  const vec3 target(0.055f, 0.045f, 0.13f);
  Pose half = pose;
  pinFoot(sk, pose, 3, target, 1.0f);
  auto G = boneGlobals(sk, pose, mat4(1));
  CHECK(glm::length(vec3(G[3][3]) - target) < 1e-4f);
  CHECK(quatAngle(pose.local[0] * pose.local[1] * pose.local[2] * pose.local[3], footBefore) < 0.02f);
  const vec3 free(boneGlobals(sk, half, mat4(1))[3][3]);
  pinFoot(sk, half, 3, target, 0.0f);
  CHECK(glm::length(vec3(boneGlobals(sk, half, mat4(1))[3][3]) - free) < 1e-7f);
  // out of reach: the leg stretches towards the target, no NaN
  Pose far = restPose(sk);
  pinFoot(sk, far, 3, vec3(0.05f, -0.5f, 0.6f), 1.0f);
  for (const quat& q : far.local) CHECK(std::isfinite(q.w + q.x + q.y + q.z));
}

TEST_CASE("foot lock: CMU clips on two characters, planted feet slide <= 3 mm, no popping") {
  for (const char* name : {"cmu_walk", "cmu_sit_down", "cmu_stand_up"}) {
    const fs::path file = kRoot / "content/clips/mocap" / (std::string(name) + ".clip.json");
    Json raw = parseJsonFile(file).value();
    REQUIRE(raw.contains("style"));
    const double tempo = raw["style"].value("tempo", 1.0);
    Json off = raw;
    off["style"]["foot_lock"] = false;
    const fs::path offFile = tempClip(std::string(name) + "_nolock.clip.json", off);
    const bool loop = raw.value("loop", false);
    const int frames = loop ? 72 : int(std::floor((raw["frame_count"].get<int>() - 1) / tempo)) + 1;
    for (const char* pkg : {"boy_yellow_hoodie_1.0.0", "girl_auburn_bun_glasses_m3"}) {
      const Slide with = measure(pkg, file, frames, tempo), without = measure(pkg, offFile, frames, tempo);
      MESSAGE(std::string(name) << " on " << std::string(pkg) << ": planted slide " << with.planted * 1000 << " mm (no lock " << without.planted * 1000
                   << " mm), vertical drift " << with.vertical * 1000 << " mm (no lock " << without.vertical * 1000
                   << " mm), planted ankle vs rest " << with.lowest * 1000 << " .. " << with.highest * 1000 << " mm (no lock "
                   << without.lowest * 1000 << " .. " << without.highest * 1000 << " mm), ankle 2nd difference " << with.pop * 1000
                   << " mm/f^2 (no lock " << without.pop * 1000 << "), pop frames " << with.pops << " (no lock " << without.pops << "), " << with.frames << " planted samples");
      CHECK(with.frames > 10);
      CHECK(with.planted <= 0.003f);
      CHECK(with.vertical <= 0.003f);
      CHECK(std::abs(with.lowest) <= 0.003f);  // planted ankles at their rest height (no floating, no sinking)
      CHECK(std::abs(with.highest) <= 0.003f);
      // No popping from the lock: the ankle's worst second difference stays within the motion_checks visibility
      // floor (8 mm / frame^2) of the clip's own (a mocap footfall already stops within a frame or two).
      CHECK(with.pop <= without.pop + 0.008f);
      CHECK(with.pops <= without.pops + 2);
    }
  }
}

TEST_CASE("foot lock: a clip without a style block is not touched") {
  // The same samples with and without an (all-neutral, lock off) style block give the same pose; the library clips
  // made before T-175 have no block, so their playback is unchanged (goldens: tests/test_bake_golden.cpp).
  Json raw = parseJsonFile(kRoot / "content/clips/mocap/cmu_sit_down.clip.json").value();
  Json plain = raw, neutral = raw;
  plain.erase("style");
  neutral["style"] = {{"version", 1}};
  const fs::path a = tempClip("plain.clip.json", plain), b = tempClip("neutral.clip.json", neutral);
  auto act = [](const fs::path& f) {
    return Json::array({{{"type", "clip"}, {"character", "who"}, {"file", f.string()}, {"start", 1}, {"blendIn", 4}, {"blendOut", 0}}});
  };
  auto ea = sceneWith("boy_yellow_hoodie_1.0.0", act(a), 60), eb = sceneWith("boy_yellow_hoodie_1.0.0", act(b), 60);
  float d = 0;
  for (int f = 1; f <= 40; f += 3) {
    auto Ga = ea->characterGlobals(0, f), Gb = eb->characterGlobals(0, f);
    for (size_t i = 0; i < Ga.size(); ++i)
      for (int c = 0; c < 4; ++c) d = std::max(d, glm::length(Ga[i][c] - Gb[i][c]));
  }
  CHECK(d == 0.0f);
}
