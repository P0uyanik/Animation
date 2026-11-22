// T-198 evidence tool (not part of the gate): per frame, the one-frame turn (deg) / pivot travel (mm) of body bones
// of one character, and the values of the animation tracks that drive them, to find which path makes a snap.
//   trace_t198 <resolved scene.json> <character> <from> <to> [track suffix ...]
#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

#include "anim/animation.h"
#include "scene/scene.h"

using namespace plush;

int main(int argc, char** argv) {
  if (argc < 5) return std::fprintf(stderr, "usage: trace_t198 <scene> <character> <from> <to> [tracks]\n"), 2;
  auto scene = loadScene(argv[1]);
  if (!scene) return std::fprintf(stderr, "%s\n", scene.error().message.c_str()), 1;
  SceneEvaluator ev;
  if (auto r = ev.load(*scene, EvalOptions{2.5f, 1.0f, false, 0}); !r) return std::fprintf(stderr, "%s\n", r.error().message.c_str()), 1;
  const std::string who = argv[2];
  size_t c = 0;
  while (c < ev.scene().characters.size() && ev.scene().characters[c].name != who) ++c;
  if (c == ev.scene().characters.size()) return std::fprintf(stderr, "no character %s\n", who.c_str()), 1;
  const int from = std::stoi(argv[3]), to = std::stoi(argv[4]);
  std::vector<std::string> tracks;
  for (int i = 5; i < argc; ++i) tracks.push_back(who + "/" + argv[i]);
  if (tracks.empty())
    if (ev.scene().animation.generated) for (const auto& [name, t] : ev.scene().animation.generated->tracks)
      if (name.rfind(who + "/", 0) == 0) std::printf("# track %s (%zu keys)\n", name.c_str(), t.keys.size());
  const auto& sk = ev.characters()[c].asset.skeleton;
  const char* bones[] = {"chest", "neck", "head", "upperArm.L", "forearm.L", "hand.L", "upperArm.R", "forearm.R", "hand.R"};
  std::vector<mat4> prev = ev.characterGlobals(c, from - 1);
  for (int f = from; f <= to; ++f) {
    std::vector<mat4> g = ev.characterGlobals(c, f);
    std::printf("f%d", f);
    for (const char* b : bones) {
      const int i = sk.find(b);
      if (i < 0) continue;
      const quat q0 = glm::quat_cast(mat3(prev[size_t(i)])), q1 = glm::quat_cast(mat3(g[size_t(i)]));
      const float d = glm::degrees(2.0f * std::acos(std::min(1.0f, std::abs(glm::dot(glm::normalize(q0), glm::normalize(q1))))));
      const float mm = 1000.0f * glm::distance(vec3(prev[size_t(i)][3]), vec3(g[size_t(i)][3]));
      std::printf(" %s %.0f/%.0f", b, d, mm);
    }
    for (const auto& t : tracks) {
      const vec3 v = ev.scene().animation.evaluate(t, f, vec3(NAN));
      std::printf(" | %s %.3f %.3f %.3f", t.substr(who.size() + 1).c_str(), v.x, v.y, v.z);
    }
    std::printf("\n");
    prev = g;
  }
}
