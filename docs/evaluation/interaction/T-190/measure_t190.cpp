// T-190 evidence: per-frame scan of every finger and thumb joint of every character hand in a resolved shot, in an
// anatomical frame built from the skeleton's rest geometry alone (not from the solver's own curl axes). Not part of
// the build (build_measure.sh):
//   build/fast-dev/measure_t190 <resolved scene.json> [--from f --to f] > joints.jsonl
// One JSON line per character, hand and frame. Angles in degrees, per joint [flex, side, twist]:
//   flex   the bone's swing in its flexion plane, positive = towards the palm (thumb: towards its pad side),
//          negative = bent backwards (hyperextension)
//   side   the swing out of that plane (fingers: positive = towards the thumb side; a hinge joint has none)
//   twist  the roll about the bone's own length (a finger joint has none)
// Hand frame (rest): d = wrist -> mean finger root, r = little root -> index root (towards the thumb), n = the palm
// normal r x d signed per side (the engine's own convention, checked on the rendered mesh in the README).
// Finger joints: f<k>a (knuckle), f<k>b (middle joint), the rig's distal bone when f<k>b has exactly one child.
// Thumb joints: thumbA (the rig's first driven thumb bone: saddle joint + knuckle in one), thumbB (end joint). The
// thumb's hinge is the engine's thumb axis made perpendicular to the thumb: flex = in front of the palm.
// Also per line: the wrist position, finger direction and palm normal in world space (for close-up cameras), and
// which hand tracks drive the hand at that frame (owner of the pose, for the code-path column).
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <format>
#include <iostream>
#include <string>
#include <vector>

#include "anim/animation.h"
#include "scene/scene.h"

using namespace plush;

namespace {
struct Joint {
  std::string name;
  int bone = -1;
  vec3 u{0}, h{0};  // rest bone direction, hinge axis (rotation by +angle about h = flexion)
};
// [flex, side, twist] of a joint rotation q (parent frame, rest = identity).
vec3 decompose(const Joint& j, quat q) {
  const vec3 p = glm::cross(j.h, j.u);  // flexion direction (unit)
  const vec3 v = q * j.u;
  const float flex = glm::degrees(std::atan2(glm::dot(v, p), glm::dot(v, j.u)));
  const float side = glm::degrees(std::asin(std::clamp(glm::dot(v, j.h), -1.0f, 1.0f)));
  const quat swing = glm::rotation(j.u, glm::normalize(v));
  quat t = glm::inverse(swing) * q;
  if (t.w < 0) t = -t;
  const float twist = glm::degrees(2.0f * std::atan2(glm::dot(vec3(t.x, t.y, t.z), j.u), t.w));
  return vec3(flex, side, twist);
}
}  // namespace

