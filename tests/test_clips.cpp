// Animation clips (model/clip.h, scene clip layers; T-002): parsing (sparse, dense, unknown fields), fps
// resampling, retargeting on two synthetic skeletons with different rest poses and proportions (<= 0.5 degrees),
// mirroring, blend continuity, layering priority (walk, reach IK, hand keys), base clip, and the package retarget
// block against the data derived from the skeleton.
#include <doctest/doctest.h>

#include <unistd.h>

#include <cstdlib>
#include <fstream>

#include "model/clip.h"
#include "model/imported_character.h"
#include "scene/scene.h"

using namespace plush;
namespace fs = std::filesystem;

namespace {
const fs::path kRoot = PLUSH_SOURCE_DIR;
Json profileReference() {
  return parseJsonFile(kRoot / "pipeline/charsys/rig_profiles/humanoid_rigify.json").value()["reference_pose"];
}
Json q4(quat q) { return Json::array({q.w, q.x, q.y, q.z}); }
quat rot(float deg, vec3 axis) { return glm::angleAxis(glm::radians(deg), glm::normalize(axis)); }
float angleBetween(vec3 a, vec3 b) {  // atan2 form: accurate for small angles
  glm::dvec3 x = glm::normalize(glm::dvec3(a)), y = glm::normalize(glm::dvec3(b));
  return float(glm::degrees(std::atan2(glm::length(glm::cross(x, y)), glm::dot(x, y))));
}
float quatAngle(quat a, quat b) {  // double precision: float acos near 1 cannot resolve angles below ~0.04 degrees
  glm::dquat x = glm::normalize(glm::dquat(a)), y = glm::normalize(glm::dquat(b));
  double d = std::abs(x.w * y.w + x.x * y.x + x.y * y.y + x.z * y.z), s = glm::length(glm::dvec3(y.x, y.y, y.z) * x.w - glm::dvec3(x.x, x.y, x.z) * y.w - glm::cross(glm::dvec3(x.x, x.y, x.z), glm::dvec3(y.x, y.y, y.z)));  // |vec(conj(x) y)|
  return float(glm::degrees(2.0 * std::atan2(s, d)));
}
void addBone(Skeleton& sk, const std::string& n, const std::string& parent, vec3 head) {
  sk.bones.push_back({n, parent.empty() ? -1 : sk.find(parent), head});
}
// Synthetic skeleton A: mannequin-like T-pose, arms parented to the chest, legs to the hips.
Skeleton skeletonA() {
  Skeleton s;
  addBone(s, "hips", "", {0, 0.50f, 0});
  addBone(s, "spine", "hips", {0, 0.60f, 0});
  addBone(s, "chest", "spine", {0, 0.75f, 0});
  addBone(s, "neck", "chest", {0, 0.90f, 0});
  addBone(s, "head", "neck", {0, 0.97f, 0});
  for (float sx : {1.0f, -1.0f}) {
    std::string S = sx > 0 ? ".L" : ".R";
    addBone(s, "upperArm" + S, "chest", {sx * 0.10f, 0.85f, 0});
    addBone(s, "forearm" + S, "upperArm" + S, {sx * 0.30f, 0.85f, 0});
    addBone(s, "hand" + S, "forearm" + S, {sx * 0.48f, 0.85f, 0});
    addBone(s, "thumbA" + S, "hand" + S, {sx * 0.50f, 0.85f, 0.03f});
    addBone(s, "thumbB" + S, "thumbA" + S, {sx * 0.52f, 0.85f, 0.05f});
    const float z[4] = {-0.02f, -0.007f, 0.007f, 0.02f};
    for (int f = 0; f < 4; ++f) {
      std::string a = "f" + std::to_string(f) + "a" + S, b = "f" + std::to_string(f) + "b" + S;
      addBone(s, a, "hand" + S, {sx * 0.55f, 0.85f, z[f]});
      addBone(s, b, a, {sx * 0.58f, 0.85f, z[f]});
    }
    addBone(s, "thigh" + S, "hips", {sx * 0.06f, 0.48f, 0});
    addBone(s, "shin" + S, "thigh" + S, {sx * 0.06f, 0.26f, 0});
    addBone(s, "foot" + S, "shin" + S, {sx * 0.06f, 0.04f, 0});
  }
  return s;
}
// Synthetic skeleton B: different proportions, A-pose arms hanging 50 degrees below horizontal with the hands
// turned (palms towards the body), a slightly forward-leaning spine, a helper bone between spine and chest, and arms
// and legs as top-level bones (as in the Rigify packages).
Skeleton skeletonB() {
  Skeleton s;
  addBone(s, "hips", "", {0, 0.36f, 0.01f});
  addBone(s, "spine", "hips", {0, 0.44f, 0.0f});
  addBone(s, "helper.spine", "spine", {0, 0.52f, 0.01f});
  addBone(s, "chest", "helper.spine", {0, 0.60f, 0.02f});
  addBone(s, "neck", "chest", {0, 0.70f, 0.03f});
  addBone(s, "head", "neck", {0, 0.76f, 0.02f});
  const float a = glm::radians(50.0f);
  for (float sx : {1.0f, -1.0f}) {
    std::string S = sx > 0 ? ".L" : ".R";
    vec3 sh(sx * 0.12f, 0.66f, 0.01f), d(sx * std::cos(a), -std::sin(a), 0.05f);
    d = glm::normalize(d);
    addBone(s, "upperArm" + S, "", sh);
    addBone(s, "forearm" + S, "upperArm" + S, sh + d * 0.13f);
    vec3 wr = sh + d * 0.25f;
    addBone(s, "hand" + S, "forearm" + S, wr);
    addBone(s, "thumbA" + S, "hand" + S, wr + d * 0.015f + vec3(0, 0, 0.02f));
    addBone(s, "thumbB" + S, "thumbA" + S, wr + d * 0.03f + vec3(0, 0, 0.035f));
    const float z[4] = {-0.018f, -0.006f, 0.006f, 0.018f};
    for (int f = 0; f < 4; ++f) {
      std::string an = "f" + std::to_string(f) + "a" + S, bn = "f" + std::to_string(f) + "b" + S;
      vec3 base = wr + d * 0.05f + vec3(0, 0, z[f]);
      addBone(s, an, "hand" + S, base);
      addBone(s, bn, an, base + d * 0.025f);
    }
    addBone(s, "thigh" + S, "", {sx * 0.05f, 0.34f, 0});
    addBone(s, "shin" + S, "thigh" + S, {sx * 0.055f, 0.20f, 0.01f});
    addBone(s, "foot" + S, "shin" + S, {sx * 0.06f, 0.05f, 0});
  }
  return s;
}
// A clip moving many roles (sparse keys, 30 fps, 31 frames).
Json testClipJson(bool dense = false, double fps = 30) {
  Json tracks = Json::object();
  auto keyed = [&](const std::string& role, quat a, quat b) {
    if (dense) {
      Json s = Json::array();
      int n = int(std::round(fps)) + 1;
      for (int k = 0; k < n; ++k) s.push_back(q4(glm::slerp(a, b, float(k) / float(n - 1))));
      tracks[role] = {{"samples", s}};
    } else {
      tracks[role] = {{"keys", Json::array({Json::array({0, a.w, a.x, a.y, a.z}), Json::array({fps, b.w, b.x, b.y, b.z})})}};
    }
  };
  keyed("hips", rot(5, {0, 1, 0}), rot(-10, {1, 0, 0}));
  keyed("spine", rot(8, {1, 0, 0}), rot(-6, {0, 0, 1}));
  keyed("chest", rot(-5, {1, 1, 0}), rot(12, {0, 1, 0}));
  keyed("neck", rot(10, {1, 0, 0}), rot(-15, {0, 1, 0}));
  keyed("head", rot(-8, {0, 1, 1}), rot(20, {1, 0, 0}));
  keyed("upperArm.L", rot(-70, {0, 0, 1}), rot(40, {0, 1, 1}));   // from arms down to raised forward
  keyed("forearm.L", rot(10, {0, 1, 0}), rot(80, {0, 1, 0}));
  keyed("hand.L", rot(15, {1, 0, 0}), rot(-30, {0, 0, 1}));
  keyed("upperArm.R", rot(65, {0, 0, 1}), rot(-20, {1, 0, 0}));
  keyed("forearm.R", rot(-20, {0, 1, 0}), rot(-60, {0, 1, 0}));
  keyed("thigh.L", rot(-30, {1, 0, 0}), rot(10, {0, 0, 1}));
  keyed("shin.L", rot(40, {1, 0, 0}), rot(5, {1, 0, 0}));
  keyed("foot.L", rot(-10, {1, 0, 0}), rot(15, {0, 1, 0}));
  keyed("thigh.R", rot(20, {1, 0, 0}), rot(-25, {1, 0, 0}));
  keyed("shin.R", rot(5, {1, 0, 0}), rot(60, {1, 0, 0}));
  keyed("f3a.L", rot(0, {0, 0, 1}), rot(70, {0, 0, 1}));
  keyed("thumbA.L", rot(10, {0, 1, 0}), rot(-20, {1, 0, 0}));
  return {{"format", "plush.clip"}, {"version", 1}, {"name", "synthetic"}, {"fps", fps}, {"frame_count", int(std::round(fps)) + 1},
          {"loop", false}, {"source", "script"}, {"license", "project"}, {"attribution", "test"}, {"tracks", tracks},
          {"reference_pose", profileReference()}, {"x_future_field", {{"kept", true}}},
          {"root", {{"translation", {{"keys", Json::array({Json::array({0, 0, 0, 0}), Json::array({fps, 0.1, -0.2, 0.3})})}}}}}};
}
// Rotation of every role's posed frame (G · C) after applying a sample to a skeleton at rest.
std::map<std::string, std::pair<vec3, vec3>> posedFrames(const Skeleton& sk, const ReferencePose& ref, const ClipSample& s) {
  RetargetData d = deriveRetarget(sk, ref);
  ClipBinding b = bindClip(sk, ref, d);
  Pose p = restPose(sk);
  applyClipSample(sk, b, s, p, [](const std::string&) { return 1.0f; });
  auto G = boneGlobals(sk, p, mat4(1));
  std::map<std::string, std::pair<vec3, vec3>> out;
  for (auto& [role, _] : d.roles) out[role] = {posedRoleDirection(sk, G, d, role), posedRoleTwist(sk, G, d, role)};
  return out;
}
// Expected posed frame from the clip alone: R = R_parent · L, direction = R · ref_dir.
std::map<std::string, std::pair<vec3, vec3>> expectedFrames(const ReferencePose& ref, const ClipSample& s) {
  std::map<std::string, quat> R;
  std::map<std::string, std::pair<vec3, vec3>> out;
  for (auto& r : ref.roles) {
    quat Rp = r.parent.empty() || !R.count(r.parent) ? quat(1, 0, 0, 0) : R[r.parent];
    auto it = s.local.find(r.name);
    R[r.name] = Rp * (it == s.local.end() ? quat(1, 0, 0, 0) : it->second);
    out[r.name] = {R[r.name] * r.refDir, R[r.name] * r.refTwist};
  }
  return out;
}
fs::path writeTemp(const std::string& name, const Json& j) {
  fs::path d = fs::temp_directory_path() / std::format("plush_clips_{}", ::getpid());
  fs::create_directories(d);
  std::ofstream(d / name) << j.dump();
  return d / name;
}
std::unique_ptr<SceneEvaluator> sceneWith(const char* pkg, const Json& actions, int frameEnd = 90) {
  Scene s;
  s.path = kRoot / "tests/data/imported/scene.json";
  s.rate = FrameRate{30, 1};
  s.frameStart = 1;
  s.frameEnd = frameEnd;
  CharacterDesc cd;
  cd.name = "who";
  cd.asset = std::string(pkg) + "/character.json";
  s.characters.push_back(cd);
  s.actions = actions;
  auto ev = std::make_unique<SceneEvaluator>();
  auto r = ev->load(s, EvalOptions{2.5f, 1.0f, false, 0});
  REQUIRE(r.has_value());
  return ev;
}
// Per-role global rotation of a character at a frame.
std::map<std::string, quat> roleRotations(const SceneEvaluator& ev, double f) {
  const Skeleton& sk = ev.characters()[0].asset.skeleton;
  auto G = ev.characterGlobals(0, f);
  std::map<std::string, quat> out;
  for (const char* r : {"hips", "spine", "chest", "neck", "head", "upperArm.L", "forearm.L", "hand.L", "upperArm.R", "forearm.R",
                        "hand.R", "thigh.L", "shin.L", "foot.L", "thigh.R", "shin.R", "foot.R"}) {
    int b = sk.find(r);
    if (b >= 0) out[r] = glm::normalize(glm::quat_cast(mat3(G[size_t(b)])));
  }
  return out;
}
}  // namespace

