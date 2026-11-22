// T-047 collision system (see collision.h).
#include "scene/collision.h"

#include <algorithm>
#include <cmath>
#include <format>
#include <map>
#include <tuple>
#include <iterator>
#include <unordered_map>

#include "model/character.h"

namespace plush {
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
float percentile(std::vector<float> v, float q, float fallback, size_t minCount = 20) {
  if (v.size() < minCount) return fallback;
  const size_t k = std::min(v.size() - 1, size_t(q * float(v.size() - 1)));
  std::nth_element(v.begin(), v.begin() + std::ptrdiff_t(k), v.end());
  return v[k];
}
std::vector<mat4> restGlobals(const Skeleton& sk) {
  std::vector<mat4> G(sk.bones.size());
  for (size_t b = 0; b < sk.bones.size(); ++b) G[b] = glm::translate(mat4(1), sk.bones[b].head);
  return G;
}
Json vec(vec3 v) { return Json::array({v.x, v.y, v.z}); }
vec3 vecOf(const Json& j, const char* k) {
  const Json& a = j.at(k);
  if (!a.is_array() || a.size() != 3) throw std::runtime_error(std::string("expected [x,y,z] for ") + k);
  return vec3(a[0].get<float>(), a[1].get<float>(), a[2].get<float>());
}

// Limb capsule radius: the median distance of the limb's vertices from its axis (the limb's core). Garments on a limb
// (a puffed sleeve, a cuff) and spread fingers lie outside it; that soft outer layer may touch the body's garment
// shell, as felt and cloth do when an arm hangs at the side, without the limb counting as inside.
constexpr float kLimbRadiusQuantile = 0.5f;

}  // namespace

SectionGap sectionGap(const CollisionSection& C, const mat4& Gb, vec3 p, char side) {
  vec3 u = C.p1 - C.p0;
  const float L = glm::length(u);
  u = L > 1e-6f ? u / L : glm::normalize(glm::cross(C.e1, C.e2));
  const float r = std::min(C.r1, C.r2), s1 = r / C.r1, s2 = r / C.r2;
  const vec3 q0 = vec3(glm::inverse(Gb) * vec4(p, 1)) - C.p0;
  const vec3 q(glm::dot(q0, u), glm::dot(q0, C.e1) * s1, glm::dot(q0, C.e2) * s2);
  const float radial = glm::length(vec2(q.y, q.z));
  const float ax = q.x < 0 ? -q.x : q.x > L ? q.x - L : 0.0f;
  const bool round = (q.x < 0 && C.cap0) || (q.x > L && C.cap1);
  float gap;
  vec3 g;
  if (ax <= 0 || round) {
    const vec3 d = q - vec3(std::clamp(q.x, 0.0f, L), 0, 0);
    const float dist = glm::length(d);
    gap = dist - r;
    g = dist > 1e-6f ? d / dist : vec3(0, side == 'L' ? 1.0f : -1.0f, 0);
  } else {
    const float ro = std::max(radial - r, 0.0f);
    gap = std::sqrt(ro * ro + ax * ax);
    const vec3 rad = radial > 1e-6f ? vec3(0, q.y, q.z) / radial : vec3(0);
    g = glm::normalize(vec3(q.x < 0 ? -ax : ax, 0, 0) + ro * rad);
  }
  const vec3 local = u * g.x + C.e1 * (g.y * s1) + C.e2 * (g.z * s2);  // gradient of the scaled distance
  return {gap, glm::normalize(mat3(Gb) * local)};
}

void limbSegment(const CollisionLimb& limb, const std::vector<mat4>& G, vec3& a, vec3& b) {
  const mat4& M = G[size_t(limb.bone)];
  a = vec3(M * vec4(limb.a, 1));
  b = vec3(M * vec4(limb.b, 1));
}

