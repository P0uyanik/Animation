// T-191 character-character contact measure: per frame, how deep the characters' bodies pass through each other, for
// every pair of characters. Two measures, both from the engine's own poses (SceneEvaluator::characterGlobals: clips,
// IK, constraints, secondary motion):
//   capsule  the T-191 body-part capsules (collision.h deriveBodyParts: one or two capsules per body role, fitted to
//            the skinned rest meshes, garments and hair included, 90th-percentile radius) of one character against the
//            other's: the signed gap of the closest capsule pair (negative = penetration depth), and which parts.
//   mesh     the skinned mesh vertices (linear blend skinning of the rest meshes, every --stride-th vertex, morphs
//            ignored) of one character inside the other's capsules: the deepest vertex (negative = that deep inside),
//            its own part and the part it is in. The capsules sit just inside the surface (90 % of a part's vertices
//            are within its radius), so a vertex inside one is a vertex inside the other body.
//   head     the T-096 head and hair shells (headGap; negative = overlapping, not a depth).
// Not part of the build or the gate; built like collision_trace.cpp:
//   g++ -std=c++23 -O2 -I engine -I build/fast-dev/engine tools/motion_checks/body_contact.cpp -Lbuild/fast-dev/engine \
//       -lplush_scene -lplush_model -lplush_anim -lplush_fuzz -lplush_geom -lplush_core -lembree4 -ltbb -o build/body_contact
//   build/body_contact <shot.resolved.scene.json> [--frames A-B] [--stride N] > contact.json   (from the repository root)
// Output plush.body_contact/1: {"frames": [...], "characters": [{name, capsules: [{part, r}]}],
//   "pairs": [{"a", "b", "capsule": {"gap": [...], "partA": [...], "partB": [...]},
//              "mesh": {"gap": [...], "who": [...], "part": [...], "in": [...]}, "head_gap": [...]}]}
// Metres. tools/motion_checks/body_contact_report.py turns one or more of these into the worst-case tables.
#include <cstdio>
#include <cstring>
#include <iostream>

#include "model/character.h"
#include "scene/collision.h"
#include "scene/scene.h"

using namespace plush;

