// arm-body gap per frame (armClearanceAt, mm; negative = inside the body)
#include <cstdio>
#include <string>
#include "scene/scene.h"
#include "scene/interaction.h"
using namespace plush;
int main(int argc, char** argv) {
  auto scene = loadScene(argv[1]);
  if (!scene) return std::fprintf(stderr, "%s\n", scene.error().message.c_str()), 1;
  SceneEvaluator ev;
  if (auto r = ev.load(*scene, EvalOptions{2.5f, 1.0f, false, 0}); !r) return std::fprintf(stderr, "%s\n", r.error().message.c_str()), 1;
  size_t c = 0;
  for (size_t i = 0; i < scene->characters.size(); ++i) if (scene->characters[i].name == argv[2]) c = i;
  for (int f = std::stoi(argv[4]); f <= std::stoi(argv[5]); ++f) {
    const ArmClearance a = ev.armClearanceAt(c, argv[3][0], f);
    std::printf("f%d %.1f %s %s\n", f, a.gap * 1e3, a.part.c_str(), a.against.c_str());
  }
}
