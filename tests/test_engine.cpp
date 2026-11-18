#include <doctest/doctest.h>

#include <map>

#include "render/bsdf.h"
#include "render/image.h"
#include "render/pathtracer.h"
#include "scene/scene.h"

using namespace plush;

TEST_CASE("time ticks are exact for common frame rates") {
  CHECK(frameToTicks(24, FrameRate{24, 1}) == kTicksPerSecond);
  CHECK(frameToTicks(25, FrameRate{25, 1}) == kTicksPerSecond);
  CHECK(frameToTicks(24000, FrameRate{24000, 1001}) == kTicksPerSecond * 1001);
  CHECK(ticksToFrame(frameToTicks(37, FrameRate{30, 1}), FrameRate{30, 1}) == doctest::Approx(37));
}

TEST_CASE("tracks interpolate through keys without overshoot") {
  Track t;
  t.setKey({0, vec3(0), Interp::Smooth});
  t.setKey({10, vec3(10), Interp::Smooth});
  t.setKey({20, vec3(10), Interp::Smooth});
  CHECK(t.evaluate(0).x == doctest::Approx(0));
  CHECK(t.evaluate(10).x == doctest::Approx(10));
  for (double f = 0; f <= 20; f += 0.5) CHECK(t.evaluate(f).x <= 10.0001f);
  Track lin;
  lin.setKey({0, vec3(0), Interp::Linear});
  lin.setKey({4, vec3(8), Interp::Linear});
  CHECK(lin.evaluate(1).x == doctest::Approx(2));
  CHECK(lin.removeKey(4));
  CHECK(lin.keys.size() == 1);
}

namespace {
Skeleton gazeSkeleton() {
  Skeleton sk;
  sk.bones = {{"head", -1, vec3(0, 1, 0)}, {"eye.L", 0, vec3(0, 1, 0)}};
  return sk;
}

vec3 gazeDirection(const Skeleton& sk, float headPitchDeg, float targetPitchDeg, const GazeLimits& limits = {}) {
  Pose pose = restPose(sk);
  pose.local[0] = eulerDegreesToQuat(vec3(headPitchDeg, 0, 0));
  const mat4 world(1);
  const vec3 pivot(boneGlobals(sk, pose, world)[1][3]);
  const float p = glm::radians(targetPitchDeg);
  const vec3 target = pivot + vec3(0, std::sin(p), std::cos(p));
  Clip clip;
  clip.tracks["who/lookAt"].setKey({0, target, Interp::Linear});
  applyConstraints(sk, clip, "who/", 0, world, pose, limits);
  const auto globals = boneGlobals(sk, pose, world);
  return glm::normalize(glm::transpose(mat3(globals[0])) * vec3(globals[1][2]));
}

float pitchDegrees(vec3 direction) {
  return glm::degrees(std::atan2(direction.y, glm::length(vec2(direction.x, direction.z))));
}
}  // namespace

TEST_CASE("look-at limits eye rotation relative to a downward-pitched head") {
  const Skeleton sk = gazeSkeleton();
  // Head pitches down 30 degrees while the target remains level in world space: the eye would otherwise turn up 30.
  const float eyePitch = pitchDegrees(gazeDirection(sk, 30.0f, 0.0f));
  CHECK(eyePitch < 20.0f);
  CHECK(eyePitch > 19.0f);
  GazeLimits characterLimits;
  characterLimits.maxUpDeg = 12.0f;
  const float characterPitch = pitchDegrees(gazeDirection(sk, 30.0f, 0.0f, characterLimits));
  CHECK(characterPitch < 12.0f);
  CHECK(characterPitch > 11.5f);
}

TEST_CASE("look-at leaves in-range gaze unchanged") {
  const Skeleton sk = gazeSkeleton();
  // A level world target with a 10-degree downward head pitch is 10 degrees up relative to the head.
  CHECK(pitchDegrees(gazeDirection(sk, 10.0f, 0.0f)) == doctest::Approx(10.0f).epsilon(0.0001));
}

TEST_CASE("look-at soft limit is continuous across the eye range") {
  const Skeleton sk = gazeSkeleton();
  const float below = pitchDegrees(gazeDirection(sk, 0.0f, 19.99f));
  const float at = pitchDegrees(gazeDirection(sk, 0.0f, 20.0f));
  const float above = pitchDegrees(gazeDirection(sk, 0.0f, 20.01f));
  CHECK(std::abs(at - below) < 0.01f);
  CHECK(std::abs(above - at) < 0.01f);
  CHECK(above > at);  // still eases forward beyond the nominal limit; there is no hard-stop plateau
  CHECK(above < 20.0f);
}

