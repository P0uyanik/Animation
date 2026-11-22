// T-190 evidence: what moves in each golden scene whose bake hash changes (tests/golden/interaction_hashes.json, the
// six content scenes; cast = the imported test packages, as tests/test_bake_golden.cpp contentScene). Each scene is
// evaluated twice with the same build: as it is (joint limits on) and with "<who>/hand.<s>.limits" 0 keyed on every
// hand (the poses before T-190, bit for bit). Per scene: frames that differ, the largest digit joint rotation
// difference (deg), thumb and finger joints apart, the largest fingertip displacement (mm), the largest difference of any other bone (must be 0).
//   g++ -std=c++23 -O3 -DNDEBUG -I engine docs/evaluation/interaction/T-190/golden_delta.cpp -Lbuild/fast-dev/engine \
//       -lplush_scene -lplush_model -lplush_fuzz -lplush_anim -lplush_geom -lplush_core -o build/fast-dev/golden_delta
//   build/fast-dev/golden_delta <repository root>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <string>

#include "anim/animation.h"
#include "scene/scene.h"

using namespace plush;

int main(int argc, char** argv) {
  const std::filesystem::path root = argc > 1 ? argv[1] : ".";
  std::printf("| golden scene | frames that differ | hands that differ | thumb joint, deg (max) | finger joint, deg (max) | fingertip, mm (max) | any other bone |\n| --- | --- | --- | --- | --- | --- | --- |\n");
  for (const char* rel : {"content/scenes/eval/exchange/shot.scene.json", "content/scenes/eval/handover/shot.scene.json",
                          "episodes/e901_clip_test/shots/s010/shot.scene.json", "episodes/e905_props_test/shots/s010/shot.scene.json",
                          "episodes/e907_exchange/shots/s010/shot.scene.json", "episodes/e907_exchange/shots/s010_calibrated/shot.scene.json"}) {
    auto s = loadScene(root / rel);
    if (!s) return std::fprintf(stderr, "%s\n", s.error().message.c_str()), 1;
    Scene on = *s;
    for (CharacterDesc& c : on.characters) {
      if (c.name == "boy") c.asset = (root / "tests/data/imported/boy_yellow_hoodie_1.0.0/character.json").string();
      if (c.name == "girl") c.asset = (root / "tests/data/imported/girl_auburn_bun_glasses_m3/character.json").string();
    }
    Scene off = on;
    for (const CharacterDesc& c : off.characters)
      for (char side : {'L', 'R'}) off.animation.tracks[c.name + "/hand." + side + ".limits"].setKey(Key{double(off.frameStart), vec3(0), Interp::Step});
    SceneEvaluator a, b;
    if (auto r = a.load(on, EvalOptions{2.5f, 1.0f, false, 0}); !r) return std::fprintf(stderr, "%s\n", r.error().message.c_str()), 1;
    if (auto r = b.load(off, EvalOptions{2.5f, 1.0f, false, 0}); !r) return std::fprintf(stderr, "%s\n", r.error().message.c_str()), 1;
    float joint = 0, finger = 0, tip = 0, other = 0;
    int frames = 0;
    std::string hands;
    for (int f = on.frameStart; f <= on.frameEnd; ++f) {
      bool differs = false;
      for (size_t c = 0; c < on.characters.size(); ++c) {
        const Skeleton& sk = a.characters()[c].asset.skeleton;
        Pose pa, pb;
        const auto ga = a.characterGlobals(c, f, &pa), gb = b.characterGlobals(c, f, &pb);
        std::vector<char> digit(sk.bones.size(), 0), thumb(sk.bones.size(), 0);
        for (size_t i = 0; i < sk.bones.size(); ++i) {
          const std::string& n = sk.bones[i].name;
          const int p = sk.bones[i].parent;
          thumb[i] = n.rfind("thumb", 0) == 0 || (p >= 0 && thumb[size_t(p)]);
          digit[i] = thumb[i] || (n.size() > 3 && n[0] == 'f' && std::isdigit(static_cast<unsigned char>(n[1]))) || (p >= 0 && digit[size_t(p)]);
          const quat r = glm::inverse(pa.local[i]) * pb.local[i];
          const float d = glm::degrees(2.0f * std::atan2(glm::length(vec3(r.x, r.y, r.z)), std::abs(r.w)));
          float& m = thumb[i] ? joint : digit[i] ? finger : other;
          m = std::max(m, d);
        }
        for (char side : {'L', 'R'}) {
          const auto ta = fingertips(sk, pa, mat4(1), side), tb = fingertips(sk, pb, mat4(1), side);
          float m = 0;
          for (size_t i = 0; i < ta.size(); ++i) m = std::max(m, glm::distance(ta[i], tb[i]) * 1e3f);
          tip = std::max(tip, m);
          if (m > 0) {
            differs = true;
            const std::string h = on.characters[c].name + " " + side;
            if (hands.find(h) == std::string::npos) hands += (hands.empty() ? "" : ", ") + h;
          }
        }
      }
      frames += differs ? 1 : 0;
    }
    std::printf("| `%s` | %d of %d | %s | %.1f | %.3f | %.1f | %.3f |\n", rel, frames, on.frameEnd - on.frameStart + 1, hands.c_str(), joint, finger, tip, other);
  }
  return 0;
}
