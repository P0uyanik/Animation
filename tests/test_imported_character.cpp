// Imported characters (docs/ENGINE_CHARACTER_PACKAGE.md): the same tests run on two packages that share nothing
// but the package format: boy_yellow_hoodie 1.0.0 (Rigify profile) and an engineering test fixture with different
// bone names, hierarchy, proportions, no fingers and a tail (humanoid_toy_fixture profile). Each behaviour is
// measured; supported behaviours are checked against their criteria, unsupported ones against the documented reason.
#include <doctest/doctest.h>

#include <algorithm>
#include <filesystem>

#include "model/imported_character.h"
#include "scene/scene.h"
#include "scene/shot_bake.h"

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
  for (const char* name : {"boy_yellow_hoodie_1.0.0", "toy_fixture", "girl_auburn_bun_glasses_m2", "girl_auburn_bun_glasses_m3"}) {
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
      bool eyeSkinned = false;  // does any mesh follow the eye bone? (no face yet = bone only)
      for (auto& m : c.rig.meshes)
        for (size_t i = 0; i < m.joints.size() && !eyeSkinned; ++i)
          for (int k = 0; k < 4; ++k) eyeSkinned |= m.joints[i][k] == eye && m.weights[i][k] > 0;
      float moved = maxDisplacement(c.rig, sk, p);
      MESSAGE("look-at: eye axis error " << ang << " deg, eye mesh " << std::string(eyeSkinned ? "moved " : "absent (bone only), moved ")
                                       << moved * 1000 << " mm");
      CHECK(ang < 1.0f);
      if (eyeSkinned) CHECK(moved > 0.001f);
      else CHECK(moved < 1e-5f);  // without eye meshes, gaze must not deform anything (eye bones drive eyes only)
    }
    // Expressions: each morph block deforms its mesh.
    for (size_t t = 0; t < c.rig.morphs.size(); ++t) {
      std::vector<float> w(c.rig.morphs.size(), 0.0f);
      w[t] = 1.0f;
      CHECK(maxDisplacement(c.rig, sk, rest, w) > 1e-4f);
    }
    MESSAGE("expressions: " << c.rig.morphs.size() << " morph blocks each deform their mesh");
    // Grasp: fingertips on a sphere in front of the palm, placed with the hand's own frame (derived from its fingers).
    for (char side : {'L', 'R'}) {
      const HandFrame& hf = side == 'L' ? sk.handL : sk.handR;
      if (!hasRole(c, std::string("thumbA.") + side)) {
        MESSAGE("grasp " << std::string(1, side) << ": unsupported (no finger roles; hand frame " << c.handFrameSource[side == 'L' ? 0 : 1] << ")");
        CHECK(fingertips(sk, rest, mat4(1), side).empty());
        CHECK(c.handFrameSource[side == 'L' ? 0 : 1] == "none");
        continue;
      }
      REQUIRE(c.handFrameSource[side == 'L' ? 0 : 1] == "derived");
      // A stick held across the hand (as in the engine's own grasp test): axis = the hand's across direction (index
      // - pinky), placed in the opening between thumb and fingers, radius from that opening. All from the hand's data.
      const std::string s = std::string(".") + side;
      auto H = [&](const std::string& b) { return sk.bones[size_t(sk.find(b + s))].head; };
      const vec3 hand = H("hand"), fingersB = 0.25f * (H("f0b") + H("f1b") + H("f2b") + H("f3b"));
      const vec3 n = glm::normalize(hf.palmNormal), axis = glm::normalize(H("f3a") - H("f0a"));
      vec3 mid = 0.5f * (fingersB + H("thumbB"));
      const float r = 0.35f * glm::length((fingersB - H("thumbB")) - axis * glm::dot(fingersB - H("thumbB"), axis));
      HandPose gp{0, 0, 0};
      gp.grasp = true;
      gp.graspRadius = r;
      gp.graspAxis = axis;
      gp.graspCentre = (mid - hand) + n * (0.5f * r);
      Pose p = restPose(sk);
      applyHandPose(sk, p, mat4(1), side, gp);
      const vec3 centre = hand + gp.graspCentre;
      auto tips = fingertips(sk, p, mat4(1), side);
      float worst = 0, worstFar = 0;
      for (auto& t : tips) {
        vec3 dd = t - centre;
        dd -= axis * glm::dot(dd, axis);
        float gap = glm::length(dd) - r;
        worst = std::max(worst, std::abs(gap));
        worstFar = std::max(worstFar, gap);
      }
      MESSAGE("grasp " << std::string(1, side) << ": " << tips.size() << " fingertips, worst |gap| " << worst * 1000 << " mm (radius " << r * 1000 << " mm)");
      CHECK(tips.size() == 5);
      CHECK(worstFar < 0.007f);  // every fingertip rests on the object (finger tube radius 4.5 mm)
    }
  }
}