TEST_CASE("clips: parsing (sparse, dense, unknown fields, required license)") {
  auto ref = referencePoseFromJson(profileReference());
  REQUIRE(ref);
  CHECK(ref->roles.size() == 37);  // 21 profile entries, 16 '.L' roles mirrored to '.R'
  CHECK(ref->find("upperArm.R")->refDir.x == doctest::Approx(-1));
  CHECK(ref->find("upperArm.R")->parent == "chest");
  for (size_t i = 0; i < ref->roles.size(); ++i)  // semantic parents precede children
    if (!ref->roles[i].parent.empty()) CHECK(ref->index.at(ref->roles[i].parent) < int(i));
  auto sparse = clipFromJson(testClipJson(false));
  REQUIRE(sparse);
  CHECK(sparse->tracks.size() == 17);
  CHECK(sparse->tracks.at("upperArm.L").frames.size() == 2);
  CHECK(sparse->mask.size() == 17);
  CHECK(sparse->raw.contains("x_future_field"));  // unknown fields are preserved
  CHECK(sparse->hasRoot());
  auto dense = clipFromJson(testClipJson(true));
  REQUIRE(dense);
  CHECK(dense->tracks.at("upperArm.L").frames.size() == 31);
  // dense and sparse play the same motion
  for (double f : {0.0, 7.5, 15.0, 29.0, 30.0}) {
    auto a = sampleClip(*sparse, f), b = sampleClip(*dense, f);
    for (auto& [r, q] : a.local) CHECK(quatAngle(q, b.local.at(r)) < 0.05f);
  }
  Json noLicense = testClipJson();
  noLicense.erase("license");
  CHECK_FALSE(clipFromJson(noLicense).has_value());
  Json bad = testClipJson();
  bad["tracks"]["hips"] = {{"neither", 1}};
  CHECK_FALSE(clipFromJson(bad).has_value());
}