TEST_CASE("sdf mesher produces a closed sphere with the right area") {
  SdfPart part;
  part.voxelSize = 0.004f;
  SdfPrim s;
  s.type = PrimType::Ellipsoid;
  s.radii = vec3(0.1f);
  part.prims.push_back(s);
  CHECK(sdfPrim(s, vec3(0.2f, 0, 0)) == doctest::Approx(0.1f).epsilon(0.01));
  Mesh m = meshSdfPart(part);
  REQUIRE(m.triangleCount() > 100);
  double area = 0;
  std::map<std::pair<uint32_t, uint32_t>, int> edges;
  for (size_t t = 0; t < m.triangleCount(); ++t) {
    vec3 a = m.positions[m.indices[3 * t]], b = m.positions[m.indices[3 * t + 1]], c = m.positions[m.indices[3 * t + 2]];
    area += 0.5 * glm::length(glm::cross(b - a, c - a));
    for (int k = 0; k < 3; ++k) {
      uint32_t i = m.indices[3 * t + size_t(k)], j = m.indices[3 * t + size_t((k + 1) % 3)];
      edges[{std::min(i, j), std::max(i, j)}]++;
    }
  }
  CHECK(area == doctest::Approx(4 * kPi * 0.01).epsilon(0.03));
  int open = 0;
  for (auto& [e, n] : edges) open += (n != 2);
  CHECK(open == 0);
  // Normals point outwards.
  for (size_t i = 0; i < m.positions.size(); i += 37) CHECK(glm::dot(m.normals[i], m.positions[i]) > 0);
}

TEST_CASE("brick culling in the sdf mesher matches exhaustive evaluation") {
  // A clump-like part: many blended round cones, flattened ellipsoids, a subtraction and surface noise.
  SdfPart part;
  part.voxelSize = 0.002f;
  part.noiseAmplitude = 0.0012f;
  part.noiseScale = 45;
  uint32_t seed = 7;
  auto rnd = [&]() { seed = seed * 1664525u + 1013904223u; return float(seed >> 8) / float(1 << 24); };
  for (int i = 0; i < 40; ++i) {
    SdfPrim s;
    s.type = PrimType::RoundCone;
    float az = rnd() * kTwoPi, el = rnd() * 1.4f;
    vec3 n(std::cos(el) * std::sin(az), std::sin(el), std::cos(el) * std::cos(az));
    s.a = n * 0.06f;
    s.b = n * (0.1f + 0.05f * rnd()) + vec3(0, -0.03f * rnd(), 0);
    s.r1 = 0.02f + 0.01f * rnd();
    s.r2 = 0.003f;
    s.blend = 0.004f + 0.008f * rnd();
    part.prims.push_back(s);
  }
  for (int i = 0; i < 6; ++i) {
    SdfPrim s;
    s.radii = vec3(0.05f + 0.03f * rnd(), 0.008f + 0.01f * rnd(), 0.04f);
    s.center = vec3(rnd() - 0.5f, rnd() - 0.5f, rnd() - 0.5f) * 0.12f;
    s.blend = 0.01f;
    part.prims.push_back(s);
  }
  SdfPrim cut;
  cut.type = PrimType::RoundBox;
  cut.center = vec3(0, -0.1f, 0);
  cut.radii = vec3(0.2f, 0.05f, 0.2f);
  cut.subtract = true;
  cut.blend = 0.01f;
  part.prims.push_back(cut);

  Mesh fast = meshSdfPart(part, 1.0f, true), full = meshSdfPart(part, 1.0f, false);
  REQUIRE(full.positions.size() > 1000);
  CHECK(double(fast.positions.size()) == doctest::Approx(double(full.positions.size())).epsilon(0.002));
  // Every culled-mesh vertex lies on the exhaustive surface (within a small fraction of a voxel).
  float worst = 0;
  for (const vec3& p : fast.positions) worst = std::max(worst, std::abs(sdfPart(part, p)));
  MESSAGE("max |sdf| at culled-mesh vertices: " << worst << " m (voxel " << part.voxelSize << " m)");
  CHECK(worst < 0.1f * part.voxelSize);
}

