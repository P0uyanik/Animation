// Imported characters (docs/ENGINE_CHARACTER_PACKAGE.md): the same tests run on two packages that share nothing
// but the package format: boy_yellow_hoodie 1.0.0 (Rigify profile) and an engineering test fixture with different
// bone names, hierarchy, proportions, no fingers and a tail (humanoid_toy_fixture profile). Each behaviour is
// measured; supported behaviours are checked against their criteria, unsupported ones against the documented reason.
#include <doctest/doctest.h>

#include <algorithm>
#include <filesystem>

#include "model/imported_character.h"
#include "scene/scene.h"

using namespace plush;

namespace {
std::filesystem::path pkg(const char* name) {
  return std::filesystem::path(PLUSH_SOURCE_DIR) / "tests/data/imported" / name / "character.json";
}
float figureHeight(const Skeleton& sk) {
  float lo = 1e9f, hi = -1e9f;
  for (auto& b : sk.bones) lo = std::min(lo, b.head.y), hi = std::max(hi, b.head.y);
  return hi - lo;
}
float maxDisplacement(const CharacterRig& rig, const Skeleton& sk, const Pose& pose, const std::vector<float>& morphs = {}) {
  auto skin = skinningMatrices(sk, pose, mat4(1));
  auto posed = poseCharacter(rig, skin, morphs);
  float d = 0;
  for (size_t m = 0; m < rig.meshes.size(); ++m)
    for (size_t i = 0; i < rig.meshes[m].rest.positions.size(); ++i)
      d = std::max(d, glm::distance(posed.meshes[m]->positions[i], rig.meshes[m].rest.positions[i]));
  return d;
}
std::unique_ptr<SceneEvaluator> sceneWith(const char* name, const Json& actions, bool life) {
  Scene s;
  s.path = std::filesystem::path(PLUSH_SOURCE_DIR) / "tests/data/imported/scene.json";  // only its folder is used
  s.rate = FrameRate{30, 1};
  CharacterDesc cd;
  cd.name = "who";
  cd.asset = std::string(name) + "/character.json";
  cd.life.enabled = life;
  s.characters.push_back(cd);
  s.actions = actions;
  auto ev = std::make_unique<SceneEvaluator>();
  auto r = ev->load(s, EvalOptions{2.5f, 1.0f, false, 0});
  REQUIRE(r.has_value());
  REQUIRE(ev->characters()[0].imported);
  return ev;
}
bool hasRole(const ImportedCharacter& c, const std::string& r) {
  return std::find(c.rolesPresent.begin(), c.rolesPresent.end(), r) != c.rolesPresent.end();
}
}  // namespace

TEST_CASE("imported character packages: behaviour support") {
  for (const char* name : {"boy_yellow_hoodie_1.0.0", "toy_fixture"}) {
    CAPTURE(name);
    auto loaded = loadImportedCharacter(pkg(name));
    REQUIRE(loaded.has_value());
    const ImportedCharacter& c = *loaded;
    const Skeleton& sk = c.asset.skeleton;
    const float H = figureHeight(sk);
    MESSAGE(std::string(name) << ": " << sk.bones.size() << " bones, " << c.rig.meshes.size() << " meshes, " << c.rig.morphs.size()
                 << " morph blocks, skeleton height " << H << " m, profile " << c.profile);
    for (size_t b = 0; b < sk.bones.size(); ++b) CHECK(sk.bones[b].parent < int(b));  // parents precede children

    // Rest pose skins to the rest mesh exactly (package convention = engine skinning convention).
    Pose rest = restPose(sk);
    CHECK(maxDisplacement(c.rig, sk, rest) < 1e-5f);

    // Reach (two-bone IK on the left arm) to a reachable target in front of the shoulder.
    {
      int up = sk.find("upperArm.L"), fo = sk.find("forearm.L"), ha = sk.find("hand.L");
      REQUIRE(up >= 0);
      float L = glm::distance(sk.bones[size_t(up)].head, sk.bones[size_t(fo)].head) +
                glm::distance(sk.bones[size_t(fo)].head, sk.bones[size_t(ha)].head);
      vec3 target = sk.bones[size_t(up)].head + 0.8f * L * glm::normalize(vec3(0.3f, -0.3f, 1.0f));
      Pose p = restPose(sk);
      solveTwoBoneIK(sk, p, mat4(1), ha, target, 1.0f);
      float err = glm::distance(vec3(boneGlobals(sk, p, mat4(1))[size_t(ha)][3]), target);
      float moved = maxDisplacement(c.rig, sk, p);
      MESSAGE("reach: hand error " << err * 1000 << " mm, max mesh displacement " << moved * 1000 << " mm");
      CHECK(err < 0.005f);
      CHECK(moved > 0.1f * L);
    }
    // Look-at: aim the left eye at a point in front; the eye's +Z axis must point at it.
    {
      int eye = sk.find("eye.L");
      REQUIRE(eye >= 0);
      vec3 e = sk.bones[size_t(eye)].head, target = e + vec3(0.3f, 0.1f, 1.0f) * H;
      Pose p = restPose(sk);
      aimBone(sk, p, mat4(1), eye, target, 1.0f, 60.0f);
      vec3 axis = glm::normalize(vec3(boneGlobals(sk, p, mat4(1))[size_t(eye)][2]));
      float ang = glm::degrees(std::acos(std::clamp(glm::dot(axis, glm::normalize(target - e)), -1.0f, 1.0f)));
      float moved = maxDisplacement(c.rig, sk, p);
      MESSAGE("look-at: eye axis error " << ang << " deg, eye mesh moved " << moved * 1000 << " mm");
      CHECK(ang < 1.0f);
      CHECK(moved > 0.001f);
    }
    // Expressions: each morph block deforms its mesh.
    for (size_t t = 0; t < c.rig.morphs.size(); ++t) {
      std::vector<float> w(c.rig.morphs.size(), 0.0f);
      w[t] = 1.0f;
      CHECK(maxDisplacement(c.rig, sk, rest, w) > 1e-4f);
    }
    MESSAGE("expressions: " << c.rig.morphs.size() << " morph blocks each deform their mesh");
    // Blink through the life layer needs lid bones (fixed 86 deg rotation).
    MESSAGE("blink_life: lid bones " << (sk.find("lid.L") >= 0 ? "present" : "absent"));
    CHECK(sk.find("lid.L") < 0);  // documented status: unsupported for both packages (blink is a morph)
    // Grasp: fingertips on a sphere in front of the palm (engine hand convention).
    if (hasRole(c, "thumbA.L")) {
      int ha = sk.find("hand.L");
      float seg = glm::distance(sk.bones[size_t(sk.find("f1a.L"))].head, sk.bones[size_t(sk.find("f1b.L"))].head);
      const float r = seg;
      HandPose gp{0, 0, 0};
      gp.grasp = true;
      gp.graspRadius = r;
      gp.graspCentre = vec3(-0.004f - r, -0.03f, 0.008f);
      Pose p = restPose(sk);
      applyHandPose(sk, p, mat4(1), 'L', gp);
      vec3 centre = sk.bones[size_t(ha)].head + gp.graspCentre;
      auto tips = fingertips(sk, p, mat4(1), 'L');
      float worst = 0;
      for (auto& t : tips) worst = std::max(worst, std::abs(glm::distance(t, centre) - r));
      MESSAGE("grasp: " << tips.size() << " fingertips, worst gap to the sphere " << worst * 1000 << " mm (radius " << r * 1000 << " mm)");
      // Documented status: UNSUPPORTED for A-pose imports. The finger chains resolve (5 tips) but contact fails: the
      // engine hand code assumes fingers hanging along -y with the palm facing -x (its own rest pose).
      CHECK(tips.size() == 5);
    } else {
      MESSAGE("grasp: unsupported (no finger roles in this package)");
      CHECK(fingertips(sk, rest, mat4(1), 'L').empty());
    }
  }
}