TEST_CASE("clips: fps resampling (60 fps dense vs 30 fps sparse, speed)") {
  // The same motion stored at 60 fps (dense samples) and at 30 fps (two keys): played in a 30 fps scene they agree.
  auto c30 = clipFromJson(testClipJson(false, 30)).value();
  auto c60 = clipFromJson(testClipJson(true, 60)).value();
  CHECK(c60.frameCount == 61);
  CHECK(c60.duration() == doctest::Approx(c30.duration()));
  const double sceneFps = 30;
  for (double sf = 0; sf <= 30; sf += 1) {
    auto a = sampleClip(c30, sf * c30.fps / sceneFps), b = sampleClip(c60, sf * c60.fps / sceneFps);
    for (auto& [r, q] : a.local) CHECK(quatAngle(q, b.local.at(r)) < 0.05f);
    CHECK(glm::distance(a.root, b.root) < 1e-5f);
  }
  // speed 2: a 24 fps scene sees frame k of the clip at scene frame k * 24 / (2 * 30)
  auto s = sampleClip(c30, 12.0 * 2 * 30 / 24.0), t = sampleClip(c30, 30.0);
  CHECK(quatAngle(s.local.at("upperArm.L"), t.local.at("upperArm.L")) < 0.01f);
}

TEST_CASE("clips: retargeting on two synthetic skeletons with different rest poses and proportions") {
  auto ref = referencePoseFromJson(profileReference()).value();
  const Skeleton A = skeletonA(), B = skeletonB();
  auto clip = clipFromJson(testClipJson()).value();
  float maxDir = 0, maxTwist = 0, maxExpected = 0;
  for (double f : {0.0, 10.0, 20.0, 30.0}) {
    ClipSample s = sampleClip(clip, f);
    auto a = posedFrames(A, ref, s), b = posedFrames(B, ref, s), e = expectedFrames(ref, s);
    CHECK(a.size() == 37);
    for (auto& [role, fa] : a) {
      if (!clip.tracks.count(role)) continue;  // roles the clip does not drive keep each skeleton's own rest pose
      REQUIRE(b.count(role));
      maxDir = std::max(maxDir, angleBetween(fa.first, b[role].first));
      maxTwist = std::max(maxTwist, angleBetween(fa.second, b[role].second));
      maxExpected = std::max({maxExpected, angleBetween(fa.first, e[role].first), angleBetween(fa.second, e[role].second)});
    }
  }
  MESSAGE("synthetic skeletons: max direction difference " << maxDir << " deg, twist " << maxTwist << " deg, vs clip "
                                                           << maxExpected << " deg");
  CHECK(maxDir <= 0.5f);
  CHECK(maxTwist <= 0.5f);
  CHECK(maxExpected <= 0.5f);
  // The reference pose itself (identity clip) puts both skeletons in the T-pose.
  ClipSample id;
  for (auto& r : ref.roles) id.local[r.name] = quat(1, 0, 0, 0);
  auto b = posedFrames(B, ref, id);
  CHECK(angleBetween(b["upperArm.L"].first, vec3(1, 0, 0)) < 0.01f);
  CHECK(angleBetween(b["upperArm.R"].first, vec3(-1, 0, 0)) < 0.01f);
  CHECK(angleBetween(b["thigh.L"].first, vec3(0, -1, 0)) < 0.01f);
  CHECK(angleBetween(b["hand.L"].second, vec3(0, 0, 1)) < 0.01f);
}

