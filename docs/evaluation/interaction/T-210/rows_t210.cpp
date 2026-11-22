// T-210 evidence tool (not part of the gate): the unexempt per-frame speed-limit rows (continuityReport) of one shipped
// scene with the test cast of tests/test_motion_continuity.cpp, and optionally the values of tracks of one character.
//   g++ -std=c++23 -O2 -DNDEBUG -I engine docs/evaluation/interaction/T-210/rows_t210.cpp -Lbuild/fast-dev/engine \
//       -lplush_scene -lplush_model -lplush_fuzz -lplush_anim -lplush_geom -lplush_core -o build/fast-dev/rows_t210
//   build/fast-dev/rows_t210 <shot.scene.json> [<character> <from> <to> <track suffix | =track | @bone> ...]
#include <cstdio>
#include <filesystem>
#include <string>

#include "scene/interaction.h"
#include "scene/scene.h"

using namespace plush;

int main(int argc, char** argv) {
  if (argc < 2) return std::fprintf(stderr, "usage: rows_t210 <scene> [who from to tracks...]\n"), 2;
  auto s = loadScene(argv[1]);
  if (!s) return std::fprintf(stderr, "%s\n", s.error().message.c_str()), 1;
  Scene scene = *s;
  for (CharacterDesc& c : scene.characters) {
    if (c.name == "boy") c.asset = std::filesystem::absolute("tests/data/imported/boy_yellow_hoodie_1.0.0/character.json").string();
    if (c.name == "girl") c.asset = std::filesystem::absolute("tests/data/imported/girl_auburn_bun_glasses_m3/character.json").string();
  }
  SceneEvaluator ev;
  if (auto r = ev.load(scene, EvalOptions{2.5f, 1.0f, false, 0}); !r) return std::fprintf(stderr, "%s\n", r.error().message.c_str()), 1;
  int n = 0;
  for (const auto& r : continuityReport(ev))
    if (r.exempt.empty()) std::printf("ROW %s f%d %s %.2f deg %.1f mm\n", r.character.c_str(), r.jump.frame, r.bone.c_str(), r.jump.deg, r.jump.mm), ++n;
  std::printf("rows %d\n", n);
  if (argc >= 6) {
    const std::string who = argv[2];
    for (int f = std::stoi(argv[3]); f <= std::stoi(argv[4]); ++f) {
      std::printf("f%d", f);
      for (int i = 5; i < argc; ++i) {
        if (argv[i][0] == '@') {  // "@bone": the bone's world travel (mm) from the frame before
          size_t c = 0;
          while (c + 1 < ev.scene().characters.size() && ev.scene().characters[c].name != who) ++c;
          const int b = ev.characters()[c].asset.skeleton.find(argv[i] + 1);
          if (b < 0) continue;
          const vec3 p0(ev.characterGlobals(c, f - 1)[size_t(b)][3]), p1(ev.characterGlobals(c, f)[size_t(b)][3]);
          std::printf("  %s %.1f mm", argv[i], 1000 * glm::distance(p0, p1));
          continue;
        }
        const vec3 v = ev.scene().animation.evaluate(argv[i][0] == '=' ? std::string(argv[i] + 1) : who + "/" + argv[i], f, vec3(-9));
        std::printf("  %s %.3f %.3f %.3f", argv[i], v.x, v.y, v.z);
      }
      std::printf("\n");
    }
  }
}
