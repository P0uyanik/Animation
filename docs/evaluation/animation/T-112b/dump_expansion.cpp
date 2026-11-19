// Scratch: expand a scene's verbs (as actions.cpp does) and dump the expansion + compile warnings. Not part of the build.
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
  for (CharacterDesc& c : scene.characters) {
    if (c.name == "boy") c.asset = (root / "tests/data/imported/boy_yellow_hoodie_1.0.0/character.json").string();
    if (c.name == "girl") c.asset = (root / "tests/data/imported/girl_auburn_bun_glasses_m3/character.json").string();
  }
  if (argc > 4) {  // packages given
    for (CharacterDesc& c : scene.characters) {
      if (c.name == "boy") c.asset = argv[3];
      if (c.name == "girl") c.asset = argv[4];
    }
  }
  SceneEvaluator ev;
  auto r = ev.load(scene, EvalOptions{2.5f, 1.0f, false, 0});
  if (!r) { std::cerr << "LOAD ERROR: " << r.error().message << "\n"; }
  for (auto& w : ev.warnings()) std::cerr << "warning: " << w << "\n";
  // expansion
  TimingProfile T = loadTimingProfile(root / "content/timing/calibrated.timing.json").value();
  std::vector<PersonalityProfile> P;
  P.reserve(4);
  VerbContext vc;
  vc.timing = scene.timing.is_string() ? &T : nullptr;
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
    if (r) {
      const Skeleton& sk = ev.characters()[c].asset.skeleton;
      for (char side : {'L', 'R'}) {
        const int hb = sk.find(std::string("hand.") + side), mb = sk.bones[hb].parent, rb = sk.bones[mb].parent;
        ch.armLength[side == 'L' ? 0 : 1] = glm::distance(sk.bones[rb].head, sk.bones[mb].head) + glm::distance(sk.bones[mb].head, sk.bones[hb].head);
      }
    }
    vc.characters.push_back(ch);
  }
  std::vector<PropAsset> assets;
  for (auto& p : scene.props) assets.push_back(loadAsset(root / "content/assets" / (p.id.substr(5) + ".asset.json")).value());
  for (size_t p = 0; p < scene.props.size(); ++p) vc.props.push_back({scene.props[p].name, &assets[p], scene.props[p].transform, scene.props[p].parent});
  vc.verb = [&](const std::string& id) { return loadVerb(root / "content/verbs" / (id + ".verb.json")); };
  auto x = expandVerbs(scene.actions, vc);
  if (!x) { std::cerr << x.error().message() << "\n"; return 1; }
  Json out = scene.actions.is_null() ? Json() : Json::object();
  out["actions"] = x->actions;
  out["events"] = x->events;
  Json ph = Json::array();
  for (auto& p : x->phases) ph.push_back({{"action", p.action}, {"verb", p.verb}, {"character", p.character}, {"phase", p.phase}, {"part", p.part},
                                          {"side", p.side ? std::string(1, p.side) : ""}, {"from", p.from}, {"to", p.to}});
  out["phases"] = ph;
  std::cout << out.dump(1) << "\n";
}
