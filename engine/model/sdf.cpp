#include "model/sdf.h"

#include <algorithm>
#include <array>
#include <limits>

#include "core/core.h"

namespace plush {

namespace {
float signf(float x) { return float((x > 0) - (x < 0)); }

float sdEllipsoid(vec3 p, vec3 r) {
  float k1 = glm::length(p / (r * r));
  if (k1 < 1e-12f) return -std::min(r.x, std::min(r.y, r.z));
  float k0 = glm::length(p / r);
  return k0 * (k0 - 1.0f) / k1;
}
float sdCapsule(vec3 p, vec3 a, vec3 b, float r) {
  vec3 pa = p - a, ba = b - a;
  float h = std::clamp(glm::dot(pa, ba) / std::max(glm::dot(ba, ba), 1e-12f), 0.0f, 1.0f);
  return glm::length(pa - ba * h) - r;
}
// Inigo Quilez' exact round cone between two spheres.
float sdRoundCone(vec3 p, vec3 a, vec3 b, float r1, float r2) {
  vec3 ba = b - a;
  float l2 = glm::dot(ba, ba);
  if (l2 < 1e-12f) return glm::length(p - a) - std::max(r1, r2);
  float rr = r1 - r2, a2 = l2 - rr * rr, il2 = 1.0f / l2;
  vec3 pa = p - a;
  float y = glm::dot(pa, ba), z = y - l2;
  vec3 xv = pa * l2 - ba * y;
  float x2 = glm::dot(xv, xv), y2 = y * y * l2, z2 = z * z * l2;
  float k = signf(rr) * rr * rr * x2;
  if (signf(z) * a2 * z2 > k) return std::sqrt(x2 + z2) * il2 - r2;
  if (signf(y) * a2 * y2 < k) return std::sqrt(x2 + y2) * il2 - r1;
  return (std::sqrt(x2 * a2 * il2) + y * rr) * il2 - r1;
}
float sdRoundBox(vec3 p, vec3 halfSize, float r) {
  vec3 q = glm::abs(p) - halfSize + vec3(r);
  return glm::length(glm::max(q, vec3(0))) + std::min(std::max(q.x, std::max(q.y, q.z)), 0.0f) - r;
}
float smin(float a, float b, float k) {
  if (k <= 0) return std::min(a, b);
  float h = std::max(k - std::abs(a - b), 0.0f) / k;
  return std::min(a, b) - h * h * k * 0.25f;
}
float smax(float a, float b, float k) { return -smin(-a, -b, k); }

Aabb primBounds(const SdfPrim& s) {
  Aabb b;
  switch (s.type) {
    case PrimType::Ellipsoid: {
      float r = std::max(s.radii.x, std::max(s.radii.y, s.radii.z));
      b.expand(s.center - vec3(r));
      b.expand(s.center + vec3(r));
      break;
    }
    case PrimType::RoundBox: {
      float r = glm::length(s.radii);
      b.expand(s.center - vec3(r));
      b.expand(s.center + vec3(r));
      break;
    }
    case PrimType::Capsule:
    case PrimType::RoundCone: {
      float r = std::max(s.r1, s.type == PrimType::Capsule ? s.r1 : s.r2);
      b.expand(glm::min(s.a, s.b) - vec3(r));
      b.expand(glm::max(s.a, s.b) + vec3(r));
      break;
    }
  }
  return b;
}
}  // namespace

float sdfPrim(const SdfPrim& s, vec3 p) {
  switch (s.type) {
    case PrimType::Ellipsoid: return sdEllipsoid(glm::conjugate(s.rotation) * (p - s.center), s.radii);
    case PrimType::RoundBox: return sdRoundBox(glm::conjugate(s.rotation) * (p - s.center), s.radii, s.rounding);
    case PrimType::Capsule: return sdCapsule(p, s.a, s.b, s.r1);
    case PrimType::RoundCone: return sdRoundCone(p, s.a, s.b, s.r1, s.r2);
  }
  return 1e30f;
}

float sdfPart(const SdfPart& part, vec3 p) {
  float d = std::numeric_limits<float>::max();
  bool first = true;
  for (const auto& s : part.prims) {
    if (s.subtract) continue;
    float di = sdfPrim(s, p);
    d = first ? di : smin(d, di, s.blend);
    first = false;
  }
  for (const auto& s : part.prims)
    if (s.subtract) d = smax(d, -sdfPrim(s, p), s.blend);
  if (part.noiseAmplitude > 0 && d < 4 * part.noiseAmplitude + 0.01f) d += part.noiseAmplitude * fbm(p * part.noiseScale, 3);
  if (part.pattern != SurfacePattern::None && d < 4 * part.patternAmplitude + 0.01f) d -= part.patternAmplitude * patternHeight(part, p);
  return d;
}

float patternHeight(const SdfPart& part, vec3 p) {
  vec3 q = p - part.patternCenter;
  switch (part.pattern) {
    case SurfacePattern::None: return 0.0f;
    case SurfacePattern::Strands: {
      // Hair-like ridges running from the crown downwards, gently wavy and clumped.
      float r = glm::length(q);
      if (r < 1e-6f) return 0.0f;
      float phi = std::atan2(q.x, q.z), theta = std::acos(std::clamp(q.y / r, -1.0f, 1.0f));
      float u = phi / kTwoPi * part.patternScale + 0.35f * fbm(p * 14.0f, 2) + 0.5f * theta;
      float ridge = std::pow(std::abs(std::sin(kPi * u)), 0.55f);
      float clump = 0.65f + 0.35f * gradientNoise(vec3(std::floor(u) * 3.1f, theta * 5.0f, 0.5f));
      return ridge * clump;
    }
    case SurfacePattern::Knit: {
      // Stockinette: rounded columns of V-shaped stitches wrapped around the vertical axis.
      float phi = std::atan2(q.x, q.z);
      float u = phi * 0.1f * part.patternScale, v = q.y * part.patternScale * 1.25f;
      float fu = u - std::floor(u);
      float column = std::pow(std::sin(kPi * fu), 0.7f);
      float row = 0.5f + 0.5f * std::cos(kTwoPi * (v + std::abs(fu - 0.5f) * 0.9f));
      return column * (0.55f + 0.45f * row);
    }
    case SurfacePattern::Ribbed: {
      float phi = std::atan2(q.x, q.z);
      return std::pow(std::abs(std::sin(kPi * phi * 0.1f * part.patternScale)), 0.6f);
    }
  }
  return 0.0f;
}

vec3 sdfGradient(const SdfPart& part, vec3 p, float e) {
  return vec3(sdfPart(part, p + vec3(e, 0, 0)) - sdfPart(part, p - vec3(e, 0, 0)),
              sdfPart(part, p + vec3(0, e, 0)) - sdfPart(part, p - vec3(0, e, 0)),
              sdfPart(part, p + vec3(0, 0, e)) - sdfPart(part, p - vec3(0, 0, e))) /
         (2 * e);
}

Aabb partBounds(const SdfPart& part) {
  Aabb b;
  float maxBlend = 0;
  for (const auto& s : part.prims) {
    if (s.subtract) continue;
    b.expand(primBounds(s));
    maxBlend = std::max(maxBlend, s.blend);
  }
  if (b.valid()) {
    b.lo -= vec3(maxBlend + part.noiseAmplitude + part.patternAmplitude);
    b.hi += vec3(maxBlend + part.noiseAmplitude + part.patternAmplitude);
  }
  return b;
}

std::string mirrorName(const std::string& name) {
  auto swapSuffix = [&](const char* from, const char* to) -> std::string {
    size_t n = name.size();
    if (n >= 2 && name.compare(n - 2, 2, from) == 0) return name.substr(0, n - 2) + to;
    return {};
  };
  if (auto s = swapSuffix(".L", ".R"); !s.empty()) return s;
  if (auto s = swapSuffix(".R", ".L"); !s.empty()) return s;
  return name;
}

std::vector<SdfPrim> expandMirrors(const std::vector<SdfPrim>& prims) {
  std::vector<SdfPrim> out;
  for (const auto& p : prims) {
    SdfPrim a = p;
    a.mirrorX = false;
    out.push_back(a);
    if (!p.mirrorX) continue;
    SdfPrim m = a;
    auto flip = [](vec3 v) { return vec3(-v.x, v.y, v.z); };
    m.center = flip(m.center);
    m.a = flip(m.a);
    m.b = flip(m.b);
    m.rotation = quat(m.rotation.w, m.rotation.x, -m.rotation.y, -m.rotation.z);
    m.bone = mirrorName(m.bone);
    m.name = mirrorName(m.name) == m.name ? m.name + ".mirror" : mirrorName(m.name);
    out.push_back(m);
  }
  return out;
}

Mesh meshSdfPart(const SdfPart& part, float voxelScale) {
  Mesh mesh;
  Aabb box = partBounds(part);
  if (!box.valid()) return mesh;
  const float h = part.voxelSize * std::max(0.25f, voxelScale);
  box.lo -= vec3(2 * h);
  box.hi += vec3(2 * h);
  const vec3 ext = box.extent();
  const int nx = int(std::ceil(ext.x / h)) + 1, ny = int(std::ceil(ext.y / h)) + 1, nz = int(std::ceil(ext.z / h)) + 1;
  const size_t total = size_t(nx) * ny * nz;
  if (total > 400'000'000ull) {
    logError("SDF part '{}' grid too large ({} cells); increase voxelSize", part.name, total);
    return mesh;
  }
  auto idx = [&](int x, int y, int z) { return (size_t(z) * ny + y) * nx + x; };
  auto pos = [&](int x, int y, int z) { return box.lo + vec3(x, y, z) * h; };

  std::vector<float> field(total);
  parallelFor(size_t(nz), [&](size_t z) {
    for (int y = 0; y < ny; ++y)
      for (int x = 0; x < nx; ++x) field[idx(x, y, int(z))] = sdfPart(part, pos(x, y, int(z)));
  });

  // One vertex per cell that straddles the surface.
  std::vector<int32_t> cellVertex(total, -1);
  static const int corner[8][3] = {{0, 0, 0}, {1, 0, 0}, {0, 1, 0}, {1, 1, 0}, {0, 0, 1}, {1, 0, 1}, {0, 1, 1}, {1, 1, 1}};
  static const int edges[12][2] = {{0, 1}, {2, 3}, {4, 5}, {6, 7}, {0, 2}, {1, 3}, {4, 6}, {5, 7}, {0, 4}, {1, 5}, {2, 6}, {3, 7}};
  std::vector<std::array<int, 3>> cells;
  for (int z = 0; z < nz - 1; ++z)
    for (int y = 0; y < ny - 1; ++y)
      for (int x = 0; x < nx - 1; ++x) {
        int mask = 0;
        for (int c = 0; c < 8; ++c)
          if (field[idx(x + corner[c][0], y + corner[c][1], z + corner[c][2])] < 0) mask |= 1 << c;
        if (mask == 0 || mask == 255) continue;
        cellVertex[idx(x, y, z)] = int32_t(cells.size());
        cells.push_back({x, y, z});
      }

  mesh.positions.resize(cells.size());
  mesh.normals.resize(cells.size());
  const float eps = std::max(1e-5f, 0.1f * h);
  parallelFor(cells.size(), [&](size_t i) {
    auto [x, y, z] = cells[i];
    float v[8];
    for (int c = 0; c < 8; ++c) v[c] = field[idx(x + corner[c][0], y + corner[c][1], z + corner[c][2])];
    vec3 sum(0);
    int n = 0;
    for (auto& e : edges) {
      float a = v[e[0]], b = v[e[1]];
      if ((a < 0) == (b < 0)) continue;
      float t = a / (a - b);
      vec3 pa(corner[e[0]][0], corner[e[0]][1], corner[e[0]][2]), pb(corner[e[1]][0], corner[e[1]][1], corner[e[1]][2]);
      sum += pa + (pb - pa) * t;
      ++n;
    }
    vec3 cellLo = pos(x, y, z);
    vec3 p = cellLo + (sum / float(std::max(n, 1))) * h;
    // Project onto the true surface (Newton steps), staying near the cell.
    for (int it = 0; it < 3; ++it) {
      vec3 g = sdfGradient(part, p, eps);
      float g2 = glm::dot(g, g);
      if (g2 < 1e-12f) break;
      p -= g * (sdfPart(part, p) / g2);
      p = glm::clamp(p, cellLo - vec3(0.5f * h), cellLo + vec3(1.5f * h));
    }
    mesh.positions[i] = p;
    vec3 g = sdfGradient(part, p, eps);
    float len = glm::length(g);
    mesh.normals[i] = len > 0 ? g / len : vec3(0, 1, 0);
  });

  // Quads around every grid edge with a sign change.
  auto emitQuad = [&](int32_t a, int32_t b, int32_t c, int32_t d) {
    if (a < 0 || b < 0 || c < 0 || d < 0) return;
    const vec3 &pa = mesh.positions[size_t(a)], &pb = mesh.positions[size_t(b)];
    const vec3 &pc = mesh.positions[size_t(c)], &pd = mesh.positions[size_t(d)];
    vec3 nrm = mesh.normals[size_t(a)] + mesh.normals[size_t(b)] + mesh.normals[size_t(c)] + mesh.normals[size_t(d)];
    bool flip = glm::dot(glm::cross(pb - pa, pc - pa), nrm) < 0;
    if (flip) std::swap(b, d);
    if (glm::distance2(pa, pc) <= glm::distance2(pb, pd)) {
      mesh.indices.insert(mesh.indices.end(), {uint32_t(a), uint32_t(b), uint32_t(c), uint32_t(a), uint32_t(c), uint32_t(d)});
    } else {
      mesh.indices.insert(mesh.indices.end(), {uint32_t(a), uint32_t(b), uint32_t(d), uint32_t(b), uint32_t(c), uint32_t(d)});
    }
  };
  for (int z = 0; z < nz; ++z)
    for (int y = 0; y < ny; ++y)
      for (int x = 0; x < nx; ++x) {
        bool in0 = field[idx(x, y, z)] < 0;
        if (x + 1 < nx && y >= 1 && z >= 1 && y < ny - 1 && z < nz - 1 && in0 != (field[idx(x + 1, y, z)] < 0))
          emitQuad(cellVertex[idx(x, y - 1, z - 1)], cellVertex[idx(x, y, z - 1)], cellVertex[idx(x, y, z)], cellVertex[idx(x, y - 1, z)]);
        if (y + 1 < ny && x >= 1 && z >= 1 && x < nx - 1 && z < nz - 1 && in0 != (field[idx(x, y + 1, z)] < 0))
          emitQuad(cellVertex[idx(x - 1, y, z - 1)], cellVertex[idx(x, y, z - 1)], cellVertex[idx(x, y, z)], cellVertex[idx(x - 1, y, z)]);
        if (z + 1 < nz && x >= 1 && y >= 1 && x < nx - 1 && y < ny - 1 && in0 != (field[idx(x, y, z + 1)] < 0))
          emitQuad(cellVertex[idx(x - 1, y - 1, z)], cellVertex[idx(x, y - 1, z)], cellVertex[idx(x, y, z)], cellVertex[idx(x - 1, y, z)]);
      }
  mesh.pref = mesh.positions;
  return mesh;
}

}  // namespace plush
