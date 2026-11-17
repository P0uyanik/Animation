// T-040 measurement: arm-body clearance against the skinned MESH (not only the capsules), per frame, per character
// and arm, with the always-on post-pass and without it (not part of the build):
//   g++ -std=c++23 -O2 -I engine docs/evaluation/animation/T-040/measure_t040.cpp -Lbuild/cpp/engine -lplush_scene \
//       -lplush_model -lplush_fuzz -lplush_anim -lplush_geom -lplush_core -o m          (run from the repository root)
//   ./m <shot.resolved.scene.json> [frame stride] > out.json
// Mesh model, per character and frame (engine skinning: sum of w * G[j] * (rest - head_j)):
// - body surface: every triangle whose three vertices are >= 90 % torso-carried (hips, spine, chest and their
//   helpers; garments and accessories included; the hips' leg-carried sides down to the engine's pelvis bottom), hair
//   meshes excepted (curls hanging onto the chest are not body volume);
// - arm surface: EVERY vertex carried >= 50 % by that arm (sleeve, cuff, hand, fingers; nothing of the head/legs);
// - signed distance of an arm vertex = distance to the nearest body triangle, signed by the interpolated normal there
//   (< 0 inside) by the angle-weighted pseudo-normal of the nearest feature on vertices welded by rest position (a
//   nearest feature on an open boundary - hem, armhole, neck - counts as outside). An arm vertex that is already inside at rest (a sleeve under a vest's armhole) counts from its rest
//   depth ("rest-relative"), as in the engine;
// - the armpit band (upper-arm vertices nearer the shoulder pivot than 40 % of the upper arm) is reported apart: it
//   folds with the shoulder joint (skin deformation), no arm rotation short of a raised arm moves it.
// Also reported: the engine's capsule gaps (post-pass points; T-030's armClearance gap/upperGap for the batch-1
// comparison) and the correction the post-pass made (shoulder/elbow angle, wrist offset, their frame-to-frame
// acceleration).
#include <cstdio>
#include <iostream>
#include <map>
#include <set>
#include <tuple>
#include <unordered_map>

#include "scene/interaction.h"
#include "scene/scene.h"

using namespace plush;

