// T-047 evidence: smallest gap of the held cup's surface (its cylinder: 5 rings x 12 points) to each character's
// collision body over the shot (not part of the build; build like contacts_e905.cpp, same arguments).
#include <iostream>
#include "scene/asset_library.h"
#include "scene/interaction.h"
#include "scene/scene.h"
using namespace plush;
int main(int argc, char** argv) {
  auto scene = loadScene(argv[1]);
  SceneEvaluator ev; if (auto r = ev.load(*scene, EvalOptions{2.5f,1,false,0}); !r) { std::cerr << r.error().message; return 1; }
  const PropAsset a = loadAsset(argv[2]).value();
  const float k = a.scaleMetres > 0 ? a.scaleMetres : 1, R = a.mesh.radius * k, H = a.mesh.height * k;
  Json out = Json::object();
  for (size_t c = 0; c < ev.characters().size(); ++c) {
    const auto& ci = ev.characters()[c];
    const CollisionBody B = collisionBodyFor(ci.asset.collisionBlock, ci.asset.skeleton, ci.rig.meshes);
    float worst = 1e9f; int at = 0;
    for (int f = scene->frameStart; f <= scene->frameEnd; ++f) {
      const auto G = ev.characterGlobals(c, f);
      const mat4 P = ev.propWorld(0, f);
      for (int i = 0; i <= 4; ++i) for (int j = 0; j < 12; ++j) {
        const float ang = 6.2831853f * float(j) / 12, y = H * float(i) / 4;
        const vec3 p = vec3(P * vec4(R * std::cos(ang), y, R * std::sin(ang), 1));
        const float g = segmentClearance(B, G, p, p, 0, 'R').gap;
        if (g < worst) worst = g, at = f;
      }
    }
    out[scene->characters[c].name] = {{"cup_surface_min_gap_mm", worst * 1000}, {"frame", at}};
  }
  std::cout << out.dump(1) << std::endl;
}
