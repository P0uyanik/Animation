#include "render/pathtracer.h"

#include <embree4/rtcore.h>

#include <atomic>
#include <limits>

#include "core/core.h"
#include "render/bsdf.h"

namespace plush {

namespace {
constexpr float kInf = std::numeric_limits<float>::infinity();

struct GeomRef {
  bool fiber = false;
  int index = 0;
};

float powerHeuristic(float a, float b) {
  float a2 = a * a, b2 = b * b;
  return a2 + b2 > 0 ? a2 / (a2 + b2) : 0.0f;
}

// Owen-scrambled Sobol (Burley 2020, "Practical Hash-based Owen Scrambling"): every
// dimension pair is an independently shuffled and scrambled 2D Sobol sequence, so
// samples stay well stratified per pixel and progressive rendering keeps working.
uint32_t reverseBits(uint32_t x) {
  x = ((x >> 1) & 0x55555555u) | ((x & 0x55555555u) << 1);
  x = ((x >> 2) & 0x33333333u) | ((x & 0x33333333u) << 2);
  x = ((x >> 4) & 0x0F0F0F0Fu) | ((x & 0x0F0F0F0Fu) << 4);
  x = ((x >> 8) & 0x00FF00FFu) | ((x & 0x00FF00FFu) << 8);
  return (x >> 16) | (x << 16);
}
uint32_t laineKarras(uint32_t x, uint32_t seed) {
  x += seed;
  x ^= x * 0x6c50b47cu;
  x ^= x * 0xb82f1e52u;
  x ^= x * 0xc7afe638u;
  x ^= x * 0x8d22f6e6u;
  return x;
}
uint32_t owenScramble(uint32_t x, uint32_t seed) { return reverseBits(laineKarras(reverseBits(x), seed)); }
uint32_t hash32(uint32_t a, uint32_t b) { return uint32_t(hash64((uint64_t(a) << 32) | b)); }

class Sampler {
 public:
  Sampler(uint32_t pixelSeed, uint32_t index) : seed_(pixelSeed), index_(index) {}
  vec2 next2() {
    uint32_t seed = hash32(seed_, dim_++);
    uint32_t i = owenScramble(index_, seed);
    uint32_t x = reverseBits(i), y = 0;
    for (uint32_t v = 1u << 31; i; i >>= 1, v ^= v >> 1)
      if (i & 1u) y ^= v;
    x = owenScramble(x, hash32(seed, 1));
    y = owenScramble(y, hash32(seed, 2));
    const float k = 1.0f / 4294967296.0f;
    return {std::min(float(x) * k, 0.99999994f), std::min(float(y) * k, 0.99999994f)};
  }
  float next() { return next2().x; }

 private:
  uint32_t seed_, index_, dim_ = 0;
};

void embreeError(void*, RTCError code, const char* str) { logError("Embree error {}: {}", int(code), str ? str : ""); }

struct CameraModel {
  vec3 pos, fwd, right, up;
  float sensorW, sensorH, focal, focusDist, aperture;
  int blades;
  float bladeRot;
  void setup(const Camera& c, int w, int h) {
    pos = c.position;
    fwd = glm::normalize(c.target - c.position);
    right = glm::normalize(glm::cross(fwd, c.up));
    up = glm::cross(right, fwd);
    sensorW = c.sensorWidthMm * 1e-3f;
    sensorH = sensorW * float(h) / float(w);
    focal = c.focalMm * 1e-3f;
    focusDist = c.focusDistance > 0 ? c.focusDistance : glm::dot(c.target - c.position, fwd);
    aperture = c.fStop > 0 ? 0.5f * focal / c.fStop : 0.0f;
    blades = c.blades;
    bladeRot = glm::radians(c.bladeRotationDeg);
  }
  void ray(float sx, float sy, float lensU0, vec2 lensU, vec3& o, vec3& d) const {
    vec3 dir = glm::normalize(fwd * focal + right * ((sx - 0.5f) * sensorW) + up * ((0.5f - sy) * sensorH));
    o = pos;
    d = dir;
    if (aperture > 0) {
      vec3 focusP = pos + dir * (focusDist / glm::dot(dir, fwd));
      vec2 l = sampleRegularPolygon(blades, bladeRot, lensU0, lensU) * aperture;
      o = pos + right * l.x + up * l.y;
      d = glm::normalize(focusP - o);
    }
  }
};
}  // namespace

struct PathTracer::Impl {
  RTCDevice device = nullptr;
  RTCScene scene = nullptr;
  RTCScene shadowScene = nullptr;  // only geometry that casts shadows (== scene when all do)
  std::shared_ptr<const FrameSnapshot> snap;
  std::vector<GeomRef> geoms;
  // Subsurface materials: per main-scene geometry id, a scene holding only that mesh, so a random walk below the
  // surface sees its own boundary and nothing else (eyes, teeth and other parts inside the head are ignored).
  std::vector<RTCScene> sssScenes;
  Material sssExit;  // Lambertian lobe where a subsurface walk leaves the surface
  std::vector<vec3> accColor, accAlbedo, accNormal;
  std::vector<float> accLumSq;
  std::vector<int> accCount;
  std::vector<uint8_t> tileActive;
  int width = 0, height = 0, samples = 0;
  static constexpr int kTile = 16;

