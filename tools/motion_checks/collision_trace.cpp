// T-125 interpenetration trace: per-frame signed gaps (metres; negative = inside) from the engine's own collision
// bodies (engine/scene/collision.h, interaction.h: the bodies the arm planner uses), for every character and pair, and
// the prop collision proxies (content/assets/*.asset.json "collision"). Not part of the build or the gate:
//   g++ -std=c++23 -O2 -I engine -I build/engine tools/motion_checks/collision_trace.cpp -Lbuild/engine -lplush_scene \
//       -lplush_model -lplush_anim -lplush_fuzz -lplush_geom -lplush_core -lembree4 -ltbb -o build/collision_trace
//   build/collision_trace <shot.resolved.scene.json> > trace.json          (run from the repository root)
// Output (plush.collision_trace/1), one value per scene frame:
//   characters[i].arm.<L|R>: {gap, part, against} the limb capsules (forearm wrist half, hand; sleeve included) against
//     the character's own torso + garment shell (armClearance: body-body / body-garment); upper.<L|R>: the upper arm /
//     elbow surface samples (relative to their rest depth).
//   pairs[k]: head_gap (head and hair volumes, T-096 shells) and limb.<a.L|...>: one character's limb capsules against
//     the other's torso shell (character-character).
//   props[j]: hand.<char.L|...>: hand capsule vs the prop proxy (hand-prop); body.<char>: the proxy's surface samples
//     against each torso shell (prop-body).
#include <cstdio>
#include <filesystem>
#include <iostream>

#include "scene/asset_library.h"
#include "scene/collision.h"
#include "scene/interaction.h"
#include "scene/scene.h"

using namespace plush;

namespace {
float segPointDist(vec3 a, vec3 b, vec3 p) {
  const vec3 ab = b - a;
  const float L = glm::dot(ab, ab);
  const float t = L > 0 ? glm::clamp(glm::dot(p - a, ab) / L, 0.0f, 1.0f) : 0.0f;
  return glm::distance(a + t * ab, p);
}
// Distance between two segments (sampled on the first, exact on the second; 33 samples is < 0.1 mm for these sizes).
float segSegDist(vec3 a, vec3 b, vec3 c, vec3 d) {
  float best = 1e9f;
  for (int i = 0; i <= 32; ++i) best = std::min(best, segPointDist(c, d, glm::mix(a, b, float(i) / 32)));
  return best;
}
std::optional<PropAsset> findAsset(const std::filesystem::path& root, const std::string& id) {
  std::error_code ec;
  for (const auto& e : std::filesystem::directory_iterator(root / "content" / "assets", ec)) {
    if (!e.path().string().ends_with(".asset.json")) continue;
    auto a = loadAsset(e.path());
    if (a && a->id == id) return *a;
  }
  return std::nullopt;
}
// The prop proxy as a world capsule (segment + radius); box and sphere proxies use their bounding sphere axis.
struct Capsule {
  vec3 a{0}, b{0};
  float r = 0;
};
Capsule proxyWorld(const PropAsset& a, const mat4& P) {
  const float k = a.scaleMetres > 0 ? a.scaleMetres : 1;
  Capsule c;
  mat4 T = P;
  if (a.collision) T = P * assetTransformMatrix(a.collision->transform);
  if (a.collision && a.collision->type == AssetCollisionProxy::Type::Capsule) {
    const float half = std::max(0.0f, a.collision->height * 0.5f - a.collision->radius) * k;
    c.r = a.collision->radius * k;
    // Capsule axis along local +Y, centred at the proxy transform (asset convention: tip-to-tip height). The felt cup
    // proxy has no transform, so its centre sits at the asset origin; the cup body spans y 0..height above it.
    const vec3 o = vec3(T * vec4(0, a.collision->height * 0.5f * k, 0, 1));
    const vec3 up = glm::normalize(vec3(T[1]));
    c.a = o - up * half, c.b = o + up * half;
  } else if (a.collision && a.collision->type == AssetCollisionProxy::Type::Sphere) {
    c.r = a.collision->radius * k;
    c.a = c.b = vec3(T[3]);
  } else {
    const vec3 s = (a.collision ? a.collision->size : a.mesh.size) * k * 0.5f;
    c.r = std::min({s.x, s.y, s.z});
    c.a = c.b = vec3(T[3]);
  }
  return c;
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) return std::fprintf(stderr, "usage: collision_trace <scene.json>\n"), 2;
  auto scene = loadScene(argv[1]);
  if (!scene) return std::fprintf(stderr, "%s\n", scene.error().message.c_str()), 1;
  SceneEvaluator ev;
  if (auto r = ev.load(*scene, EvalOptions{2.5f, 1.0f, false, 0}); !r) return std::fprintf(stderr, "%s\n", r.error().message.c_str()), 1;
  const size_t n = ev.characters().size();
  std::vector<BodyClearanceModel> M;
  for (const auto& ci : ev.characters()) {
    M.push_back(bodyClearanceModel(ci.asset.skeleton, ci.rig.meshes, ci.asset.collisionBlock));
    addHeadVolumes(M.back().collision, ci.asset.skeleton, ci.rig.meshes);
  }
  const auto root = std::filesystem::current_path();
  std::vector<std::optional<PropAsset>> assets;
  for (const auto& p : scene->props) assets.push_back(findAsset(root, p.id));