Clearance segmentClearance(const CollisionBody& body, const std::vector<mat4>& G, vec3 a, vec3 b, float r, char side) {
  Clearance out;
  constexpr int kSamples = 9;  // a capsule is at most ~2.5 radii between samples: the gap between them is overstated by
                               // at most a few tenths of a millimetre for the limb sizes fitted here
  for (int i = 0; i < kSamples; ++i) {
    const vec3 p = glm::mix(a, b, float(i) / float(kSamples - 1));
    for (const CollisionSection& s : body.sections) {
      const SectionGap sg = sectionGap(s, G[size_t(s.bone)], p, side);
      const float gap = sg.gap - r;
      if (gap >= out.gap) continue;
      out.gap = gap;
      out.point = p - sg.grad * r;
      out.push = sg.grad;
      out.against = s.name;
    }
  }
  return out;
}

Clearance limbClearance(const CollisionBody& body, const std::vector<mat4>& G, char side) {
  Clearance out;
  if (!body.valid) return out;
  for (const CollisionLimb& l : body.limbs) {
    if (l.side != side) continue;
    vec3 a, b;
    limbSegment(l, G, a, b);
    Clearance c = segmentClearance(body, G, a, b, l.r, side);
    c.gap -= l.allowance;
    if (c.gap < out.gap) out = c, out.part = l.name;
  }
  return out;
}

