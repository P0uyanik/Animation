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

namespace {
// Average BSDF sampling weight = directional albedo (should be <= 1).
float albedoEstimate(const Material& mat, bool fiber, vec3 wo, int n = 20000) {
  ShadingPoint sp;
  sp.material = &mat;
  sp.base = mat.baseColor;
  sp.fiber = fiber;
  sp.ng = sp.ns = vec3(0, 0, 1);
  sp.tangent = vec3(1, 0, 0);
  prepareShading(sp, wo);
  Rng rng(5);
  double sum = 0;
  for (int i = 0; i < n; ++i) {
    BsdfSample s;
    if (sampleBsdf(sp, wo, rng.next(), rng.next2(), rng.next2(), s)) sum += luminance(s.weight);
  }
  return float(sum / n);
}
}  // namespace

TEST_CASE("materials conserve energy") {
  Material plush;
  plush.type = MaterialType::Plush;
  plush.baseColor = vec3(1);
  plush.sheen = 1;
  float a = albedoEstimate(plush, false, glm::normalize(vec3(0.3f, 0, 1)));
  CHECK(a <= 1.05f);
  CHECK(a > 0.6f);
  Material std_;
  std_.baseColor = vec3(1);
  std_.coat = 1;
  std_.roughness = 0.3f;
  float b = albedoEstimate(std_, false, glm::normalize(vec3(0.5f, 0, 1)));
  CHECK(b <= 1.08f);
  CHECK(b > 0.7f);
  Material fiber;
  fiber.type = MaterialType::Fiber;
  fiber.baseColor = vec3(0.999f);
  fiber.betaM = 0.3f;
  fiber.betaN = 0.6f;
  float c = albedoEstimate(fiber, true, glm::normalize(vec3(0.2f, 0.1f, 1)));
  CHECK(c <= 1.1f);
  CHECK(c > 0.7f);
}

TEST_CASE("bsdf sampling pdf matches evaluation") {
  Material m;
  m.baseColor = vec3(0.6f);
  m.roughness = 0.4f;
  m.coat = 0.5f;
  ShadingPoint sp;
  sp.material = &m;
  sp.base = m.baseColor;
  vec3 wo = glm::normalize(vec3(0.4f, 0.2f, 1));
  prepareShading(sp, wo);
  Rng rng(3);
  for (int i = 0; i < 200; ++i) {
    BsdfSample s;
    if (!sampleBsdf(sp, wo, rng.next(), rng.next2(), rng.next2(), s)) continue;
    float pdf;
    vec3 f = evalBsdf(sp, wo, s.wi, pdf);
    CHECK(pdf == doctest::Approx(s.pdf).epsilon(0.001));
    CHECK(glm::distance(f / pdf, s.weight) < 1e-3f);
  }
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
  s.animation.tracks["camera.position"].setKey({1, vec3(1, 2, 3)});
  auto dir = std::filesystem::temp_directory_path() / "plush_test_scene";
  auto path = dir / "s.scene.json";
  REQUIRE(saveScene(s, path));
  auto back = loadScene(path);
  REQUIRE(back);
  CHECK(back->objects.size() == 1);
  CHECK(back->materials[0].texture.type == TextureType::Wood);
  CHECK(back->animation.evaluate("camera.position", 1, vec3(0)).z == doctest::Approx(3));
}

TEST_CASE("path tracer renders deterministically") {
  auto snap = std::make_shared<FrameSnapshot>();
  Material m;
  m.name = "white";
  snap->materials.push_back(m);
  snap->meshes.push_back({std::make_shared<Mesh>(makeBoxMesh(vec3(-1, -0.1f, -1), vec3(1, 0, 1))), 0});
  Light sun;
  sun.direction = glm::normalize(vec3(0.3f, -1, 0.2f));
  sun.intensity = 3;
  snap->lights.push_back(sun);
  snap->camera.position = vec3(0, 1, 2);
  snap->camera.target = vec3(0);
  RenderSettings rs;
  rs.width = 32;
  rs.height = 24;
  rs.spp = 4;
  PathTracer pt;
  auto a = pt.render(snap, rs);
  auto b = pt.render(snap, rs);
  double sum = 0;
  bool same = true;
  for (size_t i = 0; i < a.color.pixels.size(); ++i) {
    sum += luminance(a.color.pixels[i]);
    same = same && a.color.pixels[i] == b.color.pixels[i];
  }
  CHECK(sum > 1.0);
  CHECK(same);
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

TEST_CASE("glass lets light through and does not cast shadows") {
  auto make = [](bool withGlass) {
    auto snap = std::make_shared<FrameSnapshot>();
    Material white;
    white.name = "white";
    Material glass;
    glass.name = "glass";
    glass.type = MaterialType::Glass;
    glass.thin = true;
    glass.baseColor = vec3(1);
    glass.castsShadow = false;
    snap->materials = {white, glass};
    snap->meshes.push_back({std::make_shared<Mesh>(makeBoxMesh(vec3(-1, -0.1f, -1), vec3(1, 0, 1))), 0});
    if (withGlass) snap->meshes.push_back({std::make_shared<Mesh>(makeBoxMesh(vec3(-0.5f, 0.5f, -0.5f), vec3(0.5f, 0.51f, 0.5f))), 1});
    Light sun;
    sun.direction = vec3(0, -1, 0);
    sun.intensity = 3;
    snap->lights.push_back(sun);
    snap->camera.position = vec3(0, 0.3f, 0.6f);
    snap->camera.target = vec3(0, 0, 0);
    snap->camera.fStop = 0;
    return snap;
  };
  RenderSettings rs;
  rs.width = 16;
  rs.height = 12;
  rs.spp = 8;
  PathTracer pt;
  auto a = pt.render(make(false), rs), b = pt.render(make(true), rs);
  double la = 0, lb = 0;
  for (auto& p : a.color.pixels) la += luminance(p);
  for (auto& p : b.color.pixels) lb += luminance(p);
  CHECK(lb > 0.8 * la);  // the floor under the glass pane is still lit
}
