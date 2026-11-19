// T-051 evidence: per-finger grasp measures on a resolved shot (current cast packages), per held hand and frame.
// Not part of the build:
//   g++ -std=c++23 -O2 -I engine docs/evaluation/animation/T-051/measure_t051.cpp -Lbuild/engine -lplush_scene \
//       -lplush_model -lplush_fuzz -lplush_anim -lplush_geom -lplush_core -o build/measure_t051
//   build/measure_t051 <resolved scene.json> --prop cup [--asset <asset.json>] --hand <character> <L|R> <socket> <band lo> <band hi> <from> <to> ...
// (run from the repository root). Band lo / hi are the grasp site's band in the prop frame (felt_cup affordances).
// Per frame: tip_gap_mm = max |fingertip skin - cup surface| (skin radius = fingertipRadius of the skeleton),
// deepest_mm = min (fingertip or knuckle centre - surface) (< 0: inside the collision proxy), band_out_mm = how far
// the furthest fingertip centre (thumb included) is outside the band, thumb_side_mm (< 0: the thumb tip is on the
// other half of the cup from the fingertips), tip_heights_mm (prop frame), digit_points (world: tip, knuckle per
// digit, thumb first), wrist / palm world positions (compare two runs: band vs no band).
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
  std::string propName = "cup", assetPath = "content/assets/felt_cup.asset.json";
  struct H {
    std::string who, socket;
    char side;
    float lo, hi;
    int from, to;
  };
  std::vector<H> hands;
  for (int i = 2; i < argc; ++i) {
    const std::string a = argv[i];
    if (a == "--prop" && i + 1 < argc) propName = argv[++i];
    else if (a == "--asset" && i + 1 < argc) assetPath = argv[++i];
    else if (a == "--hand" && i + 7 < argc) {
      H h{argv[i + 1], argv[i + 3], argv[i + 2][0], std::stof(argv[i + 4]), std::stof(argv[i + 5]), std::stoi(argv[i + 6]),
          std::stoi(argv[i + 7])};
      hands.push_back(h);
      i += 7;
    }
  }
  SceneEvaluator ev;
  if (auto r = ev.load(*scene, EvalOptions{2.5f, 1.0f, false, 0}); !r) return std::fprintf(stderr, "%s\n", r.error().message.c_str()), 1;
  for (const auto& w : ev.warnings()) std::fprintf(stderr, "warning: %s\n", w.c_str());
  size_t p = 0;
  for (; p < ev.scene().props.size(); ++p)
    if (ev.scene().props[p].name == propName) break;
  if (p == ev.scene().props.size()) return std::fprintf(stderr, "no prop %s\n", propName.c_str()), 1;
  auto loaded = loadAsset(assetPath);
  if (!loaded) return std::fprintf(stderr, "%s\n", loaded.error().message.c_str()), 1;
  const PropAsset& asset = *loaded;
  const float R = asset.mesh.radius * (asset.scaleMetres > 0 ? asset.scaleMetres : 1.0f);
  std::cout << "{\"scene\": \"" << argv[1] << "\", \"frames\": [\n";
  bool first = true;
  for (const H& h : hands) {
    size_t c = 0;
    for (; c < ev.scene().characters.size(); ++c)
      if (ev.scene().characters[c].name == h.who) break;
    if (c == ev.characters().size()) return std::fprintf(stderr, "no character %s\n", h.who.c_str()), 1;
    const Skeleton& sk = ev.characters()[c].asset.skeleton;
    const std::string s = std::string(".") + h.side;
    const int hb = sk.find("hand" + s);
    const float r = fingertipRadius(sk, h.side);
    const HandGrip grip = handGrip(sk, hb, h.side);
    for (int f = h.from; f <= h.to; ++f) {
      const auto g = ev.characterGlobals(c, f);
      const mat4 P = ev.propWorld(p, f), Pi = glm::inverse(P);
      const vec3 axis = glm::normalize(vec3(P[1])), base = vec3(P[3]);
      auto radial = [&](vec3 q) {
        q -= base;
        return glm::length(q - axis * glm::dot(q, axis));
      };
      std::vector<vec3> tips, knuckles;
      std::vector<std::pair<std::string, std::string>> chains{{"thumbA", "thumbB"}};
      for (int k = 0; k < 4; ++k) chains.push_back({std::format("f{}a", k), std::format("f{}b", k)});
      for (auto& [a, b] : chains) {
        const int ia = sk.find(a + s), ib = sk.find(b + s);
        if (ia < 0 || ib < 0) continue;
        knuckles.push_back(vec3(g[size_t(ib)][3]));
        tips.push_back(vec3(g[size_t(ib)] * vec4(sk.bones[size_t(ib)].head - sk.bones[size_t(ia)].head, 1)));
      }
      float gap = 0, deepest = 1, bandOut = -1, fingers = 0;
      std::string heights, points;  // fingertip centre heights in the prop frame (mm), thumb first; world points
      const vec3 palmN = glm::normalize(mat3(g[size_t(hb)]) * grip.palmNormal);
      const vec3 split = glm::normalize(glm::cross(axis, palmN));
      for (size_t i = 0; i < tips.size(); ++i) {
        gap = std::max(gap, std::abs(radial(tips[i]) - R - r));
        deepest = std::min({deepest, radial(tips[i]) - R, radial(knuckles[i]) - R});
        const float y = vec3(Pi * vec4(tips[i], 1)).y;
        heights += std::format("{}{:.1f}", heights.empty() ? "" : ", ", y * 1e3);
        for (const vec3& q : {tips[i], knuckles[i]})
          points += std::format("{}[{:.6f}, {:.6f}, {:.6f}]", points.empty() ? "" : ", ", q.x, q.y, q.z);
        bandOut = std::max({bandOut, h.lo - y, y - h.hi});
        if (i > 0) fingers += glm::dot(tips[i] - base, split);
      }
      const float thumbSide = glm::dot(tips[0] - base, split) * (fingers >= 0 ? 1.0f : -1.0f);
      const vec3 wrist = vec3(g[size_t(hb)][3]), palm = ev.handGripPoint(c, h.side, f);
      std::cout << (first ? "" : ",\n")
                << std::format("  {{\"hand\": \"{}.{}\", \"frame\": {}, \"tip_gap_mm\": {:.3f}, \"deepest_mm\": {:.3f}, "
                               "\"band_out_mm\": {:.3f}, \"thumb_side_mm\": {:.3f}, \"skin_radius_mm\": {:.3f}, "
                               "\"tip_heights_mm\": [{}], \"digit_points\": [{}], \"wrist\": [{:.7f}, {:.7f}, {:.7f}], \"palm\": [{:.7f}, {:.7f}, {:.7f}]}}",
                               h.who, h.side, f, gap * 1e3, deepest * 1e3, bandOut * 1e3, thumbSide * 1e3, r * 1e3, heights, points, wrist.x,
                               wrist.y, wrist.z, palm.x, palm.y, palm.z);
      first = false;
    }
  }
  std::cout << "\n]}\n";
  return 0;
}
