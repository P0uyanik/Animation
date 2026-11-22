// T-198 motion continuity (docs/evaluation/interaction/T-198/README.md): the per-frame speed limit (anim/animation.h
// MotionLimits, motionJumps), intent exemptions by data (scene/interaction.h continuityExemptions), and the source fixes
// that keep generated motion under the limit (touch ramps and finger curl, a look that swings across the looker's head,
// the hand-orientation blend), and a ratchet over the shipped content scenes.
#include <doctest/doctest.h>

#include <filesystem>
#include <fstream>
#include <map>
#include <memory>
#include <set>
#include <string>
#include <vector>

#include "anim/animation.h"
#include "scene/asset_library.h"
#include "scene/interaction.h"
#include "scene/scene.h"

using namespace plush;
namespace fs = std::filesystem;

namespace {

const fs::path kRoot = PLUSH_SOURCE_DIR;
const char* kBoy = "boy_yellow_hoodie_1.0.0/character.json";

Scene baseScene(int frameEnd) {
  Scene s;
  s.name = "continuity test";
  s.path = kRoot / "tests/data/imported/scene.json";
  s.rate = FrameRate{24, 1};
  s.frameStart = 1;
  s.frameEnd = frameEnd;
  CharacterDesc c;
  c.name = "actor";
  c.asset = kBoy;
  c.life.enabled = true;
  s.characters.push_back(c);
  return s;
}

std::unique_ptr<SceneEvaluator> load(const Scene& scene) {
  auto ev = std::make_unique<SceneEvaluator>();
  auto r = ev->load(scene, EvalOptions{2.5f, 1.0f, false, 0});
  if (!r) FAIL(r.error().message);
  return ev;
}

vec3 bonePos(const SceneEvaluator& ev, const char* bone, double f) {
  const int b = ev.characters()[0].asset.skeleton.find(bone);
  REQUIRE(b >= 0);
  return vec3(ev.characterGlobals(0, f)[size_t(b)][3]);
}

int snaps(const SceneEvaluator& ev) {
  int n = 0;
  for (const ContinuityRow& r : continuityReport(ev))
    if (r.exempt.empty()) {
      MESSAGE("snap: " << r.character << " f" << r.jump.frame << " " << r.bone << " " << r.jump.deg << " deg / " << r.jump.mm << " mm");
      ++n;
    }
  return n;
}

}  // namespace

TEST_CASE("continuity: bone classes and the per-frame limit") {
  CHECK(motionBoneClass("hand.R") == MotionBoneClass::Body);
  CHECK(motionBoneClass("head") == MotionBoneClass::Body);
  CHECK(motionBoneClass("f1a.R") == MotionBoneClass::Finger);
  CHECK(motionBoneClass("thumbB.L") == MotionBoneClass::Finger);
  CHECK(motionBoneClass("eye.L") == MotionBoneClass::None);
  CHECK(motionBoneClass("DEF-spine.005") == MotionBoneClass::None);

  auto ev = load(baseScene(4));
  const Skeleton& sk = ev->characters()[0].asset.skeleton;
  const std::vector<mat4> g = ev->characterGlobals(0, 1);
  auto moved = [&](float metres) {
    std::vector<mat4> m = g;
    for (mat4& x : m) x = glm::translate(mat4(1), vec3(metres, 0, 0)) * x;
    return m;
  };
  // 50 mm in a frame at 24 fps is under the 100 mm limit; 200 mm is over for every body bone and no finger (fingers
  // have no travel limit and do not turn relative to their parents), eye or helper bone.
  CHECK(motionJumps(sk, {g, moved(0.05f)}, 1, 24).empty());
  const auto jumps = motionJumps(sk, {g, moved(0.2f)}, 1, 24);
  REQUIRE_FALSE(jumps.empty());
  bool hips = false;
  for (const MotionJump& j : jumps) {
    CHECK(j.frame == 2);
    CHECK(motionBoneClass(sk.bones[size_t(j.bone)].name) == MotionBoneClass::Body);
    CHECK(j.mm == doctest::Approx(200).epsilon(0.01));
    hips = hips || sk.bones[size_t(j.bone)].name == "hips";
  }
  CHECK(hips);
  // The same step is under the limit at a third of the speed (8 fps).
  CHECK(motionJumps(sk, {g, moved(0.2f)}, 1, 8).empty());
}

