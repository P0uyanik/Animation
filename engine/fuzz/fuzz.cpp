#include "fuzz/fuzz.h"

#include <algorithm>

#include "core/core.h"

namespace plush {

namespace {
struct RootFrame {
  vec3 p, t, b, n;
};
RootFrame rootFrame(const Mesh& m, uint32_t tri, vec2 uv) {
  uint32_t i0 = m.indices[3 * tri], i1 = m.indices[3 * tri + 1], i2 = m.indices[3 * tri + 2];
  float w0 = 1 - uv.x - uv.y;
  RootFrame f;
  f.p = w0 * m.positions[i0] + uv.x * m.positions[i1] + uv.y * m.positions[i2];
  vec3 n = w0 * m.normals[i0] + uv.x * m.normals[i1] + uv.y * m.normals[i2];
  float ln = glm::length(n);
  f.n = ln > 0 ? n / ln : vec3(0, 1, 0);
  vec3 e = m.positions[i1] - m.positions[i0];
  e -= f.n * glm::dot(e, f.n);
  float le = glm::length(e);
  f.t = le > 1e-12f ? e / le : Frame::fromNormal(f.n).t;
  f.b = glm::cross(f.n, f.t);
  return f;
}
}  // namespace

SurfaceFibers generateSurfaceFibers(const Mesh& rest, const FuzzParams& prm, float densityScale) {
  SurfaceFibers out;
  size_t triCount = rest.triangleCount();
  if (triCount == 0 || prm.density <= 0) return out;
  std::vector<double> cdf(triCount);
  double total = 0;
  for (size_t t = 0; t < triCount; ++t) {
    const vec3& a = rest.positions[rest.indices[3 * t]];
    const vec3& b = rest.positions[rest.indices[3 * t + 1]];
    const vec3& c = rest.positions[rest.indices[3 * t + 2]];
    total += 0.5 * glm::length(glm::cross(b - a, c - a));
    cdf[t] = total;
  }
  size_t count = size_t(prm.density * densityScale * total * 1e4);
  int seg = std::max(1, prm.segments);
  out.pointsPerFiber = seg + 1;
  out.triangle.resize(count);
  out.bary.resize(count);
  out.local.resize(count * size_t(out.pointsPerFiber));

  parallelFor(count, [&](size_t i) {
    Rng rng(prm.seed * 7919ull + i, 3);
    double target = rng.next() * total;
    size_t tri = size_t(std::lower_bound(cdf.begin(), cdf.end(), target) - cdf.begin());
    tri = std::min(tri, triCount - 1);
    float su = std::sqrt(rng.next()), v = rng.next();
    vec2 uv(su * (1 - v), su * v);
    out.triangle[i] = uint32_t(tri);
    out.bary[i] = uv;
    RootFrame f = rootFrame(rest, uint32_t(tri), uv);

    float phi = rng.next() * kTwoPi;
    vec3 lean = std::cos(phi) * f.t + std::sin(phi) * f.b;
    if (prm.comb > 0) {
      vec3 away = f.p - prm.combOrigin;
      away -= f.n * glm::dot(away, f.n);
      if (glm::length2(away) > 1e-12f) lean = glm::normalize(glm::mix(lean, glm::normalize(away), prm.comb));
    }
    float theta = prm.tilt * (kPi * 0.5f) * (0.55f + 0.45f * rng.next());
    vec3 dir = f.n * std::cos(theta) + lean * std::sin(theta);
    vec3 side = glm::normalize(glm::cross(dir, lean) + vec3(1e-6f));
    float len = prm.length * (1 - prm.lengthJitter * rng.next());
    float phase = rng.next() * kTwoPi, freq = 1.0f + 2.0f * rng.next();
    for (int k = 0; k <= seg; ++k) {
      float s = float(k) / float(seg);
      vec3 p = -0.25f * len * f.n * (k == 0 ? 1.0f : 0.0f);  // embed the root slightly
      p += dir * (len * s) + lean * (prm.curl * len * s * s) + side * (prm.curl * 0.35f * len * s * std::sin(phase + freq * kPi * s));
      float r = prm.radius * (1.0f - 0.6f * s);
      out.local[i * size_t(out.pointsPerFiber) + size_t(k)] = vec4(glm::dot(p, f.t), glm::dot(p, f.b), glm::dot(p, f.n), r);
    }
  }, 1024);
  return out;
}

std::shared_ptr<FiberSet> deformSurfaceFibers(const SurfaceFibers& sf, const Mesh& mesh) {
  auto out = std::make_shared<FiberSet>();
  size_t n = sf.fiberCount();
  size_t ppf = size_t(sf.pointsPerFiber);
  out->fiberCount = n;
  out->points.resize(n * ppf);
  out->segmentStarts.resize(n * (ppf - 1));
  parallelFor(n, [&](size_t i) {
    RootFrame f = rootFrame(mesh, sf.triangle[i], sf.bary[i]);
    for (size_t k = 0; k < ppf; ++k) {
      vec4 l = sf.local[i * ppf + k];
      out->points[i * ppf + k] = vec4(f.p + f.t * l.x + f.b * l.y + f.n * l.z, l.w);
      if (k + 1 < ppf) out->segmentStarts[i * (ppf - 1) + k] = uint32_t(i * ppf + k);
    }
  }, 4096);
  return out;
}

FiberSet generateLocks(const LockParams& prm, float densityScale) {
  FiberSet out;
  const int seg = std::max(4, prm.segments);
  const int fibers = std::max(0, int(float(prm.fibersPerLock) * densityScale));
  Rng rng(prm.seed, 11);
  auto addCurve = [&](const std::vector<vec4>& pts) {
    uint32_t base = uint32_t(out.points.size());
    out.points.insert(out.points.end(), pts.begin(), pts.end());
    for (uint32_t k = 0; k + 1 < pts.size(); ++k) out.segmentStarts.push_back(base + k);
    out.fiberCount++;
  };
  for (int j = 0; j < prm.count; ++j) {
    float t = (float(j) + 0.5f + 0.6f * (rng.next() - 0.5f)) / float(prm.count);
    float az = glm::radians(glm::mix(prm.azimuthMinDeg, prm.azimuthMaxDeg, t));
    float el = glm::radians(prm.elevationDeg + 10.0f * (rng.next() - 0.5f));
    vec3 radial(std::sin(az), 0, -std::cos(az));      // outward in the xz plane
    vec3 tangential(std::cos(az), 0, std::sin(az));
    float rxz = glm::length(vec2(prm.headRadii.x * radial.x, prm.headRadii.z * radial.z));
    float len = glm::mix(prm.lengthMin, prm.lengthMax, rng.next()) * (1.0f - 0.25f * std::abs(std::sin(az)) * 0.0f);
    float phase = rng.next() * kTwoPi;
    float rootY = prm.headCenter.y + prm.headRadii.y * std::sin(el);
    float rootR = rxz * std::cos(el) * 0.97f;

    std::vector<vec3> guide(size_t(seg) + 1);
    for (int k = 0; k <= seg; ++k) {
      float s = float(k) / float(seg);
      float y = rootY - s * len;
      float dy = (y - prm.headCenter.y) / prm.headRadii.y;
      float headR = rxz * safeSqrt(1 - dy * dy) + 0.6f * prm.lockRadius;
      float bodyR = prm.bodyClearance + prm.sideClearance * std::abs(std::sin(az));
      float blendBody = smoothstep01((prm.headBottom + 0.04f - y) / 0.08f);
      float r = std::max(rootR * (1 - s * 4) , glm::mix(headR, std::max(headR, bodyR), blendBody));
      float w = prm.wave * std::sin(phase + kTwoPi * (s * len) / prm.waveLength) * std::min(1.0f, s * 5);
      float tipCurl = smoothstep01((s - 0.8f) / 0.2f);
      vec3 p = prm.headCenter + radial * (r + 0.4f * w + 0.03f * tipCurl) + tangential * w;
      p.y = y + 0.02f * tipCurl;
      guide[size_t(k)] = p;
    }
    // Core tube + twisted fibers around it.
    std::vector<vec4> core(guide.size());
    std::vector<vec3> fn(guide.size()), fb(guide.size());
    std::vector<float> lr(guide.size());
    for (size_t k = 0; k < guide.size(); ++k) {
      float s = float(k) / float(seg);
      vec3 tg = glm::normalize(guide[std::min(k + 1, guide.size() - 1)] - guide[k > 0 ? k - 1 : 0]);
      vec3 nn = radial - tg * glm::dot(radial, tg);
      nn = glm::length2(nn) > 1e-10f ? glm::normalize(nn) : Frame::fromNormal(tg).t;
      fn[k] = nn;
      fb[k] = glm::cross(tg, nn);
      lr[k] = prm.lockRadius * (0.8f + 0.35f * std::sin(kPi * std::min(1.0f, s * 1.15f))) * (1 - 0.85f * smoothstep01((s - 0.82f) / 0.18f));
      core[k] = vec4(guide[k], std::max(lr[k] * prm.coreRatio, 2e-4f));
    }
    addCurve(core);
    std::vector<vec4> pts(guide.size());
    for (int i = 0; i < fibers; ++i) {
      bool stray = rng.next() < 0.06f;
      float rr = std::sqrt(rng.next()) * (stray ? 1.35f : 1.0f);
      rr = std::max(rr, prm.coreRatio * 0.9f);  // keep fibers outside most of the core
      float th0 = rng.next() * kTwoPi;
      float fr = prm.fiberRadius * (0.7f + 0.6f * rng.next());
      float lenScale = 0.85f + 0.15f * rng.next();
      for (size_t k = 0; k < guide.size(); ++k) {
        float s = float(k) / float(seg) * lenScale;
        size_t kk = std::min(guide.size() - 1, size_t(s * float(seg)));
        float th = th0 + kTwoPi * prm.twist * s * len;
        vec3 frizz = (vec3(rng.next(), rng.next(), rng.next()) - 0.5f) * prm.frizz * (0.3f + 2.0f * s);
        vec3 p = guide[kk] + lr[kk] * rr * (std::cos(th) * fn[kk] + std::sin(th) * fb[kk]) + frizz;
        pts[k] = vec4(p, fr * (1.0f - 0.5f * s));
      }
      addCurve(pts);
    }
  }
  return out;
}

std::shared_ptr<FiberSet> transformFibers(const FiberSet& fibers, const mat4& m) {
  auto out = std::make_shared<FiberSet>();
  out->segmentStarts = fibers.segmentStarts;
  out->fiberCount = fibers.fiberCount;
  out->points.resize(fibers.points.size());
  float scale = std::cbrt(std::abs(glm::determinant(mat3(m))));
  parallelFor(fibers.points.size(), [&](size_t i) {
    vec4 p = fibers.points[i];
    out->points[i] = vec4(vec3(m * vec4(vec3(p), 1.0f)), p.w * scale);
  }, 8192);
  return out;
}

}  // namespace plush