TEST_CASE("clips: mirroring swaps sides and reflects across x = 0") {
  auto ref = referencePoseFromJson(profileReference()).value();
  auto clip = clipFromJson(testClipJson()).value();
  for (const Skeleton& sk : {skeletonA(), skeletonB()}) {
    for (double f : {5.0, 25.0}) {
      auto plain = posedFrames(sk, ref, sampleClip(clip, f, false)), mir = posedFrames(sk, ref, sampleClip(clip, f, true));
      for (const char* r : {"upperArm.L", "forearm.L", "hand.L", "thigh.L", "shin.L", "f3a.L"}) {
        std::string m = mirrorRole(clip, r);
        vec3 d = plain[r].first, dm = mir[m].first;
        CHECK(angleBetween(vec3(-d.x, d.y, d.z), dm) < 0.05f);
      }
      vec3 h = plain["head"].first, hm = mir["head"].first;
      CHECK(angleBetween(vec3(-h.x, h.y, h.z), hm) < 0.05f);
    }
    auto s = sampleClip(clip, 30, true);
    CHECK(s.root.x == doctest::Approx(-0.1f));
  }
}

TEST_CASE("clips: loop seam and root accumulation") {
  Json j = testClipJson();
  j["loop"] = true;
  j["root"]["cycle_offset"] = {0.0, 0.0, 0.5};
  auto c = clipFromJson(j).value();
  // across the seam (frame 30 -> 31 = 0 of the next cycle) the root keeps going, no reset
  auto a = sampleClip(c, 30.5), b = sampleClip(c, 31.0), b2 = sampleClip(c, 31.0 + 31.0);
  CHECK(b.root.z == doctest::Approx(0.5f));
  CHECK(b2.root.z == doctest::Approx(1.0f));
  CHECK(a.root.z > 0.29f);
}

