// T-171 evidence: per-frame, per-digit hand measures on a resolved shot. Not part of the build:
//   g++ -std=c++23 -O2 -I engine -I <glm/json include dirs> docs/evaluation/interaction/T-171/measure_t171.cpp \
//       <the plush_* static libraries of the build> -o build/measure_t171      (see build_measure.sh)
//   build/measure_t171 <resolved scene.json> --prop cup content/assets/felt_cup.asset.json \
//       --hand <character> <L|R> <from> <to> ...
// The prop is taken as a capped solid cylinder (radius R, height H, base at the prop origin, axis +Y): stricter than
// the real cup, which is open at the top. Digits are listed thumb, then the fingers in ANATOMICAL order index ..
// little (the finger whose root is nearest the thumb root is the index), whatever the bone numbering of the package.
// Per frame and digit:
//   tip_gap_mm   fingertip skin to the solid (negative = inside)
//   clear_mm     minimum skin clearance over the digit's moving points (segment middles, knuckle, tip)
//   root_mm      skin clearance of the digit's root pivot (fixed in the palm: a wrist-placement measure, not a finger one)
//   curl_deg     rotation of the two segments from rest (a, b)
//   tip_h_mm     fingertip height along the prop axis (root_h_mm: the same for the digit roots)
// and per frame: neighbouring fingertip distances (index-middle, middle-ring, ring-little), the same for the
// knuckles, the wrist position and the wrist-to-prop-axis distance.
// Round 3 (model-free, on the character's own mesh):
//   mesh_in_mm     deepest vertex of the hand (every vertex carried by the hand bone or a bone below it) inside the
//                  solid, per part: [palm, thumb, fingers]; 0 = none inside (positive numbers are depths)
//   mesh_gap_mm    nearest vertex of each digit to the solid (thumb, index .. little): 0 = touching, negative = inside
//   flex_deg       signed bend of every digit joint about the hand's curl axis (thumb: the thumb axis), positive =
//                  towards the palm, per digit [a, b, distal bone if the rig has one]; negative = bent backwards
//   turn_deg       total rotation of each digit's first bone from rest (thumb first): a thumb turned round shows here
//   wrist_deg      the hand's rotation against the forearm from rest: [bend, twist about the forearm]
//   thumb_up       dot(thumb side of the hand, world up): 1 = thumb up, -1 = thumb down
#include <algorithm>
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
  std::string propName = "cup", assetPath = "content/assets/felt_cup.asset.json";
  for (int i = 2; i < argc; ++i) {
    const std::string a = argv[i];
    if (a == "--hand" && i + 4 < argc) {
      hands.push_back({argv[i + 1], argv[i + 2][0], std::stoi(argv[i + 3]), std::stoi(argv[i + 4])});
      i += 4;
    } else if (a == "--prop" && i + 2 < argc) {
      propName = argv[i + 1], assetPath = argv[i + 2];
      i += 2;
    }
  }
  SceneEvaluator ev;
  if (auto r = ev.load(*scene, EvalOptions{2.5f, 1.0f, false, 0}); !r) return std::fprintf(stderr, "%s\n", r.error().message.c_str()), 1;
  size_t p = 0;
  for (; p < ev.scene().props.size(); ++p)
    if (ev.scene().props[p].name == propName) break;
  if (p == ev.scene().props.size()) return std::fprintf(stderr, "no prop %s\n", propName.c_str()), 1;
  auto asset = loadAsset(assetPath);
  if (!asset) return std::fprintf(stderr, "%s\n", asset.error().message.c_str()), 1;
  const float k = asset->scaleMetres > 0 ? asset->scaleMetres : 1.0f;
  const float R = asset->mesh.radius * k, Hh = asset->mesh.height * k;
  std::cout << "{\"scene\": \"" << argv[1] << "\", \"prop_radius_mm\": " << R * 1e3 << ", \"prop_height_mm\": " << Hh * 1e3
            << ", \"frames\": [\n";
  bool first = true;
  for (const H& h : hands) {
    size_t c = 0;
    for (; c < ev.scene().characters.size(); ++c)
      if (ev.scene().characters[c].name == h.who) break;
    if (c == ev.characters().size()) return std::fprintf(stderr, "no character %s\n", h.who.c_str()), 1;
    const Skeleton& sk = ev.characters()[c].asset.skeleton;
    const std::string s = std::string(".") + h.side;
    const float r = fingertipRadius(sk, h.side);
    // Anatomical finger order: by the distance of the finger root from the thumb root (rest pose).
    std::vector<int> order{0, 1, 2, 3};
    const int th = sk.find("thumbA" + s);
    auto rootDist = [&](int f) {
      const int i = sk.find(std::format("f{}a{}", f, s));
      return i < 0 || th < 0 ? 1e9f : glm::distance(sk.bones[size_t(i)].head, sk.bones[size_t(th)].head);
    };
    std::sort(order.begin(), order.end(), [&](int a, int b) { return rootDist(a) < rootDist(b); });
    std::vector<std::pair<std::string, std::string>> digits{{"thumbA", "thumbB"}};
    for (int f : order) digits.push_back({std::format("f{}a", f), std::format("f{}b", f)});
    // Round 3: the hand's vertices by part (0 palm, 1 thumb, 2 + k finger k in anatomical order), dominant bone.
    const int handB = sk.find("hand" + s), foreB = handB >= 0 ? sk.bones[size_t(handB)].parent : -1;
    std::vector<int> partOf(sk.bones.size(), -1);
    if (handB >= 0) partOf[size_t(handB)] = 0;
    int thumbRoot = th;
    while (thumbRoot >= 0 && sk.bones[size_t(thumbRoot)].parent != handB) thumbRoot = sk.bones[size_t(thumbRoot)].parent;
    for (size_t b = 0; b < sk.bones.size(); ++b) {
      const int par = sk.bones[b].parent;
      if (par < 0 || partOf[size_t(par)] < 0) continue;
      partOf[b] = partOf[size_t(par)];
      if (int(b) == thumbRoot) partOf[b] = 1;
      for (size_t i = 0; i < order.size(); ++i)
        if (int(b) == sk.find(std::format("f{}a{}", order[i], s))) partOf[b] = 2 + int(i);
    }
    struct HV {
      int mesh;
      uint32_t v;
      int part;
    };
    std::vector<HV> handVerts;
    const auto& meshes = ev.characters()[c].rig.meshes;
    for (size_t m = 0; m < meshes.size(); ++m)
      for (size_t i = 0; i < meshes[m].rest.positions.size(); ++i) {
        int top = 0;
        for (int j = 1; j < 4; ++j)
          if (meshes[m].weights[i][j] > meshes[m].weights[i][top]) top = j;
        if (const int part = partOf[size_t(meshes[m].joints[i][top])]; part >= 0) handVerts.push_back({int(m), uint32_t(i), part});
      }
    const HandGrip grip = handGrip(sk, handB, h.side);
    const vec3 curlAxis = glm::normalize(glm::cross(grip.fingerDir, grip.palmNormal));
    const vec3 thumbAxis = glm::normalize(0.35f * (h.side == 'L' ? -grip.palmNormal : grip.palmNormal) + curlAxis);
    for (int f = h.from; f <= h.to; ++f) {
      const auto g = ev.characterGlobals(c, f);
      const mat4 P = ev.propWorld(p, f), Pi = glm::inverse(P);
      const float ps = glm::length(vec3(P[1]));
      // Signed distance to the capped solid cylinder, world metres (prop scale is uniform).
      auto sdf = [&](vec3 q) {
        const vec3 l = vec3(Pi * vec4(q, 1));
        const float dr = std::sqrt(l.x * l.x + l.z * l.z) - R / k, dy = std::abs(l.y - 0.5f * Hh / k) - 0.5f * Hh / k;
        const float out = glm::length(vec2(std::max(dr, 0.0f), std::max(dy, 0.0f))), in = std::min(std::max(dr, dy), 0.0f);
        return (out + in) * k * ps;
      };
      std::string hs, gaps, clears, roots, curls, rhs;
      std::vector<vec3> ftips, fkn;
      for (const auto& [a, b] : digits) {
        const int ia = sk.find(a + s), ib = sk.find(b + s);
        if (ia < 0 || ib < 0) continue;
        const vec3 ha = vec3(g[size_t(ia)][3]), kn = vec3(g[size_t(ib)][3]);
        const vec3 tip = vec3(g[size_t(ib)] * vec4(sk.bones[size_t(ib)].head - sk.bones[size_t(ia)].head, 1));
        float cl = 1;
        for (const vec3& q : {0.5f * (ha + kn), kn, 0.5f * (kn + tip), tip}) cl = std::min(cl, sdf(q) - r);
        const int ih = sk.bones[size_t(ia)].parent;
        auto rot = [&](int child, int parent) {  // rotation of `child` relative to `parent`, from rest, degrees
          const mat3 m = glm::transpose(mat3(g[size_t(parent)])) * mat3(g[size_t(child)]);
          const mat3 n(glm::normalize(m[0]), glm::normalize(m[1]), glm::normalize(m[2]));
          return glm::degrees(glm::angle(glm::quat_cast(n)));
        };
        const std::string sep = hs.empty() ? "" : ", ";
        hs += std::format("{}{:.1f}", sep, vec3(Pi * vec4(tip, 1)).y * k * 1e3);
        gaps += std::format("{}{:.2f}", sep, (sdf(tip) - r) * 1e3);
        clears += std::format("{}{:.2f}", sep, cl * 1e3);
        roots += std::format("{}{:.2f}", sep, (sdf(ha) - r) * 1e3);
        rhs += std::format("{}{:.1f}", sep, vec3(Pi * vec4(ha, 1)).y * k * 1e3);
        curls += std::format("{}[{:.2f}, {:.2f}]", sep, ih >= 0 ? rot(ia, ih) : 0.0f, rot(ib, ia));
        if (a[0] == 'f') ftips.push_back(tip), fkn.push_back(kn);
      }
      std::string apart, kapart;
      for (size_t i = 1; i < ftips.size(); ++i) {
        apart += std::format("{}{:.1f}", i > 1 ? ", " : "", glm::distance(ftips[i - 1], ftips[i]) * 1e3);
        kapart += std::format("{}{:.1f}", i > 1 ? ", " : "", glm::distance(fkn[i - 1], fkn[i]) * 1e3);
      }
      // Round 3 measures.
      auto local = [&](int child, int parent) {  // rotation of `child` against `parent` from rest
        const mat3 m = glm::transpose(mat3(g[size_t(parent)])) * mat3(g[size_t(child)]);
        return glm::normalize(glm::quat_cast(mat3(glm::normalize(m[0]), glm::normalize(m[1]), glm::normalize(m[2]))));
      };
      auto about = [&](quat q, vec3 axis) {  // signed angle of q's twist about `axis`, degrees
        if (q.w < 0) q = -q;
        const float sn = glm::dot(vec3(q.x, q.y, q.z), axis);
        return glm::degrees(2.0f * std::atan2(sn, q.w));
      };
      std::string flex, turn, meshGap;
      std::vector<float> digitGap(5, 1.0f);
      float in[3] = {0, 0, 0};
      for (const HV& hv : handVerts) {
        const SkinnedMesh& m = meshes[size_t(hv.mesh)];
        vec3 q(0);
        for (int j = 0; j < 4; ++j)
          if (const float w = m.weights[hv.v][j]; w > 0)
            q += w * vec3(g[size_t(m.joints[hv.v][j])] * vec4(m.rest.positions[hv.v] - sk.bones[size_t(m.joints[hv.v][j])].head, 1));
        const float d = sdf(q);
        const int grp = hv.part == 0 ? 0 : hv.part == 1 ? 1 : 2;
        in[grp] = std::max(in[grp], -d);
        if (hv.part >= 1) digitGap[size_t(hv.part - 1)] = std::min(digitGap[size_t(hv.part - 1)], d);
      }
      for (size_t i = 0; i < digits.size(); ++i) {
        const int ia = sk.find(digits[i].first + s), ib = sk.find(digits[i].second + s);
        if (ia < 0 || ib < 0) continue;
        const vec3 ax = i == 0 ? thumbAxis : curlAxis;
        int ic = -1, nc = 0;
        for (size_t b = 0; b < sk.bones.size(); ++b)
          if (sk.bones[b].parent == ib) ic = int(b), ++nc;
        std::string one = std::format("{:.1f}, {:.1f}", about(local(ia, sk.bones[size_t(ia)].parent), ax), about(local(ib, ia), ax));
        if (nc == 1 && i > 0) one += std::format(", {:.1f}", about(local(ic, ib), ax));
        flex += std::format("{}[{}]", i ? ", " : "", one);
        turn += std::format("{}{:.1f}", i ? ", " : "", glm::degrees(glm::angle(local(ia, sk.bones[size_t(ia)].parent))));
        meshGap += std::format("{}{:.2f}", i ? ", " : "", digitGap[i] * 1e3);
      }
      float bend = 0, twist = 0;
      if (handB >= 0 && foreB >= 0) {
        const quat q = local(handB, foreB);
        const vec3 fa = glm::normalize(sk.bones[size_t(handB)].head - sk.bones[size_t(foreB)].head);
        twist = about(q, fa);
        bend = glm::degrees(glm::angle(glm::normalize(q * glm::inverse(glm::angleAxis(glm::radians(twist), fa)))));
      }
      const vec3 thumbSide = glm::normalize(mat3(g[size_t(handB)]) * ((h.side == 'R' ? 1.0f : -1.0f) * glm::cross(grip.fingerDir, grip.palmNormal)));
      const std::string r3 = std::format("\"mesh_in_mm\": [{:.2f}, {:.2f}, {:.2f}], \"mesh_gap_mm\": [{}], \"flex_deg\": [{}], \"turn_deg\": [{}], "
                                         "\"wrist_deg\": [{:.1f}, {:.1f}], \"thumb_up\": {:.2f}, ",
                                         in[0] * 1e3, in[1] * 1e3, in[2] * 1e3, meshGap, flex, turn, bend, twist, thumbSide.y);
      const vec3 wrist = vec3(g[size_t(sk.find("hand" + s))][3]);
      const vec3 wl = vec3(Pi * vec4(wrist, 1));
      std::cout << (first ? "" : ",\n")
                << std::format("  {{\"hand\": \"{}.{}\", \"frame\": {}, \"skin_radius_mm\": {:.2f}, \"tip_h_mm\": [{}], "
                               "\"tip_gap_mm\": [{}], \"clear_mm\": [{}], \"root_mm\": [{}], \"root_h_mm\": [{}], \"curl_deg\": [{}], "
                               "\"tips_apart_mm\": [{}], \"knuckles_apart_mm\": [{}], {}\"wrist\": [{:.7f}, {:.7f}, {:.7f}], "
                               "\"wrist_axis_mm\": {:.2f}}}",
                               h.who, h.side, f, r * 1e3, hs, gaps, clears, roots, rhs, curls, apart, kapart, r3, wrist.x, wrist.y,
                               wrist.z, std::sqrt(wl.x * wl.x + wl.z * wl.z) * k * ps * 1e3);
      first = false;
    }
  }
  std::cout << "\n]}\n";
  return 0;
}