CollisionBody deriveCollisionBody(const Skeleton& sk, const std::vector<SkinnedMesh>& meshes) {
  CollisionBody M;
  M.source = "derived";
  const int hips = sk.find("hips"), chest = sk.find("chest"), spine = sk.find("spine"), neck = sk.find("neck");
  if (hips < 0 || chest < 0) return M;
  int handB[2], foreB[2], upperB[2];
  for (int s = 0; s < 2; ++s) {
    handB[s] = sk.find(std::string("hand.") + (s == 0 ? 'L' : 'R'));
    if (handB[s] < 0) return M;
    foreB[s] = sk.bones[size_t(handB[s])].parent;
    upperB[s] = foreB[s] >= 0 ? sk.bones[size_t(foreB[s])].parent : -1;
    if (upperB[s] < 0) return M;
  }
  auto head = [&](int b) { return sk.bones[size_t(b)].head; };
  std::vector<int> region(sk.bones.size()), part(sk.bones.size());
  for (size_t b = 0; b < sk.bones.size(); ++b) region[b] = int(regionOf(sk, int(b))), part[b] = int(armPartOf(sk, int(b)));
  // Rest vertices by region (>= 90 % of the weight in the torso) and by arm part (>= 50 % on that arm's forearm or
  // hand, nothing of the head or legs).
  std::vector<vec3> torso, fore[2], hand[2];
  for (const SkinnedMesh& m : meshes)
    for (size_t v = 0; v < m.rest.positions.size() && v < m.joints.size() && v < m.weights.size(); ++v) {
      float w[6] = {0, 0, 0, 0, 0, 0}, wp[2][4] = {{0, 0, 0, 0}, {0, 0, 0, 0}};
      for (int k = 0; k < 4; ++k) {
        const int j = m.joints[v][k];
        if (j < 0 || size_t(j) >= sk.bones.size() || m.weights[v][k] <= 0) continue;
        w[region[size_t(j)]] += m.weights[v][k];
        const int r = region[size_t(j)];
        if (r == int(Region::ArmL) || r == int(Region::ArmR)) wp[r == int(Region::ArmL) ? 0 : 1][part[size_t(j)]] += m.weights[v][k];
      }
      const vec3 p = m.rest.positions[v];
      if (w[int(Region::Torso)] >= 0.9f) torso.push_back(p);
      if (w[int(Region::Head)] + w[int(Region::Leg)] >= 0.1f) continue;
      for (int s = 0; s < 2; ++s) {
        if (wp[s][int(ArmPart::Fore)] >= 0.5f) fore[s].push_back(p);
        if (wp[s][int(ArmPart::Hand)] >= 0.5f) hand[s].push_back(p);
      }
    }
  const int ua = upperB[0], ub = upperB[1];
  const float shoulderHalf = 0.5f * glm::distance(head(ua), head(ub));
  const float rDefault = 0.95f * shoulderHalf;
  // Sections along the spine (the T-030 fit): pelvis (below the hips, carried by the hips), lower torso (hips -> chest,
  // carried by the spine or hips) and upper torso (chest -> neck, carried by the chest), each cut into short bands
  // whose radii fit the vertices of their own height slab.
  auto band = [&](std::string name, int bone, vec3 a, vec3 b) {
    CollisionSection C;
    C.name = std::move(name);
    C.bone = bone;
    C.p0 = a - head(bone);
    C.p1 = b - head(bone);
    const vec3 u = glm::normalize(b - a);
    C.e1 = glm::normalize(vec3(1, 0, 0) - u * u.x);
    C.e2 = glm::normalize(glm::cross(C.e1, u));  // forward (+Z) for an upright segment
    C.cap0 = C.cap1 = false;
    std::vector<float> side, front;
    for (const vec3& p : torso) {
      const float t = glm::dot(p - a, b - a) / glm::dot(b - a, b - a);
      if (t < 0 || t > 1) continue;
      const vec3 d = p - (a + t * (b - a));
      if (glm::dot(d, C.e2) < 0) continue;  // front half only
      side.push_back(std::abs(glm::dot(d, C.e1)));
      front.push_back(glm::dot(d, C.e2));
    }
    C.r1 = std::clamp(percentile(side, 0.99f, rDefault), 0.02f, 0.5f);
    C.r2 = std::clamp(percentile(front, 0.99f, rDefault), 0.02f, 0.5f);
    M.sections.push_back(C);
  };
  const vec3 top = neck >= 0 ? head(neck) : head(chest) + vec3(0, 0.6f * shoulderHalf, 0);
  const vec3 bottom = head(hips) + 0.4f * (head(hips) - head(chest));
  auto bands = [&](const char* name, int bone, vec3 a, vec3 b, int n) {
    for (int i = 0; i < n; ++i)
      band(std::format("{}_{}", name, i + 1), bone, glm::mix(a, b, float(i) / float(n)), glm::mix(a, b, float(i + 1) / float(n)));
  };
  bands("pelvis", hips, bottom, head(hips), 2);
  bands("torso_lower", spine >= 0 ? spine : hips, head(hips), head(chest), 3);
  bands("torso_upper", chest, head(chest), top, 2);
  M.sections.front().cap0 = true;
  M.sections.back().cap1 = true;
  M.valid = true;  // sections first: the limbs below are checked against them at rest
  // Limbs. Forearm: its wrist half (the elbow half rests against the body's side; the elbow pole keeps it outward),
  // radius the 90th percentile of the forearm-carried vertices' distance from the elbow -> wrist axis. Hand: from the
  // wrist along the finger direction (wrist -> mean finger root) to the 98th percentile of the hand-carried vertices,
  // radius their 90th percentile distance from that axis.
  const std::vector<mat4> rest = restGlobals(sk);
  for (int s = 0; s < 2; ++s) {
    const char side = s == 0 ? 'L' : 'R';
    const vec3 e = head(foreB[s]), w = head(handB[s]);
    const float foreLen = glm::distance(e, w);
    vec3 fingers(0);
    int nf = 0;
    for (int k = 0; k < 4; ++k)
      if (int f = sk.find(std::format("f{}a.{}", k, side)); f >= 0) fingers += head(f), ++nf;
    vec3 dir = nf > 0 ? fingers / float(nf) - w : w - e;
    dir = glm::length(dir) > 1e-6f ? glm::normalize(dir) : glm::normalize(w - e);
    auto radial = [](const std::vector<vec3>& P, vec3 o, vec3 u, float t0, float t1, std::vector<float>* along) {
      std::vector<float> r;
      for (const vec3& p : P) {
        const float t = glm::dot(p - o, u);
        if (t < t0 || t > t1) continue;
        r.push_back(glm::length((p - o) - u * t));
        if (along) along->push_back(t);
      }
      return r;
    };
    const vec3 uf = glm::normalize(w - e);
    CollisionLimb F;
    F.name = std::format("forearm.{}", side);
    F.bone = foreB[s];
    F.side = side;
    float t0 = 0.5f;
    F.r = std::clamp(percentile(radial(fore[s], e, uf, t0 * foreLen, foreLen, nullptr), kLimbRadiusQuantile, 0.18f * foreLen, 10), 0.008f, 0.08f);
    std::vector<float> along;
    const float handLen = std::max(0.02f, 0.75f * foreLen);
    std::vector<float> hr = radial(hand[s], w, dir, -0.01f, 2.0f * handLen, &along);
    CollisionLimb H;
    H.name = std::format("hand.{}", side);
    H.bone = handB[s];
    H.side = side;
    H.r = std::clamp(percentile(hr, kLimbRadiusQuantile, 0.3f * handLen, 10), 0.008f, 0.06f);
    const float tipT = std::max(H.r + 0.005f, percentile(along, 0.98f, handLen, 10));
    H.a = vec3(0);
    H.b = dir * std::max(0.005f, tipT - H.r);
    auto placeForearm = [&] {
      F.a = uf * (t0 * foreLen);
      F.b = uf * foreLen;
    };
    placeForearm();
    // Rest pose clear by construction: a limb that touches the body at rest is shortened (forearm, towards the
    // wrist) and then thinned (both, to 60 % at most) until it keeps the margin.
    auto restGap = [&](const CollisionLimb& l) {
      vec3 a, b;
      limbSegment(l, rest, a, b);
      return segmentClearance(M, rest, a, b, l.r, side).gap;
    };
    while (restGap(F) < M.margin && t0 < 0.85f) t0 += 0.05f, placeForearm();
    for (CollisionLimb* l : {&F, &H}) {
      const float r0 = l->r;
      while (restGap(*l) < M.margin && l->r > 0.6f * r0) l->r -= 0.001f;
    }
    // A limb that still rests against the body (a character modelled with its arms down, hands on a skirt) keeps its
    // rest depth as an allowance: it may rest that deep, never deeper.
    for (CollisionLimb* l : {&F, &H}) l->allowance = std::min(0.0f, restGap(*l) - M.margin);
    M.limbs.push_back(F);
    M.limbs.push_back(H);
  }
  return M;
}