namespace {
bool starts(const std::string& s, const char* p) { return s.rfind(p, 0) == 0; }
bool finger(const std::string& n) { return n.size() >= 4 && ((n[0] == 'f' && n[1] >= '0' && n[1] <= '9') || starts(n, "thumb")); }
// 0 other, 1 torso, 2 arm L, 3 arm R, 4 leg, 5 head (as engine/scene/interaction.cpp)
int region(const Skeleton& sk, int b) {
  for (int k = b; k >= 0; k = sk.bones[size_t(k)].parent) {
    const std::string& n = sk.bones[size_t(k)].name;
    const char side = n.empty() ? ' ' : n.back();
    if (starts(n, "upperArm.") || starts(n, "forearm.") || starts(n, "hand.") || (finger(n) && n.find('.') != std::string::npos)) return side == 'L' ? 2 : 3;
    if (starts(n, "thigh.") || starts(n, "shin.") || starts(n, "foot.") || starts(n, "toe")) return 4;
    if (n == "neck" || n == "head" || starts(n, "eye.")) return 5;
    if (n == "hips" || n == "spine" || n == "chest") return 1;
  }
  return 0;
}
vec3 closestOnTri(vec3 p, vec3 a, vec3 b, vec3 c, vec3& bary) {  // Ericson, Real-Time Collision Detection 5.1.5
  const vec3 ab = b - a, ac = c - a, ap = p - a;
  const float d1 = glm::dot(ab, ap), d2 = glm::dot(ac, ap);
  if (d1 <= 0 && d2 <= 0) return bary = {1, 0, 0}, a;
  const vec3 bp = p - b;
  const float d3 = glm::dot(ab, bp), d4 = glm::dot(ac, bp);
  if (d3 >= 0 && d4 <= d3) return bary = {0, 1, 0}, b;
  const float vc = d1 * d4 - d3 * d2;
  if (vc <= 0 && d1 >= 0 && d3 <= 0) { const float v = d1 / (d1 - d3); bary = {1 - v, v, 0}; return a + v * ab; }
  const vec3 cp = p - c;
  const float d5 = glm::dot(ab, cp), d6 = glm::dot(ac, cp);
  if (d6 >= 0 && d5 <= d6) return bary = {0, 0, 1}, c;
  const float vb = d5 * d2 - d1 * d6;
  if (vb <= 0 && d2 >= 0 && d6 <= 0) { const float w = d2 / (d2 - d6); bary = {1 - w, 0, w}; return a + w * ac; }
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

struct Skinned {
  std::vector<vec3> p, n;
};
struct CharMesh {
  struct V { size_t m, v; };
  std::vector<std::array<V, 3>> bodyTris;
  // topology of the body triangles, on vertices welded by rest position (UV seams split vertices)
  std::vector<std::array<int, 3>> weld;
  std::vector<char> flip;                       // the triangle's winding is against its vertex normals
  std::vector<std::vector<int>> vertexTris;     // welded vertex -> triangles
  std::map<std::pair<int, int>, std::vector<int>> edgeTris;
  std::vector<char> boundaryVertex;
  std::vector<V> arm[2];
  std::vector<float> along[2], restDepth[2];
};

Skinned skin(const SkinnedMesh& m, const Skeleton& sk, const std::vector<mat4>& G) {
  Skinned s;
  s.p.resize(m.rest.positions.size());
  s.n.resize(m.rest.positions.size(), vec3(0, 0, 1));
  for (size_t v = 0; v < m.rest.positions.size() && v < m.joints.size(); ++v) {
    vec3 p(0), n(0);
    for (int k = 0; k < 4; ++k) {
      const float w = m.weights[v][k];
      if (w <= 0) continue;
      const int j = std::clamp(m.joints[v][k], 0, int(sk.bones.size()) - 1);
      p += w * vec3(G[size_t(j)] * vec4(m.rest.positions[v] - sk.bones[size_t(j)].head, 1));
      if (v < m.rest.normals.size()) n += w * (mat3(G[size_t(j)]) * m.rest.normals[v]);
    }
    s.p[v] = p;
    if (glm::length(n) > 1e-9f) s.n[v] = glm::normalize(n);
  }
  return s;
}

// Uniform grid over the body triangles of one frame; signed distance of a point to the nearest one.
struct Grid {
  float cell = 0.03f;
  std::unordered_map<long long, std::vector<int>> cells;
  const std::vector<Skinned>* S;
  const CharMesh* C;
  static long long key(int x, int y, int z) { return ((long long)(x + 4096) << 40) | ((long long)(y + 4096) << 20) | (long long)(z + 4096); }
  Grid(const std::vector<Skinned>& s, const CharMesh& c) : S(&s), C(&c) {
    normals();
    for (size_t t = 0; t < c.bodyTris.size(); ++t) {
      vec3 lo(1e9f), hi(-1e9f);
      for (auto& v : c.bodyTris[t]) lo = glm::min(lo, (*S)[v.m].p[v.v]), hi = glm::max(hi, (*S)[v.m].p[v.v]);
      const glm::ivec3 a(glm::floor(lo / cell)), b(glm::floor(hi / cell));
      for (int x = a.x; x <= b.x; ++x)
        for (int y = a.y; y <= b.y; ++y)
          for (int z = a.z; z <= b.z; ++z) cells[key(x, y, z)].push_back(int(t));
    }
  }
  std::vector<vec3> faceN;  // oriented face normals of this frame
  mutable int lastTri = -1, lastFeature = -1;
  mutable float lastDot = 0;
  vec3 P(int t, int k) const { const auto& v = C->bodyTris[size_t(t)][size_t(k)]; return (*S)[v.m].p[v.v]; }
  void normals() {
    faceN.resize(C->bodyTris.size());
    for (size_t t = 0; t < C->bodyTris.size(); ++t) {
      vec3 n = glm::cross(P(int(t), 1) - P(int(t), 0), P(int(t), 2) - P(int(t), 0));
      n = glm::length(n) > 1e-12f ? glm::normalize(n) : vec3(0);
      faceN[t] = C->flip[t] ? -n : n;
    }
  }
  float angleAt(int t, int k) const {
    const vec3 a = P(t, k), b = P(t, (k + 1) % 3), c = P(t, (k + 2) % 3);
    const vec3 u = b - a, v = c - a;
    const float l = glm::length(u) * glm::length(v);
    return l > 1e-12f ? std::acos(std::clamp(glm::dot(u, v) / l, -1.0f, 1.0f)) : 0.0f;
  }
  // Sign from the angle-weighted pseudo-normal of the nearest feature (face, edge or vertex: Baerentzen & Aanaes);
  // a nearest feature on an open boundary (a hem, an armhole, the neck) has no inside: outside.
  float sign(int t, vec3 bary, vec3 d) const {
    int zero = 0;
    for (int k = 0; k < 3; ++k) zero += bary[k] <= 1e-6f;
    const auto& W = C->weld[size_t(t)];
    vec3 n(0);
    if (zero == 0) n = faceN[size_t(t)];
    else if (zero == 1) {
      int a = -1, b = -1;
      for (int k = 0; k < 3; ++k)
        if (bary[k] > 1e-6f) (a < 0 ? a : b) = W[size_t(k)];
      const auto& tris = C->edgeTris.at({std::min(a, b), std::max(a, b)});
      if (tris.size() < 2) return 1;
      for (int u : tris) n += faceN[size_t(u)];
    } else {
      int k = bary.x > 0.5f ? 0 : bary.y > 0.5f ? 1 : 2;
      const int wv = W[size_t(k)];
      if (C->boundaryVertex[size_t(wv)]) return 1;
      for (int u : C->vertexTris[size_t(wv)])
        for (int j = 0; j < 3; ++j)
          if (C->weld[size_t(u)][size_t(j)] == wv) n += angleAt(u, j) * faceN[size_t(u)];
    }
    lastFeature = zero;
    lastDot = glm::length(n) > 0 ? glm::dot(glm::normalize(d), glm::normalize(n)) : 9;
    return glm::dot(d, n) < 0 ? -1.0f : 1.0f;
  }
  float signedDistance(vec3 p) const {
    const glm::ivec3 c(glm::floor(p / cell));
    float best = 1e9f, sd = 1e9f;
    for (int r = 0; r <= 10; ++r) {
      for (int x = -r; x <= r; ++x)
        for (int y = -r; y <= r; ++y)
          for (int z = -r; z <= r; ++z) {
            if (std::max({std::abs(x), std::abs(y), std::abs(z)}) != r) continue;
            auto it = cells.find(key(c.x + x, c.y + y, c.z + z));
            if (it == cells.end()) continue;
            for (int t : it->second) {
              const auto& T = C->bodyTris[size_t(t)];
              vec3 bary;
              const vec3 q = closestOnTri(p, (*S)[T[0].m].p[T[0].v], (*S)[T[1].m].p[T[1].v], (*S)[T[2].m].p[T[2].v], bary);
              const float d = glm::distance(p, q);
              if (d >= best) continue;
              best = d;
              sd = sign(t, bary, p - q) * d;
              lastTri = t;
              nearest = q;
            }
          }
      if (best < float(r) * cell) break;
    }
    // A negative sign is confirmed by rays: a point inside a shell hits that shell in (nearly) every direction; one
    // outside a thin or open shell (a drawstring, a hood roll) escapes. Inside = at least 2 of 3 rays hit it.
    if (sd < 0 && lastTri >= 0) {
      const size_t mesh = C->bodyTris[size_t(lastTri)][0].m;
      vec3 a = p - nearest;
      a = glm::length(a) > 1e-7f ? glm::normalize(a) : vec3(0, 0, 1);
      const vec3 t1 = glm::normalize(std::abs(a.y) < 0.9f ? glm::cross(a, vec3(0, 1, 0)) : glm::cross(a, vec3(1, 0, 0)));
      const vec3 t2 = glm::cross(a, t1);
      int hits = 0;
      for (vec3 dir : {a, glm::normalize(a + t1), glm::normalize(a - 0.5f * t1 + 0.9f * t2)}) hits += rayHits(p, dir, mesh);
      if (hits < 2) sd = -sd;
    }
    return sd;
  }
  mutable vec3 nearest{0};
  bool rayHits(vec3 o, vec3 d, size_t mesh) const {  // Moller-Trumbore against one shell's body triangles
    for (size_t t = 0; t < C->bodyTris.size(); ++t) {
      if (C->bodyTris[t][0].m != mesh) continue;
      const vec3 v0 = P(int(t), 0), e1 = P(int(t), 1) - v0, e2 = P(int(t), 2) - v0;
      const vec3 h = glm::cross(d, e2);
      const float det = glm::dot(e1, h);
      if (std::abs(det) < 1e-12f) continue;
      const float inv = 1 / det;
      const vec3 sv = o - v0;
      const float u = inv * glm::dot(sv, h);
      if (u < 0 || u > 1) continue;
      const vec3 q = glm::cross(sv, e1);
      const float v = inv * glm::dot(d, q);
      if (v < 0 || u + v > 1) continue;
      if (inv * glm::dot(e2, q) > 1e-6f) return true;
    }
    return false;
  }
};

CharMesh charMesh(const SceneEvaluator::CharacterInstance& ci, const BodyClearanceModel& M) {
  const Skeleton& sk = ci.asset.skeleton;
  CharMesh C;
  std::vector<int> reg(sk.bones.size());
  for (size_t b = 0; b < sk.bones.size(); ++b) reg[b] = region(sk, int(b));
  std::vector<std::vector<char>> torso(ci.rig.meshes.size());
  // the hips' sides count as body down to the bottom of the engine's pelvis section (as the engine's fit)
  const float pelvisBottom = (M.body.front().p0 + sk.bones[size_t(M.body.front().bone)].head).y;
  for (size_t mi = 0; mi < ci.rig.meshes.size(); ++mi) {
    const SkinnedMesh& m = ci.rig.meshes[mi];
    torso[mi].assign(m.rest.positions.size(), 0);
    for (size_t v = 0; v < m.rest.positions.size() && v < m.joints.size(); ++v) {
      float w[6] = {0, 0, 0, 0, 0, 0};
      for (int k = 0; k < 4; ++k) {
        const int j = m.joints[v][k];
        if (j >= 0 && size_t(j) < sk.bones.size() && m.weights[v][k] > 0) w[reg[size_t(j)]] += m.weights[v][k];
      }
      torso[mi][v] = w[1] >= 0.9f || (w[1] + w[4] >= 0.9f && m.rest.positions[v].y >= pelvisBottom);
      for (int s = 0; s < 2; ++s)
        if (w[2 + s] >= 0.5f && w[4] + w[5] < 0.1f) {
          C.arm[s].push_back({mi, v});
          const int up = M.arm[s].upper, fo = M.arm[s].fore;
          const vec3 a = sk.bones[size_t(up)].head, b = sk.bones[size_t(fo)].head, p = m.rest.positions[v];
          float t = glm::dot(p - a, b - a) / glm::dot(b - a, b - a);
          // only upper-arm-carried vertices can be in the armpit band
          float wu = 0;
          for (int k = 0; k < 4; ++k)
            if (m.weights[v][k] > 0 && starts(sk.bones[size_t(std::clamp(m.joints[v][k], 0, int(sk.bones.size()) - 1))].name, "upperArm.")) wu += m.weights[v][k];
          if (wu < 0.5f) t = std::max(t, 1.0f);
          C.along[s].push_back(t);
        }
    }
    for (size_t t = 0; t + 2 < m.rest.indices.size(); t += 3) {
      const uint32_t a = m.rest.indices[t], b = m.rest.indices[t + 1], c = m.rest.indices[t + 2];
      if (starts(m.part, "hair")) break;  // hair (curls hanging onto the chest) is not body volume
      if (torso[mi][a] && torso[mi][b] && torso[mi][c]) C.bodyTris.push_back({CharMesh::V{mi, a}, {mi, b}, {mi, c}});
    }
  }
  // topology: weld by rest position (0.1 mm) within each mesh
  {
    std::map<std::tuple<size_t, long, long, long>, int> ids;
    auto id = [&](const CharMesh::V& v) {
      const vec3 p = ci.rig.meshes[v.m].rest.positions[v.v] * 10000.0f;
      auto [it, fresh] = ids.try_emplace({v.m, std::lround(p.x), std::lround(p.y), std::lround(p.z)}, int(ids.size()));
      return it->second;
    };
    for (size_t t = 0; t < C.bodyTris.size(); ++t) {
      std::array<int, 3> w{};
      for (int k = 0; k < 3; ++k) w[size_t(k)] = id(C.bodyTris[t][size_t(k)]);
      C.weld.push_back(w);
      const auto& T = C.bodyTris[t];
      const auto& R = ci.rig.meshes[T[0].m].rest;
      const vec3 n = glm::cross(R.positions[T[1].v] - R.positions[T[0].v], R.positions[T[2].v] - R.positions[T[0].v]);
      vec3 vn(0);
      if (R.normals.size() == R.positions.size()) vn = R.normals[T[0].v] + R.normals[T[1].v] + R.normals[T[2].v];
      C.flip.push_back(glm::dot(n, vn) < 0);
    }
    C.vertexTris.resize(ids.size());
    C.boundaryVertex.assign(ids.size(), 0);
    for (size_t t = 0; t < C.weld.size(); ++t)
      for (int k = 0; k < 3; ++k) {
        const int a = C.weld[t][size_t(k)], b = C.weld[t][size_t((k + 1) % 3)];
        C.vertexTris[size_t(a)].push_back(int(t));
        C.edgeTris[{std::min(a, b), std::max(a, b)}].push_back(int(t));
      }
    for (auto& [e, tris] : C.edgeTris)
      if (tris.size() < 2) C.boundaryVertex[size_t(e.first)] = C.boundaryVertex[size_t(e.second)] = 1;
  }
  // rest depth
  std::vector<mat4> rest(sk.bones.size());
  for (size_t b = 0; b < sk.bones.size(); ++b) rest[b] = glm::translate(mat4(1), sk.bones[b].head);
  std::vector<Skinned> S;
  for (const auto& m : ci.rig.meshes) S.push_back(skin(m, sk, rest));
  Grid g(S, C);
  for (int s = 0; s < 2; ++s)
    for (auto& v : C.arm[s]) C.restDepth[s].push_back(std::min(0.0f, g.signedDistance(S[v.m].p[v.v])));
  return C;
}

float angleBetween(quat a, quat b) { return 2 * std::acos(std::min(1.0f, std::abs(glm::dot(glm::normalize(a), glm::normalize(b))))); }
double mm(float m) { return std::round(m * 10000.0) / 10.0; }
}  // namespace

int main(int argc, char** argv) {
  auto scene = loadScene(argv[1]);
  if (!scene) { std::cerr << scene.error().message << "\n"; return 1; }
  SceneEvaluator on, off;
  for (SceneEvaluator* ev : {&on, &off})
    if (auto r = ev->load(*scene, EvalOptions{2.5f, 1.0f, false, 0}); !r) { std::cerr << r.error().message << "\n"; return 1; }
  if (auto r = off.setArmBodyClearance(false); !r) { std::cerr << r.error().message << "\n"; return 1; }
  const Scene& s = on.scene();
  const int stride = argc > 2 ? std::max(1, std::atoi(argv[2])) : 1;  // > 1: quick look (accelerations then meaningless)
  Json out;
  out["scene"] = argv[1];
  out["warnings_on"] = on.warnings();
  out["warnings_off"] = off.warnings();
  for (size_t c = 0; c < s.characters.size(); ++c) {
    const auto& ci = on.characters()[c];
    const BodyClearanceModel& M = *on.clearanceModel(c);
    if (!M.valid) continue;
    const CharMesh C = charMesh(ci, M);
    Json jc;
    jc["body_triangles"] = C.bodyTris.size();
    jc["capsules"] = Json::array();
    {  // capsule fit against the rest mesh: gap of each body vertex in a section's slab to that section (> 0: the mesh
       // is outside the capsule there, so a capsule-clear arm could still touch it; < 0: the capsule is fuller)
      const Skeleton& sk = ci.asset.skeleton;
      std::vector<mat4> rest(sk.bones.size());
      for (size_t b = 0; b < sk.bones.size(); ++b) rest[b] = glm::translate(mat4(1), sk.bones[b].head);
      std::set<std::pair<size_t, size_t>> verts;
      for (const auto& T : C.bodyTris)
        for (const auto& v : T) verts.insert({v.m, v.v});
      for (const auto& b : M.body) {
        const vec3 a = b.p0 + sk.bones[size_t(b.bone)].head, e = b.p1 + sk.bones[size_t(b.bone)].head;
        std::vector<float> gf, gb;
        for (auto [mi, v] : verts) {
          const vec3 p = ci.rig.meshes[mi].rest.positions[v];
          const float t = glm::dot(p - a, e - a) / glm::dot(e - a, e - a);
          if (t < 0 || t > 1) continue;
          (glm::dot(p - a, b.e2) >= 0 ? gf : gb).push_back(bodySectionGap(b, rest[size_t(b.bone)], p));
        }
        auto pct = [](std::vector<float> v, float q) {
          if (v.empty()) return 0.0f;
          std::sort(v.begin(), v.end());
          return v[std::min(v.size() - 1, size_t(q * float(v.size() - 1)))];
        };
        jc["capsules"].push_back({{"name", b.name}, {"r_side_mm", mm(b.r1)}, {"r_front_mm", mm(b.r2)},
                                  {"front_vertices", gf.size()}, {"front_mesh_gap_p50_mm", mm(pct(gf, 0.5f))},
                                  {"front_mesh_gap_p99_mm", mm(pct(gf, 0.99f))}, {"front_mesh_gap_max_mm", mm(pct(gf, 1.0f))},
                                  {"back_mesh_gap_p99_mm", mm(pct(gb, 0.99f))}});
      }
    }
    struct Acc { float min = 1e9f; double at = 0; void add(float v, double f) { if (v < min) min = v, at = f; } };
    for (int side = 0; side < 2; ++side) {
      const char sc = side == 0 ? 'L' : 'R';
      const ArmModel& A = M.arm[side];
      Acc capOn, capOff, meshOn, meshOff, rawOn, armpitOn, armpitOff, t030gap, t030upper, t030gapOff, t030upperOff;
      float maxAngle = 0, maxWrist = 0, maxAcc = 0, maxWristAcc = 0, maxWristAccOff = 0;
      double maxAngleAt = 0;
      int changed = 0;
      std::vector<float> angS, angE;
      std::vector<vec3> wristOn, wristOff;
      Json frames = Json::array();
      for (int f = s.frameStart; f <= s.frameEnd; f += stride) {
        Pose pOn, pOff;
        const auto Gon = on.characterGlobals(c, f, &pOn), Goff = off.characterGlobals(c, f, &pOff);
        const float cOn = armBodyGap(M, Gon, sc), cOff = armBodyGap(M, Goff, sc);
        capOn.add(cOn, f), capOff.add(cOff, f);
        const ArmClearance a1 = armClearance(M, Gon, sc), a0 = armClearance(M, Goff, sc);
        t030gap.add(a1.gap, f), t030upper.add(a1.upperGap, f), t030gapOff.add(a0.gap, f), t030upperOff.add(a0.upperGap, f);
        float mOn = 1e9f, mOff = 1e9f, rOn = 1e9f, apOn = 1e9f, apOff = 1e9f;
        for (int pass = 0; pass < 2; ++pass) {
          const auto& G = pass == 0 ? Gon : Goff;
          std::vector<Skinned> S;
          for (const auto& m : ci.rig.meshes) S.push_back(skin(m, ci.asset.skeleton, G));
          Grid g(S, C);
          for (size_t i = 0; i < C.arm[side].size(); ++i) {
            const auto& v = C.arm[side][i];
            const float sd = g.signedDistance(S[v.m].p[v.v]);
            const float rel = sd - C.restDepth[side][i];
            const bool armpit = C.along[side][i] < 0.4f;
            if (pass == 0 && !armpit && rel < mOn && std::getenv("T040_DEBUG")) {
              const int t = g.lastTri;
              const auto& T = C.bodyTris[size_t(t)];
              std::fprintf(stderr, "f%d %s arm %s v%zu sd %.1f rest %.1f along %.2f | body %s tri %d feat %d dot %.2f boundaryV %d%d%d\n", f,
                           s.characters[c].name.c_str(), ci.rig.meshes[v.m].part.c_str(), v.v, sd * 1000, C.restDepth[side][i] * 1000,
                           C.along[side][i], ci.rig.meshes[T[0].m].part.c_str(), t, g.lastFeature, g.lastDot, C.boundaryVertex[size_t(C.weld[size_t(t)][0])],
                           C.boundaryVertex[size_t(C.weld[size_t(t)][1])], C.boundaryVertex[size_t(C.weld[size_t(t)][2])]);
            }
            if (pass == 0) {
              if (armpit) apOn = std::min(apOn, rel);
              else mOn = std::min(mOn, rel), rOn = std::min(rOn, sd);
            } else {
              if (armpit) apOff = std::min(apOff, rel);
              else mOff = std::min(mOff, rel);
            }
          }
        }
        meshOn.add(mOn, f), meshOff.add(mOff, f), rawOn.add(rOn, f), armpitOn.add(apOn, f), armpitOff.add(apOff, f);
        const float as = angleBetween(pOn.local[size_t(A.upper)], pOff.local[size_t(A.upper)]);
        const float ae = angleBetween(pOn.local[size_t(A.fore)], pOff.local[size_t(A.fore)]);
        const vec3 wOn(Gon[size_t(A.hand)][3]), wOff(Goff[size_t(A.hand)][3]);
        changed += (as > 1e-5f || ae > 1e-5f);
        if (std::max(as, ae) > maxAngle) maxAngle = std::max(as, ae), maxAngleAt = f;
        maxWrist = std::max(maxWrist, glm::distance(wOn, wOff));
        angS.push_back(as), angE.push_back(ae), wristOn.push_back(wOn), wristOff.push_back(wOff);
        frames.push_back({{"f", f}, {"capsule_mm", mm(cOn)}, {"capsule_off_mm", mm(cOff)}, {"mesh_mm", mm(mOn)},
                          {"mesh_off_mm", mm(mOff)}, {"armpit_mm", mm(apOn)}, {"shoulder_deg", glm::degrees(as)},
                          {"elbow_deg", glm::degrees(ae)}, {"wrist_offset_mm", mm(glm::distance(wOn, wOff))}});
      }
      for (size_t i = 1; i + 1 < angS.size(); ++i) {
        maxAcc = std::max({maxAcc, std::abs(angS[i + 1] - 2 * angS[i] + angS[i - 1]), std::abs(angE[i + 1] - 2 * angE[i] + angE[i - 1])});
        maxWristAcc = std::max(maxWristAcc, glm::length(wristOn[i + 1] - 2.0f * wristOn[i] + wristOn[i - 1]));
        maxWristAccOff = std::max(maxWristAccOff, glm::length(wristOff[i + 1] - 2.0f * wristOff[i] + wristOff[i - 1]));
      }
      jc[std::string("arm_") + sc] = {
          {"mesh_min_mm", mm(meshOn.min)}, {"mesh_min_frame", meshOn.at}, {"mesh_min_off_mm", mm(meshOff.min)},
          {"mesh_min_off_frame", meshOff.at}, {"mesh_raw_min_mm", mm(rawOn.min)},
          {"armpit_band_min_mm", mm(armpitOn.min)}, {"armpit_band_min_off_mm", mm(armpitOff.min)},
          {"capsule_min_mm", mm(capOn.min)}, {"capsule_min_frame", capOn.at}, {"capsule_min_off_mm", mm(capOff.min)},
          {"t030_gap_min_mm", mm(t030gap.min)}, {"t030_gap_min_off_mm", mm(t030gapOff.min)},
          {"t030_upper_min_mm", mm(t030upper.min)}, {"t030_upper_min_off_mm", mm(t030upperOff.min)},
          {"frames_corrected", changed}, {"max_correction_deg", glm::degrees(maxAngle)}, {"max_correction_frame", maxAngleAt},
          {"max_wrist_offset_mm", mm(maxWrist)}, {"max_correction_accel_deg_per_frame2", glm::degrees(maxAcc)},
          {"max_wrist_accel_mm_per_frame2", mm(maxWristAcc)}, {"max_wrist_accel_off_mm_per_frame2", mm(maxWristAccOff)},
          {"arm_vertices", C.arm[side].size()}, {"frames", frames}};
    }
    out["characters"][s.characters[c].name] = jc;
  }
  std::cout << out.dump(1) << "\n";
}