  // Marks tiles whose estimated relative error is below the threshold as converged.
  int updateAdaptive(float threshold) {
    int tx = (width + kTile - 1) / kTile, ty = (height + kTile - 1) / kTile, active = 0;
    for (int t = 0; t < tx * ty; ++t) {
      if (!tileActive[size_t(t)]) continue;
      int x0 = (t % tx) * kTile, y0 = (t / tx) * kTile;
      // Mean relative standard error over the tile (the denoiser removes isolated outliers).
      float sum = 0;
      int count = 0;
      for (int y = y0; y < std::min(y0 + kTile, height); ++y)
        for (int x = x0; x < std::min(x0 + kTile, width); ++x) {
          size_t p = size_t(y) * size_t(width) + size_t(x);
          float n = float(std::max(1, accCount[p]));
          float mean = luminance(accColor[p]) / n;
          float var = std::max(0.0f, accLumSq[p] / n - mean * mean);
          sum += std::sqrt(var / n) / (mean + 0.05f);
          ++count;
        }
      if (sum / float(std::max(1, count)) < threshold) tileActive[size_t(t)] = 0;
      else ++active;
    }
    return active;
  }
  CameraModel cam;

  Impl() {
    sssExit.name = "subsurface exit";
    sssExit.type = MaterialType::Plush;
    sssExit.baseColor = vec3(1);
    sssExit.sheen = 0;
    device = rtcNewDevice(nullptr);
    if (!device) logError("Embree device creation failed");
    rtcSetDeviceErrorFunction(device, embreeError, nullptr);
  }
  void releaseSss() {
    for (RTCScene s : sssScenes)
      if (s) rtcReleaseScene(s);
    sssScenes.clear();
  }
  ~Impl() {
    releaseSss();
    if (shadowScene && shadowScene != scene) rtcReleaseScene(shadowScene);
    if (scene) rtcReleaseScene(scene);
    if (device) rtcReleaseDevice(device);
  }