TEST_CASE("imported character packages: walk and idle through the scene") {
  for (const char* name : {"boy_yellow_hoodie_1.0.0", "toy_fixture"}) {
    CAPTURE(name);
    {
      Json actions = Json::parse(R"([{"type": "walk", "character": "who", "start": 1, "end": 61, "to": [0.0, 0.6]}])");
      auto ev = sceneWith(name, actions, false);
      const auto& sk = ev->characters()[0].asset.skeleton;
      int footL = sk.find("foot.L"), footR = sk.find("foot.R");
      vec3 endPos = ev->scene().animation.evaluate("who.position", 61, vec3(0));
      int sliding = 0;
      float minLift = 1, maxLift = 0;
      for (int f = 2; f < 61; ++f) {
        auto a = ev->characterGlobals(0, f - 1), b = ev->characterGlobals(0, f);
        float dl = glm::distance(vec3(a[size_t(footL)][3]), vec3(b[size_t(footL)][3]));
        float dr = glm::distance(vec3(a[size_t(footR)][3]), vec3(b[size_t(footR)][3]));
        if (std::min(dl, dr) > 0.0025f) ++sliding;
        float y = std::max(b[size_t(footL)][3].y, b[size_t(footR)][3].y);
        minLift = std::min(minLift, y), maxLift = std::max(maxLift, y);
      }
      MESSAGE("walk: end " << glm::distance(endPos, vec3(0, 0, 0.6f)) << " m from target, sliding frames " << sliding
                           << "/59, foot lift " << (maxLift - minLift) * 1000 << " mm");
      CHECK(glm::distance(endPos, vec3(0, 0, 0.6f)) < 1e-4f);
      CHECK(maxLift - minLift > 0.012f);
      // Documented status: the boy meets the engine's no-skating criterion; the short-legged fixture does not
      // (PARTIAL): the walk action uses a fixed 0.11 m step that is not scaled by leg length.
      if (std::string(name) == "toy_fixture") CHECK(sliding > 6);
      else CHECK(sliding <= 6);
    }
    {
      auto ev = sceneWith(name, Json::array(), true);
      const auto& sk = ev->characters()[0].asset.skeleton;
      int chest = sk.find("chest");
      auto c0 = ev->characterGlobals(0, 1);
      float diff = 0;
      for (int f = 2; f < 110; f += 6)
        diff = std::max(diff, glm::distance(vec3(ev->characterGlobals(0, f)[size_t(chest)][2]), vec3(c0[size_t(chest)][2])));
      auto a1 = ev->characterGlobals(0, 50), a2 = ev->characterGlobals(0, 50);
      MESSAGE("idle: chest axis motion " << diff);
      CHECK(diff > 0.008f);
      CHECK(a1[size_t(chest)] == a2[size_t(chest)]);  // deterministic
    }
  }
}