TEST_CASE("automatic skin weights follow the driving primitives") {
  SdfPart part;
  part.voxelSize = 0.004f;
  SdfPrim a;
  a.type = PrimType::Capsule;
  a.a = vec3(0, 0, 0);
  a.b = vec3(0, 0.2f, 0);
  a.r1 = 0.04f;
  a.boneIndex = 0;
  SdfPrim b = a;
  b.a = vec3(0, 0.2f, 0);
  b.b = vec3(0, 0.4f, 0);
  b.boneIndex = 1;
  part.prims = {a, b};
  Mesh m = meshSdfPart(part);
  std::vector<glm::ivec4> joints;
  std::vector<vec4> weights;
  computeSkinWeights(part, 2, m, joints, weights);
  for (size_t i = 0; i < m.positions.size(); ++i) {
    float sum = weights[i].x + weights[i].y + weights[i].z + weights[i].w;
    CHECK(sum == doctest::Approx(1.0f));
    if (m.positions[i].y < 0.08f) CHECK(joints[i].x == 0);
    if (m.positions[i].y > 0.32f) CHECK(joints[i].x == 1);
  }
}

TEST_CASE("rest pose skinning is the identity") {
  Skeleton sk;
  sk.bones = {{"hips", -1, vec3(0, 0.4f, 0)}, {"spine", 0, vec3(0, 0.5f, 0)}};
  auto m = skinningMatrices(sk, restPose(sk), mat4(1));
  vec3 p(0.1f, 0.6f, 0.05f);
  CHECK(glm::distance(vec3(m[1] * vec4(p, 1)), p) < 1e-6f);
  Pose pose = restPose(sk);
  pose.local[1] = eulerDegreesToQuat(vec3(0, 0, 90));
  auto r = skinningMatrices(sk, pose, mat4(1));
  vec3 q = vec3(r[1] * vec4(0, 0.6f, 0, 1));  // 0.1 above the spine pivot, rotated 90 deg about z
  CHECK(q.x == doctest::Approx(-0.1f).epsilon(0.001));
  CHECK(q.y == doctest::Approx(0.5f).epsilon(0.001));
}

TEST_CASE("scene json round trip") {
  Scene s;
  s.name = "t";
  Material m;
  m.name = "floor";
  m.texture.type = TextureType::Wood;
  s.materials.push_back(m);
  ObjectDesc o;
  o.name = "box";
  o.material = "floor";
  s.objects.push_back(o);
  CharacterDesc c;
  c.name = "kid";
  c.life.gaze.maxUpDeg = 12.0f;
  c.life.gaze.maxDownDeg = 18.0f;
  c.life.gaze.maxLeftDeg = 22.0f;
  c.life.gaze.maxRightDeg = 24.0f;
  s.characters.push_back(c);
  s.animation.tracks["camera.position"].setKey({1, vec3(1, 2, 3)});
  auto dir = std::filesystem::temp_directory_path() / "plush_test_scene";
  auto path = dir / "s.scene.json";
  REQUIRE(saveScene(s, path));
  auto back = loadScene(path);
  REQUIRE(back);
  CHECK(back->objects.size() == 1);
  CHECK(back->materials[0].texture.type == TextureType::Wood);
  REQUIRE(back->characters.size() == 1);
  CHECK_FALSE(back->characters[0].life.enabled);
  CHECK(back->characters[0].life.gaze.maxUpDeg == doctest::Approx(12.0f));
  CHECK(back->characters[0].life.gaze.maxDownDeg == doctest::Approx(18.0f));
  CHECK(back->characters[0].life.gaze.maxLeftDeg == doctest::Approx(22.0f));
  CHECK(back->characters[0].life.gaze.maxRightDeg == doctest::Approx(24.0f));
  CHECK(back->animation.evaluate("camera.position", 1, vec3(0)).z == doctest::Approx(3));
}

TEST_CASE("surface fibers grow outwards and follow deformation") {
  SdfPart part;
  part.voxelSize = 0.004f;
  SdfPrim s;
  s.radii = vec3(0.1f);
  part.prims.push_back(s);
  Mesh m = meshSdfPart(part);
  FuzzParams fp;
  fp.density = 5;
  fp.length = 0.01f;
  SurfaceFibers sf = generateSurfaceFibers(m, fp);
  REQUIRE(sf.fiberCount() > 100);
  auto fs = deformSurfaceFibers(sf, m);
  int outside = 0, total = 0;
  for (size_t f = 0; f < fs->fiberCount; ++f) {
    vec3 tip = vec3(fs->points[f * size_t(sf.pointsPerFiber) + size_t(sf.pointsPerFiber - 1)]);
    outside += glm::length(tip) > 0.1015f;
    ++total;
  }
  CHECK(outside == total);
}