  void build(std::shared_ptr<const FrameSnapshot> s) {
    Stopwatch sw;
    releaseSss();
    if (shadowScene && shadowScene != scene) rtcReleaseScene(shadowScene);
    if (scene) rtcReleaseScene(scene);
    shadowScene = nullptr;
    snap = std::move(s);
    geoms.clear();
    scene = rtcNewScene(device);
    rtcSetSceneBuildQuality(scene, RTC_BUILD_QUALITY_MEDIUM);
    std::vector<RTCGeometry> casters;
    bool anyNonCaster = false;
    size_t tris = 0, segs = 0;
    for (size_t i = 0; i < snap->meshes.size(); ++i) {
      const Mesh& m = *snap->meshes[i].mesh;
      if (m.indices.empty()) continue;
      RTCGeometry g = rtcNewGeometry(device, RTC_GEOMETRY_TYPE_TRIANGLE);
      auto* vb = static_cast<float*>(rtcSetNewGeometryBuffer(g, RTC_BUFFER_TYPE_VERTEX, 0, RTC_FORMAT_FLOAT3, 3 * sizeof(float), m.positions.size()));
      for (size_t v = 0; v < m.positions.size(); ++v) {
        vb[3 * v] = m.positions[v].x;
        vb[3 * v + 1] = m.positions[v].y;
        vb[3 * v + 2] = m.positions[v].z;
      }
      auto* ib = static_cast<uint32_t*>(rtcSetNewGeometryBuffer(g, RTC_BUFFER_TYPE_INDEX, 0, RTC_FORMAT_UINT3, 3 * sizeof(uint32_t), m.triangleCount()));
      std::copy(m.indices.begin(), m.indices.end(), ib);
      rtcCommitGeometry(g);
      unsigned id = rtcAttachGeometry(scene, g);
      if (snap->materials[size_t(snap->meshes[i].material)].subsurface > 0) {
        RTCScene ss = rtcNewScene(device);
        rtcAttachGeometry(ss, g);
        rtcCommitScene(ss);
        if (sssScenes.size() <= id) sssScenes.resize(id + 1, nullptr);
        sssScenes[id] = ss;
      }
      if (snap->materials[size_t(snap->meshes[i].material)].castsShadow) {
        rtcRetainGeometry(g);
        casters.push_back(g);
      } else {
        anyNonCaster = true;
      }
      rtcReleaseGeometry(g);
      if (geoms.size() <= id) geoms.resize(id + 1);
      geoms[id] = {false, int(i)};
      tris += m.triangleCount();
    }
    for (size_t i = 0; i < snap->fibers.size(); ++i) {
      const FiberSet& f = *snap->fibers[i].fibers;
      if (f.segmentStarts.empty()) continue;
      RTCGeometry g = rtcNewGeometry(device, RTC_GEOMETRY_TYPE_ROUND_LINEAR_CURVE);
      auto* vb = static_cast<vec4*>(rtcSetNewGeometryBuffer(g, RTC_BUFFER_TYPE_VERTEX, 0, RTC_FORMAT_FLOAT4, sizeof(vec4), f.points.size()));
      std::copy(f.points.begin(), f.points.end(), vb);
      auto* ib = static_cast<uint32_t*>(rtcSetNewGeometryBuffer(g, RTC_BUFFER_TYPE_INDEX, 0, RTC_FORMAT_UINT, sizeof(uint32_t), f.segmentStarts.size()));
      std::copy(f.segmentStarts.begin(), f.segmentStarts.end(), ib);
      rtcCommitGeometry(g);
      unsigned id = rtcAttachGeometry(scene, g);
      rtcRetainGeometry(g);
      casters.push_back(g);
      rtcReleaseGeometry(g);
      if (geoms.size() <= id) geoms.resize(id + 1);
      geoms[id] = {true, int(i)};
      segs += f.segmentStarts.size();
    }
    rtcCommitScene(scene);
    if (anyNonCaster) {
      shadowScene = rtcNewScene(device);
      rtcSetSceneBuildQuality(shadowScene, RTC_BUILD_QUALITY_MEDIUM);
      for (RTCGeometry g : casters) rtcAttachGeometry(shadowScene, g);
      rtcCommitScene(shadowScene);
    } else {
      shadowScene = scene;
    }
    for (RTCGeometry g : casters) rtcReleaseGeometry(g);
    samples = 0;
    logInfo("scene built in {:.2f}s: {} triangles, {} fiber segments", sw.seconds(), tris, segs);
  }

  static void setupRay(RTCRayHit& rh, vec3 o, vec3 d, float tnear, float tfar) {
    rh.ray.org_x = o.x; rh.ray.org_y = o.y; rh.ray.org_z = o.z;
    rh.ray.dir_x = d.x; rh.ray.dir_y = d.y; rh.ray.dir_z = d.z;
    rh.ray.tnear = tnear;
    rh.ray.tfar = tfar;
    rh.ray.time = 0;
    rh.ray.mask = 0xFFFFFFFFu;
    rh.ray.id = 0;
    rh.ray.flags = 0;
    rh.hit.geomID = RTC_INVALID_GEOMETRY_ID;
    rh.hit.instID[0] = RTC_INVALID_GEOMETRY_ID;
  }

  bool hasSubsurface(unsigned geomID) const { return geomID < sssScenes.size() && sssScenes[geomID]; }

