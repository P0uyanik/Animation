// Scratch (T-114, after T-112b's dump_expansion.cpp; not part of the build): writes a scene with its verbs expanded
// (as actions.cpp does, with the scene's timing profile: the calibrated default when "timing" is absent) and the
// generated reaction actions appended, so the animcheck rules (timing.py, acting.py) see every beat.
//   g++ -std=c++23 -O1 -I engine -I build/engine dump_expanded.cpp -L build/engine -lplush_scene -lplush_model
//       -lplush_anim -lplush_fuzz -lplush_geom -lplush_core -lembree4 -o dump_expanded
//   dump_expanded <repo root> <resolved scene.json> > expanded.scene.json
#include <fstream>
#include <iostream>
#include "anim/personality.h"
#include "scene/scene.h"
#include "scene/verbs.h"
using namespace plush;
int main(int argc, char** argv) {
  const std::filesystem::path root = argv[1], scenePath = argv[2];
  auto s = loadScene(scenePath);
  if (!s) { std::cerr << s.error().message << "\n"; return 1; }
  Scene scene = *s;
  SceneEvaluator ev;
  auto r = ev.load(scene, EvalOptions{2.5f, 1.0f, false, 0});
  if (!r) { std::cerr << "LOAD ERROR: " << r.error().message << "\n"; return 1; }
  for (auto& w : ev.warnings()) std::cerr << "warning: " << w << "\n";
  TimingProfile T = loadTimingProfile(root / "content/timing" / (scene.timingProfile() + ".timing.json")).value();
  std::vector<PersonalityProfile> P;
  P.reserve(4);
  VerbContext vc;
  vc.timing = &T;
  vc.events = !scene.events.is_null();
  vc.fps = 24;
  vc.frameStart = scene.frameStart;
  for (size_t c = 0; c < scene.characters.size(); ++c) {
    const PersonalityProfile* pp = nullptr;
    if (scene.characters[c].personality.is_string()) {
      P.push_back(loadPersonality(root / "content/personality" / (scene.characters[c].personality.get<std::string>() + ".json")).value());
      pp = &P.back();
    }
    VerbContext::Character ch{scene.characters[c].name, pp};
    const Skeleton& sk = ev.characters()[c].asset.skeleton;
    for (char side : {'L', 'R'}) {
      const int hb = sk.find(std::string("hand.") + side), mb = sk.bones[hb].parent, rb = sk.bones[mb].parent;
      ch.armLength[side == 'L' ? 0 : 1] = glm::distance(sk.bones[rb].head, sk.bones[mb].head) + glm::distance(sk.bones[mb].head, sk.bones[hb].head);
    }
    vc.characters.push_back(ch);
  }
  std::vector<PropAsset> assets;
  for (auto& p : scene.props) assets.push_back(loadAsset(root / "content/assets" / (p.id.substr(5) + ".asset.json")).value());
  for (size_t p = 0; p < scene.props.size(); ++p) vc.props.push_back({scene.props[p].name, &assets[p], scene.props[p].transform, scene.props[p].parent});
  vc.verb = [&](const std::string& id) { return loadVerb(root / "content/verbs" / (id + ".verb.json")); };
  auto x = expandVerbs(scene.actions, vc);
  if (!x) { std::cerr << x.error().message() << "\n"; return 1; }
  Json doc = Json::parse(std::ifstream(scenePath));
  Json acts = x->actions;
  for (const Json& a : ev.reactionActions()) acts.push_back(a);
  doc["actions"] = acts;
  Json evs = doc.contains("events") ? doc["events"] : Json::array();
  for (const Json& e : x->events) evs.push_back(e);
  doc["events"] = evs;
  Json ph = Json::array();
  for (auto& p : x->phases) ph.push_back({{"action", p.action}, {"verb", p.verb}, {"character", p.character}, {"phase", p.phase}, {"part", p.part},
                                          {"side", p.side ? std::string(1, p.side) : ""}, {"from", p.from}, {"to", p.to}});
  doc["x_t114_phases"] = ph;
  std::cout << doc.dump(1) << "\n";
}
