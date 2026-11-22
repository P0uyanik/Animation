// T-198 evidence tool (not part of the gate): the per-frame speed-limit report (scene/interaction.h continuityReport)
// of one resolved scene, one line per character and frame: the bones over the limit (deg / mm in that frame) and the
// class (SNAP = not intended by data, cut, fast).
//   g++ -std=c++23 -O2 -DNDEBUG -I engine docs/evaluation/interaction/T-198/continuity_t198.cpp -Lbuild/fast-dev/engine \
//       -lplush_scene -lplush_model -lplush_fuzz -lplush_anim -lplush_geom -lplush_core -o build/fast-dev/continuity_t198
//   build/fast-dev/continuity_t198 <resolved scene.json>
#include <cstdio>
#include <map>
#include <string>

#include "scene/interaction.h"
#include "scene/scene.h"

using namespace plush;

int main(int argc, char** argv) {
  if (argc < 2) return std::fprintf(stderr, "usage: continuity_t198 <scene>\n"), 2;
  auto scene = loadScene(argv[1]);
  if (!scene) return std::fprintf(stderr, "%s\n", scene.error().message.c_str()), 1;
  SceneEvaluator ev;
  if (auto r = ev.load(*scene, EvalOptions{2.5f, 1.0f, false, 0}); !r) return std::fprintf(stderr, "%s\n", r.error().message.c_str()), 1;
  std::map<std::pair<std::string, int>, std::string> lines;
  std::map<std::string, int> snaps;
  for (const auto& r : continuityReport(ev)) {
    auto& l = lines[{r.character, r.jump.frame}];
    if (l.empty()) l = r.exempt.empty() ? "SNAP" : r.exempt;
    char b[96];
    std::snprintf(b, sizeof b, " %s %.0f/%.0f", r.bone.c_str(), r.jump.deg, r.jump.mm);
    l += b;
  }
  for (const auto& [k, l] : lines) {
    std::printf("%s f%d %s\n", k.first.c_str(), k.second, l.c_str());
    if (l.rfind("SNAP", 0) == 0) ++snaps[k.first];
  }
  int total = 0;
  for (const auto& [c, n] : snaps) total += n;
  std::printf("# snap frames: %d\n", total);
  return 0;
}