  Json out = {{"format", "plush.collision_trace"}, {"version", 1}, {"scene", argv[1]}, {"frames", Json::array()},
              {"characters", Json::array()}, {"pairs", Json::array()}, {"props", Json::array()}};
  for (size_t c = 0; c < n; ++c)
    out["characters"].push_back({{"name", scene->characters[c].name}, {"source", M[c].collision.source},
                                 {"valid", M[c].valid}, {"head_volumes", M[c].collision.heads.size()}});
  for (size_t a = 0; a < n; ++a)
    for (size_t b = a + 1; b < n; ++b) out["pairs"].push_back({{"a", scene->characters[a].name}, {"b", scene->characters[b].name}});
  for (size_t j = 0; j < scene->props.size(); ++j) {
    Json jp = {{"name", scene->props[j].name}, {"id", scene->props[j].id}, {"proxy", bool(assets[j] && assets[j]->collision)}};
    out["props"].push_back(jp);
  }
  for (int f = scene->frameStart; f <= scene->frameEnd; ++f) {
    out["frames"].push_back(f);
    std::vector<std::vector<mat4>> G;
    for (size_t c = 0; c < n; ++c) G.push_back(ev.characterGlobals(c, f));
    for (size_t c = 0; c < n; ++c) {
      auto& jc = out["characters"][c];
      for (char side : {'L', 'R'}) {
        const std::string s(1, side);
        const ArmClearance ac = armClearance(M[c], G[c], side);
        jc["arm"][s]["gap"].push_back(ac.gap);
        jc["arm"][s]["part"].push_back(ac.part);
        jc["arm"][s]["against"].push_back(ac.against);
        jc["upper"][s].push_back(ac.upperGap);
      }
    }
    size_t k = 0;
    for (size_t a = 0; a < n; ++a)
      for (size_t b = a + 1; b < n; ++b, ++k) {
        auto& jk = out["pairs"][k];
        jk["head_gap"].push_back(headGap(M[a].collision, G[a], M[b].collision, G[b]).gap);
        for (auto [x, y] : {std::pair{a, b}, std::pair{b, a}})
          for (const auto& l : M[x].collision.limbs) {
            vec3 p0, p1;
            limbSegment(l, G[x], p0, p1);
            const Clearance cl = segmentClearance(M[y].collision, G[y], p0, p1, l.r, l.side);
            jk["limb"][scene->characters[x].name + "." + l.name].push_back(cl.gap);
          }
      }
    for (size_t j = 0; j < scene->props.size(); ++j) {
      if (!assets[j]) continue;
      auto& jp = out["props"][j];
      const Capsule P = proxyWorld(*assets[j], ev.propWorld(j, f));
      for (size_t c = 0; c < n; ++c) {
        for (const auto& l : M[c].collision.limbs) {
          if (!l.name.starts_with("hand")) continue;
          vec3 p0, p1;
          limbSegment(l, G[c], p0, p1);
          jp["hand"][scene->characters[c].name + "." + l.name].push_back(segSegDist(p0, p1, P.a, P.b) - l.r - P.r);
        }
        // proxy surface samples (3 rings x 8 + the two tips) against the torso shell
        float worst = 1e9f;
        const vec3 ax = P.b - P.a, u = glm::length(ax) > 1e-6f ? glm::normalize(ax) : vec3(0, 1, 0);
        const vec3 e1 = glm::normalize(glm::cross(u, std::abs(u.x) < 0.9f ? vec3(1, 0, 0) : vec3(0, 0, 1))), e2 = glm::cross(u, e1);
        for (int i = 0; i < 3; ++i)
          for (int q = 0; q < 8; ++q) {
            const float ang = 6.2831853f * float(q) / 8;
            const vec3 p = glm::mix(P.a, P.b, float(i) / 2) + P.r * (std::cos(ang) * e1 + std::sin(ang) * e2);
            worst = std::min(worst, segmentClearance(M[c].collision, G[c], p, p, 0, 'R').gap);
          }
        for (vec3 p : {P.a - u * P.r, P.b + u * P.r}) worst = std::min(worst, segmentClearance(M[c].collision, G[c], p, p, 0, 'R').gap);
        jp["body"][scene->characters[c].name].push_back(worst);
      }
    }
  }
  out["warnings"] = ev.warnings();
  std::cout << out.dump() << std::endl;
}
