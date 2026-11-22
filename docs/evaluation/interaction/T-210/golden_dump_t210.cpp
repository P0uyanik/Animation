// T-210 evidence tool (not part of the gate): dumps the world transform of every bone, per frame and character, of
// every golden scene of tests/test_bake_golden.cpp (its own goldenScenes(), compiled in with the test cases disabled),
// in the line format of ../T-198/golden_dump_t198.cpp, so two builds (before / after) compare with
// ../T-198/golden_delta_t198.py.
//   g++ -std=c++23 -O2 -DNDEBUG -DDOCTEST_CONFIG_DISABLE -DPLUSH_SOURCE_DIR='"'$PWD'"' -I engine \
//       docs/evaluation/interaction/T-210/golden_dump_t210.cpp -Lbuild/fast-dev/engine -lplush_scene -lplush_model \
//       -lplush_fuzz -lplush_anim -lplush_geom -lplush_core -o build/fast-dev/golden_dump_t210
//   build/fast-dev/golden_dump_t210 > dump.txt
//   build/fast-dev/golden_dump_t210 report   (instead: per golden, the peak per-frame turn of each character's finger
//                                             bones over the limit and how many unexempt rows of continuityReport)
#include <cstdio>
#include <cstring>
#include <map>

#include "../../../../tests/test_bake_golden.cpp"
#include "scene/interaction.h"

int main(int argc, char** argv) {
  const bool report = argc > 1 && std::strcmp(argv[1], "report") == 0;
  for (const GoldenScene& g : goldenScenes()) {
    const Scene scene = g.make();
    auto ev = load(scene);
    const Scene& sc = ev->scene();
    if (report) {
      std::map<std::string, std::pair<float, int>> peak;  // character: finger peak (deg), rows
      int rows = 0;
      for (const ContinuityRow& r : continuityReport(*ev)) {
        if (!r.exempt.empty()) continue;
        ++rows;
        auto& p = peak[r.character + (motionBoneClass(r.bone) == MotionBoneClass::Finger ? " fingers" : " " + r.bone)];
        p.first = std::max(p.first, std::max(r.jump.deg, r.jump.mm)), ++p.second;
      }
      std::printf("%s: %d rows", g.name.c_str(), rows);
      for (const auto& [k, v] : peak) std::printf("; %s %.2f (%d)", k.c_str(), v.first, v.second);
      std::printf("\n");
      continue;
    }
    for (size_t c = 0; c < sc.characters.size() && c < ev->characters().size(); ++c) {
      const Skeleton& sk = ev->characters()[c].asset.skeleton;
      for (int f = sc.frameStart; f <= sc.frameEnd; ++f) {
        const auto m = ev->characterGlobals(c, f, nullptr);
        for (size_t i = 0; i < sk.bones.size(); ++i) {
          const quat q = glm::quat_cast(mat3(m[i]));
          std::printf("%s %s %d %s %.7g %.7g %.7g %.7g %.7g %.7g %.7g\n", g.name.c_str(), sc.characters[c].name.c_str(), f,
                      sk.bones[i].name.c_str(), m[i][3].x, m[i][3].y, m[i][3].z, q.w, q.x, q.y, q.z);
        }
      }
    }
  }
}