  // Random walk below a subsurface surface (Chiang et al. 2016 albedo inversion, chromatic free-flight sampling
  // with balance-heuristic weights over the three channels, isotropic phase function). On success returns the
  // boundary hit where the light leaves (geomID mapped back to the main scene) and the walk's last ray.
  bool subsurfaceWalk(const ShadingPoint& sp, unsigned geomID, Sampler& rng, vec3& beta, RTCRayHit& exitHit,
                      vec3& exitOrigin, vec3& exitDir) const {
    RTCScene ss = sssScenes[geomID];
    const Material& m = *sp.material;
    const vec3 sigmaT = 1.0f / m.subsurfaceRadius;
    vec3 alpha;
    for (int c = 0; c < 3; ++c) {
      float a = std::clamp(sp.base[c], 0.001f, 0.999f);
      float t = 4.09712f + 4.20863f * a - std::sqrt(9.59217f + 41.6808f * a + 17.7126f * a * a);
      alpha[c] = 1 - t * t;
    }
    const vec3 sigmaS = alpha * sigmaT;
    vec3 d = Frame::fromNormal(-sp.ng).toWorld(sampleCosineHemisphere(rng.next2()));
    vec3 p = sp.p - sp.ng * 2e-5f;
    vec3 w(1);
    for (int step = 0; step < 256; ++step) {
      // Channel chosen in proportion to its current throughput: the mixture pdf then bounds every channel's
      // weight by the total, which keeps long walks free of fireflies.
      float wsum = w.x + w.y + w.z;
      if (!(wsum > 0)) return false;
      vec3 pc = w / wsum;
      float uc = rng.next();
      int c = uc < pc.x ? 0 : (uc < pc.x + pc.y ? 1 : 2);
      float t = -std::log(std::max(1e-7f, 1 - rng.next())) / sigmaT[c];
      RTCRayHit rh;
      setupRay(rh, p, d, 0, t);
      rtcIntersect1(ss, &rh);
      if (rh.hit.geomID != RTC_INVALID_GEOMETRY_ID) {
        vec3 tr = glm::exp(-sigmaT * rh.ray.tfar);
        w *= tr / glm::dot(pc, tr);
        rh.hit.geomID = geomID;
        exitHit = rh;
        exitOrigin = p;
        exitDir = d;
        beta *= w;
        return std::isfinite(beta.x + beta.y + beta.z);
      }
      p += d * t;
      vec3 tr = glm::exp(-sigmaT * t);
      w *= sigmaS * tr / glm::dot(pc, sigmaT * tr);
      if (step >= 8) {
        float q = std::min(0.99f, maxComponent(w));
        if (rng.next() >= q) return false;
        w /= q;
      }
      d = sampleUniformSphere(rng.next2());
    }
    return false;
  }

  bool intersect(vec3 o, vec3 d, float tnear, RTCRayHit& rh) const {
    rh.ray.org_x = o.x; rh.ray.org_y = o.y; rh.ray.org_z = o.z;
    rh.ray.dir_x = d.x; rh.ray.dir_y = d.y; rh.ray.dir_z = d.z;
    rh.ray.tnear = tnear;
    rh.ray.tfar = kInf;
    rh.ray.time = 0;
    rh.ray.mask = 0xFFFFFFFFu;
    rh.ray.id = 0;
    rh.ray.flags = 0;
    rh.hit.geomID = RTC_INVALID_GEOMETRY_ID;
    rh.hit.instID[0] = RTC_INVALID_GEOMETRY_ID;
    rtcIntersect1(scene, &rh);
    return rh.hit.geomID != RTC_INVALID_GEOMETRY_ID;
  }
  bool occluded(vec3 o, vec3 d, float tnear, float tfar) const {
    RTCRay r;
    r.org_x = o.x; r.org_y = o.y; r.org_z = o.z;
    r.dir_x = d.x; r.dir_y = d.y; r.dir_z = d.z;
    r.tnear = tnear;
    r.tfar = tfar;
    r.time = 0;
    r.mask = 0xFFFFFFFFu;
    r.id = 0;
    r.flags = 0;
    rtcOccluded1(shadowScene, &r);
    return r.tfar < 0;
  }