TEST_CASE("imported character packages: walk and idle through the scene") {
  for (const char* name : {"boy_yellow_hoodie_1.0.0", "toy_fixture", "girl_auburn_bun_glasses_m2", "girl_auburn_bun_glasses_m3"}) {
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
      CHECK(maxLift - minLift > 0.035f * legLength(sk));  // feet leave the ground (relative to leg length)
      CHECK(sliding <= 6);  // step length from the character's legs (walkStep)
      MESSAGE("walk: step " << walkStep(ev->characters()[0].asset) * 1000 << " mm for legs " << legLength(sk) * 1000 << " mm");
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

TEST_CASE("imported character packages: blink morph in the life layer and per-character expression names") {
  for (const char* name : {"boy_yellow_hoodie_1.0.0", "toy_fixture", "girl_auburn_bun_glasses_m2", "girl_auburn_bun_glasses_m3"}) {
    CAPTURE(name);
    // Blink: the life layer drives the morph mapped to "blink" (no lid bones exist; none are rotated).
    auto ev = sceneWith(name, Json::array(), true);
    const auto& ci = ev->characters()[0];
    if (!ci.asset.expressionMap.count("blink")) {  // no face yet (e.g. a base body): reported, not faked
      MESSAGE("blink and expressions: unsupported for this package (no blink morph, " << ci.rig.morphs.size() << " morphs)");
      CHECK(ci.rig.morphs.empty());
      Json actions = Json::parse(R"([{"type": "expression", "character": "who", "name": "smile", "start": 5}])");
      auto ev2 = sceneWith(name, actions, false);
      CHECK(ev2->warnings().size() == 1);  // the missing expression is reported
      continue;
    }
    const std::string blink = ci.asset.expressionMap.at("blink");
    const LifeParams& life = ev->scene().characters[0].life;
    int open = -1, closed = -1;
    for (int f = 1; f < 600 && (open < 0 || closed < 0); ++f) {
      float b = blinkAmount(f / 30.0, life.blinkInterval, life.seed);
      if (b == 0 && open < 0) open = f;
      if (b > 0.99f && closed < 0) closed = f;
    }
    REQUIRE(open > 0);
    REQUIRE(closed > 0);
    auto a = ev->evaluate(open), b = ev->evaluate(closed);
    // The meshes carrying the blink morph move between an open and a closed frame.
    float moved = 0;
    for (auto& mt : ci.rig.morphs)
      if (mt.name == blink)
        for (uint32_t v : mt.vertices)
          moved = std::max(moved, glm::distance(a->meshes[size_t(mt.mesh)].mesh->positions[v], b->meshes[size_t(mt.mesh)].mesh->positions[v]) -
                                      0.0f);
    MESSAGE("blink (morph '" << blink << "'): closed frame " << closed << ", morph vertices moved " << moved * 1000 << " mm");
    CHECK(moved > 0.001f);
    // Expressions by engine name resolve to the character's own morph; a missing one is reported.
    Json actions = Json::parse(R"([{"type": "expression", "character": "who", "name": "blink", "start": 5},
                                   {"type": "expression", "character": "who", "name": "smile", "start": 5}])");
    auto ev2 = sceneWith(name, actions, false);
    CHECK(ev2->scene().animation.evaluate("who/expr." + blink, 20, vec3(0)).x > 0.99f);
    bool hasSmile = ev2->characters()[0].asset.expressionMap.count("smile") > 0;
    bool warned = false;
    for (auto& w : ev2->warnings()) warned |= w.find("'smile'") != std::string::npos;
    MESSAGE("expressions: smile " << std::string(hasSmile ? "mapped" : "missing -> warning") << "; warnings " << ev2->warnings().size());
    CHECK(warned == !hasSmile);
  }
}

TEST_CASE("imported character packages: semantic expressions from the shared face library") {
  // The generic face (face_generic/1) bakes library presets into morphs and maps engine expression names to them
  // (per character, no engine change). Each mapped expression must resolve, reach full weight and move the face.
  for (const char* name : {"girl_auburn_bun_glasses_m3"}) {
    CAPTURE(name);
    auto ev0 = sceneWith(name, Json::array(), false);
    const auto map = ev0->characters()[0].asset.expressionMap;
    REQUIRE(map.count("happy"));
    auto rest = ev0->evaluate(20);
    for (const char* e : {"happy", "sad", "surprised", "angry", "laugh", "squint", "confused", "frown", "blink", "jawOpen"}) {
      CAPTURE(e);
      REQUIRE(map.count(e));
      Json actions = Json::parse(std::string(R"([{"type": "expression", "character": "who", "name": ")") + e + R"(", "start": 5}])");
      auto ev = sceneWith(name, actions, false);
      CHECK(ev->warnings().empty());
      CHECK(ev->scene().animation.evaluate("who/expr." + map.at(e), 20, vec3(0)).x > 0.99f);
      auto posed = ev->evaluate(20);
      float moved = 0;
      for (size_t m = 0; m < posed->meshes.size(); ++m) {
        const auto& p1 = posed->meshes[m].mesh->positions;
        const auto& p0 = rest->meshes[m].mesh->positions;
        for (size_t v = 0; v < p1.size(); ++v) moved = std::max(moved, glm::distance(p0[v], p1[v]));
      }
      MESSAGE("expression '" << std::string(e) << "' -> morph '" << map.at(e) << "': max vertex motion " << moved * 1000 << " mm");
      CHECK(moved > 0.002f);
    }
  }
}

namespace {
// Skinning matrices of character 0 at a frame (as SceneEvaluator::evaluate builds them).
std::vector<mat4> skinAt(const SceneEvaluator& ev, double frame) {
  const auto& ci = ev.characters()[0];
  auto skin = ev.characterGlobals(0, frame);
  for (size_t b = 0; b < skin.size(); ++b) skin[b] = skin[b] * glm::translate(mat4(1), -ci.asset.skeleton.bones[b].head);
  return skin;
}
int meshPart(const CharacterRig& rig, const std::string& part) {
  for (size_t k = 0; k < rig.meshes.size(); ++k)
    if (rig.meshes[k].part == part) return int(k);
  return -1;
}
}  // namespace

TEST_CASE("morph in-betweens: piecewise chain weights") {
  CharacterAsset a;
  a.morphInbetweens["Blink"] = {{0.25f, "Blink@25"}, {0.5f, "Blink@50"}, {0.75f, "Blink@75"}};
  const std::vector<std::string> names{"Smile", "Blink", "Blink@25", "Blink@50", "Blink@75"};
  auto w = [&](float smile, float blink) { return expandInbetweens(a, names, {smile, blink, 0.3f, 0.3f, 0.3f}); };
  auto r = w(0.4f, 0.0f);  // no blink: the whole chain is off, other morphs untouched (their own channels ignored)
  CHECK(r == std::vector<float>{0.4f, 0, 0, 0, 0});
  r = w(0, 0.125f);
  CHECK(r[2] == doctest::Approx(0.5f));
  CHECK(r[1] + r[3] + r[4] == 0.0f);
  r = w(0, 0.6f);  // between the 50% and 75% stops
  CHECK(r[3] == doctest::Approx(0.6f));
  CHECK(r[4] == doctest::Approx(0.4f));
  r = w(0, 1.0f);
  CHECK(r[1] == 1.0f);
  CHECK(r[2] + r[3] + r[4] == 0.0f);
  CharacterAsset none;  // no metadata: weights pass through unchanged (e.g. the boy 1.0.0 package)
  CHECK(expandInbetweens(none, names, {0.1f, 0.5f, 0.2f, 0.3f, 0.4f}) == std::vector<float>{0.1f, 0.5f, 0.2f, 0.3f, 0.4f});
}

TEST_CASE("imported character packages: blink stays outside the eyeball at every closure (in-betweens)") {
  // Girl M3: the upper lid must never enter the eyeball while closing. With the exported in-between chain the lid
  // follows its arc; a single linear morph (the chain removed) cuts through the eye halfway, as measured in M3.
  auto ev = sceneWith("girl_auburn_bun_glasses_m3", Json::array(), false);
  const auto& ci = ev->characters()[0];
  REQUIRE(ci.asset.morphInbetweens.count("Blink"));
  const auto skin = skinAt(*ev, 1);
  std::vector<std::string> names;
  for (auto& mt : ci.rig.morphs) names.push_back(mt.name);
  for (const char* side : {"L", "R"}) {
    CAPTURE(side);
    const int eye = meshPart(ci.rig, std::string("eye.") + side), lid = meshPart(ci.rig, std::string("lid_upper.") + side);
    REQUIRE(eye >= 0);
    REQUIRE(lid >= 0);
    vec3 c(0);  // eyeball centre = centroid of its (closed, symmetric) mesh
    for (auto& p : ci.rig.meshes[size_t(eye)].rest.positions) c += p;
    c /= float(ci.rig.meshes[size_t(eye)].rest.positions.size());
    float r = 0;
    for (auto& p : ci.rig.meshes[size_t(eye)].rest.positions) r = std::max(r, glm::distance(p, c));
    for (bool chain : {true, false}) {
      CharacterAsset a = ci.asset;
      if (!chain) a.morphInbetweens.clear();
      float worst = 1e9f;
      for (float b : {0.1f, 0.25f, 0.4f, 0.5f, 0.6f, 0.75f, 0.9f, 1.0f}) {
        std::vector<float> w(names.size(), 0.0f);
        for (size_t i = 0; i < names.size(); ++i)
          if (names[i] == "Blink") w[i] = b;
        auto posed = poseCharacter(ci.rig, skin, expandInbetweens(a, names, w), ci.asset.dualQuaternion);
        vec3 pc(0);  // centre of the posed eyeball (same frame as the posed lid)
        for (auto& p : posed.meshes[size_t(eye)]->positions) pc += p;
        pc /= float(posed.meshes[size_t(eye)]->positions.size());
        for (auto& p : posed.meshes[size_t(lid)]->positions) worst = std::min(worst, glm::distance(p, pc) - r);
      }
      MESSAGE("lid clearance over the blink, " << std::string(chain ? "in-between chain" : "single linear morph") << ": " << worst * 1000 << " mm");
      if (chain) CHECK(worst > 0.0003f);  // the lid shell stays outside the eyeball (measured 0.51 mm; chord error of the 25% steps)
      else CHECK(worst < 0.0f);           // the old linear interpolation enters the eye (the M3 engine limitation)
    }
  }
}

TEST_CASE("imported character packages: expression-driven jaw bone") {
  // The girl's package maps JawOpen, MouthOpen, Laugh, Smile (happy) and Surprise to DEF-jaw rotations taken from her
  // face configuration; the C++ code reads names and angles from the package only.
  auto ev0 = sceneWith("girl_auburn_bun_glasses_m3", Json::array(), false);
  const auto& asset = ev0->characters()[0].asset;
  REQUIRE(asset.expressionBones.count("MouthOpen"));
  const auto rest = ev0->evaluate(20);
  const auto restG = ev0->characterGlobals(0, 20);
  for (const char* e : {"mouthOpen", "laugh", "happy", "jawOpen"}) {
    CAPTURE(e);
    const std::string morph = asset.expressionMap.at(e);
    Json actions = Json::parse(std::string(R"([{"type": "expression", "character": "who", "name": ")") + e + R"(", "start": 5}])");
    auto ev = sceneWith("girl_auburn_bun_glasses_m3", actions, false);
    const auto& eb = asset.expressionBones.at(morph)[0];
    const int jaw = asset.skeleton.find(eb.bone);
    REQUIRE(jaw >= 0);
    const auto g = ev->characterGlobals(0, 20);
    const int parent = asset.skeleton.bones[size_t(jaw)].parent;
    // jaw rotation relative to its parent, compared with the metadata angle
    const quat rel0 = glm::quat_cast(glm::inverse(mat3(restG[size_t(parent)])) * mat3(restG[size_t(jaw)]));
    const quat rel1 = glm::quat_cast(glm::inverse(mat3(g[size_t(parent)])) * mat3(g[size_t(jaw)]));
    const float deg = glm::degrees(glm::angle(glm::inverse(rel0) * rel1));
    // lowest point of the skin near the face midline (the chin) moves down
    const auto posed = ev->evaluate(20);
    const int skinMesh = meshPart(ev->characters()[0].rig, "body_skin");
    REQUIRE(skinMesh >= 0);
    float drop = 0;
    const auto& p0 = rest->meshes[size_t(skinMesh)].mesh->positions;
    const auto& p1 = posed->meshes[size_t(skinMesh)].mesh->positions;
    for (size_t v = 0; v < p0.size(); ++v) drop = std::max(drop, p0[v].y - p1[v].y);
    MESSAGE("expression '" << std::string(e) << "' (" << morph << "): jaw " << deg << " deg (metadata " << eb.degrees << "), skin drop " << drop * 1000 << " mm");
    CHECK(deg == doctest::Approx(eb.degrees).epsilon(0.02));
    CHECK(drop > 0.001f * eb.degrees);  // > 1 mm of chin drop per degree of jaw rotation (girl: 10 deg -> > 10 mm)
  }
  // A package without jaw metadata keeps morph-only expressions (reported, nothing invented).
  auto boy = sceneWith("boy_yellow_hoodie_1.0.0", Json::array(), false);
  CHECK(boy->characters()[0].asset.expressionBones.empty());
}

TEST_CASE("per-character blink timing from the package") {
  auto girl = sceneWith("girl_auburn_bun_glasses_m3", Json::array(), true);
  auto boy = sceneWith("boy_yellow_hoodie_1.0.0", Json::array(), true);
  const LifeParams g = girl->lifeParams(0), b = boy->lifeParams(0);
  CHECK(g.blinkInterval == doctest::Approx(3.2f));
  CHECK(g.blinkClose == doctest::Approx(0.08f));
  CHECK(g.blinkHold == doctest::Approx(0.04f));
  CHECK(g.blinkOpen == doctest::Approx(0.14f));
  // the boy's package has no timing: the original global defaults (frozen baseline)
  CHECK(b.blinkInterval == doctest::Approx(3.6f));
  CHECK(b.blinkClose == doctest::Approx(0.07f));
  CHECK(b.blinkHold == doctest::Approx(0.03f));
  CHECK(b.blinkOpen == doctest::Approx(0.12f));
  // measured blink shape: time from the first non-zero closure to fully open again
  auto duration = [](const LifeParams& l) {
    double first = -1, last = -1;
    for (double t = 0; t < 30; t += 0.0005) {
      float v = blinkAmount(t, l.blinkInterval, l.seed, l.blinkClose, l.blinkHold, l.blinkOpen);
      if (v > 0 && first < 0) first = t;
      if (first >= 0 && v == 0 && t > first) {
        last = t;
        break;
      }
    }
    return last - first;
  };
  MESSAGE("blink duration: girl " << duration(g) << " s, boy " << duration(b) << " s");
  CHECK(duration(g) == doctest::Approx(0.26).epsilon(0.02));
  CHECK(duration(b) == doctest::Approx(0.22).epsilon(0.02));
  // default arguments reproduce the original curve exactly
  for (double t = 0; t < 10; t += 0.013) CHECK(blinkAmount(t, 3.6f, 7u) == blinkAmount(t, 3.6f, 7u, 0.07f, 0.03f, 0.12f));
  // an explicit scene interval wins over the character's
  Scene s;
  s.path = std::filesystem::path(PLUSH_SOURCE_DIR) / "tests/data/imported/scene.json";
  s.rate = FrameRate{30, 1};
  CharacterDesc cd;
  cd.name = "who";
  cd.asset = "girl_auburn_bun_glasses_m3/character.json";
  cd.life.enabled = true;
  cd.life.blinkInterval = 5.0f;
  cd.life.blinkIntervalSet = true;
  s.characters.push_back(cd);
  SceneEvaluator ev;
  REQUIRE(ev.load(s, EvalOptions{2.5f, 1.0f, false, 0}).has_value());
  CHECK(ev.lifeParams(0).blinkInterval == doctest::Approx(5.0f));
  CHECK(ev.lifeParams(0).blinkClose == doctest::Approx(0.08f));
}

TEST_CASE("shot bake: engine animation hand-off (plush.shot_bake/1)") {
  // The bake carries exactly the skinning the engine renders: rebuilding the posed mesh from the baked matrices and
  // control weights reproduces SceneEvaluator::evaluate (the production renderer receives the same animation).
  Json actions = Json::parse(R"([{"type": "expression", "character": "who", "name": "laugh", "start": 2},
                                 {"type": "look", "character": "who", "start": 1, "end": 30, "target": [0.4, 0.8, 1.0]}])");
  auto ev = sceneWith("girl_auburn_bun_glasses_m3", actions, true);
  Json bake = bakeShot(*ev, 1, 20);
  CHECK(bake["format"] == "plush.shot_bake");
  CHECK(bake["version"] == 1);
  REQUIRE(bake["frame_data"].size() == 20);
  const auto& ci = ev->characters()[0];
  const Json& ch = bake["characters"][0];
  CHECK(ch["supported"].get<bool>());
  REQUIRE(ch["bones"].size() == ci.asset.skeleton.bones.size());
  const Json& fd = bake["frame_data"][19]["characters"]["who"];
  std::vector<mat4> skin(ci.asset.skeleton.bones.size());
  for (size_t b = 0; b < skin.size(); ++b)
    for (int k = 0; k < 16; ++k) skin[b][k / 4][k % 4] = fd["skin"][b * 16 + k].get<float>();
  std::vector<std::string> unique = ch["morphs"].get<std::vector<std::string>>(), names;
  std::vector<float> w;
  for (auto& mt : ci.rig.morphs) {
    names.push_back(mt.name);
    size_t k = size_t(std::find(unique.begin(), unique.end(), mt.name) - unique.begin());
    w.push_back(fd["morphs"][k].get<float>());
  }
  auto rebuilt = poseCharacter(ci.rig, skin, expandInbetweens(ci.asset, names, w), ci.asset.dualQuaternion);
  auto ref = ev->evaluate(20);
  float worst = 0;
  for (size_t m = 0; m < rebuilt.meshes.size(); ++m)
    for (size_t v = 0; v < rebuilt.meshes[m]->positions.size(); ++v)
      worst = std::max(worst, glm::distance(rebuilt.meshes[m]->positions[v], ref->meshes[m].mesh->positions[v]));
  MESSAGE("bake round trip: max vertex difference " << worst * 1000 << " mm");
  CHECK(worst < 1e-5f);
  CHECK(glm::distance(vec3(bake["frame_data"][0]["camera"]["position"][0].get<float>(), bake["frame_data"][0]["camera"]["position"][1].get<float>(),
                           bake["frame_data"][0]["camera"]["position"][2].get<float>()),
                      ev->cameraAt(1).position) < 1e-6f);
}

TEST_CASE("hand pose is independent of hand orientation and works with fewer digits") {
  // The original chibi hand (engine convention, grasp verified in test_engine.cpp), and the same skeleton rotated by an
  // arbitrary rotation Q with its hand frame rotated likewise: the grasp must give exactly Q x the original fingertips.
  auto asset = loadCharacter(std::filesystem::path(PLUSH_SOURCE_DIR) / "content/characters/boy_dark_hair.character.json");
  REQUIRE(asset.has_value());
  const Skeleton& sk = asset->skeleton;
  const quat Q = glm::angleAxis(glm::radians(70.0f), glm::normalize(vec3(1, 0.4f, 0.3f)));
  Skeleton rot = sk;
  for (auto& b : rot.bones) b.head = Q * b.head;
  rot.handL = HandFrame{Q * vec3(0, -1, 0), Q * vec3(-1, 0, 0)};
  const float r = 0.012f;
  HandPose gp{0, 0, 0};
  gp.grasp = true;
  gp.graspRadius = r;
  gp.graspCentre = vec3(-0.004f - r, -0.03f, 0.008f);
  Pose p0 = restPose(sk), p1 = restPose(rot);
  applyHandPose(sk, p0, mat4(1), 'L', gp);
  HandPose gq = gp;
  gq.graspCentre = Q * gp.graspCentre;
  applyHandPose(rot, p1, mat4(1), 'L', gq);
  auto t0 = fingertips(sk, p0, mat4(1), 'L'), t1 = fingertips(rot, p1, mat4(1), 'L');
  REQUIRE(t0.size() == 5);
  REQUIRE(t1.size() == 5);
  float worst = 0;
  for (size_t i = 0; i < 5; ++i) worst = std::max(worst, glm::distance(Q * t0[i], t1[i]));
  MESSAGE("rotated hand: max fingertip difference " << worst * 1000 << " mm");
  CHECK(worst < 1e-4f);
  // Fewer digits: rename two fingers away; the remaining thumb and two fingers still grasp, the hand is not skipped.
  Skeleton three = sk;
  for (auto& b : three.bones)
    if (b.name.rfind("f0", 0) == 0 || b.name.rfind("f2", 0) == 0) b.name = "x_" + b.name;
  HandPose gc = gp;  // stick across the palm, as in the engine's own grasp test
  gc.graspAxis = vec3(0, 0, 1);
  Pose p3 = restPose(three);
  applyHandPose(three, p3, mat4(1), 'L', gc);
  auto t3 = fingertips(three, p3, mat4(1), 'L');
  REQUIRE(t3.size() == 3);
  vec3 centre = sk.bones[size_t(sk.find("hand.L"))].head + gc.graspCentre;
  for (auto& t : t3) {
    vec3 dd = t - centre;
    dd.z = 0;
    CHECK(glm::length(dd) - r < 0.007f);
  }
  // A single digit is not a hand: grasp reports unsupported (no tips), nothing is posed.
  Skeleton one = three;
  for (auto& b : one.bones)
    if (b.name.rfind("f1", 0) == 0 || b.name.rfind("f3", 0) == 0) b.name = "x_" + b.name;
  CHECK(fingertips(one, restPose(one), mat4(1), 'L').empty());
}
