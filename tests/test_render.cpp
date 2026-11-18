// Engine path tracer tests (built only with PLUSH_BUILD_RENDERER=ON). Moved verbatim from test_engine.cpp (T-085).
#include <doctest/doctest.h>

#include <memory>

#include "render/bsdf.h"
#include "render/image.h"
#include "render/pathtracer.h"
#include "scene/scene.h"

using namespace plush;

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

TEST_CASE("subsurface random walk returns about the base albedo under uniform light") {
  // A large sphere (radius >> mean free path) under a uniform white sky: a purely subsurface material should
  // reflect close to its base colour (that is what the albedo inversion is for), and a white one about 1.
  SdfPart part;
  part.voxelSize = 0.01f;
  SdfPrim s;
  s.radii = vec3(0.3f);
  part.prims.push_back(s);
  auto sphere = std::make_shared<Mesh>(meshSdfPart(part));
  for (float a : {0.5f, 0.95f}) {
    auto snap = std::make_shared<FrameSnapshot>();
    Material m;
    m.name = "sss";
    m.baseColor = vec3(a);
    m.specular = 0;
    m.subsurface = 1;
    m.subsurfaceRadius = vec3(0.01f);
    snap->materials.push_back(m);
    snap->meshes.push_back({sphere, 0});
    Light sky;
    sky.type = Light::Type::Sky;
    sky.intensity = 1;
    snap->lights.push_back(sky);
    snap->camera.position = vec3(0, 0, 2);
    snap->camera.target = vec3(0);
    snap->camera.focalMm = 200;
    snap->camera.fStop = 0;
    RenderSettings rs;
    rs.width = 16;
    rs.height = 16;
    rs.spp = 256;
    rs.denoise = false;
    rs.maxDepth = 64;
    rs.clamp = 1e6f;
    PathTracer pt;
    auto out = pt.render(snap, rs);
    double sum = 0;
    for (const vec3& c : out.color.pixels) sum += luminance(c);
    double mean = sum / double(out.color.pixels.size());
    MESSAGE("base " << a << " -> mean radiance " << mean);
    CHECK(mean == doctest::Approx(a).epsilon(0.12));
  }
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
