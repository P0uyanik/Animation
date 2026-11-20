// T-157 evidence: per-digit grasp measures on a resolved shot (as T-051 measure_t051, per digit). Not part of the build:
//   g++ -std=c++23 -O2 -I engine docs/evaluation/animation/T-157/measure_t157.cpp -Lbuild/engine -lplush_scene \
//       -lplush_model -lplush_fuzz -lplush_anim -lplush_geom -lplush_core -o build/measure_t157
//   build/measure_t157 <resolved scene.json> --hand <character> <L|R> <from> <to> ...
// Per frame and digit (thumb, little, ring, middle, index): tip centre height in the cup frame (mm), tip gap (tip skin
// to cup surface, mm; < 0: skin inside), min skin clearance over the digit's points (segment heads, middles, tip; mm;
// < 0 = penetration of the cup's side), and the closest pair of neighbouring fingertips (mm). Cup: felt_cup.
#include <cstdio>
#include <format>
#include <iostream>
#include <string>
#include <vector>

#include "anim/animation.h"
#include "scene/asset_library.h"
#include "scene/interaction.h"
#include "scene/scene.h"

using namespace plush;

int main(int argc, char** argv) {
  if (argc < 2) return std::fprintf(stderr, "usage: see the header\n"), 2;
  auto scene = loadScene(argv[1]);
  if (!scene) return std::fprintf(stderr, "%s\n", scene.error().message.c_str()), 1;
  struct H {
    std::string who;
    char side;
    int from, to;
  };
  std::vector<H> hands;
  for (int i = 2; i < argc; ++i)
    if (std::string(argv[i]) == "--hand" && i + 4 < argc) {
      hands.push_back({argv[i + 1], argv[i + 2][0], std::stoi(argv[i + 3]), std::stoi(argv[i + 4])});
      i += 4;
    }
  SceneEvaluator ev;
  if (auto r = ev.load(*scene, EvalOptions{2.5f, 1.0f, false, 0}); !r) return std::fprintf(stderr, "%s\n", r.error().message.c_str()), 1;
  size_t p = 0;
  for (; p < ev.scene().props.size(); ++p)
    if (ev.scene().props[p].name == "cup") break;
  if (p == ev.scene().props.size()) return std::fprintf(stderr, "no prop cup\n"), 1;
  auto asset = loadAsset("content/assets/felt_cup.asset.json");
  if (!asset) return std::fprintf(stderr, "%s\n", asset.error().message.c_str()), 1;
  const float R = asset->mesh.radius * (asset->scaleMetres > 0 ? asset->scaleMetres : 1.0f);
  std::cout << "{\"scene\": \"" << argv[1] << "\", \"frames\": [\n";
  bool first = true;
  for (const H& h : hands) {
    size_t c = 0;
    for (; c < ev.scene().characters.size(); ++c)
      if (ev.scene().characters[c].name == h.who) break;
    if (c == ev.characters().size()) return std::fprintf(stderr, "no character %s\n", h.who.c_str()), 1;
    const Skeleton& sk = ev.characters()[c].asset.skeleton;
    const std::string s = std::string(".") + h.side;
    const float r = fingertipRadius(sk, h.side);
    for (int f = h.from; f <= h.to; ++f) {
      const auto g = ev.characterGlobals(c, f);
      const mat4 P = ev.propWorld(p, f), Pi = glm::inverse(P);
      const vec3 axis = glm::normalize(vec3(P[1])), base = vec3(P[3]);
      auto radial = [&](vec3 q) {
        q -= base;
        return glm::length(q - axis * glm::dot(q, axis));
      };
      std::string hs, gaps, clears;
      std::vector<vec3> ftips;
      for (const auto& [a, b] : std::vector<std::pair<std::string, std::string>>{
               {"thumbA", "thumbB"}, {"f0a", "f0b"}, {"f1a", "f1b"}, {"f2a", "f2b"}, {"f3a", "f3b"}}) {
        const int ia = sk.find(a + s), ib = sk.find(b + s);
        if (ia < 0 || ib < 0) continue;
        const vec3 ha = vec3(g[size_t(ia)][3]), kn = vec3(g[size_t(ib)][3]);
        const vec3 tip = vec3(g[size_t(ib)] * vec4(sk.bones[size_t(ib)].head - sk.bones[size_t(ia)].head, 1));
        float cl = 1;
        for (const vec3& q : {ha, 0.5f * (ha + kn), kn, 0.5f * (kn + tip), tip}) cl = std::min(cl, radial(q) - R - r);
        const float y = vec3(Pi * vec4(tip, 1)).y;
        const std::string sep = hs.empty() ? "" : ", ";
        hs += std::format("{}{:.1f}", sep, y * 1e3);
        gaps += std::format("{}{:.2f}", sep, (radial(tip) - R - r) * 1e3);
        clears += std::format("{}{:.2f}", sep, cl * 1e3);
        if (a[0] == 'f') ftips.push_back(tip);
      }
      float apart = 1;
      for (size_t i = 1; i < ftips.size(); ++i) apart = std::min(apart, glm::distance(ftips[i - 1], ftips[i]));
      const vec3 wrist = vec3(g[size_t(sk.find("hand" + s))][3]);
      std::cout << (first ? "" : ",\n")
                << std::format("  {{\"hand\": \"{}.{}\", \"frame\": {}, \"skin_radius_mm\": {:.2f}, \"tip_heights_mm\": [{}], "
                               "\"tip_gap_mm\": [{}], \"min_clearance_mm\": [{}], \"closest_tips_mm\": {:.1f}, "
                               "\"wrist\": [{:.7f}, {:.7f}, {:.7f}]}}",
                               h.who, h.side, f, r * 1e3, hs, gaps, clears, apart * 1e3, wrist.x, wrist.y, wrist.z);
      first = false;
    }
  }
  std::cout << "\n]}\n";
  return 0;
}