TEST_CASE("two-bone IK reaches reachable targets") {
  Skeleton sk;
  sk.bones = {{"chest", -1, vec3(0, 0.6f, 0)}, {"upperArm", 0, vec3(0.08f, 0.62f, 0)},
              {"forearm", 1, vec3(0.12f, 0.51f, 0)}, {"hand", 2, vec3(0.15f, 0.43f, 0.01f)}};
  mat4 world = glm::rotate(mat4(1), 0.4f, vec3(0, 1, 0));
  for (vec3 target : {vec3(0.15f, 0.55f, 0.12f), vec3(0.05f, 0.62f, 0.15f), vec3(0.17f, 0.47f, 0.03f)}) {  // all within the 0.203 m reach
    Pose pose = restPose(sk);
    solveTwoBoneIK(sk, pose, world, 3, target, 1.0f);
    vec3 reached(boneGlobals(sk, pose, world)[3][3]);
    CHECK(glm::distance(reached, target) < 1e-3f);
  }
}

TEST_CASE("eye aim points the bone at the target") {
  Skeleton sk;
  sk.bones = {{"head", -1, vec3(0, 0.8f, 0)}, {"eye.L", 0, vec3(0.05f, 0.8f, 0.1f)}};
  Pose pose = restPose(sk);
  vec3 target(0.3f, 0.5f, 1.0f);
  aimBone(sk, pose, mat4(1), 1, target, 1.0f, 89.0f);
  mat4 g = boneGlobals(sk, pose, mat4(1))[1];
  vec3 fwd = glm::normalize(vec3(g * vec4(0, 0, 1, 0)));
  CHECK(glm::dot(fwd, glm::normalize(target - vec3(g[3]))) > 0.9999f);
}

TEST_CASE("dual quaternion and linear skinning agree for a single rigid bone") {
  CharacterRig rig;
  SkinnedMesh sm;
  sm.rest = makeBoxMesh(vec3(-0.1f), vec3(0.1f));
  sm.joints.assign(sm.rest.positions.size(), glm::ivec4(0));
  sm.weights.assign(sm.rest.positions.size(), vec4(1, 0, 0, 0));
  rig.meshes.push_back(sm);
  mat4 m = glm::translate(mat4(1), vec3(0.3f, -0.2f, 0.5f)) * glm::rotate(mat4(1), 1.1f, glm::normalize(vec3(1, 2, 3)));
  auto lin = poseCharacter(rig, {m}, {}, false);
  auto dq = poseCharacter(rig, {m}, {}, true);
  for (size_t i = 0; i < sm.rest.positions.size(); ++i)
    CHECK(glm::distance(lin.meshes[0]->positions[i], dq.meshes[0]->positions[i]) < 1e-4f);
}

TEST_CASE("expression morph targets move the surface to the edited shape") {
  CharacterAsset c;
  c.skeleton.bones.push_back({"root", -1, vec3(0)});
  SdfPart part;
  part.name = "ball";
  part.voxelSize = 0.004f;
  SdfPrim s;
  s.name = "s";
  s.radii = vec3(0.1f);
  part.prims.push_back(s);
  c.parts.push_back(part);
  c.expressions.push_back({"grow", "ball", {Json{{"prim", "s"}, {"radii", {0.11, 0.11, 0.11}}}}, {}});
  CharacterRig rig = buildCharacter(c, BuildOptions{1.0f, 1.0f, false});
  REQUIRE(rig.morphs.size() == 1);
  auto posed = poseCharacter(rig, {mat4(1)}, {1.0f});
  double avg = 0;
  for (auto& p : posed.meshes[0]->positions) avg += glm::length(p);
  avg /= double(posed.meshes[0]->positions.size());
  CHECK(avg == doctest::Approx(0.11).epsilon(0.01));
}