TEST_CASE("clips: retarget block equals the data derived from the skeleton") {
  auto ref = referencePoseFromJson(profileReference()).value();
  for (const Skeleton& sk : {skeletonA(), skeletonB()}) {
    RetargetData d = deriveRetarget(sk, ref);
    auto back = retargetFromJson(retargetToJson(d));
    REQUIRE(back);
    CHECK(retargetMaxDifferenceDeg(d, *back) < 1e-3f);
    CHECK(back->legLength == doctest::Approx(d.legLength));
  }
  // A package exported with a "retarget" block (set PLUSH_TEST_PACKAGE; run by the pipeline tests on new exports).
  if (const char* p = std::getenv("PLUSH_TEST_PACKAGE"); p && *p) {
    for (std::string path : {std::string(p)}) {
      size_t start = 0;
      while (start <= path.size()) {
        size_t end = path.find(':', start);
        std::string one = path.substr(start, end == std::string::npos ? std::string::npos : end - start);
        start = end == std::string::npos ? path.size() + 1 : end + 1;
        auto pk = loadImportedCharacter(one);
        REQUIRE(pk);
        REQUIRE(pk->asset.retargetBlock.is_object());
        auto block = retargetFromJson(pk->asset.retargetBlock).value();
        RetargetData derived = deriveRetarget(pk->asset.skeleton, ref);
        float diff = retargetMaxDifferenceDeg(derived, block);
        MESSAGE(one << ": block vs derived max difference " << diff << " deg, leg " << block.legLength << " / " << derived.legLength);
        CHECK(diff < 0.01f);
        CHECK(block.roles.size() == derived.roles.size());
        CHECK(block.legLength == doctest::Approx(derived.legLength).epsilon(1e-4));
        CHECK(block.height == doctest::Approx(derived.height).epsilon(1e-4));
      }
    }
  }
}

