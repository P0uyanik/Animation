// T-047 evidence: e905 palm-to-socket contacts and prop continuity with planning on and off (not part of the build):
//   g++ -std=c++23 -O2 -I engine <this file> -Lbuild/engine -lplush_scene -lplush_model -lplush_fuzz -lplush_anim \
//       -lplush_geom -lplush_core -o build/contacts_e905
//   build/contacts_e905 episodes/e905_props_test/shots/s010/build/shot.resolved.scene.json content/assets/felt_cup.asset.json
// Frames from the shot: boy grasps at 17 (socket grip) and lets go at 51; the girl receives at 46 (grip_b).
#include <iostream>
#include "scene/asset_library.h"
#include "scene/interaction.h"
#include "scene/scene.h"
using namespace plush;
int main(int argc, char** argv) {
  auto scene = loadScene(argv[1]);
  Json out = Json::object();
  for (int planning = 1; planning >= 0; --planning) {
    Scene s = *scene;
    if (!planning) for (auto& c : scene->characters) s.actions.push_back({{"type","collision"},{"character",c.name},{"enabled",false}});
    SceneEvaluator ev; if (auto r = ev.load(s, EvalOptions{2.5f,1,false,0}); !r) { std::cerr << r.error().message; return 1; }
    const PropAsset a = loadAsset(argv[2]).value();
    auto sock = [&](const char* k, double f) { return vec3((ev.propWorld(0, f) * assetTransformMatrix(a.sockets.at(k)))[3]); };
    float boyGrasp = glm::distance(ev.handGripPoint(0,'R',17), sock("grip",17));
    float girlGrasp = glm::distance(ev.handGripPoint(1,'R',46), sock("grip_b",46));
    float boyHeld = 0, girlHeld = 0, jump = 0;
    for (double f = 17; f <= 51; f += 0.5) boyHeld = std::max(boyHeld, glm::distance(ev.handGripPoint(0,'R',f), sock("grip",f)));
    for (double f = 46; f <= 72; f += 0.5) girlHeld = std::max(girlHeld, glm::distance(ev.handGripPoint(1,'R',f), sock("grip_b",f)));
    for (double f : {17.0, 46.0}) jump = std::max(jump, glm::distance(vec3(ev.propWorld(0,f-1e-3)[3]), vec3(ev.propWorld(0,f+1e-3)[3])));
    out[planning ? "planned" : "unplanned"] = {{"boy_grasp_f17_mm", boyGrasp*1000}, {"girl_grasp_f46_mm", girlGrasp*1000},
      {"boy_held_f17_51_max_mm", boyHeld*1000}, {"girl_held_f46_72_max_mm", girlHeld*1000}, {"prop_jump_at_switches_mm", jump*1000}, {"warnings", ev.warnings()}};
  }
  std::cout << out.dump(1) << std::endl;
}