TEST_CASE("continuity: intended jumps by data (cut = camera or own position step, fast = an action's flag)") {
  Scene s = baseScene(40);
  CharacterDesc other = s.characters[0];
  other.name = "other";
  other.position = vec3(1, 0, 0);
  s.characters.push_back(other);
  s.animation.tracks["camera.position"].keys = {{1, vec3(0, 1, 3), Interp::Step}, {10, vec3(2, 1, 3), Interp::Step}};
  s.animation.tracks["actor.position"].keys = {{1, vec3(0), Interp::Step}, {30, vec3(0.5f, 0, 0), Interp::Step}};
  s.animation.tracks["other.position"].keys = {{1, vec3(1, 0, 0), Interp::Linear}, {30, vec3(1.5f, 0, 0), Interp::Linear}};
  s.actions = Json::parse(R"([{"type": "look", "character": "actor", "start": 20, "end": 24, "target": [0, 1, 2], "fast": true}])");
  const auto a = continuityExemptions(s, "actor"), o = continuityExemptions(s, "other");
  CHECK(a.at(10) == "cut");
  CHECK(a.at(30) == "cut");
  for (int f = 20; f <= 25; ++f) CHECK(a.at(f) == "fast");
  CHECK_FALSE(a.count(19));
  CHECK_FALSE(a.count(26));
  CHECK(o.at(10) == "cut");  // the camera cuts for everyone
  CHECK_FALSE(o.count(30));  // a linear move is not a cut
  CHECK_FALSE(o.count(22));  // the fast action names the actor
}

TEST_CASE("continuity: a touch that ends before contact + 10 ramps out without a jump") {
  Scene s = baseScene(60);
  auto probe = load(s);
  const vec3 shoulder = bonePos(*probe, "upperArm.R", 1), hand = bonePos(*probe, "hand.R", 1);
  const float arm = glm::distance(shoulder, hand);
  const vec3 target = shoulder + vec3(-0.1f, -0.25f, 0.75f) * arm;
  s.actions = Json::parse(R"([{"type": "touch", "character": "actor", "hand": "R", "start": 10, "contact": 20, "end": 27}])");
  s.actions[0]["target"] = {target.x, target.y, target.z};
  auto ev = load(s);
  const Clip& clip = ev->scene().animation;
  const std::string w = "actor/ik." + std::string("hand.R") + ".weight";
  REQUIRE(clip.find(w));
  // After the contact the arm only lets go: the IK weight never rises again (it used to jump 0 -> 1 after the end).
  for (int f = 21; f <= 60; ++f) CHECK(clip.evaluate(w, f, vec3(0)).x <= clip.evaluate(w, f - 1, vec3(0)).x + 1e-5f);
  CHECK(clip.evaluate(w, 20, vec3(0)).x == doctest::Approx(1));
  CHECK(snaps(*ev) == 0);
}

TEST_CASE("continuity: a look that swings across the looker's head turns round it; a clear one is keyed as before") {
  Scene s = baseScene(60);
  auto probe = load(s);
  const vec3 head = bonePos(*probe, "head", 1);
  auto scene = [&](float side, float front) {
    Scene t = s;
    t.actions = Json::parse(R"([{"type": "look", "character": "actor", "start": 1, "end": 29},
                                {"type": "look", "character": "actor", "start": 30, "end": 60}])");
    const vec3 a = head + vec3(side, 0, front), b = head + vec3(-side, 0, front);
    t.actions[0]["target"] = {a.x, a.y, a.z};
    t.actions[1]["target"] = {b.x, b.y, b.z};
    return t;
  };
  // From one side straight through the head to the other (the e912 s020 case): over the limit as keyed straight.
  auto through = load(scene(1.5f, 0.05f));
  const Track* arc = through->scene().animation.find("actor/continuity.lookArc");
  REQUIRE(arc);
  CHECK(arc->evaluate(30).x == doctest::Approx(1));
  CHECK(arc->evaluate(29).x == doctest::Approx(0));
  CHECK(snaps(*through) == 0);
  // A small shift in front: no arc, no marker.
  auto clear = load(scene(0.3f, 2.0f));
  CHECK_FALSE(clear->scene().animation.find("actor/continuity.lookArc"));
  CHECK(snaps(*clear) == 0);
}