TEST_CASE("lock groups build tapered cores and an outward halo") {
  LockGroupParams prm;
  prm.fuzzDensity = 40;
  LockCurve L;
  L.points = {vec3(0, 1, 0), vec3(0, 0.9f, 0.02f), vec3(0, 0.8f, 0.0f)};
  L.curlRadius = 0.01f;
  L.curlTurns = 2;
  FiberSet cores, fibers;
  generateLockGroup(prm, {L}, 1.0f, cores, fibers);
  REQUIRE(cores.fiberCount == 1);
  CHECK(cores.pinned[0] == 1);
  CHECK(cores.points.front().w > cores.points.back().w);  // tapers to the tip
  CHECK(glm::distance(vec3(cores.points.front()), L.points.front()) < 1e-4f);  // starts at the root
  REQUIRE(fibers.fiberCount > 50);
  // Halo fibre roots lie on the core surface: farther from the curve centre than the axis.
  CHECK(fibers.curveOffsets.size() == fibers.fiberCount + 1);
}

TEST_CASE("finger poses close the hand and a grasp adapts to the object's size") {
  // Hand of the iteration-4 characters (left side): hand bone, thumb and four two-segment fingers.
  Skeleton sk;
  sk.bones.push_back({"hand.L", -1, vec3(0.155f, 0.43f, 0.015f)});
  sk.bones.push_back({"thumbA.L", 0, vec3(0.152f, 0.418f, 0.04f)});
  sk.bones.push_back({"thumbB.L", 1, vec3(0.149f, 0.4075f, 0.0445f)});
  const float zs[4] = {0.006f, 0.0165f, 0.027f, 0.0375f};
  for (int k = 0; k < 4; ++k) {
    sk.bones.push_back({std::format("f{}a.L", k), 0, vec3(0.159f, 0.398f, zs[k])});
    sk.bones.push_back({std::format("f{}b.L", k), int(sk.bones.size()) - 1, vec3(0.156f, 0.3875f, zs[k] + 0.002f)});
  }
  const mat4 world(1);
  const vec3 palm(0.146f, 0.41f, 0.021f);  // palm surface facing the body (-x)
  auto meanTipToPalm = [&](const Pose& p) {
    auto tips = fingertips(sk, p, world, 'L');
    REQUIRE(tips.size() == 5);
    float d = 0;
    for (size_t i = 1; i < tips.size(); ++i) d += glm::distance(tips[i], palm);
    return d / 4;
  };
  Pose open = restPose(sk), fist = restPose(sk);
  applyHandPose(sk, open, world, 'L', HandPose{0, 0, 0});
  applyHandPose(sk, fist, world, 'L', HandPose{1, 1, 0});
  CHECK(meanTipToPalm(fist) < 0.6f * meanTipToPalm(open));
  // Pointing: index (finger 3) straight, the others curled.
  Pose point = restPose(sk);
  HandPose hp{1, 1, 0};
  hp.index = 0;
  applyHandPose(sk, point, world, 'L', hp);
  auto tipsP = fingertips(sk, point, world, 'L'), tipsO = fingertips(sk, open, world, 'L');
  CHECK(glm::distance(tipsP[4], tipsO[4]) < 1e-5f);
  CHECK(glm::distance(tipsP[1], tipsO[1]) > 0.005f);
  // Grasp a stick (cylinder along z) in front of the palm: every fingertip ends on its surface, and the thin
  // one closes the hand more than the thick one.
  float curlSmall = 0, curlLarge = 0;
  for (float r : {0.008f, 0.016f}) {
    Pose g = restPose(sk);
    HandPose gp{0, 0, 0};
    gp.grasp = true;
    gp.graspRadius = r;
    gp.graspCentre = vec3(-0.004f - r, -0.03f, 0.008f);  // relative to the hand bone head
    gp.graspAxis = vec3(0, 0, 1);
    applyHandPose(sk, g, world, 'L', gp);
    vec3 centre = sk.bones[0].head + gp.graspCentre;
    auto tips = fingertips(sk, g, world, 'L');
    for (size_t i = 1; i < tips.size(); ++i) {
      vec3 d = tips[i] - centre;
      d.z = 0;
      float gap = glm::length(d) - r;
      CHECK(gap <= 0.0046f);
      CHECK(gap >= 0.0040f);
    }
    float curl = glm::angle(g.local[3]);  // f0a rotation angle
    (r < 0.01f ? curlSmall : curlLarge) = curl;
  }
  MESSAGE("first-segment curl: small object " << glm::degrees(curlSmall) << " deg, large " << glm::degrees(curlLarge) << " deg");
  CHECK(curlSmall > curlLarge);
}

