// T-030 arm-body clearance measurement from a shot bake (not part of the build). The bone globals are rebuilt from
// the baked skinning matrices (G = S * translate(head)), so any bake can be measured the same way, before or after a
// fix. Uses the shared model (scene/interaction.h: bodyClearanceModel + armClearance) of each character's package.
//   g++ -std=c++23 -O2 -I engine docs/evaluation/animation/T-030/measure_clearance.cpp -Lbuild/engine -lplush_scene \
//       -lplush_model -lplush_fuzz -lplush_anim -lplush_geom -lplush_core -o mc        (run from the repository root)
//   ./mc <bake.json> <scene name>=<package dir> [...]  > clearance.json
#include <fstream>
#include <iostream>

#include "model/imported_character.h"
#include "scene/interaction.h"

using namespace plush;

int main(int argc, char** argv) {
  if (argc < 3) { std::cerr << "usage: mc bake.json name=package ...\n"; return 2; }
  std::ifstream f(argv[1]);
  const Json bake = Json::parse(f);
  Json out;
  out["bake"] = argv[1];
  out["margin_mm"] = kArmBodyMargin * 1000;
  for (int a = 2; a < argc; ++a) {
    const std::string arg = argv[a];
    const std::string name = arg.substr(0, arg.find('=')), pkg = arg.substr(arg.find('=') + 1);
    auto ic = loadImportedCharacter(std::filesystem::path(pkg) / "character.json");
    if (!ic) { std::cerr << ic.error().message << "\n"; return 1; }
    const Skeleton& sk = ic->asset.skeleton;
    const BodyClearanceModel M = bodyClearanceModel(sk, ic->rig.meshes);
    Json& oc = out["characters"][name];
    oc["model_source"] = M.source;
    for (const auto& C : M.body)
      oc["body_capsules"][C.name] = {{"radius_side_mm", C.r1 * 1000}, {"radius_front_mm", C.r2 * 1000},
                                     {"length_mm", glm::length(C.p1 - C.p0) * 1000}};
    for (int s = 0; s < 2; ++s)
      oc["arm_surface_points"][s == 0 ? "L" : "R"] = M.arm[s].points.size();
    const Json* chj = nullptr;
    for (const Json& c : bake["characters"]) if (c["name"] == name) chj = &c;
    if (!chj) { std::cerr << "no character " << name << " in bake\n"; return 1; }
    std::vector<int> map;
    for (const auto& bn : (*chj)["bones"]) map.push_back(sk.find(bn.get<std::string>()));
    for (char side : {'L', 'R'}) {
      Json per = Json::array();
      float worst = 1e9f, upper = 1e9f, raw = 1e9f;
      int at = 0;
      std::string part, against;
      vec3 wp(0);
      for (const Json& fd : bake["frame_data"]) {
        const auto& skin = fd["characters"][name]["skin"];
        std::vector<mat4> G(sk.bones.size(), mat4(1));
        for (size_t i = 0; i < map.size(); ++i) {
          if (map[i] < 0) continue;
          mat4 S;
          for (int k = 0; k < 16; ++k) S[k / 4][k % 4] = skin[i * 16 + size_t(k)].get<float>();
          G[size_t(map[i])] = S * glm::translate(mat4(1), sk.bones[size_t(map[i])].head);
        }
        const ArmClearance c = armClearance(M, G, side);
        per.push_back(std::round(c.gap * 1e4) / 10);
        upper = std::min(upper, c.upperGap);
        raw = std::min(raw, c.rawGap);
        if (c.gap < worst) worst = c.gap, at = fd["frame"].get<int>(), part = c.part, against = c.against, wp = c.point;
      }
      oc["arms"][std::string(1, side)] = {{"min_gap_mm", worst * 1000}, {"frame", at}, {"part", part},
                                          {"against", against}, {"worst_point", {wp.x, wp.y, wp.z}}, {"upper_arm_min_gap_mm", upper * 1000}, {"raw_min_gap_mm_no_rest_allowance", raw * 1000}, {"gap_mm_per_frame", per}};
    }
  }
  std::cout << out.dump(1) << "\n";
}