TEST_CASE("continuity: a grasp whose hand turns nearly opposite in a short ramp turns one way, under the limit") {
  // test_bake_golden.cpp visibleGrip (boy): the shortest-path blend from the clip hand to the planned grip changed
  // side between two frames (the hand turned 147 deg in frame 11).
  Scene s = baseScene(40);
  auto probe = load(s);
  const vec3 shoulder = bonePos(*probe, "upperArm.R", 1), elbow = bonePos(*probe, "forearm.R", 1);
  const float arm = glm::distance(shoulder, elbow) + glm::distance(elbow, bonePos(*probe, "hand.R", 1));
  const mat4 rot = assetTransformMatrix({vec3(0), vec3(0, 180, 0), vec3(1)});
  const PropAsset cupAsset = loadAsset(kRoot / "content/assets/felt_cup.asset.json").value();
  PropDesc cup;
  cup.name = "cup";
  cup.id = "prop.felt_cup";
  cup.transform.translation = shoulder + vec3(0.04f, -0.45f, 0.85f) * arm - vec3(rot * vec4(cupAsset.sockets.at("grip").translation, 0));
  cup.transform.rotationDeg = {0, 180, 0};
  s.props.push_back(cup);
  s.camera.position = cup.transform.translation + vec3(-1.5f, 0.3f, 0.2f);
  s.camera.target = cup.transform.translation;
  s.actions = Json::parse(R"([
      {"type": "grasp", "character": "actor", "hand": "R", "prop": "cup", "start": 5, "contact": 20},
      {"type": "hold", "character": "actor", "hand": "R", "start": 22, "end": 36, "by": [0, 0.04, 0]}])");
  s.interaction = Json{{"visibleGrip", true}};
  auto ev = load(s);
  for (const ContinuityRow& r : continuityReport(*ev)) CHECK_MESSAGE(r.bone != "hand.R", "f" << r.jump.frame << " " << r.jump.deg << " deg");
  // The blend is keyed per frame (weight 1) only over that ramp.
  CHECK(ev->scene().animation.evaluate("actor/orient.hand.R.weight", 11, vec3(0)).x == doctest::Approx(1));
}

TEST_CASE("continuity: shipped content scenes stay under the per-frame limit (ratchet on the recorded rows)") {
  // Every unexempt row of continuityReport on the shipped content scenes (cast = the imported test packages, as
  // test_bake_golden.cpp contentScene) must be a recorded row of the baseline (scene, character, frame, bone) whose
  // turn / travel does not grow. Recorded rows: grasp / release finger curls (follow-up T-210) and one walk start.
  std::ifstream in(kRoot / "docs/evaluation/interaction/T-198/continuity_baseline.json");
  REQUIRE(in.good());
  const Json base = Json::parse(in);
  std::map<std::string, std::pair<float, float>> recorded;
  for (const Json& r : base["rows"])
    recorded[r["scene"].get<std::string>() + " " + r["character"].get<std::string>() + " f" + std::to_string(r["frame"].get<int>()) + " " +
             r["bone"].get<std::string>()] = {r["deg"].get<float>(), r["mm"].get<float>()};
  std::set<std::string> seen;
  for (const char* rel : {"content/scenes/eval/exchange/shot.scene.json", "content/scenes/eval/handover/shot.scene.json",
                          "episodes/e901_clip_test/shots/s010/shot.scene.json", "episodes/e905_props_test/shots/s010/shot.scene.json",
                          "episodes/e907_exchange/shots/s010/shot.scene.json", "episodes/e907_exchange/shots/s010_calibrated/shot.scene.json"}) {
    auto s = loadScene(kRoot / rel);
    REQUIRE(s);
    Scene scene = *s;
    for (CharacterDesc& c : scene.characters) {
      if (c.name == "boy") c.asset = (kRoot / "tests/data/imported" / kBoy).string();
      if (c.name == "girl") c.asset = (kRoot / "tests/data/imported/girl_auburn_bun_glasses_m3/character.json").string();
    }
    auto ev = load(scene);
    for (const ContinuityRow& r : continuityReport(*ev)) {
      if (!r.exempt.empty()) continue;
      const std::string key = std::string(rel) + " " + r.character + " f" + std::to_string(r.jump.frame) + " " + r.bone;
      seen.insert(key);
      const auto it = recorded.find(key);
      CHECK_MESSAGE(it != recorded.end(), "new snap: " << key << " " << r.jump.deg << " deg / " << r.jump.mm << " mm");
      if (it == recorded.end()) continue;
      CHECK_MESSAGE(r.jump.deg <= it->second.first + 0.01f, "grew: " << key << " " << r.jump.deg << " deg (recorded " << it->second.first << ")");
      CHECK_MESSAGE(r.jump.mm <= it->second.second + 0.01f, "grew: " << key << " " << r.jump.mm << " mm (recorded " << it->second.second << ")");
    }
  }
  for (const auto& [key, v] : recorded)
    if (!seen.count(key)) MESSAGE("recorded row no longer over the limit (remove it from the baseline): " << key);
}