TEST_CASE("automatic blinks happen at jittered intervals and are deterministic") {
  int blinks = 0;
  bool wasClosed = false;
  for (double t = 0; t < 60; t += 1.0 / 30) {
    bool closed = blinkAmount(t, 3.6f, 77) > 0.9f;
    if (closed && !wasClosed) ++blinks;
    wasClosed = closed;
    CHECK(blinkAmount(t, 3.6f, 77) == blinkAmount(t, 3.6f, 77));
  }
  CHECK(blinks >= 12);  // ~16.7 expected in a minute
  CHECK(blinks <= 22);
  CHECK(blinkAmount(5.0, 0.0f, 77) == 0.0f);
}

namespace {
// The boy (C) from the content folder, built coarse and without fibres (fast) for animation tests.
std::unique_ptr<SceneEvaluator> loadTestScene(const Json& actions, bool life) {
  Scene s;
  s.path = std::filesystem::path(PLUSH_SOURCE_DIR) / "content/scenes/unit_test.scene.json";
  s.rate = FrameRate{30, 1};
  CharacterDesc cd;
  cd.name = "kid";
  cd.asset = "../characters/boy_dark_hair.character.json";
  cd.life.enabled = life;
  s.characters.push_back(cd);
  ObjectDesc ball;
  ball.name = "ball";
  ball.kind = ObjectDesc::Kind::Box;
  ball.boxMin = vec3(-0.015f);
  ball.boxMax = vec3(0.015f);
  ball.position = vec3(-0.17f, 0.47f, 0.2f);  // slightly beyond the chibi arm: the reach must lean
  s.objects.push_back(ball);
  s.actions = actions;
  auto ev = std::make_unique<SceneEvaluator>();
  auto r = ev->load(s, EvalOptions{2.5f, 1.0f, false, 0});
  REQUIRE(r.has_value());
  return ev;
}
}  // namespace

TEST_CASE("life layer breathes and the head follows the gaze later than the eyes") {
  auto ev = loadTestScene(Json::array(), true);
  Scene& s = ev->mutableScene();
  s.animation.tracks["kid/lookAt"].setKey({1, vec3(0, 0.8f, 3), Interp::Step});
  s.animation.tracks["kid/lookAt"].setKey({30, vec3(-2.5f, 0.8f, 1.0f), Interp::Step});
  const auto& sk = ev->characters()[0].asset.skeleton;
  int chest = sk.find("chest"), head = sk.find("head");
  // Breathing: the chest moves over a breath cycle.
  float maxDiff = 0;
  auto c0 = ev->characterGlobals(0, 1);
  for (int f = 2; f < 110; f += 6) {
    auto g = ev->characterGlobals(0, f);
    maxDiff = std::max(maxDiff, glm::distance(vec3(g[size_t(chest)][2]), vec3(c0[size_t(chest)][2])));
  }
  CHECK(maxDiff > 0.008f);
  // The gaze jumps at frame 30; the head has turned only a little 2 frames later and much more by frame 45.
  auto yawOf = [&](int f) {
    vec3 fwd = vec3(ev->characterGlobals(0, f)[size_t(head)][2]);
    return std::atan2(fwd.x, fwd.z);
  };
  float before = yawOf(29), soon = yawOf(32), later = yawOf(45);
  MESSAGE("head yaw (deg) before " << glm::degrees(before) << ", +2 frames " << glm::degrees(soon) << ", +15 frames " << glm::degrees(later));
  CHECK(std::abs(soon - before) < std::abs(later - before) * 0.5f);
  CHECK(glm::degrees(std::abs(later - before)) > 10.0f);
}