  ShadingPoint shade(const RTCRayHit& rh, vec3 o, vec3 d) const {
    ShadingPoint sp;
    const GeomRef& ref = geoms[rh.hit.geomID];
    float t = rh.ray.tfar;
    if (ref.fiber) {
      const SnapshotFibers& sf = snap->fibers[size_t(ref.index)];
      const FiberSet& f = *sf.fibers;
      uint32_t start = f.segmentStarts[rh.hit.primID];
      vec4 p0 = f.points[start], p1 = f.points[start + 1];
      sp.fiber = true;
      sp.p = o + d * t;
      vec3 tg = vec3(p1) - vec3(p0);
      float lt = glm::length(tg);
      sp.tangent = lt > 0 ? tg / lt : vec3(0, 1, 0);
      vec3 ng(rh.hit.Ng_x, rh.hit.Ng_y, rh.hit.Ng_z);
      float ln = glm::length(ng);
      sp.ng = ln > 0 ? ng / ln : -d;
      sp.ns = sp.ng;
      sp.fiberRadius = glm::mix(p0.w, p1.w, rh.hit.u);
      sp.pref = sp.p;
      sp.material = &snap->materials[size_t(sf.material)];
      sp.base = sp.material->baseColor;
      if (sp.material->type != MaterialType::Fiber) {
        // Thick curves with a surface material (e.g. felted yarn cores) shade as tubes.
        sp.fiber = false;
        sp.base = evalTexture(*sp.material, sp.p);
      }
    } else {
      const SnapshotMesh& sm = snap->meshes[size_t(ref.index)];
      const Mesh& m = *sm.mesh;
      uint32_t i0 = m.indices[3 * rh.hit.primID], i1 = m.indices[3 * rh.hit.primID + 1], i2 = m.indices[3 * rh.hit.primID + 2];
      float u = rh.hit.u, v = rh.hit.v, w = 1 - u - v;
      sp.p = w * m.positions[i0] + u * m.positions[i1] + v * m.positions[i2];
      vec3 ng = glm::cross(m.positions[i1] - m.positions[i0], m.positions[i2] - m.positions[i0]);
      float ln = glm::length(ng);
      sp.ng = ln > 0 ? ng / ln : -d;
      vec3 ns = w * m.normals[i0] + u * m.normals[i1] + v * m.normals[i2];
      float lns = glm::length(ns);
      sp.ns = lns > 0 ? ns / lns : sp.ng;
      sp.pref = m.pref.empty() ? sp.p : w * m.pref[i0] + u * m.pref[i1] + v * m.pref[i2];
      sp.material = &snap->materials[size_t(sm.material)];
      sp.base = evalTexture(*sp.material, sp.pref);
    }
    return sp;
  }

  // Spawns a ray leaving the shading point in direction wi.
  void spawn(const ShadingPoint& sp, vec3 wi, vec3& o, float& tnear) const {
    if (sp.fiber) {
      o = sp.p;
      tnear = 2.2f * sp.fiberRadius + 1e-6f;
    } else {
      float side = glm::dot(wi, sp.ng) >= 0 ? 1.0f : -1.0f;
      o = sp.p + sp.ng * (side * 2e-5f);
      tnear = 0;
    }
  }

  // Analytic test of one-sided rectangle lights. Returns light index or -1.
  int hitRectLight(vec3 o, vec3 d, float tmax, float& tHit) const {
    int best = -1;
    tHit = tmax;
    for (size_t i = 0; i < snap->lights.size(); ++i) {
      const Light& l = snap->lights[i];
      if (l.type != Light::Type::Rect) continue;
      vec3 n = glm::cross(l.edgeU, l.edgeV);
      float dn = glm::dot(d, n);
      if (dn >= 0) continue;  // back side does not emit
      float t = glm::dot(l.corner - o, n) / dn;
      if (t <= 1e-5f || t >= tHit) continue;
      vec3 q = o + d * t - l.corner;
      float a = glm::dot(q, l.edgeU) / glm::dot(l.edgeU, l.edgeU), b = glm::dot(q, l.edgeV) / glm::dot(l.edgeV, l.edgeV);
      if (a < 0 || a > 1 || b < 0 || b > 1) continue;
      tHit = t;
      best = int(i);
    }
    return best;
  }

  float skyPdf(const ShadingPoint& sp, vec3 wi) const {
    return sp.fiber ? 1.0f / (4 * kPi) : std::max(0.0f, glm::dot(wi, sp.ns)) * kInvPi;
  }