TEST_CASE("clips: scene playback on two characters, blending, base clip and layering priority") {
  auto clip = testClipJson();
  clip["frame_count"] = 31;
  const fs::path armFile = writeTemp("arm.clip.json", [&] {
    Json j = clip;
    j["mask"] = {"upperArm.R", "forearm.R"};
    j.erase("root");  // an arm-only clip
    return j;
  }());
  // base: a gentle loop around a relaxed stance (arms down)
  Json base = clip;
  base["loop"] = true;
  base["frame_count"] = 60;
  base.erase("root");
  Json bt = Json::object();
  auto keys = [&](quat a, quat b) {
    return Json{{"keys", Json::array({Json::array({0, a.w, a.x, a.y, a.z}), Json::array({30, b.w, b.x, b.y, b.z})})}};
  };
  bt["upperArm.L"] = keys(rot(-75, {0, 0, 1}), rot(-72, {0, 0, 1}));
  bt["upperArm.R"] = keys(rot(75, {0, 0, 1}), rot(72, {0, 0, 1}));
  bt["chest"] = keys(rot(0, {1, 0, 0}), rot(2, {1, 0, 0}));
  base["tracks"] = bt;
  base["mask"] = {"upperArm.L", "upperArm.R", "chest"};
  const fs::path baseFile = writeTemp("base.clip.json", base);

  SUBCASE("same clip, both characters: matching role directions (life off)") {
    const fs::path full = writeTemp("full.clip.json", clip);
    Json acts = Json::array({{{"type", "clip"}, {"character", "who"}, {"file", full.string()}, {"start", 1}, {"blendIn", 0}, {"blendOut", 0}}});
    auto boy = sceneWith("boy_yellow_hoodie_1.0.0", acts), girl = sceneWith("girl_auburn_bun_glasses_m3", acts);
    auto ref = clipFromJson(clip).value().reference;
    auto rb = boy->retargetData(0, ref), rg = girl->retargetData(0, ref);
    CHECK(rb.source == "derived");  // these test packages predate the retarget block
    float maxD = 0;
    for (double f : {2.0, 10.0, 20.0, 30.0}) {
      auto Gb = boy->characterGlobals(0, f), Gg = girl->characterGlobals(0, f);
      for (const char* r : {"upperArm.L", "forearm.L", "upperArm.R", "forearm.R", "thigh.L", "shin.L", "thigh.R", "shin.R", "spine", "chest", "neck", "head"})
        maxD = std::max(maxD, angleBetween(posedRoleDirection(boy->characters()[0].asset.skeleton, Gb, rb, r),
                                           posedRoleDirection(girl->characters()[0].asset.skeleton, Gg, rg, r)));
    }
    MESSAGE("test packages boy vs girl: max role direction difference " << maxD << " deg");
    CHECK(maxD <= 2.0f);
  }
  SUBCASE("blend in / out: no pop, bounded per-frame change") {
    Json acts = Json::array({{{"type", "clip"}, {"character", "who"}, {"file", baseFile.string()}, {"base", true}},
                             {{"type", "clip"}, {"character", "who"}, {"file", armFile.string()}, {"start", 20}, {"blendIn", 10}, {"blendOut", 10}}});
    auto ev = sceneWith("boy_yellow_hoodie_1.0.0", acts);
    auto baseOnly = sceneWith("boy_yellow_hoodie_1.0.0", Json::array({acts[0]}));
    float maxStep = 0, entry = 0;
    for (double f = 2; f <= 70; f += 1) {
      auto a = roleRotations(*ev, f - 1), b = roleRotations(*ev, f);
      maxStep = std::max(maxStep, quatAngle(a["upperArm.R"], b["upperArm.R"]));
    }
    // the frame the clip starts (weight 0) equals the underlying pose; the next frame differs by one blend step
    entry = quatAngle(roleRotations(*ev, 20)["upperArm.R"], roleRotations(*baseOnly, 20)["upperArm.R"]);
    MESSAGE("arm clip on the base: max per-frame change " << maxStep << " deg, entry difference " << entry << " deg");
    CHECK(entry < 1e-3f);
    CHECK(maxStep <= 12.0f);
    // after the clip ends the base pose returns exactly
    CHECK(quatAngle(roleRotations(*ev, 60)["upperArm.R"], roleRotations(*baseOnly, 60)["upperArm.R"]) < 1e-3f);
  }
  SUBCASE("base clip replaces the default pose; walk arm swing is added on top; walk keeps the legs") {
    Json walk = {{"type", "walk"}, {"character", "who"}, {"start", 10}, {"end", 50}, {"to", {0.0, 0.4}}};
    auto noBase = sceneWith("boy_yellow_hoodie_1.0.0", Json::array({walk}));
    auto withBase = sceneWith("boy_yellow_hoodie_1.0.0", Json::array({{{"type", "clip"}, {"character", "who"}, {"file", baseFile.string()}, {"base", true}}, walk}));
    const Skeleton& sk = withBase->characters()[0].asset.skeleton;
    auto ref = clipFromJson(base).value().reference;
    auto rd = withBase->retargetData(0, ref);
    // arms down with the base (A-pose without)
    vec3 dBase = posedRoleDirection(sk, withBase->characterGlobals(0, 2), rd, "upperArm.L");
    vec3 dNo = posedRoleDirection(sk, noBase->characterGlobals(0, 2), rd, "upperArm.L");
    CHECK(dBase.y < -0.9f);
    CHECK(dNo.y > dBase.y + 0.1f);
    // arm swing during the walk changes the arm relative to the base alone
    auto baseOnly = sceneWith("boy_yellow_hoodie_1.0.0", Json::array({{{"type", "clip"}, {"character", "who"}, {"file", baseFile.string()}, {"base", true}}}));
    float swing = 0;
    for (double f = 15; f <= 45; f += 2)
      swing = std::max(swing, angleBetween(posedRoleDirection(sk, withBase->characterGlobals(0, f), rd, "upperArm.L"),
                                           posedRoleDirection(sk, baseOnly->characterGlobals(0, f), rd, "upperArm.L")));
    CHECK(swing > 5.0f);
    // the legs during the walk are the walk's (same as without the base clip)
    for (double f : {20.0, 30.0, 40.0})
      for (const char* r : {"hips", "thigh.L", "shin.L", "thigh.R", "shin.R"})
        CHECK(quatAngle(roleRotations(*withBase, f)[r], roleRotations(*noBase, f)[r]) < 1e-3f);
  }
  SUBCASE("a full-body clip during a walk leaves legs and root to the walk; reach IK keeps priority; hand keys win") {
    const fs::path full = writeTemp("full2.clip.json", clip);
    Json walk = {{"type", "walk"}, {"character", "who"}, {"start", 5}, {"end", 60}, {"to", {0.0, 0.5}}};
    auto walkOnly = sceneWith("boy_yellow_hoodie_1.0.0", Json::array({walk}));
    auto both = sceneWith("boy_yellow_hoodie_1.0.0", Json::array({walk, {{"type", "clip"}, {"character", "who"}, {"file", full.string()}, {"start", 15}}}));
    for (const char* r : {"thigh.L", "shin.L", "hips"})
      CHECK(quatAngle(roleRotations(*both, 30)[r], roleRotations(*walkOnly, 30)[r]) < 0.01f);
    CHECK(quatAngle(roleRotations(*both, 30)["upperArm.L"], roleRotations(*walkOnly, 30)["upperArm.L"]) > 5.0f);  // arms: the clip
    // wave-while-walking rule: an arm clip replaces the walk's arm swing only on its mask; the other arm keeps the
    // swing; legs, hips and root stay the walk's
    auto armWalk = sceneWith("boy_yellow_hoodie_1.0.0", Json::array({walk, {{"type", "clip"}, {"character", "who"}, {"file", armFile.string()}, {"start", 15}}}));
    for (double f : {25.0, 30.0, 35.0}) {
      auto a = roleRotations(*armWalk, f), w = roleRotations(*walkOnly, f);
      CHECK(quatAngle(a["upperArm.R"], w["upperArm.R"]) > 5.0f);   // masked arm: the clip
      CHECK(quatAngle(a["upperArm.L"], w["upperArm.L"]) < 1e-3f);  // other arm: the walk swing
      for (const char* r : {"hips", "thigh.L", "shin.L", "thigh.R", "shin.R", "spine", "chest"}) CHECK(quatAngle(a[r], w[r]) < 1e-3f);
      Pose pa, pw;
      armWalk->characterGlobals(0, f, &pa);
      walkOnly->characterGlobals(0, f, &pw);
      CHECK(glm::distance(pa.rootOffset, pw.rootOffset) < 1e-6f);
    }
    // reach on the right arm while an arm clip plays on the same arm: the IK target wins
    Scene s;
    s.path = kRoot / "tests/data/imported/scene.json";
    s.rate = FrameRate{30, 1};
    CharacterDesc cd;
    cd.name = "who";
    cd.asset = "boy_yellow_hoodie_1.0.0/character.json";
    s.characters.push_back(cd);
    vec3 shoulder;
    {
      SceneEvaluator probe;
      REQUIRE(probe.load(s, EvalOptions{2.5f, 1.0f, false, 0}));
      shoulder = vec3(probe.characterGlobals(0, 1)[size_t(probe.characters()[0].asset.skeleton.find("upperArm.R"))][3]);
    }
    const vec3 cupAt = shoulder + vec3(-0.03f, -0.08f, 0.12f);  // within reach, in front of the right shoulder
    ObjectDesc box;
    box.name = "cup";
    box.kind = ObjectDesc::Kind::Box;
    box.boxMin = cupAt - vec3(0.01f);
    box.boxMax = cupAt + vec3(0.01f);
    box.position = cupAt;  // reach targets the object position
    s.objects.push_back(box);
    s.actions = Json::array({{{"type", "clip"}, {"character", "who"}, {"file", armFile.string()}, {"start", 1}, {"blendIn", 0}, {"end", 80}},
                             {{"type", "reach"}, {"character", "who"}, {"hand", "R"}, {"object", "cup"}, {"start", 10}, {"contact", 25}, {"look", false}}});
    SceneEvaluator ev;
    REQUIRE(ev.load(s, EvalOptions{2.5f, 1.0f, false, 0}));
    s.actions = Json::array({s.actions[1]});
    SceneEvaluator ref;
    REQUIRE(ref.load(s, EvalOptions{2.5f, 1.0f, false, 0}));
    const int hand = ev.characters()[0].asset.skeleton.find("hand.R");
    float d = glm::distance(vec3(ev.characterGlobals(0, 25)[size_t(hand)][3]), vec3(ref.characterGlobals(0, 25)[size_t(hand)][3]));
    const vec3 tgt = ev.scene().animation.evaluate("who/ik.hand.R", 25, vec3(0));
    CHECK(glm::distance(tgt, vec3(ev.characterGlobals(0, 25)[size_t(hand)][3])) < 0.001f);  // the IK target is reached
    MESSAGE("reach with an arm clip on the same arm: wrist differs by " << d * 1000 << " mm from reach alone");
    CHECK(d < 0.005f);
    // hand keys win over the clip
    Scene k = s;
    k.actions = Json::array({{{"type", "clip"}, {"character", "who"}, {"file", armFile.string()}, {"start", 1}, {"blendIn", 0}, {"end", 80}}});
    k.animation.tracks["who/upperArm.R.rot"].setKey({1, vec3(10, 20, 30)});
    SceneEvaluator kev;
    REQUIRE(kev.load(k, EvalOptions{2.5f, 1.0f, false, 0}));
    Pose p;
    kev.characterGlobals(0, 15, &p);
    CHECK(quatAngle(p.local[size_t(kev.characters()[0].asset.skeleton.find("upperArm.R"))], eulerDegreesToQuat(vec3(10, 20, 30))) < 0.01f);
  }
}