namespace {
struct Sample {
  const SkinnedMesh* mesh;
  size_t v;
  std::string part;
};
}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) return std::fprintf(stderr, "usage: body_contact <scene.json> [--frames A-B] [--stride N]\n"), 2;
  int fa = -1, fb = -1, stride = 4;
  for (int i = 2; i + 1 < argc; i += 2) {
    if (!std::strcmp(argv[i], "--frames")) std::sscanf(argv[i + 1], "%d-%d", &fa, &fb);
    else if (!std::strcmp(argv[i], "--stride")) stride = std::max(1, std::atoi(argv[i + 1]));
  }
  auto scene = loadScene(argv[1]);
  if (!scene) return std::fprintf(stderr, "%s\n", scene.error().message.c_str()), 1;
  SceneEvaluator ev;
  if (auto r = ev.load(*scene, EvalOptions{2.5f, 1.0f, false, 0}); !r) return std::fprintf(stderr, "%s\n", r.error().message.c_str()), 1;
  if (fa < 0) fa = scene->frameStart, fb = scene->frameEnd;
  const size_t n = ev.characters().size();
  std::vector<BodyParts> P;
  std::vector<CollisionBody> H;
  std::vector<std::vector<Sample>> S(n);
  Json out = {{"format", "plush.body_contact"}, {"version", 1}, {"scene", argv[1]}, {"stride", stride},
              {"frames", Json::array()}, {"characters", Json::array()}, {"pairs", Json::array()}};
  for (size_t c = 0; c < n; ++c) {
    const auto& ci = ev.characters()[c];
    P.push_back(deriveBodyParts(ci.asset.skeleton, ci.rig.meshes));
    H.emplace_back();
    addHeadVolumes(H.back(), ci.asset.skeleton, ci.rig.meshes);
    Json jc = {{"name", scene->characters[c].name}, {"capsules", Json::array()}};
    for (const auto& k : P.back().capsules) jc["capsules"].push_back({{"part", k.part}, {"r", k.r}});
    out["characters"].push_back(jc);
    // vertex samples and the part each belongs to (its rest position's nearest own capsule)
    size_t i = 0;
    for (const SkinnedMesh& m : ci.rig.meshes)
      for (size_t v = 0; v < m.rest.positions.size() && v < m.joints.size(); ++v, ++i) {
        if (i % size_t(stride)) continue;
        S[c].push_back({&m, v, ""});
      }
    std::vector<mat4> rest(ci.asset.skeleton.bones.size());
    for (size_t b = 0; b < rest.size(); ++b) rest[b] = glm::translate(mat4(1), ci.asset.skeleton.bones[b].head);
    for (auto& s : S[c]) pointBodyGap(P[c], rest, s.mesh->rest.positions[s.v], &s.part);
  }
  for (size_t a = 0; a < n; ++a)
    for (size_t b = a + 1; b < n; ++b)
      out["pairs"].push_back({{"a", scene->characters[a].name}, {"b", scene->characters[b].name}});
  for (int f = fa; f <= fb; ++f) {
    out["frames"].push_back(f);
    std::vector<std::vector<mat4>> G(n);
    std::vector<std::vector<vec3>> X(n);  // skinned sample positions
    for (size_t c = 0; c < n; ++c) {
      G[c] = ev.characterGlobals(c, f);
      const Skeleton& sk = ev.characters()[c].asset.skeleton;
      std::vector<mat4> skin(G[c].size());
      for (size_t j = 0; j < skin.size(); ++j) skin[j] = G[c][j] * glm::translate(mat4(1), -sk.bones[j].head);
      for (const auto& s : S[c]) {
        mat4 M(0.0f);
        for (int k = 0; k < 4; ++k)
          if (const float w = s.mesh->weights[s.v][k]; w > 0) M += w * skin[size_t(s.mesh->joints[s.v][k])];
        X[c].push_back(vec3(M * vec4(s.mesh->rest.positions[s.v], 1)));
      }
    }
    size_t k = 0;
    for (size_t a = 0; a < n; ++a)
      for (size_t b = a + 1; b < n; ++b, ++k) {
        Json& jp = out["pairs"][k];
        const BodyGap g = bodyGap(P[a], G[a], P[b], G[b]);
        jp["capsule"]["gap"].push_back(g.gap);
        jp["capsule"]["partA"].push_back(g.partA);
        jp["capsule"]["partB"].push_back(g.partB);
        float best = 1e9f;
        std::string who, part, in;
        for (auto [x, y] : {std::pair{a, b}, std::pair{b, a}}) {
          // broad phase: the other body's capsule bounds
          vec3 lo(1e9f), hi(-1e9f);
          for (const auto& c : P[y].capsules) {
            vec3 p0, p1;
            bodyPartSegment(c, G[y], p0, p1);
            lo = glm::min(lo, glm::min(p0, p1) - c.r), hi = glm::max(hi, glm::max(p0, p1) + c.r);
          }
          for (size_t i = 0; i < X[x].size(); ++i) {
            const vec3 p = X[x][i];
            if (glm::any(glm::lessThan(p, lo)) || glm::any(glm::greaterThan(p, hi))) continue;
            std::string pin;
            const float gg = pointBodyGap(P[y], G[y], p, &pin);
            if (gg < best) best = gg, who = scene->characters[x].name, part = S[x][i].part, in = pin;
          }
        }
        jp["mesh"]["gap"].push_back(best);
        jp["mesh"]["who"].push_back(who);
        jp["mesh"]["part"].push_back(part);
        jp["mesh"]["in"].push_back(in);
        jp["head_gap"].push_back(headGap(H[a], G[a], H[b], G[b]).gap);
      }
  }
  out["warnings"] = ev.warnings();
  std::cout << out.dump() << std::endl;
}