  vec3 directLight(const ShadingPoint& sp, vec3 wo, Sampler& rng, int depth, float clampLum) const {
    vec3 sum(0);
    for (const Light& l : snap->lights) {
      vec3 wi, Le;
      float lightPdf = 0, dist = kInf;
      bool useMis = true;
      if (l.type == Light::Type::Sun) {
        float halfAngle = glm::radians(std::max(0.05f, l.angleDeg * 0.5f));
        float cosMax = std::cos(halfAngle);
        Frame f = Frame::fromNormal(-glm::normalize(l.direction));
        wi = f.toWorld(sampleUniformCone(rng.next2(), cosMax));
        lightPdf = 1.0f / (kTwoPi * (1 - cosMax));
        Le = l.color * (l.intensity / (kPi * sqr(std::sin(halfAngle))));
        useMis = false;
      } else if (l.type == Light::Type::Rect) {
        vec2 u = rng.next2();
        vec3 q = l.corner + l.edgeU * u.x + l.edgeV * u.y;
        vec3 n = glm::cross(l.edgeU, l.edgeV);
        float area = glm::length(n);
        n /= area;
        wi = q - sp.p;
        dist = glm::length(wi);
        wi /= dist;
        float cosL = -glm::dot(wi, n);
        if (cosL <= 1e-4f) continue;
        lightPdf = dist * dist / (cosL * area);
        Le = l.color * l.intensity;
        dist *= 0.999f;
      } else {  // sky
        if (sp.fiber) {
          wi = sampleUniformSphere(rng.next2());
        } else {
          wi = Frame::fromNormal(sp.ns).toWorld(sampleCosineHemisphere(rng.next2()));
        }
        lightPdf = skyPdf(sp, wi);
        if (lightPdf <= 0) continue;
        Le = l.color * l.intensity;
      }
      float bsdfPdf;
      vec3 f = evalBsdf(sp, wo, wi, bsdfPdf);
      if (maxComponent(f) <= 0) continue;
      vec3 o;
      float tnear;
      spawn(sp, wi, o, tnear);
      if (occluded(o, wi, tnear, dist)) continue;
      float w = useMis ? powerHeuristic(lightPdf, bsdfPdf) : 1.0f;
      vec3 c = f * Le * (w / lightPdf);
      if (depth > 0) {
        float lum = luminance(c);
        if (lum > clampLum) c *= clampLum / lum;
      }
      sum += c;
    }
    return sum;
  }