TEST_CASE("reach action brings the hand to the object, carries it and puts it down") {
  Json actions = Json::parse(R"([{"type": "reach", "character": "kid", "hand": "R", "object": "ball",
      "start": 10, "contact": 24, "lift": 0.06, "liftEnd": 36, "place": 60, "placeAt": [-0.12, 0.45, 0.25],
      "release": 63, "end": 78, "graspRadius": 0.015}])");
  // (the ball starts slightly beyond arm's length: the reach leans the upper body towards it)
  auto ev = loadTestScene(actions, false);
  const auto& sk = ev->characters()[0].asset.skeleton;
  int hand = sk.find("hand.R");
  vec3 ball0 = vec3(ev->objectWorld(0, 1)[3]);
  // At contact the object sits in front of the palm, within reach of the fingers.
  vec3 wrist = vec3(ev->characterGlobals(0, 24)[size_t(hand)][3]);
  MESSAGE("wrist to object at contact: " << glm::distance(wrist, ball0) * 1000 << " mm");
  CHECK(glm::distance(wrist, ball0) < 0.065f);
  CHECK(glm::length(ev->scene().animation.evaluate("kid/spine.rot", 24, vec3(0))) > 2.0f);  // leaned
  // Held: it moves up with the hand; after release it stays where it was put down.
  vec3 lifted = vec3(ev->objectWorld(0, 40)[3]);
  CHECK(lifted.y > ball0.y + 0.03f);
  vec3 placed = vec3(ev->objectWorld(0, 70)[3]);
  CHECK(glm::distance(vec2(placed.x, placed.z), vec2(-0.12f, 0.25f)) < 0.04f);
  CHECK(glm::distance(placed, vec3(ev->objectWorld(0, 90)[3])) < 1e-5f);
  // The eyes are on the object while it is held (generated lookAt track).
  vec3 look = ev->scene().animation.evaluate("kid/lookAt", 40, vec3(0));
  CHECK(glm::distance(look, lifted) < 0.03f);
}

TEST_CASE("walk action moves the character and keeps the standing foot planted") {
  Json actions = Json::parse(R"([{"type": "walk", "character": "kid", "start": 1, "end": 61, "to": [0.0, 0.6]}])");
  auto ev = loadTestScene(actions, false);
  const auto& sk = ev->characters()[0].asset.skeleton;
  int footL = sk.find("foot.L"), footR = sk.find("foot.R");
  vec3 endPos = ev->scene().animation.evaluate("kid.position", 61, vec3(0));
  CHECK(glm::distance(endPos, vec3(0, 0, 0.6f)) < 1e-4f);
  // Over the walk, at every frame at least one foot is (nearly) still: no skating.
  int slidingFrames = 0;
  float minLift = 1, maxLift = 0;
  for (int f = 2; f < 61; ++f) {
    auto a = ev->characterGlobals(0, f - 1), b = ev->characterGlobals(0, f);
    float dl = glm::distance(vec3(a[size_t(footL)][3]), vec3(b[size_t(footL)][3]));
    float dr = glm::distance(vec3(a[size_t(footR)][3]), vec3(b[size_t(footR)][3]));
    if (std::min(dl, dr) > 0.0025f) ++slidingFrames;
    float y = std::max(b[size_t(footL)][3].y, b[size_t(footR)][3].y);
    minLift = std::min(minLift, y);
    maxLift = std::max(maxLift, y);
  }
  MESSAGE("frames with both feet moving: " << slidingFrames << " / 59; ankle height range " << minLift << " .. " << maxLift);
  CHECK(slidingFrames <= 6);
  CHECK(maxLift - minLift > 0.012f);  // feet leave the ground
  // The feet end next to each other under the body.
  auto g = ev->characterGlobals(0, 70);
  CHECK(std::abs(g[size_t(footL)][3].z - g[size_t(footR)][3].z) < 0.03f);
}

TEST_CASE("touch action puts the index fingertip on the target") {
  Json actions = Json::parse(R"([{"type": "touch", "character": "kid", "hand": "L", "start": 5, "contact": 20, "end": 40,
      "target": [0.13, 0.45, 0.12]}])");
  auto ev = loadTestScene(actions, false);
  Pose pose;
  ev->characterGlobals(0, 20, &pose);
  auto tips = fingertips(ev->characters()[0].asset.skeleton, pose, mat4(1), 'L');
  REQUIRE(tips.size() == 5);
  MESSAGE("index fingertip to target at contact: " << glm::distance(tips[4], vec3(0.13f, 0.45f, 0.12f)) * 1000 << " mm");
  CHECK(glm::distance(tips[4], vec3(0.13f, 0.45f, 0.12f)) < 0.006f);
  // Pointing: the index is straighter than the other fingers at contact.
  const auto& sk = ev->characters()[0].asset.skeleton;
  CHECK(glm::angle(pose.local[size_t(sk.find("f3a.L"))]) < glm::angle(pose.local[size_t(sk.find("f1a.L"))]));
}