void addHeadVolumes(CollisionBody& M, const Skeleton& sk, const std::vector<SkinnedMesh>& meshes) {
  M.heads.clear();
  const int head = sk.find("head");
  if (head < 0) return;
  std::vector<char> underHead(sk.bones.size(), 0);
  for (size_t b = 0; b < sk.bones.size(); ++b)
    for (int k = int(b); k >= 0; k = sk.bones[size_t(k)].parent)
      if (k == head) underHead[b] = 1;
  // Voxel groups of the head-carried rest vertices (ordered map: the result does not depend on hashing).
  std::map<std::tuple<int, int, int>, std::vector<vec3>> cells;
  size_t count = 0;
  for (const SkinnedMesh& m : meshes)
    for (size_t v = 0; v < m.rest.positions.size() && v < m.joints.size() && v < m.weights.size(); ++v) {
      float w = 0;
      for (int k = 0; k < 4; ++k) {
        const int j = m.joints[v][k];
        if (j >= 0 && size_t(j) < sk.bones.size() && underHead[size_t(j)] && m.weights[v][k] > 0) w += m.weights[v][k];
      }
      if (w < 0.5f) continue;
      const vec3 p = m.rest.positions[v];
      const glm::ivec3 i = glm::ivec3(glm::floor(p / kHeadCell));
      cells[{i.x, i.y, i.z}].push_back(p);
      ++count;
    }
  if (count < 50) return;
  const vec3 hb = sk.bones[size_t(head)].head;
  for (const auto& [key, pts] : cells) {
    vec3 lo(1e9f), hi(-1e9f);
    for (const vec3& p : pts) lo = glm::min(lo, p), hi = glm::max(hi, p);
    const vec3 c = 0.5f * (lo + hi);
    float r = 0;
    for (const vec3& p : pts) r = std::max(r, glm::distance(p, c));
    M.heads.push_back({head, c - hb, std::max(r, kHeadMinRadius)});
  }
}

