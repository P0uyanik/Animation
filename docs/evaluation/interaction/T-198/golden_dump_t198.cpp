// T-198 evidence tool (not part of the gate): dumps the world transform of every bone, per frame and character, of the
// six content golden scenes (cast = the imported test packages, as tests/test_bake_golden.cpp contentScene) and the
// test_interaction/visibleGrip scenes (as test_bake_golden.cpp visibleGrip), so two
// builds (before / after) can be compared with golden_delta_t198.py. One line per bone: scene char frame bone pos quat.
//   g++ -std=c++23 -O2 -DNDEBUG -I engine docs/evaluation/interaction/T-198/golden_dump_t198.cpp -Lbuild/fast-dev/engine \
//       -lplush_scene -lplush_model -lplush_fuzz -lplush_anim -lplush_geom -lplush_core -o build/fast-dev/golden_dump_t198
//   build/fast-dev/golden_dump_t198 <repository root> > dump.txt
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <string>

#include <glm/gtc/quaternion.hpp>

#include "scene/asset_library.h"
#include "scene/scene.h"

using namespace plush;

void dump(const std::string& rel, const Scene& sc) {
  SceneEvaluator ev;
  if (auto r = ev.load(sc, EvalOptions{2.5f, 1.0f, false, 0}); !r) std::fprintf(stderr, "%s\n", r.error().message.c_str()), std::exit(1);
  for (int f = sc.frameStart; f <= sc.frameEnd; ++f)
    for (size_t c = 0; c < sc.characters.size(); ++c) {
      const Skeleton& sk = ev.characters()[c].asset.skeleton;
      const auto g = ev.characterGlobals(c, f, nullptr);
      for (size_t i = 0; i < sk.bones.size(); ++i) {
        const quat q = glm::quat_cast(mat3(g[i]));
        std::printf("%s %s %d %s %.7g %.7g %.7g %.7g %.7g %.7g %.7g\n", rel.c_str(), sc.characters[c].name.c_str(), f, sk.bones[i].name.c_str(),
                    g[i][3].x, g[i][3].y, g[i][3].z, q.w, q.x, q.y, q.z);
      }
    }
}

// test_bake_golden.cpp visibleGrip(asset), the same construction.
Scene visibleGrip(const std::filesystem::path& root, const std::string& asset) {
  Scene s;
  s.name = "interaction test";
  s.path = root / "tests/data/imported/scene.json";
  s.rate = FrameRate{24, 1};
  s.frameStart = 1;
  s.frameEnd = 40;
  CharacterDesc c;
  c.name = "actor", c.asset = asset, c.life.enabled = true;
  s.characters.push_back(c);
  SceneEvaluator probe;
  if (!probe.load(s, EvalOptions{2.5f, 1.0f, false, 0})) std::exit(1);
  auto at = [&](const char* b) { return vec3(probe.characterGlobals(0, 1)[size_t(probe.characters()[0].asset.skeleton.find(b))][3]); };
  const vec3 shoulder = at("upperArm.R"), elbow = at("forearm.R");
  const float arm = glm::distance(shoulder, elbow) + glm::distance(elbow, at("hand.R"));
  const vec3 grip = shoulder + vec3(0.04f, -0.45f, 0.85f) * arm;
  const mat4 rot = assetTransformMatrix({vec3(0), vec3(0, 180, 0), vec3(1)});
  const PropAsset pa = loadAsset(root / "content/assets/felt_cup.asset.json").value();
  PropDesc cup;
  cup.name = "cup", cup.id = "prop.felt_cup";
  cup.transform.translation = grip - vec3(rot * vec4(pa.sockets.at("grip").translation, 0));
  cup.transform.rotationDeg = {0, 180, 0};
  s.props.push_back(cup);
  s.camera.position = cup.transform.translation + vec3(-1.5f, 0.3f, 0.2f);
  s.camera.target = cup.transform.translation;
  s.actions = Json::parse(R"([
      {"type": "grasp", "character": "actor", "hand": "R", "prop": "cup", "start": 5, "contact": 20},
      {"type": "hold", "character": "actor", "hand": "R", "start": 22, "end": 36, "by": [0, 0.04, 0]}])");
  s.interaction = Json{{"visibleGrip", true}};
  return s;
}

int main(int argc, char** argv) {
  const std::filesystem::path root = argc > 1 ? argv[1] : ".";
  for (auto [n, a] : {std::pair{"boy", "boy_yellow_hoodie_1.0.0/character.json"}, std::pair{"girl", "girl_auburn_bun_glasses_m3/character.json"},
                      std::pair{"engine", "../../../content/characters/girl_white_hair.character.json"}})
    dump(std::string("test_interaction/visibleGrip/") + n, visibleGrip(root, (root / "tests/data/imported" / a).string()));
  for (const char* rel : {"content/scenes/eval/exchange/shot.scene.json", "content/scenes/eval/handover/shot.scene.json",
                          "episodes/e901_clip_test/shots/s010/shot.scene.json", "episodes/e905_props_test/shots/s010/shot.scene.json",
                          "episodes/e907_exchange/shots/s010/shot.scene.json", "episodes/e907_exchange/shots/s010_calibrated/shot.scene.json"}) {
    auto s = loadScene(root / rel);
    if (!s) return std::fprintf(stderr, "%s\n", s.error().message.c_str()), 1;
    Scene sc = *s;
    for (CharacterDesc& c : sc.characters) {
      if (c.name == "boy") c.asset = (root / "tests/data/imported/boy_yellow_hoodie_1.0.0/character.json").string();
      if (c.name == "girl") c.asset = (root / "tests/data/imported/girl_auburn_bun_glasses_m3/character.json").string();
    }
    dump(rel, sc);
  }
  return 0;
}