  vec3 radiance(vec3 o, vec3 d, Sampler& rng, const RenderSettings& rs, vec3* albedo, vec3* normal) const {
    vec3 L(0), beta(1);
    float tnear = 0, prevPdf = 0;
    bool aovDone = false;  // denoiser guides come from the first non-glass surface
    ShadingPoint prev;
    for (int depth = 0; depth <= rs.maxDepth; ++depth) {
      RTCRayHit rh;
      bool hit = intersect(o, d, tnear, rh);
      float tHit = hit ? rh.ray.tfar : kInf;
      float tLight;
      int li = hitRectLight(o, d, tHit, tLight);
      if (li >= 0) {
        const Light& l = snap->lights[size_t(li)];
        vec3 Le = l.color * l.intensity;
        if (depth == 0 || prevPdf > 1e17f) {  // seen directly or through glass
          L += beta * Le;
          if (!aovDone && albedo) *albedo = glm::min(Le, vec3(1));
          if (!aovDone && normal) *normal = -d;
          aovDone = true;
        } else {
          vec3 n = glm::cross(l.edgeU, l.edgeV);
          float area = glm::length(n);
          float cosL = std::abs(glm::dot(d, n / area));
          float lightPdf = tLight * tLight / std::max(1e-6f, cosL * area);
          vec3 c = beta * Le * powerHeuristic(prevPdf, lightPdf);
          float lum = luminance(c);
          if (lum > rs.clamp) c *= rs.clamp / lum;
          L += c;
        }
        break;
      }
      if (!hit) {
        for (const Light& l : snap->lights) {
          if (l.type != Light::Type::Sky) continue;
          vec3 Le = l.color * l.intensity;
          float w = depth == 0 ? 1.0f : powerHeuristic(prevPdf, skyPdf(prev, d));
          L += beta * Le * w;
          if (!aovDone && albedo) *albedo = glm::min(Le, vec3(1));
        }
        break;
      }
      ShadingPoint sp = shade(rh, o, d);
      vec3 wo = -d;
      prepareShading(sp, wo);
      if (!aovDone && (sp.fiber || sp.material->type != MaterialType::Glass)) {
        // Fibres: modulate the guide by the across-fibre offset so each fibre is a
        // visible line in the albedo buffer and the denoiser preserves it.
        // Glass is skipped: the guides come from what is seen through it.
        aovDone = true;
        if (albedo) *albedo = sp.fiber ? sp.base * (0.45f + 0.55f * safeSqrt(1 - sp.h * sp.h)) : sp.base;
        if (normal) *normal = sp.fiber ? sp.ng : sp.ns;
      }
      // Subsurface materials: the BSDF keeps the specular lobes and (1 - subsurface) of the diffuse; the rest of
      // the diffuse light is carried by a random walk below the surface, chosen stochastically for the next event.
      const bool sss = !sp.fiber && !sp.backface && sp.material->subsurface > 0 && hasSubsurface(rh.hit.geomID);
      const vec3 fullBase = sp.base;
      if (sss) sp.base = fullBase * (1 - sp.material->subsurface);
      if (sp.fiber || sp.material->type != MaterialType::Glass) L += beta * directLight(sp, wo, rng, depth, rs.clamp);
      if (sss) {
        const float sw = sp.material->subsurface, q = 0.75f * sw;
        if (rng.next() < q) {
          const Material& m = *sp.material;
          float f0 = std::clamp(sqr((m.ior - 1) / (m.ior + 1)) * m.specular, 0.0f, 1.0f);
          float cosO = std::max(0.0f, glm::dot(wo, sp.ns));
          float F = f0 + (1 - f0) * std::pow(1 - cosO, 5.0f);
          beta *= sw * (1 - F) / q;
          ShadingPoint inside = sp;
          inside.base = fullBase;
          RTCRayHit eh;
          vec3 eo, ed;
          if (!subsurfaceWalk(inside, rh.hit.geomID, rng, beta, eh, eo, ed)) break;
          ShadingPoint ex = shade(eh, eo, ed);
          ex.material = &sssExit;
          ex.base = vec3(1);
          vec3 out = glm::dot(ex.ng, ed) >= 0 ? ex.ng : -ex.ng;
          prepareShading(ex, out);
          L += beta * directLight(ex, out, rng, depth, rs.clamp);
          BsdfSample bs;
          float u0 = rng.next();
          vec2 u1 = rng.next2(), u2 = rng.next2();
          if (!sampleBsdf(ex, out, u0, u1, u2, bs)) break;
          beta *= bs.weight;
          if (!std::isfinite(beta.x + beta.y + beta.z)) break;
          prevPdf = bs.pdf;
          prev = ex;
          spawn(ex, bs.wi, o, tnear);
          d = bs.wi;
          if (depth >= 3) {
            float rr = std::min(0.95f, maxComponent(beta));
            if (rng.next() >= rr) break;
            beta /= rr;
          }
          continue;
        }
        beta /= 1 - q;
      }
      BsdfSample bs;
      float u0 = rng.next();
      vec2 u1 = rng.next2(), u2 = rng.next2();
      if (!sampleBsdf(sp, wo, u0, u1, u2, bs)) break;
      beta *= bs.weight;
      if (!std::isfinite(beta.x + beta.y + beta.z)) break;
      prevPdf = bs.pdf;  // delta lobes carry a huge pdf, so light hits after them get full weight
      prev = sp;
      spawn(sp, bs.wi, o, tnear);
      d = bs.wi;
      if (depth >= 3) {
        float q = std::min(0.95f, maxComponent(beta));
        if (rng.next() >= q) break;
        beta /= q;
      }
    }
    return L;
  }
};

PathTracer::PathTracer() : impl_(std::make_unique<Impl>()) {}
PathTracer::~PathTracer() = default;

void PathTracer::setScene(std::shared_ptr<const FrameSnapshot> snapshot) { impl_->build(std::move(snapshot)); }

int PathTracer::accumulatedSamples() const { return impl_->samples; }

void PathTracer::accumulate(const RenderSettings& rs, int count, const std::function<bool()>& cancel) {
  Impl& im = *impl_;
  if (!im.snap || count <= 0) return;
  if (im.width != rs.width || im.height != rs.height || im.samples == 0) {
    im.width = rs.width;
    im.height = rs.height;
    size_t n = size_t(im.width) * size_t(im.height);
    im.accColor.assign(n, vec3(0));
    im.accAlbedo.assign(n, vec3(0));
    im.accNormal.assign(n, vec3(0));
    im.accLumSq.assign(n, 0.0f);
    im.accCount.assign(n, 0);
    im.tileActive.assign(size_t((im.width + Impl::kTile - 1) / Impl::kTile) * size_t((im.height + Impl::kTile - 1) / Impl::kTile), 1);
    im.samples = 0;
  }
  im.cam.setup(im.snap->camera, im.width, im.height);
  const int tile = Impl::kTile;
  int tx = (im.width + tile - 1) / tile, ty = (im.height + tile - 1) / tile;
  int first = im.samples;
  std::atomic<bool> stopped{false};
  parallelFor(size_t(tx) * size_t(ty), [&](size_t ti) {
    if (stopped.load(std::memory_order_relaxed) || !im.tileActive[ti]) return;
    if (cancel && cancel()) {
      stopped = true;
      return;
    }
    int x0 = int(ti % size_t(tx)) * tile, y0 = int(ti / size_t(tx)) * tile;
    for (int y = y0; y < std::min(y0 + tile, im.height); ++y)
      for (int x = x0; x < std::min(x0 + tile, im.width); ++x) {
        size_t pix = size_t(y) * size_t(im.width) + size_t(x);
        for (int s = first; s < first + count; ++s) {
          Sampler rng(uint32_t(hash64(uint64_t(rs.seed) * 0x9E3779B97F4A7C15ull ^ pix * 0x100000001B3ull)), uint32_t(s));
          vec2 jitter = rng.next2();
          vec3 o, d;
          float lu0 = rng.next();
          vec2 lu = rng.next2();
          im.cam.ray((float(x) + jitter.x) / float(im.width), (float(y) + jitter.y) / float(im.height), lu0, lu, o, d);
          vec3 albedo(0), normal(0);
          vec3 c = im.radiance(o, d, rng, rs, &albedo, &normal);
          if (!std::isfinite(c.x + c.y + c.z)) c = vec3(0);
          im.accColor[pix] += c;
          im.accAlbedo[pix] += albedo;
          im.accNormal[pix] += normal;
          float l = luminance(c);
          im.accLumSq[pix] += l * l;
        }
        im.accCount[pix] += count;
      }
  });
  if (!stopped) im.samples += count;
}

RenderOutput PathTracer::output() const {
  const Impl& im = *impl_;
  RenderOutput out;
  out.samples = im.samples;
  out.color.resize(im.width, im.height);
  out.albedo.resize(im.width, im.height);
  out.normal.resize(im.width, im.height);
  for (size_t i = 0; i < out.color.pixels.size(); ++i) {
    float inv = im.accCount[i] > 0 ? 1.0f / float(im.accCount[i]) : 0.0f;
    out.color.pixels[i] = im.accColor[i] * inv;
    out.albedo.pixels[i] = im.accAlbedo[i] * inv;
    vec3 n = im.accNormal[i];
    float l = glm::length(n);
    out.normal.pixels[i] = l > 0 ? n / l : vec3(0);
  }
  return out;
}

RenderOutput PathTracer::render(std::shared_ptr<const FrameSnapshot> snapshot, const RenderSettings& rs,
                                const std::function<void(float)>& progress) {
  Stopwatch sw;
  setScene(std::move(snapshot));
  int done = 0;
  const int chunk = std::max(1, std::min(8, rs.spp / 8));
  const int warmup = std::min(rs.spp, std::max(16, rs.spp / 4));  // every pixel gets at least this many
  while (done < rs.spp) {
    int n = std::min(chunk, rs.spp - done);
    accumulate(rs, n);
    done += n;
    if (rs.adaptiveThreshold > 0 && done >= warmup && impl_->updateAdaptive(rs.adaptiveThreshold) == 0) break;
    if (progress) progress(float(done) / float(rs.spp));
  }
  RenderOutput out = output();
  out.seconds = sw.seconds();
  return out;
}

}  // namespace plush