std::vector<std::pair<vec3, float>> headSpheres(const CollisionBody& M, const std::vector<mat4>& G) {
  std::vector<std::pair<vec3, float>> out;
  out.reserve(M.heads.size());
  for (const CollisionSphere& s : M.heads)
    if (s.bone >= 0 && size_t(s.bone) < G.size()) out.push_back({vec3(G[size_t(s.bone)] * vec4(s.centre, 1)), s.r});
  return out;
}

HeadGap headGap(const CollisionBody& a, const std::vector<mat4>& Ga, const CollisionBody& b, const std::vector<mat4>& Gb) {
  HeadGap out;
  const auto A = headSpheres(a, Ga), B = headSpheres(b, Gb);
  if (A.empty() || B.empty()) return out;
  auto consider = [&](const std::pair<vec3, float>& sa, const std::pair<vec3, float>& sb) {
    const vec3 d = sa.first - sb.first;
    const float L = glm::length(d), g = L - sa.second - sb.second;
    if (g >= out.gap) return;
    out.gap = g;
    out.dir = L > 1e-6f ? d / L : vec3(0, 1, 0);
    out.pointA = sa.first - out.dir * sa.second;
    out.pointB = sb.first + out.dir * sb.second;
  };
  // Near pairs through a grid over b's spheres (cell = the search reach); exact for gaps below kHeadNearGap. Farther
  // heads: every pair (rare: a pass only measures far heads once per frame).
  float rmax = 0;
  for (const auto& s : A) rmax = std::max(rmax, s.second);
  for (const auto& s : B) rmax = std::max(rmax, s.second);
  const float cell = 2.0f * rmax + kHeadNearGap;
  std::unordered_map<long long, std::vector<int>> grid;
  auto key = [](glm::ivec3 i) { return ((long long)(i.x + 100000) * 200003LL + (long long)(i.y + 100000)) * 200003LL + (long long)(i.z + 100000); };
  for (size_t j = 0; j < B.size(); ++j) grid[key(glm::ivec3(glm::floor(B[j].first / cell)))].push_back(int(j));
  for (const auto& sa : A) {
    const glm::ivec3 i = glm::ivec3(glm::floor(sa.first / cell));
    for (int dx = -1; dx <= 1; ++dx)
      for (int dy = -1; dy <= 1; ++dy)
        for (int dz = -1; dz <= 1; ++dz)
          if (auto it = grid.find(key(i + glm::ivec3(dx, dy, dz))); it != grid.end())
            for (int j : it->second) consider(sa, B[size_t(j)]);
  }
  if (out.gap < kHeadNearGap) return out;
  out = HeadGap{};
  for (const auto& sa : A)
    for (const auto& sb : B) consider(sa, sb);
  return out;
}

Json collisionBodyToJson(const CollisionBody& body, const Skeleton& sk) {
  Json sections = Json::array(), limbs = Json::array();
  for (const CollisionSection& s : body.sections)
    sections.push_back({{"name", s.name}, {"bone", sk.bones[size_t(s.bone)].name}, {"p0", vec(s.p0)}, {"p1", vec(s.p1)},
                        {"e1", vec(s.e1)}, {"e2", vec(s.e2)}, {"r1", s.r1}, {"r2", s.r2}, {"cap0", s.cap0}, {"cap1", s.cap1}});
  for (const CollisionLimb& l : body.limbs)
    limbs.push_back({{"name", l.name}, {"bone", sk.bones[size_t(l.bone)].name}, {"side", std::string(1, l.side)},
                     {"a", vec(l.a)}, {"b", vec(l.b)}, {"r", l.r}, {"allowance", l.allowance}});
  return {{"format", "plush.collision_body"}, {"version", 1}, {"margin", body.margin},
          {"max_elbow_swing_deg", glm::degrees(body.maxElbowSwing)}, {"sections", sections}, {"limbs", limbs}};
}

