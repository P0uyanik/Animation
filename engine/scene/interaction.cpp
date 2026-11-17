// Hand-prop interaction actions (see interaction.h). Compiled into generated tracks and prop parent switches by
// SceneEvaluator::compileActions (actions.cpp); evaluated by the ordinary pose path (IK, hand pose, look) plus the
// orientation constraint below, which scene.cpp applies after IK.
#include "scene/interaction.h"

#include <algorithm>
#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <format>
#include <map>
#include <optional>
#include <set>
#include <unordered_map>

#include "scene/scene.h"

namespace plush {

// ------------------------------------------------------------------------------------------------ shared helpers
vec3 rotationVector(const quat& q0) {
  quat q = glm::normalize(q0);
  if (q.w < 0) q = -q;  // shortest arc, angle in [0, pi]
  const float s = std::sqrt(std::max(0.0f, 1.0f - q.w * q.w));
  const float angle = 2.0f * std::atan2(s, q.w);
  if (s < 1e-7f) return vec3(q.x, q.y, q.z) * 2.0f;
  return vec3(q.x, q.y, q.z) / s * angle;
}

quat fromRotationVector(vec3 v) {
  const float angle = glm::length(v);
  if (angle < 1e-8f) return quat(1, 0, 0, 0);
  return glm::angleAxis(angle, v / angle);
}

HandGrip handGrip(const Skeleton& sk, int handBone, char side) {
  HandGrip g;
  if (handBone < 0 || size_t(handBone) >= sk.bones.size()) return g;
  const vec3 head = sk.bones[size_t(handBone)].head;
  const std::string s = std::string(".") + side;
  vec3 sum(0);
  int n = 0;
  for (int k = 0; k < 4; ++k)
    if (int b = sk.find(std::format("f{}a{}", k, s)); b >= 0) sum += sk.bones[size_t(b)].head, ++n;
  if (n == 0)  // no finger roles: the hand's children stand in for the finger roots
    for (const Bone& b : sk.bones)
      if (b.parent == handBone) sum += b.head, ++n;
  const vec3 roots = n > 0 ? sum / float(n) : head;
  const HandFrame& f = side == 'L' ? sk.handL : sk.handR;
  vec3 d = glm::length(f.fingerDir) > 1e-6f ? glm::normalize(f.fingerDir)
           : glm::length(roots - head) > 1e-4f ? glm::normalize(roots - head)
                                                : vec3(0, -1, 0);
  vec3 nn = glm::length(f.palmNormal) > 1e-6f ? f.palmNormal : vec3(side == 'L' ? -1.0f : 1.0f, 0, 0);
  nn -= d * glm::dot(nn, d);
  nn = glm::length(nn) > 1e-6f ? glm::normalize(nn) : glm::normalize(glm::cross(d, vec3(0, 0, 1)));
  g.fingerDir = d;
  g.palmNormal = nn;
  g.palmLength = n > 0 ? std::max(0.02f, glm::dot(roots - head, d)) : 0.06f;
  // The contact point sits on the palm surface between the wrist and the finger roots.
  g.palm = d * (0.65f * g.palmLength) + nn * (0.22f * g.palmLength);
  return g;
}

void applyOrientConstraints(const Skeleton& sk, const Clip& clip, const std::string& prefix, double frame,
                            const mat4& world, Pose& pose) {
  for (size_t i = 0; i < sk.bones.size(); ++i) {
    const std::string name = prefix + "orient." + sk.bones[i].name;
    const Track* t = clip.find(name);
    if (!t || t->keys.empty()) continue;
    const float w = std::clamp(clip.evaluate(name + ".weight", frame, vec3(1)).x, 0.0f, 1.0f);
    if (w <= 0) continue;
    const int parent = sk.bones[i].parent;
    const mat4 parentGlobal = parent >= 0 ? boneGlobals(sk, pose, world)[size_t(parent)] : world;
    const mat3 pm(glm::normalize(vec3(parentGlobal[0])), glm::normalize(vec3(parentGlobal[1])),
                  glm::normalize(vec3(parentGlobal[2])));
    const quat local = glm::normalize(glm::inverse(glm::normalize(glm::quat_cast(pm))) * fromRotationVector(t->evaluate(frame)));
    pose.local[i] = w >= 1.0f ? local : glm::normalize(glm::slerp(pose.local[i], local, w));
  }
}

// ------------------------------------------------------------------------------------- arm-body clearance (T-030)
namespace {

enum class Region { Other, Torso, ArmL, ArmR, Leg, Head };
enum class ArmPart { None, Upper, Fore, Hand };

bool startsWith(const std::string& s, const char* p) { return s.rfind(p, 0) == 0; }
bool isFingerName(const std::string& n) {
  return n.size() >= 4 && ((n[0] == 'f' && n[1] >= '0' && n[1] <= '9') || startsWith(n, "thumb"));
}

// Region of a bone: the nearest role on its way to the root decides (helpers belong to their role's region).
Region regionOf(const Skeleton& sk, int b) {
  for (int k = b; k >= 0; k = sk.bones[size_t(k)].parent) {
    const std::string& n = sk.bones[size_t(k)].name;
    const char side = n.empty() ? ' ' : n.back();
    if (startsWith(n, "upperArm.") || startsWith(n, "forearm.") || startsWith(n, "hand.") || (isFingerName(n) && n.find('.') != std::string::npos))
      return side == 'L' ? Region::ArmL : Region::ArmR;
    if (startsWith(n, "thigh.") || startsWith(n, "shin.") || startsWith(n, "foot.") || startsWith(n, "toe")) return Region::Leg;
    if (n == "neck" || n == "head" || startsWith(n, "eye.")) return Region::Head;
    if (n == "hips" || n == "spine" || n == "chest") return Region::Torso;
  }
  return Region::Other;
}
ArmPart armPartOf(const Skeleton& sk, int b) {
  for (int k = b; k >= 0; k = sk.bones[size_t(k)].parent) {
    const std::string& n = sk.bones[size_t(k)].name;
    if (startsWith(n, "hand.") || isFingerName(n)) return ArmPart::Hand;
    if (startsWith(n, "forearm.")) return ArmPart::Fore;
    if (startsWith(n, "upperArm.")) return ArmPart::Upper;
  }
  return ArmPart::None;
}

float percentile(std::vector<float> v, float q, float fallback) {
  if (v.size() < 20) return fallback;
  const size_t k = std::min(v.size() - 1, size_t(q * float(v.size() - 1)));
  std::nth_element(v.begin(), v.begin() + std::ptrdiff_t(k), v.end());
  return v[k];
}


// Signed gap of world point p to a body section whose owning bone has global Gb. The section is elliptical (radii
// r1 along e1, r2 along e2; round ends are half-ellipsoids with axial radius min(r1, r2)). The gap is the first-order
// distance to that surface, (F - 1) / |grad F| for the implicit F = |(ax / rc, y / r1, z / r2)| (T-040; T-030 used
// coordinates scaled to the smaller radius, which made a flat section read as deep as its narrow side everywhere:
// up to several centimetres too conservative in front of a wide, shallow pelvis). It is exact on the surface and
// along the axes, and its gradient is the outward normal. Past a joined (flat) end it is the distance to the end
// disc.
struct SectionGap {
  float gap;
  vec3 worldGrad;
};
SectionGap sectionGapInv(const BodyCapsule& C, const mat4& Gb, const mat4& invGb, vec3 p, char side) {
  vec3 u = C.p1 - C.p0;
  const float L = glm::length(u);
  u = L > 1e-6f ? u / L : glm::normalize(glm::cross(C.e1, C.e2));
  const float rc = std::min(C.r1, C.r2);
  const vec3 q0 = vec3(invGb * vec4(p, 1)) - C.p0;
  const float x = glm::dot(q0, u), y = glm::dot(q0, C.e1), z = glm::dot(q0, C.e2);
  const float ax = x < 0 ? -x : x > L ? x - L : 0.0f;
  const float axSign = x < 0 ? -1.0f : 1.0f;
  const bool round = (x < 0 && C.cap0) || (x > L && C.cap1);
  const vec3 sideDir = C.e1 * (side == 'L' ? 1.0f : -1.0f);
  float gap;
  vec3 local;
  if (ax <= 0 || round) {
    const vec3 a(ax / rc, y / C.r1, z / C.r2);
    const float F = glm::length(a);
    const vec3 grad(axSign * ax / (rc * rc), y / (C.r1 * C.r1), z / (C.r2 * C.r2));  // F * grad F
    const float gl = glm::length(grad);
    if (F < 1e-4f || gl < 1e-9f) {
      gap = -rc;
      local = sideDir;
    } else {
      gap = (F - 1) * F / gl;
      local = u * grad.x + C.e1 * grad.y + C.e2 * grad.z;
    }
  } else {
    const float rho = glm::length(vec2(y / C.r1, z / C.r2));
    const vec2 g2(y / (C.r1 * C.r1), z / (C.r2 * C.r2));
    const float gl = glm::length(g2);
    const float radialGap = rho > 1e-4f && gl > 1e-9f ? (rho - 1) * rho / gl : -rc;
    const float ro = std::max(radialGap, 0.0f);
    gap = std::sqrt(ro * ro + ax * ax);
    const vec3 rad = gl > 1e-9f ? (C.e1 * g2.x + C.e2 * g2.y) / gl : vec3(0);
    local = u * (axSign * ax) + ro * rad;
  }
  if (glm::length(local) < 1e-9f) local = sideDir;
  return {gap, glm::normalize(mat3(Gb) * glm::normalize(local))};
}
SectionGap sectionGap(const BodyCapsule& C, const mat4& Gb, vec3 p, char side) {
  return sectionGapInv(C, Gb, glm::inverse(Gb), p, side);
}

vec3 skinPoint(const ArmPoint& P, const std::vector<mat4>& G) {
  vec3 p(0);
  for (int k = 0; k < 4; ++k)
    if (P.weight[k] > 0) p += P.weight[k] * vec3(G[size_t(P.joint[k])] * vec4(P.local[k], 1));
  return p;
}

}  // namespace

namespace {

// Torso clearance field (T-040r1, see interaction.h) from the body triangles of the rest meshes.
vec3 closestOnTriangle(vec3 p, vec3 a, vec3 b, vec3 c, vec3& bary) {  // Ericson, Real-Time Collision Detection 5.1.5
  const vec3 ab = b - a, ac = c - a, ap = p - a;
  const float d1 = glm::dot(ab, ap), d2 = glm::dot(ac, ap);
  if (d1 <= 0 && d2 <= 0) return bary = {1, 0, 0}, a;
  const vec3 bp = p - b;
  const float d3 = glm::dot(ab, bp), d4 = glm::dot(ac, bp);
  if (d3 >= 0 && d4 <= d3) return bary = {0, 1, 0}, b;
  const float vc = d1 * d4 - d3 * d2;
  if (vc <= 0 && d1 >= 0 && d3 <= 0) {
    const float v = d1 / (d1 - d3);
    bary = {1 - v, v, 0};
    return a + v * ab;
  }
  const vec3 cp = p - c;
  const float d5 = glm::dot(ab, cp), d6 = glm::dot(ac, cp);
  if (d6 >= 0 && d5 <= d6) return bary = {0, 0, 1}, c;
  const float vb = d5 * d2 - d1 * d6;
  if (vb <= 0 && d2 >= 0 && d6 <= 0) {
    const float w = d2 / (d2 - d6);
    bary = {1 - w, 0, w};
    return a + w * ac;
  }
  const float va = d3 * d6 - d5 * d4;
  if (va <= 0 && (d4 - d3) >= 0 && (d5 - d6) >= 0) {
    const float w = (d4 - d3) / ((d4 - d3) + (d5 - d6));
    bary = {0, 1 - w, w};
    return b + w * (c - b);
  }
  const float den = 1 / (va + vb + vc), v = vb * den, w = vc * den;
  bary = {1 - v - w, v, w};
  return a + ab * v + ac * w;
}

TorsoField buildTorsoField(const Skeleton& sk, const std::vector<SkinnedMesh>& meshes, const std::vector<int>& region,
                           float bottomY) {
  TorsoField F;
  // Body triangles (vertices welded by rest position within a mesh, for the topology the sign needs).
  struct Tri { vec3 p[3]; int w[3]; vec3 n; size_t mesh; };
  std::vector<Tri> tris;
  std::vector<std::vector<int>> vertexTris;
  std::map<std::pair<int, int>, int> edgeCount;
  struct BodyVertex { vec3 p; int joint[4]; float weight[4]; };
  std::vector<BodyVertex> verts;
  std::map<std::tuple<long, long, long, size_t>, int> weldIds;
  size_t meshIndex = 0;
  for (const SkinnedMesh& m : meshes) {
    ++meshIndex;
    if (startsWith(m.part, "hair")) continue;  // hair (curls hanging onto the chest) is not body volume
    const size_t n = std::min({m.rest.positions.size(), m.joints.size(), m.weights.size()});
    std::vector<char> body(n, 0);
    for (size_t v = 0; v < n; ++v) {
      float w[6] = {0, 0, 0, 0, 0, 0};
      for (int k = 0; k < 4; ++k) {
        const int j = m.joints[v][k];
        if (j >= 0 && size_t(j) < sk.bones.size() && m.weights[v][k] > 0) w[region[size_t(j)]] += m.weights[v][k];
      }
      // Body: mostly torso-carried (>= 90 %, the hips' leg-carried sides down to the pelvis bottom), or, on packages
      // whose torso skin is shared with the neck or legs, torso-dominant with (almost) nothing on the arms and neither
      // the head nor the legs carrying half.
      const float torso = w[int(Region::Torso)], leg = w[int(Region::Leg)];
      const float arm = std::max(w[int(Region::ArmL)], w[int(Region::ArmR)]), headW = w[int(Region::Head)];
      body[v] = torso >= 0.9f || (torso + leg >= 0.9f && m.rest.positions[v].y >= bottomY) ||
                (torso >= 0.5f && arm < 0.1f && headW < 0.5f && leg < 0.5f);
    }
    std::vector<char> used(n, 0);
    auto weld = [&](uint32_t v) {
      const vec3 q = m.rest.positions[v] * 10000.0f;
      auto [it, fresh] = weldIds.try_emplace({std::lround(q.x), std::lround(q.y), std::lround(q.z), meshIndex}, int(vertexTris.size()));
      if (fresh) vertexTris.emplace_back();
      return it->second;
    };
    for (size_t t = 0; t + 2 < m.rest.indices.size(); t += 3) {
      const uint32_t a = m.rest.indices[t], b = m.rest.indices[t + 1], c = m.rest.indices[t + 2];
      if (a >= n || b >= n || c >= n || !body[a] || !body[b] || !body[c]) continue;
      Tri T{{m.rest.positions[a], m.rest.positions[b], m.rest.positions[c]}, {weld(a), weld(b), weld(c)}, vec3(0), meshIndex};
      vec3 nn = glm::cross(T.p[1] - T.p[0], T.p[2] - T.p[0]);
      if (glm::length(nn) < 1e-14f) continue;
      nn = glm::normalize(nn);
      if (m.rest.normals.size() == m.rest.positions.size() &&
          glm::dot(nn, m.rest.normals[a] + m.rest.normals[b] + m.rest.normals[c]) < 0)
        nn = -nn;  // winding against the vertex normals
      T.n = nn;
      for (int k = 0; k < 3; ++k) {
        vertexTris[size_t(T.w[k])].push_back(int(tris.size()));
        const int e0 = T.w[k], e1 = T.w[(k + 1) % 3];
        ++edgeCount[{std::min(e0, e1), std::max(e0, e1)}];
      }
      tris.push_back(T);
      used[a] = used[b] = used[c] = 1;
    }
    for (size_t v = 0; v < n; ++v) {
      if (!used[v]) continue;
      BodyVertex bv{m.rest.positions[v], {0, 0, 0, 0}, {0, 0, 0, 0}};
      for (int k = 0; k < 4; ++k) {
        const int j = m.joints[v][k];
        const bool torsoBone = j >= 0 && size_t(j) < sk.bones.size() && region[size_t(j)] == int(Region::Torso);
        bv.joint[k] = torsoBone ? j : -1;
        bv.weight[k] = torsoBone ? m.weights[v][k] : 0.0f;
      }
      verts.push_back(bv);
    }
  }
  F.triangles = tris.size();
  if (tris.size() < 100) return F;
  std::vector<char> boundaryVertex(vertexTris.size(), 0);
  for (const auto& [e, count] : edgeCount)
    if (count < 2) boundaryVertex[size_t(e.first)] = boundaryVertex[size_t(e.second)] = 1;
  // Rows up the body (+Y): the torso bones' mean skin weights per row (normalised), for blending the bones' copies.
  float top = -1e9f, low = 1e9f;
  for (const BodyVertex& v : verts) top = std::max(top, v.p.y), low = std::min(low, v.p.y);
  F.h0 = low;
  F.nh = int(std::ceil((top - low) / F.dh)) + 1;
  const int nh = F.nh;
  std::vector<std::vector<float>> bw{size_t(nh), std::vector<float>{}};
  std::vector<float> bwSum(size_t(nh), 0.0f);
  for (const BodyVertex& v : verts) {
    const float s = (v.p.y - F.h0) / F.dh;
    for (int r = std::max(0, int(std::floor(s - 1.5f))); r <= std::min(nh - 1, int(std::ceil(s + 1.5f))); ++r) {
      if (std::abs(s - float(r)) > 1.5f) continue;
      for (int k = 0; k < 4; ++k) {
        if (v.joint[k] < 0 || v.weight[k] <= 0) continue;
        auto it = std::find(F.bones.begin(), F.bones.end(), v.joint[k]);
        const size_t bi = size_t(it - F.bones.begin());
        if (it == F.bones.end()) {
          F.bones.push_back(v.joint[k]);
          for (auto& row : bw) row.push_back(0.0f);
        }
        bw[size_t(r)][bi] += v.weight[k];
        bwSum[size_t(r)] += v.weight[k];
      }
    }
  }
  if (F.bones.empty()) return F;
  for (int b : F.bones) F.heads.push_back(sk.bones[size_t(b)].head);
  const size_t nb = F.bones.size();
  F.weight.assign(nb * size_t(nh), 0.0f);
  std::vector<char> hasW(size_t(nh), 0);
  for (int r = 0; r < nh; ++r)
    if (bwSum[size_t(r)] > 1e-6f) {
      hasW[size_t(r)] = 1;
      for (size_t b = 0; b < nb; ++b) F.weight[b * size_t(nh) + size_t(r)] = bw[size_t(r)][b] / bwSum[size_t(r)];
    }
  for (int r = 0; r < nh; ++r) {
    if (hasW[size_t(r)]) continue;
    for (int d = 1; d < nh; ++d) {
      const int from = r - d >= 0 && hasW[size_t(r - d)] ? r - d : r + d < nh && hasW[size_t(r + d)] ? r + d : -1;
      if (from < 0) continue;
      for (size_t b = 0; b < nb; ++b) F.weight[b * size_t(nh) + size_t(r)] = F.weight[b * size_t(nh) + size_t(from)];
      break;
    }
  }
  // Grid over the body with a margin; signed distance to the nearest body triangle (exact within the band, by the
  // swept nearest triangle beyond it), signed by the angle-weighted pseudo-normal of the nearest feature (a nearest
  // feature on an open boundary - a hem, an armhole, a side panel carried by the arm - has no inside: outside).
  vec3 lo(1e9f), hi(-1e9f);
  for (const Tri& T : tris)
    for (const vec3& q : T.p) lo = glm::min(lo, q), hi = glm::max(hi, q);
  const float pad = 0.06f, h = F.cell, band = 0.03f;
  F.origin = lo - vec3(pad);
  F.dims = glm::ivec3(glm::ceil((hi - lo + 2 * pad) / h)) + 1;
  const glm::ivec3 D = F.dims;
  const size_t cells = size_t(D.x) * size_t(D.y) * size_t(D.z);
  F.dist.assign(cells, 1e9f);
  std::vector<int> nearest(cells, -1);
  std::vector<vec3> nearestBary(cells);
  auto id = [&](int x, int y, int z) { return (size_t(z) * size_t(D.y) + size_t(y)) * size_t(D.x) + size_t(x); };
  for (size_t t = 0; t < tris.size(); ++t) {
    const Tri& T = tris[t];
    const vec3 tl = glm::min(glm::min(T.p[0], T.p[1]), T.p[2]) - vec3(band), th = glm::max(glm::max(T.p[0], T.p[1]), T.p[2]) + vec3(band);
    const glm::ivec3 c0 = glm::max(glm::ivec3(glm::ceil((tl - F.origin) / h)), glm::ivec3(0));
    const glm::ivec3 c1 = glm::min(glm::ivec3(glm::floor((th - F.origin) / h)), D - 1);
    for (int z = c0.z; z <= c1.z; ++z)
      for (int y = c0.y; y <= c1.y; ++y)
        for (int x = c0.x; x <= c1.x; ++x) {
          const vec3 p = F.origin + vec3(x, y, z) * h;
          vec3 bary;
          const float d = glm::distance(p, closestOnTriangle(p, T.p[0], T.p[1], T.p[2], bary));
          const size_t i = id(x, y, z);
          if (d < F.dist[i]) F.dist[i] = d, nearest[i] = int(t), nearestBary[i] = bary;
        }
  }
  // Buckets (2.5 cm) of the triangles, for the confirming rays.
  const float bucket = 0.025f;
  const glm::ivec3 BD = glm::ivec3(glm::ceil((hi - lo) / bucket)) + 1;
  std::vector<std::vector<int>> buckets(size_t(BD.x) * size_t(BD.y) * size_t(BD.z));
  auto bucketId = [&](glm::ivec3 c) { return (size_t(c.z) * size_t(BD.y) + size_t(c.y)) * size_t(BD.x) + size_t(c.x); };
  for (size_t t = 0; t < tris.size(); ++t) {
    const Tri& T = tris[t];
    const glm::ivec3 b0 = glm::clamp(glm::ivec3(glm::floor((glm::min(glm::min(T.p[0], T.p[1]), T.p[2]) - lo) / bucket)), glm::ivec3(0), BD - 1);
    const glm::ivec3 b1 = glm::clamp(glm::ivec3(glm::floor((glm::max(glm::max(T.p[0], T.p[1]), T.p[2]) - lo) / bucket)), glm::ivec3(0), BD - 1);
    for (int z = b0.z; z <= b1.z; ++z)
      for (int y = b0.y; y <= b1.y; ++y)
        for (int x = b0.x; x <= b1.x; ++x) buckets[bucketId({x, y, z})].push_back(int(t));
  }
  std::vector<unsigned> stamp(tris.size(), 0);
  unsigned rayId = 0;
  auto rayHitsShell = [&](vec3 o, vec3 d, size_t mesh) -> int {  // Moller-Trumbore against one shell's triangles
    ++rayId;
    const float len = glm::length(hi - lo) + bucket;
    for (float t = 0; t <= len; t += 0.5f * bucket) {
      const glm::ivec3 c = glm::ivec3(glm::floor((o + d * t - lo) / bucket));
      if (glm::any(glm::lessThan(c, glm::ivec3(0))) || glm::any(glm::greaterThanEqual(c, BD))) {
        if (t > 0) break;
        continue;
      }
      for (int u : buckets[bucketId(c)]) {
        if (stamp[size_t(u)] == rayId) continue;
        stamp[size_t(u)] = rayId;
        const Tri& T = tris[size_t(u)];
        if (mesh != size_t(-1) && T.mesh != mesh) continue;
        const vec3 e1 = T.p[1] - T.p[0], e2 = T.p[2] - T.p[0], hv = glm::cross(d, e2);
        const float det = glm::dot(e1, hv);
        if (std::abs(det) < 1e-12f) continue;
        const float inv = 1 / det;
        const vec3 sv = o - T.p[0];
        const float bu = inv * glm::dot(sv, hv);
        if (bu < 0 || bu > 1) continue;
        const vec3 qv = glm::cross(sv, e1);
        const float bv = inv * glm::dot(d, qv);
        if (bv < 0 || bu + bv > 1) continue;
        if (inv * glm::dot(e2, qv) > 1e-6f) return 1;
      }
    }
    return 0;
  };
  auto angleAt = [&](const Tri& T, int k) {
    const vec3 u = T.p[(k + 1) % 3] - T.p[k], v = T.p[(k + 2) % 3] - T.p[k];
    const float l = glm::length(u) * glm::length(v);
    return l > 1e-12f ? std::acos(std::clamp(glm::dot(u, v) / l, -1.0f, 1.0f)) : 0.0f;
  };
  // Beyond the band: the nearest triangle is carried on by sweeps (each cell tries its swept neighbours' triangles,
  // exactly), so every cell knows its nearest triangle and gets its sign by the same rule.
  for (int pass = 0; pass < 4; ++pass) {
    const int dir = pass % 2 == 0 ? 1 : -1;
    for (int zz = 0; zz < D.z; ++zz)
      for (int yy = 0; yy < D.y; ++yy)
        for (int xx = 0; xx < D.x; ++xx) {
          const int x = dir > 0 ? xx : D.x - 1 - xx, y = dir > 0 ? yy : D.y - 1 - yy, z = dir > 0 ? zz : D.z - 1 - zz;
          const size_t i = id(x, y, z);
          if (F.dist[i] <= band) continue;
          const vec3 p = F.origin + vec3(x, y, z) * h;
          for (int k = 0; k < 3; ++k) {
            glm::ivec3 c(x, y, z);
            c[k] -= dir;
            if (c[k] < 0 || c[k] >= D[k]) continue;
            const int t = nearest[id(c.x, c.y, c.z)];
            if (t < 0 || t == nearest[i]) continue;
            const Tri& T = tris[size_t(t)];
            vec3 bary;
            const float d = glm::distance(p, closestOnTriangle(p, T.p[0], T.p[1], T.p[2], bary));
            if (d < F.dist[i]) F.dist[i] = d, nearest[i] = t, nearestBary[i] = bary;
          }
        }
  }
  std::vector<signed char> sign(cells, 0);
  for (size_t i = 0; i < cells; ++i) {
    if (nearest[i] < 0) continue;
    const Tri& T = tris[size_t(nearest[i])];
    const vec3 bary = nearestBary[i];
    const glm::ivec3 c(int(i % size_t(D.x)), int((i / size_t(D.x)) % size_t(D.y)), int(i / (size_t(D.x) * size_t(D.y))));
    const vec3 p = F.origin + vec3(c) * h;
    const vec3 q = T.p[0] * bary.x + T.p[1] * bary.y + T.p[2] * bary.z;
    int zero = 0;
    for (int k = 0; k < 3; ++k) zero += bary[k] <= 1e-6f;
    vec3 n(0);
    bool open = false;
    if (zero == 0) n = T.n;
    else if (zero == 1) {
      int a = -1, b = -1;
      for (int k = 0; k < 3; ++k)
        if (bary[k] > 1e-6f) (a < 0 ? a : b) = T.w[k];
      if (edgeCount[{std::min(a, b), std::max(a, b)}] < 2) open = true;
      else
        for (int u : vertexTris[size_t(a)])
          for (int k = 0; k < 3; ++k)
            if (tris[size_t(u)].w[k] == b) n += tris[size_t(u)].n;
    } else {
      const int k = bary.x > 0.5f ? 0 : bary.y > 0.5f ? 1 : 2;
      const int wv = T.w[k];
      if (boundaryVertex[size_t(wv)]) open = true;
      else
        for (int u : vertexTris[size_t(wv)])
          for (int j = 0; j < 3; ++j)
            if (tris[size_t(u)].w[j] == wv) n += angleAt(tris[size_t(u)], j) * tris[size_t(u)].n;
    }
    sign[i] = open || glm::dot(p - q, n) >= 0 ? 1 : -1;
    // A negative sign is confirmed by rays, as the T-040 mesh measurement does: a point inside a shell hits that shell
    // in (nearly) every direction; one outside a thin or open shell (a drawstring, a hood roll) escapes.
    // Inside = at least 2 of 3 rays hit the nearest triangle's own shell (the T-040 measurement's rule, so the
    // post-pass and the evidence agree on what is inside).
    if (sign[i] < 0) {
      vec3 a = p - q;
      a = glm::length(a) > 1e-7f ? glm::normalize(a) : -n;
      const vec3 t1 = glm::normalize(std::abs(a.y) < 0.9f ? glm::cross(a, vec3(0, 1, 0)) : glm::cross(a, vec3(1, 0, 0)));
      const vec3 t2 = glm::cross(a, t1);
      int hits = 0;
      for (vec3 dir : {a, glm::normalize(a + t1), glm::normalize(a - 0.5f * t1 + 0.9f * t2)}) hits += rayHitsShell(p, dir, T.mesh);
      if (hits < 2) sign[i] = 1;
    }
  }
  for (size_t i = 0; i < cells; ++i) F.dist[i] = sign[i] == 0 ? band : float(sign[i]) * F.dist[i];
  F.valid = true;
  return F;
}

}  // namespace

ProfileGap torsoFieldGap(const TorsoField& F, vec3 q) {
  // Trilinear in the grid (outside it: the distance to the grid box added to the border value).
  const vec3 s = (q - F.origin) / F.cell;
  const vec3 maxIdx = vec3(F.dims - 1) - vec3(1e-3f);
  const vec3 sc = glm::clamp(s, vec3(0), maxIdx);
  const glm::ivec3 c = glm::min(glm::ivec3(sc), F.dims - 2);
  const vec3 t = sc - vec3(c);
  auto at = [&](int x, int y, int z) {
    return F.dist[(size_t(c.z + z) * size_t(F.dims.y) + size_t(c.y + y)) * size_t(F.dims.x) + size_t(c.x + x)];
  };
  float v[2][2][2];
  for (int z = 0; z < 2; ++z)
    for (int y = 0; y < 2; ++y)
      for (int x = 0; x < 2; ++x) v[z][y][x] = at(x, y, z);
  auto lerp = [](float a, float b, float u) { return a + (b - a) * u; };
  const float x00 = lerp(v[0][0][0], v[0][0][1], t.x), x10 = lerp(v[0][1][0], v[0][1][1], t.x);
  const float x01 = lerp(v[1][0][0], v[1][0][1], t.x), x11 = lerp(v[1][1][0], v[1][1][1], t.x);
  const float y0 = lerp(x00, x10, t.y), y1 = lerp(x01, x11, t.y);
  float gap = lerp(y0, y1, t.z);
  vec3 g;
  g.x = lerp(lerp(v[0][0][1] - v[0][0][0], v[0][1][1] - v[0][1][0], t.y), lerp(v[1][0][1] - v[1][0][0], v[1][1][1] - v[1][1][0], t.y), t.z);
  g.y = lerp(x10 - x00, x11 - x01, t.z);
  g.z = y1 - y0;
  const float outside = glm::length((s - sc) * F.cell);
  if (outside > 0) gap += outside, g += (s - sc);
  const float gl = glm::length(g);
  return {gap, gl > 1e-12f ? g / gl : vec3(0, 1, 0)};
}


BodyClearanceModel bodyClearanceModel(const Skeleton& sk, const std::vector<SkinnedMesh>& meshes) {
  BodyClearanceModel M;
  const int hips = sk.find("hips"), chest = sk.find("chest"), spine = sk.find("spine"), neck = sk.find("neck");
  if (hips < 0 || chest < 0) return M;
  auto head = [&](int b) { return sk.bones[size_t(b)].head; };
  for (int s = 0; s < 2; ++s) {
    const char side = s == 0 ? 'L' : 'R';
    ArmModel& A = M.arm[s];
    A.hand = sk.find(std::string("hand.") + side);
    if (A.hand < 0) return M;
    A.fore = sk.bones[size_t(A.hand)].parent;
    A.upper = A.fore >= 0 ? sk.bones[size_t(A.fore)].parent : -1;
    if (A.upper < 0) return M;
  }
  // Skinned rest vertices by region (a vertex counts when >= 90 % of its weight is in one region).
  std::vector<int> region(sk.bones.size()), part(sk.bones.size());
  for (size_t b = 0; b < sk.bones.size(); ++b) region[b] = int(regionOf(sk, int(b))), part[b] = int(armPartOf(sk, int(b)));
  std::vector<vec3> torso, pelvisLegs;
  struct Cand { const SkinnedMesh* m; size_t v; };
  std::vector<Cand> armCand[2];
  for (const SkinnedMesh& m : meshes) {
    for (size_t v = 0; v < m.rest.positions.size() && v < m.joints.size() && v < m.weights.size(); ++v) {
      float w[6] = {0, 0, 0, 0, 0, 0};
      for (int k = 0; k < 4; ++k) {
        const int j = m.joints[v][k];
        if (j < 0 || size_t(j) >= sk.bones.size() || m.weights[v][k] <= 0) continue;
        w[region[size_t(j)]] += m.weights[v][k];
      }
      if (w[int(Region::Torso)] >= 0.9f) torso.push_back(m.rest.positions[v]);
      // At the pelvis the hips' sides are often carried by the thighs (shorts, a skirt, the skin of the hip): there
      // the body is torso and leg together (T-040; a torso-only fit found a 4 cm wide pelvis on some characters).
      else if (w[int(Region::Torso)] + w[int(Region::Leg)] >= 0.9f) pelvisLegs.push_back(m.rest.positions[v]);
      // Arm surface: carried at least half by that arm (a sleeve between shoulder and hand included), nothing of the
      // head or legs; torso garment vertices with a little weight bleed onto the arm stay body.
      for (int s = 0; s < 2; ++s)
        if (w[int(s == 0 ? Region::ArmL : Region::ArmR)] >= 0.5f && w[int(Region::Head)] + w[int(Region::Leg)] < 0.1f)
          armCand[s].push_back({&m, v});
    }
  }
  const bool fromMesh = torso.size() >= 200;
  M.source = fromMesh ? "mesh" : "skeleton";
  const int ua = sk.find("upperArm.L"), ub = sk.find("upperArm.R");
  const float shoulderHalf = ua >= 0 && ub >= 0 ? 0.5f * glm::distance(head(ua), head(ub)) : 0.12f;
  const float rDefault = 0.95f * shoulderHalf;
  // Body sections along the spine: pelvis (below the hips, carried by the hips), lower torso (hips -> chest, carried
  // by the spine or hips) and upper torso (chest -> neck, carried by the chest), each cut into short bands whose
  // radii fit the vertices of their own height slab (a waist is narrower than a belly). Bands meet with flat ends;
  // the lowest and highest are capsules with round ends.
  auto band = [&](std::string name, int bone, vec3 a, vec3 b, bool withLegs) {
    BodyCapsule C;
    C.name = std::move(name);
    C.bone = bone;
    C.p0 = a - head(bone);
    C.p1 = b - head(bone);
    const vec3 u = glm::normalize(b - a);
    C.e1 = glm::normalize(vec3(1, 0, 0) - u * u.x);
    C.e2 = glm::normalize(glm::cross(C.e1, u));  // forward (+Z) for an upright segment
    C.cap0 = C.cap1 = false;
    std::vector<float> side, front;
    for (size_t i = 0; i < torso.size() + (withLegs ? pelvisLegs.size() : 0); ++i) {
      const vec3& p = i < torso.size() ? torso[i] : pelvisLegs[i - torso.size()];
      const float t = glm::dot(p - a, b - a) / glm::dot(b - a, b - a);
      if (t < 0 || t > 1) continue;
      const vec3 d = p - (a + t * (b - a));
      if (glm::dot(d, C.e2) < 0) continue;  // front half only: hands work in front (hair, a backpack are not body)
      side.push_back(std::abs(glm::dot(d, C.e1)));
      front.push_back(glm::dot(d, C.e2));
    }
    C.r1 = std::clamp(percentile(side, 0.99f, rDefault), 0.02f, 0.5f);
    C.r2 = std::clamp(percentile(front, 0.99f, rDefault), 0.02f, 0.5f);
    M.body.push_back(C);
  };
  const vec3 top = neck >= 0 ? head(neck) : head(chest) + vec3(0, 0.6f * shoulderHalf, 0);
  const vec3 bottom = head(hips) + 0.4f * (head(hips) - head(chest));
  auto bands = [&](const char* name, int bone, vec3 a, vec3 b, int n, bool withLegs) {
    for (int i = 0; i < n; ++i)
      band(std::format("{}_{}", name, i + 1), bone, glm::mix(a, b, float(i) / float(n)), glm::mix(a, b, float(i + 1) / float(n)), withLegs);
  };
  bands("pelvis", hips, bottom, head(hips), 2, true);
  bands("torso_lower", spine >= 0 ? spine : hips, head(hips), head(chest), 3, false);
  bands("torso_upper", chest, head(chest), top, 2, false);
  M.body.front().cap0 = true;
  M.body.back().cap1 = true;
  // Arm points: an even subsample (at most 600 per arm) of the arm surface, with skin weights and joint offsets.
  for (int s = 0; s < 2; ++s) {
    ArmModel& A = M.arm[s];
    const char side = s == 0 ? 'L' : 'R';
    const HandGrip g = handGrip(sk, A.hand, side);
    const vec3 su = head(A.upper), sf = head(A.fore), sh = head(A.hand), st = sh + g.fingerDir * (1.5f * g.palmLength);
    auto segDist = [](vec3 p, vec3 a, vec3 b) {
      const float t = std::clamp(glm::dot(p - a, b - a) / std::max(1e-9f, glm::dot(b - a, b - a)), 0.0f, 1.0f);
      return glm::distance(p, a + t * (b - a));
    };
    const size_t stride = std::max<size_t>(1, armCand[s].size() / 600);
    // The post-pass (T-040r1) takes the arm surface at 3 mm spacing (one vertex per 3 mm cell): a sleeve puff or cuff
    // that a sparse subsample misses is exactly what presses into the body.
    std::set<std::tuple<long, long, long>> welded;
    for (size_t i = 0; i < armCand[s].size(); ++i) {
      const SkinnedMesh& m = *armCand[s][i].m;
      const size_t v = armCand[s][i].v;
      const vec3 key = glm::floor(m.rest.positions[v] / 0.003f);  // one vertex per 3 mm cell
      const bool dense = welded.insert({std::lround(key.x), std::lround(key.y), std::lround(key.z)}).second;
      const bool sparse = i % stride == 0;
      if (!dense && !sparse) continue;
      ArmPoint P;
      const vec3 p = m.rest.positions[v];
      for (int k = 0; k < 4; ++k) {
        const int j = std::clamp(m.joints[v][k], 0, int(sk.bones.size()) - 1);
        P.joint[k] = j;
        P.weight[k] = m.weights[v][k];
        P.local[k] = p - sk.bones[size_t(j)].head;
        if (part[size_t(j)] == int(ArmPart::Fore) || part[size_t(j)] == int(ArmPart::Hand)) P.mobility += m.weights[v][k];
        const int pj = part[size_t(j)];
        if (pj != int(ArmPart::None)) P.followUpper += m.weights[v][k];
        if (pj == int(ArmPart::Fore) || pj == int(ArmPart::Hand)) P.followFore += m.weights[v][k];
        if (pj == int(ArmPart::Hand)) P.followHand += m.weights[v][k];
      }
      P.along = glm::dot(p - su, sf - su) / std::max(1e-9f, glm::dot(sf - su, sf - su));
      const float du = segDist(p, su, sf), df = segDist(p, sf, sh), dh = segDist(p, sh, st);
      // The elbow half of the forearm counts with the upper arm: an elbow rests against the body's side.
      const float tf = glm::dot(p - sf, sh - sf) / std::max(1e-9f, glm::dot(sh - sf, sh - sf));
      P.part = dh <= df && dh <= du ? 2 : (df <= du && tf >= 0.5f) ? 1 : 0;
      if (sparse) A.points.push_back(P);
      if (dense) A.dense.push_back(P);
    }
  }
  // Resting contact: an arm point already inside a body section at rest (a sleeve under a vest's armhole, a puff
  // pressed against the side) may stay as deep as it rests, never deeper; every other point keeps the margin.
  std::vector<mat4> rest(sk.bones.size());
  for (size_t b = 0; b < sk.bones.size(); ++b) rest[b] = glm::translate(mat4(1), sk.bones[b].head);
  M.field = buildTorsoField(sk, meshes, region, bottom.y);
  for (int s = 0; s < 2; ++s)
    for (ArmPoint& P : M.arm[s].points) {
      float g = 1e9f;
      for (const BodyCapsule& C : M.body) g = std::min(g, sectionGap(C, rest[size_t(C.bone)], skinPoint(P, rest), s == 0 ? 'L' : 'R').gap);
      P.allowance = std::min(0.0f, g - kArmBodyMargin);
      // (20 microns below the exact value: posed and rest evaluations differ by float rounding)
      P.restGap = (M.field.valid ? torsoFieldGap(M.field, skinPoint(P, rest)).gap : g) - 2e-5f;
    }
  for (int s = 0; s < 2; ++s)
    for (ArmPoint& P : M.arm[s].dense) {
      float g = 1e9f;
      if (!M.field.valid)
        for (const BodyCapsule& C : M.body) g = std::min(g, sectionGap(C, rest[size_t(C.bone)], skinPoint(P, rest), s == 0 ? 'L' : 'R').gap);
      P.restGap = (M.field.valid ? torsoFieldGap(M.field, skinPoint(P, rest)).gap : g) - 2e-5f;
    }
  M.valid = true;
  static std::atomic<unsigned long long> fits{0};
  M.id = ++fits;
  return M;
}

float bodySectionGap(const BodyCapsule& C, const mat4& Gb, vec3 p) { return sectionGap(C, Gb, p, 'L').gap; }

ArmClearance armClearance(const BodyClearanceModel& M, const std::vector<mat4>& G, char side) {
  ArmClearance out;
  if (!M.valid) return out;
  static const char* kPart[3] = {"upperArm", "forearm", "hand"};
  for (const ArmPoint& P : M.arm[side == 'L' ? 0 : 1].points) {
    const vec3 p = skinPoint(P, G);
    for (const BodyCapsule& C : M.body) {
      const SectionGap sg = sectionGap(C, G[size_t(C.bone)], p, side);
      const float gap = sg.gap - P.allowance;  // never deeper than at rest
      if (P.part == 0) {  // upper arm: reported only here (the T-040 post-pass clears it past the armpit band)
        out.upperGap = std::min(out.upperGap, gap);
        continue;
      }
      out.rawGap = std::min(out.rawGap, sg.gap);
      if (gap >= out.gap) continue;
      out.gap = gap;
      out.part = kPart[P.part];
      out.against = C.name;
      out.mobility = P.mobility;
      out.point = p;
      out.push = sg.worldGrad;
    }
  }
  return out;
}

void applyArmPoles(const Skeleton& sk, const Clip& clip, const std::string& prefix, double frame, const mat4& world,
                   Pose& pose) {
  for (size_t i = 0; i < sk.bones.size(); ++i) {
    const std::string name = prefix + "pole." + sk.bones[i].name;
    const Track* t = clip.find(name);
    if (!t || t->keys.empty()) continue;
    const float w = std::clamp(clip.evaluate(name + ".weight", frame, vec3(1)).x, 0.0f, 1.0f);
    const int mid = sk.bones[i].parent, root = mid >= 0 ? sk.bones[size_t(mid)].parent : -1;
    if (w <= 0 || root < 0) continue;
    const std::vector<mat4> G = boneGlobals(sk, pose, world);
    const vec3 a(G[size_t(root)][3]), b(G[size_t(mid)][3]), c(G[i][3]);
    if (glm::length(c - a) < 1e-5f) continue;
    const vec3 u = glm::normalize(c - a), pole = t->evaluate(frame);
    vec3 e = (b - a) - u * glm::dot(b - a, u), p = pole - u * glm::dot(pole, u);
    const float le = glm::length(e), lp = glm::length(p), lpole = glm::length(pole);
    if (le < 1e-5f || lp < 1e-6f || lpole < 1e-6f) continue;
    e /= le;
    p /= lp;
    // A pole nearly along the arm has no meaningful plane: fade out instead of flipping.
    const float strength = std::clamp((lp / lpole) / 0.3f, 0.0f, 1.0f);
    const float angle = std::atan2(glm::dot(glm::cross(e, p), u), glm::dot(e, p));
    const quat R = glm::angleAxis(angle * w * strength, u);
    const int parent = sk.bones[size_t(root)].parent;
    const mat4 pg = parent >= 0 ? G[size_t(parent)] : world;
    const quat parentRot = glm::normalize(glm::quat_cast(mat3(glm::normalize(vec3(pg[0])), glm::normalize(vec3(pg[1])),
                                                              glm::normalize(vec3(pg[2])))));
    const quat handBefore = glm::normalize(glm::quat_cast(mat3(G[i])));
    pose.local[size_t(root)] = glm::normalize(glm::inverse(parentRot) * R * parentRot * pose.local[size_t(root)]);
    // Only the elbow moves: the hand keeps its world rotation (the forearm's swing is taken out of the hand's local).
    const quat midAfter = glm::normalize(glm::quat_cast(mat3(boneGlobals(sk, pose, world)[size_t(mid)])));
    pose.local[i] = glm::normalize(glm::inverse(midAfter) * handBefore);
  }
}

// ------------------------------------------------------------------------ always-on arm-body clearance (T-040)
namespace {

quat rotationOf(const mat4& m) {
  return glm::normalize(glm::quat_cast(mat3(glm::normalize(vec3(m[0])), glm::normalize(vec3(m[1])), glm::normalize(vec3(m[2])))));
}
quat rotationFromVector(vec3 w) {
  const float a = glm::length(w);
  return a > 1e-9f ? glm::angleAxis(a, w / a) : quat(1, 0, 0, 0);
}

// The post-pass body is carried by torso bones, which the arm pass never moves: their frames and inverses are computed
// once per pass.
struct BodyFrames {
  std::vector<mat4> G, inv;          // sections (fallback)
  std::vector<mat4> profG, profInv;  // profile bones
};
BodyFrames bodyFrames(const BodyClearanceModel& M, const std::vector<mat4>& G) {
  BodyFrames B;
  if (M.field.valid) {
    for (int b : M.field.bones) B.profG.push_back(G[size_t(b)]), B.profInv.push_back(glm::inverse(G[size_t(b)]));
    return B;
  }
  for (const BodyCapsule& C : M.body) B.G.push_back(G[size_t(C.bone)]), B.inv.push_back(glm::inverse(G[size_t(C.bone)]));
  return B;
}
// Gap of a world point to the post-pass body: the profile carried by each of its bones, blended by the bones' row
// weights at the point's height in that bone's frame (the sections when the character has no profile).
SectionGap postPassGap(const BodyClearanceModel& M, const BodyFrames& B, vec3 p, char side) {
  const TorsoField& P = M.field;
  if (!P.valid) {
    SectionGap best{1e9f, vec3(0)};
    for (size_t k = 0; k < M.body.size(); ++k) {
      const SectionGap sg = sectionGapInv(M.body[k], B.G[k], B.inv[k], p, side);
      if (sg.gap < best.gap) best = sg;
    }
    return best;
  }
  // Rest coordinates of the point as carried by each torso bone (skinning: G_b (rest - head_b)), blended with the
  // bones' weights at that height (an inverse of the torso's skinning), then one field lookup; the gradient goes
  // back to the world with the blended rotation.
  vec3 rest(0);
  mat3 rot(0.0f);
  float wsum = 0;
  for (size_t b = 0; b < P.bones.size(); ++b) {
    const vec3 q = vec3(B.profInv[b] * vec4(p, 1)) + P.heads[b];
    const float s = std::clamp((q.y - P.h0) / P.dh, 0.0f, float(P.nh - 1));
    const int i0 = std::min(int(s), std::max(0, P.nh - 2)), i1 = std::min(i0 + 1, P.nh - 1);
    const float* W = &P.weight[b * size_t(P.nh)];
    const float w = glm::mix(W[i0], W[i1], s - float(i0));
    if (w <= 1e-4f) continue;
    rest += w * q;
    rot += w * mat3(B.profG[b]);
    wsum += w;
  }
  if (wsum <= 0) return {1e9f, vec3(0)};
  const ProfileGap pg = torsoFieldGap(P, rest / wsum);
  const vec3 grad = rot * pg.grad;
  const float gl = glm::length(grad);
  return {pg.gap, gl > 1e-9f ? grad / gl : vec3(side == 'L' ? 1.0f : -1.0f, 0, 0)};
}
bool postPassPoint(const ArmPoint& P, const ArmPostPassOptions& o) {
  return !(P.part == 0 && P.along < o.armpit) && P.followUpper >= 0.5f;
}
// Gap of a point for the post-pass: a point that rests nearer than the untouched threshold (margin + band) counts
// from its rest gap, so the rest pose itself is never corrected.
float passGap(const ArmPoint& P, float gapValue, const ArmPostPassOptions& o) {
  return gapValue - std::min(0.0f, P.restGap - (o.margin + o.band));
}
// C1 ramp of the target gap (see interaction.h).
float targetGap(float gap, const ArmPostPassOptions& o) {
  const float x = o.margin + o.band - gap, b = std::max(o.band, 1e-6f);
  if (x <= 0) return gap;
  return gap + (x < 2 * b ? x * x / (4 * b) : x - b);
}
// Per point of the post-pass: position, gap (rest-relative) and outward world normal.
struct PointGap {
  vec3 p, n;
  float gap;
};
const std::vector<ArmPoint>& passPoints(const ArmModel& A) { return A.dense.empty() ? A.points : A.dense; }
void pointGaps(const BodyClearanceModel& M, const BodyFrames& B, const std::vector<mat4>& G, const ArmModel& A, char side,
               const ArmPostPassOptions& o, std::vector<PointGap>& out, const std::vector<int>* subset = nullptr) {
  const std::vector<ArmPoint>& pts = passPoints(A);
  out.resize(pts.size());
  const size_t n = subset ? subset->size() : pts.size();
  for (size_t k = 0; k < n; ++k) {
    const size_t i = subset ? size_t((*subset)[k]) : k;
    const ArmPoint& P = pts[i];
    if (!postPassPoint(P, o)) {
      out[i].gap = 1e9f;
      continue;
    }
    const vec3 p = skinPoint(P, G);
    const SectionGap sg = postPassGap(M, B, p, side);
    out[i] = {p, sg.worldGrad, passGap(P, sg.gap, o)};
  }
}
float worstGap(const std::vector<PointGap>& g) {
  float w = 1e9f;
  for (const PointGap& x : g) w = std::min(w, x.gap);
  return w;
}
void rotateBoneWorld(const Skeleton& sk, const std::vector<mat4>& G, const mat4& world, int bone, const quat& R, Pose& pose) {
  const int parent = sk.bones[size_t(bone)].parent;
  const quat pr = rotationOf(parent >= 0 ? G[size_t(parent)] : world);
  pose.local[size_t(bone)] = glm::normalize(glm::inverse(pr) * R * pr * pose.local[size_t(bone)]);
}
// Solve the small symmetric positive definite system A x = b (n <= 7) by Cholesky.
template <int N>
bool solveSpd(float (&A)[N][N], float (&b)[N], float (&x)[N]) {
  float L[N][N] = {};
  for (int i = 0; i < N; ++i)
    for (int j = 0; j <= i; ++j) {
      double sum = A[i][j];
      for (int k = 0; k < j; ++k) sum -= double(L[i][k]) * L[j][k];
      if (i == j) {
        if (sum <= 1e-20) return false;
        L[i][i] = float(std::sqrt(sum));
      } else L[i][j] = float(sum / L[j][j]);
    }
  float y[N];
  for (int i = 0; i < N; ++i) {
    double sum = b[i];
    for (int k = 0; k < i; ++k) sum -= double(L[i][k]) * y[k];
    y[i] = float(sum / L[i][i]);
  }
  for (int i = N - 1; i >= 0; --i) {
    double sum = y[i];
    for (int k = i + 1; k < N; ++k) sum -= double(L[k][i]) * x[k];
    x[i] = float(sum / L[i][i]);
  }
  return true;
}

}  // namespace

float armBodyGap(const BodyClearanceModel& M, const std::vector<mat4>& G, char side, const ArmPostPassOptions& o) {
  if (!M.valid) return 1e9f;
  const ArmModel& A = M.arm[side == 'L' ? 0 : 1];
  if (passPoints(A).empty()) return 1e9f;
  std::vector<PointGap> g;
  pointGaps(M, bodyFrames(M, G), G, A, side, o, g);
  return worstGap(g);
}

// The correction runs in two stages from the evaluated pose, blended by the IK weight `pin`:
//  1. swing (share pin of every point's demand): the upper arm turns about shoulder -> wrist (the wrist and the
//     hand's world rotation stay), at most maxSwing; it moves only what the upper arm and forearm carry;
//  2. free (share 1 - pin of what remains): shoulder (3 rotations) and elbow (3, twice as stiff), the hand following
//     the forearm or keeping its world rotation as far as `keepHand` asks.
// So a pinned arm keeps its wrist exactly, a free arm is corrected fully, and an IK weight ramp hands over linearly.
// Each stage is a damped Gauss-Newton solve of: every point at or above its target gap (targetGap of its gap at the
// stage start, scaled by the stage's share), the rotations as small as possible. Points weigh in by how far they are
// below their target (zero at the target, full 1 mm under it), so points enter and leave continuously; the iteration
// count is fixed, so the result is a continuous function of the pose.
namespace {
ArmPostPassResult armPostPass(const Skeleton& sk, const BodyClearanceModel& M, const mat4& world, char side, float pin,
                              float keepHand, Pose& pose, const ArmPostPassOptions& o) {
  ArmPostPassResult out;
  if (!M.valid) return out;
  const ArmModel& A = M.arm[side == 'L' ? 0 : 1];
  if (A.points.empty() || A.upper < 0 || A.fore < 0 || A.hand < 0) return out;
  pin = std::clamp(pin, 0.0f, 1.0f);
  keepHand = std::clamp(std::max(keepHand, pin), 0.0f, 1.0f);
  std::vector<mat4> G = boneGlobals(sk, pose, world);
  const BodyFrames B = bodyFrames(M, G);
  const float T = o.margin + o.band;
  std::vector<PointGap> gaps;
  pointGaps(M, B, G, A, side, o, gaps);
  out.before = out.after = worstGap(gaps);
  if (out.before >= T) return out;  // already clear: the pose is not touched
  auto stage = [&](bool swing, float scale) {
    if (scale <= 0) return;
    pointGaps(M, B, G, A, side, o, gaps);
    std::vector<float> target(gaps.size());
    bool any = false;
    for (size_t i = 0; i < gaps.size(); ++i) {
      const float g = std::min(gaps[i].gap, T);
      target[i] = g + scale * (targetGap(g, o) - g);
      any |= gaps[i].gap < T;
    }
    if (!any) return;
    // The points that can take part: within 4 cm of their target at the stage start (a correction does not move the
    // arm further than that towards the body); the others keep their start gaps.
    std::vector<int> near;
    for (size_t i = 0; i < gaps.size(); ++i)
      if (gaps[i].gap < T + 0.04f) near.push_back(int(i));
    const float kh = swing ? 1.0f : keepHand;
    const vec3 sh0(G[size_t(A.upper)][3]), el0(G[size_t(A.fore)][3]), wr0(G[size_t(A.hand)][3]);
    const vec3 u = glm::length(wr0 - sh0) > 1e-6f ? glm::normalize(wr0 - sh0) : vec3(0, -1, 0);
    // Elbow hinge: the normal of the arm's plane, or the forearm's own x axis while the arm is nearly straight.
    vec3 hinge = glm::cross(el0 - sh0, wr0 - el0);
    {
      const float lu = glm::length(el0 - sh0) * glm::length(wr0 - el0);
      const float bend = lu > 1e-9f ? glm::length(hinge) / lu : 0.0f;  // sine of the elbow angle
      const vec3 boneX = glm::normalize(vec3(G[size_t(A.fore)][0]));
      const vec3 h = bend > 1e-6f ? hinge / (bend * lu) : boneX;
      const float k = std::clamp(bend / 0.2f, 0.0f, 1.0f);
      hinge = glm::normalize(k * h + (1 - k) * (glm::dot(boneX, h) < 0 ? -boneX : boneX));
    }
    // The pose along a path: swing angle about shoulder -> wrist (swing stage), or shoulder rotation vector + elbow
    // flexion (free stage); the hand keeps its world rotation as far as kh asks.
    struct Dof { vec3 shoulder{0}; float swing = 0, elbow = 0; };
    const Pose start = pose;
    const std::vector<mat4> G0 = G;
    const quat handWorld = rotationOf(G0[size_t(A.hand)]);
    const quat handLocal = start.local[size_t(A.hand)];
    auto apply = [&](const Dof& v, Pose& p, std::vector<mat4>& g) {
      p = start;
      g = G0;
      rotateBoneWorld(sk, g, world, A.upper, glm::angleAxis(v.swing, u) * fromRotationVector(v.shoulder), p);
      g = boneGlobals(sk, p, world);
      if (v.elbow != 0) {
        rotateBoneWorld(sk, g, world, A.fore, glm::angleAxis(v.elbow, hinge), p);
        g = boneGlobals(sk, p, world);
      }
      const quat kept = glm::normalize(glm::inverse(rotationOf(g[size_t(A.fore)])) * handWorld);
      p.local[size_t(A.hand)] = kh >= 1 ? kept : glm::normalize(glm::slerp(handLocal, kept, kh));
      g = boneGlobals(sk, p, world);
    };
    // The largest deficit (target - gap) over the points: continuous in the pose; <= 0 clears every point.
    auto maxDeficit = [&](const std::vector<PointGap>& pg) {
      float mx = -1e9f;
      for (size_t i = 0; i < pg.size(); ++i)
        if (pg[i].gap < 1e8f) mx = std::max(mx, target[i] - pg[i].gap);
      return mx;
    };
    Pose trial;
    std::vector<mat4> g;
    std::vector<PointGap> cur = gaps;
    Dof x;
    // Rounds: a direction (the deficit-weighted gradient of the points' gaps: the rotation that lifts the points below
    // their target fastest, the elbow weighted by its forearm share), then the smallest angle along it at which the soft maximum
    // deficit reaches 0 (Newton steps from 0, damped). Every quantity varies continuously with the pose.
    for (int round = 0; round < o.rounds; ++round) {
      float mx = -1e9f;
      for (size_t i = 0; i < cur.size(); ++i)
        if (cur[i].gap < 1e8f) mx = std::max(mx, target[i] - cur[i].gap);
      if (mx <= 1e-5f) break;
      apply(x, trial, g);
      const vec3 sh(g[size_t(A.upper)][3]), el(g[size_t(A.fore)][3]);
      // Direction: the deficit-weighted gradient of the points' gaps (the rotation that lifts the points below their
      // target fastest, the elbow weighted by its forearm share). The weights are the squared deficit (fading to 0 at
      // the target), so the direction does not flip when the deepest point changes.
      vec3 ds(0);
      float dt = 0, de = 0, wsum = 0;
      for (int i : near) {
        if (cur[size_t(i)].gap >= 1e8f) continue;
        const float dfc = target[size_t(i)] - cur[size_t(i)].gap + 0.0006f;
        if (dfc <= 0) continue;
        const float w = dfc * dfc;
        const ArmPoint& P = passPoints(A)[size_t(i)];
        const vec3 q = cur[size_t(i)].p, nrm = cur[size_t(i)].n;
        if (swing) dt += w * std::clamp(P.followUpper - P.followHand * kh, 0.0f, 1.0f) * glm::dot(u, glm::cross(q - sh, nrm));
        else {
          ds += w * P.followUpper * glm::cross(q - sh, nrm);
          de += w * P.followFore * glm::dot(hinge, glm::cross(q - el, nrm));
        }
        wsum += w;
      }
      if (wsum <= 0) break;
      Dof dir;
      if (swing) dir.swing = dt;
      else dir.shoulder = ds, dir.elbow = 0.5f * de;
      const float norm = std::sqrt(glm::dot(dir.shoulder, dir.shoulder) + dir.swing * dir.swing + dir.elbow * dir.elbow);
      if (norm < 1e-9f) break;
      dir.shoulder /= norm, dir.swing /= norm, dir.elbow /= norm;
      auto along = [&](float t) {
        Dof v = x;
        v.shoulder += t * dir.shoulder, v.elbow += t * dir.elbow;
        v.swing = std::clamp(v.swing + t * dir.swing, -o.maxSwing, o.maxSwing);
        return v;
      };
      std::vector<PointGap> pg = cur;
      auto D = [&](float t) {
        apply(along(t), trial, g);
        pointGaps(M, B, g, A, side, o, pg, &near);
        return maxDeficit(pg);
      };
      // Newton steps until the soft deficit crosses 0, then the crossing refined in its bracket (Illinois): the root
      // itself, not wherever a step happened to land.
      float t = 0, Dt = maxDeficit(cur);
      float lo = 0, Dlo = Dt, hi = -1, Dhi = 0;
      for (int it = 0; it < o.iterations && Dt > 1e-5f; ++it) {
        constexpr float h = 1e-3f;
        const float slope = (D(t + h) - Dt) / h;
        float stepT = slope > 1e-4f ? 1.2f * Dt / slope : o.maxStep;  // aim a little past the root to bracket it
        stepT = std::clamp(stepT, 0.0f, o.maxStep);
        if (t + stepT > o.maxAngle) stepT = o.maxAngle - t;
        if (stepT <= 1e-7f) break;
        const float tn = t + stepT, Dn = D(tn);
        if (Dn <= 0) {
          hi = tn, Dhi = Dn;
          break;
        }
        if (Dn >= Dt) {
          // The deficit stopped falling: a local minimum lies in [t - step, tn]. Stop there (golden section) and let the
          // next round's direction take the rest: the stop moves continuously with the pose, a jump to a later
          // crossing would not.
          float a = std::max(0.0f, t - stepT), b = tn;
          constexpr float g = 0.618034f;
          float c1 = b - g * (b - a), c2 = a + g * (b - a), f1 = D(c1), f2 = D(c2);
          for (int k = 0; k < 14 && b - a > 2e-5f; ++k) {
            if (f1 <= f2) b = c2, c2 = c1, f2 = f1, c1 = b - g * (b - a), f1 = D(c1);
            else a = c1, c1 = c2, f1 = f2, c2 = a + g * (b - a), f2 = D(c2);
          }
          const float tm = 0.5f * (a + b);
          if (D(tm) <= 0) hi = tm, Dhi = D(tm);  // the minimum already clears: refine the crossing before it
          else t = tm;
          break;
        }
        t = lo = tn, Dt = Dlo = Dn;
      }
      if (hi > 0) {
        int sideKept = 0;
        for (int it = 0; it < 16 && hi - lo > 1e-6f; ++it) {
          float m = (lo * Dhi - hi * Dlo) / (Dhi - Dlo);
          if (!(m > lo && m < hi)) m = 0.5f * (lo + hi);
          const float Dm = D(m);
          if (std::abs(Dm) < 2e-6f) { hi = m; break; }
          if (Dm > 0) {
            lo = m, Dlo = Dm;
            if (sideKept == 1) Dhi *= 0.5f;
            sideKept = 1;
          } else {
            hi = m, Dhi = Dm;
            if (sideKept == -1) Dlo *= 0.5f;
            sideKept = -1;
          }
        }
        t = hi;
      }
      if (t <= 0) break;
      x = along(t);
      apply(x, trial, g);
      pointGaps(M, B, g, A, side, o, cur, &near);
    }
    if (x.swing == 0 && x.elbow == 0 && x.shoulder == vec3(0)) return;
    apply(x, pose, G);
    out.changed = true;
  };
  stage(true, pin);
  stage(false, 1 - pin);
  pointGaps(M, B, G, A, side, o, gaps);
  out.after = worstGap(gaps);
  out.changed = true;
  return out;
}

// The post-pass is a pure function of (model, skeleton, world, side, pin, keepHand, pose, options), and an evaluation
// asks for the same frame's pose many times (interaction compiles, secondary motion, prop worlds): the result is
// memoised on the exact bytes of those inputs (per thread, bounded). Identical inputs give identical outputs, so this
// changes nothing but the time.
struct PassKey {
  std::vector<unsigned char> bytes;
  size_t hash = 0;
  bool operator==(const PassKey& k) const { return hash == k.hash && bytes == k.bytes; }
};
struct PassKeyHash {
  size_t operator()(const PassKey& k) const { return k.hash; }
};
struct PassValue {
  quat upper, fore, hand;
  ArmPostPassResult result;
};
template <class T>
void putBytes(std::vector<unsigned char>& b, const T& v) {
  const auto* p = reinterpret_cast<const unsigned char*>(&v);
  b.insert(b.end(), p, p + sizeof(T));
}
}  // namespace

ArmPostPassResult applyArmBodyClearance(const Skeleton& sk, const BodyClearanceModel& M, const mat4& world, char side,
                                        float pin, float keepHand, Pose& pose, const ArmPostPassOptions& o) {
  if (!M.valid) return {};
  const ArmModel& A = M.arm[side == 'L' ? 0 : 1];
  if (A.points.empty() || A.upper < 0 || A.fore < 0 || A.hand < 0) return {};
  thread_local std::unordered_map<PassKey, PassValue, PassKeyHash> cache;
  PassKey key;
  key.bytes.reserve(64 + pose.local.size() * sizeof(quat));
  putBytes(key.bytes, M.id), putBytes(key.bytes, &M), putBytes(key.bytes, &sk), putBytes(key.bytes, world), putBytes(key.bytes, side);
  putBytes(key.bytes, pin), putBytes(key.bytes, keepHand), putBytes(key.bytes, pose.rootOffset);
  putBytes(key.bytes, o.margin), putBytes(key.bytes, o.band), putBytes(key.bytes, o.armpit), putBytes(key.bytes, o.iterations), putBytes(key.bytes, o.rounds), putBytes(key.bytes, o.maxAngle);
  putBytes(key.bytes, o.maxStep), putBytes(key.bytes, o.maxSwing);
  key.bytes.insert(key.bytes.end(), reinterpret_cast<const unsigned char*>(pose.local.data()),
                   reinterpret_cast<const unsigned char*>(pose.local.data() + pose.local.size()));
  size_t h = 1469598103934665603ull;  // FNV-1a
  for (unsigned char c : key.bytes) h = (h ^ c) * 1099511628211ull;
  key.hash = h;
  if (auto it = cache.find(key); it != cache.end()) {
    pose.local[size_t(A.upper)] = it->second.upper;
    pose.local[size_t(A.fore)] = it->second.fore;
    pose.local[size_t(A.hand)] = it->second.hand;
    return it->second.result;
  }
  const ArmPostPassResult r = armPostPass(sk, M, world, side, pin, keepHand, pose, o);
  if (cache.size() >= 8192) cache.clear();
  cache.emplace(std::move(key), PassValue{pose.local[size_t(A.upper)], pose.local[size_t(A.fore)], pose.local[size_t(A.hand)], r});
  return r;
}

namespace {

double num(const Json& j, const char* k, double fallback) {
  auto it = j.find(k);
  return (it != j.end() && it->is_number()) ? it->get<double>() : fallback;
}
std::string str(const Json& j, const char* k, const std::string& fallback = {}) {
  auto it = j.find(k);
  return (it != j.end() && it->is_string()) ? it->get<std::string>() : fallback;
}
bool flag(const Json& j, const char* k, bool fallback) {
  auto it = j.find(k);
  return (it != j.end() && it->is_boolean()) ? it->get<bool>() : fallback;
}
std::optional<vec3> vecOpt(const Json& j, const char* k) {
  auto it = j.find(k);
  if (it == j.end() || !it->is_array() || it->size() != 3) return std::nullopt;
  for (const auto& x : *it)
    if (!x.is_number()) return std::nullopt;
  return vec3((*it)[0].get<float>(), (*it)[1].get<float>(), (*it)[2].get<float>());
}
void key(Clip& c, const std::string& track, double f, vec3 v, Interp in = Interp::Smooth) {
  c.tracks[track].setKey({f, v, in});
}
void dropKeysAfter(Clip& c, const std::string& track, double f) {
  auto it = c.tracks.find(track);
  if (it == c.tracks.end()) return;
  auto& k = it->second.keys;
  k.erase(std::remove_if(k.begin(), k.end(), [&](const Key& x) { return x.frame > f; }), k.end());
}
char sideOf(const Json& a, const char* k) {
  const std::string s = str(a, k, "R");
  return !s.empty() && (s[0] == 'L' || s[0] == 'l') ? 'L' : 'R';
}

// Where a hand closes on a prop, in the prop's local frame (metres): the grasp centre (on the object's axis or
// mid-plane next to the socket), the inward direction (from the socket into the object), the cylinder axis (zero for
// a sphere-like grasp) and the radius the fingers close on. Primitive cylinders stand on their base at the origin
// along +Y; boxes and spheres are centred (docs/ASSET_LIBRARY.md).
struct GraspShape {
  vec3 centre{0}, inward{0, -1, 0}, axis{0}, middle{0};
  float radius = 0.03f;
};

GraspShape graspShape(const PropAsset& asset, vec3 s) {
  enum class Kind { Box, Sphere, Cylinder } kind = Kind::Sphere;
  vec3 size(0.06f);
  float radius = 0.03f, y0 = 0, y1 = 0;
  mat4 frame(1);  // proxy frame inside the prop
  const float k = asset.scaleMetres > 0 ? asset.scaleMetres : 1.0f;
  if (asset.mesh.kind == AssetMeshSource::Kind::Primitive) {
    using P = AssetMeshSource::Primitive;
    kind = asset.mesh.primitive == P::Box ? Kind::Box : asset.mesh.primitive == P::Sphere ? Kind::Sphere : Kind::Cylinder;
    size = asset.mesh.size * k;
    radius = asset.mesh.radius * k;
    y0 = 0;
    y1 = asset.mesh.height * k;
  } else if (asset.collision) {
    using T = AssetCollisionProxy::Type;
    const auto& c = *asset.collision;
    kind = c.type == T::Box ? Kind::Box : c.type == T::Sphere ? Kind::Sphere : Kind::Cylinder;
    size = c.size;
    radius = c.radius;
    y0 = -0.5f * c.height;  // capsules are centred
    y1 = 0.5f * c.height;
    frame = assetTransformMatrix(c.transform);
  }
  const mat4 inv = glm::inverse(frame);
  const vec3 p = vec3(inv * vec4(s, 1));
  GraspShape g;
  switch (kind) {
    case Kind::Cylinder: {
      const vec3 radial(p.x, 0, p.z);
      g.middle = vec3(0, 0.5f * (y0 + y1), 0);
      if (glm::length(radial) >= 0.5f * radius && p.y >= y0 - 1e-4f && p.y <= y1 + 1e-4f) {
        g.centre = vec3(0, std::clamp(p.y, y0, y1), 0);
        g.inward = -glm::normalize(radial);
        g.axis = vec3(0, 1, 0);
        g.radius = radius;
      } else {  // on a cap: a sphere-like grasp across the cap
        g.inward = vec3(0, p.y > g.middle.y ? -1.0f : 1.0f, 0);
        g.centre = vec3(p.x, g.middle.y, p.z);
        g.radius = std::min(radius, 0.5f * (y1 - y0));
      }
      break;
    }
    case Kind::Box: {
      const vec3 half = 0.5f * glm::max(size, vec3(1e-5f));
      const vec3 r = glm::abs(p) / half;
      const int i = r.x >= r.y && r.x >= r.z ? 0 : r.y >= r.z ? 1 : 2;
      vec3 out(0);
      out[i] = p[i] >= 0 ? 1.0f : -1.0f;
      g.inward = -out;
      g.centre = p;
      g.centre[i] = 0;
      g.radius = half[i];
      break;
    }
    case Kind::Sphere:
      g.inward = glm::length(p) > 1e-6f ? -glm::normalize(p) : vec3(0, -1, 0);
      g.radius = radius;
      break;
  }
  g.centre = vec3(frame * vec4(g.centre, 1));
  g.middle = vec3(frame * vec4(g.middle, 1));
  g.inward = glm::normalize(vec3(frame * vec4(g.inward, 0)));
  if (glm::length(g.axis) > 0) g.axis = glm::normalize(vec3(frame * vec4(g.axis, 0)));
  return g;
}

// Moves a wrist key at frame f until `error()` (target - measured) is below 0.3 mm: the arm solve, the life layer and
// clip layers make the first estimate a little off. Keeps the best key and stops when a step no longer helps (a
// target out of reach), so the key never runs away. Returns the remaining error.
template <class F>
float correctKey(Track& track, double f, F error) {
  Key* key = nullptr;
  for (auto& k : track.keys)
    if (std::abs(k.frame - f) < 1e-6) key = &k;
  vec3 d = error();
  float e = glm::length(d);
  if (!key) return e;
  vec3 best = key->value;
  float bestE = e;
  for (int it = 0; it < 12 && bestE >= 0.0003f; ++it) {
    key->value = best + d;
    d = error();
    e = glm::length(d);
    if (e >= bestE) break;
    best = key->value;
    bestE = e;
  }
  key->value = best;
  return bestE;
}

constexpr vec3 kUp(0, 1, 0);
const vec3 kRelaxed(0.25f, 0.15f, 0), kOpen(0.03f, 0.05f, 0.35f);

}  // namespace

vec3 SceneEvaluator::handGripPoint(size_t c, char side, double frame) const {
  const int hb = characterSocketBone(c, std::string("hand.") + side);
  if (hb < 0) return vec3(0);
  const HandGrip g = handGrip(characters_[c].asset.skeleton, hb, side);
  return vec3(characterGlobals(c, frame)[size_t(hb)] * vec4(g.palm, 1));
}

Result<bool> SceneEvaluator::compileInteraction(const Json& a, Clip& gen, InteractionContext& ctx) {
  const std::string type = str(a, "type");
  const bool reach = (type == "reach" || type == "grasp") && a.contains("prop");
  if (type == "grasp" && !a.contains("prop")) return fail("grasp: give 'prop' (a scene prop instance)");
  if (!reach && type != "hold" && type != "place" && type != "handover") return false;
  const Clip& clip = scene_.animation;

  auto charIndex = [&](const std::string& n) -> int {
    for (size_t c = 0; c < scene_.characters.size(); ++c)
      if (scene_.characters[c].name == n) return int(c);
    return -1;
  };
  auto propIndex = [&](const std::string& n) -> int {
    for (size_t p = 0; p < scene_.props.size(); ++p)
      if (scene_.props[p].name == n) return int(p);
    return -1;
  };

  struct Hand {
    int c = -1;
    char side = 'R';
    int bone = -1, mid = -1, root = -1;
    std::string who, prefix, ik, orient, pose;
    HandGrip grip;
    float armLength = 0;
  };
  auto handOf = [&](int c, char side, const std::string& what) -> Result<Hand> {
    Hand h;
    h.c = c;
    h.side = side;
    h.bone = characterSocketBone(size_t(c), std::string("hand.") + side);
    const Skeleton& sk = characters_[size_t(c)].asset.skeleton;
    if (h.bone >= 0) h.mid = sk.bones[size_t(h.bone)].parent;
    if (h.mid >= 0) h.root = sk.bones[size_t(h.mid)].parent;
    h.who = scene_.characters[size_t(c)].name;
    if (h.root < 0) return fail(std::format("{}: character '{}' has no hand.{} arm chain", what, h.who, side));
    h.prefix = h.who + "/";
    h.ik = h.prefix + "ik." + sk.bones[size_t(h.bone)].name;
    h.orient = h.prefix + "orient." + sk.bones[size_t(h.bone)].name;
    h.pose = h.prefix + "hand." + side;
    h.grip = handGrip(sk, h.bone, side);
    const auto& B = sk.bones;
    h.armLength = glm::distance(B[size_t(h.root)].head, B[size_t(h.mid)].head) + glm::distance(B[size_t(h.mid)].head, B[size_t(h.bone)].head);
    return h;
  };
  auto boneAt = [&](const Hand& h, int bone, double f) { return vec3(characterGlobals(size_t(h.c), f)[size_t(bone)][3]); };
  auto socketWorld = [&](int p, const std::string& socket, double f) {
    return propWorld(size_t(p), f) * assetTransformMatrix(propAssets_[size_t(p)].sockets.at(socket));
  };
  auto propMiddle = [&](int p, double f) {
    return vec3(propWorld(size_t(p), f) * vec4(graspShape(propAssets_[size_t(p)], vec3(0)).middle, 1));
  };
  auto requireSocket = [&](int p, const std::string& socket, const std::string& what) -> Result<void> {
    if (!propAssets_[size_t(p)].sockets.count(socket))
      return fail(std::format("{}: prop '{}' (asset '{}') has no socket '{}'", what, scene_.props[size_t(p)].name,
                              propAssets_[size_t(p)].id, socket));
    return {};
  };
  auto addSwitch = [&](int p, double f, std::optional<PropParent> parent, const std::string& what) -> Result<void> {
    auto& sw = scene_.props[size_t(p)].parentSwitch;
    for (const auto& e : sw)
      if (e.frame == f) return fail(std::format("{}: prop '{}' already switches parent at frame {}", what, scene_.props[size_t(p)].name, f));
    sw.push_back({f, std::move(parent)});
    std::stable_sort(sw.begin(), sw.end(), [](const PropParentSwitch& x, const PropParentSwitch& y) { return x.frame < y.frame; });
    key(gen, scene_.props[size_t(p)].name + ".parent.weight", f, vec3(1), Interp::Step);  // explicit: fully attached
    return {};
  };
  // Moves the wrist key at frame f until `error()` (target - measured) is below 0.3 mm (the arm solve, life layer
  // and clip layers make the first estimate a little off).
  auto correct = [&](const Hand& h, double f, auto error) { return correctKey(gen.tracks[h.ik], f, error); };
  auto warnReach = [&](const Hand& h, vec3 wrist, double f, const std::string& what) {
    const float d = glm::distance(boneAt(h, h.root, f), wrist) - 0.98f * h.armLength;
    if (d > 0.005f)
      warnings_.push_back(std::format("{}: '{}' cannot reach with hand.{} at frame {} ({:.0f} mm short); move them closer",
                                      what, h.who, h.side, f, d * 1000));
  };
  auto gazeOn = [&](const Hand& h, int p, double from, double to) {
    const std::string track = h.prefix + "lookAt";
    const vec3 prev = clip.evaluate(track, from - 4, propMiddle(p, from));
    dropKeysAfter(gen, track, from - 4);
    key(gen, track, from - 4, prev, Interp::Linear);
    for (double f = from; f < to; f += 3) key(gen, track, f, propMiddle(p, f), Interp::Linear);
    key(gen, track, to, propMiddle(p, to), Interp::Linear);
  };
  auto gazeAt = [&](const Hand& h, vec3 target, double f) { key(gen, h.prefix + "lookAt", f, target, Interp::Linear); };
  auto forwardPoint = [&](const Hand& h, double f) {  // a point ahead of the character at eye height
    const CharacterDesc& cd = scene_.characters[size_t(h.c)];
    const vec3 pos = clip.evaluate(cd.name + ".position", f, cd.position);
    const float yaw = glm::radians(clip.evaluate(cd.name + ".yaw", f, vec3(cd.yawDeg)).x);
    const int head = characterSocketBone(size_t(h.c), "head");
    const float y = head >= 0 ? vec3(characterGlobals(size_t(h.c), f)[size_t(head)][3]).y + 0.05f : pos.y + 0.6f;
    return vec3(pos.x + 2.0f * std::sin(yaw), y, pos.z + 2.0f * std::cos(yaw));
  };
  auto headPoint = [&](int c, double f) {
    const int head = characterSocketBone(size_t(c), "head");
    if (head < 0) return vec3(scene_.characters[size_t(c)].position + vec3(0, 0.6f, 0));
    return vec3(characterGlobals(size_t(c), f)[size_t(head)] * vec4(0, 0.06f, 0.04f, 1));
  };

  // Grasp plan at frame f: the hand's world orientation (palm towards the prop, fingers away from the body, thumb
  // along the prop's axis), the wrist position that puts the palm point on the socket, and the grasp sphere/cylinder
  // in the hand's rest frame.
  struct Plan {
    quat orient{1, 0, 0, 0};
    mat3 R{1};
    vec3 wrist{0}, socket{0}, inward{0, 0, 1}, centre{0}, axis{0};
    float radius = 0.03f;
  };
  auto plan = [&](const Hand& h, int p, const std::string& socket, double f) {
    const mat4 P = propWorld(size_t(p), f);
    const AssetTransform& st = propAssets_[size_t(p)].sockets.at(socket);
    const GraspShape gs = graspShape(propAssets_[size_t(p)], st.translation);
    const mat3 PR(P);
    Plan pl;
    pl.socket = vec3(P * vec4(st.translation, 1));
    const vec3 n = glm::normalize(PR * gs.inward);
    const vec3 centreW = vec3(P * vec4(gs.centre, 1));
    const vec3 axisW = glm::length(gs.axis) > 0 ? glm::normalize(PR * gs.axis) : vec3(0);
    pl.radius = gs.radius * glm::length(vec3(P[0]));
    const vec3 out = pl.socket - boneAt(h, h.root, f);
    const float sgn = h.side == 'R' ? 1.0f : -1.0f;  // thumb = sgn * (fingers x palm normal)
    vec3 d, t;
    if (glm::length(axisW) > 0 && std::abs(glm::dot(axisW, n)) < 0.95f) {
      t = axisW * (axisW.y >= 0 ? 1.0f : -1.0f);
      t = glm::normalize(t - n * glm::dot(t, n));
      d = sgn * glm::cross(n, t);
      if (glm::dot(d, out) < 0) d = -d, t = -t;  // fingers never point back at the body
    } else {
      vec3 o = out - n * glm::dot(out, n);
      if (glm::length(o) < 1e-4f) o = glm::cross(n, std::abs(n.y) < 0.9f ? kUp : vec3(1, 0, 0));
      d = glm::normalize(o);
      t = sgn * glm::cross(d, n);
    }
    const mat3 W(d, n, glm::cross(d, n));
    const mat3 B(h.grip.fingerDir, h.grip.palmNormal, glm::cross(h.grip.fingerDir, h.grip.palmNormal));
    pl.R = W * glm::transpose(B);
    pl.orient = glm::normalize(glm::quat_cast(pl.R));
    pl.R = glm::mat3_cast(pl.orient);
    pl.wrist = pl.socket - pl.R * h.grip.palm;
    pl.inward = n;
    pl.centre = glm::transpose(pl.R) * (centreW - pl.wrist);
    pl.axis = glm::length(axisW) > 0 ? glm::transpose(pl.R) * axisW : vec3(0);
    return pl;
  };
  // Reach + grasp of `socket` on prop p, arriving at `contact` (shared by reach/grasp and the hand-over receiver).
  auto reachTo = [&](const Hand& h, int p, const std::string& socket, double start, double contact, bool grasp,
                     const std::string& what) -> Result<Plan> {
    if (contact < start + 6) return fail(std::format("{}: contact must be at least 6 frames after start", what));
    Plan pl = plan(h, p, socket, contact);
    const vec3 natural = boneAt(h, h.bone, start);
    const vec3 approach = pl.wrist - pl.inward * 0.05f + kUp * 0.02f;
    const double pre = contact - std::min(6.0, 0.4 * (contact - start));
    warnReach(h, pl.wrist, contact, what);
    key(gen, h.ik, start, clip.evaluate(h.ik + ".weight", start, vec3(0)).x > 0 ? clip.evaluate(h.ik, start, natural) : natural);
    key(gen, h.ik, pre, approach);
    key(gen, h.ik, contact, pl.wrist);
    key(gen, h.ik + ".weight", start, vec3(clip.evaluate(h.ik + ".weight", start, vec3(0)).x));
    key(gen, h.ik + ".weight", pre, vec3(1));
    key(gen, h.ik + ".weight", contact, vec3(1));
    key(gen, h.orient, start, rotationVector(pl.orient), Interp::Linear);
    key(gen, h.orient, contact, rotationVector(pl.orient), Interp::Linear);
    key(gen, h.orient + ".weight", start, vec3(clip.evaluate(h.orient + ".weight", start, vec3(0)).x));
    key(gen, h.orient + ".weight", pre + 1, vec3(1));
    key(gen, h.orient + ".weight", contact, vec3(1));
    key(gen, h.pose, start, clip.evaluate(h.pose, start, kRelaxed));
    key(gen, h.pose, pre, kOpen);
    key(gen, h.pose, contact, kOpen);
    if (grasp) {  // fingers close on the prop's size by contact search (anim: applyHandPose)
      key(gen, h.pose + ".grasp", start, pl.centre, Interp::Step);
      key(gen, h.pose + ".graspRadius", start, vec3(pl.radius), Interp::Step);
      key(gen, h.pose + ".graspAxis", start, pl.axis, Interp::Step);
      key(gen, h.pose + ".grasp.weight", start, vec3(0));
      key(gen, h.pose + ".grasp.weight", contact - 4, vec3(0));
      key(gen, h.pose + ".grasp.weight", contact, vec3(1));
    }
    correct(h, contact, [&] { return socketWorld(p, socket, contact)[3] - vec4(handGripPoint(size_t(h.c), h.side, contact), 1); });
    return pl;
  };
  // Lets go: fingers open, the wrist backs away from the prop and the arm returns to its own animation by `end`.
  auto release = [&](const Hand& h, const quat& orient, double from, double end, vec3 retreat) {
    const vec3 wrist = clip.evaluate(h.ik, from, vec3(0));
    key(gen, h.pose + ".grasp.weight", from, vec3(1));
    key(gen, h.pose + ".grasp.weight", from + 5, vec3(0));
    key(gen, h.pose, from, kOpen);
    key(gen, h.pose, from + 3, kOpen);
    key(gen, h.pose, end, kRelaxed);
    key(gen, h.ik, from + 1, wrist);
    key(gen, h.ik, std::max(from + 6, end - 4), wrist + retreat);
    key(gen, h.ik, end, wrist + retreat);
    key(gen, h.ik + ".weight", from + 1, vec3(1));
    key(gen, h.ik + ".weight", end, vec3(0));
    key(gen, h.orient, end, rotationVector(orient), Interp::Linear);
    key(gen, h.orient + ".weight", from + 1, vec3(1));
    key(gen, h.orient + ".weight", end, vec3(0));
  };
  auto held = [&](const Hand& h, const std::string& what) -> Result<int> {
    auto it = ctx.hands.find({h.c, h.side});
    const int p = it == ctx.hands.end() ? -1 : it->second.prop;
    if (p < 0) return fail(std::format("{}: '{}' holds nothing in hand.{} at this point", what, h.who, h.side));
    if (a.contains("prop") && str(a, "prop") != scene_.props[size_t(p)].name)
      return fail(std::format("{}: '{}' holds '{}', not '{}'", what, h.who, scene_.props[size_t(p)].name, str(a, "prop")));
    return p;
  };

  if (!ctx.parentsChecked) {  // props are evaluated while compiling: their authored parents must resolve first
    for (const PropDesc& prop : scene_.props) {
      std::vector<PropParent> parents;
      if (prop.parent) parents.push_back(*prop.parent);
      for (const auto& sw : prop.parentSwitch)
        if (sw.parent) parents.push_back(*sw.parent);
      for (const PropParent& pp : parents) {
        const bool ok = pp.kind == PropParent::Kind::Character
                            ? charIndex(pp.name) >= 0 && characterSocketBone(size_t(charIndex(pp.name)), pp.socket) >= 0
                            : propIndex(pp.name) >= 0 && propAssets_[size_t(propIndex(pp.name))].sockets.count(pp.socket) > 0;
        if (!ok) return fail(std::format("prop '{}': parent '{}' socket '{}' does not resolve", prop.name, pp.name, pp.socket));
      }
    }
    ctx.parentsChecked = true;
  }
  const std::string who = str(a, "character");
  const int c = charIndex(who);
  if (c < 0) return fail(std::format("{}: unknown character '{}'", type, who));
  const double start = num(a, "start", num(a, "frame", 0));
  const bool look = flag(a, "look", true);
  auto h0 = handOf(c, sideOf(a, "hand"), type);
  if (!h0) return std::unexpected(h0.error());
  const Hand& h = *h0;

  if (reach) {
    const std::string what = std::format("{} '{}'", type, str(a, "prop"));
    const int p = propIndex(str(a, "prop"));
    if (p < 0) return fail(std::format("{}: unknown prop '{}'", type, str(a, "prop")));
    const std::string socket = str(a, "socket", "grip");
    if (auto r = requireSocket(p, socket, what); !r) return std::unexpected(r.error());
    if (auto it = ctx.hands.find({c, h.side}); it != ctx.hands.end() && it->second.prop >= 0)
      return fail(std::format("{}: '{}' already holds '{}' in hand.{}", what, who, scene_.props[size_t(it->second.prop)].name, h.side));
    const double contact = num(a, "contact", start + 14);
    const bool grasp = flag(a, "grasp", true);
    auto pl = reachTo(h, p, socket, start, contact, grasp, what);
    if (!pl) return std::unexpected(pl.error());
    ctx.contacts.push_back({c, h.side, contact, p, socket, false, vec3(0)});
    if (grasp) {
      if (auto r = addSwitch(p, contact, PropParent{PropParent::Kind::Character, who, std::string("hand.") + h.side}, what); !r)
        return std::unexpected(r.error());
      ctx.hands[{c, h.side}] = {p, pl->orient};
      if (look) gazeOn(h, p, start, contact + 8);
    } else {
      const double end = num(a, "end", contact + 12);
      key(gen, h.ik, contact + 2, clip.evaluate(h.ik, contact, vec3(0)));
      release(h, pl->orient, contact + 2, std::max(end, contact + 10), -pl->inward * 0.05f + kUp * 0.02f);
      if (look) {
        gazeOn(h, p, start, contact + 6);
        gazeAt(h, forwardPoint(h, end), end + 6);
      }
    }
    return true;
  }

  if (type == "hold") {
    auto p = held(h, "hold");
    if (!p) return std::unexpected(p.error());
    const double end = num(a, "end", start + 16);
    if (end <= start) return fail("hold: end must be after start");
    const quat orient = ctx.hands[{c, h.side}].orient;
    const vec3 origin = vec3(propWorld(size_t(*p), start)[3]);
    const auto at = vecOpt(a, "at"), by = vecOpt(a, "by");
    const vec3 target = at ? *at : origin + (by ? *by : vec3(0));
    const vec3 wrist = clip.evaluate(h.ik, start, vec3(0));
    key(gen, h.ik, start, wrist);
    key(gen, h.ik, end, wrist + (target - origin));
    key(gen, h.ik + ".weight", end, vec3(1));
    key(gen, h.orient, end, rotationVector(orient), Interp::Linear);
    key(gen, h.orient + ".weight", end, vec3(1));
    warnReach(h, wrist + (target - origin), end, "hold");
    correct(h, end, [&] { return target - vec3(propWorld(size_t(*p), end)[3]); });
    if (look) gazeOn(h, *p, start, end);
    return true;
  }

  if (type == "place") {
    auto p = held(h, "place");
    if (!p) return std::unexpected(p.error());
    const std::string socket = str(a, "socket", "place");
    if (auto r = requireSocket(*p, socket, "place"); !r) return std::unexpected(r.error());
    const double contact = num(a, "contact", start + 16), end = num(a, "end", contact + 14);
    if (contact < start + 6 || end < contact + 8) return fail("place: needs contact >= start + 6 and end >= contact + 8");
    std::optional<PropParent> onto;
    vec3 target(0);
    if (auto it = a.find("onto"); it != a.end() && it->is_object()) {
      const int q = propIndex(str(*it, "prop"));
      const std::string s = str(*it, "socket", "place");
      if (q < 0) return fail(std::format("place: unknown prop '{}' in onto", str(*it, "prop")));
      if (auto r = requireSocket(q, s, "place onto"); !r) return std::unexpected(r.error());
      onto = PropParent{PropParent::Kind::Prop, scene_.props[size_t(q)].name, s};
      target = vec3(socketWorld(q, s, contact)[3]);
    } else if (auto at = vecOpt(a, "at")) {
      target = *at;
    } else {
      return fail("place: give 'at' [x,y,z] or 'onto' {prop, socket}");
    }
    const quat orient = ctx.hands[{c, h.side}].orient;
    const vec3 wrist = clip.evaluate(h.ik, start, vec3(0));
    const vec3 wristC = wrist + (target - vec3(socketWorld(*p, socket, start)[3]));
    key(gen, h.ik, start, wrist);
    key(gen, h.ik, contact - 5, wristC + kUp * 0.03f);
    key(gen, h.ik, contact, wristC);
    key(gen, h.ik + ".weight", contact, vec3(1));
    key(gen, h.orient, contact, rotationVector(orient), Interp::Linear);
    key(gen, h.orient + ".weight", contact, vec3(1));
    warnReach(h, wristC, contact, "place");
    correct(h, contact, [&] { return target - vec3(socketWorld(*p, socket, contact)[3]); });
    if (auto r = addSwitch(*p, contact, onto, "place"); !r) return std::unexpected(r.error());
    ctx.contacts.push_back({c, h.side, contact, *p, socket, true, target});
    ctx.hands[{c, h.side}].prop = -1;
    release(h, orient, contact, end, -(glm::mat3_cast(orient) * h.grip.palmNormal) * 0.05f + kUp * 0.03f);
    if (look) {
      gazeOn(h, *p, start, contact + 6);
      gazeAt(h, forwardPoint(h, end), end + 6);
    }
    return true;
  }

  // handover
  const std::string to = str(a, "to");
  const int rc = charIndex(to);
  if (rc < 0) return fail(std::format("handover: unknown receiver '{}'", to));
  auto r0 = handOf(rc, sideOf(a, "toHand"), "handover");
  if (!r0) return std::unexpected(r0.error());
  const Hand& r = *r0;
  if (rc == c && r.side == h.side) return fail("handover: the receiving hand is the giving hand");
  auto p = held(h, "handover");
  if (!p) return std::unexpected(p.error());
  if (auto it = ctx.hands.find({rc, r.side}); it != ctx.hands.end() && it->second.prop >= 0)
    return fail(std::format("handover: '{}' already holds '{}' in hand.{}", to, scene_.props[size_t(it->second.prop)].name, r.side));
  const std::string toSocket = str(a, "toSocket", "grip_b");
  if (auto rs = requireSocket(*p, toSocket, "handover"); !rs) return std::unexpected(rs.error());
  const double contact = num(a, "contact", start + 18), rStart = num(a, "receiverStart", start + 4);
  const double rel = num(a, "release", contact + 4), end = num(a, "end", rel + 12);
  if (contact < start + 6 || contact < rStart + 6 || rel < contact + 1 || end < rel + 8)
    return fail("handover: needs contact >= start + 6, contact >= receiverStart + 6, release > contact, end >= release + 8");
  // Giver: brings the prop to the meeting point a little before contact and holds it still until it lets go.
  const quat gOrient = ctx.hands[{c, h.side}].orient;
  const vec3 origin = vec3(propWorld(size_t(*p), start)[3]);
  vec3 meet;
  if (auto at = vecOpt(a, "at")) {
    meet = *at;
  } else {
    meet = 0.5f * (boneAt(h, h.root, contact) + boneAt(r, r.root, contact)) - kUp * (0.35f * h.armLength);
  }
  const vec3 wrist = clip.evaluate(h.ik, start, vec3(0));
  const double still = contact - std::min(4.0, 0.3 * (contact - start));
  const std::string what = std::format("handover '{}' to '{}'", scene_.props[size_t(*p)].name, to);
  vec3 wristM(0);
  // Giver brings the prop to `meet` and holds it still; the receiver reaches its socket there (compiled together,
  // so the meeting point can move).
  auto meetAt = [&](vec3 m) -> Result<Plan> {
    wristM = wrist + (m - origin);
    key(gen, h.ik, start, wrist);
    key(gen, h.ik, still, wristM);
    key(gen, h.ik, contact, wristM);
    key(gen, h.ik + ".weight", contact, vec3(1));
    key(gen, h.orient, contact, rotationVector(gOrient), Interp::Linear);
    key(gen, h.orient + ".weight", contact, vec3(1));
    correct(h, still, [&] { return m - vec3(propWorld(size_t(*p), still)[3]); });
    for (auto& k : gen.tracks[h.ik].keys)  // still means still: contact repeats the corrected meeting key
      if (std::abs(k.frame - contact) < 1e-6) k.value = clip.evaluate(h.ik, still, wristM);
    return reachTo(r, *p, toSocket, rStart, contact, true, what);
  };
  // T-030: the meeting point must leave both arms (forearm and hand surface) outside their own bodies and within
  // both reaches. Candidates on a grid around the requested point (3 cm steps, then 1 cm steps around the best); the
  // closest one that keeps both arms at the margin wins, else the one with the largest clearance (the depth left is
  // reported).
  auto shortfall = [&](const Hand& x, vec3 target) {
    return glm::distance(boneAt(x, x.root, contact), target) - 0.98f * x.armLength;
  };
  auto score = [&](vec3 m) -> Result<float> {
    auto pl = meetAt(m);
    if (!pl) return std::unexpected(pl.error());
    const float sg = shortfall(h, wristM), sr = shortfall(r, pl->wrist);
    if (std::max(sg, sr) > 0.003f) return -1.0f - std::max(sg, sr);  // out of reach: never chosen over a reachable point
    const float g = armClearance(clearance_[size_t(c)], characterGlobals(size_t(c), contact), h.side).gap;
    const float q = armClearance(clearance_[size_t(rc)], characterGlobals(size_t(rc), contact), r.side).gap;
    return std::min(g, q);
  };
  const bool canClear = c < int(clearance_.size()) && rc < int(clearance_.size()) && clearance_[size_t(c)].valid &&
                        clearance_[size_t(rc)].valid;
  if (canClear) {
    const size_t warningsBefore = warnings_.size();  // trial reaches report nothing
    if (auto pl = meetAt(meet); !pl) return std::unexpected(pl.error());
    writeArmPole(gen, size_t(c), h.side);  // poles first: the elbows they set are part of the clearance
    writeArmPole(gen, size_t(rc), r.side);
    const vec3 across = glm::normalize(vec3(boneAt(r, r.root, contact) - boneAt(h, h.root, contact)) * vec3(1, 0, 1));
    const vec3 side = glm::cross(kUp, across);
    const vec3 asked = meet;
    vec3 best = asked;
    float bestScore = -1e9f, bestDist = 1e9f;
    auto consider = [&](vec3 m) -> Result<void> {
      auto sc = score(m);
      if (!sc) return std::unexpected(sc.error());
      const float d = glm::distance(m, asked);
      const bool clear = *sc >= kArmBodyMargin - 0.0005f, bestClear = bestScore >= kArmBodyMargin - 0.0005f;
      if ((clear && (!bestClear || d < bestDist)) || (!clear && !bestClear && *sc > bestScore))
        best = m, bestScore = *sc, bestDist = d;
      return {};
    };
    for (int i = -4; i <= 4; ++i)  // coarse: 3 cm steps, +-12 cm across and sideways, +-9 cm up and down
      for (int j = -4; j <= 4; ++j)
        for (int k = -3; k <= 3; ++k)
          if (auto e = consider(asked + across * (0.03f * float(i)) + side * (0.03f * float(j)) + kUp * (0.03f * float(k))); !e)
            return std::unexpected(e.error());
    const vec3 coarse = best;
    for (int i = -2; i <= 2; ++i)  // fine: 1 cm steps around the best coarse point
      for (int j = -2; j <= 2; ++j)
        for (int k = -2; k <= 2; ++k)
          if (auto e = consider(coarse + across * (0.01f * float(i)) + side * (0.01f * float(j)) + kUp * (0.01f * float(k))); !e)
            return std::unexpected(e.error());
    meet = best;
    warnings_.resize(warningsBefore);
    if (bestScore < 0)
      warnings_.push_back(std::format("{}: no meeting point keeps both arms outside the bodies ({:.0f} mm inside); move them apart",
                                      what, -bestScore * 1000));
  }
  auto pl = meetAt(meet);
  if (!pl) return std::unexpected(pl.error());
  warnReach(h, wristM, contact, "handover (giver)");
  ctx.frozen.push_back({c, h.side, still, rel});  // the giver holds still: the clearance pass leaves it there
  if (auto rs = addSwitch(*p, contact, PropParent{PropParent::Kind::Character, to, std::string("hand.") + r.side}, what); !rs)
    return std::unexpected(rs.error());
  ctx.contacts.push_back({rc, r.side, contact, *p, toSocket, false, vec3(0)});
  ctx.hands[{rc, r.side}] = {*p, pl->orient};
  ctx.hands[{c, h.side}].prop = -1;
  // Giver lets go after the receiver holds it and draws the hand back towards its own shoulder.
  key(gen, h.ik, rel, clip.evaluate(h.ik, contact, wristM));
  key(gen, h.ik + ".weight", rel, vec3(1));
  key(gen, h.orient, rel, rotationVector(gOrient), Interp::Linear);
  key(gen, h.orient + ".weight", rel, vec3(1));
  const vec3 back = boneAt(h, h.root, rel) - wristM;
  release(h, gOrient, rel, end, glm::normalize(back) * 0.08f - (glm::mat3_cast(gOrient) * h.grip.palmNormal) * 0.03f);
  if (look) {
    gazeOn(h, *p, start, rel);
    gazeAt(h, headPoint(rc, end), end);
    gazeOn(r, *p, rStart, contact + 8);
  }
  return true;
}

void SceneEvaluator::buildClearanceModels() {
  clearance_.clear();
  for (const auto& ci : characters_) clearance_.push_back(bodyClearanceModel(ci.asset.skeleton, ci.rig.meshes));
}

// Elbow pole of an IK-driven arm, per frame over the scene: out of the body (the character's side, down and a little
// back, in the chest frame), weighted by the arm's IK weight so it fades with the IK and leaves the clip arm alone.
void SceneEvaluator::writeArmPole(Clip& gen, size_t c, char side) {
  const Skeleton& sk = characters_[c].asset.skeleton;
  const int hand = characterSocketBone(c, std::string("hand.") + side), chest = sk.find("chest");
  if (hand < 0 || chest < 0) return;
  const std::string who = scene_.characters[c].name, ik = who + "/ik." + sk.bones[size_t(hand)].name;
  const std::string pole = who + "/pole." + sk.bones[size_t(hand)].name;
  if (!gen.find(ik)) return;
  const float out = side == 'L' ? 1.0f : -1.0f;  // engine +X is the character's left
  gen.tracks.erase(pole);
  gen.tracks.erase(pole + ".weight");  // the chest frame below is the pose without this arm's pole
  std::vector<Key> dir, wt;
  for (int f = scene_.frameStart - 1; f <= scene_.frameEnd + 1; ++f) {
    const mat4 Gc = characterGlobals(c, f)[size_t(chest)];
    const vec3 X = glm::normalize(vec3(Gc[0])), Y = glm::normalize(vec3(Gc[1])), Z = glm::normalize(vec3(Gc[2]));
    dir.push_back({double(f), glm::normalize(out * 0.8f * X - 1.0f * Y - 0.25f * Z), Interp::Linear});
    wt.push_back({double(f), vec3(std::clamp(scene_.animation.evaluate(ik + ".weight", f, vec3(1)).x, 0.0f, 1.0f)), Interp::Linear});
  }
  gen.tracks[pole].keys = std::move(dir);
  gen.tracks[pole + ".weight"].keys = std::move(wt);
}

ArmClearance SceneEvaluator::armClearanceAt(size_t c, char side, double frame) const {
  if (c >= clearance_.size() || !clearance_[c].valid) return {};
  return armClearance(clearance_[c], characterGlobals(c, frame), side);
}

// For every arm driven by an IK track ("<who>/ik.<hand>"):
//  1. elbow pole: per frame, the elbow is swung (about the shoulder -> wrist axis, so the wrist does not move) to
//     point out of the body: the character's side, down and a little back in the chest frame. Its weight is the IK
//     weight, so it fades in and out with the IK and the clip arm is untouched;
//  2. wrist target: per frame, the target is pushed out of the body capsules along the gap gradient until hand,
//     forearm and the elbow half of the upper arm keep kArmBodyMargin (a few re-solves: the elbow moves with the
//     wrist); the per-frame pushes are then eased in time (cosine-weighted max over +-5 frames for the size, weighted
//     mean for the direction), so the correction starts before the arm gets close and never pops. Contact frames keep
//     their exact target (the push fades out over 4 frames towards a contact), and a contact inside the body is
//     reported. The IK track becomes per-frame keys only when some push is needed.
void SceneEvaluator::armClearancePass(Clip& gen, const InteractionContext& ctx) {
  const Clip& clip = scene_.animation;
  const int fs = scene_.frameStart, fe = scene_.frameEnd;
  if (clearance_.size() != characters_.size()) buildClearanceModels();
  for (size_t c = 0; c < characters_.size(); ++c) {
    const Skeleton& sk = characters_[c].asset.skeleton;
    if (!clearance_[c].valid) continue;
    const std::string who = scene_.characters[c].name;
    for (char side : {'L', 'R'}) {
      const ArmModel& A = clearance_[c].arm[side == 'L' ? 0 : 1];
      const std::string ik = who + "/ik." + sk.bones[size_t(A.hand)].name;
      auto it = gen.tracks.find(ik);
      if (it == gen.tracks.end() || it->second.keys.empty()) continue;
      auto weight = [&](double f) { return std::clamp(clip.evaluate(ik + ".weight", f, vec3(1)).x, 0.0f, 1.0f); };
      std::vector<double> contacts;
      for (const auto& k : ctx.contacts)
        if (size_t(k.character) == c && k.side == side) contacts.push_back(k.frame);
      // 1. pole
      const std::string pole = who + "/pole." + sk.bones[size_t(A.hand)].name;
      writeArmPole(gen, c, side);
      for (const auto& fz : ctx.frozen)
        if (size_t(fz.character) == c && fz.side == side) contacts.push_back(fz.from), contacts.push_back(fz.to);
      // 2. wrist target
      Track& T = gen.tracks[ik];
      const Track original = T;
      const int n = fe - fs + 3;
      std::vector<vec3> base(static_cast<size_t>(n)), raw(static_cast<size_t>(n), vec3(0));
      std::vector<float> w(static_cast<size_t>(n));
      for (int i = 0; i < n; ++i) base[size_t(i)] = original.evaluate(fs - 1 + i), w[size_t(i)] = weight(fs - 1 + i);
      auto setDense = [&](const std::vector<vec3>& push) {
        T.keys.clear();
        for (int i = 0; i < n; ++i) T.keys.push_back({double(fs - 1 + i), base[size_t(i)] + push[size_t(i)], Interp::Linear});
      };
      auto keyAt = [&](int f) -> Key& { return T.keys[size_t(f - (fs - 1))]; };
      // The clip arm's own gap per frame (IK and pole off): while the IK fades in or out the arm may rest as deep as
      // the clip puts it (a sleeve hanging against the side), never deeper; at full IK weight it keeps the margin.
      std::vector<float> idle(static_cast<size_t>(n), 1e9f);
      {
        const std::string wk = ik + ".weight", pk = pole + ".weight";
        const std::optional<Track> savedW = gen.tracks.count(wk) ? std::optional<Track>(gen.tracks[wk]) : std::nullopt;
        const Track savedP = gen.tracks[pk];
        gen.tracks[wk].keys = {{0.0, vec3(0), Interp::Step}};
        gen.tracks[pk].keys = {{0.0, vec3(0), Interp::Step}};
        for (int i = 0; i < n; ++i)
          if (w[size_t(i)] > 1e-3f) idle[size_t(i)] = armClearance(clearance_[c], characterGlobals(c, fs - 1 + i), side).gap;
        if (savedW) gen.tracks[wk] = *savedW;
        else gen.tracks.erase(wk);
        gen.tracks[pk] = savedP;
      }
      auto required = [&](int f) {
        const size_t i = size_t(f - (fs - 1));
        return std::min(kArmBodyMargin, w[i] * kArmBodyMargin + (1 - w[i]) * std::min(kArmBodyMargin, idle[i]));
      };
      // Pushes `f`'s key until the arm clears; returns the push added. Steps are capped (3 cm) so a point that follows
      // the wrist only partly (a sleeve) does not throw the hand away.
      auto clear = [&](int f, int iterations) {
        vec3 added(0);
        const float wf = w[size_t(f - (fs - 1))];
        if (wf <= 1e-3f) return added;
        const float req = required(f);
        for (int k = 0; k < iterations; ++k) {
          const ArmClearance s = armClearance(clearance_[c], characterGlobals(c, f), side);
          if (s.gap >= req - 0.0005f) break;
          vec3 step = s.push * ((req - s.gap) * 1.1f / (std::max(wf, 0.3f) * std::max(s.mobility, 0.5f)));
          if (glm::length(step) > 0.03f) step = glm::normalize(step) * 0.03f;
          keyAt(f).value += step;
          added += step;
        }
        return added;
      };
      auto gapAt = [&](int f) { return armClearance(clearance_[c], characterGlobals(c, f), side).gap; };
      setDense(raw);
      bool any = false;
      // Frame by frame, starting from the previous frame's push (coherent in time: the worst point or its direction
      // may change between frames, the push should not), then shrunk to the smallest quarter that still clears.
      vec3 prev(0);
      for (int f = fs; f <= fe; ++f) {
        const size_t i = size_t(f - (fs - 1));
        if (w[i] <= 1e-3f) {
          prev = vec3(0);
          continue;
        }
        keyAt(f).value = base[i] + prev;
        vec3 push = prev + clear(f, 12);
        const float req = required(f);
        for (float k : {0.0f, 0.25f, 0.5f, 0.75f}) {
          keyAt(f).value = base[i] + push * k;
          if (gapAt(f) >= req - 0.0005f) {
            push *= k;
            break;
          }
          keyAt(f).value = base[i] + push;
        }
        keyAt(f).value = base[i] + push;
        raw[i] = prev = push;
        any |= glm::length(push) > 1e-6f;
      }
      if (!any) {
        T = original;
        continue;
      }
      constexpr int R = 5;
      std::vector<vec3> eased(static_cast<size_t>(n), vec3(0));
      for (int i = 0; i < n; ++i) {
        float mag = 0;
        vec3 dir(0);
        for (int k = -R; k <= R; ++k) {
          const int j = i + k;
          if (j < 0 || j >= n) continue;
          const float cw = 0.5f * (1.0f + std::cos(glm::pi<float>() * float(k) / float(R + 1)));
          mag = std::max(mag, cw * glm::length(raw[size_t(j)]));
          dir += cw * raw[size_t(j)];
        }
        float fade = 1.0f;  // contact frames and held-still spans keep their exact target
        const double fi = double(fs - 1 + i);
        for (double cf : contacts) {
          const float d = float(std::abs(fi - cf));
          if (d < 4.0f) fade = std::min(fade, 0.5f - 0.5f * std::cos(glm::pi<float>() * d / 4.0f));
        }
        for (const auto& fz : ctx.frozen)
          if (size_t(fz.character) == c && fz.side == side && fi >= fz.from && fi <= fz.to) fade = 0;
        if (glm::length(dir) > 1e-9f) eased[size_t(i)] = glm::normalize(dir) * mag * fade;
      }
      setDense(eased);
      for (int f = fs; f <= fe; ++f) {  // residuals (direction mixing in the easing): small, local top-ups
        bool nearContact = false;
        for (double cf : contacts) nearContact |= std::abs(double(f) - cf) < 4.0;
        for (const auto& fz : ctx.frozen)
          nearContact |= size_t(fz.character) == c && fz.side == side && f >= fz.from - 4 && f <= fz.to + 4;
        if (!nearContact) clear(f, 4);
      }
    }
  }
}

Result<void> SceneEvaluator::finishInteractions(Clip& gen, InteractionContext& ctx) {
  armClearancePass(gen, ctx);
  // Later actions (clips, walks, other interactions) may change the body at an earlier contact: re-correct every
  // contact in time order, so each one is exact in the final animation.
  std::stable_sort(ctx.contacts.begin(), ctx.contacts.end(),
                   [](const InteractionContext::Contact& x, const InteractionContext::Contact& y) { return x.frame < y.frame; });
  for (const auto& k : ctx.contacts) {
    const int hb = characterSocketBone(size_t(k.character), std::string("hand.") + k.side);
    const std::string ik = scene_.characters[size_t(k.character)].name + "/ik." + characters_[size_t(k.character)].asset.skeleton.bones[size_t(hb)].name;
    auto measure = [&]() -> vec3 {
      const mat4 S = propWorld(size_t(k.prop), k.frame) * assetTransformMatrix(propAssets_[size_t(k.prop)].sockets.at(k.socket));
      if (k.placeTarget) return k.target - vec3(S[3]);
      return vec3(S[3]) - handGripPoint(size_t(k.character), k.side, k.frame);
    };
    const float e = correctKey(gen.tracks[ik], k.frame, measure);
    if (e > 0.005f)
      warnings_.push_back(std::format("interaction: '{}' hand.{} misses '{}' socket '{}' by {:.1f} mm at frame {} (out of reach?)",
                                      scene_.characters[size_t(k.character)].name, k.side, scene_.props[size_t(k.prop)].name,
                                      k.socket, e * 1000, k.frame));
  }
  // The final arms (after the contact corrections): an IK-driven arm inside the body is reported.
  for (size_t c = 0; c < clearance_.size(); ++c) {
    if (!clearance_[c].valid) continue;
    const std::string who = scene_.characters[c].name;
    for (char side : {'L', 'R'}) {
      const std::string ik = who + "/ik." + characters_[c].asset.skeleton.bones[size_t(clearance_[c].arm[side == 'L' ? 0 : 1].hand)].name;
      if (!gen.find(ik)) continue;
      float worst = 1e9f;
      double at = 0;
      for (int f = scene_.frameStart; f <= scene_.frameEnd; ++f) {  // full IK weight: the margin is required
        if (scene_.animation.evaluate(ik + ".weight", f, vec3(1)).x < 0.99f) continue;
        const float g = armClearanceAt(c, side, f).gap;
        if (g < worst) worst = g, at = f;
      }
      if (worst < 0)
        warnings_.push_back(std::format("interaction: '{}' arm {} passes {:.1f} mm into the body at frame {} (target inside the body?)",
                                        who, side, -worst * 1000, at));
    }
  }
  return {};
}

}  // namespace plush