int main(int argc, char** argv) {
  if (argc < 2) return std::fprintf(stderr, "usage: measure_t190 <resolved scene.json> [--from f --to f]\n"), 2;
  auto scene = loadScene(argv[1]);
  if (!scene) return std::fprintf(stderr, "%s\n", scene.error().message.c_str()), 1;
  SceneEvaluator ev;
  if (auto r = ev.load(*scene, EvalOptions{2.5f, 1.0f, false, 0}); !r) return std::fprintf(stderr, "%s\n", r.error().message.c_str()), 1;
  int from = ev.scene().frameStart, to = ev.scene().frameEnd;
  for (int i = 2; i + 1 < argc; i += 2) {
    if (std::string(argv[i]) == "--from") from = std::stoi(argv[i + 1]);
    if (std::string(argv[i]) == "--to") to = std::stoi(argv[i + 1]);
  }
  const Clip& clip = ev.scene().animation;
  for (size_t c = 0; c < ev.scene().characters.size(); ++c) {
    const Skeleton& sk = ev.characters()[c].asset.skeleton;
    const std::string who = ev.scene().characters[c].name;
    for (char side : {'L', 'R'}) {
      const std::string s = std::string(".") + side;
      const int hand = sk.find("hand" + s), idx = sk.find("f3a" + s), pinky = sk.find("f0a" + s);
      if (hand < 0 || idx < 0 || pinky < 0) continue;
      auto head = [&](int b) { return sk.bones[size_t(b)].head; };
      vec3 base(0);
      int n = 0;
      for (int k = 0; k < 4; ++k)
        if (int a = sk.find(std::format("f{}a{}", k, s)); a >= 0) base += head(a), ++n;
      const vec3 d = glm::normalize(base / float(n) - head(hand));
      vec3 r = head(idx) - head(pinky);
      r = glm::normalize(r - d * glm::dot(r, d));
      const vec3 nrm = glm::normalize(glm::cross(r, d)) * (side == 'L' ? -1.0f : 1.0f);
      std::vector<std::pair<std::string, std::vector<Joint>>> digits;
      auto onlyChild = [&](int b) {
        int ch = -1, nc = 0;
        for (size_t i = 0; i < sk.bones.size(); ++i)
          if (sk.bones[i].parent == b) ch = int(i), ++nc;
        return nc == 1 ? ch : -1;
      };
      if (const int ta = sk.find("thumbA" + s), tb = sk.find("thumbB" + s); ta >= 0 && tb >= 0) {
        const vec3 t = glm::normalize(head(tb) - head(ta));
        // Hinge: the engine's thumb axis (0.35 x back of the hand + the fingers' curl axis), made perpendicular to the
        // thumb. On the rendered mesh a rotation about it takes the thumb in front of the palm (study sheet, README).
        const vec3 curl = glm::cross(d, nrm), back = side == 'L' ? -nrm : nrm;
        vec3 h = glm::normalize(0.35f * back + curl);
        h = glm::normalize(h - t * glm::dot(h, t));
        digits.push_back({"thumb", {{"thumbA", ta, t, h}, {"thumbB", tb, t, h}}});
      }
      for (int k = 3; k >= 0; --k) {  // index .. little
        const int a = sk.find(std::format("f{}a{}", k, s)), b = sk.find(std::format("f{}b{}", k, s));
        if (a < 0 || b < 0) continue;
        const int dist = onlyChild(b);
        auto joint = [&](const std::string& name, int bone, vec3 u) {
          u = glm::normalize(u);
          return Joint{name, bone, u, glm::normalize(glm::cross(u, nrm))};
        };
        std::vector<Joint> js{joint(std::format("f{}a", k), a, head(b) - head(a)),
                              joint(std::format("f{}b", k), b, dist >= 0 ? head(dist) - head(b) : head(b) - head(a))};
        if (dist >= 0) js.push_back(joint(std::format("f{}c", k), dist, head(dist) - head(b)));
        digits.push_back({std::format("f{}", k), js});
      }
      const std::string tb = who + "/hand." + side;
      auto keyed = [&](const std::string& name) {
        const Track* t = clip.find(name);
        return t && !t->keys.empty() ? t : nullptr;
      };
      for (int f = from; f <= to; ++f) {
        Pose pose;
        const auto g = ev.characterGlobals(c, f, &pose);
        const vec3 w = vec3(g[size_t(hand)][3]), fd = glm::normalize(mat3(g[size_t(hand)]) * d), pn = glm::normalize(mat3(g[size_t(hand)]) * nrm);
        std::string out = std::format("{{\"who\": \"{}\", \"side\": \"{}\", \"frame\": {}, \"owned\": {}", who, side, f, keyed(tb) ? "true" : "false");
        out += std::format(", \"wrist\": [{:.4f}, {:.4f}, {:.4f}], \"finger_dir\": [{:.3f}, {:.3f}, {:.3f}], \"palm_normal\": [{:.3f}, {:.3f}, {:.3f}]",
                           w.x, w.y, w.z, fd.x, fd.y, fd.z, pn.x, pn.y, pn.z);
        if (keyed(tb)) {
          const vec3 v = keyed(tb)->evaluate(f);
          out += std::format(", \"hand\": [{:.3f}, {:.3f}, {:.3f}]", v.x, v.y, v.z);
        }
        if (keyed(tb + ".grasp")) out += std::format(", \"grasp_w\": {:.3f}", clip.evaluate(tb + ".grasp.weight", f, vec3(1)).x);
        for (const char* t : {".wrap", ".band", ".bandFit", ".thumb", ".graspFace", ".stagger", ".seat", ".index", ".f0", ".f1", ".f2", ".f3"})
          if (const Track* tr = keyed(tb + t)) out += std::format(", \"{}\": {:.3f}", t + 1, tr->evaluate(f).x);
        out += ", \"joints\": {";
        bool first = true;
        for (const auto& [dn, js] : digits)
          for (const Joint& j : js) {
            const vec3 a = decompose(j, pose.local[size_t(j.bone)]);
            out += std::format("{}\"{}\": [{:.1f}, {:.1f}, {:.1f}]", first ? "" : ", ", j.name, a.x, a.y, a.z);
            first = false;
          }
        std::cout << out << "}}\n";
      }
    }
  }
  return 0;
}