Result<CollisionBody> collisionBodyFromJson(const Json& j, const Skeleton& sk) {
  if (!j.is_object() || j.value("format", std::string()) != "plush.collision_body") return fail("collision: not a plush.collision_body block");
  if (j.value("version", 0) != 1) return fail("collision: unsupported version");
  CollisionBody M;
  M.source = "package";
  try {
    M.margin = j.value("margin", kCollisionMargin);
    const float swingDeg = j.value("max_elbow_swing_deg", kDefaultMaxElbowSwingDeg);
    if (!(swingDeg >= 0 && swingDeg <= 120)) throw std::runtime_error("max_elbow_swing_deg must be in [0, 120]");
    M.maxElbowSwing = glm::radians(swingDeg);
    auto bone = [&](const Json& e) -> int {
      const int b = sk.find(e.at("bone").get<std::string>());
      if (b < 0) throw std::runtime_error("unknown bone " + e.at("bone").get<std::string>());
      return b;
    };
    for (const Json& e : j.at("sections")) {
      CollisionSection s;
      s.name = e.at("name").get<std::string>();
      s.bone = bone(e);
      s.p0 = vecOf(e, "p0"), s.p1 = vecOf(e, "p1"), s.e1 = vecOf(e, "e1"), s.e2 = vecOf(e, "e2");
      s.r1 = e.at("r1").get<float>(), s.r2 = e.at("r2").get<float>();
      s.cap0 = e.value("cap0", false), s.cap1 = e.value("cap1", false);
      if (!(s.r1 > 0) || !(s.r2 > 0)) throw std::runtime_error("section " + s.name + ": radii must be > 0");
      M.sections.push_back(s);
    }
    for (const Json& e : j.at("limbs")) {
      CollisionLimb l;
      l.name = e.at("name").get<std::string>();
      l.bone = bone(e);
      const std::string side = e.at("side").get<std::string>();
      if (side != "L" && side != "R") throw std::runtime_error("limb " + l.name + ": side must be L or R");
      l.side = side[0];
      l.a = vecOf(e, "a"), l.b = vecOf(e, "b"), l.r = e.at("r").get<float>();
      l.allowance = std::min(0.0f, e.value("allowance", 0.0f));
      if (!(l.r > 0)) throw std::runtime_error("limb " + l.name + ": radius must be > 0");
      M.limbs.push_back(l);
    }
  } catch (const std::exception& e) {
    return fail(std::string("collision: ") + e.what());
  }
  if (M.sections.empty()) return fail("collision: no sections");
  M.valid = true;
  return M;
}

CollisionBody collisionBodyFor(const Json& block, const Skeleton& sk, const std::vector<SkinnedMesh>& meshes) {
  if (block.is_object())
    if (auto b = collisionBodyFromJson(block, sk)) return *b;
  return deriveCollisionBody(sk, meshes);
}

}  // namespace plush

