// One-off T-022 measurement of the e905 shot with the engine (not part of the build):
//   g++ -std=c++23 -O2 -I engine docs/evaluation/animation/T-022/measure_e905.cpp -Lbuild/engine -lplush_scene \
//       -lplush_model -lplush_fuzz -lplush_anim -lplush_geom -lplush_core -o m          (run from the repository root)
//   ./m episodes/e905_props_test/shots/s010/build/shot.resolved.scene.json > docs/evaluation/animation/T-022/e905_measurements.json
// Reports contact distances (palm point to grasp socket), prop continuity at the parent switches, prop speed,
// uprightness and palm-to-socket drift while held.
#include <cstdio>
#include <iostream>

#include "scene/scene.h"

using namespace plush;

int main(int argc, char** argv) {
  auto scene = loadScene(argv[1]);
  if (!scene) { std::cerr << scene.error().message << "\n"; return 1; }
  SceneEvaluator ev;
  if (auto r = ev.load(*scene, EvalOptions{2.5f, 1.0f, false, 0}); !r) { std::cerr << r.error().message << "\n"; return 1; }
  const Scene& s = ev.scene();
  const PropAsset cup = loadAsset(argc > 2 ? argv[2] : "content/assets/felt_cup.asset.json").value_or(PropAsset{});
  auto socket = [&](const char* n, double f) {
    for (auto& [k, t] : cup.sockets)
      if (k == n) return vec3((ev.propWorld(0, f) * assetTransformMatrix(t))[3]);
    return vec3(0);
  };
  size_t boy = 0, girl = 1;
  for (size_t c = 0; c < s.characters.size(); ++c) (s.characters[c].name == "boy" ? boy : girl) = c;
  Json out;
  out["scene"] = argv[1];
  out["warnings"] = ev.warnings();
  int grasp = 0, give = 0, rel = 0;
  for (const auto& a : s.actions) {
    if (a.value("type", "") == "grasp") grasp = a.value("contact", 0);
    if (a.value("type", "") == "handover") give = a.value("contact", 0), rel = a.value("release", 0);
  }
  out["frames"] = {{"boy_grasp_contact", grasp}, {"handover_contact", give}, {"giver_release", rel}};
  out["contact_mm"] = {
      {"boy_palm_to_grip_at_grasp", 1000 * glm::distance(ev.handGripPoint(boy, 'R', grasp), socket("grip", grasp))},
      {"girl_palm_to_grip_b_at_handover", 1000 * glm::distance(ev.handGripPoint(girl, 'R', give), socket("grip_b", give))},
      {"boy_palm_to_grip_at_handover", 1000 * glm::distance(ev.handGripPoint(boy, 'R', give), socket("grip", give))}};
  Json jumps = Json::object();
  for (int f : {grasp, give}) {
    const mat4 a = ev.propWorld(0, f - 1e-3), b = ev.propWorld(0, f + 1e-3);
    jumps[std::to_string(f)] = 1000 * glm::distance(vec3(a[3]), vec3(b[3]));
  }
  out["prop_jump_across_switch_mm"] = jumps;
  float vmax = 0, upMin = 1, driftBoy = 0, driftGirl = 0;
  Json speed = Json::array();
  for (int f = s.frameStart; f < s.frameEnd; ++f) {
    const float v = 1000 * glm::distance(vec3(ev.propWorld(0, f)[3]), vec3(ev.propWorld(0, f + 1)[3]));
    speed.push_back(std::round(v * 100) / 100);
    vmax = std::max(vmax, v);
    upMin = std::min(upMin, glm::dot(glm::normalize(vec3(ev.propWorld(0, f)[1])), vec3(0, 1, 0)));
    if (f >= grasp && f <= give) driftBoy = std::max(driftBoy, 1000 * glm::distance(ev.handGripPoint(boy, 'R', f), socket("grip", f)));
    if (f >= give) driftGirl = std::max(driftGirl, 1000 * glm::distance(ev.handGripPoint(girl, 'R', f), socket("grip_b", f)));
  }
  out["prop_speed_mm_per_frame"] = speed;
  out["prop_speed_max_mm_per_frame"] = vmax;
  out["cup_upright_min_cos"] = upMin;
  out["palm_to_socket_max_mm_while_held"] = {{"boy_grasp_to_handover", driftBoy}, {"girl_handover_to_end", driftGirl}};
  std::cout << out.dump(1) << "\n";
}