// ---- T-191 body parts (see collision.h) ----
namespace plush {
namespace {
const char* const kBodyRoles[] = {"hips",      "spine",     "chest",  "neck",   "head",   "upperArm.L", "upperArm.R",
                                  "forearm.L", "forearm.R", "hand.L", "hand.R", "thigh.L", "thigh.R",   "shin.L",
                                  "shin.R",    "foot.L",    "foot.R"};
// Eigenvectors of a symmetric 3x3 matrix (Jacobi), columns sorted by decreasing eigenvalue.
void symEigen(glm::dmat3 A, glm::dvec3& w, glm::dmat3& V) {
  V = glm::dmat3(1.0);
  for (int sweep = 0; sweep < 32; ++sweep) {
    double off = std::abs(A[0][1]) + std::abs(A[0][2]) + std::abs(A[1][2]);
    if (off < 1e-14) break;
    for (int p = 0; p < 2; ++p)
      for (int q = p + 1; q < 3; ++q) {
        if (std::abs(A[p][q]) < 1e-18) continue;
        const double th = 0.5 * (A[q][q] - A[p][p]) / A[p][q];
        const double t = (th >= 0 ? 1.0 : -1.0) / (std::abs(th) + std::sqrt(th * th + 1));
        const double c = 1 / std::sqrt(t * t + 1), s = t * c;
        glm::dmat3 J(1.0);
        J[p][p] = c, J[q][q] = c, J[q][p] = s, J[p][q] = -s;  // column-major: J[col][row]
        A = glm::transpose(J) * A * J;
        V = V * J;
      }
  }
  int idx[3] = {0, 1, 2};
  std::sort(idx, idx + 3, [&](int i, int j) { return A[i][i] > A[j][j]; });
  glm::dmat3 S;
  for (int k = 0; k < 3; ++k) w[k] = A[idx[k]][idx[k]], S[k] = V[idx[k]];
  V = S;
}
}  // namespace

BodyParts deriveBodyParts(const Skeleton& sk, const std::vector<SkinnedMesh>& meshes) {
  BodyParts out;
  constexpr int nRoles = int(std::size(kBodyRoles));
  int roleBone[nRoles];
  std::unordered_map<int, int> roleOfBone;
  for (int r = 0; r < nRoles; ++r) {
    roleBone[r] = sk.find(kBodyRoles[r]);
    if (roleBone[r] >= 0) roleOfBone[roleBone[r]] = r;
  }
  std::vector<int> role(sk.bones.size(), -1);
  for (size_t b = 0; b < sk.bones.size(); ++b)
    for (int k = int(b); k >= 0; k = sk.bones[size_t(k)].parent)
      if (auto it = roleOfBone.find(k); it != roleOfBone.end()) {
        role[b] = it->second;
        break;
      }
  std::vector<std::vector<vec3>> pts(static_cast<size_t>(nRoles));
  for (const SkinnedMesh& m : meshes)
    for (size_t v = 0; v < m.rest.positions.size() && v < m.joints.size() && v < m.weights.size(); ++v) {
      float w[nRoles] = {};
      for (int k = 0; k < 4; ++k) {
        const int j = m.joints[v][k];
        if (j < 0 || size_t(j) >= sk.bones.size() || m.weights[v][k] <= 0 || role[size_t(j)] < 0) continue;
        w[role[size_t(j)]] += m.weights[v][k];
      }
      const int best = int(std::max_element(w, w + nRoles) - w);
      if (w[best] >= 0.5f) pts[size_t(best)].push_back(m.rest.positions[v]);
    }
  for (int r = 0; r < nRoles; ++r) {
    const auto& P = pts[size_t(r)];
    if (P.size() < 20 || roleBone[r] < 0) continue;
    glm::dvec3 c(0);
    for (const vec3& p : P) c += glm::dvec3(p);
    c /= double(P.size());
    glm::dmat3 C(0.0);
    for (const vec3& p : P) {
      const glm::dvec3 d = glm::dvec3(p) - c;
      C += glm::outerProduct(d, d);
    }
    glm::dvec3 w;
    glm::dmat3 V;
    symEigen(C / double(P.size()), w, V);
    const vec3 ax = glm::normalize(vec3(V[0])), e1 = glm::normalize(vec3(V[1])), e2 = glm::normalize(vec3(V[2]));
    std::vector<float> t, d1, d2;
    for (const vec3& p : P) {
      const vec3 d = p - vec3(c);
      t.push_back(glm::dot(d, ax));
      d1.push_back(std::abs(glm::dot(d, e1)));
      d2.push_back(std::abs(glm::dot(d, e2)));
    }
    float q1 = percentile(d1, kBodyPartRadiusQuantile, 0.05f), q2 = percentile(d2, kBodyPartRadiusQuantile, 0.05f);
    vec3 wide = e1;
    if (q2 > q1) std::swap(q1, q2), wide = e2;
    const bool flat = q1 > kBodyPartFlat * q2;
    const float rad = flat ? q2 : q1;
    float t0 = percentile(t, 0.01f, 0), t1 = percentile(t, 0.99f, 0);
    t0 += rad, t1 -= rad;
    if (t0 > t1) t0 = t1 = 0.5f * (t0 + t1);
    const vec3 head = sk.bones[size_t(roleBone[r])].head;
    const vec3 a = vec3(c) + ax * t0 - head, b = vec3(c) + ax * t1 - head;
    for (float s : flat ? std::vector<float>{-1.0f, 1.0f} : std::vector<float>{0.0f})
      out.capsules.push_back({kBodyRoles[r], roleBone[r], a + wide * (s * (q1 - q2)), b + wide * (s * (q1 - q2)), rad});
  }
  out.valid = !out.capsules.empty();
  return out;
}

void bodyPartSegment(const BodyPartCapsule& c, const std::vector<mat4>& G, vec3& a, vec3& b) {
  const mat4& M = G[size_t(c.bone)];
  a = vec3(M * vec4(c.a, 1));
  b = vec3(M * vec4(c.b, 1));
}

float segmentSegment(vec3 p1, vec3 q1, vec3 p2, vec3 q2, vec3& c1, vec3& c2) {
  // Ericson, Real-Time Collision Detection 5.1.9.
  const vec3 d1 = q1 - p1, d2 = q2 - p2, r = p1 - p2;
  const float a = glm::dot(d1, d1), e = glm::dot(d2, d2), f = glm::dot(d2, r);
  float s = 0, t = 0;
  if (a <= 1e-12f && e <= 1e-12f) {
  } else if (a <= 1e-12f) {
    t = std::clamp(f / e, 0.0f, 1.0f);
  } else {
    const float c = glm::dot(d1, r);
    if (e <= 1e-12f) {
      s = std::clamp(-c / a, 0.0f, 1.0f);
    } else {
      const float b = glm::dot(d1, d2), den = a * e - b * b;
      s = den > 1e-12f ? std::clamp((b * f - c * e) / den, 0.0f, 1.0f) : 0.0f;
      t = (b * s + f) / e;
      if (t < 0) t = 0, s = std::clamp(-c / a, 0.0f, 1.0f);
      else if (t > 1) t = 1, s = std::clamp((b - c) / a, 0.0f, 1.0f);
    }
  }
  c1 = p1 + d1 * s;
  c2 = p2 + d2 * t;
  return glm::distance(c1, c2);
}

BodyGap bodyGap(const BodyParts& A, const std::vector<mat4>& Ga, const BodyParts& B, const std::vector<mat4>& Gb,
                bool (*skip)(const std::string&, const std::string&)) {
  BodyGap out;
  std::vector<std::pair<vec3, vec3>> sb;
  for (const auto& c : B.capsules) {
    vec3 p0, p1;
    bodyPartSegment(c, Gb, p0, p1);
    sb.emplace_back(p0, p1);
  }
  for (const auto& ca : A.capsules) {
    vec3 a0, a1;
    bodyPartSegment(ca, Ga, a0, a1);
    for (size_t j = 0; j < B.capsules.size(); ++j) {
      const auto& cb = B.capsules[j];
      if (skip && skip(ca.part, cb.part)) continue;
      vec3 pa, pb;
      const float d = segmentSegment(a0, a1, sb[j].first, sb[j].second, pa, pb);
      const float g = d - ca.r - cb.r;
      if (g >= out.gap) continue;
      vec3 dir = d > 1e-6f ? (pa - pb) / d : vec3(0);
      if (d <= 1e-6f) {  // axes cross: away horizontally, bone to bone
        dir = vec3(Ga[size_t(ca.bone)][3]) - vec3(Gb[size_t(cb.bone)][3]);
        dir.y = 0;
        dir = glm::length(dir) > 1e-6f ? glm::normalize(dir) : vec3(1, 0, 0);
      }
      out.gap = g, out.partA = ca.part, out.partB = cb.part, out.dir = dir;
      out.pointA = pa - dir * ca.r, out.pointB = pb + dir * cb.r;
    }
  }
  return out;
}

float pointBodyGap(const BodyParts& body, const std::vector<mat4>& G, vec3 p, std::string* part) {
  float best = 1e9f;
  for (const auto& c : body.capsules) {
    vec3 a, b, ca, cb;
    bodyPartSegment(c, G, a, b);
    const float g = segmentSegment(a, b, p, p, ca, cb) - c.r;
    if (g < best) {
      best = g;
      if (part) *part = c.part;
    }
  }
  return best;
}
}  // namespace plush
